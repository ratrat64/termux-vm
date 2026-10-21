"""Offline assessment of inspect-retained.py JSON; no Docker/GCP commands."""
import argparse
import json
import os
from pathlib import Path

EXPECTED_PACKAGES = {'openvpn':'2.6.14-0+deb12u2','dnsmasq-base':'2.90-4~deb12u2',
                     'libjansson4':'2.14-2','liblzo2-2':'2.10-2',
                     'libnftables1':'1.0.6-2+deb12u2','libpkcs11-helper1':'1.29.0-1'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory',type=Path)
    args=parser.parse_args()
    os.umask(0o077)
    inventory=json.loads(args.inventory.read_text()); obs=inventory['observations']
    vm=obs.get('controlled-vm',{})
    assessment=dict(baseline_adopted=False,inventory=str(args.inventory),
        source_matches=sum(x['status']=='MATCH' for x in inventory['comparisons']),
        differences=[x for x in inventory['comparisons'] if x['status']!='MATCH'],
        unavailable=inventory['unverified'],checks={},observations={})
    assessment['observations']['containers']={o['Name'].lstrip('/'):dict(
        status=o['State']['Status'],exit=o['State']['ExitCode'],finished=o['State']['FinishedAt'],
        endpoints={name:dict(ip=v.get('IPAddress'),mac=v.get('MacAddress'),gateway=v.get('Gateway'))
                   for name,v in o['NetworkSettings']['Networks'].items()}) for o in obs.get('containers',[])}
    assessment['observations']['network_peers']={n['Name']:list(n['Containers']) for n in obs.get('networks',[])}
    assessment['unavailable'] += ['in-container processes/zombies/journals/routes/resolver unavailable while containers are stopped',
                                  'home volume contents not inspected; volume metadata retention is not content equality']
    listeners=obs.get('host-listeners','')
    assessment['checks']['host_task_ports_closed']=not any(':'+str(p)+' ' in listeners for p in (20990,20991,20992))
    if vm.get('host'):
        assessment['checks']['vm_identity']=vm['host']=='free-vm'
        units={name:dict(line.split('=',1) for line in row['state']['stdout'].splitlines() if '=' in line)
               for name,row in vm['units'].items()}
        assessment['checks']['vm_task_units_inactive']=all(s.get('ActiveState')=='inactive' and s.get('MainPID')=='0' for s in units.values())
        assessment['checks']['vm_task_unit_files_absent']=all(not s['file']['exists'] for s in vm['units'].values())
        assessment['checks']['vm_task_ports_closed']=vm['listeners']['exit']==0 and not any(
            ':'+str(p)+' ' in vm['listeners']['stdout'] for p in (11940,19090,19091))
        active=[line for line in vm['processes']['stdout'].splitlines() if line.split() and
                line.split()[-1]=='openvpn' and not line.split()[2].startswith('Z')]
        assessment['checks']['no_active_vm_openvpn']=vm['processes']['exit']==0 and not active
        links=json.loads(vm['links']['stdout']) if vm['links']['exit']==0 else None
        assessment['checks']['vm_task_tunnel_absent']=links is not None and not any(x['ifname']=='ld01srv' for x in links)
        packages={line.split('\t')[0].split(':')[0]:line.split('\t')[1] for line in vm['packages']['stdout'].splitlines()}
        assessment['checks']['vm_retained_package_versions']=vm['packages']['exit']==0 and packages==EXPECTED_PACKAGES
        assessment['observations']['packages']=packages
        assessment['observations']['default_openvpn']=vm['default_openvpn']['stdout']
        assessment['observations']['vm_directories']={name:dict(exists=d['exists'],mode=d.get('mode'),uid=d.get('uid'),
            files=len(d.get('entries',{}))) for name,d in vm['directories'].items()}
        assessment['checks']['vm_retained_directories_present']=all(d['exists'] for d in vm['directories'].values())
        assessment['checks']['vm_private_directory_modes']=all(d.get('mode')=='0o700' for d in vm['directories'].values())
        assessment['checks']['vm_root_directories_owned_by_root']=all(d.get('uid')==0 for n,d in vm['directories'].items() if n.startswith('/var/lib/'))
    else:
        assessment['unavailable'].append('controlled VM inspection unavailable')
    directory=args.inventory.parent
    assessment['checks']['private_permissions']=directory.stat().st_mode&0o777==0o700 and all(
        f.stat().st_mode&0o777==0o600 for f in directory.iterdir() if f.is_file())
    assessment['inspection_status']='REQUIRES DECISION' if assessment['differences'] else 'RECORDED'
    with open(directory/'assessment.json','x',opener=lambda p,f:os.open(p,f,0o600)) as stream:
        json.dump(assessment,stream,indent=2)
    print(json.dumps(assessment,indent=2))

if __name__=='__main__': main()
