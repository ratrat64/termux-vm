# Repaired DNS fixture — next baseline-only attempt

**Offline preparation complete; live admission blocked pending three separate
gates below.** Owner OpenCode; worktree
`/home/rat/Git/termux-vm-n2-baseline-diagnostic`, branch
`fix/n2-baseline-diagnostic`. Inspected source HEAD:
`2293a9943a570ff627e07856581d3fea2f2df85f`.

## Evidence and offline readiness

- The saved `baseline-live-20261020T140706Z-attempt1/` under
  `/home/rat/.local/state/termux-vm-private/` still records **baseline FAIL,
  cleanup PASS**. Both shells failed `validate-dns-baseline`: lab A passed;
  UDP/TCP AAAA NOERROR/NODATA lacked AA; embedded DNS did not reply. Cleanup
  finished `2026-10-20T14:08:07.927968Z`; controller finished `14:08:18.294694Z`.
- Saved final process evidence lists state-Z python3 PID 198 and openvpn PID 219,
  both parent PID 1. It does **not** supply a fresh `/proc` start identity for
  admission. Zero zombies in the accepted `baseline-20261020T134845Z/` inputs is
  historical, not the next reference. Do not restart A to remove these entries.
- Saved package delta is empty; capture is 92 captured/92 received/zero dropped;
  final VM output has no task listeners/loaded units. These are saved controller
  observations, not an independent current-state audit.
- Fresh offline suite: **98 tests PASS in 27.544 seconds, no skips**; Bash syntax,
  CLI help and saved-evidence consistency checks PASS. Nine accepted-input hashes
  and three provenance hashes match. Saved `reconcile()` and capture proof pass;
  neither establishes runtime freshness. No Docker/GCP/VPN operation occurred.

## Gate 1 — authorize read-only reconciliation only

Request explicit permission for metadata-only Docker/host inspection and
IAP/SSH inspection of controlled VM `free-vm`, using the existing identity and
strict known-host trust. Confirm exclusive LD01 access/no overlapping worker or
controller during inspection. Write the receipt and results to a **new** 0700
directory under `/home/rat/.local/state/termux-vm-private/`, files 0600. This
permission does not accept a changed reference or authorize deployment, probes,
capture, connection, off, starts, cleanup or other resource mutation.

Inspect in bounded steps; save each result before evaluating it. Stop at the
first unexpected command failure or unexplained drift and report it. Expected
B firewall unreadability from absent NET_ADMIN remains a documented limitation;
omit those reads rather than grant privileges or claim firewall equality.

1. **Retained identities/configuration:** compare original A/B IDs, frozen image,
   full Config/HostConfig/NetworkSettings/endpoints and destination-keyed mounts
   to accepted `baseline-20261020T134845Z/` metadata. Check network IDs/IPAM/peers,
   home-volume metadata, ownership labels, existing scratch path/type/permissions,
   running state, capability/device/limit settings and distinct namespaces.
   Record host/A/B routes/rules/resolver and A filter/NAT/IPv6 state against saved
   accepted state/restoration evidence. Never silently replace a differing value.
2. **Idle A/residuals:** reuse `trial.py:IDLE_A` and the metadata-only journal
   reader in `inspect-retained.py`. Record every zombie as
   `{pid, comm, state, identity}` from `/proc/<pid>/stat` (start ticks), with
   parent/boot/container-start context separately. Enumerate every retained
   `/run/ld01-cvpn*` path, active marker, restore/cleanup SHA256, cleanup status and
   intent. Require inactive, readable PASS/off journals, no active VPN/watcher,
   `ld01tun` or task containment chains. The last attempt reports its new A
   material removed; verify absence rather than creating a journal entry for it.
3. **Host/VM inactivity and retention:** check no competing controller/supervisor,
   capture or task SSH forwards/listeners, no `ld01srv` or task VM services/unit
   files, and no occupied planned host bindings (A bridge 20990/20992, B bridge
   and host loopback 20991) or VM loopback 11940/19090 listeners. Enumerate task
   directories/units read-only, including all four known tasks:
   `cvpn7a1a8819b397`, `cvpn152283967635`, `cvpnb76f5884442f`,
   **`cvpn309ee7be4837`**, and disclose additional matches. Stat retained VM
   PKI/audit/upload entries; hash source/rollback files only, without opening
   keys/profiles. Check retained package versions and required executables.

Reuse the existing readers, not a new diagnostic platform. The historical
`inspect-retained.py` VM task list omits the latest task and its command loop
continues after errors: **do not launch it wholesale** for this stop-first
inspection. Apply the bounded readers in supervised steps with the full scope
above. Their embedded `query()` functions also continue on nonzero exit: split
these into individual reads, evaluate each exit/status before the next read,
and omit B firewall queries in advance. Do not run `start-retained.py`, rollback
scripts or the live controller.

## Gate 2 — explicitly accept the inspected reference; prepare inputs only

Present the fresh inventory's exact differences and residual identities to the
user. Expected *candidate* difference is the two disclosed zombies, not an
assumption that they still exist or that everything else matches. Any other
difference needs its own disposition. Active/failed journals, live task resources,
missing scratch or stopped containers block this path; acceptance is not repair
permission. Historical B8/full lost-baseline equality remains unverified.

Only after explicit acceptance, write a new sibling private baseline directory
with provenance/acceptance receipt and hashes, leaving old inputs untouched.
Preserve the existing formats: `resources.json`, `image.json`, `baseline.json`,
`retained-metadata.json`, exact `residuals.json` zombie/journal lists and supporting
network/volume/inspection metadata. Reuse unchanged accepted metadata only where
fresh comparisons prove equality. Reuse `diagnostic_inputs()` and saved-data
`reconcile()` with runtime functions trapped; validate network peers/IPAM,
permissions and provenance. Encode the accepted residuals in later authorization.

Do not run `prepare-baseline-inputs.py` unchanged: it expects the historical
start-inventory schema and asserts an empty zombie list. A separately accepted
two-zombie reference already fits the controller's exact residual schema; no
controller predicate change is needed. Input preparation creates **no execution
approval, live timestamps or attempt directory**. Do not set
`post_reboot_reconciled: true` until reconciliation and acceptance are complete.

## Gate 3 — fresh authorization for one normal connect/check/off

After gates 1/2, ask separately for all of:

- Exact **fixed UTC start and hard stop**, at most 30 minutes apart. Cleanup must
  begin by hard stop minus ten minutes and finish within the window. The unchanged
  controller requires launch/deployment/capture with **more than 15 minutes**
  remaining; a late/missed admission stops, without moving the deadline or retry.
- Explicit exclusive reuse of retained LD01 A/B, networks, homes and scratch,
  with no overlapping session/controller; no ownership relabeling.
- One baseline-only attempt from the authenticated operator terminal: controlled
  IAP/SSH forwards, fresh task-private lab PKI/profile/source/services, A-only
  VPN/routing/resolver/containment lifecycle, two existing-style non-root joined
  shells, approved lab/embedded DNS/HTTP/canary and `example.com` off checks,
  host/B negative/continuity observations. No company material, injection or
  reconnect. Retain the existing no-package-change requirement.
- Capture on **only A's freshly identified veth**, inbound direction, 96-byte
  snaplen, numeric timestamped header output: chosen lab subnet, UDP/TCP DNS and
  A-bridge VPN/direct-canary ports 20990/20992. Preserve existing filter, positive
  canary and zero-drop/count checks; no broad interface or payload capture.
- **Supervised explicit off/abort/expiry/controller-loss cleanup**, including
  stopping only this attempt's client/watchers/capture/forwards/VM units, exact
  restoration, archiving A rollback evidence and removing only the new transient
  A material/unit files after verified restoration. Retain all earlier resources,
  journals, VM PKI/audit/uploads and private evidence. Failed teardown is reported
  and retained, with no automatic cleanup retry or container restart.

The separate 0600 private `authorization.json` in a new 0700 approval directory
must contain `mode: "baseline-only"`, `injection: false`, `cases: []`,
`observation: true`, `exclusive_reuse: true`, `supervised_off: true`,
`post_reboot_reconciled: true`, exact newly accepted `baseline_dir`,
`retained_metadata`, `residuals`, `start`, `deadline`, and targets exactly
`["tvm-share-ld01-a", "free-vm", "A-veth", "example.com"]`. Record approved source
revision/content hashes alongside it. These fields are a contract, **not an
approval file or an open window**.

Use a new, unused durable attempt path, e.g.
`/home/rat/.local/state/termux-vm-private/baseline-dns-live-<UTC>-attempt1`.
Its private parent must already be 0700; let the controller create the attempt
directory. Authenticate sudo in the operator terminal; validate noninteractive
capture/cleanup authority before deployment, without changing privilege policy.
Source, approval and accepted-input hashes must match the reviewed inputs.
Immediately before deployment, under the live authorization and exclusive reuse,
repeat gate 1's inactivity/retention comparisons, including journal intent/off,
watcher identities, all task VM units/unit files and old source/rollback hashes.
Controller preflight alone does not cover all these checks. Any intervening drift
blocks deployment and returns to reconciliation/acceptance; do not update inputs
inside the live attempt. These read-only admission checks consume the same window.

Only after authorization, from the designated worktree, the command shape is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py \
  --baseline-only --authorization "$NEW_APPROVAL/authorization.json" \
  --private-dir "$NEW_UNUSED_ATTEMPT"
```

No actual path variables or live timestamps have been assigned. Do not use the
old approval or old command. Keep the inherited exclusive flock, independent
supervisor, lease, reserves, cancellation/publication locks and rollback intact.
Stop testing at the first unexpected failure; run only the authorized supervised
abort/off path, then report. No automatic second attempt.

For an operator abort, use the attempt's durable `state.json` controller PID and
start identity, compare them to the live non-zombie `/proc/<pid>/stat` identity
and expected controller command, then send **one SIGTERM to that controller
only**. Its handler enters supervised abort; do not signal a reused PID, process
group, client, forward or watcher directly. If the controller is already gone,
observe the registered independent supervisor; do not launch a second controller
or cleanup worker. Cancellation/off markers prove a request, not restoration.
Wait for `cleaned.json`, `evidence.json` and any `supervisor-result.json`, within
the fixed window. A failed cleanup-attempt/supervisor record or absent completion
is reported as failed/unverified cleanup, retaining material for a human decision.

## Verdict and next product slice

Report separately: admission; both-shell baseline DNS/HTTP and embedded rejection;
normal off/restoration; host/B continuity/negative checks; capture accounting;
overall baseline and cleanup verdicts; exact new residuals/evidence paths. Require
the controller's evidence and explicit cleanup proof, not just VPN initialization
or a green DNS query. Record failures/NOT RUN stages honestly and append results
without replacing the original **baseline FAIL / cleanup PASS**.

The live authorization must also cover bounded read-only final verification
within the same hard stop. Check `cleaned.json` PASS/empty errors, A cleanup/archive
restoration proof, final `evidence.json` cleanup/teardown fields and any supervisor
result; then verify no live task client/watcher/tunnel/capture/forward/listener or
VM unit/unit file remains, exact restored A/host/B state, preserved old journal
and VM source/rollback hashes and retained PKI/audit/upload metadata, and exact new
zombie/journal residuals. Compare cleanup/final observation times to the fixed
deadline. The controller records some final process/listener/unit output without
asserting absence, and `cleaned.json` precedes final observations: neither alone
proves these postconditions. Where saved evidence is insufficient, use the
authorized final read-only audit; report FAIL or unverified conditions separately
from controller verdicts. No audit permission implies repair or cleanup retry.

After a new baseline and cleanup PASS, the smallest Linux-alpha step is one
user-facing CLI entry to **list/status and join an existing named Linux context**,
reusing the proven non-root shell entry and shared context, with a short manual
try-it command. Scope its next small implementation separately; do not turn this
blocker into another research campaign, broad test platform or N2 reconnect run.
