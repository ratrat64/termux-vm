"""Authorized, read-only LD01 live smoke; no authorization is created here."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import stat
import subprocess
import sys
import time
import uuid

import cli


NAMES = ("tvm-share-ld01-a", "tvm-share-ld01-b")
CLI = str(Path(__file__).with_name("cli.py"))
# Deliberately exclude environment, arbitrary labels and command arguments.
ADMISSION_FORMAT = (
    '{"identity":' + cli.INSPECT_FORMAT + ',"image":{{json .Image}},'
    '"network_mode":{{json .HostConfig.NetworkMode}},'
    '"mounts":{{json .Mounts}}}'
)
OBSERVE = (
    'id -u; id -g; printf "%s\\n" "$HOME" "$PWD" "$$"; '
    'stat -Lc "%d:%i" /home/session /project; readlink /proc/self/ns/net'
)
REMOTE_JOURNALS = """
import hashlib,json,os,pathlib,sys
try:
    expected = json.loads(sys.argv[1])
    assert set(map(str, pathlib.Path('/run').glob('ld01-cvpn*'))) == set(expected)
    found = {}
    for directory, files in expected.items():
        root = pathlib.Path(directory)
        assert root.is_dir() and not root.is_symlink()
        assert not os.path.lexists(root / 'active')
        found[directory] = {}
        for name in files:
            path = root / name
            assert path.is_file() and not path.is_symlink()
            found[directory][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(found, sort_keys=True))
except (OSError, ValueError, AssertionError):
    print('{}')
    sys.exit(1)
"""


class Blocked(Exception):
    pass


class Failed(Exception):
    pass


def require(predicate, reason, error=Blocked):
    if not predicate:
        raise error(reason)


def utc(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.utcoffset() == timedelta(0), "window must use UTC")
    return result


def private_file(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
            and info.st_uid == os.getuid(), "private input mode/owner invalid")
    return path.read_bytes()


def normalize(record):
    result = dict(record)
    result["mounts"] = sorted(result["mounts"], key=lambda m: json.dumps(m, sort_keys=True))
    return result


class Run:
    def __init__(self, start, end, evidence):
        require(end - start == timedelta(minutes=20), "window must be exactly 20 minutes")
        self.start, self.end = start, end
        # Monotonic cap also prevents a backwards wall-clock adjustment extending access.
        self.deadline = time.monotonic() + max(0, (end - datetime.now(timezone.utc)).total_seconds())
        self.evidence = evidence
        info = evidence.lstat()
        require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
                and info.st_uid == os.getuid(), "private evidence directory mode/owner invalid")
        self.number = 0
        self.checks = []
        self.sessions = []

    def remaining(self):
        return min((self.end - datetime.now(timezone.utc)).total_seconds(),
                   self.deadline - time.monotonic())

    def begin(self):
        require(datetime.now(timezone.utc) >= self.start and self.remaining() > 300,
                "outside authorized check-start window")

    def save(self, data):
        self.number += 1
        path = self.evidence / ("smoke-" + self.token + "-%03d.raw" % self.number)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data if isinstance(data, bytes) else data.encode())

    def command(self, argv, seconds=40):
        self.begin()
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                                    timeout=min(seconds, self.remaining() - 10))
        except subprocess.TimeoutExpired as exc:
            self.save((exc.stdout or b"") + (exc.stderr or b""))
            raise Failed("subprocess deadline") from None
        self.save(result.stdout + b"\nSTDERR\n" + result.stderr)
        return result

    def check(self, name, predicate):
        require(predicate, name, Failed)
        self.checks.append({"check": name, "result": "PASS"})

    def admit(self, expected):
        self.begin()
        require(isinstance(expected, dict), "admission must be an object")
        require(isinstance(expected.get("containers"), dict), "containers must be an object")
        require(isinstance(expected.get("journals"), dict), "journals must be an object")
        require(set(expected["containers"]) == set(NAMES), "expected A/B required")
        require(expected["journals"], "saved journal evidence required")
        require(expected["absent_markers"], "saved inactive-marker evidence required")
        for path, digest in expected["journals"].items():
            require(hashlib.sha256(private_file(Path(path))).hexdigest() == digest,
                    "journal evidence mismatch")
        for path in expected["absent_markers"]:
            require(not os.path.lexists(path), "unexpected active marker")
        for name in NAMES:
            saved = expected["containers"][name]
            result = self.command(["docker", "container", "inspect", "--format",
                                   ADMISSION_FORMAT, "--", name], 15)
            require(result.returncode == 0, "metadata access denied or unavailable")
            actual = json.loads(result.stdout)
            require(normalize(actual) == normalize(saved["metadata"]), "container configuration drift")
            identity = actual["identity"]
            require(identity["name"] == "/" + name and cli.identity_supported(identity)
                    and cli.eligible(dict(identity, name=name))
                    and re.fullmatch(r"[0-9a-f]{64}", identity["id"])
                    and identity["state"] == "running" and identity["running"] is True
                    and all(identity[k] is False for k in ("paused", "restarting", "dead")),
                    "unsupported or stopped target")
            result = self.command(["docker", "top", identity["id"], "-eo", "pid,ppid,stat,comm"], 15)
            require(result.returncode == 0 and result.stdout.decode().splitlines()
                    == saved["processes"], "process/residual drift")
        remote = expected.get("remote_journals")
        require(isinstance(remote, dict) and remote, "live retained journal evidence required")
        for directory, files in remote.items():
            require(re.fullmatch(r"/run/ld01-cvpn[^/]+", directory)
                    and isinstance(files, dict) and files
                    and {"restore.json", "cleanup.json"} <= set(files),
                    "invalid retained journal directory or files")
            require(all(name not in (".", "..", "active") and "/" not in name
                        and isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
                        for name, digest in files.items()), "invalid retained journal hashes")
        result = self.command([
            "docker", "exec", "--user", "0:0", expected["containers"][NAMES[0]]["metadata"]["identity"]["id"],
            "python3", "-I", "-c", REMOTE_JOURNALS, json.dumps(remote, sort_keys=True)], 15)
        require(result.returncode == 0 and json.loads(result.stdout) == remote,
                "live retained journal or active-marker drift")
        host = os.stat(expected["host_project"])
        require(f"{host.st_dev}:{host.st_ino}" == expected["project_identity"],
                "host shared project identity drift")
        for name in NAMES:
            saved = expected["containers"][name]
            result = self.command(["docker", "exec", "--user", "1001:1001", "--workdir",
                                   "/project", saved["metadata"]["identity"]["id"],
                                   "bash", "--noprofile", "--norc", "-ic", OBSERVE], 15)
            lines = result.stdout.decode().splitlines()
            require(result.returncode == 0 and len(lines) == 8, "identity observation unavailable")
            require(lines[:4] == ["1001", "1001", "/home/session", "/project"]
                    and lines[5:] == saved["identities"]
                    and lines[6] == expected["project_identity"], "saved resource identity drift")
        self.check("admission", True)

    def verify(self, expected):
        result = self.command([sys.executable, CLI, "list"])
        self.check("list", result.returncode == 0 and not result.stderr and result.stdout.decode()
                   == "NAME\tSTATE\n" + "".join(n + "\trunning\n" for n in NAMES))
        for name in NAMES:
            result = self.command([sys.executable, CLI, "status", name])
            self.check("status-" + name[-1], result.returncode == 0 and not result.stderr
                       and result.stdout.decode() == "NAME\tSTATE\tIDENTITY_SUPPORTED\n"
                       + name + "\trunning\ttrue\n")
        result = self.command([sys.executable, CLI, "join", NAMES[0]])
        self.check("non-tty-refusal", result.returncode == 1 and result.stdout == b""
                   and result.stderr == b"join failed: interactive stdin and stdout TTY required\n")
        a1, a2, b = [self.join(name) for name in (NAMES[0], NAMES[0], NAMES[1])]
        observations = [s.observe() for s in (a1, a2, b)]
        for index, (name, values) in enumerate(zip((NAMES[0], NAMES[0], NAMES[1]), observations)):
            self.check("daily-identity-%d" % index,
                       values[:4] == ["1001", "1001", "/home/session", "/project"]
                       and values[4].isdigit() and values[5:] == expected["containers"][name]["identities"])
        x, y, z = observations
        self.check("concurrent-context-identities", x[4] != y[4] and x[5:] == y[5:]
                   and x[5] != z[5] and x[7] != z[7]
                   and x[6] == z[6] == expected["project_identity"]
                   and all(s.process.poll() is None for s in (a1, a2, b)))
        self.begin()
        self.check("exit-37", a1.exit(37) == 37)
        self.begin()
        self.check("surviving-a-shell", a2.observe() == y)
        self.begin()
        self.check("remaining-shell-exits", a2.exit(0) == 0 and b.exit(0) == 0)

    def join(self, name):
        self.begin()
        session = Session(self, name)
        self.sessions.append(session)
        return session


class Session:
    def __init__(self, run, name):
        self.run = run
        self.master, slave = pty.openpty()
        try:
            self.process = subprocess.Popen([sys.executable, CLI, "join", name],
                                            stdin=slave, stdout=slave, stderr=slave,
                                            start_new_session=True)
        except BaseException:
            os.close(self.master)
            raise
        finally:
            os.close(slave)
        self.closed = False
        self.exit_sent = False

    def observe(self):
        self.run.begin()
        marker = "SMOKE_" + uuid.uuid4().hex
        command = "printf '\\n%s\\n' " + marker + "; " + OBSERVE + "; printf '%s\\n' " + marker + "_END\n"
        os.write(self.master, command.encode())
        end = time.monotonic() + min(20, self.run.remaining() - 10)
        data = b""
        try:
            while time.monotonic() < end:
                if select.select([self.master], [], [], max(0, end - time.monotonic()))[0]:
                    chunk = os.read(self.master, 65536)
                    if not chunk:
                        break
                    data += chunk
                    require(len(data) <= 1024 * 1024, "session output limit", Failed)
                    lines = data.decode(errors="replace").replace("\r", "").split("\n")
                    if marker in lines and marker + "_END" in lines:
                        first, last = lines.index(marker), lines.index(marker + "_END")
                        values = lines[first + 1:last]
                        require(len(values) == 8, "session observation malformed", Failed)
                        return values
        except OSError:
            raise Failed("session disconnected") from None
        finally:
            self.run.save(data)
        raise Failed("session deadline")

    def exit(self, code, cleanup=False):
        if not cleanup:
            self.run.begin()
        require(not self.exit_sent, "shell exit already requested", Failed)
        self.exit_sent = True
        os.write(self.master, ("exit %d\n" % code).encode())
        try:
            return self.process.wait(timeout=min(15, max(0.1, self.run.remaining() - 5)))
        except subprocess.TimeoutExpired:
            raise Failed("shell exit deadline") from None

    def close(self):
        if self.closed:
            return True
        self.closed = True
        exited = self.process.poll() is not None
        clean = exited and self.exit_sent
        try:
            if not exited:
                try:
                    require(not self.exit_sent and self.run.remaining() > 5,
                            "closure deadline", Failed)
                    clean = self.exit(0, cleanup=True) == 0
                except (OSError, Failed):
                    # Only this run's client PID; never a process group/container kill.
                    if self.process.poll() is None:
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                            self.process.wait(timeout=2)
        finally:
            os.close(self.master)
        return clean


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args(argv)
    run = None
    outcome, reason = "BLOCKED", "admission unavailable"
    try:
        run = Run(utc(args.window_start), utc(args.window_end), args.evidence_dir)
        run.token = uuid.uuid4().hex
        run.begin()  # No evidence reads or subprocesses outside the original window.
        expected = json.loads(private_file(args.admission))
        run.admit(expected)
        outcome = "FAIL"
        run.verify(expected)
        outcome, reason = "PASS", "all predicates satisfied"
    except Blocked as exc:
        outcome, reason = "BLOCKED", str(exc)
    except Failed as exc:
        outcome, reason = "FAIL", str(exc)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        reason = "required evidence or observation unavailable"
    except KeyboardInterrupt:
        outcome, reason = "FAIL", "interrupted"
    finally:
        if run:
            for session in run.sessions:
                try:
                    if not session.close():
                        outcome, reason = "FAIL", "session closure unconfirmed"
                except (OSError, subprocess.SubprocessError):
                    outcome, reason = "FAIL", "session closure unconfirmed"
    report = {"result": outcome, "reason": reason, "checks": run.checks if run else []}
    print(json.dumps(report, sort_keys=True))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[outcome]


if __name__ == "__main__":
    sys.exit(main())
