# LD01 provisioning and host-comparison audit record

Executed 2026-10-19 in `/tmp/opencode/termux-vm-linux-docker-trial-preparation`, using Python `subprocess` for structured capture. The shell operations below expand those subprocess argument lists; they are an audit/reproduction reference, not a launcher to rerun against retained resources. Existing names must cause a stop, not replacement. Raw output is private under `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/`.

## Initial checks and private scratch allocation

```bash
docker image inspect tvm-eval-dhlrhsji:foundation --format '{{.Id}}'
docker ps -a --filter name=tvm-share-ld01- --format '{{.Names}}'
docker network ls --filter name=tvm-share-ld01- --format '{{.Name}}'
docker volume ls --filter name=tvm-share-ld01- --format '{{.Name}}'
docker image ls tvm-share-ld01:tooling --format '{{.ID}}'
ls -ld /tmp/opencode
mktemp -d /tmp/opencode/linux-docker-sharing-ld01.XXXXXXXX
```

The foundation ID had to equal `sha256:831666c75ae440c43933711269a44181e946e6bec156e7e1dddd3c8002886afb`; all proposed-name listings were empty. `mktemp` produced `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM`, mode 0700. With `os.umask(0o077)`, `Path(trial_dir, 'project').mkdir()` initialized fresh scratch; Docker populated each new home volume from the image's `/home/session` defaults. No source home or original project was copied.

## Host snapshot before building

The inline Python snapshot command captured `returncode`, `stdout`, `stderr` for each list below with `subprocess.run(..., text=True, capture_output=True, timeout=30)`. It recorded a UTC ISO timestamp and **names only** of configured `http_proxy`, `https_proxy`, `all_proxy`, `no_proxy` environment variables, compared case-insensitively. It inspected the IDs from `docker network ls --quiet` and stored their complete pre-existing metadata. The resulting dictionary was written to `host-before.json` under umask 077.

```python
commands = [
    ['ip', '-j', 'route', 'show', 'table', 'all'],
    ['ip', '-6', '-j', 'route', 'show', 'table', 'all'],
    ['ip', '-j', 'rule', 'show'], ['ip', '-6', '-j', 'rule', 'show'],
    ['ip', 'route', 'get', '1.1.1.1'],
    ['resolvectl', 'dns'], ['resolvectl', 'domain'],
    ['nmcli', '-t', '-f', 'TYPE,STATE', 'connection', 'show', '--active'],
    ['docker', 'network', 'ls', '--quiet'], ['docker', 'context', 'show'],
]
```

## Build

```bash
docker build --pull=false \
  --label task=linux-docker-sharing-trial --label trial=ld01 \
  --label owner=opencode-linux-trial-preparation \
  --tag tvm-share-ld01:tooling _bmad-output/linux-docker-trial/tooling
```

Combined stdout/stderr was saved to `build.log`. The CLI labels explain the label steps in that log; they are not hidden Dockerfile instructions. `docker image inspect` captured both images; the child's `RootFS.Layers` prefix had to equal the foundation's full layer list. The result was stored in `image.json` with `foundation_id`. All later `docker run` calls used the **full immutable result ID**, not the tooling tag.

## Prefix selection and collision handling

Immediately before creation, the same filtered container/network/volume name listings had to remain empty. Current `ip -j route show table all` and full `docker network inspect` IPAM were read again. Selection logic, using Python `ipaddress`:

```python
used = [ipaddress.ip_network(r['dst'], strict=False) for r in routes
        if r.get('dst') not in (None, 'default', '0.0.0.0/0')]
for n in networks:
    for config in n.get('IPAM', {}).get('Config') or []:
        if config.get('Subnet'):
            net = ipaddress.ip_network(config['Subnet'], strict=False)
            if net.version == 4:
                used.append(net)
selected = []
for candidate in ipaddress.ip_network('172.16.0.0/12').subnets(new_prefix=28):
    if not any(candidate.overlaps(other) for other in used):
        selected.append(candidate)
        used.append(candidate)
    if len(selected) == 2:
        break
```

Required two available prefixes before any creation. The selected prefixes were `172.16.0.32/28` and `172.16.0.48/28`; they are historical observations, not guaranteed free choices for a later run.

## Fresh resources

For suffix `a` then `b`, the following expanded commands ran with the corresponding prefix. `resources.json` was written in a `finally` block after appending each successful resource's kind/name/ID, so partial creation would not silently lose ownership tracking. Volumes record their names; Docker network/container IDs are full-length.

```bash
docker network create --label task=linux-docker-sharing-trial --label trial=ld01 \
  --label owner=opencode-linux-trial-preparation --driver bridge \
  --subnet 172.16.0.32/28 tvm-share-ld01-net-a
docker volume create --label task=linux-docker-sharing-trial --label trial=ld01 \
  --label owner=opencode-linux-trial-preparation tvm-share-ld01-home-a
docker run --detach --name tvm-share-ld01-a \
  --label task=linux-docker-sharing-trial --label trial=ld01 \
  --label owner=opencode-linux-trial-preparation --network tvm-share-ld01-net-a \
  --mount type=volume,src=tvm-share-ld01-home-a,dst=/home/session \
  --mount type=bind,src=/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/project,dst=/project \
  --cap-drop=ALL --security-opt=no-new-privileges \
  --memory=512m --memory-swap=512m --cpus=1 --pids-limit=128 --restart=no \
  --cap-add=NET_ADMIN --device=/dev/net/tun:/dev/net/tun:rw \
  sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050
```

B used the same commands with names ending `-b`, subnet `172.16.0.48/28`, and **without** either `--cap-add` or `--device`. Both inherited image default UID/GID 1001:1001, home/workdir and `sleep infinity` command. No other environment variables/mounts were forwarded. The build-created intermediate containers were removed normally by Docker.

## Host comparison after creation and baseline

The snapshot reran the same `commands` array. Trial bridges came only from the two new network IDs (`br-` plus first 12 ID characters unless the network specified a bridge name). It read `ip -j link show`, selected those bridges and veth links whose `master` matched a trial bridge name/index, and saved that exact exclusion set in `host-after.json`.

Comparison logic used on the first seven snapshot outputs (all commands returned 0):

```python
for old, after in zip(before['commands'][:7], out['commands'][:7]):
    cmd = old['command']
    a, b = old['stdout'], after['stdout']
    if 'route' in cmd and 'get' not in cmd:
        a = json.loads(a)
        b = [r for r in json.loads(b) if r.get('dev') not in trial_links]
        same = sorted(json.dumps(x, sort_keys=True) for x in a) == sorted(
            json.dumps(x, sort_keys=True) for x in b)
    elif cmd[0] == 'resolvectl':
        lines = []
        for line in b.splitlines():
            match = re.match(r'Link \d+ \(([^)]+)\):\s*(.*)$', line)
            if match and match[1] in trial_links:
                assert not match[2], 'unexpected DNS/domain on trial link'
            else:
                lines.append(line)
        same = a.splitlines() == lines
    else:
        same = a == b
    comparisons.append(dict(command=cmd, equal_after_excluding_only_trial_interfaces=same))
```

The one-off comparison was executed with normal Python (no optimization). Every comparison had to be true. Full metadata of each **pre-existing** Docker network ID was inspected again and compared to its before snapshot for exact dictionary equality. The host then ran `socket.getaddrinfo('example.com', 443, type=socket.SOCK_STREAM)` and one `socket.create_connection(('1.1.1.1', 443), timeout=10)`, closing it after recording its peer. These observations were saved to `host-after.json`; no held-flow or firewall-equivalence claim follows.

## Baseline source and inventory

The runnable baseline is [spot-check.py](spot-check.py), with the command in [execution-results.md](execution-results.md). Inventory used `docker exec tvm-share-ld01-a` for `dpkg-query -W '-f=${binary:Package}\t${Version}\n'`, `openvpn --version`, `openssl version`, `git --version`, `python3 --version`, `curl --version`, `ip -Version`, `iptables --version`, `tcpdump --version`, and `getent passwd nm-openvpn`. Their command/exit/stdout/stderr entries are in `tooling-versions.json`.
