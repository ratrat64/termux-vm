#!/bin/bash
# Run as root from a fresh private upload directory. No public listeners or NAT.
set -euo pipefail
umask 077
task=${1:?task}; subnet=${2:?subnet}; deadline=${3:?UTC deadline}
bridge=${4:?A bridge}; forward_port=${5:?forward port}
receipt=${6:?ownership receipt}
root=/var/lib/ld01-cvpn-$task
prefix=ld01-$task
source_dir=$(dirname "$(readlink -f "$0")")
mode=${7:-setup}
python3 - "$source_dir/authorization.json" "$deadline" "$mode" <<'PY'
import datetime, json, sys
approval = json.load(open(sys.argv[1]))
def check(value):
    if not value: raise ValueError('fresh campaign authorization mismatch')
check(approval['deadline'] == sys.argv[2])
start, end = [datetime.datetime.strptime(approval[k], '%Y-%m-%dT%H:%M:%SZ') for k in ('start', 'deadline')]
baseline = approval.get('mode') == 'baseline-only'
check(0 < (end-start).total_seconds() <= (1800 if baseline else 2700))
check(all(approval.get(k) is True for k in ('observation','exclusive_reuse','supervised_off')))
if baseline:
    check(approval.get('injection') is False and approval.get('cases') == [])
    check(approval.get('post_reboot_reconciled') is True)
else:
    check(approval.get('mode','n2') == 'n2' and approval.get('injection') is True)
    check(approval.get('cases') == ['F1', 'F2'])
check(approval.get('targets') == ['tvm-share-ld01-a','free-vm','A-veth','example.com'])
if sys.argv[3] != 'rollback':
    check(start <= datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) < end-datetime.timedelta(minutes=10))
PY
[[ $task =~ ^cvpn[0-9a-f]{12}$ && $receipt =~ ^[0-9a-f]{32}$ ]] || exit 1
end_epoch=$(date -u -d "$deadline" +%s)

cleanup_reserve() {
    remaining=$(( end_epoch - $(date -u +%s) - 600 ))
    (( remaining > 0 )) && [[ ! -e $source_dir/cancelled ]]
}

rollback_units() {
    local failed=0 service unit
    if [[ -e $root ]]; then
        [[ $(< "$root/receipt") == "$receipt" ]] || return 1
    fi
    for service in http dns heartbeat vpnheartbeat vpn; do
        unit=$prefix-$service.service
        if [[ -f /etc/systemd/system/$unit ]] && ! systemctl stop "$unit"; then
            failed=1
            continue  # Keep the unit definition for an explicit teardown retry.
        fi
        if systemctl is-active --quiet "$unit"; then failed=1; continue; fi
        rm -f "/etc/systemd/system/$unit"
    done
    systemctl daemon-reload || failed=1
    return "$failed"
}

if [[ $mode == rollback ]]; then
    # Publish cancellation before waiting: a queued/late setup cannot start later.
    touch "$source_dir/cancelled"
    exec 9>"$source_dir/lifecycle.lock"
    flock -w 90 9 || exit 1
    # The setup worker (and its timeout-controlled children) have now terminated.
    rollback_units
    exit $?
elif [[ $mode == setup ]]; then
    cleanup_reserve
    budget=$remaining
    (( budget <= 80 )) || budget=80
    # Bound the whole worker, including lock acquisition, packages and services.
    exec timeout --signal=TERM --kill-after=5s "${budget}s" bash "$0" "${@:1:6}" worker
elif [[ $mode != worker ]]; then
    exit 1
fi

exec 9>"$source_dir/lifecycle.lock"
flock -w 8 9
cleanup_reserve

# All collision/deadline checks precede packages, directories, keys and units.
python3 - "$task" "$subnet" "$deadline" "$bridge" "$forward_port" "$root" "$receipt" <<'PY'
import datetime, ipaddress, json, pathlib, re, socket, subprocess, sys
def check(value, message):
    if not value: raise ValueError(message)
task, subnet, deadline, bridge, port, root, receipt = sys.argv[1:]
check(re.fullmatch(r'cvpn[0-9a-f]{12}', task), 'invalid task identity')
check(re.fullmatch(r'[0-9a-f]{32}', receipt), 'invalid ownership receipt')
end = datetime.datetime.fromisoformat(deadline.replace('Z', '+00:00'))
check(datetime.datetime.now(datetime.timezone.utc) < end - datetime.timedelta(minutes=10), 'deadline/cleanup reserve')
net = ipaddress.ip_network(subnet)
check(net.version == 4 and net.prefixlen == 24 and net.is_private, 'invalid subnet')
check(ipaddress.ip_address(bridge).version == 4 and 1024 < int(port) < 65536, 'invalid forward')
check(not pathlib.Path(root).exists(), 'occupied task path')
check(not list(pathlib.Path('/etc/systemd/system').glob('ld01-' + task + '*')), 'occupied units')
check(not pathlib.Path('/sys/class/net/ld01srv').exists(), 'occupied tunnel')
for route in json.loads(subprocess.check_output(['ip', '-4', '-j', 'route', 'show', 'table', 'all'])):
    if route.get('dst') not in (None, 'default'):
        check(not net.overlaps(ipaddress.ip_network(route['dst'], strict=False)), 'subnet collision')
for port in (11940, 19090):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', port))
PY

mkdir -m 700 "$root"
printf '%s\n' "$receipt" > "$root/receipt"
cp "$source_dir/fixtures.py" "$root/fixtures.py"
dpkg-query -W -f='${binary:Package}\t${Version}\n' > "$root/packages-before.tsv"

# Rollback retains the fresh PKI and audit files, but removes all task units.
cat > "$root/rollback.sh" <<EOF
#!/bin/bash
exec bash "$source_dir/setup-server.sh" "$task" "$subnet" "$deadline" "$bridge" "$forward_port" "$receipt" rollback
EOF
chmod 700 "$root/rollback.sh"
trap 'status=$?; if (( status != 0 )); then touch "$source_dir/cancelled"; rollback_units > "$root/rollback-failure.log" 2>&1 || true; fi' EXIT
trap 'exit 143' TERM

# Reuse retained versions. A missing prerequisite rejects this campaign; no apt action.
for binary in openvpn dnsmasq openssl python3; do command -v "$binary" >/dev/null; done
dpkg-query -W -f='${binary:Package}\t${Version}\n' > "$root/packages-after.tsv"
cd "$root"
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 2 -subj /CN=LD01-Controlled-Lab-CA \
    -keyout ca.key -out ca.crt > pki.log 2>&1
for role in server client; do
    name=lab.ld01.test; usage=serverAuth
    if [[ $role == client ]]; then name=ld01-lab-client; usage=clientAuth; fi
    openssl req -new -newkey rsa:2048 -nodes -sha256 -subj "/CN=$name" \
        -keyout "$role.key" -out "$role.csr" >> pki.log 2>&1
    printf 'basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=%s\n' "$usage" > "$role.ext"
    openssl x509 -req -in "$role.csr" -CA ca.crt -CAkey ca.key -CAcreateserial \
        -days 2 -sha256 -extfile "$role.ext" -out "$role.crt" >> pki.log 2>&1
done
openvpn --genkey secret tls-crypt.key
network=${subnet%/*}; server=${network%.*}.1
cat > server.conf <<EOF
local 127.0.0.1
port 11940
proto tcp-server
dev ld01srv
dev-type tun
topology subnet
server $network 255.255.255.0
ca $root/ca.crt
cert $root/server.crt
key $root/server.key
dh none
tls-crypt $root/tls-crypt.key
tls-version-min 1.2
remote-cert-tls client
verify-x509-name ld01-lab-client name
auth SHA256
data-ciphers AES-256-GCM:AES-128-GCM
keepalive 5 20
max-clients 1
verb 3
log $root/server.log
EOF
cat > client.ovpn <<EOF
# Requires this trial controller's IAP/SSH forward; no public VPN endpoint.
client
proto tcp-client
remote $bridge $forward_port
dev ld01tun
dev-type tun
nobind
remote-cert-tls server
verify-x509-name lab.ld01.test name
tls-version-min 1.2
auth SHA256
data-ciphers AES-256-GCM:AES-128-GCM
route-nopull
auth-nocache
connect-retry-max 1
connect-timeout 10
resolv-retry 0
tls-exit
reneg-sec 0
verb 3
EOF
for entry in 'ca ca.crt' 'cert client.crt' 'key client.key' 'tls-crypt tls-crypt.key'; do
    read -r tag file <<< "$entry"
    printf '<%s>\n' "$tag" >> client.ovpn
    cat "$file" >> client.ovpn
    printf '</%s>\n' "$tag" >> client.ovpn
done
for service in vpn http dns heartbeat vpnheartbeat; do
    cleanup_reserve
    case $service in
        vpn) command="/usr/sbin/openvpn --config $root/server.conf"; after=network.target ;;
        http) command="/usr/bin/python3 $root/fixtures.py http --host $server --port 8080 --fixture $task"; after="$prefix-vpn.service" ;;
        dns) command="/usr/bin/python3 $root/fixtures.py dns --host $server --port 53"; after="$prefix-vpn.service" ;;
        heartbeat) command="/usr/bin/python3 $root/fixtures.py heartbeat --host 127.0.0.1 --port 19090"; after=network.target ;;
        vpnheartbeat) command="/usr/bin/python3 $root/fixtures.py heartbeat --host $server --port 19091"; after="$prefix-vpn.service" ;;
    esac
    cat > "/etc/systemd/system/$prefix-$service.service" <<EOF
[Unit]
Description=LD01 controlled VPN $task $service
After=$after
[Service]
Type=simple
ExecStart=$command
Restart=no
# Leave the cleanup reserve, including any delay between unit creation/start.
RuntimeMaxSec=$remaining
TimeoutStopSec=15
TimeoutStartSec=15
UMask=0077
StandardOutput=append:$root/$service-unit.log
StandardError=append:$root/$service-unit.log
EOF
    chmod 600 "/etc/systemd/system/$prefix-$service.service"
done
systemctl daemon-reload
cleanup_reserve
systemctl start "$prefix-vpn.service"
for attempt in {1..40}; do
    if ip -4 addr show dev ld01srv 2>/dev/null | grep -q "$server/24"; then break; fi
    sleep 0.25
done
ip -4 addr show dev ld01srv > tunnel.txt
for service in http dns heartbeat vpnheartbeat; do
    cleanup_reserve
    systemctl start "$prefix-$service.service"
done
for service in vpn http dns heartbeat vpnheartbeat; do systemctl is-active --quiet "$prefix-$service.service"; done
python3 - "$task" "$subnet" "$server" "$deadline" <<'PY' > server.json
import json, subprocess, sys
task, subnet, server, deadline = sys.argv[1:]
print(json.dumps(dict(task=task, subnet=subnet, server=server, deadline=deadline,
    dns_backend='fixtures.py:dns', python_executable='/usr/bin/python3',
    python=subprocess.check_output(['/usr/bin/python3', '--version'], text=True).strip(),
    openvpn=subprocess.check_output(['openvpn', '--version'], text=True).splitlines()[0],
    dnsmasq=subprocess.check_output(['dnsmasq', '--version'], text=True).splitlines()[0])))
PY
chmod 600 "$root"/*
chmod 700 "$root/rollback.sh"
