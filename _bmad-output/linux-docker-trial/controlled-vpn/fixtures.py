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
import uuid


def emit(value):
    print(json.dumps(value), flush=True)


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


def hold(host, port):
    # Exactly one socket creation. Any timeout/reset/protocol error exits FAIL.
    with socket.create_connection((host, port), timeout=5) as sock:
        identity = {"local": sock.getsockname(), "peer": sock.getpeername(),
                    "inode": os.fstat(sock.fileno()).st_ino}
        stream = sock.makefile("rwb", buffering=0)
        connection = None
        seq = 0
        while True:
            seq += 1
            stream.write((json.dumps({"seq": seq}) + "\n").encode())
            reply = json.loads(stream.readline(256))
            if connection is None:
                connection = reply["connection"]
            if reply != {"connection": connection, "seq": seq}:
                raise ValueError("heartbeat identity/sequence changed")
            emit({"kind": "ack", "seq": seq, "connection": connection,
                  "socket": identity, "monotonic": time.monotonic()})
            if select.select([sys.stdin], [], [], 0.5)[0]:
                line = sys.stdin.readline()
                if line.strip() != "stop":
                    raise ValueError("heartbeat controller disappeared")
                emit({"kind": "finished", "acks": seq, "connection": connection,
                      "socket": identity, "reconnects": 0, "errors": 0})
                return


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
        elif action == "quit":
            return
        else:
            raise ValueError("unknown shell request")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("http", "heartbeat", "hold", "shell"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19090)
    parser.add_argument("--fixture", default="ld01-controlled")
    args = parser.parse_args()
    if args.mode == "hold":
        hold(args.host, args.port)
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
