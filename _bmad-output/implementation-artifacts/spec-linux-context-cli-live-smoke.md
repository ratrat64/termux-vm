---
title: 'Real-Docker smoke verification of the Linux LD01 context CLI'
type: 'feature'
created: '2026-10-27'
status: 'blocked'
baseline_revision: '85a0d47bd09ca7a4ae296640e22ee5c34da7aaf7'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The committed CLI has offline coverage but real Docker format rendering,
PTY joins, concurrent shell independence and exit propagation remain unverified.

**Approach:** Add a minimal Python-stdlib smoke harness invoking `cli.py` as a real
process, then verify it within one authorized live window. Fix only demonstrated
CLI/harness defects with focused offline regressions.

## Boundaries & Constraints

**Always:** Exclusively own `feat/linux-context-cli` in the designated worktree.
Require a clean committed start. Record one fixed 20-minute UTC live window before
preflight; stop starting checks with less than five minutes remaining. Reconcile
saved identities/configuration and current residuals before joins. Keep raw evidence
outside Git with directory mode 0700 and file mode 0600. Preserve journals and all
unrelated work. Bound subprocesses and sessions with timeouts; close only sessions
created by this run. Missing evidence, denied access, unexpected drift, unsupported
or stopped containers, or window expiry block completion. The user's later context
allows the already-completed original-container restart and new empty scratch;
historical zombies need not survive that restart. No VPN baseline adoption is required.

**Never:** Provision, change lifecycle or permissions, use sudo, access credentials
or profiles, probe networks, perform VPN/GCP activity, write shared project data,
retry cleanup, delete history, or kill broad process groups. Do not infer VPN,
account-isolation, restoration, WSL2 or general-container acceptance. Publish only
implementation, tests, usage and redacted evidence after checks and independent
review pass; no merge, tag or force-push.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Authorized run | Reconciled running A/B and sufficient window | Deterministic machine-readable check results | Any failed predicate prevents PASS |
| Admission failure | Access denied, drift, missing evidence or unsupported target | BLOCKED with redacted reason | No repair or join |
| Non-TTY join | Actual process with pipes | Exit 1 and TTY refusal, no shell | Unexpected entry fails verification |
| Session deadline | Created shell fails to respond | Bounded failure and session-specific closure | Never signal unrelated shells |

</intent-contract>

## Code Map

- `_bmad-output/linux-context/cli.py`: `LIST_FORMAT`, `INSPECT_FORMAT`, `select`,
  `identity_supported`, `main`; invoke the process entry point, not in-process mocks.
- `_bmad-output/linux-context/test_cli.py`: 19 existing offline stdlib tests with
  process/TTY boundaries mocked; retain Docker independence and add demonstrated regressions.
- `_bmad-output/linux-context/README.md`: current commands and historical proposed
  manual checks; add reusable harness usage and explicit authorization prerequisites.
- `_bmad-output/implementation-artifacts/spec-linux-context-cli.md`: completed
  historical spec, read-only; do not redispatch or rewrite.
- Completion worktree `_bmad-output/linux-docker-trial/ld01-gate5-completion.md`:
  read-only historical closeout and private non-credential evidence locators.

## Tasks & Acceptance

**Execution:**
- [x] `_bmad-output/linux-context/smoke.py` — implement bounded stdlib PTY/process
  verification, with private raw observations and deterministic redacted checks.
- [x] `_bmad-output/linux-context/cli.py`, `test_cli.py` — patch only demonstrated
  defects and add focused offline regressions, if needed.
- [x] `_bmad-output/linux-context/README.md` — document authorized harness invocation.
- [x] This spec — record exact PASS/FAIL/BLOCKED, review dispositions and limits.

**Acceptance Criteria:**
- Given freshly reconciled running eligible A/B, when actual list/status run, then
  real Docker rendering reports exactly A/B with supported daily identities.
- Given controlled PTYs, when two actual A joins and one B join coexist, then UID
  and GID are 1001, HOME is /home/session, cwd is /project, A PIDs differ, A home,
  project and network identities match, B home/network differ, and host/A/B project
  identity matches the expected shared bind.
- Given both A sessions, when one exits, then the other remains usable; when a
  joined shell exits 37, then its actual CLI process returns 37.
- Given non-TTY input/output, when join runs, then it refuses before shell entry.
- Given any subprocess/session, when its deadline elapses, then verification ends
  boundedly without affecting pre-existing shells or extending authorization.
- Given implementation and any demonstrated fixes, when offline tests, affected
  live checks and independent review finish, then exact results and remaining limits
  are recorded before task-scoped publication.

## Spec Change Log

## Review Triage Log

### 2026-10-27 — Independent review and patch verification

Four synchronous independent reviewers used separate `chore/ld01-smoke-review-*`
branches and `/tmp/opencode/ld01-smoke-review-*` worktrees, at the recorded starting
revision. No reviewer accessed Docker or private evidence. Final focused independent
patch verification PASS; supplied suite 33/33 PASS, plus one reviewer-only offline
remote-journal-checker test (34/34 including that check).

Verdicts: 19 observations — high 0, medium 9, low 0, false 10, maybe-false 0.
Each original observation is recorded separately below; overlapping roots share patches.

| ID | Verdict | Route | Evidence/disposition |
|---|---|---|---|
| Blind 1 | false | reject | Admission already uses both `--noprofile --norc` before `-ic`; the review's profile-reading claim omits the actual flags. No startup profile is read. |
| Blind 2 | false | reject | Replacement under the same name is hypothetical under the user's exclusive LD01 ownership and no-lifecycle scope. Fresh CLI inspection uses the full ID; pre/post configuration and identities matched. No replacement or demonstrated defect. |
| Blind 3 | medium | patch | Unrequested client exit/nonzero cleanup was incorrectly called clean. Closure now reports unconfirmed; focused regression passes. |
| Blind 4 | medium | patch | Cutoff after admission retained FAIL. Blocked handler now explicitly sets BLOCKED; regression exercises cutoff during verification. |
| Blind 5 | medium | patch | Non-object journal mapping raised AttributeError. Root/containers/journals objects are validated; JSON BLOCKED regressions pass. |
| Blind 6 | medium | patch | Central verify predicates lacked offline regression protection. Passing orchestration and duplicate A PID rejection added and pass. Live checks still establish acceptance independently. |
| Edge 1 | medium | patch | Same malformed journal mapping defect as Blind 5; fixed by that validation and regression. |
| Gap 1 | medium | patch | Process-drift guard lacked regression. Matching metadata plus changed process snapshot now blocks before exec in a passing focused test. |
| Gap 2 | medium | patch | Same uncovered verify predicate root as Blind 6; real predicates now exercised with passing/duplicate-PID synthetic evidence. |
| Intent scope/history | false | reject | Descriptive alignment: new spec, unchanged completed historical spec/CLI; no defect alleged. |
| Intent actual CLI surface | false | reject | Descriptive alignment: actual subprocess/PTY execution, subsequently verified live. |
| Intent admission | false | reject | Descriptive alignment on explicit comparisons; parent separately reconciled saved original identities and restart-related residuals. |
| Intent main predicates | false | reject | Descriptive alignment; actual live run and patched rerun passed every predicate. |
| Intent operator prerequisites | false | reject | Correct operator/harness split, not a requirement to automate authorization or branch ownership. Clean start/exclusive assignment/window are recorded. |
| Intent cutoff outcome | medium | patch | Same verified FAIL/BLOCKED classification root as Blind 4; explicit handler and regression pass. |
| Intent non-TTY proof | false | reject | Exact actual refusal/status plus inspected CLI control flow establishes refusal before exec; no mock substitutes for this live check. |
| Intent closure | false | reject | Descriptive remote-client limit is explicitly disclosed; normal owned exits verified and final process inventory equals prejoin inventory. Blind 3 separately patched the actual closure classification defect. |
| Intent completion evidence | false | reject | Frozen pre-closeout diff intentionally lacked final results. This log supplies completed checks/review and distinguishes publication blocker. |
| Parent live-journal audit | medium | patch | Local archives/absent paths cannot establish live retained journals. Required remote journal mapping now checks exact retained directory set, hashes and absent active markers in admitted A full ID. Offline mismatch test, independent checker negatives and patched live admission PASS. |

No deferred findings. Six patch roots: closure, outcome classification, malformed
mapping validation, verify predicates, process-drift coverage and live journal
binding. Patched entry severities: six medium, zero high/low. Follow-up review
recommendation false after the focused independent verification: no specific
unverified runtime risk remains in the authorized happy-path scope. Failure-path
timeouts remain synthetic; unconfirmed remote closure remains explicitly limited.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-context -p 'test_*.py'`
  — existing and focused regression tests pass without Docker.
- Authorized `smoke.py` invocation — actual process/PTY acceptance passes in the
  original window, after metadata/read-only admission; no mocked live acceptance.
- `git diff --check` and independent review — pass before publication.

## Ownership and canonical revisions

Owner: this unattended OpenCode continuation, exclusively assigned by the user.
Worktree: `/home/rat/Git/termux-vm/termux-vm-linux-context-cli`.
Clean starting HEAD and origin task branch:
`85a0d47bd09ca7a4ae296640e22ee5c34da7aaf7`.
Local origin/main reference: `31d41e256cc8d25c92490fb54ca64ed179717415`.
`git add --refresh -- .` succeeded; initial porcelain status was empty.
No other listed worktree owns this branch. Historical reviewer worktrees are
prunable records and were left untouched.

## Execution handoff

Implementation delegate exclusively uses `/tmp/opencode/linux-context-smoke-builder`
on `feat/linux-context-smoke-builder`; parent owns integration into the designated
task worktree. Read this spec at its original absolute path; do not edit that copy
or other worktrees. Implement source/tests/README only in the delegate worktree.
Do not commit or publish. Parent performs live checks, evidence reconciliation and
review after return; delegate must not contact Docker or private evidence.
Return promptly after offline verification so the parent can use the fixed window.

The one recorded live window is 2026-10-27T12:51:27.080191+00:00 through
2026-10-27T13:11:27.080191+00:00; no new checks at or after
2026-10-27T13:06:27.080191+00:00. Private evidence directory:
`/tmp/opencode/ld01-cli-smoke-20261027T125127080191Z`.
Metadata access succeeded. Saved original container IDs, images, user, workdir,
privileged mode, network mode and mounts match both running containers after
normalizing mount order. Initial B mount-array inequality was order-only, not drift.
Both retained A journals match all four recorded file hashes with no active marker.
Fresh process/zombie reconciliation and home/project/network checks remain required
before joins. Harness accepts the existing fixed window and private evidence path;
it must not silently create a replacement authorization window. Use explicit
admission inputs/expected identities rather than accepting current state as baseline.

## Auto Run Result

**Status: BLOCKED — publication scope, not live CLI verification.**

Implemented `smoke.py` (stdlib real subprocess/PTY smoke and guarded admission),
`test_smoke.py` (14 offline boundary/predicate tests), and README usage/admission
contract. CLI and its 19 existing tests are unchanged: no CLI defect was demonstrated.

### Exact verification outcomes

| Check | Result | Evidence |
|---|---|---|
| Clean committed starting tree/branch | PASS | Canonical revisions and refresh above |
| Normal Docker metadata access | PASS | Bounded version projection, no permission activation |
| Saved A/B configuration | PASS | Original IDs/images/user/workdir/privilege/network mode/mounts match; mount order normalized |
| Current residuals | PASS | Only original sleep process in each container; zero zombies/OpenVPN processes; authorized restart explains historical zombie absence |
| Retained A journals | PASS | Both directories, all four recorded hashes each, absent active markers; no VPN baseline adoption |
| First actual CLI smoke | PASS | 12/12 checks, before review patches |
| Patched actual CLI smoke | PASS | 12/12 checks, same original window, after live-journal binding/closure/outcome patches |
| Final preservation | PASS | Completed 2026-10-27T13:04:10.103923+00:00; original process inventory, journals, metadata and home/project/network identities unchanged |
| Existing plus harness offline suite | PASS | Exact prescribed unittest command, 33 tests |
| Independent review | PASS | Four layers plus focused final independent patch verification above |
| Whitespace | PASS | `git diff --check`, `git diff --cached --check` |
| Task-scoped PR | BLOCKED | Pre-existing unrelated unmerged ancestor described below |

Both smoke runs exercised actual Docker list/status template rendering with exact
A/B results, actual simultaneous A/A/B PTYs, UID/GID 1001, HOME `/home/session`, cwd
`/project`, distinct A PIDs, shared A identities, distinct B home/network, matching
host/A/B shared project identity, exit 37 propagation, remaining A usability and
non-TTY refusal. All created sessions exited normally; postcheck found no survivors.
No environment repair, lifecycle, VPN, probe, shared-project write or cleanup retry.

The fixed window started 2026-10-27T12:51:27.080191+00:00, check-start cutoff
13:06:27.080191+00:00, expiry 13:11:27.080191+00:00. All live work finished by
13:04:10.103923+00:00. No new live checks are needed or authorized after closeout.
Private observations remain only in the mode-0700 evidence directory recorded
above, with mode-0600 files. Raw IDs, PIDs, mount sources, namespace identifiers and
journal contents/hashes are not published in this continuation.

### Concrete publication blocker

Fresh `git fetch origin` confirms main is
`31d41e256cc8d25c92490fb54ca64ed179717415`. The supplied published task branch
contains unrelated ancestor `f04c0716a8b06cec3136f7f7d07bf9145d964162`
(`chore(trial): prepare LD01 Gate 4 private inputs`) in addition to the existing
CLI commit. Its two Gate 4 documentation files (437 lines) appear in the PR diff
against main. A PR containing only the existing CLI and this continuation cannot
be opened from this branch without changing that dependency situation. Force-push,
unrelated deletion, and expanding the task to publish Gate 4 are not authorized.
Preserve task-scoped verified work with a normal commit/push; do not create a
mis-scoped PR or mark this increment complete. A separately authorized integration
decision is required; no merge/tag/history rewrite is performed here.

Limits: CLI behavior only. Timeout/error paths use offline regressions, not live
fault injection; abnormal remote-shell closure can only be reported unconfirmed.
No VPN readiness, account isolation, restoration audit, WSL2 or arbitrary-container
support claim. Historical evidence and completed spec remain untouched.
