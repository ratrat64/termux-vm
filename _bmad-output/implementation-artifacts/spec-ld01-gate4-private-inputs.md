---
title: 'LD01 Gate 4 offline private baseline inputs'
type: 'chore'
created: '2026-10-21'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
deferred: []
baseline_commit: '111162f9ec05f767e01879449ebcef64725e992a'
baseline_revision: '111162f9ec05f767e01879449ebcef64725e992a'
---

<intent-contract>

## Intent

**Problem:** Gate 3's explicitly accepted inspected reference needs new private
controller inputs. Historical baseline inputs cannot substitute for that reference.

**Approach:** Validate the pinned acceptance and saved observations, construct one
new private sibling baseline, then verify it using current input consumers with
external execution disabled. Publish only this spec and a redacted completion handoff.

## Boundaries & Constraints

**Always:** Owner OpenCode; branch `chore/ld01-gate4-private-inputs`; worktree
`/home/rat/Git/termux-vm-ld01-gate4-private-inputs`; exact base above. Preserve the
diagnostic and historical worktrees and their tracked, untracked and ignored files.
Bind preparation to the user's exact accepted summary and final explicit-residual
validation. Private directory 0700, files 0600, exclusive creation only. Keep full
inspection/configuration/endpoints, network peers/IPAM, volumes, host/container
network state, observation times, acceptance, hashes and limitations outside Git.
Use the controller's exact zombie/journal schema; extra journal source/intent hashes
and process/start context belong in separate provenance. The empty replacement
scratch is new data, not recovered history. Set reconciliation-complete metadata
only after integrity, acceptance and saved-data validation succeed.

**Never:** Modify source, tests, owner handoffs, completed specs or historical
results. No Docker/GCP/VPN operation, container exec/start/restart, scratch change,
cleanup retry, capture, credentials/profiles, live probe, live controller, sudo,
gcloud or resource helper. Do not execute the old preparation script. No execution
authorization, execution window or attempt directory. Do not claim freshness,
live admission, B firewall equality or repaired historical evidence. Halt blocked
on changed/incomplete evidence or missing schema facts; retain partial outputs.
User authorizes committing/pushing only the reviewed two redacted task artifacts
on this branch, without force; no PR, merge, tag or other branch push.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Accepted evidence | Pinned summary, exact acceptance and completed explicit Gate 3 validation | New private inputs preserve exact accepted inventory and original observation times | No error expected |
| Changed/incomplete evidence | Digest mismatch, broken provenance or unavailable schema value | No completed reconciliation claim | Halt blocked; preserve existing and partial material |
| Offline boundary | Source import or consumer attempts external execution | Immediate failure | Stop; never relax the trap |

</intent-contract>

## Code Map

- `_bmad-output/linux-docker-trial/controlled-vpn/trial.py:81` — read-only
  `diagnostic_inputs()` checks absolute durable private inputs and residual shape.
- Same file, `:243–272` — `mounts()` and saved-data `reconcile()` validate original
  identity, image, runtime configuration, capabilities, attachments and mounts.
- Same file, `:1101–1135`, `:1164–1229` — exact residual contract; network peer/IPAM,
  volume labels, full retained configuration/endpoints and veth checks. Read/reuse
  pure predicates only; never invoke `Trial.preflight` or live `check_idle_a`.
- `_bmad-output/linux-docker-trial/prepare-baseline-inputs.py` — read-only format
  reference; its historical inventory/assessment schema and zombie assumption are
  unsuitable for unchanged execution.
- Accepted private Gate 3 summary/acceptance/final result link Gate 2 recovery,
  post-start inspection, retention continuation and saved explicit idle validation.
  Original post-start failure remains preserved; continuation supplies retention.
- Private locators (metadata only): accepted summary in
  `ld01-gate3-retention-continuation-20261021T132743138902Z/inspection-summary.json`
  under the private state parent, SHA256
  `c274e4821065d2cd178d31d9631705f30c67982696425576ff380d893d6ea465`;
  acceptance and explicit idle/result receipts in
  `ld01-gate3-accepted-validation-20261021T133326030075Z/`.
  `/tmp/opencode/ld01-gate4-offline.py` is the planning-stage offline checker:
  its evidence audit passed; extend it for this one-off preparation and read-back
  validation, retaining its source privately. Never execute saved historical drivers.
- Offline recovery/admission runbook, owner handoff, later attempt results and
  completed capture-accounting spec are read-only context, never resumed.

## Tasks & Acceptance

**Execution:**
- [x] New private sibling under `/home/rat/.local/state/termux-vm-private/` — build
  resources/image/baseline/full retained metadata/residuals and supporting metadata,
  acceptance/observation provenance, content hashes and offline validation results.
- [x] This spec — record planning, verification and workflow-review state, retaining intent.
- [x] `_bmad-output/linux-docker-trial/ld01-gate4-private-inputs.md` — concise redacted
  handoff with outcomes, private locators and remaining live gates.

**Acceptance Criteria:**
- Given the user-pinned summary, when all linked saved evidence is checked, then
  hashes, acceptance and final explicit residual validation agree before construction.
- Given the accepted observations, when new files are read by `diagnostic_inputs()`
  and `reconcile()` with external execution trapped, then schemas, original IDs,
  image/configuration/mounts, exact peers/IPAM, residuals, permissions and provenance
  pass; extra journal context stays outside `residuals.json`.
- Given completed saved-data validation, when reconciliation metadata is published,
  then its scope is offline accepted evidence only, with original timestamps and
  all differences/limitations preserved; no live authority or freshness is implied.
- Given completed review, when publication runs, then only the two redacted Gate 4
  artifacts are committed and this task branch is pushed to origin without force.

## Spec Change Log

- 2026-10-21 — OpenCode resumed on the exact pinned base/task worktree; the
  frontmatter `context:` list is empty. Extended the one-off offline checker only;
  source, tests, owner handoffs, completed specs and historical results are intact.
- **BLOCKED before construction:** accepted saved host-link metadata lacks
  `linkinfo.info_kind`. Its saved command uses `ip -j link show`, without `-d`.
  The current controller's pure veth predicate explicitly requires
  `linkinfo.info_kind == "veth"`. Saved interface names, reciprocal indices and
  Ethernet link type cannot supply that missing schema fact. No value was inferred,
  no predicate relaxed and no new observation authorized or collected.
- The partial checker remains at `/tmp/opencode/ld01-gate4-offline.py` outside Git.
  No new private baseline directory, completion/adoption metadata, input-paths
  record, execution authorization/window or attempt directory was created.
- Execution tasks and construction/read-back acceptance remain incomplete. The
  redacted blocked handoff was written; publication is not complete. Resume only
  after the missing fact has an explicitly approved evidence/acceptance disposition.

### Scope correction and completed implementation — supersedes the initial blocker

- The coordinating agent requested a read-only scope check, then directed completion
  with only the introduced checker overreach corrected. `trial.py:81–95` and
  `:243–272` do not consume `linkinfo.info_kind`; neither does a required baseline
  schema. `:1222–1228` obtains that fact from fresh detailed live queries and stores
  runtime identity. It is a Gate 5 admission requirement, not a Gate 4 input field.
  The initial blocker above was an implementation scope error, not an evidence gap.
- Removed only the checker's added detailed-link-kind requirement. Kept current
  `diagnostic_inputs()` and saved-data `reconcile()`, plus the exact network
  identity/configuration/ownership/peer/IPAM, volume-label and full retained
  configuration/endpoint/mount predicates from `:1173–1182` and `:1216–1220`.
  Saved peer names, reciprocal indices and endpoint comparisons remain checked.
- Created exactly one new exclusive private sibling:
  `/home/rat/.local/state/termux-vm-private/ld01-gate4-private-inputs-20261021T140731404796Z/`.
  Its 19 files include required inputs, complete saved container/host/network/volume
  and retention metadata, provenance, hashes, validation and runnable source.
  Saved `host-links.json` is byte-for-byte unchanged, with no fabricated `linkinfo`.
- Original observations, acceptance, differences and limitations remain private and
  exact. Preparation time is distinct from original observation times. The empty
  scratch is explicitly new replacement data, not recovered history. Completion
  flags were written only after acceptance, integrity, saved-data validation and
  consumer read-back succeeded. Detailed live veth-kind validation is explicitly
  **UNVERIFIED — fresh Gate 5 admission required** in provenance and receipts.
- Added read-only `--verify-existing PATH` to the same checker and retained the
  exact runnable source as `prepare-offline.py` inside the new directory. This mode
  denies filesystem writes/mutations as well as process/network execution, re-audits
  evidence, verifies every output/hash/permission and re-exercises consumers and
  negative checks without constructing another directory.
- The coordinating agent's implementation handoff reserves final workflow review/publication for the
  parent: **do not stage, commit or push**. Implementation is complete; status is
  `in-review`. The intent-contract is unchanged and no independent review is claimed.

## Review Triage Log

**Current disposition:** all four independent workflow layers completed. Offline
Gate 4 inputs and retained-source read-only validation PASS; no construction
blocker remains. Earlier blocking/pending entries below are chronological history
superseded by the scope correction and final review. Gate 5 is NOT RUN.

- Local implementation/schema inspection identified the missing saved veth-kind
  fact before any output construction. Disposition: **blocking evidence gap**,
  following the existing halt rule; not a source change or historical repair.
- The initial command-binding check compared raw route-array order to the saved
  canonical representation. Inspection confirmed the saved values use the current
  `canonical()` transformation; the checker now applies that same pure predicate
  when binding routing observations to command output. Accepted files are unchanged.
- Completion workflow review and publication were not reached because the
  construction/read-back acceptance criteria are unsatisfied. No independent
  review is claimed.

- **Correction to the earlier blocking disposition:** the missing detailed veth-kind
  field is not required for offline input construction. Retain it as an explicit
  live-verification limitation, rather than a Gate 4 blocker. No production source,
  accepted evidence or required offline predicate was changed.
- A direct endpoint-drift negative test initially mutated both sides through an
  in-memory shared dictionary. The test now independently copies the corrupted
  input, matching separately persisted files; the unchanged endpoint predicate
  rejects it. All 31 final negative cases pass. No baseline had yet been created
  when this test-harness issue was found and corrected.
- Parent workflow review and publication remain pending by explicit instruction;
  the local checks below establish implementation verification only.

### 2026-10-21 — Review pass

- verdicts: 11 findings/observations — high 0, medium 0, low 2, false 9,
  maybe-false 0. Blind layer: five findings; edge-case layer: none;
  verification-gap layer: no gaps; intent auditor: six surface observations.
- All reviewers operated read-only in separate task worktrees. Reports contain
  redacted conclusions only. No private inputs/evidence were published for review.
- findings:
  - `[low]` `[reject]` B1, supplied summary digest in spec — this is the user's
    already supplied reference pin, not private file contents or generated input
    hashes. Removing it is a spec-only editorial change; generated digests stay
    private. No new evidence content is exposed.
  - `[false]` `[reject]` B2, implementation must be added to Git — the invocation
    expressly limits repository outputs to two redacted documents, with no new
    framework/runtime automation. The one-off preparation/check source is retained
    privately and independently runnable; publishing it would violate that scope.
  - `[false]` `[reject]` B3, missing independently pinned acceptance-record digests —
    no such trusted digests were supplied or required. The exact user-pinned summary,
    named acceptance/final-validation receipts, explicit expected residuals, saved
    command results and prior-inspection manifest agree. Original receipt bytes are
    hashed and preserved; read-only verification confirms they remain unchanged.
  - `[false]` `[reject]` B4, completion before validation — before either completion
    flag, the checker has already passed evidence/acceptance validation, schema and
    saved-data reconciliation, consumer read-back, permissions and negative checks.
    Its subsequent complete-set verification checks the newly published records;
    that final check also passed. No failed/partial baseline carries this result.
  - `[low]` `[reject]` B5, obsolete blocked assertions in chronological spec log —
    the correction explicitly supersedes the initial blocker. The current-disposition
    heading and final result give one authoritative status without rewriting history;
    no implementation or evidence correction is needed.
  - `[false]` `[reject]` I1, public/private verification surface — deliberately split
    by the user. The intent auditor independently ran retained-source read-only
    validation successfully; the public diff contains only the requested documents.
  - `[false]` `[reject]` I2, no consumer implementation/test-file changes in diff —
    expressly required. Existing consumers and saved-data predicates are reused
    against the actual private outputs; source hashes and receipts remain private.
  - `[false]` `[reject]` I3, aggregate negatives differ from live-admission tests —
    documented as in-memory negatives, including both exact-data preservation and
    direct consumer drift rejection. No live-admission testing is claimed.
  - `[false]` `[reject]` I4, detailed live veth-kind check absent — source confirms it
    is fresh runtime admission, not a required baseline-schema field. Exact saved
    observations remain unchanged; Gate 5 must perform the full live predicate.
  - `[false]` `[reject]` I5, publication pending at review — correct intermediate
    sequencing, not a failed implementation. Finalization commits only reviewed
    documents, then the separately authorized task-branch push follows. Its actual
    outcome is reported to the user rather than preclaimed in this document.
  - `[false]` `[reject]` I6, read-back cannot reconstruct every past operation —
    no such historical omniscience is claimed. Source evidence/content hashes,
    task-only Git changes, recorded original status and guarded execution support
    this task's preservation claims; live freshness remains expressly unclaimed.

## Verification

### Initial run history — superseded by completed verification below

- Fresh planning-check replay: **435 saved JSON files / 1,364 checks PASS**,
  including the summary pin, prior-inspection manifest, acceptance, original failed
  inspection, retention continuation and final explicit-residual validation.
- Extended checker `python3 /tmp/opencode/ld01-gate4-offline.py --check` repeats
  that successful evidence audit, then **fails closed on missing saved veth kind**.
  Process/network audit traps were installed before controller import; `run`,
  `inside`, `remote` and port checks were denied. No external/runtime command ran.
- Construction, generated-input consumer read-back, permission checks and runnable
  corruption/trap negative checks were **NOT RUN**: the evidence gap stops the
  checker before those stages. Their implementation in the partial checker is
  unverified and must not be treated as completed proof.
- Final task-artifact diff/redaction and `git diff --check` PASS. Only this spec
  and the redacted blocked handoff are task changes; no files were staged,
  committed or pushed. Publication remains incomplete at the blocking evidence gap.

- One-off offline preparation/validation under `/tmp/opencode/`, retained privately
  with its source hash; imports source with process/network audit traps and denied
  `run`, `inside`, `remote` and port checks. Re-read all outputs and source evidence;
  compare generated schemas with saved observations and exercise existing consumers.
  Include runnable negative checks using in-memory corruptions only: integrity and
  schema mismatches must fail closed; process/network attempts must hit the trap.
- Evidence-only planning check: 435 saved JSON files checked; accepted summary pin,
  full prior-inspection hash manifest, acceptance, explicit idle receipt and Gate 2/3
  provenance PASS. Initial checker assumed an inspection array where the saved
  final A observation is an object; corrected after inspecting its actual schema.
  No evidence was changed, and no private output directory had been created.
- Inspect final Git diff/status/history and redaction before staging exactly two
  files; `git diff --check` must pass. Record publication outcome separately.
- Historical **124 offline tests PASS** is not rerun or presented as new proof.
  Earlier **baseline FAIL / cleanup PASS** and later **baseline FAIL / cleanup FAIL**
  remain unchanged. **Final-source live validation: NOT RUN.** Gate 5 requires
  separate final-source approval, fresh admission and explicit live authorization.

### Completed construction and retained-source read-only revalidation

- `python3 /tmp/opencode/ld01-gate4-offline.py --check` — **PASS**: 435 saved JSON
  files / 1,364 evidence-audit checks, then saved-data schema/consumer predicates
  and 28 preconstruction in-memory negative checks. Original evidence and current
  controller source were rehashed before construction.
- `python3 /tmp/opencode/ld01-gate4-offline.py --prepare` — **PASS**, exactly one
  new private baseline, 19 files. Directory 0700; every file 0600, regular and
  nonsymlink; all outputs created exclusively. Current `diagnostic_inputs()` and
  saved-data `reconcile()` read-back, retained configuration/endpoints/mounts,
  exact network peers/IPAM and volume labels pass. Exact residual schema contains
  zero A zombies and two journals; extra source/intent/process context is separate.
- Reran the retained `prepare-offline.py` with `--verify-existing` and the exact
  directory above — **VERIFY_EXISTING_PASS**, read-only mode true, 19 outputs,
  unchanged source/adoption hashes, all source-evidence and output hashes checked.
  No second baseline or validation output was created. The source and adoption
  digests are retained privately in the validation receipt/manifest and run output.
- **31 in-memory negative checks PASS** during construction and revalidation:
  evidence integrity and acceptance binding; residual/runtime-schema corruption;
  identity/image/configuration/capability/mount/network/endpoint/peer/IPAM drift;
  altered observation time and fabricated host-link metadata; volume-label drift;
  missing residuals and non-private file/directory permissions; process/shell/socket/
  DNS audit traps and denied runtime helpers/port checks. Two additional read-only
  audit-event negative checks prove write-open and mkdir denial without filesystem
  mutation. Corruptions and permission substitutions are in memory only.
- Original summary/acceptance/final explicit validation, receipts, command start/end
  times, original inspection failure and retention continuation remain preserved.
  All accepted differences/limitations and new-empty-scratch disposition are private
  provenance. `post_reboot_reconciled` is true only for that offline accepted scope.
- **Runtime commands executed: 0.** No live preflight, idle check, Docker/GCP/VPN,
  capture, scratch change, credentials/profiles, authorization/window or attempt.
  Detailed live veth-kind validation and final-source live validation remain NOT RUN;
  freshness, live admission, B-firewall equality and historical repair are unclaimed.
- Only the new task spec and handoff are Git changes. Final unstaged diff/redaction,
  tracked `git diff --check` and explicit untracked-file whitespace checks PASS.
  No staging, commit, push or independent review; parent owns those remaining steps.

## Auto Run Result

Status: **done — offline preparation, verification and workflow review complete**.

- Created one new 0700 private sibling containing 19 exclusively created 0600 files:
  controller inputs, supporting saved metadata, acceptance/observation provenance,
  hashes, validation results and retained runnable preparation/check source.
- Repository changes: this new spec records intent, implementation, corrections,
  verification and review; the new Gate 4 handoff records the redacted outcome,
  private input locator and remaining live gates. Source/tests/historical documents
  are unchanged. The diagnostic worktree's existing untracked bytecode is preserved.
- Coordinating retained-source `--verify-existing` run: **PASS**, 435 source JSON
  files, 1,364 evidence-audit checks, 19 output files, 31 in-memory negative checks,
  two read-only mutation-guard negatives, zero runtime commands. The intent reviewer
  independently reran that same allowed read-only validation successfully.
- Matrix audit: accepted-evidence success, changed integrity/acceptance/schema
  rejection and external-execution denial all have executed runnable checks in the
  retained private checker. No repository test/source change was needed.
- Review: four layers completed; 11 findings/observations triaged above; patches
  applied 0 (high 0 / medium 0 / low 0), deferred 0, rejected 11 with individual
  reasons. Follow-up review recommendation: **false**; no unverified introduced
  implementation risk remains identified by this pass.
- Publication: user authorizes only these reviewed redacted artifacts on
  `chore/ld01-gate4-private-inputs`. Workflow finalization creates their scoped
  Conventional Commit; the post-finalization task-branch push outcome and full
  canonical commit identifier are returned in the final completion report.
- Residual limits: observations retain their original times, not runtime freshness;
  detailed live veth kind and full fresh admission remain required at Gate 5.
  B firewall equality, historical B8/lost-baseline equality and historical network
  ownership/cause remain unclaimed. New empty scratch is not recovered data.
  Historical verdicts are unchanged. **Final-source live validation: NOT RUN.**
  Gate 5 needs separate final-source approval, fresh admission and explicit live
  authorization. No execution authorization/window or attempt was created.
