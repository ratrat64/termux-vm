---
title: 'Bound capture-accounting convergence before shutdown'
type: 'bugfix'
created: '2026-10-21'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
baseline_commit: '243d1a9fa61e2ee47f8e3a9676efa7dce5bb9f9f'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Implement the approved capture-accounting shutdown proposal offline. Enable
immediate delivery and give the existing privileged capture worker a bounded
identity-checked SIGUSR1 accounting-convergence phase before requested SIGINT.
Use fresh complete repeated equal positive processed/received counts with zero
drops as a stop hint only. Bind success to separate terminal statistics and retain
exact parsed/captured/received equality, zero kernel/interface drops, interval
canaries and underlay checks. Convergence timeout, missing statistics, expiry,
premature exit or forced retirement remains failure. Preserve fixed expiry,
retirement budget, detached cleanup authority, locks, interfaces and capture scope.

The user approved implementation and verification and explicitly confirmed using
the existing dirty worktree while preserving owner/result updates and untracked
files. Change only `controlled-vpn/trial.py`, `test_trial.py` and implementation
documentation. No Docker/GCP/VPN operation, real capture, container start, scratch
recreation, cleanup retry, live attempt, reference adoption, commit or push.
Historical verdicts and private evidence remain unchanged. The historical four
packets remain unidentified; synthetic verification cannot establish their cause.

</frozen-after-approval>

## Implementation Notes

- No unresolved intent gaps or irreversible actions; the change is confined to
  two existing source/test files and documentation. The small internal change uses
  the oneshot route with an independent review after verification.
- Reuse `CAPTURE.checked_signal`, `remaining`, `retire`, `capture_proof` and the
  existing ordinary-user `DetachedCaptureTests.capture_worker` harness. All normal
  and detached callers already share this path; no fixture/server change.
- Installed binary inspection shows SIGUSR1 progress uses a single line:
  `tcpdump: N packets captured, N packets received by filter, N packets dropped by kernel`.
  SIGINT completion uses separate lines. Handle singular counts and optional
  interface-drop accounting without treating progress as terminal proof.
- Read progress through a read-only reopen of the wrapper's own `/proc/self/fd/2`,
  checking matching regular-file identity with stderr. Use positional bounded reads
  so output offsets are undisturbed. This introduces no arbitrary privileged file
  path input and avoids pipes or background reader threads.
- Use at most two seconds for convergence, retaining seven seconds for existing
  interrupt/kill retirement inside the caller's ten-second wait. Check both UTC
  and monotonic expiry. Require two identical fresh good samples separated by a
  short polling interval; a partial/missing sample cannot be reused as fresh.
- A wrapper-generated terminal marker before SIGINT separates terminal counters
  from progress. New successful receipts must attest convergence. Legacy saved
  evidence remains readable by direct proof replay, but is not a new successful
  stop contract or a cleanup-retry authorization.
- Verification targets: delayed tails; late final mismatch; missing/partial/stale
  samples; timeout/expiry; positive progress with terminal mismatch/drops/missing
  terminal counters; detached controller-loss cleanup; existing identity/gate/
  clock/forced-stop guards; historical-shaped 176/180/0 remains rejected. Use only
  disposable ordinary-user workers and synthetic evidence.

### Completed offline implementation

- `trial.py` explicitly requests `--immediate-mode`. The existing worker samples
  fresh SIGUSR1 accounting through its own regular stderr descriptor, preserves a
  positional-read cursor, and permits at most two seconds of convergence while
  retaining seven seconds for retirement. Two identical good complete samples
  are required; unanswered samples are never followed by another request.
- Root authority, exact PID/start/command checks, private stop markers, gate,
  absolute/monotonic expiry and detached-supervisor ownership remain shared.
  Extra/partial sample output, drops or timeout prevent successful completion.
- A wrapper terminal marker separates final accounting from progress; the new
  stop contract requires convergence attestation and one complete terminal block.
  Final parsed/captured/received equality, positive canaries, zero drops and
  underlay predicates remain mandatory. An in-flight tail after a progress sample
  still fails terminal proof. No claim of guaranteed future live success is made.
- `test_trial.py` extends the existing disposable-worker harness. It covers delayed
  tails, late final mismatch, missing final statistics, fresh-response timing and
  fragmentation, stale/mixed/late-partial samples, kernel/interface drops, optional
  zero interface drops, insufficient reserve and expiry during requested sampling.
  Existing controller-loss, identity/specification, gate and forced-stop tests pass.

## Review Triage Log

Independent blind review ran read-only using branch `chore/capture-accounting-review`
and worktree `/tmp/opencode/termux-vm-capture-accounting-review`. The oneshot workflow
uses this one review layer. Every finding was verified and patched; none deferred.
The reviewer then rechecked each correction and found no remaining introduced
correctness issue in that focused check.

| ID | Verdict / disposition | Evidence and correction |
|---|---|---|
| R1 | medium / patched | A 300 ms per-response cutoff could fail a healthy delayed response within the two-second budget. Outstanding requests now use the remaining total budget; the 350 ms synthetic response passes. |
| R2 | medium / patched | Extracting a valid line could ignore trailing incomplete bytes. Full-response matching plus a retained positional cursor rejects mixed and late-partial accounting; valid split writes pass. |
| R3 | medium / patched verification gap | Progress kernel/interface drops and optional interface accounting were untested. Added negative progress/terminal drop cases and a positive explicit-zero case. |
| R4 | medium / patched verification gap | Short-expiry tests skipped convergence. Added wall-clock and monotonic expiry after sampling begins, asserting unsuccessful completion, bounded retirement and no cleanup PASS. |

## Verification

- Pre-change focused capture checks: **20 PASS in 17.720 seconds**.
- Initial revised focused checks: **25 PASS in 25.281 seconds**; initial full
  suite **122 PASS in 46.555 seconds**. These precede review corrections.
- Corrected focused checks: **28 PASS in 34.454 seconds**. Final full command:
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p 'test_*.py'`
  — **124 PASS in 56.211 seconds, no skips**. The reviewer independently reran all
  **25 DetachedCaptureTests PASS** against final source.
- Bash syntax, CLI help and `git diff --check` PASS. Disabling convergence in
  memory makes the delayed-tail regression fail as expected; no mutation persists.
- Actual saved attempt replay, with external-command execution forbidden, still
  parses 176 headers and rejects 176/180/0 with `capture loss/count mismatch`.
  Saved baseline FAIL / cleanup FAIL and absent `cleaned.json` remain intact.
- No Docker/GCP/VPN operation, real packet capture, container start, scratch
  recreation, cleanup retry, live attempt, adoption, commit or push occurred.
  Private evidence and the pre-existing owner/result updates and bytecode are
  preserved. The original earlier baseline FAIL / cleanup PASS is unchanged.
- Offline implementation/review is complete. Future source approval, admission,
  stopped-container/scratch decisions and live execution remain separate gates.
