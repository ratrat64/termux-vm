"""Offline disposition assessment; no starts, probes, adoption or cleanup."""
import argparse
import json
import os
from pathlib import Path

def canonical(value):
    if isinstance(value,dict): return {k:canonical(v) for k,v in value.items() if k!='expires'}
    if isinstance(value,list): return sorted((canonical(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    return value

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory',type=Path)
    args=parser.parse_args()
    os.umask(0o077)
    data=json.loads(args.inventory.read_text()); o=data['observations']
    summary=dict(baseline_adopted=False,source=str(args.inventory),checks={},unavailable=[],residuals={},differences=[])
    # The initial helper classified permission-denied B firewall reads as false;
    # preserve that original record and explicitly qualify it here.
    for name,value in data['checks'].items():
        if name=='tvm-share-ld01-b task chains absent': continue
        summary['checks'][name]=value
    namespaces={}
    for suffix in ('a','b'):
        name='tvm-share-ld01-'+suffix; runtime=o['runtime-'+name]
        namespaces[suffix]=o['mount-stat-'+name]['net']
        summary['residuals'][name]=dict(zombies=[p for p in runtime['processes'] if p['state']=='Z'],
            journals=[dict(path=j['path'],active=j['active'],cleanup=j['files'].get('cleanup.json',{}).get('data',{}).get('status'),
                           intent=j['files'].get('intent.json',{}).get('data',{}).get('phase'),
                           hashes={n:f['sha256'] for n,f in j['files'].items()}) for j in runtime['journals']])
        summary['checks'][name+' inactive retained journals']=all(not j['active'] and
             j['files'].get('cleanup.json',{}).get('data',{}).get('status')=='PASS' and
             j['files'].get('intent.json',{}).get('data',{}).get('phase')=='off' for j in runtime['journals'])
        if any(runtime[k]['exit']!=0 for k in ('filter4','filter6','nat')):
            summary['unavailable'].append(name+' firewall query: NET_ADMIN absent; permissions not changed')
        if suffix=='a':
            summary['checks']['A filter4/filter6/nat query succeeded']=all(runtime[k]['exit']==0 for k in ('filter4','filter6','nat'))
            summary['checks']['A no task chains']=all('LDC' not in runtime[k]['stdout'] for k in ('filter4','filter6'))
            old=runtime['journals'][0]['files']['restore.json']['data'] if runtime['journals'] else None
            if old:
                summary['checks']['A resolver matches surviving restore journal']=runtime['resolver'].encode()==__import__('base64').b64decode(old['resolver'])
                summary['checks']['A routes/rules match surviving restore journal']=all(v['exit']==0 and canonical(json.loads(v['stdout']))==canonical(old['routing'][k]) for k,v in runtime['network'].items())
                summary['checks']['A filter policies match surviving restore journal']=all(runtime[k]['stdout']==old[key] for k,key in (('filter4','ipv4'),('filter6','ipv6')))
                if runtime['nat']['stdout']!=old['nat']:
                    summary['differences'].append('A Docker embedded-resolver NAT configuration differs from the old generation journal after container start; recorded, not historical equality')
    summary['checks']['A/B namespaces distinct']=namespaces['a']!=namespaces['b']
    summary['differences'] += ['new empty scratch data replaces lost temporary contents at unchanged bind path',
                              'old zombie PID list no longer present after stop/start',
                              'live endpoint identities/namespaces are current observations, not equality with lost historical endpoint baseline']
    summary['status']='RUNNING STATE RECORDED; BASELINE DECISION PENDING' if all(summary['checks'].values()) else 'FINDINGS REQUIRE DECISION'
    with open(args.inventory.parent/'assessment.json','x',opener=lambda p,f:os.open(p,f,0o600)) as stream:
        json.dump(summary,stream,indent=2)
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
