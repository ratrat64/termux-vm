---
title: 'LD01 credential-free tooling and fresh Docker baseline'
type: 'chore'
created: '2026-10-19'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Build one credential-free tooling image and run the smallest fresh-context baseline from the existing LD01 plan. The user explicitly authorized Ubuntu package downloads, fresh A/B containers/home volumes/scratch storage, Docker-managed networks, A-only TUN/NET_ADMIN, and public probes to example.com and 1.1.1.1:443. The user also approved extending the existing uncommitted handoff in this dedicated worktree.

Reuse the existing foundation image/source, verify its recorded immutable ID, freeze the derived image ID, and leave source plus one runnable spot-check under `_bmad-output/linux-docker-trial`. Check distinct network namespaces/private homes, two non-root joined A shells, selected scratch visibility, ordinary application DNS and public IPv4 connectivity, effective capabilities/mounts and A's TUN usability. Preserve timestamped raw/private evidence outside Git. Retain only new task-labeled resources and update the handoff with exact observed results and unrun gates.

This authorization excludes existing trial resources and staged credentials, company endpoint resolution or VPN connections, account logins, failure injection and host VPN/daemon configuration changes. This stage does not establish same-socket continuity through VPN toggles, DNS containment, shared accounts, copied state, restricted VPN controls or WSL2 acceptance.

</frozen-after-approval>

## Implementation Notes

- Used the oneshot path: no unresolved intent gaps for the explicitly authorized credential-free baseline, no irreversible user-data/configuration mutation, and a small tooling/check-source footprint. Reversible fresh Docker resources and public probes were explicitly approved.
- Added `linux-docker-trial/tooling/Dockerfile`, narrow `.dockerignore` and one Python-standard-library `spot-check.py`; reused read-only foundation source/image and no product launcher.
- Built/froze image `sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050`; retained only fresh LD01 resources and private evidence outside Git. Full authorized baseline passed; host pre-existing routes/rules/DNS and Docker network metadata matched under the stated comparison.
- First checker run exposed Docker capability-prefix normalization and unsupported `Path.open(opener=...)`; corrected both, preserved the failed attempt and ran an expected wrong-image negative check proving failure evidence is now written with mode 0600.
- Updated ownership, runbook, readiness and new execution-results record. Credential access/VPN/account/failure/WSL2 stages remain unrun. Current A-only NET_ADMIN does not establish ability to drop daemon identity; recorded as a later configuration/permission gate, without adding privileges.
- Required read-only Blind Hunter review returned seven findings. Patched all seven without changing frozen intent: explicit non-assert guards and descriptive errors, exact resource ownership/ID/topology/device validation, retained runtime limits/configuration, and an executed-command/provenance record. Added no product control API and no external dependency. Final positive baseline and optimized wrong-image negative proof passed; evidence paths are in execution-results.md.
- Commit/push/PR not performed: repository policy and developer instructions require an explicit user request; none was made. No work stashed/reset or other owner's files changed.

## Review Triage Log

- **high → patch:** Python optimization removed assert-based ownership/acceptance guards and embedded subprocess checks; source confirmed this path could reach marker/TUN operations. Replaced assertions with explicit checks; optimized wrong-image run now raises a descriptive ValueError before mutations.
- **medium → patch:** distinct network namespaces alone accepted a same-bridge topology. Source confirmed missing expected-network enforcement. Now requires exact A/B network names, recorded IDs, attachments and ownership labels; final positive report retains network IDs.
- **high → patch:** any distinct named home volumes were accepted before marker writes, without volume ownership checks. Source confirmed potential other-task volume mutation. Now validates exact expected names and labels before all writes; final positive report retains volume ownership metadata.
- **medium → patch:** only container device pathname was checked. Source confirmed host source/access mismatch could pass. Now checks the complete exact A mapping `/dev/net/tun` → `/dev/net/tun`, `rw`, and no devices in B; final positive run passed.
- **medium → patch:** bare assertion errors produced empty private error messages, confirmed in the first deliberate negative report. Now stores exception type and descriptive failed-check message; optimized negative proof recorded `tvm-share-ld01-a: immutable image mismatch`.
- **medium → patch:** limits/restart/capability/security claims were not independently retained in the reduced snapshot. Added explicit limit/restart checks and bounded `runtime_config`/mount/ownership evidence; final positive report contains those exact inspected values.
- **medium → patch:** build CLI labels, provisioning inputs and host-comparison code were missing from the durable source handoff. Preserved expanded commands, selection/initialization and comparison rules in `linux-docker-trial/executed-commands.md`; linked from execution-results.md. No findings deferred.
