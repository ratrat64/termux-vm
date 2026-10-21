"""One approved LD01 controlled trial. Secrets and evidence never enter the worktree.

Run only after fresh live approval, with --authorization and an unused --private-dir.
Offline implementation is not live authorization. The fixed window includes cleanup.
"""

import argparse
import contextlib
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import fcntl
import ipaddress
import json
import os
import re
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
ROOT = HERE.parents[2]
BASELINE = Path("/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM")
A, B = "tvm-share-ld01-a", "tvm-share-ld01-b"
DEADLINE = None  # Set only by a fresh, explicit live authorization, never at import.
CANCEL = None
OWNERSHIP = threading.local()
# One admitted command (server worker: 80s + 5s kill grace), then ownership/off.
COMMAND_TIMEOUT = 100
SUPERVISOR_WAIT = COMMAND_TIMEOUT + 10
TEARDOWN_BUDGET = 300
LABELS = {"task": "linux-docker-sharing-trial", "trial": "ld01",
          "owner": "opencode-linux-trial-preparation"}


def check(value, message):
    if not value:
        raise ValueError(message)


def utc():
    return dt.datetime.now(dt.timezone.utc)


def remaining(now=None, deadline=None):
    check(deadline or DEADLINE, "fresh live authorization required")
    return (dt.datetime.fromisoformat((deadline or DEADLINE).replace("Z", "+00:00")) - (now or utc())).total_seconds()


def reserve(seconds=600):
    check(remaining() > seconds, "approval expired or cleanup reserve reached")
    if CANCEL is not None: require_uncancelled({'private': CANCEL.parent})


def authorize(value, now=None, baseline_only=False):
    """Admission is local and non-mutating; the human supplies this private record."""
    now = now or utc()
    for key in ("observation", "exclusive_reuse", "supervised_off"):
        check(value.get(key) is True, "missing affirmative approval: " + key)
    if baseline_only:
        check(value.get('mode') == 'baseline-only' and value.get('injection') is False and
              value.get('cases') == [], 'baseline-only approval must prohibit injection')
        check(value.get('post_reboot_reconciled') is True, 'post-reboot reconciliation required')
    else:
        check(value.get('mode', 'n2') == 'n2' and value.get('injection') is True, 'exact F1/F2 approval required')
        check(value.get("cases") == ["F1", "F2"], "exact F1/F2 approval required")
    check(value.get("targets") == [A, "free-vm", "A-veth", "example.com"], "target approval mismatch")
    start, end = [dt.datetime.strptime(value[k], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
                  for k in ("start", "deadline")]
    check(0 < (end - start).total_seconds() <= (1800 if baseline_only else 2700), "window exceeds approved bound")
    check(start <= now < end - dt.timedelta(minutes=15), "window inactive or injection reserve reached")
    return value


def diagnostic_inputs(approval):
    """Missing reboot-lost metadata blocks admission locally, never fabricates history."""
    directory = Path(approval.get('baseline_dir', ''))
    metadata = Path(approval.get('retained_metadata', ''))
    check(directory.is_absolute() and metadata.is_absolute(), 'absolute private baseline paths required')
    paths = [directory / name for name in ('resources.json', 'image.json', 'baseline.json')]
    for path in [*paths, metadata]:
        check(path.is_file() and not path.is_symlink() and path.stat().st_mode & 0o777 == 0o600 and
              path.parent.stat().st_mode & 0o777 == 0o700, 'missing or non-private reconciled metadata: ' + path.name)
        check(ROOT not in path.resolve().parents, 'private metadata must be outside Git')
        json.loads(path.read_text())
    residuals = approval.get('residuals', {})
    check(set(residuals) == {'zombies', 'journals'} and all(isinstance(v, list) for v in residuals.values()),
          'explicit reconciled zombie/journal inventory required')
    return directory


def check_ports(bindings):
    for host, port in bindings:
        with socket.socket() as sock:
            sock.bind((host, port))


def run(*command, data=None, timeout=30):
    owner = getattr(OWNERSHIP, 'current', None)
    if owner is not None:
        if owner[1]:
            budget = owner[2] - time.monotonic()
            if budget <= 0: raise TimeoutError('supervised teardown budget exhausted')
            timeout = min(timeout, budget)
        else:
            require_uncancelled({'private': owner[0]})
            timeout = min(timeout, COMMAND_TIMEOUT)
    result = subprocess.run(command, input=data, text=True, capture_output=True, timeout=timeout)
    if owner is not None and not owner[1]:
        require_uncancelled({'private': owner[0]})
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
    temporary = path.with_name(".pending-" + uuid.uuid4().hex)
    try:
        with open(temporary, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        # Publish complete immutable evidence without overwriting an earlier attempt.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def file_lock(path, timeout=8):
    owner = getattr(OWNERSHIP, 'current', None)
    if owner is not None and owner[1]:
        timeout = min(timeout, max(0, owner[2] - time.monotonic()))
    with open(path, "a", opener=lambda p, f: os.open(p, f, 0o600)) as lock:
        until = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= until: raise TimeoutError(f"lifecycle lock timeout: {path.name} ({timeout}s)")
                time.sleep(.05)
        yield


def require_uncancelled(state):
    private = Path(state['private'])
    check(not any((private / name).exists() for name in ('cancel-requested.json', 'off-requested.json')),
          "supervised trial-off requested")


def teardown_budget(state, limit):
    # Reserve bounded process-exit polling and private failure evidence before stop.
    return min(limit, max(0, remaining(deadline=state['deadline']) - 20)) if state.get('deadline') else limit


@contextlib.contextmanager
def lifecycle(state, teardown=False):
    """The existing cleanup lock also owns controller mutation and publication."""
    private = Path(state["private"])
    owner = getattr(OWNERSHIP, "current", None)
    if owner is not None:
        check(owner[0] == private, "different lifecycle already owned")
        if not owner[1]: require_uncancelled(state)
        yield
        return
    if not teardown: require_uncancelled(state)
    with file_lock(private / "cleanup.lock", timeout=teardown_budget(state, SUPERVISOR_WAIT) if teardown else 8):
        path = private / "state.json"
        if path.exists():
            latest = json.loads(path.read_text())
            if teardown:
                state.clear(); state.update(latest)
            else:
                check(state.get("revision", 0) == latest.get("revision", 0), "stale controller state")
        if not teardown: require_uncancelled(state)
        OWNERSHIP.current = (private, teardown, time.monotonic() + teardown_budget(state, TEARDOWN_BUDGET) if teardown else None)
        try: yield
        finally: OWNERSHIP.current = None


def mutating(method):
    def owned(self, *args, **kwargs):
        with lifecycle(self.state):
            return method(self, *args, **kwargs)
    return owned


def cancel(state, reason):
    private = Path(state["private"])
    # Stop the next command before waiting for the in-flight publication/command.
    try:
        private_write(private / 'cancel-requested.json', json.dumps(dict(reason=reason, time=time.time())))
    except FileExistsError:
        pass
    if (private / 'off-requested.json').exists(): return
    with file_lock(private / "publication.lock", timeout=teardown_budget(state, SUPERVISOR_WAIT)):
        if not (private / "off-requested.json").exists():
            private_write(private / "off-requested.json", json.dumps(dict(reason=reason, time=time.time())))


def save(state):
    with lifecycle(state):
        with file_lock(Path(state["private"]) / "publication.lock"):
            if not OWNERSHIP.current[1]: require_uncancelled(state)
            state["revision"] = state.get("revision", 0) + 1
            publish(state)


def publish(state):
    path = Path(state["private"]) / "state.json"
    temporary = path.with_name(".state-" + uuid.uuid4().hex + ".new")
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
class LockTimeout(RuntimeError): pass
def atomic(name, value):
    path=root/name; temporary=root/('.pending-'+uuid.uuid4().hex)
    temporary.write_text(value); os.replace(temporary,path)
@contextlib.contextmanager
def locked():
    with open(root/'lifecycle.lock','a') as lock:
        until=time.monotonic()+8
        while True:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.monotonic()>=until: raise LockTimeout('lifecycle lock timeout')
                time.sleep(.05)
        yield
def identity(pid):
    try:
        fields=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except FileNotFoundError: return None
def reserve(seconds=600):
    approval=json.loads((root/'authorization.json').read_text())
    baseline=approval.get('mode')=='baseline-only'
    allowed=(approval.get('injection') is False and approval.get('cases')==[]) if baseline else (
        approval.get('mode','n2')=='n2' and approval.get('injection') is True and approval.get('cases')==['F1','F2'])
    if not allowed or not all(approval.get(k) is True for k in ('observation','exclusive_reuse','supervised_off')):
        raise RuntimeError('fresh live authorization required')
    start=datetime.datetime.fromisoformat(approval['start'].replace('Z','+00:00')).timestamp()
    end=datetime.datetime.fromisoformat(approval['deadline'].replace('Z','+00:00')).timestamp()
    if not start<=time.time()<end-seconds or not 0<end-start<=(1800 if baseline else 2700):
        raise RuntimeError('cleanup reserve reached')
def active(generation):
    return (root/'active').exists() and (root/'active').read_text()==generation
def cancelled(generation):
    return (root/'cancelled').exists() and (root/'cancelled').read_text()==generation
def phase():
    return json.loads((root/'intent.json').read_text()) if (root/'intent.json').exists() else {}
def intent(generation, value, reason=None):
    atomic('intent.json',json.dumps(dict(generation=generation,phase=value,reason=reason,time=time.time())))
def require_active(generation):
    reserve()
    if not active(generation) or cancelled(generation) or phase().get('phase') in ('faulted','off'):
        raise RuntimeError('cancelled or obsolete generation')
def cmd(*args, required=True):
    p = subprocess.run(args, capture_output=True, text=True, timeout=2)
    if required and p.returncode: raise RuntimeError(args[0] + ' failed')
    return p
def state():
    return dict(resolver=base64.b64encode(pathlib.Path('/etc/resolv.conf').read_bytes()).decode(),
        ipv4=cmd('iptables','-S').stdout, ipv6=cmd('ip6tables','-S').stdout,
        nat=cmd('iptables','-t','nat','-S').stdout,
        routing={family+kind:json.loads(cmd('ip',family,'-j',kind,'show',*(['table','all'] if kind=='route' else [])).stdout)
                 for family in ('-4','-6') for kind in ('route','rule')},
        sysctl={p.parent.name:p.read_text() for p in pathlib.Path('/proc/sys/net/ipv6/conf').glob('*/disable_ipv6')})
def prepare(generation, server, subnet=None):
    with locked():
        reserve()
        if (root/'active').exists(): raise RuntimeError('previous generation still active')
        if (root/('watch-pending-'+generation)).exists(): raise RuntimeError('obsolete generation')
        if (root/'restore.json').exists() and json.loads((root/'cleanup.json').read_text())['status']!='PASS':
            raise RuntimeError('previous restoration failed')
        import ipaddress
        net=ipaddress.ip_network(subnet or server+'/24',strict=False)
        if net.version!=4 or net.prefixlen!=24 or ipaddress.ip_address(server) not in net:
            raise RuntimeError('invalid VPN prefix')
        if (root/'restore.json').exists(): archive_locked('before-generation')
        old=state(); old.update(server=server,subnet=str(net),generation=generation)
        atomic('restore.json',json.dumps(old)); atomic('active',generation)
        atomic('lease',generation)
        for name in ('vpn.pid','vpn.log'): (root/name).unlink(missing_ok=True)
        try: block_locked(generation)
        except Exception:
            intent(generation,'faulted','protection installation failed')
            archive_locked('protection installation failed')
            raise
        intent(generation,'starting')
        (root/('watch-pending-'+generation)).touch()
        return old
def protection(old):
    return [['-d',old['subnet'],'!','-o','ld01tun','-j','REJECT']] + [
        ['-p',p,'-m','conntrack','--ctdir','ORIGINAL','--ctorigdstport','53',*restriction,'-j','REJECT']
        for p in ('udp','tcp') for restriction in
        (['!','--ctorigdst',old['server']],['!','-o','ld01tun'])]
def block(generation):
    with locked():
        require_active(generation)
        block_locked(generation)
def block_locked(generation):
    if (root/'protected').exists() and (root/'protected').read_text()==generation: return
    old=json.loads((root/'restore.json').read_text()); server=old['server']
    cmd('ip6tables','-N',chain); cmd('ip6tables','-A',chain,'-j','DROP')
    for hook in ('INPUT','OUTPUT','FORWARD'): cmd('ip6tables','-I',hook,'1','-j',chain)
    cmd('iptables','-N',chain)
    # Original DNS tuples survive Docker DNAT. Prefix protection precedes ESTABLISHED.
    for rule in protection(old): cmd('iptables','-A',chain,*rule)
    cmd('iptables','-I','OUTPUT','1','-j',chain)
    pathlib.Path('/etc/resolv.conf').write_text('nameserver '+server+'\noptions timeout:2 attempts:1\n')
    atomic('protected',generation)
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
        if not (root/'protected').exists() or (root/'protected').read_text()!=generation:
            raise RuntimeError('protection required before client startup')
        if (root/'vpn.pid').exists(): raise RuntimeError('client already registered')
        spawn(command or ['openvpn','--config',str(root/'client.ovpn'),'--log',str(root/'vpn.log')],'vpn.pid')
def connected(generation):
    with locked():
        require_active(generation)
        intent(generation,'connected')
def launch_watch(generation):
    with locked():
        require_active(generation)
        spawn([sys.executable,str(root/'agent.py'),str(root),'watch',generation],'watch-pid-'+generation+'.json')
def checked_daemon():
    if not (root/'vpn.pid').exists(): return
    record=json.loads((root/'vpn.pid').read_text()); pid=record['pid']
    if identity(pid) != record['identity']: return
    if str(root/'client.ovpn').encode() not in pathlib.Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0'):
        raise RuntimeError('daemon PID identity mismatch')
    return record
def kill_client(generation):
    with locked():
        approval=json.loads((root/'authorization.json').read_text())
        if approval.get('mode','n2')!='n2' or approval.get('injection') is not True:
            raise RuntimeError('fault injection prohibited by baseline-only approval')
        require_active(generation)
        reserve(900)
        record=checked_daemon()
        if record is None: raise RuntimeError('client missing before injection')
        archive_locked('before-client-kill')
        reserve(900)
        if checked_daemon()!=record: raise RuntimeError('client identity changed before injection')
        os.kill(record['pid'],signal.SIGKILL)
def stop_daemon():
    record=checked_daemon()
    if record is None: return
    pid=record['pid']
    os.kill(pid,signal.SIGTERM)
    for _ in range(40):
        if identity(pid) != record['identity']: return
        time.sleep(.1)
    os.kill(pid,signal.SIGKILL)
    for _ in range(20):
        if identity(pid) != record['identity']: return
        time.sleep(.1)
    raise RuntimeError('daemon did not exit')
def bounded(path, limit=12000):
    with path.open('rb') as stream:
        stream.seek(0,2); stream.seek(max(0,stream.tell()-limit))
        return stream.read(limit).decode(errors='replace')
def journals(archives=False):
    result={}
    for p in root.glob('*.json'):
        if p.name.startswith('archive-') and not archives: continue
        try: result[p.name]=json.loads(p.read_text())
        except (ValueError,UnicodeError) as error:
            if p.name in ('restore.json','intent.json','authorization.json','cleanup.json') or p.name.startswith('watch-pid-'):
                raise
            result[p.name]=dict(raw=bounded(p),error=str(error))
    if (root/'vpn.pid').exists(): result['vpn.pid']=json.loads((root/'vpn.pid').read_text())
    return result
def archive_locked(reason):
    record=dict(reason=reason,time=time.time(),intent=phase(),journals=journals(),observation_errors=[])
    def observe(label, fn):
        try: return fn()
        except Exception as error:
            record['observation_errors'].append(dict(observation=label,error=type(error).__name__+': '+str(error)))
    record['network']={label:observe(label,lambda c=command:cmd(*c).stdout[-24000:]) for label,command in (
        ('ipv4',('iptables','-S')),('ipv6',('ip6tables','-S')),('nat',('iptables','-t','nat','-S')),
        ('routes4',('ip','-4','-j','route','show','table','all')),('routes6',('ip','-6','-j','route','show','table','all')),
        ('rules4',('ip','-4','-j','rule','show')),('rules6',('ip','-6','-j','rule','show')))}
    record['resolver']=observe('resolver',lambda:bounded(pathlib.Path('/etc/resolv.conf')))
    record['counters']=observe('counters',lambda:cmd('iptables','-nvx','-L',chain).stdout[-12000:])
    record['processes']=observe('processes',lambda:cmd('ps','-eo','pid,ppid,stat,comm').stdout[-12000:])
    record['client']=observe('client',lambda:dict(
        journal=json.loads((root/'vpn.pid').read_text()),
        start_identity=identity(json.loads((root/'vpn.pid').read_text())['pid']))) if (root/'vpn.pid').exists() else None
    if record['client'] is not None:
        record['client']['status']=observe('client status',lambda:bounded(pathlib.Path('/proc',str(record['client']['journal']['pid']),'status')))
    record['log']=observe('log',lambda:bounded(root/'vpn.log')) if (root/'vpn.log').exists() else ''
    atomic('archive-'+uuid.uuid4().hex+'.json',json.dumps(record))
    return record
def fault_locked(generation, reason):
    if not active(generation) or cancelled(generation): return
    intent(generation,'faulted',reason)
    archive_locked(reason)
    # Failure to retire must never release protection. The journal remains retryable.
    stop_daemon()
def fault(generation, reason='controller failure'):
    with locked(): fault_locked(generation,reason)
def restore_locked(generation=None):
    if not (root/'restore.json').exists():
        if (root/'active').exists(): raise RuntimeError('missing restoration journal')
        atomic('cleanup.json',json.dumps(dict(status='PASS',errors=[],generation=None)))
        return
    old=json.loads((root/'restore.json').read_text())
    if generation is not None and generation!=old['generation']: return
    generation=old['generation']; atomic('cancelled',generation); failures=[]
    archive_locked('explicit-off')
    intent(generation,'off','explicit off')
    def attempt(fn):
        try: fn()
        except Exception as e: failures.append(type(e).__name__ + ': ' + str(e))
    attempt(stop_daemon)
    if failures:
        result=json.dumps(dict(status='FAIL',errors=failures,generation=generation))
        atomic('cleanup-attempt-'+uuid.uuid4().hex+'.json',result); atomic('cleanup.json',result)
        raise RuntimeError('; '.join(failures))
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
    release_at=time.time()
    for tool, hooks in [('ip6tables',('INPUT','OUTPUT','FORWARD')),('iptables',('OUTPUT',))]:
        for hook in hooks:
            remove_rule(tool,hook,['-j',chain])
        present=None
        def inspect_chain():
            nonlocal present
            present=cmd(tool,'-S',chain,required=False).returncode==0
        attempt(inspect_chain)
        if present is not False:
            rules=[['-j','DROP']] if tool=='ip6tables' else protection(old)
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
    def normalized(value):
        if isinstance(value,dict): return {k:normalized(v) for k,v in value.items() if k!='expires'}
        if isinstance(value,list): return sorted((normalized(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
        return value
    attempt(lambda: equal(normalized(state()['routing']),normalized(old['routing'])))
    result=json.dumps(dict(status='FAIL' if failures else 'PASS',errors=failures,generation=generation,release_at=release_at))
    atomic('cleanup-attempt-'+uuid.uuid4().hex+'.json',result)
    atomic('cleanup.json',result)
    if not failures: (root/'active').unlink(missing_ok=True)
    if failures: raise RuntimeError('; '.join(failures))
def restore(generation=None):
    with locked():
        if not (root/'restore.json').exists(): return restore_locked(generation)
        old=json.loads((root/'restore.json').read_text())
        if generation is not None and generation!=old['generation']: return
        generation=old['generation']
        atomic('cancelled',generation)
        archive_locked('explicit-off-request')
        intent(generation,'off','explicit off requested')
        try: stop_daemon()
        except Exception as error:
            result=json.dumps(dict(status='FAIL',errors=[str(error)],generation=generation))
            atomic('cleanup-attempt-'+uuid.uuid4().hex+'.json',result); atomic('cleanup.json',result)
            raise
    # Cancel under the same lock as start/renew, then retire watchers before release.
    join_watchers()
    with locked(): restore_locked(generation)
def renew(generation):
    with locked():
        require_active(generation); atomic('lease',generation)
def watch(generation):
    try:
        while True:
            try:
                with locked():
                    if not active(generation) or cancelled(generation) or phase().get('phase')=='faulted': return
                    stale=time.time()-(root/'lease').stat().st_mtime>20
                    record=json.loads((root/'vpn.pid').read_text()) if (root/'vpn.pid').exists() else None
                    exited=record is not None and identity(record['pid'])!=record['identity']
                    try: reserve(); expired=False
                    except RuntimeError: expired=True
                    if stale or exited or expired:
                        fault_locked(generation,'lease' if stale else 'client' if exited else 'deadline'); return
                    (root/('watch-ready-'+generation)).touch()
            except LockTimeout:
                continue
            time.sleep(.5)
    finally: (root/('watch-done-'+generation)).touch()
def join_watchers():
    for pending in root.glob('watch-pending-*'):
        generation=pending.name.removeprefix('watch-pending-')
        for _ in range(100):
            with locked():
                journal=root/('watch-pid-'+generation+'.json')
                record=json.loads(journal.read_text()) if journal.exists() else None
                if record is None and (not active(generation) or cancelled(generation)):
                    (root/('watch-done-'+generation)).touch(); break
                if record is not None and identity(record['pid'])!=record['identity']:
                    (root/('watch-done-'+generation)).touch(); break
                if record is None and (root/('watch-done-'+generation)).exists(): break
            time.sleep(.1)
        else: raise RuntimeError('watcher did not retire')
def main():
    action=sys.argv[2]; generation=sys.argv[3] if len(sys.argv)>3 else None
    if action=='prepare': print(json.dumps(prepare(generation,sys.argv[4],sys.argv[5])))
    elif action=='block': block(generation)
    elif action=='start': start(generation)
    elif action=='launch_watch': launch_watch(generation)
    elif action=='renew':
        try: renew(generation); print(json.dumps(dict(accepted=True)))
        except RuntimeError:
            if active(generation) and phase().get('phase')=='faulted':
                print(json.dumps(dict(accepted=False,phase='faulted',reason=phase().get('reason'))))
            else: raise
    elif action=='connected': connected(generation)
    elif action=='fault': fault(generation)
    elif action=='kill_client': kill_client(generation)
    elif action=='restore': restore(generation)
    elif action=='watch': watch(generation)
    elif action=='join': join_watchers()
    elif action=='archive':
        with locked():
            snapshot=archive_locked('controller archive')
            print(json.dumps(dict(snapshot=snapshot,journals=journals(archives=True))))
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
            watcher=root/('watch-pid-'+str(generation)+'.json')
            watch_record=json.loads(watcher.read_text()) if watcher.exists() else None
            watch_done=(root/('watch-done-'+str(generation))).exists()
            watch_live=watch_record is not None and identity(watch_record['pid'])==watch_record['identity'] and not watch_done
            if watch_record is not None and not watch_live and active(generation) and not cancelled(generation) and phase().get('phase')!='faulted':
                fault_locked(generation,'watcher lost')
            record=json.loads((root/'vpn.pid').read_text()) if (root/'vpn.pid').exists() else None
            pid=record['pid'] if record else None; status=pathlib.Path('/proc',str(pid),'status')
            print(json.dumps(dict(active=active(generation) and not cancelled(generation),intent=phase(),pid=pid,
                watcher_ready=(root/('watch-ready-'+str(generation))).exists(),
                watcher_live=watch_live,watcher_registered=watch_record is not None,watcher_done=watch_done,
                daemon_live=record is not None and identity(pid)==record['identity'],
                daemon_status=status.read_text() if status.exists() else None,
                log=(root/'vpn.log').read_text()[-12000:] if (root/'vpn.log').exists() else '',network=state(),
                counters=cmd('iptables','-nvx','-L',chain,required=False).stdout)))
if __name__=='__main__': main()
'''


def agent(state, action, *args):
    if action == 'renew': require_uncancelled(state)
    if action in ('prepare', 'block', 'start', 'launch_watch', 'connected', 'kill_client', 'fault', 'restore', 'remove'):
        with lifecycle(state):
            with file_lock(Path(state['private']) / 'publication.lock'):
                if not OWNERSHIP.current[1]: require_uncancelled(state)
                return inside(A, "python3", state["container_root"] + "/agent.py", state["container_root"], action, *args, root=True)
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
        self.allow_fault = threading.Event()
        self.thread = threading.Thread(target=self.renew)
        self.thread.start()

    def renew(self):
        while not self.stopped.is_set():
            try:
                response = json.loads(agent(self.state, "renew", self.generation))
                if not response["accepted"]:
                    if self.allow_fault.is_set() and response.get("phase") == "faulted" and response.get('reason') in ('client','controller failure'): return
                    raise RuntimeError("lease renewal rejected")
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


def stop_forward(record, injection=False):
    """Retire only a durably registered, identity/specification-checked process group."""
    matching = record.get("identity") is not None and process_identity(record["pid"]) == record["identity"]
    if injection: check(matching, "injection target is not live with matching start identity")
    if matching:
        command = Path(f'/proc/{record["pid"]}/cmdline').read_bytes().split(b'\0')
        check(all(s.encode() in command for s in record["specifications"]), "forward specification identity mismatch")
        check(os.getpgid(record["pid"]) == record["pid"], "forward group identity mismatch")
        if injection: reserve(900)
        os.killpg(record["pid"], signal.SIGTERM)
        for _ in range(30):
            if process_identity(record["pid"]) != record["identity"]:
                break
            time.sleep(.1)
        else:
            os.killpg(record["pid"], signal.SIGKILL)
    for _ in range(30):
        listeners = run("ss", "-H", "-lnt")
        bindings = [s.rsplit(":", 2)[0] for s in record["specifications"]]
        if not any(binding + " " in listeners for binding in bindings):
            return
        time.sleep(.1)
    raise RuntimeError("task forward still listening")


# Root capture has its own absolute expiry even if both controller and supervisor die.
CAPTURE = r'''
import json,os,re,select,signal,stat,subprocess,sys,time
stop=sys.argv[2]
command=sys.argv[3:]
if os.path.lexists(stop): raise RuntimeError('occupied capture stop request')
end=float(sys.argv[1]); monotonic_end=time.monotonic()+max(0,end-time.time())
def remaining(): return min(end-time.time(),monotonic_end-time.monotonic())
gate="import os,sys; token=sys.stdin.buffer.read(1); sys.exit(1) if token!=b'G' else os.execvp(sys.argv[1],sys.argv[1:])"
gate_command=[sys.executable,'-c',gate,*command]
p=subprocess.Popen(gate_command,stdin=subprocess.PIPE)
identity=open('/proc/%s/stat'%p.pid).read().rsplit(')',1)[1].split()[19]
registration=dict(pid=p.pid,identity=identity,stop_request=stop,command=command,
    worker_pid=os.getpid(),worker_identity=open('/proc/self/stat').read().rsplit(')',1)[1].split()[19])
print(json.dumps(registration),flush=True)
reason='gate'; forced=False; released=False; signalled=False; convergence='not-requested'
def checked_signal(sig):
    if p.poll() is not None: return None
    fields=open('/proc/%s/stat'%p.pid).read().rsplit(')',1)[1].split()
    actual=open('/proc/%s/cmdline'%p.pid,'rb').read().split(b'\0')[:-1]
    kind='capture' if actual==[os.fsencode(a) for a in command] else 'gate' if actual==[os.fsencode(a) for a in gate_command] else None
    if fields[0]=='Z': p.wait(timeout=2); return None
    if fields[19]!=identity or kind is None: raise RuntimeError('capture identity/specification mismatch')
    if sig==signal.SIGUSR1 and kind!='capture': return None
    if sig==signal.SIGINT and kind=='capture':
        print('capture-terminal:',file=sys.stderr,flush=True)
    p.send_signal(sig)
    return kind if p.returncode is None else None
def converge():
    # Read only our already-owned stderr file; positional reads do not move its write offset.
    fd=os.open('/proc/self/fd/2',os.O_RDONLY|os.O_CLOEXEC)
    try:
        actual,expected=os.fstat(fd),os.fstat(2)
        if not stat.S_ISREG(actual.st_mode) or (actual.st_dev,actual.st_ino)!=(expected.st_dev,expected.st_ino):
            raise RuntimeError('capture statistics descriptor mismatch')
        if b'listening on ' not in os.pread(fd,65536,0): return False
        until=time.monotonic()+max(0,min(2,remaining()-7))
        previous=None; offset=os.fstat(fd).st_size
        while time.monotonic()<until and remaining()>7:
            if os.fstat(fd).st_size!=offset: return False
            if checked_signal(signal.SIGUSR1)!='capture': return False
            while time.monotonic()<until and remaining()>7 and p.poll() is None:
                data=os.pread(fd,65537,offset)
                if len(data)>65536: return False
                if b'\n' in data:
                    sample=re.fullmatch(rb'tcpdump: (\d+) packets? captured, (\d+) packets? received by filter, (\d+) packets? dropped by kernel(?:, (\d+) packets? dropped by interface)?\n',data)
                    if sample is None: return False
                    break
                time.sleep(.01)
            else: return False  # Never issue another request with an unanswered sample pending.
            offset+=len(data)
            if os.fstat(fd).st_size!=offset: return False
            counts=tuple(int(n or b'0') for n in sample.groups())
            if counts[2:]!=(0,0): return False
            good=counts[0]==counts[1]>0
            if good and previous==counts: return remaining()>7
            previous=counts if good else None
            time.sleep(min(.05,max(0,until-time.monotonic())))
        return False
    finally: os.close(fd)
def retire():
    global forced
    kind=checked_signal(signal.SIGINT)
    if kind=='gate':
        forced=True; checked_signal(signal.SIGKILL); p.wait(timeout=2)
    elif kind is not None:
        try: p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            forced=True
            checked_signal(signal.SIGKILL)
            p.wait(timeout=2)
    return kind
try:
    budget=remaining()
    if budget<=0 or not select.select([sys.stdin],[],[],budget)[0]: sys.exit(1)
    if os.read(sys.stdin.fileno(),1)!=b'G' or remaining()<=0: sys.exit(1)
    p.stdin.write(b'G'); p.stdin.close(); released=True
    while p.poll() is None:
        if remaining()<=0: reason='expiry'; break
        if os.path.lexists(stop):
            info=os.lstat(stop)
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_uid!=os.stat(os.path.dirname(stop)).st_uid:
                raise RuntimeError('capture stop request must be a private file')
            reason='requested'; break
        time.sleep(.05)
    else: reason='premature'
    if p.poll() is None:
        if reason=='requested': convergence='complete' if converge() else 'timeout'
        if remaining()<=0: reason='expiry'
        signalled=retire()=='capture'
    else: reason='premature'
    sys.exit(0 if reason=='requested' and convergence=='complete' and signalled and not forced and p.returncode==0 else 1)
finally:
    if p.poll() is None:
        if not released:
            p.stdin.close()
            try: p.wait(timeout=1)
            except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=2)
        else: retire()
    print('capture-result: '+json.dumps(dict(**registration,reason=reason,
        signalled=signalled,forced=forced,returncode=p.returncode,convergence=convergence)),file=sys.stderr,flush=True)
'''


def capture_rows(path):
    rows = []
    # A live reader may race the final write; only consume newline-complete headers.
    for line in path.read_text().split('\n')[1:-1]:
        if not line.strip(): continue  # tcpdump emits a blank separator on shutdown.
        match = re.match(r"^(\d+\.\d+) IP (\d+\.\d+\.\d+\.\d+)\.(\d+) > (\d+\.\d+\.\d+\.\d+)\.(\d+):", line)
        check(match is not None, "unparsed capture header")
        stamp, source, sport, destination, dport = match.groups()
        rows.append((float(stamp), source, int(sport), destination, int(dport)))
    return rows


def check_counter_growth(before, after):
    def counts(text):
        return [int(x) for x in re.findall(r"(?m)^\s*(\d+)\s+\d+\s+REJECT\s", text)]
    old, new = counts(before), counts(after)
    check(len(old) == len(new) == 5, "required containment counters missing")
    check(all(b >= a for a, b in zip(old, new)) and new[0] > old[0] and
          sum(new[1:]) > sum(old[1:]), "no prefix/DNS rejection counter growth")


def capture_proof(state, intervals, terminal=False):
    record = state["capture"]
    text = Path(record["stderr"]).read_text()
    check("listening on " + state["veth"] in text, "capture readiness missing")
    if terminal or 'capture-terminal:\n' in text:
        check(text.count('capture-terminal:\n') == 1 and text.count('capture-result: ') == 1,
              'capture terminal statistics boundary missing')
        text = text.split('capture-terminal:\n', 1)[1].split('capture-result: ', 1)[0]
        check(re.fullmatch(r'\d+ packets? captured\n\d+ packets? received by filter\n'
                           r'\d+ packets? dropped by kernel\n(?:\d+ packets? dropped by interface\n)?', text),
              'capture terminal statistics missing or malformed')
    counts = [re.search(r"(?m)^(\d+) packets? " + label, text)
              for label in ("captured", "received by filter", "dropped by kernel")]
    check(all(counts), "capture drop accounting missing")
    captured, received, dropped = [int(x[1]) for x in counts]
    rows = capture_rows(Path(record["stdout"]))
    check(captured == len(rows) == received > 0 and dropped == 0, "capture loss/count mismatch")
    check(any(src == state["a_ip"] and dst == state["a_bridge"] and port == 20992
              for _, src, _, dst, port in rows), "positive A-veth canary missing")
    for start, end in intervals:
        check(any(start <= stamp <= end and src == state["a_ip"] and dst == state["a_bridge"] and port == 20992
                  for stamp, src, _, dst, port in rows), "protected interval lacks a positive canary")
    check(all(int(n) == 0 for n in re.findall(r"(?m)^(\d+) packets? dropped by interface", text)), "interface capture drops")
    check_underlay(state, rows, intervals)
    return dict(captured=captured, received=received, dropped=dropped, protected_intervals=intervals)


def check_underlay(state, rows, intervals):
    network = ipaddress.ip_network(state["subnet"])
    for stamp, src, _, dst, port in rows:
        check(src == state["a_ip"] or ipaddress.ip_address(src) in network, "capture source mismatch")
        if any(start <= stamp <= end for start, end in intervals):
            check(ipaddress.ip_address(dst) not in network and port != 53, "forbidden underlay egress")


def stop_capture(state):
    with lifecycle(state):
        return stop_capture_owned(state)


def stop_capture_owned(state):
    record = state["capture"]
    record["stop_requested_at"] = time.time()
    registration = json.loads(Path(record['stdout']).read_text().splitlines()[0])
    keys = ('pid', 'identity', 'stop_request', 'command', 'worker_pid', 'worker_identity')
    check(all(record[k] == registration[k] for k in keys), 'capture registration mismatch')
    check(all(s in record['command'] for s in ('tcpdump', state['veth'], record['filter'])),
          'capture specification mismatch')
    stop = Path(record['stop_request'])
    check(stop == Path(record['stdout']).with_suffix('.stop') and
          stop.parent == Path(state['private']) and not stop.is_symlink(), 'capture stop path mismatch')
    check(not stop.exists() or (stop.is_file() and stop.stat().st_mode & 0o777 == 0o600),
          'capture stop request must be a private file')
    if not stop.exists(): private_write(stop, 'stop registered capture\n')
    for _ in range(100):
        if process_identity(record['worker_pid']) != record['worker_identity']: break
        time.sleep(.1)
    else: raise RuntimeError('capture worker did not stop')
    check(process_identity(record['pid']) != record['identity'], 'capture did not stop')
    completed = [json.loads(line.removeprefix('capture-result: '))
                 for line in Path(record['stderr']).read_text().splitlines() if line.startswith('capture-result: ')]
    check(len(completed) == 1 and all(completed[0].get(k) == record[k] for k in keys) and
           completed[0].get('reason') == 'requested' and completed[0].get('returncode') == 0 and
          completed[0].get('signalled') is True and completed[0].get('forced') is False and
          completed[0].get('convergence') == 'complete',
          'capture completion missing or failed')
    # Missing statistics are a failure even when the capture process has vanished.
    proof = capture_proof(state, record.get("intervals", []), terminal=True)
    record["stopped_at"] = time.time()
    save(state)
    return {**proof, "source": dict(record)}


def cleanup(state, explicit_off=None):
    try:
        if explicit_off is not None and state.get("authorization", {}).get("supervised_off"):
            cancel(state, explicit_off)
        with lifecycle(state, teardown=True):
            return cleanup_owned(state, explicit_off)
    except TimeoutError as error:
        errors = [str(error)]
        private_write(Path(state['private']) / ('cleanup-attempt-' + uuid.uuid4().hex + '.json'),
                      json.dumps(dict(status='FAIL', errors=errors, finished=utc().isoformat())))
        return errors


def cleanup_owned(state, explicit_off=None):
    """Idempotent, best-effort all resources; every restoration error blocks PASS."""
    errors = []
    private = Path(state["private"])
    if explicit_off is None or not state.get("authorization", {}).get("supervised_off"):
        # Ordinary failure callers may latch/retire, but cannot restore the baseline.
        if state.get("prepared"):
            try:
                check(json.loads(run("docker", "inspect", A))[0]["Id"] == state["a_id"], "A identity changed before fault")
                agent(state, "fault", state["generation"])
            except Exception as error:
                errors.append(str(error))
        errors.append("fault latched; authorized explicit trial-off required")
        private_write(private / ("fault-" + uuid.uuid4().hex + ".json"), json.dumps({"errors": errors, "state": state}))
        return errors
    with lifecycle(state, teardown=True):
        if (private / "cleaned.json").exists() and json.loads((private / "cleaned.json").read_text())["status"] == "PASS":
            return []
        if (private / "cleaned.json").exists():
            os.replace(private / "cleaned.json", private / ("cleanup-previous-" + uuid.uuid4().hex + ".json"))
        def attempt(label, fn):
            try:
                fn()
            except Exception as error:
                errors.append(label + ": " + str(error))
        private_write(private / ("trial-off-" + uuid.uuid4().hex + ".json"),
                      json.dumps({"reason": explicit_off, "time": utc().isoformat()}))
        restored = False
        if state.get("restoration_failed"):
            errors.append("previous explicit off failed; retain A journals/material without automatic retry")
        elif state.get("prepared") or state.get("a_material"):
            def restore():
                nonlocal restored
                obj = json.loads(run("docker", "inspect", A))[0]
                check(obj["Id"] == state["a_id"], "A identity changed before cleanup")
                private_write(private / ("a-before-off-" + uuid.uuid4().hex + ".json"), agent(state, "archive"))
                agent(state, "restore")
                agent(state, "join")
                result = inside(A, "cat", state["container_root"] + "/cleanup.json", root=True)
                private_write(private / ("a-cleanup-" + uuid.uuid4().hex + ".json"), result)
                check(json.loads(result)["status"] == "PASS", "explicit A restoration PASS required")
                if state.get("capture") and state["capture"].get("intervals"):
                    state["capture"]["intervals"][-1][1] = json.loads(result)["release_at"]
                    save(state)
                restored = True
            attempt("A restoration", restore)
        if state.get("capture"):
            attempt("capture stop", lambda: stop_capture(state))
        for process in state.get("forwards", []):
            if process.get("retired"): continue  # Its verified-closed binding may now belong to the fresh VPN forward.
            attempt("forward stop", lambda p=process: stop_forward(p))
        if state.get("deployed"):
            def rollback():
                import shlex
                command = ["sudo", "bash", state["upload"] + "/setup-server.sh", state["task"],
                           state["subnet"], state["deadline"], state["a_bridge"], "20990", state["receipt"], "rollback"]
                remote(shlex.join(command), timeout=180)
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
        owner = getattr(OWNERSHIP, 'current', None)
        self.private = owner[0] if owner is not None else None
        if self.private is not None: require_uncancelled({'private': self.private})
        source = (HERE / "fixtures.py").read_text()
        self.stderr_path = self.private / ('shell-' + uuid.uuid4().hex + '.stderr') if self.private else None
        stream = open(self.stderr_path, 'x', opener=lambda p,f: os.open(p,f,0o600)) if self.stderr_path else None
        try:
            self.process = subprocess.Popen(["docker", "exec", "-i", A, "bash", "--noprofile", "--norc", "-c",
                'python3 -u -c "$1" shell; :', "--", source], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=stream if stream is not None else subprocess.PIPE, text=True, bufsize=1)
        finally:
            if stream is not None: stream.close()

    def request(self, action, **values):
        if self.private is not None: require_uncancelled({'private': self.private})
        self.process.stdin.write(json.dumps({"action": action, **values}) + "\n")
        self.process.stdin.flush()
        check(select.select([self.process.stdout], [], [], 35)[0], "joined shell timeout")
        line = self.process.stdout.readline()
        if not line:
            _, error = self.process.communicate(timeout=5)
            if self.private is not None:
                private_write(self.private / ("shell-failure-" + uuid.uuid4().hex + ".json"),
                              json.dumps(dict(action=action, exit=self.process.returncode,
                                              stderr=(error or '')[-12000:], stderr_path=str(getattr(self,'stderr_path',None)), time=utc().isoformat())))
            raise ValueError("joined shell exited; see private shell-failure diagnostics")
        if self.private is not None: require_uncancelled({'private': self.private})
        result = json.loads(line)
        if action in ('baseline_probe', 'fault_probe', 'off_probe'):
            if self.private is not None:
                private_write(self.private / ('shell-probe-' + uuid.uuid4().hex + '.json'),
                              json.dumps(dict(action=action, result=result, time=utc().isoformat(),
                                              stderr_path=str(getattr(self,'stderr_path',None)))))
            if result.get('error'):
                raise ValueError('probe failed at ' + str(result['error'].get('stage')) + '; see private shell diagnostics')
        return result

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write('{"action":"quit"}\n')
            self.process.stdin.flush()
        self.process.communicate(timeout=10)


IDLE_A = r'''
import hashlib,json,pathlib
processes=[]
for p in pathlib.Path('/proc').glob('[0-9]*'):
    try:
        fields=(p/'stat').read_text().rsplit(')',1)[1].split()
        comm=(p/'comm').read_text().strip()
        if comm=='openvpn' or fields[0]=='Z':
            processes.append(dict(pid=int(p.name),comm=comm,state=fields[0],identity=fields[19]))
    except FileNotFoundError: continue
unresolved=[]; journals=[]
for p in pathlib.Path('/run').glob('ld01-cvpn*'):
    try:
        cleaned=json.loads((p/'cleanup.json').read_text())
        if (p/'active').exists() or cleaned['status']!='PASS': unresolved.append(str(p))
        journals.append(dict(path=str(p),files={name:hashlib.sha256((p/name).read_bytes()).hexdigest()
                        for name in ('restore.json','cleanup.json') if (p/name).is_file()}))
    except (OSError,ValueError,KeyError): unresolved.append(str(p))
print(json.dumps(dict(processes=processes,unresolved=unresolved,journals=journals)))
'''


def check_idle_a(expected=None):
    result = json.loads(inside(A, 'python3', '-c', IDLE_A, root=True))
    check(not result['unresolved'], 'unresolved A task journals')
    check(not any(p['comm']=='openvpn' and p['state']!='Z' for p in result['processes']), 'existing active A VPN daemon')
    zombies = [p for p in result['processes'] if p['state']=='Z']
    if expected is None:
        check({p['pid'] for p in zombies} == {1006, 1037, 1294, 1325}, 'disclosed A zombie baseline drift')
    else:
        check(canonical(zombies) == canonical(expected['zombies']), 'reconciled A zombie baseline drift')
        check(canonical(result['journals']) == canonical(expected['journals']), 'reconciled A journal baseline drift')
    for tool in ('iptables', 'ip6tables'):
        check(not re.search(r'\bLDC[0-9a-f]{12}\b', inside(A, tool, '-S', root=True)), 'unresolved A containment chain')
    return result


class Trial:
    def __init__(self, private, authorization=None):
        self.private = private
        self.baseline_only = (authorization or {}).get('mode') == 'baseline-only'
        task = "cvpn" + uuid.uuid4().hex[:12]
        self.state = {"private": str(private), "task": task, "deadline": DEADLINE,
                      "authorization": authorization or {},
                      "receipt": uuid.uuid4().hex,
                      "server_root": "/var/lib/ld01-cvpn-" + task,
                      "container_root": "/run/ld01-" + task, "forwards": [],
                      "controller_pid": os.getpid(), "controller_identity": process_identity(os.getpid())}
        self.evidence = {"started": utc().isoformat(), "status": "FAIL", "cycles": []}
        self.shells, self.holds = [], []
        self.lease = None
        self.vpn_hold = None

    def preflight(self):
        reserve()
        authorize(self.state["authorization"], baseline_only=self.baseline_only)
        baseline_dir = diagnostic_inputs(self.state['authorization']) if self.baseline_only else BASELINE
        run('sudo', '-n', 'python3', '-c',
            "import os,shutil,sys; sys.exit(0 if os.geteuid()==0 and shutil.which('tcpdump') else 1)")
        branch = 'fix/n2-baseline-diagnostic' if self.baseline_only else 'feat/n2-vpn-failure-containment'
        worktree = ROOT if self.baseline_only else Path('/tmp/opencode/termux-vm-n2-vpn-failure-containment')
        check(run("git", "branch", "--show-current").strip() == branch, "wrong worktree branch")
        check(Path.cwd().resolve() == worktree, "wrong worktree")
        resources = json.loads((baseline_dir / "resources.json").read_text())
        baseline_name = 'baseline.json' if self.baseline_only else 'spot-check-20261019T152932087625Z.json'
        baseline = json.loads((baseline_dir / baseline_name).read_text())
        image = json.loads((baseline_dir / "image.json").read_text())["image"]["Id"]
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
        check_ports(((self.state["a_bridge"], 20990), (self.state["a_bridge"], 20992),
                     (self.state["b_bridge"], 20991), ("127.0.0.1", 20991)))
        check(inside(A, "test", "!", "-e", self.state["container_root"], root=True) == "", "occupied A task path")
        links = json.loads(inside(A, "ip", "-j", "link", "show"))
        check(not any(x["ifname"] == "ld01tun" for x in links), "occupied A tunnel")
        self.evidence['idle_a'] = check_idle_a(self.state['authorization']['residuals'] if self.baseline_only else None)
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
        # The approved metadata-only reconciliation record must include full endpoints.
        metadata = Path(self.state["authorization"]["retained_metadata"])
        check(metadata.stat().st_mode & 0o777 == 0o600 and metadata.parent.stat().st_mode & 0o777 == 0o700,
              "retained metadata must be private (0700/0600)")
        check(Path.cwd().resolve() not in metadata.resolve().parents, "retained metadata must remain outside Git")
        retained = json.loads(metadata.read_text())
        for obj in objects:
            old = retained[obj["Name"].lstrip("/")]
            for key in ("Id", "Image", "Config", "HostConfig", "NetworkSettings"):
                check(obj[key] == old[key], "retained full configuration/endpoint drift: " + key)
            check(mounts(obj) == mounts(old), "retained mount drift")
        # Identify A's exact peer by ifindex, then check its Docker endpoint address.
        peer = int(inside(A, "cat", "/sys/class/net/eth0/iflink").strip())
        host_links = json.loads(run("ip", "-d", "-j", "link", "show"))
        matches = [link for link in host_links if link["ifindex"] == peer]
        check(len(matches) == 1 and matches[0].get("linkinfo", {}).get("info_kind") == "veth", "A veth identity unavailable")
        self.state["veth"] = matches[0]["ifname"]
        self.state["veth_identity"] = {key: matches[0].get(key) for key in
                                       ("ifindex", "address", "link_index", "master", "link_netnsid")}
        self.state["a_ip"] = next(iter(objects[0]["NetworkSettings"]["Networks"].values()))["IPAddress"]
        self.evidence["processes_before"] = inside(A, "ps", "-eo", "pid,ppid,stat,comm")
        check(run("pgrep", "-af", "[t]rial.py") .count("--private-dir") <= 1, "overlapping controller")
        self.evidence["preflight"] = {"containers": objects, "networks": networks, "volumes": volumes, "vm": cloud,
                                      "subnet": str(chosen)}
        save(self.state)

    @mutating
    def deploy(self):
        reserve(900)
        task = self.state["task"]
        upload = "/tmp/ld01-upload-" + task
        # Fresh source-only upload. No key/profile is sent in command arguments.
        payload = {"setup-server.sh": (HERE / "setup-server.sh").read_text(),
                   "fixtures.py": (HERE / "fixtures.py").read_text(),
                   "authorization.json": json.dumps(self.state["authorization"])}
        script = ("import json,os,pathlib,sys; os.umask(0o077); p=pathlib.Path(" + repr(upload) + "); p.mkdir(mode=0o700); "
                  "files=json.load(sys.stdin); [(p/k).write_text(v) for k,v in files.items()]")
        import shlex
        self.state["upload"] = upload
        # Mark before deployment: even partial setup needs scoped rollback.
        self.state["deployed"] = True
        save(self.state)
        remote("python3 -c " + shlex.quote(script), data=json.dumps(payload))
        require_uncancelled(self.state)
        command = ["sudo", "bash", upload + "/setup-server.sh", task, self.state["subnet"], DEADLINE,
                   self.state["a_bridge"], "20990", self.state["receipt"]]
        try:
            remote("umask 077; " + shlex.join(command) + " > " + upload + "/setup.log 2>&1", timeout=COMMAND_TIMEOUT)
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
        check(not any(self.evidence["packages"].values()), "VM packages changed")

    @mutating
    def forward(self, name, specifications):
        reserve()
        stream = open(self.private / (name + "-" + uuid.uuid4().hex + "-forward.log"), "x", opener=lambda p, f: os.open(p, f, 0o600))
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
            with file_lock(self.private / 'publication.lock'):
                require_uncancelled(self.state)
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

    def start_hold(self, name, container=None, vpn=False):
        require_uncancelled(self.state)
        source = (HERE / "fixtures.py").read_text()
        host = self.state["server"] if vpn else (self.state["a_bridge"] if container == A else
               self.state["b_bridge"] if container else "127.0.0.1")
        port = "19091" if vpn else "20992" if container == A else "20991"
        command = ["python3", "-u", "-c", source, "fault-hold" if vpn else "hold", "--host", host, "--port", port]
        if container:
            command = ["docker", "exec", "-i", container, *command]
        path = self.private / (name + "-heartbeat.jsonl")
        stream = open(path, "x", opener=lambda p, f: os.open(p, f, 0o600))
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stream, stderr=stream, text=True)
        stream.close()
        if vpn: self.vpn_hold = (process, path)
        else: self.holds.append((process, path))
        for _ in range(60):
            require_uncancelled(self.state)
            check(process.poll() is None, name + " heartbeat startup failed")
            if path.stat().st_size:
                check(json.loads(path.read_text().splitlines()[0])["kind"] == "ack", "invalid heartbeat start")
                return
            time.sleep(0.1)
        raise TimeoutError("heartbeat startup timeout")

    def health(self, expected_fault=False):
        reserve()
        if hasattr(self, "watchdog"):
            check(self.watchdog.poll() is None, "independent supervisor failed")
        capture = self.state.get("capture", {})
        if capture.get("ready_at"):
            check(process_identity(capture["pid"]) == capture["identity"], "capture process failed")
        check(self.lease is None or self.lease.error is None, "independent lease renewal failed")
        for p, _ in self.holds:
            check(p.poll() is None, "held heartbeat failed")
        for record in self.state["forwards"]:
            if record.get("retired") or (record.get("intentionally_stopped") and expected_fault):
                continue
            check(process_identity(record["pid"]) == record["identity"], "forward transport failed")
        if self.state.get("prepared"):
            status = json.loads(agent(self.state, "status", self.state["generation"]))
            check(status["active"], "unexpected A off/restoration")
            check(status['intent'].get('reason') != 'watcher lost', "A watcher lost after registration")
            check(status['intent'].get('reason') not in ('lease','deadline'), "unexpected A lease/deadline fault")
            if status.get('watcher_registered') and status['intent']['phase'] != 'faulted':
                check(status['watcher_live'] and not status['watcher_done'], "A watcher lost after registration")
            if not expected_fault:
                check(status["intent"]["phase"] != "faulted", "A fault latch active")
            return status

    @mutating
    def prepare(self):
        reserve()
        root = self.state["container_root"]
        self.state["a_material"] = True
        save(self.state)
        inside(A, "python3", "-c", "import os,sys; os.umask(0o077); os.mkdir(sys.argv[1],0o700)", root, root=True)
        for name, value in (("agent.py", AGENT), ("client.ovpn", self.profile),
                            ("authorization.json", json.dumps(self.state["authorization"]))):
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

    @mutating
    def connect(self, record, initiator=0):
        reserve()
        check(not self.state.get("prepared"), "explicit off required before connect")
        record["request_connect"] = self.shells[initiator].request("connect")
        self.state["prepared"] = True
        generation = uuid.uuid4().hex
        self.state["generation"] = generation
        save(self.state)
        record["protected_at"] = time.time()
        if self.state.get("capture"):
            self.state["capture"]["intervals"].append([record["protected_at"],
                dt.datetime.fromisoformat(self.state["deadline"].replace("Z", "+00:00")).timestamp()])
            save(self.state)
        try:
            record["a_before"] = json.loads(agent(self.state, "prepare", generation, self.state["server"], self.state["subnet"]))
            self.lease = Lease(self.state, generation)
            agent(self.state, "launch_watch", generation)
            for _ in range(40):
                status = self.health()
                if status["watcher_ready"] and status["watcher_live"]:
                    break
                time.sleep(.1)
            else:
                raise TimeoutError("A watcher did not register")
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
            record["probes"] = self.probe_shells("baseline_probe")
            record["connected_routes"] = snapshot(A)
            routes = record["connected_routes"]["-4route"]
            check(any(r.get("dst") == self.state["subnet"] and r.get("dev") == "ld01tun" for r in routes), "VPN subnet route missing")
            check([r for r in routes if r.get("dev") != "ld01tun"] == self.a_before["-4route"], "non-VPN IPv4 routes changed")
            self.negative_probes(record)
            record["siblings"] = self.siblings()
            agent(self.state, "connected", generation)
            self.health()
        except BaseException:
            # A failed start is a fault, never an implicit request to release protection.
            agent(self.state, "fault", generation)
            raise

    def probe_shells(self, action):
        def request(shell):
            require_uncancelled(self.state)
            probe = shell.request(action, server=self.state['server'], direct=self.state['a_bridge'])
            require_uncancelled(self.state)
            return probe
        with ThreadPoolExecutor(max_workers=2) as executor:
            probes = list(executor.map(request, self.shells))
        for identity, probe in zip(self.evidence["shells"], probes):
            check(probe["identity"] == identity, "joined shell identity changed")
            check(probe["direct"]["seq"] == 1 and probe["direct"]["connection"], "direct canary failed")
            if action == "baseline_probe":
                check(probe["http"] == {"fixture": self.state["task"], "service": "service.ld01.test"}, "HTTP fixture mismatch")
            if action == "fault_probe":
                check(not probe["application"] and not probe["application_aaaa"] and probe["http"] is None and
                      not any(d["responded"] for d in probe["dns"]) and not probe["public_dns"], "fault probe escaped containment")
        return probes

    @mutating
    def off(self, record):
        record["request_disconnect"] = self.shells[1].request("disconnect")
        if self.lease is not None:
            self.lease.stop()
            self.lease = None
        record["before_off"] = json.loads(agent(self.state, "status", self.state["generation"]))
        private_write(self.private / ("before-off-" + uuid.uuid4().hex + ".json"), agent(self.state, "archive"))
        record["off_requested_at"] = time.time()
        try:
            agent(self.state, "restore", self.state["generation"])
            agent(self.state, "join")
            check(snapshot(A) == self.a_before, "A routes/rules/resolver not exactly restored")
            record["a_cleanup"] = json.loads(inside(A, "cat", self.state["container_root"] + "/cleanup.json", root=True))
            check(record["a_cleanup"]["status"] == "PASS", "A cleanup failed")
        except BaseException:
            self.state["restoration_failed"] = True
            save(self.state)
            raise
        self.state["prepared"] = False
        save(self.state)
        record["off_requested_at"] = record["a_cleanup"]["release_at"]
        if self.state.get("capture"):
            self.state["capture"]["intervals"][-1][1] = record["off_requested_at"]
            save(self.state)
        record["off_probes"] = self.probe_shells("off_probe")

    @mutating
    def start_capture(self):
        reserve(900)
        self.check_veth()
        expression = (f"(dst net {self.state['subnet']} or "
                      f"((udp or tcp) and dst port 53) or (dst host {self.state['a_bridge']} and tcp and "
                      "(dst port 20990 or dst port 20992)))")
        stem = "capture-" + uuid.uuid4().hex
        output, error = self.private / (stem + ".headers"), self.private / (stem + ".stats")
        stop = self.private / (stem + '.stop')
        with open(output, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stdout, \
                open(error, "x", opener=lambda p, f: os.open(p, f, 0o600)) as stderr:
            end = dt.datetime.fromisoformat(self.state["deadline"].replace("Z", "+00:00")).timestamp() - 600
            process = subprocess.Popen(["sudo", "-n", "python3", "-u", "-c", CAPTURE, str(end), str(stop),
                "tcpdump", "--immediate-mode", "-i", self.state["veth"], "-Q", "in", "-nn", "-tt", "-q", "-l", "-s", "96", expression],
                stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
        self.capture_process = process
        try:
            for _ in range(50):
                check(process.poll() is None, "capture startup failed")
                lines = output.read_text().splitlines()
                if lines: break
                time.sleep(.1)
            else: raise TimeoutError("capture registration timeout")
            self.state["capture"] = {**json.loads(lines[0]), "stdout": str(output), "stderr": str(error),
                                     "filter": expression, "intervals": [], "registered_at": time.time()}
            save(self.state)
            with file_lock(self.private / 'publication.lock'):
                require_uncancelled(self.state)
                process.stdin.write(b"G"); process.stdin.flush()
        finally:
            process.stdin.close()
        for _ in range(50):
            check(process.poll() is None, "capture exited before readiness")
            if "listening on " + self.state["veth"] in error.read_text():
                self.state["capture"]["ready_at"] = time.time()
                save(self.state)
                return
            time.sleep(.1)
        raise TimeoutError("capture readiness timeout")

    def capture_ready(self):
        self.check_veth()
        record = self.state["capture"]
        check(process_identity(record["pid"]) == record["identity"], "capture died")
        rows = capture_rows(Path(record["stdout"]))
        check_underlay(self.state, rows, record["intervals"])
        check(any(src == self.state["a_ip"] and dst == self.state["a_bridge"] and port == 20992
                  for _, src, _, dst, port in rows), "capture has no positive A canary")

    def check_veth(self):
        links = json.loads(run("ip", "-d", "-j", "link", "show", "dev", self.state["veth"]))
        check(len(links) == 1 and links[0].get("linkinfo", {}).get("info_kind") == "veth" and
              {key: links[0].get(key) for key in self.state["veth_identity"]} == self.state["veth_identity"],
              "A-veth identity drift")

    def siblings(self):
        check(snapshot() == self.host_before and snapshot(B) == self.b_before, "host/B routes/rules/DNS changed")
        source = (HERE / "fixtures.py").read_text()
        results = []
        for container, host in ((None, "127.0.0.1"), (B, self.state["b_bridge"])):
            execute = (lambda *args: inside(container, *args)) if container else run
            result = json.loads(execute("python3", "-c", source, "fresh", "--host", host, "--port", "20991"))
            check(result["seq"] == 1 and result["connection"], "fresh host/B canary failed")
            results.append(result)
        return results

    def observe_transport_loss(self, record):
        observation = record['live_client_transport_loss'] = dict(start=time.monotonic())
        observation['before'] = self.health(expected_fault=True)
        check(observation['before']['daemon_live'], 'live-client transport-loss interval unavailable')
        self.capture_ready()
        observation['probes'] = self.probe_shells('fault_probe')
        observation['siblings'] = self.siblings()
        until = time.monotonic() + 6
        while True:
            self.capture_ready()
            check(self.vpn_hold[0].poll() is None, 'held VPN probe exited')
            held = [json.loads(line) for line in self.vpn_hold[1].read_text().splitlines()]
            attempts = [r for r in held if r['kind']=='attempt' and r['monotonic']>=observation['start']]
            observation['after'] = self.health(expected_fault=True)
            check(observation['after']['daemon_live'], 'client exited before live-transport probes completed')
            if attempts: break
            check(time.monotonic() < until, 'no held-flow attempt during live-client transport loss')
            time.sleep(.1)
        observation.update(held_attempts=attempts, finished=time.monotonic())

    def cycle(self, number):
        check(not self.baseline_only, 'fault campaign prohibited in baseline-only mode')
        record = {"case": "F1" if number == 0 else "F2", "started": utc().isoformat(), "status": "FAIL"}
        self.evidence["cycles"].append(record)
        self.start_capture()
        baseline = record["baseline"] = {}
        self.connect(baseline, number)
        self.start_hold("vpn-" + record["case"], A, vpn=True)
        self.capture_ready()
        record["counters_before"] = self.health()["counters"]
        with lifecycle(self.state):
            reserve(900)  # Recheck after the positive baseline consumed time.
            self.lease.allow_fault.set()
            record["injected_monotonic"] = time.monotonic()
            record["injected_at"] = time.time()
            if number == 0:
                agent(self.state, "kill_client", self.state["generation"])
            else:
                vpn = next(p for p in self.state["forwards"] if p["name"] == "vpn" and not p.get("retired"))
                with file_lock(self.private / 'publication.lock'):
                    require_uncancelled(self.state)
                    stop_forward(vpn, injection=True)
                vpn["intentionally_stopped"] = True
                save(self.state)
        deadline = record['injected_monotonic'] + 60
        if number == 1:
            self.observe_transport_loss(record)
            agent(self.state, "fault", self.state["generation"])
        record["observations"] = []
        while True:
            status = self.health(expected_fault=True)
            self.capture_ready()
            check(self.vpn_hold[0].poll() is None, "held VPN probe exited")
            record["observations"].append(dict(time=time.time(), status=status, probes=self.probe_shells("fault_probe")))
            record["observations"][-1]["siblings"] = self.siblings()
            if time.monotonic() >= deadline: break
            time.sleep(.5)
        check(status["intent"]["phase"] == "faulted", "fault was not latched")
        record["observed_until_monotonic"] = time.monotonic()
        record["held_vpn"] = str(self.vpn_hold[1])
        held = [json.loads(line) for line in self.vpn_hold[1].read_text().splitlines()]
        check(not any(r["kind"] == "blocked" and r["monotonic"] < record["injected_monotonic"] for r in held),
              "held VPN flow failed before injection")
        check(any(r["kind"] == "blocked" and record["injected_monotonic"] <= r["monotonic"] <=
                  record["observed_until_monotonic"] for r in held), "held VPN fault observation missing")
        record["counters_after"] = self.health(expected_fault=True)["counters"]
        check_counter_growth(record["counters_before"], record["counters_after"])
        private_write(self.private / ("fault-evidence-" + record["case"] + ".json"), json.dumps(record, indent=2))
        self.off(baseline)
        if number == 1:
            with lifecycle(self.state):
                vpn["retired"] = True
                save(self.state)
            self.forward("vpn", vpn["specifications"])
        recovery = record["recovery"] = {}
        self.connect(recovery)
        self.off(recovery)
        self.state["capture"]["intervals"] = [[r["protected_at"], r["off_requested_at"]] for r in (baseline, recovery)]
        save(self.state)
        record["capture"] = stop_capture(self.state)
        check(self.capture_process.wait(timeout=10) == 0, "capture process failed")
        self.state.pop("capture")
        save(self.state)
        process, path = self.vpn_hold
        process.communicate("stop\n", timeout=10)
        self.vpn_hold = None
        check(process.returncode == 0, "held VPN probe failed")
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        check(rows[0]["kind"] == "ack" and any(r["kind"] == "blocked" for r in rows) and
              rows[-1]["kind"] == "finished" and rows[-1]["reconnects"] == 0, "held VPN observation missing")
        check(all(r["socket"] == rows[0]["socket"] for r in rows), "held VPN socket identity changed")
        record["held_vpn"] = str(path)
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

    def baseline(self):
        """Exactly one normal connection and off; never invoke either fault case."""
        check(self.baseline_only, 'baseline-only approval required')
        record = dict(case='baseline-only', status='FAIL', started=utc().isoformat())
        self.evidence['cycles'].append(record)
        self.start_capture()
        self.connect(record)
        self.capture_ready()
        self.off(record)
        record['capture'] = stop_capture(self.state)
        check(self.capture_process.wait(timeout=10) == 0, 'capture process failed')
        self.state.pop('capture')
        save(self.state)
        record.update(status='PASS', finished=utc().isoformat())

    def execute(self):
        try:
            self.preflight()
            # Independent host watchdog survives controller termination. Server
            # units and the A lease watchdog independently bound remote/VPN life.
            watchdog_log = open(self.private / "watchdog.log", "x", opener=lambda p, f: os.open(p, f, 0o600))
            inherited = (self.exclusive_fd,) if hasattr(self, 'exclusive_fd') else ()
            self.watchdog = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--watch", str(self.private / "state.json"),
                *(['--exclusive-fd', str(self.exclusive_fd)] if inherited else [])],
                stdout=watchdog_log, stderr=watchdog_log, start_new_session=True, pass_fds=inherited)
            watchdog_log.close()
            for _ in range(50):
                check(self.watchdog.poll() is None, "supervisor exited before readiness")
                if (self.private / "supervisor-ready.json").exists(): break
                time.sleep(.1)
            else: raise TimeoutError("supervisor readiness timeout")
            self.deploy()
            self.forward("heartbeat", ["127.0.0.1:20991:127.0.0.1:19090", self.state["b_bridge"] + ":20991:127.0.0.1:19090",
                                       self.state["a_bridge"] + ":20992:127.0.0.1:19090"])
            self.forward("vpn", [self.state["a_bridge"] + ":20990:127.0.0.1:11940"])
            self.host_before, self.b_before, self.a_before = snapshot(), snapshot(B), snapshot(A)
            self.evidence.update(host_before=self.host_before, b_before=self.b_before)
            self.start_hold("host")
            self.start_hold("b", B)
            self.start_hold("a-direct", A)
            self.prepare()
            if self.baseline_only:
                self.baseline()
            else:
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
            # Persist failed observations before any pre-authorized abort off.
            private_write(self.private / "before-teardown.json", json.dumps(self.evidence, indent=2))
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
            if self.vpn_hold is not None:
                try: self.vpn_hold[0].communicate("stop\n", timeout=10)
                except Exception: self.evidence.setdefault("teardown_errors", []).append("VPN hold did not stop")
            errors = cleanup(self.state, explicit_off="campaign completion" if self.evidence["status"] == "PASS" else "supervised abort")
            self.evidence["cleanup_errors"] = errors
            if hasattr(self, "watchdog"):
                try:
                    check(self.watchdog.wait(timeout=5) == 0, "supervisor failed")
                    if (self.private / "supervisor-result.json").exists():
                        raise RuntimeError("independent supervisor aborted the campaign")
                except Exception as error:
                    self.evidence.setdefault("teardown_errors", []).append(str(error))
            if errors or self.evidence.get("teardown_errors"):
                self.evidence["status"] = "FAIL"
            if hasattr(self, "a_before"):
                try:
                    check(snapshot(A) == self.a_before and snapshot() == self.host_before and snapshot(B) == self.b_before,
                          "final A/host/B routes/rules/resolver drift")
                    current = json.loads(run("docker", "inspect", A, B))
                    for old, new in zip(self.objects, current):
                        check(all(old[k] == new[k] for k in ("Id", "Image", "Config", "HostConfig", "NetworkSettings")) and
                              mounts(old) == mounts(new), "final retained resource drift")
                    self.evidence["processes_after"] = inside(A, "ps", "-eo", "pid,ppid,stat,comm")
                except Exception as error:
                    self.evidence.setdefault("teardown_errors", []).append(str(error))
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
    private_write(path.parent / "supervisor-ready.json", json.dumps({"pid": os.getpid(), "time": utc().isoformat()}))
    while True:
        state = json.loads(path.read_text())
        if (path.parent / "cleaned.json").exists() and json.loads((path.parent / "cleaned.json").read_text())["status"] == "PASS":
            return
        # A completed failed teardown requires a human-directed retry, not a second worker.
        failed = [p for p in path.parent.glob('cleanup-attempt-*.json') if json.loads(p.read_text())["status"] == "FAIL"]
        if failed:
            private_write(path.parent / "supervisor-result.json", json.dumps(dict(
                campaign_status="FAIL", cleanup_status="FAIL", reason="retain failed teardown; no automatic retry")))
            return
        lost = process_identity(state["controller_pid"]) != state["controller_identity"]
        expired = remaining(deadline=state["deadline"]) <= 600
        if lost or expired:
            fault_errors = []
            try:
                cancel(state, 'supervisor controller loss' if lost else 'supervisor expiry')
                # One bounded ownership/teardown budget covers both latch and off.
                with lifecycle(state, teardown=True):
                    fault_errors = cleanup(state)
                    errors = ["supervised off was not authorized"]
                    if state.get("authorization", {}).get("supervised_off"):
                        errors = cleanup(state, explicit_off="supervised controller-loss off" if lost else "supervised expiry off")
            except TimeoutError as error:
                errors = [str(error)]
                private_write(path.parent / ('cleanup-attempt-' + uuid.uuid4().hex + '.json'),
                              json.dumps(dict(status='FAIL', errors=errors, finished=utc().isoformat())))
            private_write(path.parent / "supervisor-result.json", json.dumps(dict(
                campaign_status="FAIL", cleanup_status="FAIL" if errors else "PASS", fault_errors=fault_errors,
                cleanup_errors=errors, time=utc().isoformat())))
            return
        time.sleep(1)


def main():
    global DEADLINE, CANCEL
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path)
    parser.add_argument("--authorization", type=Path, help="fresh private execution scope/window approval JSON")
    parser.add_argument('--baseline-only', action='store_true', help='one diagnostic connection/off; no fault injection or reconnect')
    parser.add_argument("--watch", type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--exclusive-fd', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.watch:
        # Inherited open-file description retains the same flock after controller death.
        if args.exclusive_fd is not None:
            with os.fdopen(args.exclusive_fd, 'a'):
                watch(args.watch)
        else:
            watch(args.watch)
        return
    check(args.private_dir is not None, "--private-dir required")
    if args.baseline_only:
        check(args.private_dir.is_absolute() and args.private_dir.parent.is_dir() and
              args.private_dir.parent.stat().st_mode & 0o777 == 0o700 and
              ROOT not in args.private_dir.resolve().parents and
              not args.private_dir.resolve().is_relative_to('/tmp') and
              not args.private_dir.resolve().is_relative_to('/run'), 'durable private parent (0700), outside Git, required')
    else:
        check(args.private_dir.parent.resolve() == Path("/tmp/opencode"), "private directory parent mismatch")
    try:
        args.private_dir.mkdir(mode=0o700)
    except FileExistsError:
        failure = Path(tempfile.mkdtemp(prefix="controlled-vpn-rejected-", dir="/tmp/opencode"))
        private_write(failure / "evidence.json", json.dumps({"status": "FAIL", "error": "occupied private directory", "timestamp": utc().isoformat()}))
        print("FAIL: " + str(failure / "evidence.json"))
        return 1
    try:
        check(args.authorization is not None, "--authorization required; no live approval supplied")
        check(args.authorization.stat().st_mode & 0o777 == 0o600, "authorization must be private (0600)")
        check(args.authorization.parent.stat().st_mode & 0o777 == 0o700, "authorization directory must be private (0700)")
        check(Path.cwd().resolve() not in args.authorization.resolve().parents, "authorization must remain outside Git")
        approval = authorize(json.loads(args.authorization.read_text()), baseline_only=args.baseline_only)
        if args.baseline_only: diagnostic_inputs(approval)
        DEADLINE = approval["deadline"]
    except Exception as error:
        private_write(args.private_dir / "evidence.json", json.dumps({"status": "FAIL", "error": str(error), "timestamp": utc().isoformat()}))
        print("FAIL: " + str(args.private_dir / "evidence.json"))
        return 1
    CANCEL = args.private_dir / "off-requested.json"
    trial = Trial(args.private_dir.resolve(), approval)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError("controller terminated")))
    with open("/tmp/opencode/ld01-n2-exclusive.lock", "a", opener=lambda p, f: os.open(p, f, 0o600)) as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            private_write(trial.private / "evidence.json", json.dumps({"status": "FAIL", "error": "exclusive reuse lock occupied"}))
            print("FAIL: " + str(trial.private / "evidence.json"))
            return 1
        trial.exclusive_fd = lock.fileno()
        status = trial.execute()
    print(status + ": " + str(trial.private / "evidence.json"))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
