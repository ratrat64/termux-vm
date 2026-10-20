---
title: 'Controlled OpenVPN lab on GCP'
type: 'feature'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '7e37565174b54105293c75c214c0b8b97202ff21'
context:
  - '/tmp/opencode/termux-vm-controlled-vpn-trial/AGENTS.md'
  - '/tmp/opencode/termux-vm-controlled-vpn-trial/_bmad-output/task-owner.md'
  - '/tmp/opencode/termux-vm-controlled-vpn-trial/_bmad-output/linux-docker-trial/vpn-stage-readiness.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Replace the company VPN with stock OpenVPN on supplied GCP VM `free-vm`. Generate a private `.ovpn` and demonstrate VPN-only HTTP/private DNS from both joined LD01 A shells, without affecting host/B.

Use controller-managed IAP/SSH TCP forwarding: the profile requires this helper, not a standalone public endpoint. Bind private services to the server tunnel address.

## Boundaries & Constraints

**Always:** Fresh lab PKI, TLS server-name verification, explicit SHA256; secrets outside Git, directories 0700/files 0600 or stricter. Reconcile retained identities/configuration before mutation. Preserve image/homes/networks/project/labels/limits. A recreation may add read-only lab material and NET_ADMIN/SETUID/SETGID; preserve its rollback configuration and record replacement identity. Daily shells remain UID/GID 1001; B stays capability-free.

Split IPv4 routes carry only a collision-free VPN subnet. While connected, all A DNS uses the lab resolver; restore its exact prior resolver on stop/failure. Disable IPv6 only inside A; live IPv6 is NOT RUN. Trial-controller connect/disconnect does not prove restricted daily controls.

Bind forwards only to loopback/selected LD01 bridges; heartbeat and VPN use separate SSH transports. No public ingress, paid IPv4, extra VM, host VPN/resolver/daemon change or host sockets/agents in containers.

Approval starts a fresh maximum-three-hour window including disconnect/cleanup; reconnecting never extends it. Preserve evidence/rollback and report residual resources.

**Never:** Company credentials, original evaluation mutations, global prune/flush, unrelated workloads, secret logging, fault injection or account logins. No company/native-UDP/full-tunnel/account/S1–N3 acceptance claims.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Preflight mismatch | Retained ID/config drift, occupied task path/port, expired deadline | No connection or destructive replacement | Stop with bounded private FAIL evidence |
| Connection | Fresh profile, working forward, daemon-readable material | Verified server; private name resolves; HTTP returns fixture identity | No verification weakening; stop and restore A |
| Stop/failure | Daemon exits or controller aborts | Disconnect, restore resolver/routes/IPv6 state and close task forwards | Record cleanup failure; do not report PASS |
| Continuity | Held host/B sockets with sequenced acknowledgements | Same socket/server connection identity, zero reconnect/reset/error | Failure blocks continuity verdict |

</frozen-after-approval>

## Code Map

Under `_bmad-output/linux-docker-trial/`:
- `tooling/Dockerfile`: frozen OpenVPN 2.6.19 client; avoid rebuild.
- `executed-commands.md`: provisioning/host comparisons; reference, not a rerun script.
- `spot-check.py`: reuse explicit guards, destination-keyed mounts and private reports, not its baseline-only capability expectations/probe campaign.
- `vpn-stage-readiness.md`: superseded company-scope history.

Inspected: GCP IAP/sudo/TUN work; Debian 12/e2-micro, 589 MiB available/26 GiB free, no OpenVPN/dnsmasq. VM has public IPv6 only and IAP ingress; LD01 is IPv4-only. A/B remain running with recorded image/mount layout; full reconciliation is pending.

## Tasks & Acceptance

**Execution:**

Source paths below are under `_bmad-output/linux-docker-trial/controlled-vpn/`.
- [x] `setup-server.sh` — install native packages; create collision-checked task PKI/config/units, tunnel-only DNS/HTTP and loopback heartbeat; export private profile and scoped rollback. Deployment mutates VM packages/services.
- [x] `fixtures.py` — stdlib HTTP identity and persistent sequenced heartbeat/server connection IDs; no reconnect.
- [x] `trial.py` — reconcile ownership/deadline, establish forwards, prepare A, verify actual daemon material access, manage resolver/daemon/cleanup and private evidence. A1 connects/A2 observes-disconnects; A2 reconnects/A1 observes-disconnects. Hold host/B heartbeats throughout.
- [x] `test_trial.py` — regression checks for fail-before-mutation rejection and restoration after connection failure.
- [x] `_bmad-output/linux-docker-trial/controlled-vpn-results.md`, `_bmad-output/task-owner.md`, `_bmad-output/linux-docker-trial/vpn-stage-readiness.md` — profile location, commands, versions/scope, evidence/status and resource disposition.

**Acceptance Criteria:**
- Given reconciled resources, when preparing A, then B retains its ID/capabilities/mounts and A shells stay non-root in one namespace.
- Given the profile/forward, when either A shell connects, then both resolve `service.ld01.test` and reach its HTTP identity; host/B cannot reach it directly.
- Given held host/B sockets, when both cycles complete, then socket identities/acknowledgements persist without reconnect and host/B routes/rules/DNS remain unchanged.
- Given disconnect/failed startup, when cleanup finishes, then A's resolver/routes/IPv6 restore and no task VPN/forward remains active; failed restoration is FAIL.

## Implementation Notes

- **Fresh explicit execution authorization:** user selected “Authorize fresh window” after offline review fixes. Receipt/controller UTC `2026-10-20T07:31:09Z`; new fixed hard stop `2026-10-20T10:31:09Z`, including disconnection/cleanup. This is a separate authorized run, not extension/reuse of the original expired window. Update source guards to this deadline; preserve historical run/evidence and old rollback scripts. Reconcile resources/VM task leftovers before mutation, then deploy revised source with fresh task identities/private lab material and run both cycles including embedded-resolver UDP/TCP and host/B TCP DNS negatives. No live fault injection. Clean up and document exact new results/disposition. No commit/push/PR.

- Approved and continued by the user at the resumed approval checkpoint. Re-read from disk; no external spec changes observed. Existing uncommitted planning updates are preserved.
- Approval receipt/controller UTC: `2026-10-19T21:43:21Z`; fixed hard stop `2026-10-20T00:43:21Z`, including disconnection and cleanup. Controller local timezone is UTC+03; use UTC throughout. Reconnects do not extend the deadline.
- Exclusive LD01 reuse acknowledgement carries forward from task-owner.md. Reconcile before mutation; do not access company material.
- Implementation session uses `/tmp/opencode/termux-vm-controlled-vpn-trial` on `feat/controlled-vpn-trial` exclusively; the coordinating session waits during the delegated implementation. Preserve all existing planning edits and check for external changes/overlapping processes before editing. No commit, push, PR, or VCS remote changes authorized. GCP deployment/execution explicitly authorized with `gcloud compute ssh free-vm --tunnel-through-iap`.
- Read private baseline only from `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/resources.json`, `image.json`, and `spot-check-20261019T152932087625Z.json`; avoid the historical company-material readiness file and all company staging. Source audit is [executed commands](../linux-docker-trial/executed-commands.md). Inspect configuration destination-keyed, not mount-array order.
- Implement, run regression checks, deploy, execute both live cycles and restore/clean up within the fixed deadline. Keep generated lab secrets/raw logs/evidence in a new 0700 directory under `/tmp/opencode`, never in the worktree. Record paths/identities and exact failures honestly. Reserve cleanup time and arm bounded cleanup/watchdogs; do not start a cycle too close to the deadline.
- Completed implementation/live execution `2026-10-19T21:53:15Z`–`21:54:56Z`; cleanup `21:54:47Z`. No container recreation was needed: capability-restricted root daemon reads root-owned 0600 material; A-only netfilter rules disable IPv6 traffic and restrict DNS during connection. Exact prior state restored on both stops. See [controlled results](../linux-docker-trial/controlled-vpn-results.md).
- Three independent review layers completed; source fixes and coordinating offline verification passed. The expired original-window blocker was resolved by the separate fresh authorization at `2026-10-20T07:31:09Z`; revised live attempt 1 and both cycles PASS, cleanup PASS `07:36:31.392240Z`. Exact new evidence/profile: `/tmp/opencode/controlled-vpn-20261020T0736Z-attempt1/`. Original evidence and old VM rollback scripts are preserved. Coordinating evidence verification passed; status `done`. No commit/push/PR authorized or performed.

## Spec Change Log

## Review Triage Log

| ID | Verdict | Evidence and route |
|---|---|---|
| B1 | high | `cleanup()` caches failed `cleaned.json`, preventing retries after transient restoration/SSH failure. Patch: cache only PASS, preserve failed attempts. |
| B2 | high | Agent clears active on failed restoration; controller can then delete the only restore journal. Patch: retain active/journal and require explicit successful restoration before deletion. |
| B3 | high | Remote setup is not serialized with rollback and may continue after SSH loss. Patch: shared deployment/rollback lock plus cancellation marker and server-side bounded setup. |
| B4 | high | Agent mutation/startup does not share restoration lock, allowing a late daemon/state mutation after cleanup. Patch: serialize actions, validate active generation, atomically journal daemon launch. |
| B5 | medium | Sleep-only cycle watchdog retirement has no generation identity. Patch: generation-bound watchers and explicit retirement. |
| B6 | high | Read-only `iptables -t nat -S` confirms Docker DNATs embedded-resolver port 53 to high ports before filter OUTPUT. Patch: restrict original DNS destinations before DNAT and prove UDP/TCP embedded-resolver rejection. Original live probes used the correct lab resolver, but did not prove this restriction. |
| B7 | medium | Sequential bounded probes can outlast the 20-second lease. Patch: renew independently during controller work, retain fixed deadline/controller-loss cleanup. |
| B8 | maybe-false | Historical baseline retains network IDs/IPAM but not original endpoint MAC/IP/gateway values. Current run's full endpoint snapshot is preserved; a changed historical endpoint cannot be established from that baseline. Defer medium/unverified historical endpoint comparison pending authoritative original endpoint evidence. |
| B9 | medium | Host/B negatives omit TCP DNS although DNS listens on both transports. Patch: require bounded TCP DNS unreachability too. |
| B10 | high | Slow package/PKI setup can pass initial deadline then create late units. Patch: bound server-side setup and recheck positive deadline reserve before unit creation/start. |
| E1 | medium | Forward spawn precedes durable PID registration. Patch: gate exec until registration, EOF cancels unregistered child. |
| E2 | high | Same late-unit/deadline root cause as B10. Patch together. |
| E3 | high | Same startup/restoration race as B4; missing PID creates a late tunnel. Patch together. |
| E4 | high | Firewall inspection timeout escapes before resolver restoration. Patch: independently attempt each firewall operation and resolver restoration. |
| E5 | high | Same rollback-journal deletion as B2. Patch together. |
| E6 | medium | Unreaped controller zombie retains start identity. Patch: treat zombie as dead. |
| E7 | medium | Same missing TCP DNS negative as B9. Patch together. |
| V1 | medium | Pre-verified test gap: one-ack fixture test and synthesized JSONL never test wrong later peer replies. Patch: actual multi-ack sequence/connection-ID corruption tests. |
| V2 | medium | Pre-verified test gap: no watchdog trigger tests. Patch: sandbox actual A/controller watch paths, including healthy case and terminal cleanup state. |
| V3 | medium | Pre-verified test gap: daemon TERM/KILL and tunnel deletion skipped in sandbox. Patch: disposable task-identified process and scoped tunnel deletion transport. |

All fixes preserve approved intent and successful live behavior; no frozen changes are needed. Three independent read-only review layers completed. Review source snapshot: `/tmp/opencode/controlled-vpn-diff-2epssklo.patch`.

Patch verification: B1–B7, B9–B10, E1–E7 and V1–V3 have source corrections and passing focused regression coverage. B8 remains deferred/unverified as recorded. Runtime mutation after the original window occurred only under the separate fresh explicit authorization below.

Fresh-run triage disposition: both cycles now pass conntrack-protected embedded
UDP/TCP DNS negatives and host/B TCP DNS negatives (B6, B9, E7), alongside working
lab DNS/HTTP. Normal-path generation locking, lease renewal, watcher retirement and
restoration passed live. Automatic failure paths retain sandbox evidence only;
no live fault injection was performed. Additional full-endpoint equality compares
the original controlled live capture with this run, not the missing earlier
baseline; it does not resolve B8.

Two private audit failures are preserved, with no failed live trial attempt:
preflight inspection self-match corrected to exact fixture arguments, and a
post-audit name-only process check corrected to distinguish state-Z entries from
active daemons. State-aware post-audit passed all 19 checks. Four actual residual
A zombie entries remain: watchers 1006/1294, OpenVPN 1037/1325, all parent PID 1;
no active task VPN/watcher/socket/tunnel remains. The unchanged PID 1 is
`sleep infinity`, which has not reaped them; no container restart/recreation was
performed. These residuals and every audit/run disposition are recorded in
[controlled results](../linux-docker-trial/controlled-vpn-results.md).

## Verification

- `python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p 'test_*.py'` — rejection/restoration checks pass.
- `bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh` and `git diff --check` — pass.
- Historical live invocation: `python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py --private-dir /tmp/opencode/controlled-vpn-20261019T2153Z` — exit 0, both cycles and cleanup PASS; host/B 43/42 sequenced acknowledgements, zero reconnects/errors. Timestamped evidence and 0600 private profile are outside Git in that directory. Original shell DNS/HTTP, continuity and restoration observations remain valid; review identified missing TCP DNS negatives and embedded-DNS enforcement, so final patched acceptance is not claimed. IAP heartbeat continuity proves only that controlled non-VPN path. No live fault injection or expanded acceptance claim.
- Coordinating offline verification `2026-10-20T07:25Z`: all 31 sandbox regressions passed, Bash syntax passed, tracked/untracked whitespace checks passed. Untracked source checked for private-key/static-key markers; none found. Generated test bytecode removed. No commit/push/PR or runtime mutation occurred at that checkpoint; the then-expired-window blocker is resolved by the separate fresh authorization/run below.
- Fresh predeployment checks `2026-10-20T07:32:21Z`: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p test_trial.py -v` — all 31 pass (7.582 s); `bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh` — pass. Reconciliation and source/context/overlap checks passed before deployment. No further trial implementation edit was required.
- Exact fresh live invocation: `PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py --private-dir /tmp/opencode/controlled-vpn-20261020T0736Z-attempt1` — exit 0/PASS. Started `2026-10-20T07:34:59.838456Z`, finished `07:36:40.236169Z`; task `cvpn152283967635`; cycle 1 `07:35:49.989077Z`–`07:36:07.179645Z`, cycle 2 `07:36:07.179675Z`–`07:36:24.377179Z`. Both shells' DNS/HTTP, embedded-resolver UDP/TCP negatives, host/B HTTP/UDP/TCP DNS negatives, exact A restoration and host/B configuration preservation PASS. Held socket acknowledgements host/B 53/52, zero reconnects/errors. Cleanup PASS `07:36:31.392240Z`, before fixed `10:31:09Z` stop; no active task VPN/forward/VM services remain, four state-Z A residuals documented above.
- Fresh private audit evidence: `/tmp/opencode/controlled-vpn-20261020T0733Z-audit/preflight.json` FAIL (inspection self-match, retained); `/tmp/opencode/controlled-vpn-20261020T0735Z-audit/preflight.json` PASS; run directory `post-run-audit.json` FAIL (name-only zombie criterion, retained), `post-run-audit-2.json` PASS (19 checks, `07:40:48.924494Z`). Original local profile/evidence/state/cleanup hashes and old VM rollback hash/mtime unchanged. Both retained VM task/material/source directory sets and six native packages are inventoried in controlled results. No company material, live fault injection, commit/push/PR, or spec-done transition.
- Final coordinating proof: `python3 /tmp/opencode/controlled-vpn-final-proof.py` — PASS. Directly checked both cycles, four identical persistent-shell probes, TLS exact-name log entries, all added negatives, every heartbeat sequence/socket/server identity, all 19 audit checks, cleanup deadline, actual current implementation/original-evidence hashes, private permissions and four disclosed state-Z residuals. Matrix rows covered by live connection/continuity/restoration and 31 sandbox rejection/failure/watchdog checks. All task acceptance is complete; B8 remains explicitly deferred/unverified. Spec then marked done without a commit, respecting the user's Git restriction.
