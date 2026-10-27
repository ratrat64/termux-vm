---
title: 'Linux alpha: list, status and join existing LD01 contexts'
type: 'feature'
created: '2026-10-22'
status: 'done'
context: []
---

# Smallest proposed CLI slice

**Proposal only — not implementation or runtime authorization.** Gate 5 baseline,
cleanup and independent audit passed; the next step is a small user entry point
to existing contexts. No product source or tests are changed by this proposal.

## Goal and bounded surface

One Python-stdlib script, using the existing operator-selected Docker endpoint and
normal Docker access. No installation step, config file, context registry, dependency
or background service. Commands proposed for a later implementation:

```text
python3 _bmad-output/linux-context/cli.py list
python3 _bmad-output/linux-context/cli.py status NAME
python3 _bmad-output/linux-context/cli.py join NAME
```

`NAME` is the exact existing Docker container name, not a new alias. The initial
alpha is deliberately limited to LD01 context containers: names beginning
`tvm-share-ld01-` and all three existing ownership labels:
`task=linux-docker-sharing-trial`, `trial=ld01`,
`owner=opencode-linux-trial-preparation`. No claim of support for arbitrary Docker
containers or another backend. The operator retains normal Docker authority; this
CLI is not a security boundary or a restricted privilege broker.

## Behavior

All Docker metadata requests must project only required fields on the Docker side
with explicit `--format` output; do not retrieve full inspection JSON. For identity
checks, project user/workdir/privileged state and a boolean that HOME has exactly
the supported value, not the environment array. Require exactly one HOME entry;
duplicates or conflicting values are unsupported. Fetch only the three eligibility
label values, not arbitrary labels. Synthetic tests must assert these query boundaries.

- **`list`:** discover existing matching containers, including stopped ones, through
  metadata-only Docker queries. Print a deterministic name-sorted text table with
  `NAME` and `STATE`. An empty result is successful and prints an empty-state message.
  Do not print raw inspection objects, host mount paths, environment, IPs or credentials.
- **`status NAME`:** resolve an exact eligible name and inspect its current ID,
  ownership labels and state. Print only name/state and whether the configured daily
  identity is supported. It describes container state, not VPN readiness or a fresh
  restoration/audit verdict. An unknown or ineligible name fails without exec.
  `IDENTITY_SUPPORTED` means exactly user `1001:1001`, HOME `/home/session`, workdir
  `/project` and non-privileged mode. State is separate: a stopped container can
  have supported identity but cannot be joined. Reuse this same identity predicate
  in the join guard; do not maintain a second support definition.
- **`join NAME`:** inspect the exact target again and require all eligibility labels,
  `Config.User == "1001:1001"`, non-privileged mode, running and not paused/restarting/
  dead. Require its existing daily defaults `HOME=/home/session` and workdir `/project`;
  fail on an unsupported configuration rather than adapting or repairing it.
  Require an interactive stdin/stdout TTY. Use the inspected full container ID as
  the exec target, replacing the CLI process with a fresh ordinary shell:
  `docker exec -it --user 1001:1001 --workdir /project ID bash --noprofile --norc`.
  Use argument arrays, never shell interpolation. The shell inherits the validated
  container HOME; no host environment, profile or credential forwarding.
- Exiting one joined shell leaves the context and other shells running. Repeated
  joins share the selected container's home/project/network context, while A and B
  remain distinct contexts. Propagate the shell's exit status through process replacement.
- Exit 0 for successful metadata commands; exit 1 for unknown/ineligible context,
  pre-exec Docker access/daemon failure or unsupported join target/TTY. Invalid CLI usage
  exits 2 through `argparse`. Errors identify the failed operation without dumping
  raw Docker output or private inspection metadata during metadata/pre-exec checks.
  After process replacement, Docker owns its diagnostics and exit status; pass
  those through along with shell status. Do not promise Python normalization after
  exec or retry a failed exec. No implicit sudo, group switch,
  Docker context change, authentication-policy edit or automatic lifecycle action.

## Exclusions and preservation

No create/start/stop/restart/remove, network/mount/capability changes, package work,
VPN connect/off/reconnect, trial controller import, health probes, cleanup retry,
home copying or host integration. Do not turn the CLI into a new trial runner.
No default context or automatic fallback from a missing name. Joining starts only
the requested shell inside an existing running context.

The two post-Gate-5 zombies and prior journals retain their recorded disposition.
Implementing metadata commands offline does not accept new residuals or require a
new VPN campaign. Any later live smoke check requires explicit scoped access and
fresh appropriate resource/residual reconciliation; no such check is authorized here.

## Reuse and proposed implementation footprint

- `_bmad-output/linux-docker-trial/spot-check.py:43–86` — existing name/label and
  daily UID/home/workdir patterns; `:93–104` — distinct shells sharing A's context.
  Read as evidence only; the full spot-check mutates markers/TUN state and must not
  become the CLI implementation or be run to test this proposal.
- `_bmad-output/linux-docker-trial/controlled-vpn/trial.py:123–125,1055–1068` —
  argument-array Docker exec and shell flags. Do not import this trial module or
  reuse its privileged agents/lifecycle for the product CLI.
- New `_bmad-output/linux-context/cli.py` — one entry point and the smallest shared
  target-selection logic needed by these three commands; stdlib `argparse`, `json`,
  `subprocess` and `os.execvp` suffice.
- New `_bmad-output/linux-context/test_cli.py` — one focused stdlib test file with
  synthetic Docker metadata and mocked command/exec boundaries; no real daemon,
  container, credential, network or terminal session during offline tests.
- New `_bmad-output/linux-context/README.md` — the three commands, existing-access
  prerequisite and a short separately authorized manual two-shell try-it sequence.

## Acceptance and focused verification

1. Given eligible and unrelated synthetic containers, when `list` runs, then only
   eligible names appear in deterministic order, stopped states remain visible,
   and only metadata commands run; an empty set succeeds.
2. Given an exact eligible name, when `status NAME` runs, then state/support status
   is derived from its current inspection without exec or lifecycle mutation;
   stopped-but-supported and running-but-unsupported targets are distinct cases.
3. Given missing/unknown/ineligible names or daemon/access errors, when selection
   fails, then the command returns the specified error and never executes a shell.
4. Given an eligible running daily-identity target and TTY, when `join NAME` runs,
   then the exact non-root exec argv uses its inspected full ID and process replacement;
   default-root, privileged, unsupported defaults or inactive/non-TTY targets fail closed.
5. Given invalid usage or shell exit, when the command ends, then usage exit 2 and
   the replaced shell's exit status are preserved respectively; post-exec Docker
   errors remain Docker's own diagnostics/status.

Future focused command: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-context -p 'test_*.py'`.
Mock boundaries must assert absence of create/start/restart/remove, root exec,
sudo/group activation and VPN operations. A later explicit manual check may open
two shells to one context and one to its sibling, confirm UID/GID, HOME/workdir and
shared/distinct namespaces, and exit without lifecycle changes. Until separately
approved and implemented, all CLI commands/tests/manual checks are **NOT RUN**.

## Verification log

- 2026-10-22: User explicitly approved this spec for offline implementation; the
  proposal wording above is preserved as historical text. Runtime authorization
  remains absent. Only this task copy's workflow status and verification log change.
- Owner: implementation agent; branch `feat/linux-context-cli`; worktree
  `/home/rat/Git/termux-vm-linux-context-cli`; canonical base
  `f04c0716a8b06cec3136f7f7d07bf9145d964162`. Initial task worktree clean.
- Planning gate: read the full source spec, AGENTS.md, and cited name/label,
  identity, argv and shell-flag patterns as evidence only. Existing trial helpers
  perform excluded operations and are unsuitable for import. The three explicit
  product paths and five acceptance criteria are actionable and ready for development.
- User preservation constraint overrides workflow template rewriting: approved
  requirements remain verbatim. No commit, push, PR, merge or tag is authorized.
- Real-Docker/manual smoke testing: **NOT RUN** (separate authorization required).
- Implementation execution boundary: work only in the task worktree above. No real
  Docker queries/exec/joins, sudo/group activation, GCP/VPN, network probes, capture,
  credentials/profiles, scratch changes, cleanup retries, baseline adoption,
  execution authorization or live attempt. Do not execute historical scripts.
  Tests must mock subprocess/exec/TTY boundaries and fail closed on every unmocked
  subprocess path. Use synthetic metadata only. Run the exact focused unittest
  command above. README must provide future proposed smoke commands, never run them.
- 2026-10-22: Offline implementation completed in the designated worktree at the
  recorded canonical baseline (confirmed with `git rev-parse HEAD`). Added
  [CLI](../linux-context/cli.py), [synthetic tests](../linux-context/test_cli.py),
  and [usage/manual-check documentation](../linux-context/README.md). Approved
  requirements are preserved verbatim; only workflow status and this log changed.
- Verification: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-context -p 'test_*.py'`
  **PASS**, 16 tests. Covered sorted eligible/stopped discovery and empty results;
  exact-name/label/ID selection; independent state and shared identity reporting;
  unsupported identity/runtime/TTY refusal; sanitized Docker/metadata/exec failures;
  usage exits; fresh inspection, exact non-root ID-targeted exec argv and mocked
  process-replacement status/diagnostic pass-through. Query-shape assertions limit
  projected fields and labels, and pin the unique/exact HOME boolean template.
  Subprocess run/Popen, exec and TTY boundaries were mocked, with unexpected process
  requests failing closed. No Docker daemon or terminal session was used.
- `git diff --no-index --check` against `/dev/null` for each new product file:
  **PASS**. Git status shows only the supplied task spec and three new product
  files; no tracked baseline files changed. No commit, push or PR performed.
- Remaining verification: independent review and real-Docker/template/multi-shell
  smoke checks are **NOT RUN**. No subagent tool is available in this session.
  Live checks still require separate scoped authorization and fresh appropriate
  resource/residual reconciliation; offline tests do not prove runtime behavior or
  change the prior zombies/journals' disposition. Ready for review, not live use
  authorization.
- The preceding implementation-agent entry describes its own stage. Independent
  review is now complete through the orchestrating session, as recorded below.
  Workflow baseline and follow-up metadata are recorded in this log to preserve
  the user's constraint that only status and the verification log change.

### 2026-10-22 — Independent review and dispositions

Four context-free reviewers received the frozen diff, separate worktrees based on
`f04c0716a8b06cec3136f7f7d07bf9145d964162`, and explicit read-only/offline boundaries.
Reviewer worktrees and their exclusively assigned branches:

- Blind hunter: `/tmp/opencode/linux-context-cli-review-blind`,
  `chore/linux-context-cli-review-blind`.
- Edge-case hunter: `/tmp/opencode/linux-context-cli-review-edge`,
  `chore/linux-context-cli-review-edge`.
- Verification-gap reviewer: `/tmp/opencode/linux-context-cli-review-verification`,
  `chore/linux-context-cli-review-verification`.
- Intent auditor: `/tmp/opencode/linux-context-cli-review-intent`,
  `chore/linux-context-cli-review-intent`.

The parent populated snapshots before launching reviewers. Reviewers could read
source and run synthetic mocked checks only; no live queries, edits, private
evidence access or publication were authorized. The intent auditor independently
ran the prescribed initial suite: 16 tests passed.

Review triage: 15 observations — high 0, medium 6, low 2, false 7, maybe-false 0.
Each observation below has its own disposition; duplicated root causes share a fix.

| ID | Verdict | Route | Evidence and disposition |
| --- | --- | --- | --- |
| Blind 1 | low | patch | README said only Python 3, but required subparsers and capture_output need 3.7+. Corrected prerequisite to Python 3.7+. |
| Blind 2 | medium | patch | splitlines() splits raw U+0085 inside valid JSON identity strings. Changed to split("\\n"); synthetic regression covers U+0085/U+2028/U+2029 in user/workdir, status false and join rejection. |
| Blind 3 | false | reject | The proposed finer failure categories are not required by the approved contract. Existing errors identify list/status/join, exit 1, and suppress raw Docker output as required. No demonstrated incorrect status or disclosure. |
| Blind 4 | false | reject | An empty object has neither eligible name nor labels and is correctly excluded. The contract requires only eligible discovery, not rejection of every unrelated/incomplete dictionary. Invalid JSON/non-object records and invalid eligible states already fail. |
| Blind 5 | low | reject | A broken stdout pipe can raise BrokenPipeError; rejected as a rare output-consumer failure for this small LD01 table. Reliable handling includes buffered interpreter shutdown and is more than a direct correction; no lifecycle, privacy or join guard is affected. |
| Blind 6 | medium | patch | Prior regex assertions missed appended whole-object output. Independently pin complete permitted formats and assert disclosure mutations fail; subprocess argv assertions now use independent expected formats too. |
| Blind 7 | medium | defer | Actual Docker-template evaluation is not exercised. HOME logic was traced: seen requires one entry, unique stays false after any duplicate, home requires the exact supported value. Missing/wrong/duplicate/conflicting HOME all fail the final conjunction. Rendering compatibility still needs a separately authorized runtime check; no new interpreter/dependency or Docker execution added. |
| Edge 1 | medium | patch | Same demonstrated Unicode parsing defect as Blind 2; fixed and covered by that regression. |
| Edge 2 | medium | patch | Closed descriptors can make sys.stdin/stdout None. Existing TTY guard now rejects either absent stream; synthetic tests verify operation-specific exit 1 and no exec. |
| Verification 1 | medium | patch | In-memory swapping of user/workdir selectors previously escaped all tests. Independent full-format assertions plus mutation checks now reject that exact regression. Actual template rendering remains explicitly unverified under Blind 7. |
| Intent 1 | false | reject | Runtime template evaluation is absent by the explicit offline boundary, not an implementation/intent divergence. Static projection checks were strengthened; runtime evidence is deferred as above. |
| Intent 2 | false | reject | Synthetic exact-name/identity/state checks are the authorized verification surface. Actual Docker name resolution is intentionally not exercised. |
| Intent 3 | false | reject | os.execvp implements process replacement; mocked termination/diagnostics and pre-exec OSError test the permitted boundary. Actual shell/Docker exit evidence requires live authorization. |
| Intent 4 | false | reject | Multi-shell behavior is documented for future authorization; executing it is expressly excluded from this offline task. |
| Intent 5 | false | reject | Frozen diff correctly captured review as pending. This log now records all independent reviews and dispositions; source-copy preservation and final Git checks are recorded below. |

Grouped changes: four small patches (three medium, one low) resolved six finding
rows. One runtime verification item is deferred; eight observations rejected with
reasons above. No unresolved intent gap or approved-requirement change.

### Final verification and auto-run result

- Implemented [CLI](../linux-context/cli.py): metadata-only list/status, exact
  eligible selection, shared identity predicate, independent runtime/TTY guards,
  and the specified full-ID non-root argv through os.execvp. No shell interpolation,
  lifecycle operation, privilege activation, registry, trial-controller import or
  dependency was introduced.
- Added [tests](../linux-context/test_cli.py): synthetic metadata; mocked run,
  Popen, exec and terminal state; unexpected process requests fail immediately.
  Covered metadata boundaries, selection, state/identity distinctions, refusal
  cases, sanitized failures, argparse exits, exec argv and simulated passthrough.
- Added [README](../linux-context/README.md): prerequisites, three commands,
  exit semantics and proposed separately authorized three-terminal smoke sequence.
- After review fixes, exact command
  `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-context -p 'test_*.py'`:
  **PASS, 19 tests**. All five approved acceptance criteria covered at the allowed
  synthetic/process-boundary surface. No real Docker query/exec or shell occurred.
- Follow-up review recommended: **true**, at the separately authorized runtime
  gate. The pass patched three medium root causes; the specific unverified risk is
  actual Docker template rendering/compatibility. Stronger static tests prevent
  demonstrated projection mutations but do not constitute a Docker runtime test.
  Real process replacement/status propagation and multi-shell semantics likewise
  retain the documented live-smoke evidence gap. No further offline code change is
  identified by this review.
- Real-Docker/manual smoke testing: **NOT RUN**. Proposed commands, only after
  separate scoped authorization and appropriate resource/residual reconciliation:
  `python3 _bmad-output/linux-context/cli.py list`, then `status tvm-share-ld01-a`
  and `status tvm-share-ld01-b`; `join tvm-share-ld01-a` in two terminals and
  `join tvm-share-ld01-b` in a third. Use the README's read-only UID/GID, HOME/pwd,
  inode and namespace checks, then exit one A shell and confirm the other remains
  usable before exiting all. No provisioning, marker writes, probes or cleanup.
- Publication: **NOT AUTHORIZED**. The workflow's automatic commit/clean-tree
  finalization is overridden by the user. Reviewed task changes remain uncommitted;
  no push, PR, merge or tag. Historical dispositions and evidence are preserved.
- Final Git checks: `git diff --check` and `git diff --cached --check` **PASS**.
  Original/task-spec comparison shows exactly the draft-to-done status change and
  appended verification log; all approved requirements remain byte-identical.
  Completion worktree retains its original three untracked handoff/spec files,
  no tracked/index differences, and the recorded canonical HEAD. Implementation
  changes are limited to these four new task files; the canonical HEAD is unchanged.
  Final diff was inspected, including review fixes; all four files remain staged
  and uncommitted. Reviewer snapshots are retained, with no cleanup performed.
