---
title: 'Retain admitted capture authority for detached cleanup'
type: 'bugfix'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '2293a9943a570ff627e07856581d3fea2f2df85f'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Fix capture cleanup when terminal sudo succeeds but sudo in the independent
detached supervisor fails. Admit root authority once for the existing bounded
capture wrapper; let that wrapper stop only its own registered capture child on
an attempt-specific durable request. Normal off and controller-loss/expiry cleanup
must share this path without another sudo invocation.

## Boundaries & Constraints

**Always:** Preserve the detached independent supervisor, exclusive ownership,
fixed authorization window, ten-minute reserve, cancellation/publication locks,
rollback behavior and exact capture PID/start identity/interface/filter checks.
Retain inbound A-veth-only 96-byte capture, positive-canary and zero-drop/count
proof. Admission/cleanup errors remain failures. Check authority before deployment
where feasible; fail closed rather than silently depending on a detached sudo
timestamp. Keep root authority restricted to the existing bounded capture worker.

**Never:** Modify sudo policy/cache scope, run the whole controller as root, add
capabilities/dependencies or a general privileged service. No Docker/GCP/VPN,
real packet capture, injection, company material, resource changes, live retry,
new live window, publication, or historical-verdict rewriting in this task.
Verification uses only disposable ordinary-user subprocesses and temporary files.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Normal off | Admitted wrapper, matching child and private stop request | Wrapper identity-checks and interrupts its child, reaps it and reports completion | Missing/bad completion or statistics fails |
| Controller loss | Detached supervisor reloads durable state; sudo now denied | Supervisor requests the same stop without sudo; wrapper completes bounded stop | Cleanup remains FAIL if termination/proof is absent |
| Cross-attempt request | Stop marker for another capture | Current worker continues until its own request or expiry | Never signal another PID |
| PID/specification drift | Stale start identity or wrong command/interface/filter | No signal to the mismatching process | Explicit failure; no PASS from disappearance alone |
| No release | Gate EOF or gate held open through expiry | Child never executes capture; wrapper retires it by bounded expiry | Nonzero result |
| Expiry or stuck child | Gate released, no valid stop, or child ignores interrupt | Absolute expiry retires owned child with bounded escalation | Expiry/forced termination cannot count as normal capture success |
| Premature worker exit | Child or wrapper exits before requested stop | Independent child termination and completion accounting required | Incomplete capture cannot yield cleanup PASS |

</frozen-after-approval>

## Code Map

All runtime/test paths are under `_bmad-output/linux-docker-trial/controlled-vpn/`.

- `trial.py:770–794 CAPTURE` already gates a child, records its identity, owns its
  process handle and enforces absolute expiry. Extend this worker rather than
  introducing another privileged process/service.
- `trial.py:846–873 stop_capture/stop_capture_owned` currently reauthenticates with
  `sudo -n python3` to signal tcpdump. Both controller and cleanup route here.
- `trial.py:1378–1416 start_capture` registers state before releasing the child;
  persist the unique stop endpoint before release, preserving this ordering.
- `trial.py:818–835 capture_proof` enforces readiness/canary/count/drop/underlay;
  retain those predicates and require worker completion where appropriate.
- `trial.py:889–960 cleanup_owned`, `1523–1526 cycle`, `1572–1575 baseline`,
  `1583–1587 execute`, `1679–1711 watch`: preserve all callers and independent
  supervisor semantics. No second cleanup retry after a failed attempt.
- `test_trial.py:876–907,1016–1037` contains synthetic capture evidence and real
  disposable gate/expiry subprocess tests; extend these helpers for stop requests.
- `test_baseline.py:360–400` checks single baseline/no injection and abort paths.
- `_bmad-output/task-owner.md`: append this isolated task's offline disposition.

## Tasks & Acceptance

**Execution:**
- [x] `trial.py` — extend the admitted wrapper/registration/stop handshake; remove
  stop-time sudo while preserving exact identity, expiry and proof contracts.
- [x] `test_trial.py` — reproduce detached cleanup with a fake ordinary-user
  capture child and a forbidden sudo runner; cover the matrix without real capture.
- [x] `_bmad-output/task-owner.md` — record the confirmed admission blocker,
  implementation boundaries, checks and remaining live admission prerequisites.

**Acceptance Criteria:**
- Given an admitted synthetic capture and a detached cleanup process with no sudo
  authority, when the controller disappears and the supervisor requests off,
  then the real wrapper retires its own child and strict capture proof passes.
- Given malformed/stale state, wrong identities or missing completion, when stop
  runs, then it cannot signal unrelated processes or return capture success.
- Given the existing baseline-only and campaign orchestration, when regression
  tests run, then no injection/acceptance/restoration predicate is weakened.
- Given completion, when inspected, then only offline source/tests/redacted
  artifacts changed and no new live verdict or execution authority is claimed.

## Implementation Notes

- User approved and continued; frozen intent re-read unchanged before approval.
- Owner OpenCode; branch `fix/detached-cleanup-authority`; worktree
  `/home/rat/Git/termux-vm-detached-cleanup`, created with explicit user permission.
- No intent gaps or irreversible actions. Privileged worker lifecycle changes
  merit dispatch review despite the narrow code footprint.
- Planning delegation failed because the subagent usage limit was reached;
  investigation continued inline. No investigator edited the separate read-only
  worktree. Review will follow the workflow's unavailable-agent fallback if needed.
- Implemented in `trial.py` and `test_trial.py`; only redacted task handoff/spec
  accompanies code. CAPTURE retains its one admitted privilege context, polls an
  attempt-specific stop marker, validates the child, reaps it and writes a receipt
  to existing private stderr. No privileged file contents are read for the marker;
  it only requests retirement of the worker's own registered child.
- Unexpected command drift is fail-closed: the worker does not signal a changed
  command or claim it was retired. Tests clean only their disposable child after
  proving this refusal. Normal operational expiry still retires the matching child.
- Old capture records without the new control/receipt contract fail closed; no
  compatibility cleanup of an earlier retained attempt is implied.
- The original baseline branch/worktree admission pins are preserved. This new
  branch is an offline fix artifact and requires integration and refreshed source
  approval/admission before live use; no controller invocation was made here.

## Spec Change Log

## Review Triage Log

- Independent review has not run: subagent launch returned `The usage limit has
  been reached`. No findings or clean-review result are claimed. Workflow fallback
  handoffs are provided as `review-detached-cleanup-{blind,edge,verification}.md`
  beside this spec for separate sessions; await all three results before triage.

### Independent review retry — all three reviewers returned

Review retry succeeded in three separate worktrees. Findings are individually
classified below before grouping. This supersedes the unavailable-review status
above. The generated fallback prompts were removed after actual reviews returned;
the findings and dispositions below replace those redundant diff copies.

| ID | Verdict | Evidence and route |
|---|---|---|
| B1 | medium | Reviewer follow-up compared old/new workers: SIGINT previously ran unconditional finalization, but the changed released-child branch leaves the matching child alive. Patch bounded identity-checked finalization. SIGTERM/SIGKILL worker-loss cases were reproduced in both versions and are separately deferred as pre-existing. |
| B2 | medium | Worker accepts `lexists()` markers while the caller rejects unsafe endpoint types/permissions; a dangling symlink yields a successful requested-stop receipt. Patch worker-side private regular-file validation before accepting a request. |
| B3 | medium | Child can exec a different command during the five-second interrupt grace. Revalidate the owned PID/start identity/command immediately before forced escalation; mismatches remain unverified, not signalled. |
| B4 | medium | Child can exit between liveness polls after a marker is noticed; old code emits requested success without an identity-checked interrupt. Patch explicit requested-stop signal accounting and add the interleaving test. |
| B5 | medium | Wall-clock rollback extends the polling loop's lifetime versus its initial remaining duration. Patch a monotonic cap alongside absolute UTC expiry and test a backwards clock. |
| B6 | false | Reviewer withdrew this as a regression after tracing: new preflight is explicitly a best-effort root/tool probe, not a guarantee of later exact-command sudo grants. Later sudo invocation denial was possible before this change; failure still blocks capture and invokes scoped teardown. |
| E1 | high | Released gate may not have exec'd capture when request/expiry arrives. Current command equality rejects the still-owned gate and skips finalization. Patch recognition/retirement of the exact registered gate argv, without treating a gate stop as successful capture. |
| E2 | medium | Independent report of B4's second-poll early exit. Same requested-stop accounting correction; preserve this finding separately. |
| E3 | medium | Deletion review independently identifies B1's released-child KeyboardInterrupt finalization regression. Same shared finalization correction. |
| E4 | medium | Claims check independently confirms B1/E3's lost expiry after post-release interruption. Same shared finalization correction; no frozen intent change needed. |
| V1 | medium | Pre-verified receipt-binding gap: deleting receipt-to-registration equality passes existing direct-worker tests. Add wrong-child/worker/command/endpoint receipt cases. |
| V2 | medium | Pre-verified endpoint-test gap: altered state is rejected by registration before path guards, so path/privacy guard removal is undetected. Add consistent-registration location and completed-worker symlink/type/mode cases. |
| V3 | medium | Pre-verified admission predicate gap: injected `run()` failure never executes root/tool expression. Execute submitted predicate in an ordinary-user controlled UID/lookup harness. |

All surviving story findings route to **patch**: internal local guards/accounting,
bounded finalization reuse and regression checks; no new public interface or intent
decision. Groups: B1/E3/E4 (released-child finalization), B4/E2 (premature completion).
Other findings remain individual corrections. Arbitrary SIGTERM/SIGKILL loss of
the privileged wrapper is a confirmed pre-existing limitation, not repaired or
claimed solved by this scoped change.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p 'test_*.py' -v`
- `bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh`
- `git diff --check`

### Initial verification

- Full suite: 107 tests PASS in 30.363 seconds, no skips. Bash syntax/whitespace
  PASS. Tests invoke no sudo, retained Docker/GCP/VPN or actual packet capture.
- Matrix audit: normal off → `test_real_start_stop_is_registered_private_and_never_reauthenticates`;
  controller loss → `test_capture_survives_actual_controller_kill_then_detached_watch_cleans`
  and `test_detached_real_supervisor_reloads_after_controller_loss_without_sudo`;
  cross-attempt → `test_other_attempt_stop_does_not_interrupt_this_capture`;
  identity/spec drift → `test_wrong_registration_specification_and_path_never_request_or_signal`
  and `test_worker_refuses_to_signal_child_whose_command_changed`;
  gate EOF/stall → existing `test_capture_worker_expires_without_controller_and_cancels_on_eof`;
  expiry/stuck → `test_premature_exit_bad_exit_missing_completion_and_expiry_fail`
  and `test_ignored_interrupt_is_bounded_and_never_passes`;
  premature/missing receipt → the former combined test. All covering tests ran.

### Final verification and review corrections

- All three independent reviewers completed in separate task worktrees. Every
  reported finding has an individual disposition above. All introduced defects
  and accepted verification gaps are patched; one pre-existing privileged-wrapper
  SIGTERM/SIGKILL limitation is recorded in `deferred-work.md`. The existing sudo
  argument-policy limitation was withdrawn as a regression finding.
- Full final suite: **116 tests PASS in 39.253 seconds, no skips**. Bash syntax,
  working-diff and staged-diff whitespace checks PASS. Focused correction suite:
  **19 tests PASS in 18.743 seconds**, no skips. No real sudo, packet capture,
  retained-resource, Docker/GCP/VPN, package or privilege-policy operation occurred.
- Worker finalization now identity-checks and retires matching released children
  after Python interruption. A still-owned pre-exec gate is recognized and retired
  without a successful capture verdict. Forced escalation rechecks the command.
  A monotonic cap supplements UTC expiry; only a real requested capture interrupt
  can yield a successful completion receipt. Worker-side marker type/mode/owner
  guards reject unsafe requests before accepting them.
- Review coverage: B1/E3/E4 →
  `test_wrapper_interrupt_retires_matching_child_without_claiming_success`;
  B2 → `test_worker_rejects_unsafe_marker_instead_of_certifying_requested_stop`;
  B3 → `test_escalation_rechecks_command_after_interrupt_handler_exec`;
  B4/E2 → `test_exit_between_request_poll_and_signal_is_premature_not_success`;
  B5 → `test_clock_rollback_cannot_extend_initial_expiry_budget`;
  E1 → `test_gate_not_yet_execed_is_retired_on_stop_or_expiry`;
  V1 → `test_completion_receipt_is_bound_to_every_registered_field`;
  V2 → `test_completed_stop_rejects_unsafe_endpoint_at_the_path_guard`;
  V3 → `test_submitted_admission_predicate_rejects_nonroot_and_missing_tool`.
  All named checks ran and passed in both focused and final verification.
- `done` covers this approved offline fix and review, not live acceptance.
  Historical verdicts and old worktrees/evidence remain unchanged. No commit,
  push, PR, new live window or trial was authorized or performed in this task.
