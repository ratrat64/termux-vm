"""Regression checks are synthetic: no Docker/GCP mutation or fault injection."""

import copy
import contextlib
import datetime as dt
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

import fixtures
import trial


class AgentSandbox:
    """Actual agent functions; private files and synthetic netfilter transport."""
    def __init__(self, directory):
        self.base = Path(directory)
        self.root = self.base / "ld01-cvpn0123456789ab"
        self.root.mkdir()
        self.resolver = self.base / "resolver"
        self.original = b"# exact\r\nnameserver 127.0.0.11\nsearch prior.test\n"
        self.resolver.write_bytes(self.original)
        self.sysctl = self.base / "sysctl"
        (self.sysctl / "all").mkdir(parents=True)
        (self.sysctl / "all" / "disable_ipv6").write_text("0\n")
        self.tunnel = self.base / "tunnel"
        self.rules = {(tool, "filter"): {h: [] for h in ("INPUT", "OUTPUT", "FORWARD")}
                      for tool in ("iptables", "ip6tables")}
        self.rules["iptables", "nat"] = {"OUTPUT": [["-d", "127.0.0.11", "--dport", "53",
                                                     "-j", "DNAT", "--to-destination", "127.0.0.11:55444"]]}
        self.before = copy.deepcopy(self.rules)
        self.commands = []
        self.fail = lambda args: False
        self.now = dt.datetime.fromisoformat(trial.DEADLINE.replace('Z', '+00:00')).timestamp() - 3600
        self.ns = {"__name__": "sandbox"}
        with patch.object(sys, "argv", ["agent", str(self.root)]):
            exec(compile(trial.AGENT, "controlled-agent", "exec"), self.ns)
        self.ns["pathlib"] = types.SimpleNamespace(Path=self.path)
        self.ns["subprocess"] = types.SimpleNamespace(run=self.run, Popen=subprocess.Popen, PIPE=subprocess.PIPE)
        self.ns["time"] = types.SimpleNamespace(time=lambda: self.now, sleep=lambda n: time.sleep(min(n, .01)))
        original_atomic = self.ns["atomic"]
        def atomic(name, value):
            original_atomic(name, value)
            if name == "lease": os.utime(self.root / name, (self.now, self.now))
        self.ns["atomic"] = atomic
        self.generation = "generation-one"

    def path(self, *parts):
        value = Path(*parts)
        return {"/etc/resolv.conf": self.resolver, "/proc/sys/net/ipv6/conf": self.sysctl,
                "/sys/class/net/ld01tun": self.tunnel}.get(str(value), value)

    def run(self, args, **kwargs):
        args = list(args)
        self.commands.append(args)
        if self.fail(args):
            raise subprocess.TimeoutExpired(args, 2)
        if args[:4] == ["ip", "link", "delete", "dev"]:
            self.tunnel.unlink()
            return subprocess.CompletedProcess(args, 0, "", "")
        tool = args.pop(0)
        table = "filter"
        if args[0] == "-t":
            _, table = args[:2]
            args = args[2:]
        rules = self.rules[tool, table]
        action = args[0]
        name = args[1] if len(args) > 1 else None
        rule = args[3:] if action == "-I" else args[2:]
        code, output = 0, ""
        if action == "-S":
            if name is not None and name not in rules:
                code = 1
            else:
                output = json.dumps(rules if name is None else rules[name], sort_keys=True)
        elif action == "-N": rules[name] = []
        elif action == "-A": rules[name].append(rule)
        elif action == "-I": rules[name].insert(0, rule)
        elif action == "-C": code = 0 if rule in rules.get(name, []) else 1
        elif action == "-D":
            if rule in rules.get(name, []): rules[name].remove(rule)
            else: code = 1
        elif action == "-X":
            if rules[name]: raise AssertionError("nonempty task chain")
            del rules[name]
        else: raise AssertionError("unexpected command: " + repr(args))
        return subprocess.CompletedProcess(args, code, output, "")

    def prepare(self):
        return self.ns["prepare"](self.generation, "10.231.0.1")

    def block(self):
        self.ns["block"](self.generation)

    def restore(self):
        self.ns["restore"](self.generation)

    def dispatch(self, action):
        with patch.object(sys, "argv", ["agent", str(self.root), action, self.generation]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.ns["main"]()
        return output.getvalue()

    def watcher(self):
        errors = []
        generation = self.generation
        def watch():
            try: self.ns["watch"](generation)
            except Exception as error: errors.append(error)
        thread = threading.Thread(target=watch)
        original_identity = self.ns["identity"]
        self.ns["identity"] = lambda pid: ("thread" if thread.is_alive() else None) if pid == 2147483646 else original_identity(pid)
        (self.root / ("watch-pid-" + generation + ".json")).write_text(json.dumps({"pid": 2147483646, "identity": "thread"}))
        thread.start()
        return thread, errors


class RejectionTests(unittest.TestCase):
    def setUp(self):
        self.resources = {"image": "sha256:frozen", "resources": []}
        self.baseline = {"checks": {}}
        self.objects = []
        for name in (trial.A, trial.B):
            network = "tvm-share-ld01-net-" + name[-1]
            runtime = {"CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
                       "Memory": 536870912, "MemorySwap": 536870912, "NanoCpus": 1000000000,
                       "PidsLimit": 128, "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
                       "Privileged": False, "NetworkMode": network}
            mounts = [{"Destination": "/project", "Source": "/private/project", "RW": True},
                      {"Destination": "/home/session", "Name": "home-" + name[-1], "RW": True}]
            caps = ["CAP_NET_ADMIN"] if name == trial.A else None
            devices = [{"PathOnHost": "/dev/net/tun", "PathInContainer": "/dev/net/tun", "CgroupPermissions": "rw"}] if name == trial.A else []
            self.resources["resources"] += [{"name": name, "id": name + "-id"}, {"name": network, "id": network + "-id"}]
            self.baseline["checks"][name] = {"id": name + "-id", "mounts": mounts, "runtime_config": runtime,
                                           "cap_add": caps, "devices": devices}
            self.objects.append({"Name": "/" + name, "Id": name + "-id", "Image": "sha256:frozen",
                "State": {"Running": True, "Paused": False}, "Mounts": copy.deepcopy(mounts),
                "Config": {"User": "1001:1001", "Labels": trial.LABELS, "Cmd": ["sleep", "infinity"],
                           "Entrypoint": None, "WorkingDir": "/project", "Env": [
                               "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME=/home/session"]},
                "HostConfig": dict(runtime, CapAdd=caps, Devices=devices, Binds=None, PortBindings={},
                                   VolumesFrom=None, DeviceRequests=None, ExtraHosts=None),
                "NetworkSettings": {"Networks": {network: {"NetworkID": network + "-id"}}}})

    def reconcile(self):
        trial.reconcile(self.objects, self.resources, self.baseline, "sha256:frozen")

    def test_mount_order_is_not_drift(self):
        self.objects[0]["Mounts"].reverse()
        self.reconcile()

    def test_identity_capabilities_mounts_limits_and_ownership_reject_before_mutation(self):
        original = copy.deepcopy(self.objects)
        changes = [lambda o: o[0].update(Id="replacement"),
                   lambda o: o[1]["HostConfig"].update(CapAdd=["CAP_NET_ADMIN"]),
                   lambda o: o[0]["Mounts"][0].update(Source="/wrong"),
                   lambda o: o[0]["HostConfig"].update(Memory=1),
                   lambda o: o[0]["Config"].update(Labels={}),
                   lambda o: o[0]["Config"].update(User="0:0"),
                   lambda o: o[0].update(Image="changed")]
        for change in changes:
            with self.subTest(change=change), patch.object(trial, "run") as run:
                self.objects = copy.deepcopy(original)
                change(self.objects)
                with self.assertRaises(ValueError):
                    self.reconcile()
                run.assert_not_called()

    def test_expired_preflight_never_deploys_or_connects(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = trial.Trial(Path(directory))
            after = dt.datetime.fromisoformat(trial.DEADLINE.replace('Z', '+00:00')) + dt.timedelta(seconds=1)
            with patch.object(trial, "utc", return_value=after), patch.object(trial, "run") as run, \
                    patch.object(controller, "deploy") as deploy, patch.object(controller, "forward") as forward:
                self.assertEqual(controller.execute(), "FAIL")
                run.assert_not_called()
                deploy.assert_not_called()
                forward.assert_not_called()
            self.assertEqual(json.loads((Path(directory) / "evidence.json").read_text())["status"], "FAIL")

    def test_occupied_forward_port_rejects_without_external_command(self):
        with socket.socket() as occupied, patch.object(trial, "run") as run:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            with self.assertRaises(OSError):
                trial.check_ports([occupied.getsockname()])
            run.assert_not_called()


class RestorationTests(unittest.TestCase):
    def test_root_agent_restores_real_resolver_bytes_and_scoped_rules_after_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block(); sandbox.restore()
            self.assertEqual(sandbox.resolver.read_bytes(), sandbox.original)
            self.assertEqual(sandbox.rules, sandbox.before)
            self.assertEqual(json.loads((sandbox.root / "cleanup.json").read_text())["status"], "PASS")
            self.assertFalse((sandbox.root / "active").exists())

    def test_failed_restore_recovers_resolver_retains_journal_and_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block()
            sandbox.fail = lambda args: args[0] == "ip6tables"
            with self.assertRaises(RuntimeError): sandbox.restore()
            self.assertEqual(sandbox.resolver.read_bytes(), sandbox.original)
            self.assertTrue((sandbox.root / "restore.json").exists())
            self.assertTrue((sandbox.root / "active").exists())
            self.assertTrue(any(cmd[:2] == ["ip6tables", "-D"] for cmd in sandbox.commands))
            (sandbox.root / ("watch-done-" + sandbox.generation)).touch()
            with self.assertRaisesRegex(RuntimeError, "PASS required"): sandbox.dispatch("remove")
            with self.assertRaises(RuntimeError): sandbox.ns["start"](sandbox.generation)
            sandbox.fail = lambda args: False
            sandbox.restore()
            self.assertEqual(sandbox.rules, sandbox.before)
            self.assertEqual({json.loads(p.read_text())["status"] for p in sandbox.root.glob("cleanup-attempt-*")}, {"FAIL", "PASS"})

    def test_unresponsive_task_daemon_is_killed_and_tunnel_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block(); sandbox.tunnel.touch()
            ready = Path(directory) / "ready"
            children = []
            def spawn(*args, **kwargs):
                child = subprocess.Popen(*args, **kwargs)
                children.append(child)
                return child
            sandbox.ns["subprocess"].Popen = spawn
            command = [sys.executable, "-c", "import signal,time,sys; from pathlib import Path; "
                       "signal.signal(signal.SIGTERM,signal.SIG_IGN); Path(sys.argv[2]).touch(); time.sleep(60)",
                       str(sandbox.root / "client.ovpn"), str(ready)]
            try:
                sandbox.ns["start"](sandbox.generation, command)
                for _ in range(200):
                    if ready.exists(): break
                    time.sleep(.01)
                self.assertTrue(ready.exists())
                sandbox.restore()
                self.assertEqual(children[0].wait(timeout=3), -signal.SIGKILL)
                self.assertFalse(sandbox.tunnel.exists())
                self.assertIn(["ip", "link", "delete", "dev", "ld01tun"], sandbox.commands)
            finally:
                for child in children:
                    if child.poll() is None: child.kill()
                    child.wait(timeout=3)

    def test_failed_startup_always_restores_exact_saved_state(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = trial.Trial(Path(directory))
            controller.state.update(server="10.231.0.1", subnet="10.231.0.0/24")
            controller.shells = [Mock(), Mock()]
            old = {"resolver": "exact prior bytes", "-4route": [{"dst": "default"}], "-6route": [], "rules": "prior"}
            calls = []
            restored = False
            def agent(state, action, *args):
                nonlocal restored
                calls.append(action)
                if action == "prepare":
                    return json.dumps(old)
                if action == "block":
                    raise RuntimeError("synthetic failed startup after resolver/IPv6 mutation")
                if action == "status":
                    return json.dumps({"active": True, "watcher_ready": True})
                if action == "restore":
                    restored = True
            with patch.object(trial, "reserve"), patch.object(trial, "snapshot", return_value=old), \
                    patch.object(trial, "agent", side_effect=agent), patch.object(trial, "inside"), patch.object(trial, "run"), \
                    patch.object(trial, "Lease", return_value=Mock(error=None)):
                with self.assertRaisesRegex(RuntimeError, "synthetic failed startup"):
                    controller.cycle(0)
            self.assertTrue(restored)
            self.assertEqual(calls, ["prepare", "launch_watch", "status", "block", "status", "restore", "join"])
            self.assertFalse(controller.state["prepared"])
            self.assertEqual(controller.evidence["cycles"][0]["a_before"], old)

    def test_cleanup_failure_blocks_pass_and_other_cleanup_still_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {"private": directory, "prepared": True, "a_id": "retained", "deployed": True,
                     "task": "cvpn0123456789ab", "upload": "/private/source", "subnet": "10.231.0.0/24",
                     "a_bridge": "172.16.0.33", "receipt": "receipt", "forwards": []}
            with patch.object(trial, "run", return_value='[{"Id":"retained"}]'), \
                    patch.object(trial, "agent", side_effect=RuntimeError("restore failed")), \
                    patch.object(trial, "remote") as remote:
                errors = trial.cleanup(state)
            self.assertTrue(any("restore failed" in e for e in errors))
            remote.assert_called_once()
            self.assertFalse((Path(directory) / "cleaned.json").exists())
            self.assertEqual(json.loads(next(Path(directory).glob("cleanup-attempt-*")).read_text())["status"], "FAIL")

    def test_controller_failed_cleanup_retains_material_then_succeeds_and_caches_only_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {"private": directory, "prepared": True, "a_material": True, "a_id": "retained",
                     "container_root": "/run/task", "forwards": []}
            calls = []
            failed = True
            (Path(directory) / "cleaned.json").write_text('{"status":"FAIL","errors":["old failure"]}')
            def agent(state, action, *args):
                calls.append(action)
                if action == "restore" and failed: raise RuntimeError("retryable restore failure")
                return '{}'
            with patch.object(trial, "run", return_value='[{"Id":"retained"}]'), \
                    patch.object(trial, "inside", return_value='{"status":"PASS"}'), \
                    patch.object(trial, "agent", side_effect=agent):
                self.assertTrue(trial.cleanup(state))
                self.assertNotIn("remove", calls)
                self.assertTrue(state["a_material"])
                failed = False
                self.assertEqual(trial.cleanup(state), [])
                self.assertIn("remove", calls)
                count = len(calls)
                self.assertEqual(trial.cleanup(state), [])
                self.assertEqual(len(calls), count)
            self.assertEqual(len(list(Path(directory).glob("cleanup-attempt-*"))), 2)
            self.assertEqual(len(list(Path(directory).glob("cleanup-previous-*"))), 1)
            self.assertEqual(json.loads((Path(directory) / "cleaned.json").read_text())["status"], "PASS")


class WatchdogTests(unittest.TestCase):
    def test_healthy_agent_watcher_preserves_state_and_is_explicitly_joined(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block()
            thread, errors = sandbox.watcher()
            try:
                for _ in range(100):
                    if (sandbox.root / ("watch-ready-" + sandbox.generation)).exists(): break
                    time.sleep(.01)
                for _ in range(3):
                    sandbox.now += 19
                    sandbox.ns["renew"](sandbox.generation)
                    time.sleep(.02)
                self.assertTrue((sandbox.root / "active").exists())
                self.assertFalse((sandbox.root / "cleanup.json").exists())
                sandbox.restore()
                sandbox.ns["join_watchers"]()
            finally:
                (sandbox.root / "cancelled").write_text(sandbox.generation)
                thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

    def test_agent_watchdog_stale_lease_dead_daemon_and_deadline_restore(self):
        for trigger in ("lease", "daemon", "deadline"):
            with self.subTest(trigger=trigger), tempfile.TemporaryDirectory() as directory:
                sandbox = AgentSandbox(directory)
                sandbox.prepare(); sandbox.block(); sandbox.tunnel.touch()
                if trigger == "lease": sandbox.now += 21
                elif trigger == "daemon":
                    (sandbox.root / "vpn.pid").write_text(json.dumps({"pid": 2147483647, "identity": "dead"}))
                else: sandbox.now = dt.datetime.fromisoformat(trial.DEADLINE.replace('Z', '+00:00')).timestamp()
                sandbox.ns["watch"](sandbox.generation)
                sandbox.ns["join_watchers"]()
                self.assertEqual(sandbox.resolver.read_bytes(), sandbox.original)
                self.assertEqual(sandbox.rules, sandbox.before)
                self.assertFalse(sandbox.tunnel.exists())
                self.assertFalse((sandbox.root / "active").exists())

    def test_old_generation_watcher_cannot_restore_next_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.restore()
            old = sandbox.generation
            sandbox.generation = "generation-two"
            sandbox.prepare(); sandbox.block()
            sandbox.ns["watch"](old)
            self.assertEqual((sandbox.root / "active").read_text(), sandbox.generation)
            self.assertNotEqual(sandbox.resolver.read_bytes(), sandbox.original)
            sandbox.restore()

    def test_mutation_and_restore_share_lock_and_cancelled_start_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare()
            entered, release = threading.Event(), threading.Event()
            original_cmd = sandbox.ns["cmd"]
            def cmd(*args, **kwargs):
                if args[:2] == ("ip6tables", "-N"):
                    entered.set()
                    if not release.wait(2): raise RuntimeError("test handshake timeout")
                return original_cmd(*args, **kwargs)
            sandbox.ns["cmd"] = cmd
            mutation = threading.Thread(target=sandbox.block)
            restoration = threading.Thread(target=sandbox.restore)
            mutation.start()
            self.assertTrue(entered.wait(1))
            restoration.start()
            self.assertFalse((sandbox.root / "cleanup.json").exists())
            release.set()
            mutation.join(2); restoration.join(2)
            self.assertFalse(mutation.is_alive() or restoration.is_alive())
            self.assertEqual(sandbox.rules, sandbox.before)
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                sandbox.ns["start"](sandbox.generation)

    def test_expired_agent_generation_cannot_mutate_or_start(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare()
            sandbox.now = dt.datetime.fromisoformat(trial.DEADLINE.replace('Z', '+00:00')).timestamp()
            with self.assertRaisesRegex(RuntimeError, "reserve"): sandbox.block()
            with self.assertRaisesRegex(RuntimeError, "reserve"): sandbox.ns["start"](sandbox.generation)
            self.assertEqual(sandbox.rules, sandbox.before)

    def test_never_launched_watcher_can_be_retired_and_late_launch_is_cancelled(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.restore()
            sandbox.ns["join_watchers"]()
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                sandbox.ns["launch_watch"](sandbox.generation)

    def test_lease_renews_independently_until_stopped(self):
        renewed = threading.Event()
        with patch.object(trial, "agent", side_effect=lambda *_: renewed.set()) as agent:
            lease = trial.Lease({}, "generation")
            try:
                self.assertTrue(renewed.wait(1))
                renewed.clear()
                self.assertTrue(renewed.wait(3))  # Controller is busy; renewal continues.
            finally: lease.stop()
            count = agent.call_count
            self.assertFalse(lease.thread.is_alive())
            self.assertGreaterEqual(count, 2)

    def test_controller_watcher_healthy_then_loss_and_deadline_cleanup(self):
        for trigger in ("loss", "deadline"):
            with self.subTest(trigger=trigger), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "state.json"
                state = {"private": directory, "controller_pid": 42, "controller_identity": "original", "forwards": []}
                path.write_text(json.dumps(state))
                def healthy_sleep(_):
                    self.assertFalse((Path(directory) / "cleaned.json").exists())
                identities = ["original", None] if trigger == "loss" else ["original", "original"]
                deadlines = [600, 600] if trigger == "loss" else [600, -1]
                with patch.object(trial, "process_identity", side_effect=identities), \
                        patch.object(trial, "remaining", side_effect=deadlines), \
                        patch.object(trial, "time", types.SimpleNamespace(sleep=healthy_sleep)):
                    trial.watch(path)
                self.assertEqual(json.loads((Path(directory) / "cleaned.json").read_text())["status"], "PASS")

    def test_zombie_controller_is_dead_even_when_proc_entry_remains(self):
        text = "42 (python worker) " + " ".join(["Z"] + ["0"] * 18 + ["12345"])
        with patch.object(trial, "Path") as path:
            path.return_value.read_text.return_value = text
            self.assertIsNone(trial.process_identity(42))

    def test_controller_loss_restores_agent_state_and_stops_registered_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block(); sandbox.tunnel.touch()
            thread, errors = sandbox.watcher()
            forward = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "disposable-task-forward"],
                                       start_new_session=True)
            identity = trial.process_identity(forward.pid)
            state = {"private": directory, "a_id": "retained", "container_root": str(sandbox.root),
                     "prepared": True, "controller_pid": 42, "controller_identity": "dead-controller",
                     "forwards": [{"pid": forward.pid, "identity": identity, "specifications": ["127.0.0.1:20991:127.0.0.1:19090"]}]}
            path = Path(directory) / "state.json"
            path.write_text(json.dumps(state))
            original_identity = trial.process_identity
            def agent(state, action, *args):
                if action == "restore": sandbox.restore()
                elif action == "join": sandbox.ns["join_watchers"]()
                else: self.fail("unexpected action: " + action)
            def run(*args, **kwargs):
                if args[:2] == ("docker", "inspect"): return '[{"Id":"retained"}]'
                if args[:2] == ("ss", "-H"): return ''
                self.fail("unexpected external command")
            try:
                with patch.object(trial, "process_identity", side_effect=lambda pid: None if pid == 42 else original_identity(pid)), \
                        patch.object(trial, "run", side_effect=run), patch.object(trial, "agent", side_effect=agent), \
                        patch.object(trial, "inside", side_effect=lambda *_args, **_kwargs: (sandbox.root / "cleanup.json").read_text()):
                    trial.watch(path)
                self.assertEqual(forward.wait(timeout=3), -signal.SIGTERM)
                self.assertEqual(sandbox.resolver.read_bytes(), sandbox.original)
                self.assertEqual(sandbox.rules, sandbox.before)
                self.assertFalse(sandbox.tunnel.exists())
                self.assertEqual(json.loads((Path(directory) / "cleaned.json").read_text())["status"], "PASS")
            finally:
                if forward.poll() is None: forward.kill()
                forward.wait(timeout=3)
                (sandbox.root / "cancelled").write_text(sandbox.generation)
                thread.join(2)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])


class ForwardGateTests(unittest.TestCase):
    def test_agent_child_does_not_keep_controller_capture_pipes_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            program = ("import sys; ns={'__name__':'sandbox'}; sys.argv=['agent',sys.argv[1]]; "
                       "exec(" + repr(trial.AGENT) + ",ns); "
                       "ns['spawn']([sys.executable,'-c','import time; time.sleep(60)',"
                       "str(ns['root']/'client.ovpn')],'vpn.pid'); print('registered')")
            try:
                result = subprocess.run([sys.executable, "-c", program, directory], capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "registered")
            finally:
                if (root / "vpn.pid").exists():
                    record = json.loads((root / "vpn.pid").read_text())
                    if trial.process_identity(record["pid"]) == record["identity"]:
                        os.kill(record["pid"], signal.SIGKILL)

    def test_eof_cancels_gate_without_exec(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed"
            process = subprocess.Popen([sys.executable, "-c", trial.GATE, sys.executable, "-c",
                                        "from pathlib import Path; import sys; Path(sys.argv[1]).touch()", str(marker)],
                                       stdin=subprocess.PIPE)
            process.stdin.close()
            self.assertEqual(process.wait(timeout=3), 1)
            self.assertFalse(marker.exists())

    def test_forward_exec_waits_for_durable_registration_and_failed_save_cancels(self):
        for fail_save in (False, True):
            with self.subTest(fail_save=fail_save), tempfile.TemporaryDirectory() as directory:
                private = Path(directory)
                marker = private / "executed"
                children = []
                actual_spawn = subprocess.Popen
                def spawn(command, **kwargs):
                    code = "import json,os,sys,time; from pathlib import Path; " \
                           "s=json.loads(Path(sys.argv[1]).read_text()); " \
                           "assert s['forwards'][-1]['pid']==os.getpid(); Path(sys.argv[2]).touch(); time.sleep(60)"
                    child = actual_spawn([*command[:3], sys.executable, "-c", code,
                                          str(private / "state.json"), str(marker)], **kwargs)
                    children.append(child)
                    return child
                controller = trial.Trial(private)
                try:
                    with patch.object(trial, "reserve"), patch.object(trial.subprocess, "Popen", side_effect=spawn), \
                            patch.object(trial, "run", return_value="127.0.0.1:20991 "):
                        if fail_save:
                            with patch.object(trial, "save", side_effect=OSError("disk unavailable")):
                                with self.assertRaises(OSError): controller.forward("test", ["127.0.0.1:20991:127.0.0.1:19090"])
                            self.assertEqual(children[0].wait(timeout=3), 1)
                            self.assertFalse(marker.exists())
                        else:
                            controller.forward("test", ["127.0.0.1:20991:127.0.0.1:19090"])
                            for _ in range(100):
                                if marker.exists(): break
                                time.sleep(.01)
                            self.assertTrue(marker.exists())
                finally:
                    for child in children:
                        if child.poll() is None: child.kill()
                        child.wait(timeout=3)


class ContinuityTests(unittest.TestCase):
    def test_held_socket_rejects_changed_later_sequence_or_connection(self):
        for changed in ("seq", "connection"):
            with self.subTest(changed=changed):
                class CorruptLater(fixtures.socketserver.StreamRequestHandler):
                    def handle(self):
                        for seq in (1, 2):
                            if not self.rfile.readline(): return
                            reply = {"seq": seq, "connection": "one"}
                            if seq == 2: reply[changed] = 99 if changed == "seq" else "different"
                            self.wfile.write((json.dumps(reply) + "\n").encode())
                            self.wfile.flush()
                with fixtures.socketserver.ThreadingTCPServer(("127.0.0.1", 0), CorruptLater) as server:
                    thread = threading.Thread(target=server.serve_forever)
                    thread.start()
                    process = subprocess.Popen([sys.executable, str(Path(fixtures.__file__)), "hold", "--port",
                                                str(server.server_address[1])], stdin=subprocess.PIPE,
                                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        self.assertNotEqual(process.wait(timeout=4), 0)
                        output, error = process.communicate(timeout=2)
                        self.assertEqual(len(output.splitlines()), 1)
                        self.assertIn("identity/sequence changed", error)
                        self.assertNotIn('"finished"', output)
                    finally:
                        if process.poll() is None: process.kill()
                        process.communicate(timeout=2)
                        server.shutdown(); thread.join()

    def test_real_fixture_preserves_one_socket_and_sequence(self):
        with fixtures.socketserver.ThreadingTCPServer(("127.0.0.1", 0), fixtures.Heartbeat) as server:
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                result = subprocess.run([sys.executable, str(Path(fixtures.__file__)), "hold", "--port", str(server.server_address[1])],
                                        input="stop\n", text=True, capture_output=True, timeout=5, check=True)
                first, final = [json.loads(x) for x in result.stdout.splitlines()]
                self.assertEqual(first["connection"], final["connection"])
                self.assertEqual(first["socket"], final["socket"])
                self.assertEqual(final["reconnects"], 0)
            finally:
                server.shutdown()
                thread.join()

    def test_continuity_verdict_rejects_sequence_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "held.jsonl"
            rows = [{"kind": "ack", "seq": x, "connection": "one", "socket": {}} for x in (1, 2, 4, 5)]
            rows.append({"kind": "finished", "errors": 0, "reconnects": 0, "connection": "one", "socket": {}})
            path.write_text('\n'.join(json.dumps(x) for x in rows))
            controller = trial.Trial(Path(directory))
            process = Mock(returncode=0)
            controller.holds = [(process, path)]
            with self.assertRaisesRegex(ValueError, "acknowledgement gap"):
                controller.finish_holds()


class DNSTests(unittest.TestCase):
    def test_rules_match_original_dns_tuple_and_nat_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block()
            rules = sandbox.rules["iptables", "filter"][sandbox.ns["chain"]]
            self.assertEqual(len(rules), 2)
            for rule in rules:
                self.assertIn("--ctorigdstport", rule)
                self.assertEqual(rule[rule.index("--ctorigdstport") + 1], "53")
                self.assertEqual(rule[rule.index("--ctorigdst") - 1], "!")
                self.assertEqual(rule[rule.index("--ctorigdst") + 1], "10.231.0.1")
                self.assertNotIn("--dport", rule)  # Docker's translated port is not the match key.
            self.assertEqual(sandbox.rules["iptables", "nat"], sandbox.before["iptables", "nat"])
            sandbox.restore()
            self.assertEqual(sandbox.rules, sandbox.before)

    def test_negative_probes_include_tcp_and_udp_for_host_b_and_embedded_dns(self):
        def execute(*args):
            code, host = args[-2:]
            with patch.object(socket, "socket") as udp, \
                    patch.object(socket, "create_connection", side_effect=OSError("blocked")) as tcp, \
                    patch.object(sys, "argv", ["probe", host]), contextlib.redirect_stdout(io.StringIO()) as output:
                udp.return_value.__enter__.return_value.recv.side_effect = TimeoutError("blocked")
                exec(compile(code, "dns-probe", "exec"), {})
                tcp.assert_called_once_with((host, 53), timeout=2)
                return output.getvalue()
        with patch.object(trial, "run", side_effect=execute), patch.object(trial, "inside", side_effect=execute):
            for host, container in (("10.231.0.1", None), ("10.231.0.1", trial.B), ("127.0.0.11", trial.A)):
                self.assertEqual(trial.dns_negative(host, container), {"udp_dns_unreachable": True, "tcp_dns_unreachable": True})


class ServerLifecycleTests(unittest.TestCase):
    def sandbox(self, directory):
        base = Path(directory)
        upload, binaries, units = base / "upload", base / "bin", base / "units"
        for path in (upload, binaries, units, base / "var"): path.mkdir()
        (upload / "fixtures.py").write_text("# source-only sandbox\n")
        deadline = int(dt.datetime.fromisoformat(trial.DEADLINE.replace('Z', '+00:00')).timestamp())
        (base / "now").write_text(str(deadline - 3600))
        source = (trial.HERE / "setup-server.sh").read_text()
        # Keep actual lifecycle/timeout/reserve logic; substitute only paths and
        # the provisioning preflight so no native package/network action runs.
        first, remainder = source.split('# All collision/deadline checks', 1)
        _, last = remainder.split('\nPY\n', 1)
        source = (first + '# sandbox provisioning preflight\n' + last).replace(
            'root=/var/lib/ld01-cvpn-$task', 'root=' + str(base / 'var/ld01-cvpn-$task')).replace(
            '/etc/systemd/system', str(units))
        script = upload / "setup-server.sh"
        script.write_text(source)
        def binary(name, body):
            path = binaries / name
            path.write_text(body)
            path.chmod(0o700)
        binary("date", '#!/bin/bash\nif [[ "$*" == *"-d"* ]]; then exec /usr/bin/date "$@"; else cat "$SANDBOX/now"; fi\n')
        binary("apt-get", '#!/usr/bin/python3\nimport os,time\nfrom pathlib import Path\np=Path(os.environ["SANDBOX"]); (p/"apt-entered").touch()\nwhile not (p/"apt-release").exists(): time.sleep(.02)\n')
        binary("systemctl", '#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\np=Path(os.environ["SANDBOX"])/"systemctl.log"\nwith p.open("a") as f: f.write(" ".join(sys.argv[1:])+"\\n")\nsys.exit(3 if sys.argv[1]=="is-active" else 0)\n')
        binary("dpkg-query", '#!/bin/bash\nexit 0\n')
        binary("openssl", '#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\nfor i,a in enumerate(sys.argv):\n if a in ("-out","-keyout"): Path(sys.argv[i+1]).write_text("sandbox\\n")\n')
        binary("openvpn", '#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\nPath(sys.argv[-1]).write_text("sandbox\\n")\n')
        binary("ip", '#!/bin/bash\nprintf "inet 10.231.0.1/24\\n"\n')
        command = ["bash", str(script), "cvpn0123456789ab", "10.231.0.0/24", trial.DEADLINE,
                   "172.16.0.33", "20990", "0" * 32]
        environment = dict(os.environ, PATH=str(binaries) + ":" + os.environ["PATH"], SANDBOX=str(base))
        return base, command, environment, deadline

    def wait_for(self, path, process):
        for _ in range(200):
            if path.exists(): return
            if process.poll() is not None: break
            time.sleep(.01)
        self.fail("sandbox setup did not reach handshake")

    def test_rollback_cancels_waits_for_setup_and_prevents_late_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, _ = self.sandbox(directory)
            setup = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rollback = None
            try:
                self.wait_for(base / "apt-entered", setup)
                rollback = subprocess.Popen([*command, "rollback"], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.wait_for(base / "upload/cancelled", rollback)
                self.assertIsNone(rollback.poll())
                (base / "apt-release").touch()
                self.assertNotEqual(setup.wait(timeout=5), 0)
                self.assertEqual(rollback.wait(timeout=5), 0)
                self.assertNotIn("start ", (base / "systemctl.log").read_text())
                late = subprocess.run(command, env=environment, capture_output=True, timeout=3)
                self.assertNotEqual(late.returncode, 0)
                self.assertFalse(list((base / "units").iterdir()))
            finally:
                (base / "apt-release").touch()
                for process in (setup, rollback):
                    if process is not None:
                        if process.poll() is None: process.kill()
                        process.wait(timeout=3)

    def test_setup_rechecks_reserve_after_packages_before_units(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, deadline = self.sandbox(directory)
            setup = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                self.wait_for(base / "apt-entered", setup)
                (base / "now").write_text(str(deadline - 100))
                (base / "apt-release").touch()
                self.assertNotEqual(setup.wait(timeout=5), 0)
                self.assertFalse(list((base / "units").iterdir()))
                self.assertNotIn("start ", (base / "systemctl.log").read_text())
            finally:
                if setup.poll() is None: setup.kill()
                setup.wait(timeout=3)

    def test_server_side_timeout_bounds_entire_setup_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, deadline = self.sandbox(directory)
            (base / "now").write_text(str(deadline - 181))
            started = time.monotonic()
            result = subprocess.run(command, env=environment, capture_output=True, timeout=8)
            self.assertEqual(result.returncode, 124)
            self.assertLess(time.monotonic() - started, 7)
            rollback = subprocess.run([*command, "rollback"], env=environment, capture_output=True, timeout=3)
            self.assertEqual(rollback.returncode, 0)


if __name__ == "__main__":
    unittest.main()
