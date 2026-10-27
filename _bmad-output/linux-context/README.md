# Existing LD01 contexts (Linux alpha)

Run from the repository root with Python 3.7+ and an already accessible Docker CLI
and daemon. The CLI uses the operator-selected Docker endpoint and normal access;
it does not install anything or activate permissions. Names must start with
`tvm-share-ld01-` and carry all three labels:

- `task=linux-docker-sharing-trial`
- `trial=ld01`
- `owner=opencode-linux-trial-preparation`

```sh
python3 _bmad-output/linux-context/cli.py list
python3 _bmad-output/linux-context/cli.py status tvm-share-ld01-a
python3 _bmad-output/linux-context/cli.py join tvm-share-ld01-a
```

`list` includes stopped contexts, sorted by name. `status` prints only name, state
and `IDENTITY_SUPPORTED`: user `1001:1001`, exactly one `HOME=/home/session`,
workdir `/project`, and non-privileged mode. Identity support is independent of
state; neither command reports VPN readiness, restoration or audit success.

`join` requires that identity, a running context that is not paused/restarting/dead,
and interactive stdin/stdout terminals. It re-inspects the exact name and replaces
itself with `docker exec -it --user 1001:1001 --workdir /project ID bash --noprofile --norc`,
using the inspected full ID. The fresh shell inherits the container's validated
HOME; no host environment, profile or credentials are forwarded into it. Exiting
it leaves the context and other joined shells running. A/B remain distinct
contexts; existing deliberately shared mounts remain shared.

Metadata success exits 0; unknown/ineligible names, unsupported joins, missing TTY
or pre-exec Docker failures exit 1 with a short operation-specific error. Invalid
usage exits 2. After process replacement, Docker owns diagnostics and exit status,
including the shell's exit status. There is no retry or lifecycle operation.
This is an LD01 entry point, not a security boundary or general container manager.

## Offline verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-context -p 'test_*.py'
```

Tests use synthetic metadata and mock subprocess, process replacement and TTYs.
They never contact Docker or open a terminal session.

## Proposed manual try-it — NOT RUN; separate authorization required

Only after explicit scoped live approval and fresh appropriate resource/residual
reconciliation, confirm that A and B already exist, run, and have supported daily
identities. Preserve the two post-Gate-5 zombies and prior journals' recorded
disposition. A missing or stopped context is a failed prerequisite, not an
instruction to create, start, repair or clean anything.

1. In terminal 1 run `python3 _bmad-output/linux-context/cli.py join tvm-share-ld01-a`.
2. In terminal 2 run the same command for A. In terminal 3 run
   `python3 _bmad-output/linux-context/cli.py join tvm-share-ld01-b`.
3. In each joined shell run these read-only checks:

   ```sh
   id -u
   id -g
   printf '%s\n' "$HOME"
   pwd
   printf 'shell PID: %s\n' "$$"
   stat -Lc '%d:%i %n' /home/session /project
   readlink /proc/self/ns/net
   ```

   Expect UID/GID 1001, HOME `/home/session`, and workdir `/project`. A's shells
   have different PIDs but matching home/project inode identities and network
   namespace. B has its own home and network namespace; the existing trial's
   deliberately shared project can match A's. These observations are not VPN or
   restoration checks.
4. `exit` terminal 1's shell; repeat the read-only checks in terminal 2 to confirm
   it remains usable. Exit the remaining shells. An optional separately approved
   `status` confirms container state afterward. Do not perform lifecycle, VPN,
   network-probe, marker-write or cleanup operations.

No live query, join, or manual smoke check is authorized by implementation or by
running the offline tests.
