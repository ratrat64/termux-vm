"""Regression checks are synthetic: no Docker/GCP mutation or fault injection."""

import copy
import contextlib
import datetime as dt
import fcntl
import io
import ipaddress
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


START = trial.utc().replace(microsecond=0)
DEADLINE = (START + dt.timedelta(minutes=45)).strftime('%Y-%m-%dT%H:%M:%SZ')


def approval():
    return dict(start=START.strftime('%Y-%m-%dT%H:%M:%SZ'), deadline=DEADLINE,
                injection=True, observation=True, exclusive_reuse=True, supervised_off=True,
                cases=['F1', 'F2'], targets=[trial.A, 'free-vm', 'A-veth', 'example.com'])


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
        self.now = START.timestamp() + 1
        (self.root / "authorization.json").write_text(json.dumps(approval()))
        self.ns = {"__name__": "sandbox"}
        with patch.object(sys, "argv", ["agent", str(self.root)]):
            exec(compile(trial.AGENT, "controlled-agent", "exec"), self.ns)
        self.ns["pathlib"] = types.SimpleNamespace(Path=self.path)
        self.ns["subprocess"] = types.SimpleNamespace(run=self.run, Popen=subprocess.Popen, PIPE=subprocess.PIPE)
        self.ns["time"] = types.SimpleNamespace(time=lambda: self.now, monotonic=time.monotonic,
                                               sleep=lambda n: time.sleep(min(n, .01)))
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
        if args[0] == 'ip':
            return subprocess.CompletedProcess(args, 0, '[]', '')
        if args[0] == 'ps':
            return subprocess.CompletedProcess(args, 0, 'PID PPID STAT COMMAND\n1 0 S fixture\n', '')
        if args[1] == '-nvx':
            return subprocess.CompletedProcess(args, 0, '\n'.join('2 200 REJECT all' for _ in range(5)), '')
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

    def permits(self, destination, interface, protocol='tcp', original=None, port=8080, established=False):
        """Evaluate the emitted OUTPUT rules against fresh and pre-existing tuples."""
        packet = {'-d': destination, '-o': interface, '-p': protocol, '--ctdir': 'ORIGINAL',
                  '--ctorigdst': original or destination, '--ctorigdstport': str(port),
                  '--ctstate': 'ESTABLISHED' if established else 'NEW'}
        chains = self.rules['iptables', 'filter']
        def visit(chain):
            for rule in chains[chain]:
                i, matches, negate = 0, True, False
                while i < len(rule):
                    key = rule[i]
                    if key == '!': negate = True; i += 1; continue
                    value = rule[i+1]; i += 2
                    if key == '-m': continue
                    if key == '-j':
                        if not matches: break
                        return value if value in ('REJECT', 'DROP', 'ACCEPT') else visit(value)
                    test = (ipaddress.ip_address(packet[key]) in ipaddress.ip_network(value, strict=False)
                            if key == '-d' else packet[key] == value)
                    matches = matches and (not test if negate else test)
                    negate = False
            return 'ACCEPT'
        return visit('OUTPUT') == 'ACCEPT'


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
            controller.state.update(authorization=approval(), deadline=DEADLINE)
            after = dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')) + dt.timedelta(seconds=1)
            with patch.object(trial, 'DEADLINE', DEADLINE), patch.object(trial, "utc", return_value=after), patch.object(trial, "run") as run, \
                    patch.object(controller, "deploy") as deploy, patch.object(controller, "forward") as forward:
                self.assertEqual(controller.execute(), "FAIL")
                run.assert_not_called()
                deploy.assert_not_called()
                forward.assert_not_called()
            self.assertEqual(json.loads((Path(directory) / "evidence.json").read_text())["status"], "FAIL")
            self.assertIn('approval expired', json.loads((Path(directory) / 'evidence.json').read_text())['error']['message'])

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

    def test_failed_startup_latches_without_implicit_restoration(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = trial.Trial(Path(directory))
            controller.state.update(server="10.231.0.1", subnet="10.231.0.0/24")
            controller.shells = [Mock(), Mock()]
            old = {"resolver": "exact prior bytes", "-4route": [{"dst": "default"}], "-6route": [], "rules": "prior"}
            calls = []
            def agent(state, action, *args):
                calls.append(action)
                if action == "prepare":
                    raise RuntimeError("synthetic failed startup after resolver/IPv6 mutation")
                if action == "status":
                    return json.dumps({"active": True, "watcher_ready": True, "intent": {"phase": "starting"}})
            with patch.object(trial, "reserve"), patch.object(trial, "snapshot", return_value=old), \
                    patch.object(trial, "agent", side_effect=agent), patch.object(trial, "inside"), patch.object(trial, "run"), \
                    patch.object(trial, "Lease", return_value=Mock(error=None)):
                with self.assertRaisesRegex(RuntimeError, "synthetic failed startup"):
                    controller.connect({})
            self.assertEqual(calls, ["prepare", "fault"])
            self.assertTrue(controller.state["prepared"])

    def test_cleanup_failure_blocks_pass_and_other_cleanup_still_runs(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {"private": directory, "prepared": True, "a_id": "retained", "deployed": True,
                     "task": "cvpn0123456789ab", "upload": "/private/source", "subnet": "10.231.0.0/24",
                      "a_bridge": "172.16.0.33", "receipt": "receipt", "forwards": []}
            state.update(authorization=approval(), deadline=DEADLINE)
            with patch.object(trial, "run", return_value='[{"Id":"retained"}]'), \
                    patch.object(trial, "agent", side_effect=RuntimeError("restore failed")), \
                    patch.object(trial, "remote") as remote:
                errors = trial.cleanup(state, explicit_off="test abort")
            self.assertTrue(any("restore failed" in e for e in errors))
            remote.assert_called_once()
            self.assertFalse((Path(directory) / "cleaned.json").exists())
            self.assertEqual(json.loads(next(Path(directory).glob("cleanup-attempt-*")).read_text())["status"], "FAIL")

    def test_controller_failed_cleanup_retains_material_then_succeeds_and_caches_only_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            state = {"private": directory, "prepared": True, "a_material": True, "a_id": "retained",
                      "container_root": "/run/task", "forwards": []}
            state.update(authorization=approval(), deadline=DEADLINE)
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
                self.assertTrue(trial.cleanup(state, explicit_off="test abort"))
                self.assertNotIn("remove", calls)
                self.assertTrue(state["a_material"])
                failed = False
                self.assertEqual(trial.cleanup(state, explicit_off="test retry"), [])
                self.assertIn("remove", calls)
                count = len(calls)
                self.assertEqual(trial.cleanup(state, explicit_off="test retry"), [])
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

    def test_agent_watchdog_stale_lease_dead_daemon_and_deadline_latch(self):
        for trigger in ("lease", "daemon", "deadline"):
            with self.subTest(trigger=trigger), tempfile.TemporaryDirectory() as directory:
                sandbox = AgentSandbox(directory)
                sandbox.prepare(); sandbox.block(); sandbox.tunnel.touch()
                if trigger == "lease": sandbox.now += 21
                elif trigger == "daemon":
                    (sandbox.root / "vpn.pid").write_text(json.dumps({"pid": 2147483647, "identity": "dead"}))
                else: sandbox.now = dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')).timestamp()
                sandbox.ns["watch"](sandbox.generation)
                sandbox.ns["join_watchers"]()
                self.assertNotEqual(sandbox.resolver.read_bytes(), sandbox.original)
                self.assertNotEqual(sandbox.rules, sandbox.before)
                self.assertTrue((sandbox.root / "active").exists())
                self.assertEqual(sandbox.ns['phase']()['phase'], 'faulted')
                with self.assertRaises(RuntimeError): sandbox.ns['renew'](sandbox.generation)
                with self.assertRaises(RuntimeError): sandbox.ns['start'](sandbox.generation)
                sandbox.restore()
                self.assertEqual(sandbox.rules, sandbox.before)
                self.assertEqual(sandbox.resolver.read_bytes(), sandbox.original)

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
            entered, release = threading.Event(), threading.Event()
            original_cmd = sandbox.ns["cmd"]
            def cmd(*args, **kwargs):
                if args[:2] == ("ip6tables", "-N"):
                    entered.set()
                    if not release.wait(2): raise RuntimeError("test handshake timeout")
                return original_cmd(*args, **kwargs)
            sandbox.ns["cmd"] = cmd
            mutation = threading.Thread(target=sandbox.prepare)
            restoration = threading.Thread(target=sandbox.restore)
            mutation.start()
            self.assertTrue(entered.wait(1))
            self.assertNotEqual(sandbox.ns['phase']().get('phase'), 'starting')
            self.assertEqual(sandbox.resolver.read_bytes(), sandbox.original)
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
            protected = copy.deepcopy(sandbox.rules)
            sandbox.now = dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')).timestamp()
            with self.assertRaisesRegex(RuntimeError, "reserve"): sandbox.block()
            with self.assertRaisesRegex(RuntimeError, "reserve"): sandbox.ns["start"](sandbox.generation)
            self.assertEqual(sandbox.rules, protected)

    def test_never_launched_watcher_can_be_retired_and_late_launch_is_cancelled(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.restore()
            sandbox.ns["join_watchers"]()
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                sandbox.ns["launch_watch"](sandbox.generation)

    def test_lease_renews_independently_until_stopped(self):
        renewed = threading.Event()
        with patch.object(trial, "agent", side_effect=lambda *_: (renewed.set() or '{"accepted":true}')) as agent:
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
                state.update(authorization=approval(), deadline=DEADLINE)
                path.write_text(json.dumps(state))
                def healthy_sleep(_):
                    self.assertFalse((Path(directory) / "cleaned.json").exists())
                identities = ["original", None] if trigger == "loss" else ["original", "original"]
                deadlines = iter([1200, 1200] if trigger == "loss" else [1200, 600])
                with patch.object(trial, "process_identity", side_effect=identities), \
                        patch.object(trial, "remaining", side_effect=lambda **_: next(deadlines, 1200 if trigger == "loss" else 600)), \
                        patch.object(trial, "time", types.SimpleNamespace(sleep=healthy_sleep, monotonic=time.monotonic, time=time.time)):
                    trial.watch(path)
                self.assertEqual(json.loads((Path(directory) / "cleaned.json").read_text())["status"], "PASS")

    def test_zombie_controller_is_dead_even_when_proc_entry_remains(self):
        text = "42 (python worker) " + " ".join(["Z"] + ["0"] * 18 + ["12345"])
        with patch.object(trial, "Path") as path:
            path.return_value.read_text.return_value = text
            self.assertIsNone(trial.process_identity(42))

    def test_preauthorized_controller_loss_latches_then_explicitly_restores_and_stops_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = AgentSandbox(directory)
            sandbox.prepare(); sandbox.block(); sandbox.tunnel.touch()
            thread, errors = sandbox.watcher()
            specification = "127.0.0.1:20991:127.0.0.1:19090"
            forward = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", specification],
                                       start_new_session=True)
            identity = trial.process_identity(forward.pid)
            state = {"private": directory, "a_id": "retained", "container_root": str(sandbox.root),
                     "prepared": True, "controller_pid": 42, "controller_identity": "dead-controller",
                      "forwards": [{"pid": forward.pid, "identity": identity, "specifications": [specification]}]}
            state.update(authorization=approval(), deadline=DEADLINE, generation=sandbox.generation)
            path = Path(directory) / "state.json"
            path.write_text(json.dumps(state))
            original_identity = trial.process_identity
            def agent(state, action, *args):
                if action == "restore": sandbox.restore()
                elif action == "join": sandbox.ns["join_watchers"]()
                elif action == "fault": sandbox.ns['fault'](sandbox.generation)
                elif action == "archive": return sandbox.dispatch('archive')
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
            self.assertEqual(len(rules), 5)
            self.assertEqual(rules[0], ['-d', '10.231.0.0/24', '!', '-o', 'ld01tun', '-j', 'REJECT'])
            for rule in rules[1:]:
                self.assertIn("--ctorigdstport", rule)
                self.assertEqual(rule[rule.index("--ctorigdstport") + 1], "53")
                if '--ctorigdst' in rule:
                    self.assertEqual(rule[rule.index("--ctorigdst") - 1], "!")
                    self.assertEqual(rule[rule.index("--ctorigdst") + 1], "10.231.0.1")
                else: self.assertIn('ld01tun', rule)
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


class ContainmentTests(unittest.TestCase):
    def test_prefix_and_all_dns_close_for_fresh_and_held_flows_until_explicit_off(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory)
            s.rules['iptables', 'filter']['OUTPUT'].append(['-m', 'conntrack', '--ctstate', 'ESTABLISHED', '-j', 'ACCEPT'])
            baseline = copy.deepcopy(s.rules)
            s.prepare(); s.block()
            for faulted in (False, True):
                if faulted: s.ns['fault'](s.generation)
                for held in (False, True):
                    with self.subTest(faulted=faulted, held=held):
                        self.assertFalse(s.permits('10.231.0.1', 'eth0', established=held))
                        self.assertFalse(s.permits('10.231.0.99', 'eth0', established=held))
                        self.assertTrue(s.permits('10.231.0.1', 'ld01tun', established=held))
                        self.assertTrue(s.permits('172.16.0.33', 'eth0', port=20992, established=held))
                        for protocol in ('udp', 'tcp'):
                            for destination in ('10.231.0.1', '127.0.0.11', '192.0.2.53'):
                                self.assertFalse(s.permits(destination, 'eth0', protocol, port=53, established=held))
                            self.assertFalse(s.permits('127.0.0.11', 'lo', protocol, original='127.0.0.11', port=53))
                            self.assertTrue(s.permits('10.231.0.1', 'ld01tun', protocol, port=53, established=held))
                self.assertNotEqual(s.resolver.read_bytes(), s.original)
            s.restore()
            self.assertEqual(s.rules, baseline)
            self.assertTrue(s.permits('10.231.0.1', 'eth0', established=True))
            self.assertEqual(s.resolver.read_bytes(), s.original)

    def test_protection_precedes_resolver_and_client_and_install_failure_never_starts(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as directory:
                s = AgentSandbox(directory)
                original_cmd = s.ns['cmd']
                def cmd(*args, **kwargs):
                    self.assertEqual(s.resolver.read_bytes(), s.original)
                    return original_cmd(*args, **kwargs)
                s.ns['cmd'] = cmd
                s.fail = lambda args: failed and args[:2] == ['iptables', '-I']
                spawn = s.ns['spawn'] = Mock()
                with self.assertRaises(RuntimeError): s.ns['start'](s.generation)
                if failed:
                    with self.assertRaises(subprocess.TimeoutExpired): s.prepare()
                    with self.assertRaisesRegex(RuntimeError, 'cancelled'): s.ns['start'](s.generation)
                    self.assertEqual(s.resolver.read_bytes(), s.original)
                    self.assertEqual(s.ns['phase']()['phase'], 'faulted')
                    spawn.assert_not_called()
                else:
                    s.prepare()
                    self.assertEqual(s.ns['phase']()['phase'], 'starting')
                    self.assertFalse(s.permits('10.231.0.1', 'eth0'))
                    s.ns['start'](s.generation)
                    spawn.assert_called_once()
                    self.assertFalse(s.permits('10.231.0.1', 'eth0'))

    def test_fault_requires_off_before_fresh_generation_and_archives_old_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare(); s.block(); s.ns['fault'](s.generation)
            old = s.generation
            with self.assertRaisesRegex(RuntimeError, 'previous generation'): s.ns['prepare']('next', '10.231.0.1')
            for action in ('start', 'renew', 'connected', 'launch_watch'):
                with self.subTest(action=action), self.assertRaises(RuntimeError): s.ns[action](old)
            s.restore()
            s.generation = 'generation-two'; s.prepare(); s.block()
            for action in ('start', 'renew'):
                with self.assertRaises(RuntimeError): s.ns[action](old)
            s.ns['fault'](old); s.ns['restore'](old)
            self.assertEqual(s.ns['phase']()['phase'], 'starting')
            self.assertTrue(any('faulted' in p.read_text() for p in s.root.glob('archive-*.json')))
            s.restore()
            with self.assertRaisesRegex(RuntimeError, 'obsolete'): s.ns['prepare'](old, '10.231.0.1')

    def test_failed_daemon_retirement_keeps_protection_and_retryable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare(); s.block()
            protected = copy.deepcopy(s.rules)
            original = s.ns['stop_daemon']
            s.ns['stop_daemon'] = Mock(side_effect=RuntimeError('identity mismatch'))
            with self.assertRaises(RuntimeError): s.restore()
            self.assertEqual(s.rules, protected)
            self.assertNotEqual(s.resolver.read_bytes(), s.original)
            self.assertEqual(json.loads((s.root / 'cleanup.json').read_text())['status'], 'FAIL')
            s.ns['stop_daemon'] = original
            s.restore()
            self.assertEqual(s.rules, s.before)

    def test_explicit_off_joins_watcher_before_releasing_output_hook(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare(); s.block()
            thread, errors = s.watcher()
            command = s.ns['cmd']
            def checked(*args, **kwargs):
                if args[:3] == ('iptables', '-D', 'OUTPUT'): self.assertFalse(thread.is_alive())
                return command(*args, **kwargs)
            s.ns['cmd'] = checked
            try: s.restore()
            finally:
                (s.root / 'cancelled').write_text(s.generation); thread.join(2)
            self.assertFalse(thread.is_alive()); self.assertEqual(errors, [])

    def test_ordinary_cleanup_and_unauthorized_supervisor_do_not_release(self):
        for supervisor in (False, True):
            with self.subTest(supervisor=supervisor), tempfile.TemporaryDirectory() as directory:
                s = AgentSandbox(directory); s.prepare(); s.block()
                state = dict(private=directory, prepared=True, a_id='retained', generation=s.generation,
                             controller_pid=42, controller_identity='gone', deadline=DEADLINE, forwards=[])
                path = Path(directory) / 'state.json'; path.write_text(json.dumps(state))
                with patch.object(trial, 'run', return_value='[{"Id":"retained"}]'), \
                        patch.object(trial, 'agent', side_effect=lambda _, action, *_args: s.ns['fault'](s.generation)), \
                        patch.object(trial, 'process_identity', return_value=None):
                    if supervisor: trial.watch(path)
                    else: self.assertTrue(trial.cleanup(state))
                self.assertEqual(s.ns['phase']()['phase'], 'faulted')
                self.assertFalse(s.permits('10.231.0.1', 'eth0'))
                self.assertFalse((Path(directory) / 'cleaned.json').exists())


class AdmissionAndObservationTests(unittest.TestCase):
    def test_failed_case_off_is_not_retried_by_controller_abort_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), approval())
            c.state.update(prepared=True, a_material=True, generation='one')
            c.shells = [Mock(), Mock()]
            def agent(_state, action, *_args):
                if action == 'restore': raise RuntimeError('retirement failed')
                return '{}'
            with patch.object(trial, 'agent', side_effect=agent):
                with self.assertRaisesRegex(RuntimeError, 'retirement'): c.off({})
            self.assertTrue(c.state['restoration_failed'])
            with patch.object(trial, 'agent') as root:
                self.assertTrue(trial.cleanup(c.state, explicit_off='abort'))
                root.assert_not_called()
            self.assertTrue(c.state['a_material'])

    def test_final_cleanup_skips_retired_forward_whose_binding_was_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            old = dict(name='vpn', retired=True, specifications=['same-binding'])
            fresh = dict(name='vpn', specifications=['same-binding'])
            state = dict(private=directory, authorization=approval(), forwards=[old, fresh])
            with patch.object(trial, 'stop_forward') as stop:
                self.assertEqual(trial.cleanup(state, explicit_off='completion'), [])
                stop.assert_called_once_with(fresh)

    def test_supervisor_retains_failed_teardown_without_automatic_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.json'; path.write_text('{}')
            (path.parent / 'cleanup-attempt-one.json').write_text('{"status":"FAIL"}')
            with patch.object(trial, 'cleanup') as cleanup:
                trial.watch(path)
                cleanup.assert_not_called()
            self.assertEqual(json.loads((path.parent / 'supervisor-result.json').read_text())['cleanup_status'], 'FAIL')

    def test_approval_flags_targets_and_absolute_reserves_are_required(self):
        valid = approval()
        self.assertEqual(trial.authorize(valid, START), valid)
        for key in ('injection', 'observation', 'exclusive_reuse', 'supervised_off', 'cases', 'targets'):
            value = dict(valid); value.pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError): trial.authorize(value, START)
        for now in (START - dt.timedelta(seconds=1), START + dt.timedelta(minutes=30), START + dt.timedelta(minutes=45)):
            with self.subTest(now=now), self.assertRaises(ValueError): trial.authorize(valid, now)
        value = dict(valid, deadline=(START + dt.timedelta(minutes=46)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        with self.assertRaises(ValueError): trial.authorize(value, START)

    def test_missing_live_approval_records_private_rejection_without_external_commands(self):
        with patch.object(trial.Path, 'mkdir') as mkdir, patch.object(trial, 'private_write') as write, \
                patch.object(sys, 'argv', ['trial.py', '--private-dir', '/tmp/opencode/n2-synthetic-rejection']), \
                patch.object(trial, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(trial.main(), 1)
            run.assert_not_called(); mkdir.assert_called_once_with(mode=0o700)
            self.assertIn('no live approval', write.call_args.args[1])

    def capture(self, directory):
        path = Path(directory)
        state = dict(veth='vethA', a_ip='172.16.0.2', a_bridge='172.16.0.1', subnet='10.231.0.0/24',
                     capture=dict(stdout=str(path / 'headers'), stderr=str(path / 'stats')))
        (path / 'headers').write_text('{"pid":42}\n100.000000 IP 172.16.0.2.45000 > 172.16.0.1.20992: tcp 10\n')
        (path / 'stats').write_text('tcpdump: listening on vethA, link-type EN10MB\n1 packet captured\n1 packet received by filter\n0 packets dropped by kernel\n')
        return state

    def test_capture_verdict_requires_ready_positive_canary_and_zero_drops(self):
        for failure in (None, 'ready', 'canary', 'drops', 'counts', 'statistics', 'buffered'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                state = self.capture(directory)
                path = Path(state['capture']['stderr'])
                if failure == 'ready': path.write_text(path.read_text().replace('listening on vethA', 'listening on wrong'))
                if failure == 'canary': Path(state['capture']['stdout']).write_text('{"pid":42}\n100.000000 IP 172.16.0.2.45000 > 172.16.0.1.20990: tcp 10\n')
                if failure == 'drops': path.write_text(path.read_text().replace('0 packets dropped', '1 packet dropped'))
                if failure == 'counts': path.write_text(path.read_text().replace('1 packet captured', '2 packets captured'))
                if failure == 'statistics': path.write_text('tcpdump: listening on vethA\n')
                if failure == 'buffered': path.write_text(path.read_text().replace('1 packet received', '2 packets received'))
                if failure is None: self.assertEqual(trial.capture_proof(state, [(99, 101)])['dropped'], 0)
                else:
                    with self.assertRaises(ValueError): trial.capture_proof(state, [(99, 101)])

    def test_capture_catches_prefix_and_dns_egress_including_held_vpn_source(self):
        for source, destination, port in (('172.16.0.2', '10.231.0.1', 8080),
                                          ('10.231.0.2', '10.231.0.1', 19091),
                                          ('172.16.0.2', '192.0.2.53', 53)):
            with self.subTest(source=source, destination=destination), tempfile.TemporaryDirectory() as directory:
                state = self.capture(directory)
                row = (100.5, source, 45001, destination, port)
                with self.assertRaisesRegex(ValueError, 'forbidden'): trial.check_underlay(state, [row], [(99, 101)])
                trial.check_underlay(state, [row], [(101, 102)])  # Ordinary off is baseline, not always-private.

    def test_timeout_or_static_rules_cannot_replace_rejection_counter_growth(self):
        before = '\n'.join('0 0 REJECT all' for _ in range(5))
        after = '3 300 REJECT all\n2 200 REJECT udp\n0 0 REJECT udp\n2 200 REJECT tcp\n0 0 REJECT tcp'
        trial.check_counter_growth(before, after)
        for invalid in ('', before, '3 300 REJECT all\n' + '\n'.join('0 0 REJECT all' for _ in range(4))):
            with self.assertRaises(ValueError): trial.check_counter_growth(before, invalid)

    def test_expected_transport_fault_does_not_mask_lease_heartbeat_or_sibling_forward_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            controller = trial.Trial(Path(directory))
            controller.state['forwards'] = [dict(pid=42, identity='vpn', intentionally_stopped=True), dict(pid=43, identity='heartbeat')]
            controller.holds = [(Mock(poll=Mock(return_value=None)), None)]
            with patch.object(trial, 'reserve'), patch.object(trial, 'process_identity', return_value='heartbeat'):
                controller.health(expected_fault=True)
                controller.lease = Mock(error=RuntimeError('unexpected'))
                with self.assertRaisesRegex(ValueError, 'lease'): controller.health(expected_fault=True)
                controller.lease = None
                controller.holds[0][0].poll.return_value = 1
                with self.assertRaisesRegex(ValueError, 'heartbeat'): controller.health(expected_fault=True)
                controller.holds = []
                with patch.object(trial, 'process_identity', return_value=None), self.assertRaisesRegex(ValueError, 'transport'):
                    controller.health(expected_fault=True)
                controller.state.update(prepared=True,generation='one',forwards=[])
                for reason in ('lease','deadline'):
                    status=dict(active=True,intent=dict(phase='faulted',reason=reason))
                    with patch.object(trial,'agent',return_value=json.dumps(status)), self.assertRaisesRegex(ValueError,'lease/deadline'):
                        controller.health(expected_fault=True)

    def test_wrong_forward_identity_never_signals_any_process(self):
        record = dict(pid=42, identity='same', specifications=['172.16.0.1:20990:127.0.0.1:11940'])
        with patch.object(trial, 'process_identity', return_value='same'), patch.object(trial, 'Path') as path, \
                patch.object(trial.os, 'killpg') as kill:
            path.return_value.read_bytes.return_value = b'ssh\x00unrelated\x00'
            with self.assertRaisesRegex(ValueError, 'specification'): trial.stop_forward(record, injection=True)
            kill.assert_not_called()

    def test_both_cases_observe_then_explicit_off_and_fresh_reconnect_without_retry(self):
        for number in (0, 1):
            with self.subTest(case=number), tempfile.TemporaryDirectory() as directory:
                c = trial.Trial(Path(directory), approval())
                c.state.update(deadline=DEADLINE, server='10.231.0.1', a_bridge='172.16.0.1', generation='one',
                               forwards=[dict(name='vpn', specifications=['approved-vpn-forward'])])
                events, clock = [], [0]
                def monotonic(): clock[0] += 31; return clock[0]
                def capture(): c.state['capture'] = dict(intervals=[])
                def connect(record, *args):
                    events.append('connect'); record['protected_at'] = 10
                    c.lease = Mock(); c.lease.allow_fault = threading.Event()
                def off(record): events.append('off'); record['off_requested_at'] = 20
                path = Path(directory) / 'vpn.jsonl'
                rows = [dict(kind='ack', monotonic=1, socket='same')]
                path.write_text('\n'.join(json.dumps(r) for r in rows) + '\n')
                def probes(_action):
                    with path.open('a') as stream:
                        for kind in ('attempt','blocked'):
                            stream.write(json.dumps(dict(kind=kind, monotonic=clock[0], socket='same'))+'\n')
                    return ['synthetic-private-negatives']
                def finish(*args, **kwargs):
                    with path.open('a') as f: f.write(json.dumps(dict(kind='finished', socket='same', reconnects=0)) + '\n')
                process = Mock(returncode=0, poll=Mock(return_value=None), communicate=Mock(side_effect=finish))
                def hold(*args, **kwargs): c.vpn_hold = (process, path)
                counters = '\n'.join('0 0 REJECT all' for _ in range(5))
                growth = '\n'.join('2 200 REJECT all' for _ in range(5))
                def health(expected_fault=False):
                    return dict(counters=growth if expected_fault else counters, intent=dict(phase='faulted'), daemon_live=True)
                c.capture_process = Mock(wait=Mock(return_value=0))
                with patch.object(c, 'start_capture', side_effect=capture), patch.object(c, 'connect', side_effect=connect), \
                        patch.object(c, 'off', side_effect=off), patch.object(c, 'start_hold', side_effect=hold), \
                        patch.object(c, 'health', side_effect=health), patch.object(c, 'capture_ready'), \
                        patch.object(c, 'probe_shells', side_effect=probes), \
                        patch.object(c, 'siblings', return_value=['synthetic-continuity']), \
                        patch.object(c, 'forward') as forward, patch.object(trial, 'stop_capture', return_value={'dropped': 0}), \
                        patch.object(trial, 'stop_forward', side_effect=lambda *_a, **_k: events.append('transport-kill')) as stop, \
                        patch.object(trial, 'agent', side_effect=lambda _, action, *_a: events.append(action)), \
                        patch.object(trial, 'reserve'), patch.object(trial.time, 'monotonic', side_effect=monotonic), \
                        patch.object(trial.time, 'sleep'):
                    c.cycle(number)
                self.assertEqual(events, ['connect', 'kill_client' if number == 0 else 'transport-kill',
                                           *([] if number == 0 else ['fault']), 'off', 'connect', 'off'])
                self.assertEqual(forward.call_count, number)
                self.assertEqual(stop.call_count, number)
                record = c.evidence['cycles'][0]
                self.assertEqual(record['status'], 'PASS')
                self.assertGreaterEqual(record['observed_until_monotonic'] - record['injected_monotonic'], 60)
                self.assertTrue((Path(directory) / ('fault-evidence-F' + str(number + 1) + '.json')).exists())

    def test_failed_positive_baseline_stops_campaign_before_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory))
            with patch.object(c, 'start_capture'), patch.object(c, 'connect', side_effect=ValueError('baseline failed')), \
                    patch.object(trial, 'agent') as agent, patch.object(trial, 'stop_forward') as stop:
                with self.assertRaisesRegex(ValueError, 'baseline'): c.cycle(0)
                agent.assert_not_called(); stop.assert_not_called()

    def test_daemon_injection_rechecks_identity_and_fifteen_minute_reserve(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare(); s.block()
            s.now = dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')).timestamp() - 900
            s.ns['checked_daemon'] = Mock()
            with self.assertRaisesRegex(RuntimeError, 'reserve'): s.ns['kill_client'](s.generation)
            s.ns['checked_daemon'].assert_not_called()
            s.now -= 1
            s.ns['checked_daemon'] = Mock(side_effect=RuntimeError('identity mismatch'))
            with patch.object(s.ns['os'], 'kill') as kill:
                with self.assertRaisesRegex(RuntimeError, 'identity'): s.ns['kill_client'](s.generation)
                kill.assert_not_called()

    def test_capture_worker_expires_without_controller_and_cancels_on_eof(self):
        for release in (False, True, 'stalled-open'):
            with self.subTest(release=release), tempfile.TemporaryDirectory() as directory:
                marker = Path(directory) / 'executed'
                code = 'import pathlib,signal,sys,time; pathlib.Path(sys.argv[1]).touch(); signal.signal(signal.SIGINT,lambda *_:sys.exit(0)); time.sleep(60)'
                process = subprocess.Popen([sys.executable, '-u', '-c', trial.CAPTURE, str(time.time() + .5),
                    str(Path(directory) / 'capture.stop'), sys.executable, '-c', code, str(marker)],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    metadata = json.loads(process.stdout.readline())
                    self.assertIsNotNone(trial.process_identity(metadata['pid']))
                    self.assertFalse(marker.exists())
                    if release == 'stalled-open':
                        process.wait(timeout=3)  # stdin deliberately remains open, without a gate byte.
                        output, error = process.communicate(timeout=1)
                    else:
                        output, error = process.communicate(input=b'G' if release else b'', timeout=3)
                    self.assertNotEqual(process.returncode, 0)
                    self.assertEqual(marker.exists(), release is True)
                    self.assertIsNone(trial.process_identity(metadata['pid']))
                finally:
                    if process.poll() is None: process.kill()
                    process.communicate(timeout=3)


class FaultFixtureTests(unittest.TestCase):
    def test_fault_hold_rejects_real_malformed_oversize_and_changed_protocol_responses(self):
        for corrupt in (b'not-json\n', b'x' * 600 + b'\n', b'{"seq":99,"connection":"one"}\n'):
            with self.subTest(response=corrupt[:20]):
                class Corrupt(fixtures.socketserver.StreamRequestHandler):
                    def handle(self):
                        self.rfile.readline(); self.wfile.write(b'{"seq":1,"connection":"one"}\n'); self.wfile.flush()
                        self.rfile.readline(); self.wfile.write(corrupt); self.wfile.flush()
                with fixtures.socketserver.ThreadingTCPServer(('127.0.0.1', 0), Corrupt) as server:
                    thread = threading.Thread(target=server.serve_forever); thread.start()
                    process = subprocess.Popen([sys.executable, str(Path(fixtures.__file__)), 'fault-hold', '--port',
                        str(server.server_address[1])], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        self.assertNotEqual(process.wait(timeout=4), 0)
                        output, error = process.communicate(timeout=1)
                        self.assertIn('Error', error)
                        self.assertNotIn('"kind": "blocked"', output)
                        self.assertNotIn('"kind": "finished"', output)
                    finally:
                        if process.poll() is None: process.kill()
                        process.communicate(timeout=2); server.shutdown(); thread.join()

    def test_private_queries_are_uncached_and_cover_application_a_aaaa_and_direct_udp_tcp(self):
        names = []
        def lookup(name, port, family=socket.AF_INET):
            names.append(name)
            if family == socket.AF_INET6: raise socket.gaierror('authoritative no-data')
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.231.0.1', port))]
        queries = []
        def dig(command, **kwargs):
            queries.append(command)
            resolver, name, kind = command[1][1:], command[-2], command[-1]
            if resolver == '127.0.0.11': return subprocess.CompletedProcess(command, 9, 'no servers could be reached', '')
            answer = ';; status: NOERROR\n;; flags: qr aa rd; QUERY: 1\n'
            if kind == 'A': answer += name + ' 0 IN A 10.231.0.1\n'
            return subprocess.CompletedProcess(command, 0, answer, '')
        fixture = dict(fixture='task', service='service.ld01.test')
        sock = Mock()
        sock.recv.side_effect = [b'HTTP/1.0 200 OK\r\n\r\n' + json.dumps(fixture).encode(), b'',
                                b'HTTP/1.0 200 OK\r\n\r\n' + json.dumps(fixture).encode(), b'']
        context = Mock(__enter__=Mock(return_value=sock), __exit__=Mock(return_value=False))
        with patch.object(fixtures.socket, 'getaddrinfo', side_effect=lookup), \
                patch.object(fixtures.socket, 'create_connection', return_value=context), \
                patch.object(fixtures.subprocess, 'run', side_effect=dig), patch.object(fixtures, 'fresh', return_value={'seq': 1, 'connection': 'direct'}):
            result = fixtures.probes('10.231.0.1', '172.16.0.1', True)
        self.assertEqual(result['http'], result['named_http'])
        self.assertEqual(len(queries), 8)
        self.assertEqual(len({q[-2] for q in queries}), 8)
        self.assertEqual({q[1] for q in queries}, {'@10.231.0.1', '@127.0.0.11'})
        self.assertEqual({q[-1] for q in queries}, {'A', 'AAAA'})
        self.assertEqual(sum('+tcp' in q for q in queries), 4)
        self.assertTrue(all(name.endswith('.ld01.test') for name in names))

    def test_fault_probes_record_failures_but_require_working_direct_ip_canary(self):
        with patch.object(fixtures.socket, 'getaddrinfo', side_effect=socket.gaierror('blocked')), \
                patch.object(fixtures.socket, 'create_connection', side_effect=OSError('blocked')), \
                patch.object(fixtures.subprocess, 'run', return_value=subprocess.CompletedProcess([], 9, 'no servers reached', '')), \
                patch.object(fixtures, 'fresh', return_value={'seq': 1, 'connection': 'direct'}) as fresh:
            result = fixtures.probes('10.231.0.1', '172.16.0.1', False)
            self.assertFalse(result['public_dns']); self.assertFalse(any(d['responded'] for d in result['dns']))
            self.assertEqual(result['application'], []); self.assertIsNone(result['http'])
            fresh.side_effect = OSError('unrelated direct path failed')
            with self.assertRaises(OSError): fixtures.probes('10.231.0.1', '172.16.0.1', False)

    def test_held_fault_flow_keeps_original_socket_after_server_closes(self):
        class CloseAfterAck(fixtures.socketserver.StreamRequestHandler):
            def handle(self):
                self.rfile.readline()
                self.wfile.write(b'{"seq":1,"connection":"one"}\n'); self.wfile.flush()
        with fixtures.socketserver.ThreadingTCPServer(('127.0.0.1', 0), CloseAfterAck) as server:
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever); thread.start()
            process = subprocess.Popen([sys.executable, str(Path(fixtures.__file__)), 'fault-hold', '--port',
                                       str(server.server_address[1])], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                first = json.loads(process.stdout.readline())
                blocked = json.loads(process.stdout.readline())
                while blocked['kind']=='attempt': blocked = json.loads(process.stdout.readline())
                self.assertEqual(first['kind'], 'ack'); self.assertEqual(blocked['kind'], 'blocked')
                output, error = process.communicate('stop\n', timeout=3)
                self.assertEqual(process.returncode, 0, error)
                final = json.loads(output.splitlines()[-1])
                self.assertEqual(final['socket'], first['socket']); self.assertEqual(final['reconnects'], 0)
                self.assertGreater(final['errors'], 0)
            finally:
                if process.poll() is None: process.kill()
                process.communicate(timeout=3); server.shutdown(); thread.join()


class ReviewPatchTests(unittest.TestCase):
    def test_expected_client_fault_rejection_never_masks_lease_or_watcher_failure(self):
        for reason in ('client','controller failure','lease','deadline','watcher lost'):
            lease=object.__new__(trial.Lease)
            lease.state={}; lease.generation='one'; lease.error=None
            lease.stopped=threading.Event(); lease.allow_fault=threading.Event(); lease.allow_fault.set()
            with self.subTest(reason=reason), patch.object(trial,'agent',return_value=json.dumps(
                    dict(accepted=False,phase='faulted',reason=reason))):
                lease.renew()
                self.assertEqual(lease.error is None,reason in ('client','controller failure'))

    def test_live_transport_interval_exercises_real_fresh_dns_and_held_verdict_before_retirement(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory))
            c.state.update(prepared=True, generation='one', server='10.231.0.1', a_bridge='172.16.0.1',
                           forwards=[dict(pid=42,identity='vpn',intentionally_stopped=True),dict(pid=43,identity='heartbeat')])
            identities=[dict(pid=i) for i in (1,2)]; c.evidence['shells']=identities
            path=Path(directory)/'held.jsonl'; path.write_text('')
            c.vpn_hold=(Mock(poll=Mock(return_value=None)),path)
            def shell(identity, action, **_kwargs):
                self.assertEqual(action,'fault_probe')
                with path.open('a') as stream: stream.write(json.dumps(dict(kind='attempt',monotonic=time.monotonic()))+'\n')
                return dict(identity=identity,application=[],application_aaaa=[],http=None,public_dns=False,
                            dns=[dict(resolver=r,responded=False) for r in ('10.231.0.1','127.0.0.11')],
                            direct=dict(seq=1,connection='direct'))
            c.shells=[Mock(request=Mock(side_effect=lambda action, identity=i, **kwargs:shell(identity,action,**kwargs))) for i in identities]
            status=dict(active=True,intent=dict(phase='connected'),daemon_live=True,watcher_registered=True,watcher_live=True,watcher_done=False)
            with patch.object(trial,'reserve'), patch.object(trial,'process_identity',side_effect=lambda pid:'heartbeat' if pid==43 else None), \
                    patch.object(trial,'agent',return_value=json.dumps(status)) as agent, patch.object(c,'capture_ready') as capture, \
                    patch.object(c,'siblings',return_value=['fresh siblings']):
                record={}; c.observe_transport_loss(record)
                self.assertGreaterEqual(capture.call_count,2)
                self.assertTrue(all(call.args[1]=='status' for call in agent.call_args_list))
                observed=record['live_client_transport_loss']
                self.assertEqual(len(observed['probes']),2); self.assertTrue(observed['held_attempts'])
                self.assertTrue(observed['before']['daemon_live'] and observed['after']['daemon_live'])
                self.assertLessEqual(observed['start'],observed['held_attempts'][0]['monotonic'])
                self.assertLessEqual(observed['held_attempts'][0]['monotonic'],observed['finished'])

    def test_supervisor_cancels_before_ownership_reloads_latest_and_blocks_stale_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            state = dict(private=directory, authorization=approval(), prepared=False, forwards=[],
                         container_root='/run/task', a_id='retained', generation='old')
            trial.save(state)
            stale = copy.deepcopy(state)
            registered, cancelled, release = threading.Event(), threading.Event(), threading.Event()
            errors, restored, results, staging = [], [], [], []
            original_write, original_replace = trial.private_write, trial.os.replace
            def write(path, value):
                original_write(path, value)
                if path.name=='off-requested.json': cancelled.set()
            def replace(source, destination):
                if destination.name=='state.json': staging.append(source.name)
                return original_replace(source, destination)
            def inside(_container, *command, **_kwargs):
                if command[0]=='cat': return '{"status":"PASS","release_at":100}'
                action = command[3]
                if action=='restore': restored.append(stale['generation'])
                return '{}'
            def controller():
                try:
                    with trial.lifecycle(state):
                        state.update(prepared=True, generation='fresh')
                        trial.save(state); registered.set()
                        if not release.wait(2): raise RuntimeError('test handshake timeout')
                        state['stale_write'] = True
                        try: trial.save(state)
                        except ValueError as error: errors.append(str(error))
                        try: trial.agent(state, 'start', 'fresh')
                        except ValueError as error: errors.append(str(error))
                except Exception as error: errors.append(type(error).__name__+': '+str(error))
            def supervisor(): results.extend(trial.cleanup(stale, explicit_off='expiry'))
            with patch.object(trial, 'private_write', side_effect=write), patch.object(trial.os, 'replace', side_effect=replace), \
                    patch.object(trial, 'run', return_value='[{"Id":"retained"}]'), patch.object(trial, 'inside', side_effect=inside):
                worker = threading.Thread(target=controller); worker.start()
                self.assertTrue(registered.wait(1))
                supervisor_thread = threading.Thread(target=supervisor); supervisor_thread.start()
                try:
                    self.assertTrue(cancelled.wait(1))
                    self.assertEqual(restored, [])  # Cancellation is published while controller still owns mutation.
                finally:
                    release.set(); worker.join(3); supervisor_thread.join(3)
            self.assertFalse(worker.is_alive() or supervisor_thread.is_alive())
            self.assertEqual(results, []); self.assertEqual(restored, ['fresh'])
            self.assertEqual(len(errors), 2)
            self.assertTrue(all('supervised trial-off' in error for error in errors))
            self.assertNotIn('stale_write', json.loads((Path(directory)/'state.json').read_text()))
            self.assertTrue(all(name.startswith('.state-') and name!='state.new' for name in staging))
            self.assertEqual(len(staging), len(set(staging)))

    def test_cancellation_wins_registered_forward_gate_race(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), approval())
            trial.save(c.state)
            stale = copy.deepcopy(c.state)
            registered, cancelled, release = threading.Event(), threading.Event(), threading.Event()
            children, errors, cleaned = [], [], []
            marker = Path(directory)/'executed'
            actual_spawn, original_save, original_write = subprocess.Popen, trial.save, trial.private_write
            def spawn(command, **kwargs):
                child = actual_spawn([*command[:3], sys.executable, '-c',
                    'from pathlib import Path; import sys; Path(sys.argv[1]).touch()', str(marker)], **kwargs)
                children.append(child); return child
            def save(state):
                original_save(state)
                if state['forwards']:
                    registered.set()
                    if not release.wait(2): raise RuntimeError('handshake timeout')
            def write(path, value):
                original_write(path, value)
                if path.name=='off-requested.json': cancelled.set()
            def controller():
                try: c.forward('vpn', ['127.0.0.1:20990:127.0.0.1:11940'])
                except Exception as error: errors.append(str(error))
            def stop(record):
                cleaned.append(record['pid'])
                self.assertEqual(children[0].wait(timeout=2), 1)
            with patch.object(trial, 'reserve'), patch.object(trial, 'save', side_effect=save), \
                    patch.object(trial, 'private_write', side_effect=write), patch.object(trial.subprocess, 'Popen', side_effect=spawn), \
                    patch.object(trial, 'stop_forward', side_effect=stop):
                worker = threading.Thread(target=controller); worker.start()
                self.assertTrue(registered.wait(1))
                supervisor = threading.Thread(target=lambda:trial.cleanup(stale, explicit_off='expiry')); supervisor.start()
                try: self.assertTrue(cancelled.wait(1))
                finally:
                    release.set(); worker.join(3); supervisor.join(3)
                    for child in children:
                        if child.poll() is None: child.kill()
                        child.wait(timeout=2)
            self.assertFalse(worker.is_alive() or supervisor.is_alive())
            self.assertEqual(cleaned, [children[0].pid])
            self.assertEqual(len(errors), 1); self.assertIn('supervised trial-off', errors[0])
            self.assertFalse(marker.exists())

    def test_supervisor_inherits_reuse_flock_through_controller_death_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            code = '''import fcntl,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
import trial
private=Path(sys.argv[2]); approval=__import__('json').loads(sys.argv[3])
trial.DEADLINE=approval['deadline']
c=trial.Trial(private,approval)
def deploy(): print('entered',flush=True); sys.stdin.read(1)
with open(private/'reuse.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX); c.exclusive_fd=lock.fileno()
 with patch.object(c,'preflight',side_effect=lambda:trial.save(c.state)), patch.object(c,'deploy',side_effect=deploy): c.execute()
'''
            owner = subprocess.Popen([sys.executable, '-u', '-c', code, str(trial.HERE), directory, json.dumps(approval())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            watcher = None
            try:
                self.assertTrue(trial.select.select([owner.stdout], [], [], 3)[0])
                self.assertEqual(owner.stdout.readline().strip(), 'entered')
                ready = json.loads((private/'supervisor-ready.json').read_text()); watcher=ready['pid']
                with (private/'cleanup.lock').open('a') as cleanup_lock:
                    fcntl.flock(cleanup_lock, fcntl.LOCK_EX)
                    owner.kill(); owner.wait(timeout=2)
                    with (private/'reuse.lock').open('a') as competing:
                        with self.assertRaises(BlockingIOError): fcntl.flock(competing, fcntl.LOCK_EX|fcntl.LOCK_NB)
                until=time.monotonic()+5
                while not (private/'cleaned.json').exists() and time.monotonic()<until: time.sleep(.01)
                self.assertTrue((private/'cleaned.json').exists())
                with (private/'reuse.lock').open('a') as competing:
                    until=time.monotonic()+3
                    while True:
                        try: fcntl.flock(competing,fcntl.LOCK_EX|fcntl.LOCK_NB); break
                        except BlockingIOError:
                            if time.monotonic()>=until: raise
                            time.sleep(.01)
            finally:
                if owner.poll() is None: owner.kill()
                owner.communicate(timeout=3)
                if watcher is not None and trial.process_identity(watcher) is not None:
                    os.kill(watcher, signal.SIGTERM)

    def test_preflight_ignores_disclosed_zombies_but_rejects_live_client_journals_and_chains(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); proc, run = base/'proc', base/'run'
            proc.mkdir(); run.mkdir()
            for pid in (1006,1037,1294,1325):
                p=proc/str(pid); p.mkdir()
                (p/'comm').write_text('openvpn' if pid in (1037,1325) else 'python3')
                (p/'stat').write_text(str(pid)+' (fixture) '+' '.join(['Z']+['0']*18+['100']))
            original_path=Path
            def route(*parts):
                return {'/proc':proc,'/run':run}.get(str(parts[0]), original_path(*parts))
            def inside(_container,*command,**kwargs):
                if command[0]=='python3':
                    with patch.object(__import__('pathlib'),'Path',side_effect=route), contextlib.redirect_stdout(io.StringIO()) as output:
                        exec(compile(command[-1],'idle-check','exec'),{})
                    return output.getvalue()
                return chain[0]
            chain=['']
            with patch.object(trial,'inside',side_effect=inside):
                self.assertEqual(len(trial.check_idle_a()['processes']),4)
                chain[0]='-N LDC0123456789ab\n'
                with self.assertRaisesRegex(ValueError,'containment chain'): trial.check_idle_a()
                chain[0]=''
                unresolved=run/'ld01-cvpnfailed'; unresolved.mkdir()
                with self.assertRaisesRegex(ValueError,'task journals'): trial.check_idle_a()
                (unresolved/'cleanup.json').write_text('{"status":"PASS"}')
                trial.check_idle_a()
                active=proc/'99'; active.mkdir(); (active/'comm').write_text('openvpn')
                (active/'stat').write_text('99 (openvpn) '+' '.join(['S']+['0']*18+['200']))
                with self.assertRaisesRegex(ValueError,'active A VPN'): trial.check_idle_a()

    def test_real_fault_verdict_rejects_every_escape_in_either_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory))
            c.state.update(server='10.231.0.1', a_bridge='172.16.0.1')
            identities = [dict(pid=i, uid=1001) for i in (1, 2)]
            c.evidence['shells'] = identities
            negative = dict(application=[], application_aaaa=[], http=None, public_dns=False,
                            direct=dict(seq=1, connection='canary'),
                            dns=[dict(resolver=resolver, protocol=p, kind=k, responded=False)
                                 for resolver in ('10.231.0.1', '127.0.0.11') for p in ('udp', 'tcp') for k in ('A', 'AAAA')])
            escapes = [lambda p:p.update(application=['10.231.0.1']), lambda p:p.update(application_aaaa=['::1']),
                       lambda p:p.update(http={'fixture':'escaped'}), lambda p:p.update(public_dns=True)]
            escapes += [lambda p, index=i:p['dns'][index].update(responded=True) for i in range(8)]
            for shell in (0, 1):
                for escape in escapes:
                    probes = [dict(copy.deepcopy(negative), identity=identity) for identity in identities]
                    escape(probes[shell])
                    c.shells = [Mock(request=Mock(return_value=p)) for p in probes]
                    with self.subTest(shell=shell, probe=probes[shell]), self.assertRaisesRegex(ValueError, 'escaped containment'):
                        c.probe_shells('fault_probe')
            c.shells = [Mock(request=Mock(return_value=dict(copy.deepcopy(negative), identity=i))) for i in identities]
            self.assertEqual(len(c.probe_shells('fault_probe')), 2)

    def test_successful_real_controller_off_then_connect_uses_fresh_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare(); s.ns['fault'](s.generation)
            c = trial.Trial(Path(directory), approval())
            c.state.update(prepared=True, generation=s.generation, server='10.231.0.1', subnet='10.231.0.0/24',
                           container_root=str(s.root), deadline=DEADLINE, a_bridge='172.16.0.1')
            identities = [dict(pid=i, uid=1001) for i in (1, 2)]
            c.evidence['shells'] = identities
            fixture = dict(fixture=c.state['task'], service='service.ld01.test')
            c.shells = [Mock(request=Mock(return_value=dict(identity=i, public_dns=True, http=fixture,
                                                          direct=dict(seq=1, connection='direct')))) for i in identities]
            c.a_before = {'-4route': []}
            threads = []
            s.ns['spawn'] = Mock()
            def agent(_state, action, *args):
                if action == 'renew':
                    s.ns['renew'](args[0]); return '{"accepted":true}'
                if action == 'prepare':
                    s.generation = args[0]
                    return json.dumps(s.prepare())
                if action == 'launch_watch':
                    threads.append(s.watcher()[0]); return ''
                if action == 'status':
                    status = json.loads(s.dispatch('status'))
                    status.update(log='Initialization Sequence Completed', daemon_status='CapEff:\t0000000000001000')
                    status['network']['ipv6'] = '\n'.join('-A '+h+' -j LDC'+c.state['task'][-12:] for h in ('INPUT','OUTPUT','FORWARD'))
                    return json.dumps(status)
                if action == 'restore': s.restore(); return ''
                if action == 'join': s.ns['join_watchers'](); return ''
                if action == 'start': s.ns['start'](s.generation, ['synthetic']); return ''
                return s.dispatch(action)
            def snapshot(_container):
                return {'-4route': [dict(dst='10.231.0.0/24', dev='ld01tun')]} if (s.root/'active').exists() else c.a_before
            with patch.object(trial, 'reserve'), patch.object(trial, 'agent', side_effect=agent), \
                    patch.object(trial, 'inside', side_effect=lambda *_a, **_k:(s.root/'cleanup.json').read_text()), \
                    patch.object(trial, 'snapshot', side_effect=snapshot), patch.object(c, 'negative_probes'), \
                    patch.object(c, 'siblings', return_value=[]):
                try:
                    old = c.state['generation']
                    c.off({})
                    self.assertFalse(c.state['prepared'])
                    self.assertEqual(s.resolver.read_bytes(), s.original)
                    c.connect({})
                    self.assertTrue(c.state['prepared'])
                    self.assertNotEqual(c.state['generation'], old)
                    self.assertEqual(s.ns['phase']()['phase'], 'connected')
                    self.assertFalse(s.permits('10.231.0.1', 'eth0'))
                finally:
                    c.off({})
                    for thread in threads: thread.join(2)

    def test_f2_requires_live_identity_group_and_real_reserve_before_signal(self):
        trial.authorize(approval(), START)  # Admitted while the full approved window is available.
        record = dict(pid=42, identity='start', specifications=['172.16.0.1:20990:127.0.0.1:11940'])
        end = dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00'))
        for seconds in (900, 899, 901):
            with self.subTest(remaining=seconds), patch.object(trial, 'DEADLINE', DEADLINE), \
                    patch.object(trial, 'utc', return_value=end-dt.timedelta(seconds=seconds)), \
                    patch.object(trial, 'Path') as path, patch.object(trial.os, 'getpgid', return_value=42), \
                    patch.object(trial, 'process_identity', side_effect=['start', None] if seconds==901 else ['start']), \
                    patch.object(trial.os, 'killpg') as signal_group, patch.object(trial, 'run', return_value='') as run:
                path.return_value.read_bytes.return_value = b'ssh\0' + record['specifications'][0].encode() + b'\0'
                if seconds <= 900:
                    with self.assertRaisesRegex(ValueError, 'approval expired or cleanup reserve'): trial.stop_forward(record, injection=True)
                    signal_group.assert_not_called(); run.assert_not_called()
                else:
                    trial.stop_forward(record, injection=True)
                    signal_group.assert_called_once_with(42, signal.SIGTERM)
        for identity in (None, 'reused'):
            with patch.object(trial, 'process_identity', return_value=identity), patch.object(trial.os, 'killpg') as kill, \
                    self.assertRaisesRegex(ValueError, 'not live'):
                trial.stop_forward(record, injection=True)
            kill.assert_not_called()
        with patch.object(trial, 'process_identity', return_value=None), patch.object(trial, 'run', return_value=''):
            trial.stop_forward(record)  # Teardown remains idempotent.
        with patch.object(trial, 'process_identity', return_value='start'), patch.object(trial, 'Path') as path, \
                patch.object(trial.os,'getpgid',return_value=99), patch.object(trial.os,'killpg') as kill:
            path.return_value.read_bytes.return_value=b'ssh\0'+record['specifications'][0].encode()+b'\0'
            with self.assertRaisesRegex(ValueError,'group identity'): trial.stop_forward(record,injection=True)
            kill.assert_not_called()

    def test_admitted_campaign_rechecks_real_reserve_after_baseline_consumes_time(self):
        end = dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00'))
        now = [end-dt.timedelta(seconds=1200)]
        with tempfile.TemporaryDirectory() as directory, patch.object(trial, 'DEADLINE', DEADLINE), \
                patch.object(trial, 'utc', side_effect=lambda:now[0]):
            trial.authorize(approval())
            c = trial.Trial(Path(directory), approval())
            c.lease = Mock()
            def connect(*_): now[0] = end-dt.timedelta(seconds=899)
            with patch.object(c, 'start_capture'), patch.object(c, 'connect', side_effect=connect), \
                    patch.object(c, 'start_hold'), patch.object(c, 'capture_ready'), patch.object(c, 'health', return_value={'counters':''}), \
                    patch.object(trial, 'stop_forward', wraps=trial.stop_forward) as inject:
                with self.assertRaisesRegex(ValueError, 'approval expired or cleanup reserve'): c.cycle(1)
                inject.assert_not_called()

    def test_fault_archives_current_state_and_malformed_attempt_before_retirement_and_off(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare()
            (s.root/'cleanup-attempt-truncated.json').write_text('{truncated')
            def retirement():
                archive = json.loads(list(s.root.glob('archive-*.json'))[-1].read_text())
                self.assertIn(s.ns['chain'], archive['network']['ipv4'])
                self.assertIn('REJECT', archive['counters'])
                self.assertIn('fixture', archive['processes'])
                self.assertEqual(archive['journals']['cleanup-attempt-truncated.json']['raw'], '{truncated')
            s.ns['stop_daemon'] = retirement
            s.ns['fault'](s.generation)
            s.restore()
            self.assertEqual(s.rules, s.before)
            self.assertEqual(json.loads((s.root/'cleanup.json').read_text())['status'], 'PASS')

    def test_fault_observation_errors_are_independent_and_authoritative_journals_stay_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare()
            s.fail = lambda args: args[0]=='ps' or args[:2]==['ip6tables','-S']
            s.ns['fault'](s.generation)
            archive = json.loads(next(s.root.glob('archive-*.json')).read_text())
            self.assertIn('REJECT', archive['counters'])
            self.assertEqual({e['observation'] for e in archive['observation_errors']}, {'ipv6','processes'})
            (s.root/'restore.json').write_text('{bad authoritative journal')
            with self.assertRaises(ValueError): s.restore()
            self.assertFalse(s.permits('10.231.0.1', 'eth0'))

    def test_watcher_retries_transient_lock_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare()
            locked = s.ns['locked']; entered = []
            @contextlib.contextmanager
            def contend_once():
                entered.append(True)
                if len(entered)==1: raise s.ns['LockTimeout']('transient contention')
                with locked(): yield
            s.ns['locked'] = contend_once
            def sleep(_):
                self.assertTrue((s.root/('watch-ready-'+s.generation)).exists())
                (s.root/'cancelled').write_text(s.generation)
            s.ns['time'].sleep = sleep
            s.ns['watch'](s.generation)
            self.assertGreaterEqual(len(entered), 3)
            self.assertEqual(s.ns['phase']()['phase'], 'starting')

    def test_actual_watcher_loss_after_readiness_is_latched_and_rejected_by_health(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory); s.prepare()
            entered, release = threading.Event(), threading.Event()
            def sleep(_):
                entered.set()
                if not release.wait(2): raise RuntimeError('handshake timeout')
            s.ns['time'].sleep = sleep
            thread, errors = s.watcher()
            try:
                self.assertTrue(entered.wait(1))
                self.assertTrue((s.root/('watch-ready-'+s.generation)).exists())
                (s.root/'lease').unlink(); release.set(); thread.join(2)
                self.assertFalse(thread.is_alive()); self.assertIsInstance(errors[0], FileNotFoundError)
                c = trial.Trial(Path(directory)); c.state.update(prepared=True, generation=s.generation)
                with patch.object(trial, 'reserve'), patch.object(trial, 'agent', side_effect=lambda *_a:s.dispatch('status')):
                    with self.assertRaisesRegex(ValueError, 'watcher lost'): c.health(expected_fault=True)
                self.assertEqual(s.ns['phase']()['phase'], 'faulted')
                self.assertFalse(s.permits('10.231.0.1', 'eth0'))
            finally:
                release.set(); thread.join(2)


class C1Tests(unittest.TestCase):
    def test_real_watch_waits_past_old_lock_timeout_for_one_slow_connect_or_deploy_command(self):
        for operation in ('connect', 'deploy'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                c = trial.Trial(Path(directory), approval())
                c.state.update(deadline=DEADLINE, controller_pid=42, controller_identity='controller',
                               server='10.231.0.1', subnet='10.231.0.0/24', a_bridge='172.16.0.1', a_id='retained')
                c.shells = [Mock(), Mock()]
                trial.save(c.state)
                entered, waited, finish = threading.Event(), threading.Event(), threading.Event()
                clock, sleeps, commands, errors = [0.], [0], [], []
                real_sleep = time.sleep
                def sleep(_seconds):
                    sleeps[0] += 1
                    if sleeps[0] == 1:
                        clock[0] = 9.  # The operation is still running beyond the old eight-second wait.
                        return
                    waited.set()
                    if not finish.wait(2): raise RuntimeError('test handshake timeout')
                    real_sleep(.001)
                fake_time = types.SimpleNamespace(monotonic=lambda:clock[0], sleep=sleep, time=time.time)
                def execute(command, **kwargs):
                    owner = trial.OWNERSHIP.current
                    commands.append((command, owner[1], owner[2], kwargs['timeout']))
                    remote_command = command[-1] if command[0]=='gcloud' else ''
                    is_setup = 'setup-server.sh' in remote_command and 'rollback' not in remote_command
                    is_prepare = any(str(arg).endswith('/agent.py') for arg in command) and 'prepare' in command
                    if (operation=='deploy' and is_setup) or (operation=='connect' and is_prepare):
                        entered.set()
                        if not finish.wait(2): raise RuntimeError('command handshake timeout')
                    if command[:2] == ('docker','inspect'): output='[{"Id":"retained"}]'
                    elif 'cat' in command and str(command[-1]).endswith('/cleanup.json'): output='{"status":"PASS","release_at":9}'
                    else: output='{}'
                    return subprocess.CompletedProcess(command, 0, output, '')
                def controller():
                    try:
                        c.connect({}) if operation=='connect' else c.deploy()
                    except Exception as error: errors.append(error)
                def supervisor():
                    try: trial.watch(Path(directory)/'state.json')
                    except Exception as error: errors.append(error)
                with patch.object(trial,'time',fake_time), patch.object(trial,'reserve'), \
                        patch.object(trial,'remaining',return_value=600), patch.object(trial,'process_identity',return_value='controller'), \
                        patch.object(trial.subprocess,'run',side_effect=execute):
                    worker=threading.Thread(target=controller); worker.start()
                    self.assertTrue(entered.wait(1))
                    watcher=threading.Thread(target=supervisor); watcher.start()
                    try:
                        self.assertTrue(waited.wait(1))
                        self.assertTrue((Path(directory)/'cancel-requested.json').exists())
                        self.assertFalse((Path(directory)/'supervisor-result.json').exists())
                    finally:
                        finish.set(); worker.join(3); watcher.join(3)
                self.assertFalse(worker.is_alive() or watcher.is_alive())
                self.assertEqual(len(errors),1)
                self.assertIsInstance(errors[0],ValueError)
                self.assertIn('supervised trial-off',str(errors[0]))
                result=json.loads((Path(directory)/'supervisor-result.json').read_text())
                self.assertEqual(result['cleanup_status'],'PASS')
                self.assertEqual(json.loads((Path(directory)/'cleaned.json').read_text())['status'],'PASS')
                controller_commands=[row for row in commands if not row[1]]
                self.assertEqual(len(controller_commands),1 if operation=='connect' else 2)
                if operation=='deploy': self.assertEqual(controller_commands[-1][3],trial.COMMAND_TIMEOUT)
                teardown_commands=[row for row in commands if row[1]]
                self.assertTrue(teardown_commands)
                self.assertEqual(len({row[2] for row in teardown_commands}),1)  # Latch and off share one budget.
                if operation=='connect': self.assertTrue(any('restore' in row[0] for row in teardown_commands))
                else: self.assertTrue(any('rollback' in row[0][-1] for row in teardown_commands))

    def test_failed_supervisor_or_direct_cleanup_lock_acquisition_records_private_failure(self):
        for lock_name in ('publication.lock','cleanup.lock'):
            for caller in ('watch','cleanup'):
                with self.subTest(lock=lock_name,caller=caller), tempfile.TemporaryDirectory() as directory:
                    private=Path(directory)
                    state=dict(private=directory,deadline=DEADLINE,authorization=approval(),forwards=[],
                               controller_pid=42,controller_identity='controller')
                    trial.save(state)
                    clock=[0.]
                    def sleep(_): clock[0] += 1
                    fake_time=types.SimpleNamespace(monotonic=lambda:clock[0],sleep=sleep,time=time.time)
                    with (private/lock_name).open('a') as held, patch.object(trial,'time',fake_time), \
                            patch.object(trial,'SUPERVISOR_WAIT',.1), patch.object(trial,'remaining',return_value=600), \
                            patch.object(trial,'process_identity',return_value='controller'):
                        fcntl.flock(held,fcntl.LOCK_EX)
                        if caller=='watch':
                            trial.watch(private/'state.json')
                            result=json.loads((private/'supervisor-result.json').read_text())
                            self.assertEqual(result['cleanup_status'],'FAIL')
                        else:
                            self.assertTrue(trial.cleanup(state,explicit_off='expiry'))
                    attempts=list(private.glob('cleanup-attempt-*.json'))
                    self.assertEqual(len(attempts),1)
                    attempt=json.loads(attempts[0].read_text())
                    self.assertEqual(attempt['status'],'FAIL')
                    self.assertIn(lock_name,attempt['errors'][0])
                    self.assertEqual(attempts[0].stat().st_mode & 0o777,0o600)
                    self.assertTrue((private/'cancel-requested.json').exists())
                    self.assertFalse((private/'cleaned.json').exists())

    def test_command_cap_and_post_cancel_boundary_prevent_another_command(self):
        with tempfile.TemporaryDirectory() as directory:
            state=dict(private=directory)
            with trial.lifecycle(state), patch.object(trial.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'ok','')) as execute:
                self.assertEqual(trial.run('first',timeout=360),'ok')
                self.assertEqual(execute.call_args.kwargs['timeout'],trial.COMMAND_TIMEOUT)
                trial.cancel(state,'expiry')
                with self.assertRaisesRegex(ValueError,'supervised trial-off'): trial.run('must-not-start')
                execute.assert_called_once()
            # The same guard after an in-flight command returns also rejects its result.
        with tempfile.TemporaryDirectory() as directory:
            state=dict(private=directory)
            def complete(_command,**_kwargs):
                trial.cancel(state,'expiry')
                return subprocess.CompletedProcess([],0,'late result','')
            with trial.lifecycle(state), patch.object(trial.subprocess,'run',side_effect=complete):
                with self.assertRaisesRegex(ValueError,'supervised trial-off'): trial.run('in-flight')

    def test_shared_teardown_budget_caps_commands_and_preserves_hard_stop_margin(self):
        self.assertLessEqual(2*trial.SUPERVISOR_WAIT+trial.TEARDOWN_BUDGET+20,600)
        with tempfile.TemporaryDirectory() as directory:
            state=dict(private=directory,deadline=DEADLINE)
            clock=[0.]
            fake_time=types.SimpleNamespace(monotonic=lambda:clock[0],sleep=time.sleep,time=time.time)
            with patch.object(trial,'time',fake_time), patch.object(trial,'remaining',return_value=35), \
                    patch.object(trial.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as execute:
                with trial.lifecycle(state,teardown=True):
                    trial.run('teardown',timeout=180)
                    self.assertEqual(execute.call_args.kwargs['timeout'],15)
                    with trial.lifecycle(state,teardown=True):
                        clock[0]=16
                        with self.assertRaisesRegex(TimeoutError,'budget exhausted'): trial.run('too-late')
                    execute.assert_called_once()


class ServerLifecycleTests(unittest.TestCase):
    def sandbox(self, directory):
        base = Path(directory)
        upload, binaries, units = base / "upload", base / "bin", base / "units"
        for path in (upload, binaries, units, base / "var"): path.mkdir()
        (upload / "fixtures.py").write_text("# source-only sandbox\n")
        deadline = int(dt.datetime.fromisoformat(DEADLINE.replace('Z', '+00:00')).timestamp())
        (base / "now").write_text(str(deadline - 1800))
        (upload / 'authorization.json').write_text(json.dumps(approval()))
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
        binary("apt-get", '#!/bin/bash\nexit 99\n')
        binary("dnsmasq", '#!/bin/bash\nexit 0\n')
        binary("systemctl", '#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\np=Path(os.environ["SANDBOX"])/"systemctl.log"\nwith p.open("a") as f: f.write(" ".join(sys.argv[1:])+"\\n")\nsys.exit(3 if sys.argv[1]=="is-active" else 0)\n')
        binary("dpkg-query", '#!/bin/bash\nexit 0\n')
        binary("openssl", '#!/usr/bin/python3\nimport os,sys,time\nfrom pathlib import Path\np=Path(os.environ["SANDBOX"]); (p/"openssl-entered").touch()\nwhile not (p/"openssl-release").exists(): time.sleep(.02)\nfor i,a in enumerate(sys.argv):\n if a in ("-out","-keyout"): Path(sys.argv[i+1]).write_text("sandbox\\n")\n')
        binary("openvpn", '#!/usr/bin/python3\nimport sys\nfrom pathlib import Path\nPath(sys.argv[-1]).write_text("sandbox\\n")\n')
        binary("ip", '#!/bin/bash\nprintf "inet 10.231.0.1/24\\n"\n')
        command = ["bash", str(script), "cvpn0123456789ab", "10.231.0.0/24", DEADLINE,
                   "172.16.0.33", "20990", "0" * 32]
        environment = dict(os.environ, PATH=str(binaries) + ":" + os.environ["PATH"], SANDBOX=str(base))
        return base, command, environment, deadline

    def wait_for(self, path, process):
        for _ in range(200):
            if path.exists(): return
            if process.poll() is not None: break
            time.sleep(.01)
        self.fail("sandbox setup did not reach handshake")

    def test_failed_server_stop_retains_unit_definition_for_explicit_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, _ = self.sandbox(directory)
            unit = base / 'units/ld01-cvpn0123456789ab-vpn.service'; unit.write_text('retained definition')
            marker = base / 'fail-stop'; marker.touch()
            (base / 'bin/systemctl').write_text('#!/usr/bin/python3\nimport os,sys\nfrom pathlib import Path\nsys.exit(1 if sys.argv[1]=="stop" and (Path(os.environ["SANDBOX"])/"fail-stop").exists() else 3 if sys.argv[1]=="is-active" else 0)\n')
            first = subprocess.run([*command, 'rollback'], env=environment, capture_output=True, timeout=3)
            self.assertNotEqual(first.returncode, 0)
            self.assertEqual(unit.read_text(), 'retained definition')
            marker.unlink()
            second = subprocess.run([*command, 'rollback'], env=environment, capture_output=True, timeout=3)
            self.assertEqual(second.returncode, 0)
            self.assertFalse(unit.exists())

    def test_rollback_cancels_waits_for_setup_and_prevents_late_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, _ = self.sandbox(directory)
            setup = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rollback = None
            try:
                self.wait_for(base / "openssl-entered", setup)
                rollback = subprocess.Popen([*command, "rollback"], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.wait_for(base / "upload/cancelled", rollback)
                self.assertIsNone(rollback.poll())
                (base / "openssl-release").touch()
                self.assertNotEqual(setup.wait(timeout=5), 0)
                self.assertEqual(rollback.wait(timeout=5), 0)
                self.assertNotIn("start ", (base / "systemctl.log").read_text())
                late = subprocess.run(command, env=environment, capture_output=True, timeout=3)
                self.assertNotEqual(late.returncode, 0)
                self.assertFalse(list((base / "units").iterdir()))
            finally:
                (base / "openssl-release").touch()
                for process in (setup, rollback):
                    if process is not None:
                        if process.poll() is None: process.kill()
                        process.wait(timeout=3)

    def test_setup_rechecks_reserve_after_pki_before_units_without_package_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, deadline = self.sandbox(directory)
            setup = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                self.wait_for(base / "openssl-entered", setup)
                (base / "now").write_text(str(deadline - 100))
                (base / "openssl-release").touch()
                self.assertNotEqual(setup.wait(timeout=5), 0)
                self.assertFalse(list((base / "units").iterdir()))
                self.assertNotIn("start ", (base / "systemctl.log").read_text())
            finally:
                if setup.poll() is None: setup.kill()
                setup.wait(timeout=3)

    def test_server_side_timeout_bounds_entire_setup_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            base, command, environment, deadline = self.sandbox(directory)
            (base / "now").write_text(str(deadline - 601))
            started = time.monotonic()
            result = subprocess.run(command, env=environment, capture_output=True, timeout=8)
            self.assertEqual(result.returncode, 124)
            self.assertLess(time.monotonic() - started, 7)
            rollback = subprocess.run([*command, "rollback"], env=environment, capture_output=True, timeout=3)
            self.assertEqual(rollback.returncode, 0)


class DetachedCaptureTests(unittest.TestCase):
    @contextlib.contextmanager
    def capture_worker(self, mode='normal', expiry=30, clock_rollback=False):
        """Real registration/gate/stop worker; substitute ordinary Python for sudo/tcpdump."""
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), approval())
            c.state.update(veth='vethA', a_ip='172.16.0.2', a_bridge='172.16.0.1',
                           subnet='10.231.0.0/24', deadline=(trial.utc() + dt.timedelta(seconds=600 + expiry)).isoformat())
            code = r'''
import os,pathlib,signal,sys,time
def done(*_):
    if sys.argv[1]=='exec-on-interrupt': os.execv(sys.executable,[sys.executable,'-c','import time; time.sleep(60)'])
    print('1 packet captured\n1 packet received by filter\n0 packets dropped by kernel',file=sys.stderr,flush=True)
    sys.exit(7 if sys.argv[1]=='bad-exit' else 0)
signal.signal(signal.SIGINT,signal.SIG_IGN if sys.argv[1]=='ignore' else done)
print('100.000000 IP 172.16.0.2.45000 > 172.16.0.1.20992: tcp 10',flush=True)
print('tcpdump: listening on vethA',file=sys.stderr,flush=True)
if sys.argv[1]=='exec-drift': os.execv(sys.executable,[sys.executable,'-c','import time; time.sleep(60)'])
if sys.argv[1]=='premature':
    while not pathlib.Path(sys.argv[2]).exists(): time.sleep(.01)
    done()
time.sleep(60)
'''
            popen = subprocess.Popen
            def ordinary_worker(command, **kwargs):
                self.assertEqual(command[:6], ['sudo', '-n', 'python3', '-u', '-c', trial.CAPTURE])
                worker = trial.CAPTURE
                if clock_rollback:
                    worker = '''import sys,time,types
real=time.time; start=time.monotonic()
clock=types.ModuleType('time'); clock.__dict__.update(time.__dict__)
clock.time=lambda: real()-(3600 if time.monotonic()-start>.2 else 0)
sys.modules['time']=clock
exec(%r)
''' % worker
                return popen([sys.executable, '-u', '-c', worker, command[6], command[7],
                              sys.executable, '-u', '-c', code, mode, str(c.private / 'premature'), *command[8:]], **kwargs)
            with patch.object(trial, 'reserve'), patch.object(c, 'check_veth'), \
                    patch.object(trial.subprocess, 'Popen', side_effect=ordinary_worker):
                c.start_capture()
            try:
                yield c
            finally:
                # Only this disposable ordinary-user worker/child, never a retained resource.
                Path(c.state['capture']['stop_request']).touch(exist_ok=True)
                try: c.capture_process.wait(timeout=9)
                except subprocess.TimeoutExpired:
                    record = c.state['capture']
                    if trial.process_identity(record['pid']) == record['identity']:
                        os.kill(record['pid'], signal.SIGKILL)
                    c.capture_process.kill(); c.capture_process.wait(timeout=3)
                record = c.state['capture']
                if trial.process_identity(record['pid']) == record['identity']:
                    os.kill(record['pid'], signal.SIGKILL)

    def test_real_start_stop_is_registered_private_and_never_reauthenticates(self):
        with self.capture_worker() as c, patch.object(trial, 'run', side_effect=AssertionError('sudo/external command forbidden')):
            record = c.state['capture']
            self.assertFalse(Path(record['stop_request']).exists())
            result = trial.stop_capture(c.state)
            self.assertEqual(result['captured'], 1)
            self.assertEqual(c.capture_process.wait(timeout=2), 0)
            self.assertIsNone(trial.process_identity(record['pid']))
            self.assertEqual(Path(record['stop_request']).stat().st_mode & 0o777, 0o600)
            self.assertEqual(result['source']['command'], record['command'])
            self.assertEqual(trial.stop_capture(c.state)['dropped'], 0)  # Same completed stop is idempotent.

    def test_other_attempt_stop_does_not_interrupt_this_capture(self):
        with self.capture_worker() as c:
            (c.private / 'capture-other.stop').touch()
            time.sleep(.15)
            self.assertIsNone(c.capture_process.poll())
            self.assertIsNotNone(trial.process_identity(c.state['capture']['pid']))
            self.assertEqual(trial.stop_capture(c.state)['received'], 1)

    def test_wrong_registration_specification_and_path_never_request_or_signal(self):
        with self.capture_worker() as c:
            original = copy.deepcopy(c.state)
            cases = [('pid', 1), ('identity', 'wrong'), ('worker_identity', 'wrong'),
                     ('command', ['unrelated']), ('stop_request', str(c.private / 'other.stop'))]
            for field, value in cases:
                state = copy.deepcopy(original); state['capture'][field] = value
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'registration'):
                    trial.stop_capture_owned(state)
            for field in ('veth',):
                state = copy.deepcopy(original); state[field] = 'wrong'
                with self.assertRaisesRegex(ValueError, 'specification'): trial.stop_capture_owned(state)
            self.assertFalse(Path(original['capture']['stop_request']).exists())
            self.assertIsNone(c.capture_process.poll())

    def test_worker_refuses_to_signal_child_whose_command_changed(self):
        with self.capture_worker('exec-drift') as c:
            with self.assertRaisesRegex(ValueError, 'capture did not stop'):
                trial.stop_capture(c.state)
            self.assertNotEqual(c.capture_process.wait(timeout=2), 0)
            self.assertIsNotNone(trial.process_identity(c.state['capture']['pid']))
            self.assertIn('identity/specification mismatch', Path(c.state['capture']['stderr']).read_text())

    def test_wrapper_interrupt_retires_matching_child_without_claiming_success(self):
        with self.capture_worker() as c:
            os.kill(c.state['capture']['worker_pid'], signal.SIGINT)
            self.assertNotEqual(c.capture_process.wait(timeout=8), 0)
            self.assertIsNone(trial.process_identity(c.state['capture']['pid']))
            with self.assertRaisesRegex(ValueError, 'completion'): trial.stop_capture(c.state)

    def test_escalation_rechecks_command_after_interrupt_handler_exec(self):
        with self.capture_worker('exec-on-interrupt') as c:
            with self.assertRaisesRegex(ValueError, 'capture did not stop'): trial.stop_capture(c.state)
            self.assertIsNotNone(trial.process_identity(c.state['capture']['pid']))
            self.assertNotEqual(c.capture_process.wait(timeout=2), 0)
            self.assertIn('identity/specification mismatch', Path(c.state['capture']['stderr']).read_text())

    def test_clock_rollback_cannot_extend_initial_expiry_budget(self):
        with self.capture_worker(expiry=.5, clock_rollback=True) as c:
            self.assertNotEqual(c.capture_process.wait(timeout=3), 0)
            self.assertIsNone(trial.process_identity(c.state['capture']['pid']))
            with self.assertRaisesRegex(ValueError, 'completion'): trial.stop_capture(c.state)

    def test_worker_rejects_unsafe_marker_instead_of_certifying_requested_stop(self):
        for kind in ('symlink', 'directory', 'public'):
            with self.subTest(kind=kind), self.capture_worker() as c:
                marker = Path(c.state['capture']['stop_request'])
                if kind == 'symlink': marker.symlink_to(c.private / 'absent')
                elif kind == 'directory': marker.mkdir()
                else: marker.write_text('unsafe'); marker.chmod(0o644)
                try:
                    self.assertNotEqual(c.capture_process.wait(timeout=8), 0)
                    self.assertIsNone(trial.process_identity(c.state['capture']['pid']))
                    self.assertIn('must be a private file', Path(c.state['capture']['stderr']).read_text())
                finally:
                    if marker.is_dir(): marker.rmdir()
                    else: marker.unlink()

    def test_completed_stop_rejects_unsafe_endpoint_at_the_path_guard(self):
        with self.capture_worker() as c:
            trial.stop_capture(c.state); c.capture_process.wait(timeout=2)
            marker = Path(c.state['capture']['stop_request'])
            for kind in ('symlink', 'directory', 'public'):
                marker.unlink()
                if kind == 'symlink': marker.symlink_to(c.private / 'absent')
                elif kind == 'directory': marker.mkdir()
                else: marker.write_text('unsafe'); marker.chmod(0o644)
                with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'stop path|private file'):
                    trial.stop_capture(c.state)
                if marker.is_dir(): marker.rmdir()
                else: marker.unlink()
                trial.private_write(marker, 'restored')
            state = copy.deepcopy(c.state)
            state['capture']['stop_request'] = str(c.private / 'wrong.stop')
            headers = Path(state['capture']['stdout']); lines = headers.read_text().splitlines()
            registration = json.loads(lines[0]); registration['stop_request'] = state['capture']['stop_request']
            lines[0] = json.dumps(registration); headers.write_text('\n'.join(lines) + '\n')
            with self.assertRaisesRegex(ValueError, 'stop path mismatch'): trial.stop_capture_owned(state)

    def test_completion_receipt_is_bound_to_every_registered_field(self):
        with self.capture_worker() as c:
            trial.stop_capture(c.state); c.capture_process.wait(timeout=2)
            path = Path(c.state['capture']['stderr']); text = path.read_text()
            prefix, receipt_text = text.rsplit('capture-result: ', 1)
            receipt = json.loads(receipt_text)
            for key in ('pid', 'identity', 'stop_request', 'command', 'worker_pid', 'worker_identity', 'signalled'):
                wrong = dict(receipt); wrong[key] = False if key == 'signalled' else ['wrong'] if key == 'command' else 'wrong'
                path.write_text(prefix + 'capture-result: ' + json.dumps(wrong) + '\n')
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'completion'):
                    trial.stop_capture(c.state)
            path.write_text(text)

    def test_gate_not_yet_execed_is_retired_on_stop_or_expiry(self):
        for request in (False, True):
            with self.subTest(request=request), tempfile.TemporaryDirectory() as directory:
                private = Path(directory); stop = private / 'capture.stop'; marker = private / 'executed'
                code = 'import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(60)'
                process = subprocess.Popen([sys.executable, '-u', '-c', trial.CAPTURE, str(time.time()+.5), str(stop),
                                            sys.executable, '-c', code, str(marker)],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                registration = json.loads(process.stdout.readline())
                try:
                    os.kill(registration['pid'], signal.SIGSTOP)
                    if request: trial.private_write(stop, 'stop')
                    output, error = process.communicate(b'G', timeout=4)
                    self.assertNotEqual(process.returncode, 0, error)
                    self.assertFalse(marker.exists())
                    self.assertIsNone(trial.process_identity(registration['pid']))
                finally:
                    if trial.process_identity(registration['pid']) == registration['identity']:
                        os.kill(registration['pid'], signal.SIGKILL)
                    if process.poll() is None: process.kill()
                    process.communicate(timeout=3)

    def test_exit_between_request_poll_and_signal_is_premature_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            stop = Path(directory) / 'capture.stop'; trial.private_write(stop, 'stop')
            p = Mock(pid=os.getpid(), returncode=None)
            def poll():
                value = next(values, 0)
                p.returncode = value
                return value
            values = iter((None, 0))
            p.poll.side_effect = poll
            output, error = io.StringIO(), io.StringIO()
            with patch.object(sys, 'argv', ['capture', str(time.time()+30), str(stop), 'synthetic']), \
                    patch.object(trial.subprocess, 'Popen', return_value=p), \
                    patch('select.select', return_value=([sys.stdin], [], [])), \
                    patch.object(os, 'read', return_value=b'G'), \
                    patch.object(os.path, 'lexists', side_effect=(False, True)), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                with self.assertRaises(SystemExit) as result: exec(trial.CAPTURE, {})
            self.assertEqual(result.exception.code, 1)
            p.send_signal.assert_not_called()
            completion = json.loads(error.getvalue().split('capture-result: ', 1)[1])
            self.assertEqual(completion['reason'], 'premature')
            self.assertFalse(completion['signalled'])

    def test_premature_exit_bad_exit_missing_completion_and_expiry_fail(self):
        for mode, expiry in (('premature', 30), ('bad-exit', 30), ('normal', .4)):
            with self.subTest(mode=mode, expiry=expiry), self.capture_worker(mode, expiry) as c:
                if mode == 'premature': (c.private / 'premature').touch()
                if mode == 'premature' or expiry < 1: c.capture_process.wait(timeout=3)
                with self.assertRaisesRegex(ValueError, 'completion'):
                    trial.stop_capture(c.state)
                self.assertIsNone(trial.process_identity(c.state['capture']['pid']))
        with self.capture_worker() as c:
            trial.stop_capture(c.state); c.capture_process.wait(timeout=2)
            path = Path(c.state['capture']['stderr'])
            path.write_text('\n'.join(line for line in path.read_text().splitlines() if not line.startswith('capture-result: ')) + '\n')
            with self.assertRaisesRegex(ValueError, 'completion'): trial.stop_capture(c.state)

    def test_ignored_interrupt_is_bounded_and_never_passes(self):
        with self.capture_worker('ignore') as c:
            start = time.monotonic()
            with self.assertRaisesRegex(ValueError, 'completion'): trial.stop_capture(c.state)
            self.assertLess(time.monotonic() - start, 9)
            self.assertNotEqual(c.capture_process.wait(timeout=2), 0)
            self.assertIsNone(trial.process_identity(c.state['capture']['pid']))

    def test_detached_real_supervisor_reloads_after_controller_loss_without_sudo(self):
        with self.capture_worker() as c:
            # Model an already-dead controller using a real disposable process identity.
            dead = subprocess.Popen([sys.executable, '-c', 'pass'])
            identity = trial.process_identity(dead.pid)
            dead.wait(timeout=3)
            c.state.update(controller_pid=dead.pid, controller_identity=identity)
            trial.save(c.state)
            script = '''
import pathlib,sys
import trial
def denied(*args,**kwargs): raise AssertionError('sudo/external command unavailable in detached supervisor')
trial.run=denied
trial.watch(pathlib.Path(sys.argv[1]))
'''
            env = dict(os.environ, PYTHONPATH=str(trial.HERE), PYTHONDONTWRITEBYTECODE='1')
            supervisor = subprocess.run([sys.executable, '-c', script, str(c.private / 'state.json')],
                                        env=env, start_new_session=True, capture_output=True, text=True, timeout=15)
            self.assertEqual(supervisor.returncode, 0, supervisor.stderr)
            self.assertEqual(json.loads((c.private / 'cleaned.json').read_text())['status'], 'PASS')
            result = json.loads((c.private / 'supervisor-result.json').read_text())
            self.assertEqual(result['campaign_status'], 'FAIL')  # Controller loss is still a campaign failure.
            self.assertEqual(result['cleanup_status'], 'PASS')
            self.assertEqual(result['cleanup_errors'], [])
            self.assertEqual(c.capture_process.wait(timeout=2), 0)
            self.assertIsNone(trial.process_identity(c.state['capture']['pid']))

    def test_capture_survives_actual_controller_kill_then_detached_watch_cleans(self):
        script = '''
import signal
from test_trial import DetachedCaptureTests
with DetachedCaptureTests().capture_worker(expiry=60) as c:
    print(c.private,flush=True)
    signal.pause()
'''
        env = dict(os.environ, PYTHONPATH=str(trial.HERE), PYTHONDONTWRITEBYTECODE='1')
        controller = subprocess.Popen([sys.executable, '-u', '-c', script], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        private = None; state = None
        try:
            private = Path(controller.stdout.readline().strip())
            state = json.loads((private / 'state.json').read_text())
            controller.kill(); controller.communicate(timeout=3)
            self.assertIsNotNone(trial.process_identity(state['capture']['pid']))
            supervisor_code = '''
import pathlib,sys,trial
def denied(*a,**kw): raise AssertionError('detached sudo forbidden')
trial.run=denied
trial.watch(pathlib.Path(sys.argv[1]))
'''
            result = subprocess.run([sys.executable, '-c', supervisor_code, str(private / 'state.json')],
                                    env=env, start_new_session=True, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((private / 'supervisor-result.json').read_text())['cleanup_status'], 'PASS')
            self.assertEqual(json.loads((private / 'cleaned.json').read_text())['errors'], [])
            self.assertIsNone(trial.process_identity(state['capture']['pid']))
        finally:
            if controller.poll() is None: controller.kill()
            controller.communicate(timeout=3)
            if state:
                record = state['capture']
                Path(record['stop_request']).touch(exist_ok=True)
                for _ in range(30):
                    if trial.process_identity(record['worker_pid']) != record['worker_identity']: break
                    time.sleep(.1)
                for key, identity_key in (('pid', 'identity'), ('worker_pid', 'worker_identity')):
                    if trial.process_identity(record[key]) == record[identity_key]: os.kill(record[key], signal.SIGKILL)
            if private and private.is_dir():
                import shutil
                shutil.rmtree(private)

    def test_sudo_admission_failure_precedes_any_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), approval())
            with patch.object(trial, 'reserve'), patch.object(trial, 'run', side_effect=RuntimeError('sudo unavailable')) as run:
                with self.assertRaisesRegex(RuntimeError, 'sudo unavailable'): c.preflight()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[:4], ('sudo', '-n', 'python3', '-c'))
            self.assertNotIn('deployed', c.state)

    def test_submitted_admission_predicate_rejects_nonroot_and_missing_tool(self):
        for uid, tool in ((1001, '/tool/tcpdump'), (0, None), (0, '/tool/tcpdump')):
            with self.subTest(uid=uid, tool=tool), tempfile.TemporaryDirectory() as directory:
                c = trial.Trial(Path(directory), approval()); results = []
                def run(*args, **kwargs):
                    if args[0] != 'sudo': return 'wrong-branch'
                    harness = 'import os,shutil,sys; os.geteuid=lambda: int(sys.argv[1]); shutil.which=lambda _: sys.argv[2] or None; exec(sys.argv[3])'
                    result = subprocess.run([sys.executable, '-c', harness, str(uid), tool or '', args[-1]], capture_output=True)
                    results.append(result.returncode)
                    if result.returncode: raise RuntimeError('predicate refused')
                    return ''
                with patch.object(trial, 'reserve'), patch.object(trial, 'run', side_effect=run):
                    if uid == 0 and tool:
                        with self.assertRaisesRegex(ValueError, 'wrong worktree branch'): c.preflight()
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'predicate refused'): c.preflight()
                self.assertEqual(results, [0 if uid == 0 and tool else 1])


class LiveFailureRegressionTests(unittest.TestCase):
    def test_tcpdump_shutdown_blank_separator_is_not_a_packet_or_hidden_header(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'headers'
            header = '100.000000 IP 172.16.0.2.45000 > 172.16.0.1.20992: tcp 10\n'
            path.write_text('{"pid":42}\n' + header + '\n')
            self.assertEqual(trial.capture_rows(path), [(100., '172.16.0.2', 45000, '172.16.0.1', 20992)])
            path.write_text(path.read_text() + 'unexpected nonempty record\n')
            with self.assertRaisesRegex(ValueError, 'unparsed capture header'):
                trial.capture_rows(path)

    def test_exited_shell_retains_private_stderr_without_exposing_it_in_error(self):
        with tempfile.TemporaryDirectory() as directory:
            shell = trial.Shell.__new__(trial.Shell)
            shell.private = Path(directory)
            shell.process = subprocess.Popen([sys.executable, '-u', '-c',
                'import sys; sys.stdin.readline(); raise ValueError("synthetic baseline cause")'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                with self.assertRaisesRegex(ValueError, 'private shell-failure diagnostics') as caught:
                    shell.request('baseline_probe')
                self.assertNotIn('synthetic baseline cause', str(caught.exception))
                paths = list(Path(directory).glob('shell-failure-*.json'))
                self.assertEqual(len(paths), 1)
                result = json.loads(paths[0].read_text())
                self.assertIn('synthetic baseline cause', result['stderr'])
                self.assertEqual(result['action'], 'baseline_probe')
                self.assertNotEqual(result['exit'], 0)
                self.assertEqual(paths[0].stat().st_mode & 0o777, 0o600)
            finally:
                if shell.process.poll() is None: shell.process.kill()
                shell.process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
