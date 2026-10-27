"""Offline smoke boundaries; no Docker daemon or real joined shell is used."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import smoke


class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.now = datetime.now(timezone.utc)
        self.run = smoke.Run(self.now - timedelta(minutes=1),
                             self.now + timedelta(minutes=19), self.directory)
        self.run.token = "offline"
        self.process = patch.object(smoke.subprocess, "Popen", side_effect=AssertionError("unmocked process"))
        self.process.start()
        self.addCleanup(self.process.stop)

    def invoke_main(self, expected):
        output = io.StringIO()
        with patch.object(smoke, "Run", return_value=self.run), \
                patch.object(smoke, "private_file", return_value=json.dumps(expected).encode()), \
                redirect_stdout(output):
            code = smoke.main([
                "--window-start", self.run.start.isoformat(),
                "--window-end", self.run.end.isoformat(),
                "--evidence-dir", str(self.directory), "--admission", "/private/admission",
            ])
        return code, json.loads(output.getvalue())

    def admission(self):
        journal = self.directory / "journal"
        journal.write_bytes(b"saved")
        journal.chmod(0o600)
        containers = {}
        for index, name in enumerate(smoke.NAMES):
            identity = dict(smoke.cli.LABELS, name="/" + name, id=str(index + 1) * 64,
                            user="1001:1001", workdir="/project", home_supported=True,
                            privileged=False, state="running", running=True,
                            paused=False, restarting=False, dead=False)
            containers[name] = {"metadata": {"identity": identity, "mounts": [],
                                              "image": "saved", "network_mode": "bridge"},
                                "processes": ["HEADER", "saved process"]}
        return {"containers": containers,
                "journals": {str(journal): smoke.hashlib.sha256(b"saved").hexdigest()},
                "absent_markers": [str(self.directory / "inactive")],
                "remote_journals": {"/run/ld01-cvpn-retained": {
                    "restore.json": "a" * 64, "cleanup.json": "b" * 64}}}

    def test_cutoff_during_verify_is_machine_readable_blocked(self):
        def admitted(expected):
            self.run.deadline = smoke.time.monotonic() + 300
        with patch.object(self.run, "admit", side_effect=admitted):
            code, report = self.invoke_main({})
        self.assertEqual(code, 2)
        self.assertEqual(report["result"], "BLOCKED")
        self.assertEqual(report["reason"], "outside authorized check-start window")

    def test_malformed_admission_objects_are_machine_readable_blocked(self):
        for expected in (["non-object"], {"journals": {}, "containers": ["bad"]},
                         {"containers": dict.fromkeys(smoke.NAMES), "journals": ["bad"]}):
            with self.subTest(expected=expected):
                code, report = self.invoke_main(expected)
                self.assertEqual(code, 2)
                self.assertEqual(report["result"], "BLOCKED")

    def test_process_drift_blocks_before_any_exec(self):
        expected = self.admission()
        responses = [subprocess.CompletedProcess([], 0, json.dumps(
            expected["containers"][smoke.NAMES[0]]["metadata"]).encode(), b""),
            subprocess.CompletedProcess([], 0, b"HEADER\nchanged process\n", b"")]
        with patch.object(self.run, "command", side_effect=responses) as command:
            with self.assertRaisesRegex(smoke.Blocked, "process/residual drift"):
                self.run.admit(expected)
        self.assertEqual(command.call_count, 2)
        self.assertTrue(all("exec" not in c.args[0] for c in command.call_args_list))

    def test_live_journal_mismatch_blocks_before_daily_identity_exec(self):
        expected = self.admission()
        responses = []
        for name in smoke.NAMES:
            saved = expected["containers"][name]
            responses.extend([
                subprocess.CompletedProcess([], 0, json.dumps(saved["metadata"]).encode(), b""),
                subprocess.CompletedProcess([], 0, "\n".join(saved["processes"]).encode(), b""),
            ])
        responses.append(subprocess.CompletedProcess([], 0, b'{}', b""))
        with patch.object(self.run, "command", side_effect=responses) as command:
            with self.assertRaisesRegex(smoke.Blocked, "live retained journal"):
                self.run.admit(expected)
        self.assertEqual(command.call_count, 5)
        argv = command.call_args.args[0]
        self.assertEqual(argv[:7], ["docker", "exec", "--user", "0:0", "1" * 64, "python3", "-I"])
        self.assertEqual(json.loads(argv[-1]), expected["remote_journals"])

    def test_verify_passes_and_rejects_duplicate_a_pid(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate):
                self.run.checks.clear()
                values = [["1001", "1001", "/home/session", "/project", pid,
                           home, "shared", network] for pid, home, network in (
                               ("11", "home-a", "net-a"),
                               ("11" if duplicate else "12", "home-a", "net-a"),
                               ("11", "home-b", "net-b"))]
                expected = {"project_identity": "shared", "containers": {
                    name: {"identities": value[5:]}
                    for name, value in zip(smoke.NAMES, (values[0], values[2]))}}
                sessions = [Mock() for _ in values]
                for session, value in zip(sessions, values):
                    session.observe.return_value = value
                    session.process.poll.return_value = None
                for session, code in zip(sessions, (37, 0, 0)):
                    session.exit.return_value = code
                responses = [subprocess.CompletedProcess([], 0, (
                    "NAME\tSTATE\n" + "".join(n + "\trunning\n" for n in smoke.NAMES)).encode(), b"")]
                responses.extend(subprocess.CompletedProcess([], 0, (
                    "NAME\tSTATE\tIDENTITY_SUPPORTED\n" + n + "\trunning\ttrue\n").encode(), b"")
                    for n in smoke.NAMES)
                responses.append(subprocess.CompletedProcess([], 1, b"",
                    b"join failed: interactive stdin and stdout TTY required\n"))
                with patch.object(self.run, "command", side_effect=responses), \
                        patch.object(self.run, "join", side_effect=sessions):
                    if duplicate:
                        with self.assertRaisesRegex(smoke.Failed, "concurrent-context-identities"):
                            self.run.verify(expected)
                        sessions[0].exit.assert_not_called()
                    else:
                        self.run.verify(expected)
                        sessions[0].exit.assert_called_once_with(37)
                        self.assertEqual(sessions[1].observe.call_count, 2)
                        self.assertEqual(self.run.checks[-1]["check"], "remaining-shell-exits")

    def test_expired_window_blocks_before_input_or_process(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = smoke.main([
                "--window-start", "2020-01-01T00:00:00Z",
                "--window-end", "2020-01-01T00:20:00Z",
                "--evidence-dir", str(self.directory), "--admission", "/does/not/exist",
            ])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue()), {
            "result": "BLOCKED", "reason": "outside authorized check-start window", "checks": []})

    def test_fixed_window_and_five_minute_cutoff(self):
        with self.assertRaises(smoke.Blocked):
            smoke.Run(self.now, self.now + timedelta(minutes=21), self.directory)
        with patch.object(self.run, "remaining", return_value=300), self.assertRaises(smoke.Blocked):
            self.run.command(["must-not-run"])

    def test_private_output_and_input_permissions(self):
        self.run.save(b"PRIVATE")
        path = next(self.directory.iterdir())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(smoke.private_file(path), b"PRIVATE")
        path.chmod(0o644)
        with self.assertRaises(smoke.Blocked):
            smoke.private_file(path)
        link = self.directory / "link"
        link.symlink_to(path)
        with self.assertRaises(smoke.Blocked):
            smoke.private_file(link)

    def test_timeout_is_bounded_and_private(self):
        with patch.object(smoke.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                ["docker"], 15, output=b"PRIVATE")) as command:
            with self.assertRaisesRegex(smoke.Failed, "subprocess deadline"):
                self.run.command(["docker"], 15)
        self.assertEqual(command.call_args.kwargs["timeout"], 15)
        self.assertTrue(any(p.read_bytes() == b"PRIVATE" for p in self.directory.iterdir()))

    def test_mount_order_only_is_not_drift(self):
        self.assertEqual(smoke.normalize({"mounts": [{"a": 1}, {"b": 2}]}),
                         smoke.normalize({"mounts": [{"b": 2}, {"a": 1}]}))

    def test_metadata_drift_blocks_before_exec(self):
        journal = self.directory / "journal"
        journal.write_bytes(b"saved")
        journal.chmod(0o600)
        expected = {
            "containers": {name: {"metadata": {"mounts": [], "image": "saved"}}
                           for name in smoke.NAMES},
            "journals": {str(journal): smoke.hashlib.sha256(b"saved").hexdigest()},
            "absent_markers": [str(self.directory / "inactive")],
        }
        response = subprocess.CompletedProcess([], 0, b'{"mounts":[],"image":"drift"}', b"")
        with patch.object(self.run, "command", return_value=response) as command:
            with self.assertRaisesRegex(smoke.Blocked, "configuration drift"):
                self.run.admit(expected)
        self.assertEqual(command.call_count, 1)
        self.assertEqual(command.call_args.args[0][:3], ["docker", "container", "inspect"])

    def test_pty_observation_requires_real_marker_lines(self):
        session = smoke.Session.__new__(smoke.Session)
        session.run, session.master = self.run, 123
        marker = Mock(hex="fixed")
        data = (b"prompt$ printf 'SMOKE_fixed_END'\r\nSMOKE_fixed\r\n"
                b"1001\r\n1001\r\n/home/session\r\n/project\r\n42\r\n"
                b"1:2\r\n3:4\r\nnet:[5]\r\nSMOKE_fixed_END\r\n")
        with patch.object(smoke.uuid, "uuid4", return_value=marker), \
                patch.object(smoke.os, "write"), \
                patch.object(smoke.select, "select", return_value=([123], [], [])), \
                patch.object(smoke.os, "read", return_value=data):
            self.assertEqual(session.observe(), ["1001", "1001", "/home/session", "/project",
                                                 "42", "1:2", "3:4", "net:[5]"])

    def test_exit_timeout_closes_only_created_client_without_retry(self):
        session = smoke.Session.__new__(smoke.Session)
        session.run, session.master = self.run, 123
        session.closed, session.exit_sent = False, False
        session.process = Mock()
        session.process.poll.return_value = None
        session.process.wait.side_effect = [subprocess.TimeoutExpired([], 15), 0]
        with patch.object(smoke.os, "write") as write, patch.object(smoke.os, "close"):
            with self.assertRaises(smoke.Failed):
                session.exit(37)
            self.assertFalse(session.close())
        write.assert_called_once_with(123, b"exit 37\n")
        session.process.terminate.assert_called_once_with()
        session.process.kill.assert_not_called()

    def test_unrequested_client_exit_and_nonzero_cleanup_are_unconfirmed(self):
        for exited in (True, False):
            with self.subTest(exited=exited):
                session = smoke.Session.__new__(smoke.Session)
                session.run, session.master = self.run, 123
                session.closed, session.exit_sent = False, False
                session.process = Mock()
                session.process.poll.return_value = 1 if exited else None
                session.process.wait.return_value = 1
                with patch.object(smoke.os, "write") as write, patch.object(smoke.os, "close"):
                    self.assertFalse(session.close())
                self.assertEqual(write.call_count, 0 if exited else 1)
                session.process.terminate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
