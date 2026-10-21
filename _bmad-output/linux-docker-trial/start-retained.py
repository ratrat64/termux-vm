"""Explicitly authorized LD01 scratch replacement/original-container start only.

No VPN, application probe, service deployment, capture, recreation or baseline
adoption. Commands and partial failures are retained privately, without retry.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('inventory_source', Path(__file__).with_name('inspect-retained.py'))
inventory_source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_source)

def mounts(obj):
    return {m['Destination']:m for m in obj['Mounts']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorized-start-originals', action='store_true')
    parser.add_argument('--inspection', type=Path, required=True)
    args = parser.parse_args()
    if not args.authorized_start_originals: parser.error('explicit scratch/start authorization required')
    os.umask(0o077)
    prior = json.loads(args.inspection.read_text())['observations']
    parent = args.inspection.parent.parent
    if parent.stat().st_mode & 0o777 != 0o700: parser.error('private parent must be 0700')
    directory = parent / ('start-originals-' + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    directory.mkdir(mode=0o700)
    report = dict(started=inventory_source.utc(), baseline_adopted=False,
                  authorization='new empty scratch at existing bind path; start original A/B; inspect only',
                  reference_inventory=str(args.inspection),actions=[],checks={},observations={},errors=[])
    def record(name, value): inventory_source.private_write(directory/name,value)
    def check(name, value):
        report['checks'][name] = bool(value)
        if not value: raise RuntimeError(name)
    def command(label, *command, parse=False):
        result = subprocess.run(command, text=True, capture_output=True, timeout=45)
        row = dict(label=label, command=list(command), exit=result.returncode,
                   stdout=result.stdout, stderr=result.stderr, finished=inventory_source.utc())
        record('command-%02d.json' % len(report['actions']), row)
        report['actions'].append(row)
        record('progress-%02d.json' % len(report['actions']), report)
        if result.returncode: raise RuntimeError(label + ' failed (exit %s)' % result.returncode)
        return json.loads(result.stdout) if parse else result.stdout
    try:
        check('uid_gid_1001',os.getuid()==os.getgid()==1001)
        objects = command('before-containers','docker','inspect',*inventory_source.IDS,parse=True)
        report['observations']['containers_before'] = objects
        previous = {o['Name'].lstrip('/'):o for o in prior['containers']}
        for obj in objects:
            name=obj['Name'].lstrip('/')
            check(name+' original identity',obj['Id']==inventory_source.IDS[name]==previous[name]['Id'])
            check(name+' frozen image',obj['Image']==inventory_source.IMAGE)
            check(name+' stopped',not obj['State']['Running'] and not obj['State']['Paused'])
            check(name+' config unchanged',obj['Config']==previous[name]['Config'] and obj['HostConfig']==previous[name]['HostConfig'])
            check(name+' mounts unchanged',mounts(obj)==mounts(previous[name]))
            check(name+' ownership',all(obj['Config']['Labels'].get(k)==v for k,v in inventory_source.LABELS.items()))
        volumes = command('before-volumes','docker','volume','inspect','tvm-share-ld01-home-a','tvm-share-ld01-home-b',parse=True)
        networks = command('before-networks','docker','network','inspect','tvm-share-ld01-net-a','tvm-share-ld01-net-b',parse=True)
        check('home metadata unchanged',volumes==prior['volumes'])
        check('network identity unchanged',{n['Name']:n['Id'] for n in networks}=={n['Name']:n['Id'] for n in prior['networks']})
        scratch = Path(inventory_source.SCRATCH)
        base = scratch.parent
        check('approved temp parent',base.parent==Path('/tmp/opencode') and base.parent.is_dir() and not base.parent.is_symlink())
        check('scratch absent',not scratch.exists() and not scratch.is_symlink())
        check('scratch parent absent',not base.exists() and not base.is_symlink())
        record('before-mutation.json',report)
        base.mkdir(mode=0o700)
        scratch.mkdir(mode=0o700)
        check('new scratch empty',not any(scratch.iterdir()))
        report['observations']['scratch_created'] = dict(path=str(scratch),empty=True,
            uid=scratch.stat().st_uid,gid=scratch.stat().st_gid,mode=oct(scratch.stat().st_mode&0o777),
            inode=scratch.stat().st_ino,created=inventory_source.utc(),previous_contents_recovered=False)
        record('scratch-created.json',report['observations']['scratch_created'])
        for obj in objects:
            command('start-'+obj['Name'].lstrip('/'),'docker','start',obj['Id'])
        after = command('after-containers','docker','inspect',*inventory_source.IDS,parse=True)
        report['observations']['containers_after'] = after
        for old,new in zip(objects,after):
            name=new['Name'].lstrip('/')
            check(name+' original running',new['Id']==old['Id'] and new['State']['Running'] and not new['State']['Paused'])
            check(name+' retained config',all(new[k]==old[k] for k in ('Id','Image','Config','HostConfig')) and mounts(new)==mounts(old))
            check(name+' retained attachment',{n:v['NetworkID'] for n,v in new['NetworkSettings']['Networks'].items()}==
                  {n:v['NetworkID'] for n,v in old['NetworkSettings']['Networks'].items()})
            runtime = command('runtime-'+name,'docker','exec','--user','0',name,'python3','-c',inventory_source.CONTAINER_READ,parse=True)
            report['observations']['runtime-'+name] = runtime
            home = command('mount-stat-'+name,'docker','exec',name,'python3','-c',
                "import json,os,pathlib; print(json.dumps(dict(uid=os.getuid(),gid=os.getgid(),net=os.readlink('/proc/self/ns/net'),"
                "mounts={p:dict(uid=pathlib.Path(p).stat().st_uid,gid=pathlib.Path(p).stat().st_gid,"
                "inode=pathlib.Path(p).stat().st_ino,mode=oct(pathlib.Path(p).stat().st_mode&0o777)) "
                "for p in ('/home/session','/project')})))",parse=True)
            report['observations']['mount-stat-'+name] = home
            check(name+' ordinary identity',home['uid']==home['gid']==1001)
            check(name+' same new scratch inode',home['mounts']['/project']['inode']==scratch.stat().st_ino)
            check(name+' private home owner',home['mounts']['/home/session']['uid']==home['mounts']['/home/session']['gid']==1001)
            check(name+' no active openvpn',not any(p['comm']=='openvpn' and p['state']!='Z' for p in runtime['processes']))
            links=runtime['links']
            check(name+' no tunnel',links['exit']==0 and not any(i['ifname']=='ld01tun' for i in json.loads(links['stdout'])))
            if all(runtime[key]['exit']==0 for key in ('filter4','filter6')):
                check(name+' task chains absent',all('LDC' not in runtime[key]['stdout'] for key in ('filter4','filter6')))
            else:
                report['observations']['firewall-availability-'+name] = 'UNAVAILABLE: query lacks required capability; no capability added'
        final_volumes = command('after-volumes','docker','volume','inspect','tvm-share-ld01-home-a','tvm-share-ld01-home-b',parse=True)
        check('home volumes unchanged',final_volumes==volumes)
        report['observations']['networks_after'] = command('after-networks','docker','network','inspect','tvm-share-ld01-net-a','tvm-share-ld01-net-b',parse=True)
        report['observations']['host_task_listeners'] = command('host-listeners','ss','-H','-lntup')
        check('host task ports closed',not any(':'+str(p)+' ' in report['observations']['host_task_listeners'] for p in (20990,20991,20992)))
        report['status'] = 'STARTED AND INSPECTED' if all(report['checks'].values()) else 'STARTED; FINDINGS REQUIRE DECISION'
    except Exception as error:
        report['status']='PARTIAL OR BLOCKED; NO AUTOMATIC RETRY'
        report['errors'].append(type(error).__name__+': '+str(error))
    report['finished']=inventory_source.utc()
    record('inventory.json',report)
    print(json.dumps(dict(private_directory=str(directory),status=report['status'],baseline_adopted=False,
                         checks=report['checks'],errors=report['errors'],
                         scratch=report['observations'].get('scratch_created'),
                         endpoints={o['Name'].lstrip('/'):o['NetworkSettings']['Networks'] for o in report['observations'].get('containers_after',[])},
                         runtime={name:dict(processes=value.get('processes'),journal_paths=[j['path'] for j in value.get('journals',[])])
                                  for name,value in report['observations'].items() if name.startswith('runtime-')}),indent=2))

if __name__=='__main__': main()
