"""Build private inputs from an explicitly accepted inventory, with no runtime IO.

Never creates execution authority, timestamps for a live window, credentials or
an attempt directory. Local validation compares saved observations only.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('baseline_trial', HERE/'controlled-vpn/trial.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)

def write(path, value):
    with open(path,'x',opener=lambda p,f:os.open(p,f,0o600)) as stream:
        json.dump(value,stream,indent=2)
        stream.flush(); os.fsync(stream.fileno())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check(value,message):
    if not value: raise ValueError(message)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-inventory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--acceptance-receipt',required=True)
    args=parser.parse_args()
    os.umask(0o077)
    source=args.accepted_inventory.resolve()
    assessment=source.with_name('assessment.json')
    target=args.output.expanduser().resolve()
    check(source.is_file() and assessment.is_file(), 'accepted inventory/assessment required')
    check(target.parent.is_dir() and target.parent.stat().st_mode&0o777==0o700, '0700 private parent required')
    check(not target.is_relative_to('/tmp') and not target.is_relative_to('/run') and not target.is_relative_to(trial.ROOT), 'durable external path required')
    dt.datetime.strptime(args.acceptance_receipt,'%Y-%m-%dT%H:%M:%SZ')
    data=json.loads(source.read_text()); checks=json.loads(assessment.read_text())
    check(checks['baseline_adopted'] is False and all(checks['checks'].values()), 'inspection must be complete and not previously adopted')
    observed=data['observations']
    objects=observed['containers_after']
    networks=sorted(observed['networks_after'],key=lambda n:n['Name'])
    previous_source=Path(data['reference_inventory'])
    previous=json.loads(previous_source.read_text())['observations']
    image=previous['image'][0]
    check(len(objects)==2 and len(networks)==2 and all(o['Image']==image['Id'] for o in objects), 'accepted image/resource selection mismatch')
    runtime_keys=('CapDrop','SecurityOpt','Memory','MemorySwap','NanoCpus','PidsLimit',
                  'RestartPolicy','Privileged','NetworkMode')
    resources=dict(image=image['Id'],subnets=[n['IPAM']['Config'][0]['Subnet'] for n in networks],
        resources=[dict(name=o['Name'].lstrip('/'),id=o['Id'],type='container') for o in objects]+
                  [dict(name=n['Name'],id=n['Id'],type='network') for n in networks]+
                  [dict(name=v['Name'],type='volume') for v in previous['volumes']],
        provenance='new user-accepted post-reboot reference; not recovered historical evidence')
    baseline=dict(checks={o['Name'].lstrip('/'):dict(id=o['Id'],mounts=o['Mounts'],
        runtime_config={k:o['HostConfig'][k] for k in runtime_keys},
        cap_add=o['HostConfig']['CapAdd'],devices=o['HostConfig']['Devices']) for o in objects})
    retained={o['Name'].lstrip('/'): {k:o[k] for k in ('Id','Image','Config','HostConfig','NetworkSettings','Mounts')} for o in objects}
    a=observed['runtime-'+trial.A]
    residuals=dict(zombies=[p for p in a['processes'] if p['state']=='Z'],
        journals=[dict(path=j['path'],files={name:j['files'][name]['sha256'] for name in ('restore.json','cleanup.json') if name in j['files']}) for j in a['journals']])
    check(residuals['zombies']==[], 'accepted reference specifies no zombies')
    check(all(not j['active'] and j['files']['cleanup.json']['data']['status']=='PASS' and
               j['files']['intent.json']['data']['phase']=='off' for j in a['journals']), 'retained journals must be off/PASS')
    # Trap any accidental external-command call during this offline preparation.
    def forbidden(*args,**kwargs): raise RuntimeError('runtime command prohibited in baseline preparation')
    trial.run=trial.inside=trial.remote=forbidden
    trial.reconcile(objects,resources,baseline,image['Id'])
    for net in networks:
        expected=next(o for o in objects if o['Name'].endswith(net['Name'][-1]))
        check(set(net['Containers'])=={expected['Id']}, 'network peer mismatch')
        subnet=ipaddress.ip_network(net['IPAM']['Config'][0]['Subnet'])
        check(net['IPAM']['Config']==[dict(Subnet=str(subnet),IPRange='',Gateway=str(subnet.network_address+1))], 'network IPAM mismatch')
    target.mkdir(mode=0o700)
    write(target/'resources.json',resources)
    write(target/'baseline.json',baseline)
    write(target/'image.json',dict(image=image))
    write(target/'retained-metadata.json',retained)
    write(target/'residuals.json',residuals)
    write(target/'network-state.json',{name:observed['runtime-'+name] for name in (trial.A,trial.B)})
    write(target/'volumes.json',previous['volumes'])
    write(target/'networks.json',networks)
    paths=dict(baseline_dir=str(target),retained_metadata=str(target/'retained-metadata.json'),
               residuals=residuals,post_reboot_reconciled=True,not_execution_authorization=True)
    write(target/'input-paths.json',paths)
    check(trial.diagnostic_inputs(paths)==target,'diagnostic input path validation failed')
    hashes={p.name:digest(p) for p in target.iterdir()}
    adoption=dict(accepted=True,acceptance_receipt=args.acceptance_receipt,prepared=trial.utc().isoformat(),
        authority='user accepted inspected post-reboot running state; prepare private inputs only',
        baseline_scope='new post-reboot diagnostic reference, not historical equivalence',
        evidence_sources={str(p):digest(p) for p in (source,assessment,previous_source)},
        inputs_sha256=hashes,scratch=observed['scratch_created'],
        accepted_differences=checks['differences'],unavailable=checks['unavailable'],
        retained_journal_hashes=checks['residuals'][trial.A]['journals'],
        no_live_window=True,no_execution_approval=True,no_credentials_created=True,
        validation=dict(schema=True,saved_snapshot_reconciliation=True,network_id_ipam_peers=True,
                        private_permissions=True,runtime_commands=0))
    write(target/'adoption.json',adoption)
    check(target.stat().st_mode&0o777==0o700 and all(p.stat().st_mode&0o777==0o600 for p in target.iterdir()), 'private permission mismatch')
    print(json.dumps(dict(private_baseline=str(target),accepted=True,
        local_schema_validation='PASS',snapshot_reconciliation='PASS',network_validation='PASS',
        residual_zombies=len(residuals['zombies']),retained_journals=len(residuals['journals']),
        runtime_commands=0,execution_authorization_created=False,live_window_created=False),indent=2))

if __name__=='__main__': main()
