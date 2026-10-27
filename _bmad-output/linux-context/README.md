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

## Authorized real-process smoke harness

`smoke.py` uses only Python's standard library on Linux. It invokes the actual
`cli.py` process for list/status, piped join refusal, two concurrent A PTYs and one
B PTY. It checks daily identity, PID independence, home/project/network identities,
one A shell surviving the other's exit, and actual exit-code 37 propagation.
It does not provision or repair targets, run probes, write project markers, or
perform VPN operations. Results do not establish VPN, account isolation,
restoration, WSL2 or arbitrary-container acceptance.

The operator must have explicit live authorization, an already-recorded fixed
20-minute UTC window, reconciled saved identities/configuration and current
process/residual evidence, and a private evidence directory owned by the operator
with mode 0700. Admission input and journal evidence files must be owned regular
files with mode 0600; symlinks are refused. The harness creates raw observations
there exclusively with mode 0600. Keep all these files outside Git. It never
creates a replacement window or adopts current state as a saved baseline.

Example for the **already-recorded original window**, not a fresh authorization:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-context/smoke.py \
  --window-start 2026-10-27T12:51:27.080191+00:00 \
  --window-end 2026-10-27T13:11:27.080191+00:00 \
  --evidence-dir /tmp/opencode/ld01-cli-smoke-20261027T125127080191Z \
  --admission /PRIVATE/explicit-admission.json
```

No check starts with five minutes or less remaining. Metadata/client commands
have 15/40-second timeouts, PTY observations 20 seconds and shell exits 15 seconds,
also capped by the remaining window with closure time reserved. Closure sends at
most one exit request per shell, closes only this run's PTYs, and may terminate
only its own client PID. A failed/unresponsive remote shell's disappearance cannot
be guaranteed by client termination: closure is reported unconfirmed and FAIL;
there is no container kill, broad process-group signal or cleanup retry.

The explicit JSON admission document has this structure (placeholders below are
not usable evidence):

```json
{
  "host_project": "/saved/shared/project/path",
  "project_identity": "DEVICE:INODE",
  "journals": {"/private/retained/journal": "SAVED_SHA256"},
  "absent_markers": ["/private/retained/active-marker"],
  "remote_journals": {
    "/run/ld01-cvpn-EXACT_RETAINED_DIRECTORY": {
      "restore.json": "SAVED_SHA256",
      "cleanup.json": "SAVED_SHA256"
    }
  },
  "containers": {
    "tvm-share-ld01-a": {
      "metadata": {
        "identity": {"name": "/tvm-share-ld01-a", "id": "FULL_SAVED_ID"},
        "image": "SAVED_IMAGE_ID",
        "network_mode": "SAVED_NETWORK_MODE",
        "mounts": []
      },
      "processes": ["EXACT docker top HEADER", "RECONCILED PROCESS ROW"],
      "identities": ["HOME_DEVICE:INODE", "PROJECT_DEVICE:INODE", "net:[SAVED_INODE]"]
    },
    "tvm-share-ld01-b": {}
  }
}
```

Both container entries must be complete. `metadata.identity` contains every field
from `cli.INSPECT_FORMAT`, including the three ownership labels, runtime flags,
user/workdir/privileged state and unique/exact HOME boolean. `metadata` is exactly
the projection described by `smoke.ADMISSION_FORMAT`: saved image ID, network mode,
mount objects and identity. Mount array order alone is normalized. No full inspect,
environment array, arbitrary labels or command-line arguments are collected.
`processes` contains the exact header and rows from the operator's freshly
reconciled `docker top ID -eo pid,ppid,stat,comm` snapshot; any change blocks joins.
`journals` retains the private archive file hashes; `absent_markers` checks local
archived marker paths only. Neither establishes the live container journal state.
`remote_journals` is additionally required: map every exact retained A directory
under `/run/ld01-cvpn*` to its recorded filename/SHA-256 mapping, including
`restore.json` and `cleanup.json`. Supply saved historical evidence, not a file
automatically populated from the same run's observations.

After both containers' metadata and process admission, the harness invokes only
read-only isolated Python as root in the admitted full A ID. It checks the exact
retained directory inventory, absence of each directory's live `active` marker
(including dangling symlinks), and hashes of every recorded journal file. Missing,
changed or symlinked journals/directories block admission. Arguments are passed
as an array with JSON data, without shell interpolation. Only hashes are returned;
no journal contents are emitted. Local archive checks cannot replace this check.

Admission checks metadata, residuals and live journals before daily-identity execs or CLI joins, then
compares home/project/network identities with the explicit saved values. The
authorized historical restart means the former zombie PIDs need not survive;
current residuals still require reconciliation. No VPN baseline adoption is needed.
Missing evidence, drift, access denial, unsupported/stopped targets or insufficient
window produce redacted BLOCKED results. Failed acceptance predicates produce FAIL.
Stdout is one deterministic-key JSON report with ordered checks; exits are 0 PASS,
1 FAIL, 2 BLOCKED (invalid arguments also exit 2). Raw output is private only.

Offline tests include harness admission, cutoff, privacy, timeout and session
parsing/closure boundaries. These synthetic checks do not establish live acceptance.
