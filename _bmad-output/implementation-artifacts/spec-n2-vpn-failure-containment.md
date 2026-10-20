---
title: 'N2 controlled VPN failure containment and recovery'
type: 'feature'
created: '2026-10-20'
status: 'in-review'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: 'dc1a192619471c74692833e65122d4fa4ebeeec1'
context:
  - '{project-root}/_bmad-output/linux-docker-trial/n2-proposal.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Add failure containment/recovery to the controlled OpenVPN lab. PR #4 proves normal disconnect only. User accepted P1–P3 on 2026-10-20; spec approval remains pending.

## Boundaries & Constraints

**Always:** Preserve frozen LD01 image, A/B identities/configuration, non-root shells, resources/evidence and old deployed scripts. Reuse separate forwards/verified TLS. Reconcile endpoints/exclusive reuse before mutation. Secrets/raw evidence outside Git, 0700 directories/0600 files. Live work requires separate explicit injection/observation approval and fixed UTC window including cleanup.

**Never:** Company material, accounts, container recreation/restart, extra capabilities/dependencies, host route/resolver/firewall changes, public ingress, package upgrades, global cleanup or unrelated traffic capture. No full N2/N3, company, full-tunnel, native-UDP or live-IPv6 acceptance claims. B8 remains deferred.

## Accepted Decisions

**P1:** Starting/connected/fault: VPN-bound IPv4, including existing flows, leaves only through `ld01tun`; all A UDP/TCP DNS stays tunnel-only, without embedded/public fallback. Faults latch protection and safely retire the failed client; public DNS also fails, unrelated direct-IP traffic continues. Retain A's IPv6 block; live IPv6 untested. Explicit off stops the client before releasing protection and restores exact baseline/DNS, without an always-private-name rule.

**P2:** Explicit off → connect; reject late start/renew of faulted generations. Controller/agent/lease failure never implicitly unblocks. Later live authorization must pre-authorize supervised abort/expiry off, archiving evidence first, beginning no later than hard stop minus ten minutes. Maximum fresh window: 45 minutes including cleanup; no injection in its last fifteen minutes or automatic live retries. No window starts now.

**P3:** Identity-checked client SIGKILL and VPN-only forward termination: healthy baseline → 60-second fault observation → explicit off → verified reconnect. Keep shells/controller/heartbeat alive. Observe fresh/held VPN flows, application/direct private DNS, unrelated A direct traffic and host/B continuity using scoped A-veth headers/counters, positive readiness proof and drop statistics. Defer controller kill/blackhole/recreation. Approve live injections/capture/targets/exclusive reuse separately after offline checks/review.

## I/O & Edge-Case Matrix

| Scenario | Input/state | Required observation | Error handling |
|---|---|---|---|
| Admission | Missing approval, drift, expired window or insufficient reserve | No deployment/injection | Private rejection record |
| Positive baseline | Verified connection | Both shells reach exact private HTTP/DNS fixture | Stop campaign on failure |
| Unexpected failure | Client or VPN-only transport lost | P1 latch; no VPN-prefix/private-DNS underlay egress; unrelated direct traffic works | No PASS based on timeout alone |
| Recovery | Explicit off and later connect | P1 baseline restoration, then fresh verified connection | Preserve failures before next generation |
| Teardown error | Restoration incomplete | FAIL, retain journals/material | No destructive retry/recreation |

</frozen-after-approval>

## Code Map

Paths below are under `_bmad-output/linux-docker-trial/controlled-vpn/`:
- `trial.py:154–371` — agent locks/generations/PIDs/DNS rules/journal; faults currently restore baseline, no prefix guard.
- `trial.py:433–502,675–872` — cleanup/health/cycles/host watcher must all distinguish fault from off.
- `trial.py:27,159,540–543`, `setup-server.sh:12,69–70` — historical deadline/worktree pins; refresh together under new authorization.
- `fixtures.py:20–94` — socket sequencing/shell probes; add negatives/held VPN flow.
- `test_trial.py` — AgentSandbox/race/cleanup tests; update fault-restoration expectations.

## Tasks & Acceptance

**Execution after spec approval; live work needs separate authorization:**
- [x] `trial.py` — guard prefix/interface before DNS/client startup; latch faults across cleanup/watch callers; preserve generations, retryable journals and archival. Add bounded fault/capture orchestration and consistent deadline guards.
- [x] `fixtures.py`, `setup-server.sh` — tunnel-bound heartbeat, uncached DNS/direct-IP negatives, fresh authorization guards; retain TLS/transports/private-zone locality/packages without apt updates.
- [x] `test_trial.py` — sandbox startup ordering, existing flows, all fault callers, stale generations, manual recovery, expiry off and retryable restoration failures.
- [x] `_bmad-output/linux-docker-trial/n2-results.md`, `_bmad-output/task-owner.md` — record attempts/commands/window, private paths, measured bounds and residuals; preserve historical verdicts.

**Acceptance Criteria:**
- Given an admitted campaign, when either fault occurs, then fresh/held VPN traffic and application/direct private DNS have no forbidden underlay egress throughout observation, proven by ready/drop-accounted capture and counters, not timeouts alone.
- Given faults/recovery, when observed, then the same non-root A shells remain usable, host/B sockets have zero reconnect/reset/error/gap, and host/B settings remain unchanged.
- Given explicit off, when followed by reconnect, then approved off DNS/traffic behavior and a fresh verified fixture connection work without manual repair.
- Given completion/abort, when authorized cleanup runs, then exact A network/resolver/filter/nat state and retained configuration restore; errors block PASS.

## Implementation Notes

- Operator attempt 1 ran `2026-10-20T10:42:01.745910Z`–`10:43:15.924575Z`, task `cvpnb76f5884442f`: FAIL at positive baseline (`joined shell exited`), before any injection; F1/F2 NOT RUN. A network restoration PASS; overall cleanup FAIL on capture's blank separator. Read-only audit passes 20 disposition checks; two new state-Z children (1923/1944), A material and VM audit/PKI/source retained. No retry/recreation. Executed files hash-archived privately before offline parser and private-stderr-retention patches; 76 tests pass. Primary baseline exception remains unknown because original stderr was discarded; another live attempt requires fresh scope/window and explicit reconciliation of six zombies/retained journals. See [live failure record](../linux-docker-trial/n2-results.md#operator-attempt-1--fail-before-fault-injection).

- Separate operator-launched authorization/controller UTC `2026-10-20T10:38:30Z`, fixed hard stop `11:23:30Z` including cleanup; cleanup by `11:13:30Z`, no injection at/after `11:08:30Z`. User will run the existing controller from their authenticated terminal because their sudo cache is unavailable to the agent. Same F1/F2/capture/targets/exclusive-reuse/supervised-off scope; no automatic retries. Fresh private approval at `/tmp/opencode/n2-20261020T103830Z-approval/authorization.json`; unused attempt path `/tmp/opencode/n2-20261020T103830Z-attempt1`. No source/privilege-policy change; await operator run before judging live acceptance.

- Fresh live authorization received/controller UTC `2026-10-20T10:25:44Z`; fixed hard stop `2026-10-20T11:10:44Z` including cleanup. User explicitly authorized F1/F2, scoped capture/probes, supervised abort/expiry off and exclusive LD01 reuse with no other worker/session. Cleanup reserve starts `11:00:44Z`; no injection at/after `10:55:44Z`. One attempt per case, stop at first unexpected failure; reconnects never extend this window. This later approval supersedes the earlier offline-only restriction solely for this scoped campaign; no company material or publication authorized.
- Window admission BLOCKED before deployment: retained reconciliation passed, but host `sudo -n true` failed and `sudo -n -l` requires interactive authentication. tcpdump has no file capabilities. No live case/capture/connection/deployment occurred; no task cleanup was required. Private admission failure at `/tmp/opencode/n2-20261020T102544Z-approval/admission-failure.json`. Stop without retry; await user-side authentication and renewed instruction/window. Spec remains `in-review`; live acceptance NOT RUN.

- User approved and continued on 2026-10-20 after accepting P1–P3. Re-read unchanged spec before approval; frozen intent is locked. The earlier pending-approval sentence is historical. Approval permits offline implementation/tests/review only; no live deployment, connection, capture or injection/window is authorized.
- Project root for this task is `/tmp/opencode/termux-vm-n2-vpn-failure-containment`, branch `feat/n2-vpn-failure-containment`; implementation owner works exclusively here while coordinating session waits. Resolve `{project-root}` in context against this worktree. No concurrent runtime/artifact worker is authorized. Preserve baseline revision and all frozen content; do not commit/push or perform remote operations.
- Offline implementation and review corrections are complete. Keep status `in-review` until separately authorized live acceptance is observed; checked tasks record implementation/documentation, not live AC completion. No commit or live operation is implied by the build completion step.

## Spec Change Log

## Review Triage Log

Initial independent review, 2026-10-20. Each finding is retained below before grouping; routes are internal corrections to the approved behavior, with no intent changes.

| ID | Verdict | Evidence and route |
|---|---|---|
| B1 | medium | F2 immediately calls agent fault/retirement after one status snapshot; no probes exercise live-client/broken-transport state. Patch a bounded observation before retirement; preserve the full fault interval. |
| B2 | high | `stop_forward(injection=True)` succeeds when the recorded target already vanished, skipping reserve/identity validation. Patch: injection requires a live matching target; cleanup stays idempotent. |
| B3 | high | CAPTURE waits indefinitely for its gate byte before applying absolute expiry. Patch gate wait with the same deadline and retire on timeout/EOF. |
| B4 | high | Capture proof accepts received>captured with zero drops, leaving unparsed matching packets unaccounted. Patch fail-closed accounting/draining; no missing headers may count as proof. |
| B5 | high | Watch readiness is a permanent file; eight-second lock timeout can kill watcher without invalidating health. Patch retry contention and check watcher identity/completion after readiness. |
| B6 | high | Supervisor reads state before cleanup serialization; controller mutations/save share neither cancellation ordering nor state publication lock. Both use `state.new`. Patch cancellation-before-teardown, serialized mutation/publication, unique staging and fresh cleanup state. |
| B7 | high | Exclusive lock belongs only to controller; preflight ignores retained fault chains/journals. Patch retain lock through supervisor and reject unresolved task state before baseline adoption. |
| B8 | false | Controller refuses automatic cleanup retry after failed off, as the approved no-automatic-live-retry rule requires. Root `restore` remains directly callable for a later human-directed retry and is tested retryable. No new retry command is needed for this bounded campaign. |
| B9 | high | Fault hold catches ValueError/JSON corruption as a blocked flow, satisfying the negative oracle. Patch protocol errors to fail; only transport errors may produce blocked events. |
| B10 | medium | Fault archives contain baseline journals and log, not current rules/routes/counters/process status. Patch bounded current snapshots with independent observation error records before retirement/release. |
| E1 | high | Prepare publishes starting intent before block; watcher registration widens the unprotected startup interval. Patch install protection before publishing starting/readiness and remove controller-side gap. |
| E2 | high | Same watcher contention/root cause as B5; patch watcher-loss handling. |
| E3 | high | Direct-written cleanup-attempt JSON can be truncated; archive comprehensions raise before daemon retirement/off. Patch atomic records plus tolerant archival of malformed non-authoritative attempt records. |
| E4 | high | Same missing-injection-target defect as B2. |
| E5 | high | Same unbounded capture gate defect as B3. |
| V1 | medium | Pre-verified: cycle tests mock `probe_shells`; removing rejection of embedded DNS responses passes. Patch real verdict tests for every prohibited result. |
| V2 | medium | Pre-verified: successful controller off/reconnect is mocked; removing prepared-state clearing passes. Patch real transition test with synthetic transport. |
| V3 | medium | Pre-verified: F2 real reserve boundary is untested; expired-preflight test instead fails for absent deadline. Patch valid-authority 900/899-second F2 boundary and expiry-specific rejection tests. |
| C1 | high | Coordinating verification of B6 patch: `@mutating` holds cleanup.lock for full deployment/connect/off; supervisor waits only eight seconds and exits on contention, even though commands can run 30–360 seconds. Publication lock around a root action also exceeds cancellation's eight-second wait. Patch cooperative cancellation at command boundaries and bounded supervisor acquisition covering an in-flight command inside cleanup reserve; prove slow-operation cancellation without abandoning cleanup. |
| L1 | medium | Live cleanup parser rejects tcpdump's trailing blank separator despite 100 captured/received packet headers and zero drops. Offline patch skips only whitespace records; unknown nonblank headers and count/drop checks remain strict. Regression and retained-capture offline recheck pass; original live FAIL remains preserved. |
| L2 | medium | Baseline worker EOF discards stderr during close, preventing primary-cause diagnosis. Patch bounded private stderr/action/exit retention on EOF; actual disposable-worker regression passes. This repairs diagnostic loss, not the undiagnosed primary worker failure. |

**Disposition:** B1–B7, B9–B10, E1–E5, V1–V3 and C1 are corrected and covered by the passing 74-test suite. Shared-root findings were patched once: B2/E4, B3/E5, B5/E2, B10/E3. B8 is rejected on the specific root-restore retry evidence above. No unresolved offline review finding is deferred. Historical LD01 B8 is a different issue and remains deferred/unverified.

C1 now publishes cancellation before waiting, caps an in-flight admitted command at 100 seconds, allows 110 seconds for supervisor lock acquisition, and shares a 300-second teardown budget capped by the absolute remaining window minus 20 seconds. Deterministic connect/deploy and lock-failure tests cover cleanup continuation and private failure records. Live timing is not established by these sandbox bounds.

## Verification

Post-live offline corrections: **76 sandbox tests pass in 16.382 seconds, no skips**;
server shell syntax and `git diff --check` pass. Matrix rows are covered by admission, positive-baseline
abort, both synthetic fault/off/reconnect sequences, held-flow rule evaluation,
unauthorized versus supervised cleanup, and retryable restoration checks. See
[N2 results](../linux-docker-trial/n2-results.md) for attempts, evidence conventions,
bounds and residuals. Live acceptance criteria remain NOT RUN; no live window or
capture/injection authorization was created by implementation. All three independent
review layers reported; corrections and final coordinating verification are complete.

Before live authorization:
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p test_trial.py -v` — adapted sandbox suite passes, without Docker/GCP.
- `bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh` and `git diff --check` — pass.

Live execution needs separate authorization/window and `n2-proposal.md` gates.
