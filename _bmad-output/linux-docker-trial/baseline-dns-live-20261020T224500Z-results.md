# Baseline-only attempt — FAIL; capture accounting and final audit unresolved

- Source `243d1a9fa61e2ee47f8e3a9676efa7dce5bb9f9f`, task
  `cvpn3f70841386b2`; launched once from the authenticated operator terminal.
- User approved fixed window `2026-10-20T22:45:00Z`–`23:15:00Z`, cleanup begins
  by `23:05Z`; fresh in-window admission passed 85 checks. No injection/reconnect.
- Controller: `22:48:48.405735Z`–`22:50:22.720439Z`, **FAIL** with
  `ValueError: capture loss/count mismatch`. The sole attempt is consumed.
- Capture: **176 parsed headers / 176 captured / 180 received by filter /
  zero kernel drops**. The unchanged strict equality predicate fails. This does
  not establish why the counts differ or prove packet escape; no acceptance
  predicate was weakened and no live retry is authorized.
- The capture completion receipt is `reason=requested`, `signalled=true`,
  `forced=false`, `returncode=0`, with matching registered identities/command.
  The audited registered capture child and wrapper were inactive. This is narrow
  evidence for the new stop handshake, not overall capture or cleanup acceptance.
- Saved probe reports contain authoritative UDP/TCP A and AAAA replies, completed
  baseline probe results for both shells, and completed off probes. The controller
  proceeded through explicit off. Overall baseline remains FAIL; host/B continuity
  completion and all acceptance criteria are not claimed from partial stages.
- A restoration report: **PASS**, empty errors. Overall cleanup: **FAIL** with
  `capture stop: capture loss/count mismatch`; no `cleaned.json`. The supervisor
  recorded FAIL and retained the failed teardown without an automatic retry.
- Saved controller final output lists two new A zombie PIDs 1071/python3 and
  1093/openvpn alongside prior PIDs 198/219. New A task material remains recorded
  as retained; new VM PKI/audit/upload material remains retained. No new residual
  reference was adopted. Their complete independent current-state audit is pending.

## Final audit — incomplete, host drift observed

Read-only audit stopped at approximately `2026-10-20T22:53Z` on host snapshot drift, after
42 checks passed. It confirmed source and accepted-input hashes, inactivity of
the registered controller/capture/forwards, original LD01 container metadata,
networks/volumes/scratch and restored A/B routes/rules/resolvers. Remaining A
firewall/journal/residual and VM retention/inactivity checks did not run.

The saved host snapshot adds bridge `br-a35e42ecd1f6` (`172.19.0.0/16`) and
veths `vethc0cf5b9`/`veth6a8fc73`, plus their link-local routes and interface
listings. These were absent from admission. Ownership/cause is unverified; the
bridge is not automatically attributed to the trial, removed or adopted.
The user was asked about continuing read-only checks and instead asked how to
proceed. The next host clock observation was `2026-10-21T08:12:12Z`, after the
hard stop. No further Docker/GCP inspection ran under the expired approval.

Private evidence parent `/home/rat/.local/state/termux-vm-private/`:

- `baseline-dns-live-20261020T224500Z-attempt1/`: immutable attempt evidence.
- `baseline-dns-live-20261020T224500Z-approval/`: scope, source/input pins and claim.
- `final-audit-20261020T224500Z-225331Z/`: partial audit and failed comparison.

## Next bounded action

The subsequent audit below completed the checks available without starting the
stopped containers. Current in-container restoration/residual verification remains
unavailable, and the scratch bind source is missing. Keep the stopped resources
unchanged until the user decides the scratch disposition and explicitly approves
any original-container start or other resource action. No current reference was
adopted. The old accepted inputs cannot establish fresh live admission unchanged.

Capture accounting can be investigated offline from saved evidence without
starting A/B. Do not infer a root cause or weaken equality/drop requirements from
this run alone. Any implementation fix, cleanup retry, changed-reference acceptance
or new live attempt needs its own explicit scope. Original historical baseline
FAIL / cleanup PASS and this new baseline FAIL / cleanup FAIL remain distinct.

## Fresh read-only audit — blocked by current Docker access

The user authorized a new ten-minute audit with exclusive LD01 access. Recorded
bounds: `2026-10-21T08:14:43Z`–`08:24:43Z`. The agent reader stopped at `08:18:53Z`
on Docker socket permission denial, after 24 source/input/registered-process
checks passed. The user separately selected a normal-terminal continuation;
that reader stopped at `08:23:17Z` with the same permission denial and 24 passed
checks. Neither reader reached container/VM metadata inspection or changed
resources. Prior audit failures remain preserved.

Read-only local access diagnosis confirms:

- Current process: `uid=1001(rat)`, supplementary groups do not include Docker.
- Docker socket: `root:docker`, mode `0660`, group ID 115.
- Docker group database: `docker:x:115:botond`.

This explains current `rat` access denial; it does not establish when or why
access differed from the earlier successful inspections. A terminal switch alone
cannot resolve account-level socket access. The metadata is not proof of current
LD01/VM restoration or inactivity; those checks remain incomplete.

Evidence directories under the same private parent:

- `read-only-audit-20261021T081443Z/`: agent failure and fixed-window receipt.
- `read-only-audit-20261021T081443Z-operator/`: human-directed continuation failure
  and saved access diagnosis.

Before another audit, obtain explicit approval for a narrow existing-authority
Docker reader (for example, only fixed read-only Docker queries through existing
sudo, keeping the audit process non-root), or operator-supplied observations from
the already Docker-authorized account. Do not change group membership, socket
permissions or sudo policy implicitly. Then use a new fixed read-only window;
the old evidence remains unchanged. No cleanup retry or new live attempt.

## Subsequent read-only audit — available checks completed, stopped-state blockers

User reported adding `rat` to the Docker group and instructed continuation.
The group database then listed `botond,rat`; the existing session still had its
old supplementary groups. `sg docker` activated the user-added membership in a
normal uid-1001 child, primary group 115. The agent changed no group/socket/sudo
policy. Fixed audit bounds: `2026-10-21T08:34:09Z`–`08:44:09Z`.

The first Docker inspection succeeded but found both original containers stopped,
so the running-state reader halted after 24 checks. User separately approved
continuing only available stopped-container/host metadata and VM checks in the
same window, with no start/restart or reference adoption. The continuation
completed at **`08:39:31.588300Z`**, before the hard stop: **61 available checks
PASS, 21 successful commands**. This is not an overall baseline/cleanup PASS.

### Confirmed

- Original A/B IDs, image references, full Config/HostConfig and destination-keyed
  mounts match the retained metadata. LD01 network IDs/configuration/IPAM/labels
  and both home-volume metadata remain preserved. Runtime endpoint/sandbox fields
  differ while stopped; they were recorded, not adopted.
- No active task host controller, capture, task SSH forward or planned listener.
  The registered processes had also been checked inactive before the first Docker
  inspection. No host task process was signalled.
- VM `free-vm` boot/hostname, links, listener endpoint set and package versions
  match retained evidence. No task process, tunnel, loaded unit, unitfile or unit
  definition on disk remains active/present in the scoped checks.
- All four historical VM task PKI/audit/upload entry metadata and source/rollback
  hashes are unchanged. The fifth task's two directories remain private/retained;
  fixture/uploaded-setup hashes match executed source. No keys/profiles were read.

### Unresolved state and availability limits

- Original A and B both show `Status=exited`, `ExitCode=255`, `OOMKilled=false`,
  `RestartCount=0`. Their finish timestamps are respectively
  `2026-10-21T07:02:25.899889014Z` and `07:02:25.899989782Z`. These observations
  establish stopped state, not its cause or attribution to the earlier trial.
- The scratch bind source
  `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/project` **does not exist**.
  No directory was recreated and no contents were presumed recovered or disposable.
- Current in-container routes/rules/resolver/firewall, A journals and exact zombie
  start identities are **UNAVAILABLE while stopped**. Earlier restoration PASS and
  the controller's four-zombie report remain saved historical observations; they
  do not establish current in-container state or a new accepted residual reference.
- The previously added bridge/network prefix `a35e42ecd1f6` is **absent** from the
  current Docker network index. Its historical ownership/cause is still unverified.
  Current host route/interface/DNS/domain/connection listings differ from the old
  home snapshot and remain unadopted. The failed historical comparison is preserved.

Private evidence under `/home/rat/.local/state/termux-vm-private/`:

- `read-only-audit-20261021T083409Z/`: access context, successful original-container
  inspection, and stopped-state gate failure.
- `read-only-audit-20261021T083409Z-continued/`: separately approved continuation,
  all 61 checks, current host/VM metadata, network index and final result.

No runtime resources were changed, no container was started/recreated, no missing
scratch replaced, no baseline adopted, and no cleanup retry or new live attempt
occurred. This redacted result update remains uncommitted and unpushed.
