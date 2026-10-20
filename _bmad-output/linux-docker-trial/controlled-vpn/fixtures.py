"""Controlled LD01 fixtures; stdlib only, no heartbeat reconnection."""

import argparse
import http.server
import json
import os
import select
import socket
import socketserver
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
    parser.add_argument("mode", choices=("http", "heartbeat", "hold", "fault-hold", "shell", "fresh"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19090)
    parser.add_argument("--fixture", default="ld01-controlled")
    args = parser.parse_args()
    if args.mode == "fresh":
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
