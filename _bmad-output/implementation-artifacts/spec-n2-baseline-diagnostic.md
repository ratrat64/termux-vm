---
title: 'Baseline-only N2 diagnostic after temporary-data loss'
type: 'feature'
created: '2026-10-20'
status: 'done'
baseline_commit: 'dc1a192619471c74692833e65122d4fa4ebeeec1'
---

## User-owned intent

Prepare and verify a baseline-only diagnostic offline; do not start a live run.
Recover missing source if possible following the reported host reboot. Retain
resource identities and evidence boundaries; never invent lost raw reports or
use company VPN material. A future run requires separate authorization.

## Implementation

- Recovered the prior source/test/doc edits into durable branch/worktree
  `fix/n2-baseline-diagnostic` at `/home/rat/Git/termux-vm-n2-baseline-diagnostic`.
- `controlled-vpn/trial.py`: distinct baseline-only authority, one connection/off
  dispatch, no cycle/injection, durable private evidence, immediate probe response
  archival, private stage/error output, local missing-metadata rejection and
  explicit reconciled residual inventories without clearing them.
- `controlled-vpn/fixtures.py`: application/DNS/HTTP/direct/off stage records,
  structured failure type/stage/message and partial observations. Workers remain
  usable; the controller fails the campaign on the first probe error.
- `controlled-vpn/setup-server.sh`: baseline-only authorization accepted without
  requiring an injection grant; same fixed-window and scoped rollback safeguards.
- `controlled-vpn/test_baseline.py`: offline proofs of admission, dispatch,
  injection rejection, error retention, reconciliation and failure handling.

Paths above are under `_bmad-output/linux-docker-trial/`.

## Acceptance

- Given baseline-only authority, when executed in a sandbox, then exactly one
  connect/off occurs, no cycle/reconnect/injection occurs, and cleanup is retained.
- Given a failed probe, when the worker replies, then stage/error/partial evidence
  is privately saved before the controller fails; no automatic retry follows.
- Given missing metadata or changed residuals, when preflight runs, then no live
  action occurs and no historical proof is fabricated.
- Given no new execution approval, when preparation completes, then no Docker,
  GCP, VPN or capture operation has run.

## Limits

Historical raw evidence and metadata remain unavailable. No current resource,
zombie or VM state has been inspected after reboot. Offline readiness is distinct
from live admission: separately approved post-reboot reconciliation and a fresh
maximum-30-minute window remain required. The old failed-baseline cause is unknown.

See [diagnostic notes](../linux-docker-trial/baseline-diagnostic.md).

## Offline completion

All 87 tests passed in 15.202 seconds, with no skips. Server Bash syntax and
whitespace checks pass. CLI help exposes baseline-only mode without executing it.
The ten baseline tests plus one metadata-permission/format test verify the new
path; the 76 recovered tests remain green. One intermediate dispatch test lacked
mocked bridge metadata; its fixture was corrected without relaxing the verdict.
`done` covers source recovery and offline preparation only, not live admission,
diagnosis of the old probe error, or N2 fault acceptance. No new private execution
record, live window or runtime inspection was created.
