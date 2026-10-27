"""Offline acceptance checks: every process and terminal boundary is mocked."""

from collections import deque
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import io
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

import cli


A, B = "tvm-share-ld01-a", "tvm-share-ld01-b"
ID = "a1" * 32
PRIVATE = "PRIVATE_DOCKER_DIAGNOSTICS_OR_METADATA"
LABELS = {"task": "linux-docker-sharing-trial", "trial": "ld01",
          "owner": "opencode-linux-trial-preparation"}
EXPECTED_LIST_FORMAT = (
    '{"name":{{json .Names}},"state":{{json .State}},'
    '"task":{{json (.Label "task")}},"trial":{{json (.Label "trial")}},'
    '"owner":{{json (.Label "owner")}}}'
)
EXPECTED_INSPECT_FORMAT = (
    '{{$seen := false}}{{$unique := true}}{{$home := false}}'
    '{{range .Config.Env}}{{if eq (index (split . "=") 0) "HOME"}}'
    '{{if $seen}}{{$unique = false}}{{end}}'
    '{{$seen = true}}{{$home = eq . "HOME=/home/session"}}{{end}}{{end}}'
    '{"name":{{json .Name}},"id":{{json .Id}},'
    '"task":{{json (index .Config.Labels "task")}},'
    '"trial":{{json (index .Config.Labels "trial")}},'
    '"owner":{{json (index .Config.Labels "owner")}},'
    '"state":{{json .State.Status}},"running":{{json .State.Running}},'
    '"paused":{{json .State.Paused}},"restarting":{{json .State.Restarting}},'
    '"dead":{{json .State.Dead}},"user":{{json .Config.User}},'
    '"workdir":{{json .Config.WorkingDir}},'
    '"privileged":{{json .HostConfig.Privileged}},'
    '"home_supported":{{and $seen $unique $home}}}'
)


def container(name=A, **overrides):
    record = dict(name="/" + name, id=ID, state="running", running=True,
                  paused=False, restarting=False, dead=False, user="1001:1001",
                  workdir="/project", home_supported=True, privileged=False, **LABELS)
    record.update(overrides)
    return record


def listed(name=A, state="running", **overrides):
    record = dict(name=name, state=state, **LABELS)
    record.update(overrides)
    return record


class CLITest(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.stdout, self.stderr = io.StringIO(), io.StringIO()
        stack.enter_context(redirect_stdout(self.stdout))
        stack.enter_context(redirect_stderr(self.stderr))
        self.stdin = Mock()
        self.stdin.isatty.return_value = True
        stack.enter_context(patch.object(cli.sys, "stdin", self.stdin))
        self.stdout_tty = stack.enter_context(patch.object(self.stdout, "isatty", return_value=True))
        # An unplanned subprocess path must fail before it can reach the host.
        stack.enter_context(patch.object(subprocess, "Popen", side_effect=AssertionError("unmocked Popen")))
        self.run = stack.enter_context(patch.object(subprocess, "run", side_effect=self.docker_reply))
        self.exec = stack.enter_context(patch.object(cli.os, "execvp", side_effect=AssertionError("unexpected exec")))
        self.replies = deque()

    def docker_reply(self, argv, **kwargs):
        self.assertEqual(kwargs, dict(stdin=subprocess.DEVNULL, capture_output=True,
                                      text=True, check=True, timeout=30))
        if argv[:3] == ["docker", "container", "ls"]:
            self.assertEqual(argv, [
                "docker", "container", "ls", "--all",
                "--filter", "name=tvm-share-ld01-",
                "--filter", "label=task=linux-docker-sharing-trial",
                "--filter", "label=trial=ld01",
                "--filter", "label=owner=opencode-linux-trial-preparation",
                "--format", EXPECTED_LIST_FORMAT,
            ])
        else:
            self.assertEqual(len(argv), 7)
            self.assertEqual(argv[:6], ["docker", "container", "inspect", "--format",
                                       EXPECTED_INSPECT_FORMAT, "--"])
            self.assertTrue(argv[6].startswith("tvm-share-ld01-"))
        self.assertTrue(self.replies, "unexpected Docker metadata request")
        reply = self.replies.popleft()
        if isinstance(reply, Exception):
            raise reply
        if not isinstance(reply, str):
            reply = "\n".join(json.dumps(record) for record in reply)
        return subprocess.CompletedProcess(argv, 0, reply, PRIVATE)

    def invoke(self, argv, reply=None):
        self.stdout.seek(0)
        self.stdout.truncate()
        self.stderr.seek(0)
        self.stderr.truncate()
        if reply is not None:
            self.replies.append(reply)
        result = cli.main(argv)
        self.assertFalse(self.replies, "expected Docker request did not run")
        return result

    def assert_failed(self, argv, reply=None):
        self.assertEqual(self.invoke(argv, reply), 1)
        self.assertEqual(self.stdout.getvalue(), "")
        self.assertTrue(self.stderr.getvalue().startswith(argv[0] + " failed: "))
        self.assertNotIn(PRIVATE, self.stderr.getvalue())
        self.exec.assert_not_called()

    def test_metadata_projection_boundaries(self):
        self.assertEqual(cli.LIST_FORMAT, EXPECTED_LIST_FORMAT)
        self.assertEqual(cli.INSPECT_FORMAT, EXPECTED_INSPECT_FORMAT)

    def test_projection_assertions_reject_disclosure_and_swapped_mappings(self):
        mutations = [
            ("LIST_FORMAT", EXPECTED_LIST_FORMAT + '{{json .}}'),
            ("INSPECT_FORMAT", EXPECTED_INSPECT_FORMAT + '{{json .}}'),
            ("LIST_FORMAT", EXPECTED_LIST_FORMAT.replace(
                '"name":{{json .Names}},"state":{{json .State}}',
                '"name":{{json .State}},"state":{{json .Names}}')),
            ("INSPECT_FORMAT", EXPECTED_INSPECT_FORMAT.replace(
                '"user":{{json .Config.User}},"workdir":{{json .Config.WorkingDir}}',
                '"user":{{json .Config.WorkingDir}},"workdir":{{json .Config.User}}')),
        ]
        for attribute, mutated in mutations:
            with self.subTest(attribute=attribute, mutated=mutated):
                self.assertNotEqual(mutated, getattr(cli, attribute))
                with patch.object(cli, attribute, mutated), self.assertRaises(AssertionError):
                    self.test_metadata_projection_boundaries()

    def test_home_projection_requires_one_exact_entry(self):
        self.assertTrue(cli.INSPECT_FORMAT.startswith(
            '{{$seen := false}}{{$unique := true}}{{$home := false}}'
            '{{range .Config.Env}}{{if eq (index (split . "=") 0) "HOME"}}'
            '{{if $seen}}{{$unique = false}}{{end}}'
            '{{$seen = true}}{{$home = eq . "HOME=/home/session"}}{{end}}{{end}}'
        ))
        self.assertIn('"home_supported":{{and $seen $unique $home}}', cli.INSPECT_FORMAT)

    def test_list_filters_sorts_and_preserves_stopped_state(self):
        records = [listed(B, "exited"), listed("unrelated"), listed(A),
                   listed("tvm-share-ld01-wrong", owner="wrong")]
        for key in LABELS:
            missing = listed("tvm-share-ld01-missing-" + key)
            del missing[key]
            records.append(missing)
        self.assertEqual(self.invoke(["list"], records), 0)
        self.assertEqual(self.stdout.getvalue(), f"NAME\tSTATE\n{A}\trunning\n{B}\texited\n")
        self.assertEqual(self.stderr.getvalue(), "")
        self.run.assert_called_once()
        self.exec.assert_not_called()

    def test_empty_list_succeeds(self):
        for records in ([], [listed("unrelated")]):
            with self.subTest(records=records):
                self.assertEqual(self.invoke(["list"], records), 0)
                self.assertEqual(self.stdout.getvalue(), "No eligible LD01 contexts found.\n")
        self.exec.assert_not_called()

    def test_status_separates_state_from_supported_identity(self):
        for state in ("running", "exited", "paused", "restarting", "dead", "created"):
            with self.subTest(state=state):
                self.assertEqual(self.invoke(["status", A], [container(state=state)]), 0)
                self.assertEqual(self.stdout.getvalue(),
                                 f"NAME\tSTATE\tIDENTITY_SUPPORTED\n{A}\t{state}\ttrue\n")
        self.exec.assert_not_called()

    def test_status_and_join_share_identity_definition(self):
        unsupported = [dict(user=user) for user in ("", "0", "root", "1001", "1001:0")]
        unsupported += [dict(privileged=True), dict(workdir="/"), dict(home_supported=False),
                        dict(home_supported=None), dict(privileged=None)]
        for overrides in unsupported:
            with self.subTest(overrides=overrides):
                record = container(**overrides)
                self.assertEqual(self.invoke(["status", A], [record]), 0)
                self.assertEqual(self.stdout.getvalue(),
                                 f"NAME\tSTATE\tIDENTITY_SUPPORTED\n{A}\trunning\tfalse\n")
                self.assert_failed(["join", A], [record])

    def test_unicode_line_separators_remain_inside_json_identity_strings(self):
        for field in ("user", "workdir"):
            for separator in ("\u0085", "\u2028", "\u2029"):
                with self.subTest(field=field, separator=repr(separator)):
                    reply = json.dumps(container(**{field: "unsupported" + separator}),
                                       ensure_ascii=False) + "\n"
                    self.assertIn(separator, reply)
                    self.assertEqual(self.invoke(["status", A], reply), 0)
                    self.assertEqual(self.stdout.getvalue(),
                                     f"NAME\tSTATE\tIDENTITY_SUPPORTED\n{A}\trunning\tfalse\n")
                    self.assertEqual(self.stderr.getvalue(), "")
                    self.assert_failed(["join", A], reply)
                    self.assertEqual(self.stderr.getvalue(),
                                     "join failed: unsupported daily identity configuration\n")

    def test_unknown_and_ineligible_names_never_exec(self):
        for command in ("status", "join"):
            for name in ("unrelated", ID, "a1", "--helpful"):
                with self.subTest(command=command, name=name):
                    # Use -- to make the flag-looking name a positional argument.
                    argv = [command, "--", name]
                    self.assert_failed(argv)
            replies = [[], [container(name=B)], [container(name=A + "-suffix")]]
            for key in LABELS:
                replies.append([container(**{key: "wrong"})])
                missing = container()
                del missing[key]
                replies.append([missing])
            for records in replies:
                with self.subTest(command=command, records=records):
                    self.assert_failed([command, A], records)

    def test_docker_and_malformed_metadata_fail_safely(self):
        failures = [FileNotFoundError(PRIVATE), PermissionError(PRIVATE),
                    subprocess.CalledProcessError(1, ["docker"], output=PRIVATE, stderr=PRIVATE),
                    subprocess.TimeoutExpired(["docker"], 30, output=PRIVATE, stderr=PRIVATE),
                    PRIVATE, "null", "[]", "42"]
        for argv in (["list"], ["status", A], ["join", A]):
            for failure in failures:
                with self.subTest(argv=argv, failure=failure):
                    self.assert_failed(argv, failure)

    def test_bad_id_state_or_ambiguous_inspection_fails_closed(self):
        replies = [[container(id=identifier)] for identifier in ("short", "f" * 63, "g" * 64, None)]
        replies += [[container(state=state)] for state in (PRIVATE, None, [])]
        replies += [[container(), container()]]
        for command in ("status", "join"):
            for reply in replies:
                with self.subTest(command=command, reply=reply):
                    self.assert_failed([command, A], reply)
        self.assert_failed(["list"], [listed(state=PRIVATE)])

    def test_join_rejects_inactive_or_inconsistent_runtime_flags(self):
        overrides = [dict(state=state) for state in cli.STATES - {"running"}]
        overrides += [dict(running=False), dict(running=None)]
        overrides += [{flag: True} for flag in ("paused", "restarting", "dead")]
        overrides += [{flag: None} for flag in ("paused", "restarting", "dead")]
        for fields in overrides:
            with self.subTest(fields=fields):
                self.assert_failed(["join", A], [container(**fields)])

    def test_join_requires_both_terminal_streams(self):
        for stdin, stdout in ((False, True), (True, False), (False, False)):
            with self.subTest(stdin=stdin, stdout=stdout):
                self.stdin.isatty.return_value = stdin
                self.stdout_tty.return_value = stdout
                self.assert_failed(["join", A], [container()])

    def test_join_refuses_missing_stdin_or_stdout(self):
        for stream in ("stdin", "stdout"):
            with self.subTest(stream=stream), patch.object(cli.sys, stream, None):
                self.run.reset_mock()
                self.assert_failed(["join", A], [container()])
                self.assertEqual(self.stderr.getvalue(),
                                 "join failed: interactive stdin and stdout TTY required\n")
                self.run.assert_called_once()

    def test_metadata_commands_do_not_require_terminal(self):
        self.stdin.isatty.return_value = self.stdout_tty.return_value = False
        self.assertEqual(self.invoke(["list"], [listed()]), 0)
        self.assertEqual(self.invoke(["status", A], [container()]), 0)
        self.exec.assert_not_called()

    def test_join_reinspects_and_replaces_process_by_current_full_id(self):
        self.assertEqual(self.invoke(["status", A], [container(id="b" * 64)]), 0)
        self.replies.append([container()])
        self.exec.side_effect = SystemExit(37)
        with self.assertRaises(SystemExit) as exited:
            cli.main(["join", A])
        self.assertEqual(exited.exception.code, 37)
        self.assertFalse(self.replies)
        self.exec.assert_called_once_with("docker", [
            "docker", "exec", "-it", "--user", "1001:1001", "--workdir", "/project",
            ID, "bash", "--noprofile", "--norc",
        ])
        self.assertEqual(self.run.call_count, 2)
        for call in self.run.call_args_list:
            self.assertEqual(call.args[0][-1], A)

    def test_post_replacement_status_and_diagnostics_pass_through_without_retry(self):
        for status in (0, 17, 125, 126, 127):
            with self.subTest(status=status):
                def replaced(*args):
                    print("Docker-owned diagnostic", file=cli.sys.stderr)
                    raise SystemExit(status)
                self.exec.reset_mock()
                self.run.reset_mock()
                self.exec.side_effect = replaced
                self.replies.append([container()])
                self.stderr.seek(0)
                self.stderr.truncate()
                with self.assertRaises(SystemExit) as exited:
                    cli.main(["join", A])
                self.assertEqual(exited.exception.code, status)
                self.assertEqual(self.stderr.getvalue(), "Docker-owned diagnostic\n")
                self.exec.assert_called_once()
                self.run.assert_called_once()

    def test_exec_os_error_is_pre_replacement_failure(self):
        self.exec.side_effect = FileNotFoundError(PRIVATE)
        self.assertEqual(self.invoke(["join", A], [container()]), 1)
        self.assertEqual(self.stderr.getvalue(), "join failed: could not execute Docker\n")
        self.exec.assert_called_once()
        self.run.assert_called_once()

    def test_argparse_usage_exit_two_and_help_zero_without_docker(self):
        for argv in ([], ["status"], ["join"], ["unknown"], ["list", A],
                     ["join", A, B], ["status", "--unknown"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as exited:
                cli.main(argv)
            self.assertEqual(exited.exception.code, 2)
        with self.assertRaises(SystemExit) as exited:
            cli.main(["--help"])
        self.assertEqual(exited.exception.code, 0)
        self.run.assert_not_called()
        self.exec.assert_not_called()


if __name__ == "__main__":
    unittest.main()
