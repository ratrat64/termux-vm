---
title: 'Prepare one baseline-only validation of the repaired DNS fixture'
type: 'chore'
created: '2026-10-20'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
baseline_commit: '2293a9943a570ff627e07856581d3fea2f2df85f'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Prepare the next baseline-only DNS-fixture validation offline in the existing
`fix/n2-baseline-diagnostic` worktree. Inspect source, handoffs and saved private
evidence; reuse the controller and admission/cleanup safeguards. Record the exact
read-only reconciliation, separate acceptance of changed references, and fresh
authorization required for one normal connect/check/off. Preserve historical
verdicts, work, resources and evidence. No Docker/GCP/VPN operation, adoption,
live approval/window, injection, reconnect, company material, package change,
resource recreation/deletion or publication is authorized. The eventual attempt
needs exclusive LD01 reuse, scoped capture, supervised abort/off, a new durable
private evidence directory and a fixed UTC window of at most 30 minutes with ten
minutes reserved for cleanup. Stop at the first unexpected failure; no automatic
retry. Identify only the smallest next Linux-alpha CLI slice after this blocker.

</frozen-after-approval>

## Implementation Notes

- Small documentation-only preparation: no offline intent gaps or irreversible
  operations; future runtime decisions remain explicit gates, not assumptions.
- Source at the full `baseline_commit` above; initial working tree clean. The
  supplied completed DNS-fix spec is context, not reopened implementation.
- Code map: `controlled-vpn/trial.py` `authorize`, `diagnostic_inputs`,
  `check_idle_a`, `preflight`, `baseline`, `execute`, `cleanup` and `watch` retain
  their existing contracts. `fixtures.py`/`setup-server.sh` supply the repaired
  authoritative backend. No runtime source changes are needed for preparation.
- `linux-docker-trial/baseline-dns-validation-readiness.md` will hold the gated
  runbook; append pointers to `baseline-diagnostic.md` and `task-owner.md` without
  replacing historical results. Keep generated private reports outside Git.
- Historical helper limits: `inspect-retained.py` names only three older VM
  tasks and continues after command errors; `prepare-baseline-inputs.py` consumes
  the old start-inventory schema and asserts zero zombies. Do not blindly rerun
  either for the next reconciliation/adoption. Reuse their metadata readers and
  the controller's schemas/checks under the separate gates.
- Fresh offline verification: 98 tests PASS in 27.544 seconds, no skips; Bash
  syntax and CLI help PASS. Saved-evidence checks PASS for nine input hashes,
  three provenance hashes, private modes, saved resource reconciliation, both
  shell DNS failures and the historical 92/92/0 capture proof. Runtime command
  functions were trapped during the saved-data check; no new live evidence.
- Independent documentation review completed read-only in separate branch/worktree
  `chore/baseline-validation-readiness-review` at the pinned source revision.
  Four operational gaps corrected in the runbook; no runtime implementation
  changes or new execution authority.
- Final source-diff check confirms controller, fixture, setup and preparation
  helpers unchanged from the published revision. Documentation whitespace checks
  pass. Preparation only is done; gates 1/2/3 remain unapproved and unexecuted.
  No finding deferred, no commit/push/PR, and no live verdict claimed.

## Review Triage Log

- R1 medium, patch: inspector's embedded `query()` also continues on errors.
  Require individually evaluated reads, not just supervision of whole readers;
  omit expected B permission-denied queries before execution.
- R2 medium, patch: controller preflight does not recheck all journal intent,
  watcher or historical VM-unit conditions. Require launch-time inactivity and
  preservation comparisons inside the fresh authorization/window; drift blocks.
- R3 medium, patch: operator abort lacked an actionable request/completion path.
  Document identity-checked controller-only SIGTERM once, existing supervisor
  handling and durable cleanup verdicts; no second worker or cleanup retry.
- R4 medium, patch: controller records some post-cleanup outputs without asserting
  absence and publishes cleaned PASS before final observations. Require explicitly
  authorized bounded final metadata audit, preservation/residual/deadline checks
  and separate failed/unverified conditions. Historical verdicts remain intact.
