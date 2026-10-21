"""Read-only, metadata-only LD01/GCP inventory. Never adopts a baseline.

Requires explicit operator authorization. Writes private inventory outside Git;
does not start containers, VPN, services, captures, forwards or cleanup scripts.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050'
IDS = {'tvm-share-ld01-a': '3aca8c213551fa528142eb38b69990e797135e2d4d13b3273e44ecee6857e32b',
       'tvm-share-ld01-b': '99f9f43eb98c3a4c8be3d96c59d77b9ddb5296841fd9b93d5062f9b8e48c0abd'}
LABELS = dict(task='linux-docker-sharing-trial', trial='ld01', owner='opencode-linux-trial-preparation')
SCRATCH = '/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/project'
TASKS = ('cvpn7a1a8819b397', 'cvpn152283967635', 'cvpnb76f5884442f')

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def private_write(path, data):
    with open(path, 'x', opener=lambda p,f: os.open(p,f,0o600)) as stream:
        json.dump(data, stream, indent=2)
        stream.flush(); os.fsync(stream.fileno())

def stat_only(path):
    try:
        info = path.lstat()
        return dict(exists=True, mode=oct(info.st_mode & 0o777), uid=info.st_uid,
                    gid=info.st_gid, size=info.st_size, mtime_ns=info.st_mtime_ns,
                    symlink=path.is_symlink(), directory=path.is_dir())
    except FileNotFoundError:
        return dict(exists=False)

CONTAINER_READ = r'''
import hashlib,json,pathlib,subprocess
def query(*args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=5)
    return dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
root=pathlib.Path('/run')
journals=[]
for p in root.glob('ld01-cvpn*'):
    row=dict(path=str(p),active=(p/'active').exists(),files={})
    for name in ('restore.json','cleanup.json','intent.json'):
        f=p/name
        if f.is_file():
            data=f.read_bytes()
            row['files'][name]=dict(sha256=hashlib.sha256(data).hexdigest(),data=json.loads(data))
    journals.append(row)
processes=[]
for p in pathlib.Path('/proc').glob('[0-9]*'):
    try:
        fields=(p/'stat').read_text().rsplit(')',1)[1].split()
        comm=(p/'comm').read_text().strip()
        if comm=='openvpn' or fields[0]=='Z':
            processes.append(dict(pid=int(p.name),comm=comm,state=fields[0],identity=fields[19]))
    except FileNotFoundError: pass
network={family+kind:query('ip',family,'-j',kind,'show',*(['table','all'] if kind=='route' else []))
         for family in ('-4','-6') for kind in ('route','rule')}
print(json.dumps(dict(processes=processes,journals=journals,network=network,
    links=query('ip','-j','link','show'),resolver=pathlib.Path('/etc/resolv.conf').read_text(),
    filter4=query('iptables','-S'),filter6=query('ip6tables','-S'),nat=query('iptables','-t','nat','-S'))))
'''

VM_READ = r'''
import hashlib,json,pathlib,socket,subprocess
tasks=('cvpn7a1a8819b397','cvpn152283967635','cvpnb76f5884442f')
def query(*args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=10)
    return dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr)
def info(p):
    try:
        s=p.lstat()
        return dict(exists=True,mode=oct(s.st_mode&0o777),uid=s.st_uid,gid=s.st_gid,
                    size=s.st_size,mtime_ns=s.st_mtime_ns,symlink=p.is_symlink())
    except FileNotFoundError: return dict(exists=False)
directories={}
for task in tasks:
    for name in ('/var/lib/ld01-cvpn-'+task,'/tmp/ld01-upload-'+task):
        p=pathlib.Path(name); entry=info(p)
        if p.is_dir():
            # Stat entries only. Never open keys, profiles, logs or certificates.
            entry['entries']={f.name:info(f) for f in p.iterdir()}
            entry['source_hashes']={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                for f in p.iterdir() if f.is_file() and f.name in ('rollback.sh','setup-server.sh','fixtures.py')}
        directories[name]=entry
units={}
for task in tasks:
    for service in ('vpn','http','dns','heartbeat','vpnheartbeat'):
        name='ld01-'+task+'-'+service+'.service'
        units[name]=dict(file=info(pathlib.Path('/etc/systemd/system',name)),
            state=query('systemctl','show',name,'--property=LoadState,ActiveState,SubState,MainPID','--no-pager'))
print(json.dumps(dict(host=socket.gethostname(),boot_id=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    directories=directories,units=units,listeners=query('ss','-H','-lntup'),
    processes=query('ps','-eo','pid,ppid,stat,comm'),links=query('ip','-j','link','show'),
    routes=query('ip','-4','-j','route','show','table','all'),
    packages=query('dpkg-query','-W','-f=${binary:Package}\t${Version}\n',
                   'openvpn','dnsmasq-base','libjansson4','liblzo2-2','libnftables1','libpkcs11-helper1'),
    default_openvpn=query('systemctl','show','openvpn.service','--property=ActiveState,SubState,MainPID','--no-pager'))))
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorized-read-only', action='store_true')
    parser.add_argument('--private-parent', type=Path, required=True)
    args = parser.parse_args()
    if not args.authorized_read_only: parser.error('explicit read-only authorization required')
    os.umask(0o077)
    parent = args.private_parent.expanduser().resolve()
    if (not parent.is_absolute() or parent.is_relative_to('/tmp') or parent.is_relative_to('/run') or
            HERE.parents[1] in parent.parents):
        parser.error('durable private path outside Git required')
    if not parent.exists(): parent.mkdir(mode=0o700)
    if parent.stat().st_mode & 0o777 != 0o700: parser.error('private parent must be 0700')
    directory = parent / ('inspection-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(mode=0o700)
    report = dict(started=utc(),scope='authorized read-only post-reboot inventory; no baseline adoption',
                  baseline_adopted=False,commands=[],observations={},comparisons=[])
    def command(label, args, timeout=30, parse=False):
        started = utc()
        try:
            result = subprocess.run(args,capture_output=True,text=True,timeout=timeout)
            row = dict(label=label,started=started,finished=utc(),exit=result.returncode,
                       stdout=result.stdout,stderr=result.stderr)
            report['commands'].append(row)
            private_write(directory / ('command-%02d.json' % len(report['commands'])),row)
            if result.returncode: return None
            value = json.loads(result.stdout) if parse else result.stdout
            report['observations'][label] = value
            return value
        except Exception as error:
            row = dict(label=label,started=started,finished=utc(),error=str(error))
            report['commands'].append(row)
            private_write(directory / ('command-%02d.json' % len(report['commands'])),row)
            return None
    def compare(name, observed, expected, basis='historical redacted source'):
        report['comparisons'].append(dict(name=name,status='MATCH' if observed==expected else 'DIFFERENT',
                                         observed=observed,expected=expected,basis=basis))
    report['observations']['host_boot_id'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    report['observations']['scratch'] = stat_only(Path(SCRATCH))
    compare('scratch host directory exists',Path(SCRATCH).is_dir(),True)
    objects = command('containers',['docker','inspect',*IDS],parse=True)
    image = command('image',['docker','image','inspect',IMAGE],parse=True)
    nets = command('networks',['docker','network','inspect','tvm-share-ld01-net-a','tvm-share-ld01-net-b'],parse=True)
    volumes = command('volumes',['docker','volume','inspect','tvm-share-ld01-home-a','tvm-share-ld01-home-b'],parse=True)
    command('host-listeners',['ss','-H','-lntup'])
    command('host-routes',['ip','-4','-j','route','show','table','all'],parse=True)
    if image: compare('frozen image retained',image[0]['Id'],IMAGE)
    for obj in objects or []:
        name = obj['Name'].lstrip('/'); suffix=name[-1]; host=obj['HostConfig']; config=obj['Config']
        compare(name+' identity',obj['Id'],IDS[name])
        compare(name+' image',obj['Image'],IMAGE)
        compare(name+' labels',{k:config.get('Labels',{}).get(k) for k in LABELS},LABELS)
        compare(name+' running',obj['State']['Running'],True)
        compare(name+' daily user',config['User'],'1001:1001')
        compare(name+' command',config['Cmd'],['sleep','infinity'])
        compare(name+' limits',[host.get(k) for k in ('Memory','MemorySwap','NanoCpus','PidsLimit')],
                [536870912,536870912,1000000000,128])
        compare(name+' restart policy',host['RestartPolicy']['Name'],'no')
        compare(name+' capabilities',sorted((c.removeprefix('CAP_') for c in host.get('CapAdd') or [])),['NET_ADMIN'] if suffix=='a' else [])
        compare(name+' cap drop',host.get('CapDrop'),['ALL'])
        compare(name+' devices',host.get('Devices') or [],
                [dict(PathOnHost='/dev/net/tun',PathInContainer='/dev/net/tun',CgroupPermissions='rw')] if suffix=='a' else [])
        compare(name+' privileged',host.get('Privileged'),False)
        compare(name+' no-new-privileges',any(x.startswith('no-new-privileges') for x in host.get('SecurityOpt') or []),True)
        mounts={m['Destination']:m for m in obj['Mounts']}
        compare(name+' mount destinations',sorted(mounts),['/home/session','/project'])
        compare(name+' home name',mounts.get('/home/session',{}).get('Name'),'tvm-share-ld01-home-'+suffix)
        compare(name+' scratch source',mounts.get('/project',{}).get('Source'),SCRATCH)
        compare(name+' network attachment',sorted(obj['NetworkSettings']['Networks']),['tvm-share-ld01-net-'+suffix])
        if obj['State']['Running'] and not obj['State']['Paused'] and obj['Id']==IDS[name] and all(config['Labels'].get(k)==v for k,v in LABELS.items()):
            command('inside-'+suffix,['docker','exec','--user','0',name,'python3','-c',CONTAINER_READ],parse=True)
        else:
            report['observations']['inside-'+suffix] = dict(status='UNAVAILABLE',reason='container stopped/paused or retained identity/labels not verified; no start/exec attempted')
    for net in nets or []:
        name=net['Name']; subnet='172.16.0.32/28' if name.endswith('-a') else '172.16.0.48/28'
        compare(name+' labels',{k:(net.get('Labels') or {}).get(k) for k in LABELS},LABELS)
        compare(name+' subnet',[x.get('Subnet') for x in net['IPAM']['Config']],[subnet])
        compare(name+' driver/IPv6',[net['Driver'],net['EnableIPv6']],['bridge',False])
    for vol in volumes or []:
        compare(vol['Name']+' labels',{k:(vol.get('Labels') or {}).get(k) for k in LABELS},LABELS)
    # --plain and explicit BatchMode/identity suppress SSH key provisioning and prompts.
    key=Path.home()/'.ssh/google_compute_engine'
    known_hosts=Path.home()/'.ssh/google_compute_known_hosts'
    if key.is_file() and known_hosts.is_file():
        command('controlled-vm',['gcloud','compute','ssh','free-vm','--tunnel-through-iap','--plain','--quiet',
                '--ssh-flag=-oBatchMode=yes','--ssh-flag=-oControlMaster=no','--ssh-flag=-oControlPath=none',
                '--ssh-flag=-oStrictHostKeyChecking=yes','--ssh-flag=-i','--ssh-flag='+str(key),
                '--ssh-flag=-oUserKnownHostsFile='+str(known_hosts),
                '--command=sudo -n python3 -c '+shlex.quote(VM_READ)],timeout=120,parse=True)
    else:
        report['observations']['controlled-vm']=dict(status='UNAVAILABLE',reason='existing GCP SSH identity/known-hosts unavailable; no key or trust creation attempted')
    report['unverified']=['historical full Config/HostConfig/endpoint equality: lost private baseline',
                          'historical network IDs/volume metadata hashes: lost private baseline',
                          'historical private evidence content: unavailable after reboot',
                          'no new baseline is adopted by this inventory']
    report['finished']=utc()
    private_write(directory/'inventory.json',report)
    summary=dict(private_directory=str(directory),started=report['started'],finished=report['finished'],
                 baseline_adopted=False,comparisons=report['comparisons'],unverified=report['unverified'],
                 commands=[dict(label=r['label'],exit=r.get('exit'),error=r.get('error')) for r in report['commands']])
    private_write(directory/'summary.json',summary)
    print(json.dumps(dict(private_directory=str(directory),baseline_adopted=False,
                         match_count=sum(r['status']=='MATCH' for r in report['comparisons']),
                         differences=[r for r in report['comparisons'] if r['status']!='MATCH'],
                         commands=summary['commands']),indent=2))

if __name__=='__main__': main()
