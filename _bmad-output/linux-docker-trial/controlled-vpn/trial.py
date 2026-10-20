"""One approved LD01 controlled trial. Secrets and evidence never enter the worktree.

Run: python3 trial.py --private-dir /tmp/opencode/controlled-vpn-UNUSED
The approval deadline is fixed, including cleanup; reruns do not extend it.
"""

import argparse
import datetime as dt
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

HERE = Path(__file__).resolve().parent
BASELINE = Path("/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM")
A, B = "tvm-share-ld01-a", "tvm-share-ld01-b"
DEADLINE = "2026-10-20T10:31:09Z"
LABELS = {"task": "linux-docker-sharing-trial", "trial": "ld01",
          "owner": "opencode-linux-trial-preparation"}


def check(value, message):
    if not value:
        raise ValueError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc)


def remaining(now=None):
    return (dt.datetime.fromisoformat(DEADLINE.replace("Z", "+00:00")) - (now or utc())).total_seconds()


def reserve(seconds=600):
    check(remaining() > seconds, "approval expired or cleanup reserve reached")


def check_ports(bindings):
    for host, port in bindings:
        with socket.socket() as sock:
            sock.bind((host, port))


def run(*command, data=None, timeout=30):
    result = subprocess.run(command, input=data, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        # Do not include stdin, profile material or command output in exceptions.
        raise RuntimeError(f"{command[0]} failed (exit {result.returncode})")
    return result.stdout


def inside(container, *command, data=None, root=False):
    return run("docker", "exec", "-i", *(('--user', '0') if root else ()),
               container, *command, data=data)


def remote(command, data=None, timeout=60):
    return run("gcloud", "compute", "ssh", "free-vm", "--tunnel-through-iap", "--quiet",
               "--ssh-flag=-oControlMaster=no", "--ssh-flag=-oControlPath=none",
               "--command=" + command, data=data, timeout=timeout)


def private_write(path, value):
    with open(path, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        stream.write(value)


def save(state):
    path = Path(state["private"]) / "state.json"
    temporary = path.with_suffix(".new")
    with open(temporary, "w", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
        json.dump(state, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def mounts(obj):
    return {m["Destination"]: m for m in obj["Mounts"]}


def reconcile(objects, resources, baseline, image):
    """Reject drift before any runtime mutation; mount array ordering is irrelevant."""
    ids = {r["name"]: r.get("id") for r in resources["resources"]}
    check({o["Name"].lstrip("/") for o in objects} == {A, B}, "container selection mismatch")
    for obj in objects:
        name = obj["Name"].lstrip("/")
        old = baseline["checks"][name]
        host, config = obj["HostConfig"], obj["Config"]
        check(obj["Id"] == ids[name] == old["id"], f"{name}: identity drift")
        check(obj["Image"] == image == resources["image"], f"{name}: image drift")
        check(obj["State"]["Running"] and not obj["State"]["Paused"], f"{name}: inactive")
        check(config["User"] == "1001:1001", f"{name}: daily identity drift")
        check(all(config["Labels"].get(k) == v for k, v in LABELS.items()), "ownership drift")
        check(mounts(obj) == {m["Destination"]: m for m in old["mounts"]}, "mount drift")
        for key, value in old["runtime_config"].items():
            check(host[key] == value, f"{name}: {key} drift")
        check(host["CapAdd"] == old["cap_add"] and host["Devices"] == old["devices"], "capability/device drift")
        network = "tvm-share-ld01-net-" + name[-1]
        check(set(obj["NetworkSettings"]["Networks"]) == {network}, "network attachment drift")
        check(obj["NetworkSettings"]["Networks"][network]["NetworkID"] == ids[network], "network identity drift")
        check(config["Cmd"] == ["sleep", "infinity"] and config["Entrypoint"] is None, "entrypoint drift")
        check(config["WorkingDir"] == "/project" and config["Env"] == [
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "HOME=/home/session"], "environment drift")
        check(not any(host.get(k) for k in ("Binds", "PortBindings", "Sysctls", "Dns", "DnsOptions",
                                           "DnsSearch", "Links", "GroupAdd")), "extra runtime configuration")
        check(not host["VolumesFrom"] and not host["DeviceRequests"] and not host["ExtraHosts"], "unexpected attachment")


def canonical(value):
    if isinstance(value, list):
        return sorted((canonical(x) for x in value), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, dict):
        # RA countdown is not a route change. All destinations/interfaces/metrics remain compared.
        return {k: canonical(v) for k, v in value.items() if k != "expires"}
    return value


def snapshot(container=None):
    execute = (lambda *cmd: inside(container, *cmd)) if container else run
    out = {}
    for family in ("-4", "-6"):
        for kind in ("route", "rule"):
            command = ["ip", family, "-j", kind, "show"]
            if kind == "route":
                command += ["table", "all"]
            out[family + kind] = canonical(json.loads(execute(*command)))
    out["resolver"] = execute("python3", "-c", "import base64; print(base64.b64encode(open('/etc/resolv.conf','rb').read()).decode())").strip()
    if not container:
        out["dns"] = execute("resolvectl", "dns")
        out["domains"] = execute("resolvectl", "domain")
        out["active_connections"] = execute("nmcli", "-t", "-f", "TYPE,STATE", "connection", "show", "--active")
    return out


# This root-only agent lives in A's private /run directory. It has only the retained
# NET_ADMIN capability, no host sockets/mounts. Its watchdog also handles controller loss.
AGENT = r'''
import base64, contextlib, datetime, fcntl, json, os, pathlib, shutil, signal, subprocess, sys, time, uuid
os.umask(0o077)
root = pathlib.Path(sys.argv[1])
chain = 'LDC' + root.name[-12:]
DEADLINE = '2026-10-20T10:31:09Z'
def atomic(name, value):
    path=root/name; temporary=path.with_suffix('.new')
    temporary.write_text(value); os.replace(temporary,path)
@contextlib.contextmanager
def locked():
    with open(root/'lifecycle.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        yield
def identity(pid):
    try:
        fields=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except FileNotFoundError: return None
def reserve():
    end=datetime.datetime.fromisoformat(DEADLINE.replace('Z','+00:00')).timestamp()
    if time.time() >= end-180: raise RuntimeError('cleanup reserve reached')
def active(generation):
    return (root/'active').exists() and (root/'active').read_text()==generation
def cancelled(generation):
    return (root/'cancelled').exists() and (root/'cancelled').read_text()==generation
def require_active(generation):
    reserve()
    if not active(generation) or cancelled(generation):
        raise RuntimeError('cancelled or obsolete generation')
def cmd(*args, required=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=2)
    if required and p.returncode: raise RuntimeError(args[0] + ' failed')
    return p
def state():
    return dict(resolver=base64.b64encode(pathlib.Path('/etc/resolv.conf').read_bytes()).decode(),
        ipv4=cmd('iptables','-S').stdout, ipv6=cmd('ip6tables','-S').stdout,
        nat=cmd('iptables','-t','nat','-S').stdout,
        sysctl={p.parent.name:p.read_text() for p in pathlib.Path('/proc/sys/net/ipv6/conf').glob('*/disable_ipv6')})
def prepare(generation, server):
    with locked():
        reserve()
        if (root/'active').exists(): raise RuntimeError('previous generation still active')
        if (root/'restore.json').exists() and json.loads((root/'cleanup.json').read_text())['status']!='PASS':
            raise RuntimeError('previous restoration failed')
        old=state(); old.update(server=server,generation=generation)
        atomic('restore.json',json.dumps(old)); atomic('active',generation)
        atomic('lease',generation)
        for name in ('vpn.pid','vpn.log'): (root/name).unlink(missing_ok=True)
        (root/('watch-pending-'+generation)).touch()
        return old
def block(generation):
    with locked():
        require_active(generation)
        server=json.loads((root/'restore.json').read_text())['server']
        cmd('ip6tables','-N',chain); cmd('ip6tables','-A',chain,'-j','DROP')
        for hook in ('INPUT','OUTPUT','FORWARD'): cmd('ip6tables','-I',hook,'1','-j',chain)
        cmd('iptables','-N',chain)
        # conntrack retains the pre-DNAT address/port, including Docker's high-port DNS mapping.
        for proto in ('udp','tcp'):
            cmd('iptables','-A',chain,'-p',proto,'-m','conntrack','--ctdir','ORIGINAL',
                '--ctorigdstport','53','!','--ctorigdst',server,'-j','REJECT')
        cmd('iptables','-I','OUTPUT','1','-j',chain)
        pathlib.Path('/etc/resolv.conf').write_text('nameserver '+server+'\noptions timeout:2 attempts:1\n')
def spawn(command, journal):
    gate="import os,sys; token=sys.stdin.buffer.read(1); sys.exit(1) if token!=b'G' else os.execvp(sys.argv[1],sys.argv[1:])"
    with open(root/(journal+'.log'),'ab') as log:
        process=subprocess.Popen([sys.executable,'-c',gate,*command],stdin=subprocess.PIPE,
                                 stdout=log,stderr=log,start_new_session=True)
    try:
        identifier=identity(process.pid)
        if identifier is None: raise RuntimeError('gated child exited before registration')
        atomic(journal,json.dumps(dict(pid=process.pid,identity=identifier)))
        process.stdin.write(b'G'); process.stdin.flush()
    finally: process.stdin.close()
def start(generation, command=None):
    with locked():
        require_active(generation)
        spawn(command or ['openvpn','--config',str(root/'client.ovpn'),'--log',str(root/'vpn.log')],'vpn.pid')
def launch_watch(generation):
    with locked():
        require_active(generation)
        spawn([sys.executable,str(root/'agent.py'),str(root),'watch',generation],'watch-pid-'+generation+'.json')
def stop_daemon():
    if not (root/'vpn.pid').exists(): return
    record=json.loads((root/'vpn.pid').read_text()); pid=record['pid']
    if identity(pid) != record['identity']: return
    if str(root/'client.ovpn').encode() not in pathlib.Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0'):
        raise RuntimeError('daemon PID identity mismatch')
    os.kill(pid,signal.SIGTERM)
    for _ in range(40):
        if identity(pid) != record['identity']: return
        time.sleep(.1)
    os.kill(pid,signal.SIGKILL)
    for _ in range(20):
        if identity(pid) != record['identity']: return
        time.sleep(.1)
    raise RuntimeError('daemon did not exit')
def restore_locked(generation=None):
    if not (root/'restore.json').exists():
        if (root/'active').exists(): raise RuntimeError('missing restoration journal')
        atomic('cleanup.json',json.dumps(dict(status='PASS',errors=[],generation=None)))
        return
    old=json.loads((root/'restore.json').read_text())
    if generation is not None and generation!=old['generation']: return
    generation=old['generation']; atomic('cancelled',generation); failures=[]
    def attempt(fn):
        try: fn()
        except Exception as e: failures.append(type(e).__name__ + ': ' + str(e))
    attempt(stop_daemon)
    # A crashed daemon normally removes its own TUN. Delete only our checked name.
    if pathlib.Path('/sys/class/net/ld01tun').exists():
        attempt(lambda: cmd('ip','link','delete','dev','ld01tun'))
    def remove_rule(tool, hook, rule):
        present=None
        def inspect():
            nonlocal present
            present=cmd(tool,'-C',hook,*rule,required=False).returncode==0
        attempt(inspect)
        if present is not False:
            attempt(lambda: cmd(tool,'-D',hook,*rule))
    for tool, hooks in [('ip6tables',('INPUT','OUTPUT','FORWARD')),('iptables',('OUTPUT',))]:
        for hook in hooks:
            remove_rule(tool,hook,['-j',chain])
        present=None
        def inspect_chain():
            nonlocal present
            present=cmd(tool,'-S',chain,required=False).returncode==0
        attempt(inspect_chain)
        if present is not False:
            rules=[['-j','DROP']] if tool=='ip6tables' else [
                ['-p',p,'-m','conntrack','--ctdir','ORIGINAL','--ctorigdstport','53',
                 '!','--ctorigdst',old['server'],'-j','REJECT'] for p in ('udp','tcp')]
            for rule in rules:
                remove_rule(tool,chain,rule)
            attempt(lambda t=tool: cmd(t,'-X',chain))
    attempt(lambda: pathlib.Path('/etc/resolv.conf').write_bytes(base64.b64decode(old['resolver'])))
    def equal(actual, expected):
        if actual != expected: raise RuntimeError('restoration mismatch')
    attempt(lambda: equal(base64.b64encode(pathlib.Path('/etc/resolv.conf').read_bytes()).decode(),old['resolver']))
    for key,command in [('ipv4',['iptables','-S']),('ipv6',['ip6tables','-S']),('nat',['iptables','-t','nat','-S'])]:
        attempt(lambda k=key,c=command: equal(cmd(*c).stdout,old[k]))
    attempt(lambda: equal({p.parent.name:p.read_text() for p in pathlib.Path('/proc/sys/net/ipv6/conf').glob('*/disable_ipv6')},old['sysctl']))
    result=json.dumps(dict(status='FAIL' if failures else 'PASS',errors=failures,generation=generation))
    (root/('cleanup-attempt-'+uuid.uuid4().hex+'.json')).write_text(result)
    atomic('cleanup.json',result)
    if not failures: (root/'active').unlink(missing_ok=True)
    if failures: raise RuntimeError('; '.join(failures))
def restore(generation=None):
    with locked(): restore_locked(generation)
def renew(generation):
    with locked():
        require_active(generation); atomic('lease',generation)
def watch(generation):
    try:
        while True:
            with locked():
                if not active(generation) or cancelled(generation): return
                stale=time.time()-(root/'lease').stat().st_mtime>20
                record=json.loads((root/'vpn.pid').read_text()) if (root/'vpn.pid').exists() else None
                exited=record is not None and identity(record['pid'])!=record['identity']
                try: reserve(); expired=False
                except RuntimeError: expired=True
                if stale or exited or expired:
                    restore_locked(generation); return
                (root/('watch-ready-'+generation)).touch()
            time.sleep(.5)
    finally: (root/('watch-done-'+generation)).touch()
def join_watchers():
    for pending in root.glob('watch-pending-*'):
        generation=pending.name.removeprefix('watch-pending-')
        for _ in range(100):
            with locked():
                journal=root/('watch-pid-'+generation+'.json')
                record=json.loads(journal.read_text()) if journal.exists() else None
                if record is None and not active(generation):
                    (root/('watch-done-'+generation)).touch(); break
                if record is not None and identity(record['pid'])!=record['identity']:
                    (root/('watch-done-'+generation)).touch(); break
                if record is None and (root/('watch-done-'+generation)).exists(): break
            time.sleep(.1)
        else: raise RuntimeError('watcher did not retire')
def main():
    action=sys.argv[2]; generation=sys.argv[3] if len(sys.argv)>3 else None
    if action=='prepare': print(json.dumps(prepare(generation,sys.argv[4])))
    elif action=='block': block(generation)
    elif action=='start': start(generation)
    elif action=='launch_watch': launch_watch(generation)
    elif action=='renew': renew(generation)
    elif action=='restore': restore(generation)
    elif action=='watch': watch(generation)
    elif action=='join': join_watchers()
    elif action=='archive':
        with locked():
            print(json.dumps({p.name:json.loads(p.read_text()) for p in root.glob('*.json')}))
    elif action=='remove':
        join_watchers()
        with locked():
            result=json.loads((root/'cleanup.json').read_text())
            old=json.loads((root/'restore.json').read_text()) if (root/'restore.json').exists() else {'generation':None}
            if result['status']!='PASS' or result['generation']!=old['generation'] or (root/'active').exists():
                raise RuntimeError('restoration PASS required before material deletion')
            stop_daemon(); shutil.rmtree(root)
    elif action=='access':
        fd=os.open(root/'client.ovpn',os.O_RDONLY|os.O_NOFOLLOW); os.close(fd)
        fd=os.open('/dev/net/tun',os.O_RDWR); os.close(fd)
        print(json.dumps(dict(uid=os.getuid(),gid=os.getgid(),status=pathlib.Path('/proc/self/status').read_text(),
            mode=oct((root/'client.ovpn').stat().st_mode & 0o777))))
    elif action=='status':
        with locked():
            record=json.loads((root/'vpn.pid').read_text()) if (root/'vpn.pid').exists() else None
            pid=record['pid'] if record else None; status=pathlib.Path('/proc',str(pid),'status')
            print(json.dumps(dict(active=active(generation) and not cancelled(generation),pid=pid,
                watcher_ready=(root/('watch-ready-'+str(generation))).exists(),
                daemon_status=status.read_text() if status.exists() else None,
                log=(root/'vpn.log').read_text()[-12000:] if (root/'vpn.log').exists() else '',network=state())))
if __name__=='__main__': main()
'''


def agent(state, action, *args):
    return inside(A, "python3", state["container_root"] + "/agent.py", state["container_root"], action, *args, root=True)


def process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return None if fields[0] == "Z" else fields[19]
    except FileNotFoundError:
        return None


GATE = "import os,sys; token=sys.stdin.buffer.read(1); sys.exit(1) if token!=b'G' else os.execvp(sys.argv[1],sys.argv[1:])"


class Lease:
    def __init__(self, state, generation):
        self.state, self.generation = state, generation
        self.stopped = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self.renew)
        self.thread.start()

    def renew(self):
        while not self.stopped.is_set():
            try:
                agent(self.state, "renew", self.generation)
            except Exception as error:
                self.error = error
                return
            if self.stopped.wait(2):
                return

    def stop(self):
        self.stopped.set()
        self.thread.join(35)
        check(not self.thread.is_alive(), "lease renewal did not stop")


def dns_negative(host, container=None):
    code = r'''import json,socket,sys
host=sys.argv[1]; result={}
query=b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07service\x04ld01\x04test\x00\x00\x01\x00\x01'
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
    sock.settimeout(2)
    try:
        sock.sendto(query,(host,53)); sock.recv(4096); result['udp_dns_unreachable']=False
    except OSError: result['udp_dns_unreachable']=True
try:
    with socket.create_connection((host,53),timeout=2) as sock:
        result['tcp_dns_unreachable']=False
        sock.sendall(len(query).to_bytes(2,'big')+query)
except OSError:
    result.setdefault('tcp_dns_unreachable',True)
print(json.dumps(result))'''
    execute = (lambda *cmd: inside(container, *cmd)) if container else run
    return json.loads(execute("python3", "-c", code, host))


def cleanup(state):
    """Idempotent, best-effort all resources; every restoration error blocks PASS."""
    errors = []
    private = Path(state["private"])
    with open(private / "cleanup.lock", "a", opener=lambda p, f: os.open(p, f, 0o600)) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (private / "cleaned.json").exists() and json.loads((private / "cleaned.json").read_text())["status"] == "PASS":
            return []
        if (private / "cleaned.json").exists():
            os.replace(private / "cleaned.json", private / ("cleanup-previous-" + uuid.uuid4().hex + ".json"))
        def attempt(label, fn):
            try:
                fn()
            except Exception as error:
                errors.append(label + ": " + str(error))
        restored = False
        if state.get("prepared") or state.get("a_material"):
            def restore():
                nonlocal restored
                obj = json.loads(run("docker", "inspect", A))[0]
                check(obj["Id"] == state["a_id"], "A identity changed before cleanup")
                agent(state, "restore")
                agent(state, "join")
                result = inside(A, "cat", state["container_root"] + "/cleanup.json", root=True)
                private_write(private / ("a-cleanup-" + uuid.uuid4().hex + ".json"), result)
                check(json.loads(result)["status"] == "PASS", "explicit A restoration PASS required")
                restored = True
            attempt("A restoration", restore)
        for process in state.get("forwards", []):
            def stop(p=process):
                if process_identity(p["pid"]) == p["identity"]:
                    os.killpg(p["pid"], signal.SIGTERM)
                    for _ in range(30):
                        if process_identity(p["pid"]) is None:
                            break
                        # The process can be our unreaped child; zombie holds no socket.
                        if Path(f'/proc/{p["pid"]}/stat').read_text().split()[2] == "Z":
                            break
                        time.sleep(0.1)
                    else:
                        os.killpg(p["pid"], signal.SIGKILL)
                for _ in range(30):
                    listeners = run("ss", "-H", "-lnt")
                    bindings = [s.rsplit(":", 2)[0] for s in p["specifications"]]
                    if not any(binding + " " in listeners for binding in bindings):
                        return
                    time.sleep(.1)
                raise RuntimeError("task forward still listening")
            attempt("forward stop", stop)
        if state.get("deployed"):
            def rollback():
                import shlex
                command = ["sudo", "bash", state["upload"] + "/setup-server.sh", state["task"],
                           state["subnet"], DEADLINE, state["a_bridge"], "20990", state["receipt"], "rollback"]
                remote(shlex.join(command), timeout=360)
            attempt("server rollback", rollback)
        if state.get("a_material") and restored and not errors:
            def remove_material():
                obj = json.loads(run("docker", "inspect", A))[0]
                check(obj["Id"] == state["a_id"], "A identity changed before material cleanup")
                private_write(private / ("a-rollback-" + uuid.uuid4().hex + ".json"), agent(state, "archive"))
                agent(state, "remove")
                state["a_material"] = state["prepared"] = False
                save(state)
            attempt("A material removal", remove_material)
        result = {"finished": utc().isoformat(), "errors": errors, "status": "FAIL" if errors else "PASS"}
        private_write(private / ("cleanup-attempt-" + uuid.uuid4().hex + ".json"), json.dumps(result, indent=2))
        if not errors:
            private_write(private / "cleaned.json", json.dumps(result, indent=2))
    return errors


class Shell:
    def __init__(self):
        source = (HERE / "fixtures.py").read_text()
        self.process = subprocess.Popen(["docker", "exec", "-i", A, "bash", "--noprofile", "--norc", "-c",
            'python3 -u -c "$1" shell; :', "--", source], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    def request(self, action):
        self.process.stdin.write(json.dumps({"action": action}) + "\n")
        self.process.stdin.flush()
        check(select.select([self.process.stdout], [], [], 15)[0], "joined shell timeout")
        line = self.process.stdout.readline()
        check(line, "joined shell exited")
        return json.loads(line)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write('{"action":"quit"}\n')
            self.process.stdin.flush()
        self.process.communicate(timeout=10)


class Trial:
    def __init__(self, private):
        self.private = private
        task = "cvpn" + uuid.uuid4().hex[:12]
        self.state = {"private": str(private), "task": task, "deadline": DEADLINE,
                      "receipt": uuid.uuid4().hex,
                      "server_root": "/var/lib/ld01-cvpn-" + task,
                      "container_root": "/run/ld01-" + task, "forwards": [],
                      "controller_pid": os.getpid(), "controller_identity": process_identity(os.getpid())}
        self.evidence = {"started": utc().isoformat(), "status": "FAIL", "cycles": []}
        self.shells, self.holds = [], []
        self.lease = None

    def preflight(self):
        reserve()
        check(run("git", "branch", "--show-current").strip() == "feat/controlled-vpn-trial", "wrong worktree branch")
        check(Path.cwd().resolve() == Path("/tmp/opencode/termux-vm-controlled-vpn-trial"), "wrong worktree")
        resources = json.loads((BASELINE / "resources.json").read_text())
        baseline = json.loads((BASELINE / "spot-check-20261019T152932087625Z.json").read_text())
        image = json.loads((BASELINE / "image.json").read_text())["image"]["Id"]
        objects = json.loads(run("docker", "inspect", A, B))
        reconcile(objects, resources, baseline, image)
        self.state["a_id"] = objects[0]["Id"]
        networks = json.loads(run("docker", "network", "inspect", *["tvm-share-ld01-net-" + x for x in ("a", "b")]))
        ids = {r["name"]: r.get("id") for r in resources["resources"]}
        for net in networks:
            check(net["Id"] == ids[net["Name"]], "network identity drift")
            check(net["Driver"] == "bridge" and not net["EnableIPv6"], "network configuration drift")
            check(all(net["Labels"].get(k) == v for k, v in LABELS.items()), "network ownership drift")
            check(set(net["Containers"]) == {o["Id"] for o in objects if o["Name"].endswith(net["Name"][-1])}, "unexpected network peer")
            index = 0 if net["Name"].endswith("a") else 1
            expected_net = ipaddress.ip_network(resources["subnets"][index])
            check(net["IPAM"]["Config"] == [{"Subnet": str(expected_net), "IPRange": "", "Gateway": str(expected_net.network_address + 1)}], "network IPAM drift")
        volumes = json.loads(run("docker", "volume", "inspect", "tvm-share-ld01-home-a", "tvm-share-ld01-home-b"))
        check(all(all(v["Labels"].get(k) == x for k, x in LABELS.items()) for v in volumes), "volume ownership drift")
        self.objects = objects
        self.state["a_bridge"] = networks[0]["IPAM"]["Config"][0]["Gateway"]
        self.state["b_bridge"] = networks[1]["IPAM"]["Config"][0]["Gateway"]
        check_ports(((self.state["a_bridge"], 20990), (self.state["b_bridge"], 20991), ("127.0.0.1", 20991)))
        check(inside(A, "test", "!", "-e", self.state["container_root"], root=True) == "", "occupied A task path")
        links = json.loads(inside(A, "ip", "-j", "link", "show"))
        check(not any(x["ifname"] == "ld01tun" for x in links), "occupied A tunnel")
        # pgrep's no-match exit is expected; inspect proc without invoking/printing profiles.
        check(inside(A, "python3", "-c", "from pathlib import Path; print(any(p.read_text().strip()=='openvpn' for p in Path('/proc').glob('[0-9]*/comm')))").strip() == "False", "existing A VPN daemon")
        cloud = json.loads(remote("python3 -c " + __import__('shlex').quote(
            "import json,subprocess,socket,pathlib; print(json.dumps(dict(host=socket.gethostname(),"
            "machine=pathlib.Path('/etc/machine-id').read_text().strip(),"
            "routes=json.loads(subprocess.check_output(['ip','-4','-j','route','show','table','all'])),"
            "listeners=subprocess.check_output(['ss','-H','-lnt'],text=True))))")))
        check(cloud["host"] == "free-vm", "VM hostname mismatch")
        allnets = json.loads(run("docker", "network", "inspect", *run("docker", "network", "ls", "-q").split()))
        used = []
        for routes in (json.loads(run("ip", "-4", "-j", "route", "show", "table", "all")), cloud["routes"],
                       json.loads(inside(A, "ip", "-4", "-j", "route", "show", "table", "all")),
                       json.loads(inside(B, "ip", "-4", "-j", "route", "show", "table", "all"))):
            used += [ipaddress.ip_network(r["dst"], strict=False) for r in routes if r.get("dst") not in (None, "default")]
        for net in allnets:
            used += [ipaddress.ip_network(c["Subnet"]) for c in net["IPAM"].get("Config") or [] if c.get("Subnet") and ":" not in c["Subnet"]]
        chosen = next((n for n in ipaddress.ip_network("10.231.0.0/16").subnets(new_prefix=24)
                       if not any(n.overlaps(u) for u in used)), None)
        check(chosen is not None, "no collision-free VPN subnet")
        self.state.update(subnet=str(chosen), server=str(chosen.network_address + 1))
        self.evidence["preflight"] = {"containers": objects, "networks": networks, "volumes": volumes, "vm": cloud,
                                      "subnet": str(chosen)}
        save(self.state)

    def deploy(self):
        reserve()
        task = self.state["task"]
        upload = "/tmp/ld01-upload-" + task
        # Fresh source-only upload. No key/profile is sent in command arguments.
        payload = {"setup-server.sh": (HERE / "setup-server.sh").read_text(),
                   "fixtures.py": (HERE / "fixtures.py").read_text()}
        script = ("import json,os,pathlib,sys; os.umask(0o077); p=pathlib.Path(" + repr(upload) + "); p.mkdir(mode=0o700); "
                  "files=json.load(sys.stdin); [(p/k).write_text(v) for k,v in files.items()]")
        import shlex
        remote("python3 -c " + shlex.quote(script), data=json.dumps(payload))
        self.state["upload"] = upload
        # Mark before deployment: even partial setup needs scoped rollback.
        self.state["deployed"] = True
        save(self.state)
        command = ["sudo", "bash", upload + "/setup-server.sh", task, self.state["subnet"], DEADLINE,
                   self.state["a_bridge"], "20990", self.state["receipt"]]
        try:
            remote("umask 077; " + shlex.join(command) + " > " + upload + "/setup.log 2>&1", timeout=360)
        finally:
            private_write(self.private / "server-setup.log", remote("cat " + upload + "/setup.log"))
        profile = remote("sudo cat " + self.state["server_root"] + "/client.ovpn")
        check("verify-x509-name lab.ld01.test name\n" in profile and "auth SHA256\n" in profile,
              "profile verification policy missing")
        private_write(self.private / "client.ovpn", profile)
        self.profile = profile
        self.evidence["server"] = json.loads(remote("sudo cat " + self.state["server_root"] + "/server.json"))
        code = ("import pathlib,json; p=pathlib.Path(" + repr(self.state["server_root"]) + "); "
                "old=set((p/'packages-before.tsv').read_text().splitlines()); "
                "new=set((p/'packages-after.tsv').read_text().splitlines()); "
                "print(json.dumps(dict(added_or_changed=sorted(new-old),removed_or_replaced=sorted(old-new))))")
        self.evidence["packages"] = json.loads(remote("sudo python3 -c " + shlex.quote(code)))

    def forward(self, name, specifications):
        reserve()
        stream = open(self.private / (name + "-forward.log"), "x", opener=lambda p, f: os.open(p, f, 0o600))
        command = ["gcloud", "compute", "ssh", "free-vm", "--tunnel-through-iap", "--quiet", "--",
                   "-N", "-T", "-oControlMaster=no", "-oControlPath=none", "-oExitOnForwardFailure=yes",
                   "-oServerAliveInterval=5", "-oServerAliveCountMax=2"]
        for specification in specifications:
            command += ["-L", specification]
        process = subprocess.Popen([sys.executable, "-c", GATE, *command], stdin=subprocess.PIPE,
                                   stdout=stream, stderr=stream, start_new_session=True)
        stream.close()
        record = {"pid": process.pid, "identity": process_identity(process.pid), "name": name,
                  "specifications": specifications}
        try:
            check(record["identity"] is not None, "forward gate exited before registration")
            self.state["forwards"].append(record)
            save(self.state)
            process.stdin.write(b"G")
            process.stdin.flush()
        finally:
            # EOF before durable registration cancels the gate without spawning SSH.
            process.stdin.close()
        port = specifications[0].split(":")[1]
        for _ in range(120):
            check(process.poll() is None, name + " forwarding exited")
            if any(":" + port + " " in line for line in run("ss", "-H", "-lnt").splitlines()):
                return
            time.sleep(0.25)
        raise TimeoutError(name + " forwarding did not listen")

    def start_hold(self, name, container=None):
        source = (HERE / "fixtures.py").read_text()
        host = self.state["b_bridge"] if container else "127.0.0.1"
        command = ["python3", "-u", "-c", source, "hold", "--host", host, "--port", "20991"]
        if container:
            command = ["docker", "exec", "-i", container, *command]
        path = self.private / (name + "-heartbeat.jsonl")
        stream = open(path, "x", opener=lambda p, f: os.open(p, f, 0o600))
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stream, stderr=stream, text=True)
        stream.close()
        self.holds.append((process, path))
        for _ in range(60):
            check(process.poll() is None, name + " heartbeat startup failed")
            if path.stat().st_size:
                check(json.loads(path.read_text().splitlines()[0])["kind"] == "ack", "invalid heartbeat start")
                return
            time.sleep(0.1)
        raise TimeoutError("heartbeat startup timeout")

    def health(self):
        reserve(180)
        check(self.lease is None or self.lease.error is None, "independent lease renewal failed")
        for p, _ in self.holds:
            check(p.poll() is None, "held heartbeat failed")
        for record in self.state["forwards"]:
            check(process_identity(record["pid"]) == record["identity"], "forward transport failed")
        if self.state.get("prepared"):
            status = json.loads(agent(self.state, "status", self.state["generation"]))
            check(status["active"], "A watchdog restored after failure")
            return status

    def prepare(self):
        reserve()
        root = self.state["container_root"]
        inside(A, "python3", "-c", "import os,sys; os.umask(0o077); os.mkdir(sys.argv[1],0o700)", root, root=True)
        self.state["a_material"] = True
        save(self.state)
        for name, value in (("agent.py", AGENT), ("client.ovpn", self.profile)):
            inside(A, "python3", "-c", "import os,sys; os.umask(0o077); open(sys.argv[1],'x').write(sys.stdin.read())",
                   root + "/" + name, data=value, root=True)
        self.evidence["daemon_material_access"] = json.loads(agent(self.state, "access"))
        check(self.evidence["daemon_material_access"]["uid"] == 0, "daemon start identity mismatch")
        check("CapEff:\t0000000000001000" in self.evidence["daemon_material_access"]["status"], "unexpected daemon capabilities")
        self.shells = [Shell(), Shell()]
        identities = [s.request("identity")["identity"] for s in self.shells]
        check(all(x["uid"] == x["gid"] == 1001 for x in identities), "daily shell not non-root")
        check(inside(A, "python3", "-c", "from pathlib import Path; print(next(x for x in Path('/proc/self/status').read_text().splitlines() if x.startswith('CapEff:')))").strip() == "CapEff:\t0000000000000000", "daily effective capabilities")
        check(identities[0]["net"] == identities[1]["net"] and identities[0]["shell_pid"] != identities[1]["shell_pid"], "joined shells not distinct/shared")
        self.evidence["shells"] = identities

    def cycle(self, number):
        reserve()
        initiator, observer = (number, 1 - number)
        record = {"initiator": initiator + 1, "observer": observer + 1, "started": utc().isoformat()}
        self.evidence["cycles"].append(record)
        before = snapshot(A)
        record["request_connect"] = self.shells[initiator].request("connect")
        # Journal before the first mutable A state. The controller/agent watchdogs
        # share an idempotent scoped restoration path, also used on startup errors.
        self.state["prepared"] = True
        generation = uuid.uuid4().hex
        self.state["generation"] = generation
        save(self.state)
        record["a_before"] = json.loads(agent(self.state, "prepare", generation, self.state["server"]))
        root = self.state["container_root"]
        self.lease = Lease(self.state, generation)
        try:
            agent(self.state, "launch_watch", generation)
            for _ in range(40):
                if self.health()["watcher_ready"]:
                    break
                time.sleep(.1)
            else:
                raise TimeoutError("A watcher did not register")
            agent(self.state, "block", generation)
            agent(self.state, "start", generation)
            for _ in range(80):
                status = self.health()
                if "Initialization Sequence Completed" in status["log"]:
                    check(status["daemon_status"] and "CapEff:\t0000000000001000" in status["daemon_status"], "actual daemon capability drift")
                    break
                time.sleep(0.25)
            else:
                raise TimeoutError("VPN did not initialize")
            record["daemon"] = status
            check(all(f"-A {hook} -j LDC{self.state['task'][-12:]}" in status["network"]["ipv6"]
                      for hook in ("INPUT", "OUTPUT", "FORWARD")), "IPv6 traffic is not blocked inside A")
            record["probes"] = [s.request("probe") for s in self.shells]
            for probe in record["probes"]:
                check(probe["answers"] == [self.state["server"]], "private DNS mismatch")
                check(probe["http"] == {"fixture": self.state["task"], "service": "service.ld01.test"}, "HTTP fixture mismatch")
                check("SERVER: " + self.state["server"] + "#53" in probe["dig"], "DNS did not use lab resolver")
            record["embedded_dns_negative"] = dns_negative("127.0.0.11", A)
            check(all(record["embedded_dns_negative"].values()), "embedded DNS bypass remains reachable")
            record["connected_routes"] = snapshot(A)
            routes = record["connected_routes"]["-4route"]
            check(any(r.get("dst") == self.state["subnet"] and r.get("dev") == "ld01tun" for r in routes), "VPN subnet route missing")
            check([r for r in routes if r.get("dev") != "ld01tun"] == before["-4route"], "non-VPN IPv4 routes changed")
            self.negative_probes(record)
            check(snapshot() == self.host_before and snapshot(B) == self.b_before, "host/B routes/rules/DNS changed")
            self.health()
            record["request_disconnect"] = self.shells[observer].request("disconnect")
        finally:
            # Preserve a bounded private daemon log even when initialization fails.
            try:
                record["last_daemon"] = json.loads(agent(self.state, "status", generation))
            finally:
                self.lease.stop()
                self.lease = None
                agent(self.state, "restore", generation)
                agent(self.state, "join")
                self.state["prepared"] = False
                save(self.state)
        check(snapshot(A) == before, "A routes/rules/resolver not exactly restored")
        record["a_cleanup"] = json.loads(inside(A, "cat", root + "/cleanup.json", root=True))
        check(record["a_cleanup"]["status"] == "PASS", "A cleanup failed")
        record["finished"] = utc().isoformat()
        record["status"] = "PASS"

    def negative_probes(self, record):
        code = r'''import json,socket,sys
host=sys.argv[1]; result={}
try:
    s=socket.create_connection((host,8080),timeout=2); s.close(); result['http_unreachable']=False
except OSError: result['http_unreachable']=True
print(json.dumps(result))'''
        record["host_negative"] = json.loads(run("python3", "-c", code, self.state["server"]))
        record["b_negative"] = json.loads(inside(B, "python3", "-c", code, self.state["server"]))
        record["host_negative"].update(dns_negative(self.state["server"]))
        record["b_negative"].update(dns_negative(self.state["server"], B))
        check(all(all(record[k].values()) for k in ("host_negative", "b_negative")), "private fixture reachable outside A")

    def finish_holds(self):
        for process, path in self.holds:
            process.communicate("stop\n", timeout=10)
            check(process.returncode == 0, "heartbeat failed")
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            acks, final = rows[:-1], rows[-1]
            check(final["kind"] == "finished" and final["errors"] == final["reconnects"] == 0, "heartbeat continuity failed")
            check(len(acks) >= 4 and [x["seq"] for x in acks] == list(range(1, len(acks) + 1)), "heartbeat acknowledgement gap")
            check(all(x["socket"] == final["socket"] and x["connection"] == final["connection"] for x in acks), "heartbeat socket changed")
            self.evidence[path.stem] = final

    def execute(self):
        try:
            self.preflight()
            # Independent host watchdog survives controller termination. Server
            # units and the A lease watchdog independently bound remote/VPN life.
            watchdog_log = open(self.private / "watchdog.log", "x", opener=lambda p, f: os.open(p, f, 0o600))
            self.watchdog = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--watch", str(self.private / "state.json")],
                stdout=watchdog_log, stderr=watchdog_log, start_new_session=True)
            watchdog_log.close()
            self.deploy()
            self.forward("heartbeat", ["127.0.0.1:20991:127.0.0.1:19090", self.state["b_bridge"] + ":20991:127.0.0.1:19090"])
            self.forward("vpn", [self.state["a_bridge"] + ":20990:127.0.0.1:11940"])
            self.host_before, self.b_before = snapshot(), snapshot(B)
            self.evidence.update(host_before=self.host_before, b_before=self.b_before)
            self.start_hold("host")
            self.start_hold("b", B)
            self.prepare()
            self.cycle(0)
            self.cycle(1)
            self.finish_holds()
            check(snapshot() == self.host_before and snapshot(B) == self.b_before, "host/B final state drift")
            current = json.loads(run("docker", "inspect", A, B))
            for old, new in zip(self.objects, current):
                check(old["Id"] == new["Id"] and old["Config"] == new["Config"] and
                      old["HostConfig"] == new["HostConfig"] and mounts(old) == mounts(new) and
                      old["NetworkSettings"] == new["NetworkSettings"], "retained container configuration drift")
            self.evidence["status"] = "PASS"
        except BaseException as error:
            self.evidence["error"] = {"type": type(error).__name__, "message": str(error)}
        finally:
            if self.lease is not None:
                try:
                    self.lease.stop()
                except Exception as error:
                    self.evidence.setdefault("teardown_errors", []).append(str(error))
            for shell in self.shells:
                try:
                    shell.close()
                except Exception as error:
                    self.evidence.setdefault("teardown_errors", []).append(str(error))
            for process, _ in self.holds:
                if process.poll() is None:
                    try:
                        process.communicate("stop\n", timeout=10)
                    except Exception:
                        process.kill()
                        self.evidence.setdefault("teardown_errors", []).append("heartbeat did not stop")
            errors = cleanup(self.state)
            self.evidence["cleanup_errors"] = errors
            if errors or self.evidence.get("teardown_errors"):
                self.evidence["status"] = "FAIL"
            if self.state.get("deployed"):
                try:
                    root = self.state["server_root"]
                    private_write(self.private / "server-openvpn.log", remote("sudo cat " + root + "/server.log"))
                    self.evidence["server_after_cleanup"] = remote("ss -H -lnt; systemctl list-units 'ld01-" + self.state["task"] + "*' --all --no-pager --plain")
                except Exception as error:
                    self.evidence.setdefault("teardown_errors", []).append(str(error))
                    self.evidence["status"] = "FAIL"
            self.evidence["finished"] = utc().isoformat()
            self.evidence["resources"] = self.state
            private_write(self.private / "evidence.json", json.dumps(self.evidence, indent=2))
        return self.evidence["status"]


def watch(path):
    while True:
        state = json.loads(path.read_text())
        if (path.parent / "cleaned.json").exists() and json.loads((path.parent / "cleaned.json").read_text())["status"] == "PASS":
            return
        if process_identity(state["controller_pid"]) != state["controller_identity"] or remaining() < 180:
            cleanup(state)
            return
        time.sleep(1)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path)
    parser.add_argument("--watch", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.watch:
        watch(args.watch)
        return
    check(args.private_dir is not None, "--private-dir required")
    check(args.private_dir.parent.resolve() == Path("/tmp/opencode"), "private directory parent mismatch")
    try:
        args.private_dir.mkdir(mode=0o700)
    except FileExistsError:
        failure = Path(tempfile.mkdtemp(prefix="controlled-vpn-rejected-", dir="/tmp/opencode"))
        private_write(failure / "evidence.json", json.dumps({"status": "FAIL", "error": "occupied private directory", "timestamp": utc().isoformat()}))
        print("FAIL: " + str(failure / "evidence.json"))
        return 1
    trial = Trial(args.private_dir.resolve())
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError("controller terminated")))
    status = trial.execute()
    print(status + ": " + str(trial.private / "evidence.json"))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
