# Baseline-only diagnostic — first live result

**Current result: baseline FAIL; supervised cleanup PASS.** The user authorized
the exact baseline-only scope and launched one attempt from their authenticated
terminal at `2026-10-20T14:07:06Z`, with cleanup by `14:27:06Z` and hard stop
`14:37:06Z`. Task `cvpn309ee7be4837` finished at `14:08:18.294694Z`; the single
attempt is complete, with no retry authorized.

Both joined shells failed at `validate-dns-baseline` with `positive DNS/embedded
rejection mismatch`. Partial private probe responses were retained: lab UDP/TCP
A answers succeeded, while lab UDP/TCP AAAA returned NOERROR with no answers.
The failed stage is established; root cause and equivalence to the historical
failure are not yet established. Remaining positive-baseline/off acceptance is
not claimed; the controller aborted into supervised restoration.

Cleanup passed at `14:08:07.927968Z`, with A restoration PASS and no cleanup
errors. Final controller checks passed A/host/B route/rule/resolver and retained
container configuration/endpoint equality. Capture stopped with 92 captured and
received packets, zero kernel drops. Final VM evidence lists no task units or
task listeners. **Residuals:** A has defunct python3 PID 198 and openvpn PID 219,
both parent PID 1; no restart/recreation was performed. The previously accepted
zero-zombie reference is historical and needs explicit reconciliation before any
future admission. No injection, reconnect or company VPN material was used.

Private evidence: `/home/rat/.local/state/termux-vm-private/baseline-live-20261020T140706Z-attempt1/`.
Approval is in the sibling `baseline-live-20261020T140706Z-approval/` directory.
Follow-up read these private files only; no independent live resource audit or
cleanup retry was performed. Implementation remains unchanged and uncommitted;
the prior offline result is 87 tests PASS. See [latest handoff](../task-owner.md).

## Historical preparation and adoption handoff

Original A/B were subsequently started and new
empty scratch created under separate authorization. See [running reconciliation](originals-started.md).
Baseline adoption and a live diagnostic window are still pending.

**Follow-on inventory:** separately authorized read-only post-reboot inspection
has now completed. A/B are retained but stopped and the shared scratch path is
missing; no new baseline was adopted. See [inspection findings](post-reboot-inspection.md)
for the current observations and required user decisions. The offline-preparation
record below is historical; no live diagnostic has run.

**Authority:** user requested preparation and offline verification only. No new
live window, inspection of Docker/GCP, deployment, connection, capture or fault
injection has been performed during this task. All previous execution windows
have expired. Company VPN material remains forbidden.

## Durable location and recovery

- Owner: OpenCode, `fix/n2-baseline-diagnostic`.
- Worktree: `/home/rat/Git/termux-vm-n2-baseline-diagnostic`.
- Base: `dc1a192619471c74692833e65122d4fa4ebeeec1` (merged PR #4).
- Replayed 105 successful source patches from persistent OpenCode tool records,
  restricted to the eight N2 implementation/test/document files under
  `_bmad-output`. No credential/account tables, authorization files, raw private
  reports or profiles were exported into Git.
- Before new edits, recovered `trial.py` had Git blob hash
  `3033de41d7693bfe0e688f9c0b9f1e7e70166446`, matching the independent retained
  full-diff record. All 76 recovered tests passed in 14.983 seconds.
- The raw `/tmp/opencode` evidence, approval records and private baseline metadata
  were not recovered. Restored N2 documents contain historical summaries, not new
  current-state proof or reconstructed raw evidence. The historical live attempt
  remains FAIL; F1/F2 were NOT RUN. The six formerly disclosed zombies may have
  changed during reboot; their current existence is not assumed.

## Prepared behavior

Use the existing controller with **`--baseline-only`** and matching explicit
baseline-only authorization. It starts one normal connection, checks private
application A/AAAA lookups, lab/embedded UDP/TCP DNS, literal/named HTTP and
direct-path canaries from both joined shells, then requests explicit off and
checks ordinary DNS/direct access and exact restoration. Host/B continuity,
scoped capture and the original supervised abort/expiry cleanup remain in use.

The baseline path never calls `cycle()`, reconnects, kills the client as an
injection, or terminates a VPN forward as an injection. Calling the fault cycle
with baseline authority is rejected before any action; the root client-injection
action rejects it too. Ordinary disconnect/abort may terminate the task client
and forwards as cleanup, not as a test fault.

Probe workers now return structured failure details and partial results rather
than exiting on an expected probe exception. Every stage writes started/completed/
failed progress and tracebacks to a private `shell-*.stderr` file. The controller
publishes each probe response to a 0600 `shell-probe-*.json` **before** applying
the failure verdict. Unhandled worker exits still produce bounded private EOF
diagnostics. Terminal errors identify the stage without printing private error
details. A failed positive baseline aborts; it is never treated as successful
containment, and no automatic rerun is made.

## Reboot-loss admission gate

Do not re-use old commands or fabricate their missing metadata. A future,
separately approved **read-only post-reboot inventory/reconciliation** is needed
before execution. Preserve any retained container/VM material; no restart,
recreation, relabeling, package update or deletion is authorized by preparation.

Admission requires a new private, explicitly accepted baseline set outside Git:

- `baseline_dir` with the existing metadata formats: `resources.json`, `image.json`
  and **`baseline.json`** (the checks schema, newly named to avoid implying recovery
  of the historical dated spot-check).
- `retained_metadata` with full A/B inspect configuration/endpoints/mounts.
- `residuals.zombies`: exact current state-Z process records including PID,
  command, state and start identity; an explicitly reconciled empty list is valid.
- `residuals.journals`: exact retained task paths and SHA256 digests of their
  `restore.json`/`cleanup.json`. Active/failed/unreadable journals and task firewall
  chains still reject admission even if listed. A current snapshot is a newly
  accepted reference, not proof of pre-reboot or missing historical B8 equality.

All metadata files must be 0600 in 0700 directories; their absence fails locally
before any external command. The preflight compares these accepted records with
the actual retained resources; it does not auto-adopt current state. New metadata
may only be established following an explicit reconciliation decision, never by
relabeling current snapshots as recovered historical evidence.

The future authorization must state `mode: "baseline-only"`, `injection: false`,
`cases: []`, `observation: true`, `exclusive_reuse: true`, `supervised_off: true`,
`post_reboot_reconciled: true`, the baseline paths and residuals above, and exact
targets `["tvm-share-ld01-a", "free-vm", "A-veth", "example.com"]`. Supply fresh
fixed UTC `start`/`deadline` no more than **30 minutes** apart; ten minutes remain
reserved for cleanup. No such approval record or timestamps have been created.

The diagnostic attempt must use a fresh directory under a durable private parent
(0700) outside Git, `/tmp` and `/run`; files are 0600. Recommended future storage:
`/home/rat/.local/state/termux-vm-private/`. The operator launches from their own
authenticated terminal. Do not change sudo policy to bypass the session cache.

## Offline verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s _bmad-output/linux-docker-trial/controlled-vpn -p 'test_*.py' -v
bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh
git diff --check
```

New checks cover authority separation, root injection denial, one connect/off,
real execute dispatch/cleanup, failed-baseline abort, missing-metadata admission,
explicit post-reboot residual reconciliation, server authorization, and an actual
disposable worker returning partial stage errors while remaining alive. These
use only temporary files, synthetic transports and loopback/disposable workers;
they do not inspect retained LD01 or GCP.

**Final result: all 87 tests PASS in 15.202 seconds, no skips.** Bash syntax and
whitespace checks pass. Eleven new diagnostic checks supplement the 76 recovered
tests. CLI help was checked without launching the controller. An intermediate
execute-dispatch test initially omitted bridge fields normally supplied by
preflight; its synthetic fixture was fixed, with PASS/cleanup assertions retained.

**No live verdict is established.** The original probe failure's exact cause is
still unknown. This change prepares diagnostics to expose it; passing offline
checks does not claim the original DNS/HTTP baseline is fixed.
