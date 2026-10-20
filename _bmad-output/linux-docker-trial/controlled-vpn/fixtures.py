"""Controlled LD01 fixtures; stdlib only, no heartbeat reconnection."""

import argparse
import http.server
import json
import os
import select
import socket
import socketserver
import struct
import subprocess
import sys
import time
import traceback
import uuid


def emit(value):
    print(json.dumps(value), flush=True)


def fresh(host, port):
    with socket.create_connection((host, port), timeout=2) as sock:
        sock.sendall(b'{"seq":1}\n')
        reply = json.loads(sock.makefile("rb").readline(256))
        if reply.get("seq") != 1 or not reply.get("connection"):
            raise ValueError("fresh canary protocol mismatch")
        return reply


class Heartbeat(socketserver.StreamRequestHandler):
    def handle(self):
        connection = uuid.uuid4().hex
        self.connection.settimeout(15)
        expected = 1
        while line := self.rfile.readline(256):
            request = json.loads(line)
            if request != {"seq": expected}:
                return
            self.wfile.write((json.dumps({"connection": connection, "seq": expected}) + "\n").encode())
            self.wfile.flush()
            expected += 1


class Identity(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"fixture": self.server.fixture, "service": "service.ld01.test"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def dns_reply(packet, ipv4):
    """Bounded lab-only DNS: one plain question, optional EDNS, no resolver calls."""
    if not 12 <= len(packet) <= 512:
        raise ValueError("DNS packet length")
    ident, flags, questions, answers, authority, additional = struct.unpack('!6H', packet[:12])
    if flags & ~0x0130 or (questions, answers, authority) != (1, 0, 0) or additional > 1:
        raise ValueError("DNS query header")
    offset, labels = 12, []
    while True:
        if offset >= len(packet): raise ValueError("truncated DNS name")
        size = packet[offset]
        offset += 1
        if size == 0: break
        if size > 63 or offset + size > len(packet): raise ValueError("DNS label")
        labels.append(packet[offset:offset + size].lower())
        offset += size
    if offset - 12 > 255 or offset + 4 > len(packet):
        raise ValueError("DNS question length")
    kind, klass = struct.unpack('!HH', packet[offset:offset + 4])
    offset += 4
    question = packet[12:offset]
    opt = b''
    if additional:
        # Validate EDNS options locally; advertise only our bounded response size.
        if offset + 11 > len(packet) or packet[offset:offset + 3] != b'\0\0)':
            raise ValueError("DNS additional record")
        edns_flags = struct.unpack('!I', packet[offset + 5:offset + 9])[0]
        if edns_flags & ~0x8000:
            raise ValueError("DNS OPT header")
        length = struct.unpack('!H', packet[offset + 9:offset + 11])[0]
        offset += 11
        end = offset + length
        if end != len(packet): raise ValueError("DNS OPT length")
        while offset < end:
            if offset + 4 > end: raise ValueError("DNS option header")
            length = struct.unpack('!H', packet[offset + 2:offset + 4])[0]
            offset += 4 + length
            if offset > end: raise ValueError("DNS option length")
        opt = b'\0' + struct.pack('!HHIH', 41, 512, edns_flags, 0)
    if offset != len(packet): raise ValueError("DNS trailing data")
    response_flags = 0x8000 | (flags & 0x0100)  # QR/RD only; recursion unavailable.
    if klass != 1 or kind not in (1, 28) or len(labels) < 3 or labels[-2:] != [b'ld01', b'test']:
        return struct.pack('!6H', ident, response_flags | 5, 1, 0, 0, additional) + question + opt
    response_flags |= 0x0400  # Authoritative for every private wildcard label.
    if kind == 1:
        record = b'\xc0\x0c' + struct.pack('!HHIH', 1, 1, 0, 4) + ipv4
        return struct.pack('!6H', ident, response_flags, 1, 1, 0, additional) + question + record + opt
    zone = b'\x04ld01\x04test\0'
    soa = b'\x02ns' + zone + b'\x0ahostmaster' + zone + struct.pack('!5I', 1, 60, 60, 300, 0)
    record = zone + struct.pack('!HHIH', 6, 1, 0, len(soa)) + soa
    return struct.pack('!6H', ident, response_flags, 1, 0, 1, additional) + question + record + opt


class DNSUDP(socketserver.BaseRequestHandler):
    def handle(self):
        packet, sock = self.request
        try:
            sock.sendto(dns_reply(packet, self.server.ipv4), self.client_address)
        except (ValueError, OSError):
            pass  # Malformed datagrams are dropped; the service stays alive.


class DNSTCP(socketserver.BaseRequestHandler):
    def handle(self):
        deadline = time.monotonic() + 2
        def read(size):
            data = b''
            while len(data) < size:
                remaining = deadline - time.monotonic()
                if remaining <= 0: raise ValueError("DNS frame deadline")
                self.request.settimeout(remaining)
                chunk = self.request.recv(size - len(data))
                if not chunk: raise ValueError("truncated DNS frame")
                data += chunk
            return data
        try:
            size = struct.unpack('!H', read(2))[0]
            if not 12 <= size <= 512: raise ValueError("DNS frame length")
            reply = dns_reply(read(size), self.server.ipv4)
            remaining = deadline - time.monotonic()
            if remaining <= 0: return
            self.request.settimeout(remaining)
            self.request.sendall(struct.pack('!H', len(reply)) + reply)
        except (ValueError, OSError):
            pass  # One bounded request per connection; socketserver closes it.


class DNSTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def dns(host, port):
    ipv4 = socket.inet_pton(socket.AF_INET, host)
    with DNSTCPServer((host, port), DNSTCP) as tcp, \
            socketserver.UDPServer(tcp.server_address, DNSUDP) as udp:
        tcp.ipv4 = udp.ipv4 = ipv4
        while True:
            for server in select.select([udp, tcp], [], [])[0]:
                server.handle_request()


def hold(host, port, fault=False):
    # Exactly one socket creation. Any timeout/reset/protocol error exits FAIL.
    with socket.create_connection((host, port), timeout=5) as sock:
        identity = {"local": sock.getsockname(), "peer": sock.getpeername(),
                    "inode": os.fstat(sock.fileno()).st_ino}
        connection = None
        seq = 0
        acknowledged = 0
        pending = b""
        errors = 0
        while True:
            seq += 1
            if fault and connection is not None:
                emit({"kind": "attempt", "seq": seq, "socket": identity, "monotonic": time.monotonic()})
            try:
                sock.sendall((json.dumps({"seq": seq}) + "\n").encode())
                while b"\n" not in pending:
                    chunk = sock.recv(256)
                    if not chunk: raise ConnectionError("heartbeat closed")
                    pending += chunk
                    if len(pending) > 512: raise ValueError("heartbeat frame too large")
                line, pending = pending.split(b"\n", 1)
                reply = json.loads(line)
            except OSError as error:
                if not fault: raise
                errors += 1
                emit({"kind": "blocked", "seq": seq, "socket": identity,
                      "error": type(error).__name__, "monotonic": time.monotonic()})
                if select.select([sys.stdin], [], [], .5)[0]:
                    if sys.stdin.readline().strip() != "stop": raise ValueError("controller disappeared")
                    emit({"kind": "finished", "socket": identity, "errors": errors, "reconnects": 0})
                    return
                continue
            if connection is None:
                connection = reply["connection"]
            if reply != {"connection": connection, "seq": acknowledged + 1 if fault else seq}:
                raise ValueError("heartbeat identity/sequence changed")
            acknowledged = reply["seq"]
            emit({"kind": "ack", "seq": acknowledged, "connection": connection,
                  "socket": identity, "monotonic": time.monotonic()})
            if select.select([sys.stdin], [], [], 0.5)[0]:
                line = sys.stdin.readline()
                if line.strip() != "stop":
                    raise ValueError("heartbeat controller disappeared")
                emit({"kind": "finished", "acks": seq, "connection": connection,
                       "socket": identity, "reconnects": 0, "errors": errors})
                return


def probes(server, direct, connected, stage=None, result=None):
    """Unique private labels never reach an unrelated resolver deliberately."""
    name = uuid.uuid4().hex + ".ld01.test"
    if result is None: result = {}
    result.update(name=name, monotonic=time.monotonic(), dns=[])
    stage = stage or (lambda _: None)
    stage('application-A')
    try:
        result["application"] = sorted({x[4][0] for x in socket.getaddrinfo(name, 8080, socket.AF_INET)})
    except OSError:
        result["application"] = []
    stage('application-AAAA')
    try:
        result["application_aaaa"] = sorted({x[4][0] for x in socket.getaddrinfo(
            uuid.uuid4().hex + ".ld01.test", 8080, socket.AF_INET6)})
    except OSError:
        result["application_aaaa"] = []
    for resolver in (server, "127.0.0.11"):
        for protocol in ("udp", "tcp"):
            for kind in ("A", "AAAA"):
                stage('dns-' + ('lab' if resolver == server else 'embedded') + '-' + protocol + '-' + kind)
                query = uuid.uuid4().hex + ".ld01.test"
                answer = subprocess.run(["dig", "@" + resolver, "+time=1", "+tries=1", "+noall", "+comments", "+answer",
                    *( ["+tcp"] if protocol == "tcp" else []), query, kind],
                    capture_output=True, text=True, timeout=3)
                records = [line.split() for line in answer.stdout.splitlines() if line and not line.startswith(";")]
                positive = (answer.returncode == 0 and "status: NOERROR" in answer.stdout and
                            " aa" in answer.stdout and
                            (not records if kind == "AAAA" else
                             len(records) == 1 and records[0][-2:] == ["A", server]))
                result["dns"].append(dict(resolver=resolver, protocol=protocol, kind=kind,
                                          positive=positive, responded="status:" in answer.stdout,
                                          exit=answer.returncode, output=answer.stdout[-2000:]))
    stage('literal-http')
    try:
        with socket.create_connection((server, 8080), timeout=1) as sock:
            sock.sendall(b"GET / HTTP/1.0\r\nHost: service.ld01.test\r\n\r\n")
            data = b""
            while chunk := sock.recv(4096): data += chunk
            result["http"] = json.loads(data.split(b"\r\n\r\n", 1)[1])
    except OSError:
        result["http"] = None
    # Fresh, sequenced direct-IP canary, separate from the VPN-only forward.
    stage('direct-canary')
    result["direct"] = fresh(direct, 20992)
    if not connected:
        stage('public-dns')
        try:
            result["public_dns"] = bool(socket.getaddrinfo("example.com", 443))
        except OSError:
            result["public_dns"] = False
    if connected:
        stage('validate-private-baseline')
        if result["application"] != [server] or result["application_aaaa"] or result["http"] is None:
            raise ValueError("positive private baseline failed")
        stage('validate-dns-baseline')
        if not all(d["positive"] == (d["resolver"] == server) for d in result["dns"]):
            raise ValueError("positive DNS/embedded rejection mismatch")
        if any(d["responded"] for d in result["dns"] if d["resolver"] != server):
            raise ValueError("embedded DNS replied despite containment")
        stage('named-http')
        with socket.create_connection((name, 8080), timeout=2) as sock:
            sock.sendall(b"GET / HTTP/1.0\r\nHost: service.ld01.test\r\n\r\n")
            body = b""
            while chunk := sock.recv(4096): body += chunk
            result["named_http"] = json.loads(body.split(b"\r\n\r\n", 1)[1])
        stage('validate-named-http')
        if result["named_http"] != result["http"]: raise ValueError("named HTTP fixture mismatch")
    return result


def probe_report(action, server, direct):
    """One structured result per RPC, progress/tracebacks only on private stderr."""
    result, current = {}, None
    def stage(name):
        nonlocal current
        if current is not None:
            print(json.dumps(dict(kind='probe-stage', stage=current, status='completed', time=time.time())), file=sys.stderr, flush=True)
        current = name
        print(json.dumps(dict(kind='probe-stage', stage=name, status='started', time=time.time())), file=sys.stderr, flush=True)
    try:
        if action == 'off_probe':
            stage('off-public-dns')
            if not socket.getaddrinfo('example.com', 443): raise ValueError('baseline public DNS failed')
            result['public_dns'] = True
            stage('off-direct-canary')
            result['direct'] = fresh(direct, 20992)
        else:
            probes(server, direct, action == 'baseline_probe', stage=stage, result=result)
        stage('complete')
        return result
    except Exception as error:
        print(json.dumps(dict(kind='probe-stage', stage=current, status='failed', time=time.time())), file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return dict(error=dict(stage=current, type=type(error).__name__, message=str(error)), partial=result)


def shell():
    """Persistent non-root joined shell RPC; privileged actions are controller requests."""
    for line in sys.stdin:
        request = json.loads(line)
        action = request["action"]
        identity = {"pid": os.getpid(), "shell_pid": os.getppid(), "uid": os.getuid(),
                    "gid": os.getgid(), "net": os.readlink("/proc/self/ns/net")}
        if action in ("identity", "connect", "disconnect"):
            emit({"identity": identity, "request": action})
        elif action == "probe":
            answers = sorted({x[4][0] for x in socket.getaddrinfo(
                "service.ld01.test", 8080, socket.AF_INET, socket.SOCK_STREAM)})
            # No proxy environment, redirects or retry; use the private name directly.
            with socket.create_connection(("service.ld01.test", 8080), timeout=5) as sock:
                sock.sendall(b"GET / HTTP/1.0\r\nHost: service.ld01.test\r\n\r\n")
                response = b""
                while chunk := sock.recv(4096):
                    response += chunk
            body = json.loads(response.split(b"\r\n\r\n", 1)[1])
            dns = subprocess.check_output(["dig", "+time=2", "+tries=1", "service.ld01.test"], text=True)
            emit({"identity": identity, "answers": answers, "http": body, "dig": dns})
        elif action in ("fault_probe", "baseline_probe", "off_probe"):
            emit({"identity": identity, **probe_report(action, request.get('server'), request['direct'])})
        elif action == "quit":
            return
        else:
            raise ValueError("unknown shell request")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("http", "dns", "heartbeat", "hold", "fault-hold", "shell", "fresh"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19090)
    parser.add_argument("--fixture", default="ld01-controlled")
    args = parser.parse_args()
    if args.mode == "dns":
        dns(args.host, args.port)
    elif args.mode == "fresh":
        emit(fresh(args.host, args.port))
    elif args.mode in ("hold", "fault-hold"):
        hold(args.host, args.port, args.mode == "fault-hold")
    elif args.mode == "shell":
        shell()
    elif args.mode == "http":
        server = http.server.ThreadingHTTPServer((args.host, args.port), Identity)
        server.fixture = args.fixture
        server.serve_forever()
    else:
        with socketserver.ThreadingTCPServer((args.host, args.port), Heartbeat) as server:
            server.daemon_threads = True
            server.serve_forever()


if __name__ == "__main__":
    main()
