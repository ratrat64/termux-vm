---
title: 'Fix the baseline DNS fixture without relaxing acceptance'
type: 'bugfix'
created: '2026-10-20'
status: 'done'
route: 'dispatch'
review_loop_iteration: 0
baseline_commit: '84d21ccf9e92c63eeafb7408f1042318f3a9c1eb'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

Fix the baseline-only DNS failure offline without relaxing acceptance. The dnsmasq
wildcard supplies the correct IPv4 answer, but its AAAA NODATA lacks required AA.
Replace this bounded lab DNS service with an authoritative, non-forwarding mode
in the existing Python fixture. Reuse stdlib socketserver and existing lifecycle,
upload and cleanup paths. Preserve unique private names, exact A answers,
authoritative AAAA NOERROR/NODATA over UDP/TCP and embedded-DNS rejection.

## Boundaries & Constraints

**Always:** Owner OpenCode, branch `fix/n2-baseline-diagnostic`, worktree
`/home/rat/Git/termux-vm-n2-baseline-diagnostic`. Preserve existing work, private
evidence and retained resources. Test only with disposable loopback processes and
temporary files. Keep probe/controller acceptance, containment and abort behavior
intact. Publish redacted conclusions only; private evidence stays outside Git.

**Never:** Docker/GCP/VPN operations, fault injection, company material access,
resource recreation/deletion, baseline adoption, live retries, package changes,
new dependencies or historical-verdict rewriting. Checkpoint publication approval
does not authorize a subsequent fix commit/push.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Exact mismatch | Saved probe stdout/exit results | Existing worker reproduces `validate-dns-baseline` failure | Preserve original FAIL |
| Private A | Unique `*.ld01.test`, IN/A, UDP or TCP | AA, NOERROR, one exact configured IPv4 record | No aliases or alternate addresses |
| Private AAAA | Unique private label, IN/AAAA, UDP or TCP | AA, NOERROR, zero answers, local SOA negative authority | No IPv6 address or upstream lookup |
| Other domain/class | Query outside the lab contract | Refused, no forwarding | Never use host resolver |
| Malformed packet/frame | Invalid/truncated question or TCP framing | Bounded rejection/connection close | No worker crash, unbounded reads or leaked sockets |
| Bad baseline | Missing AA, error status, wrong A, AAAA record, or embedded reply | Original probe/controller rejects | No PASS or automatic retry |

</frozen-after-approval>

## Code Map

Under `_bmad-output/linux-docker-trial/controlled-vpn/`:

- `fixtures.py:106–200`: `probes()` enforces DNS acceptance; `probe_report()`
  retains failures. Preserve both. Extend socketserver fixtures and mode dispatch.
- `setup-server.sh:186–205`: replace dnsmasq configuration/DNS unit command;
  fixture source is already copied/uploaded.
- `trial.py:975–1001,1283–1350`: Shell archives before verdict, connect probes both
  shells, controller validates HTTP/identity/canaries. Preserve this flow.
- `test_baseline.py`: existing offline unittest/mock harness.
- `test_trial.py:1044–1087`: positive mock assumes AA on every lab response,
  missing the actual fixture incompatibility.

## Tasks & Acceptance

**Execution:**
- [x] `fixtures.py` — bounded authoritative UDP/TCP mode: validate headers, one
  uncompressed IN question, lengths and framing; return exact A or AAAA NODATA/SOA.
  Bind only the supplied fixture address; never recurse/forward.
- [x] `setup-server.sh` — wire DNS unit to the fixture, tunnel address/port 53;
  retain names, deadlines, rollback and package state.
- [x] `test_baseline.py` — synthetic saved-shape rejection, real loopback UDP/TCP
  through unchanged probe, malformed-input checks and negative acceptance cases.
- [x] `../baseline-diagnostic.md`, `../../task-owner.md` — append diagnosis and
  verification; retain original live FAIL and resource/evidence dispositions.

**Acceptance Criteria:**
- Given saved-shape responses, when replayed offline, then only lab AAAA fails at
  the observed stage.
- Given the fixture, when fresh A/AAAA labels are queried over UDP/TCP, then the
  unchanged positive predicate accepts all four replies.
- Given non-AA NODATA, bad answers/status or embedded replies, when validated,
  then baseline still fails.
- Given completion, when offline suite/syntax/whitespace checks run, then all pass
  without retained-runtime operations or a new live verdict.

## Implementation Notes

- User approved and continued on 2026-10-20; frozen intent is locked. Approval
  covers offline implementation and verification only.
- Checkpoint: 19 existing files committed/pushed as
  `84d21ccf9e92c63eeafb7408f1042318f3a9c1eb`; 87 tests PASS in 15.430 seconds.
- Read both `shell-probe-*.json` and private stage stderr under
  `/home/rat/.local/state/termux-vm-private/baseline-live-20261020T140706Z-attempt1/`.
  Mocked-I/O replay through the actual worker reproduced both errors and all DNS
  verdicts without editing evidence.
- Local dnsmasq 2.92 reproduced the flag mismatch on an ephemeral loopback port;
  retained remote version is recorded as 2.90. Saved replies prove the actual
  failure; local version equivalence is not claimed.
- Loopback authoritative-zone mode returns AA but NXDOMAIN for unique wildcard
  names. Wildcard host-record syntax does not fix that. Removing AA or unique
  labels would weaken acceptance and is excluded.
- No intent gaps or irreversible actions. Protocol fixture plus service wiring
  merits dispatch scope and BMAD approval before implementation.

## Spec Change Log

## Review Triage Log

- Implementation worker prepared portable fallback prompts because it lacked
  subagent tools. The coordinator has subagent tools, removed those redundant
  generated prompts and completed three independent reviews in separate task
  worktrees. Findings are recorded individually before shared-root patching:

| ID | Verdict | Evidence and route |
|---|---|---|
| B1 | medium | Serial TCP handler blocks UDP for two seconds, exceeding dig's one-second timeout. Patch independent TCP handling and a concurrent UDP regression. |
| B2 | medium | Default TCPServer cannot rebind after a completed TCP request leaves TIME_WAIT. Patch address reuse and fixed-port restart proof. |
| B3 | low | Accepted EDNS query gets no response OPT. Patch a minimal response OPT; preserve no-forwarding and size bounds. |
| B4 | medium | Exact-address tests use only 127.0.0.1; hard-coding it would escape verification. Patch alternate loopback address in real UDP/TCP tests. |
| B5 | medium | Idle-only TCP timeout test cannot distinguish absolute from per-read deadline. Patch paced incomplete frame spanning the deadline and delayed valid fragmentation. |
| B6 | low | server.json records dnsmasq version despite active Python backend. Patch additive active-backend/Python metadata, retaining package inventory. |
| B7 | false | Fallback prompts existed in the implementation worker result; coordinator deliberately removed them to run actual independent review instead. Replace stale pending-review prose with completed-review results; no missing review remains. |
| E1 | medium | Independent reproduction confirms B2's same-address TIME_WAIT bind failure; share its address-reuse correction. |
| V1 | medium | Pre-verified mutation forces 127.0.0.1 and all six DNS tests still pass. Share B4's alternate-address regression. |
| V2 | medium | Pre-verified per-read-timeout mutation passes existing tests. Share B5's paced absolute-deadline regression. |

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p 'test_*.py' -v`
- `bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh`
- `git diff --check`

### Offline implementation results — 2026-10-20

- All 93 tests PASS in 25.993 seconds, no skips; Bash syntax and whitespace PASS.
- Matrix coverage (all ran): exact mismatch →
  `DNSFixtureTests.test_saved_shape_reproduces_only_lab_aaaa_failure_at_original_stage`;
  private A/AAAA → `test_real_udp_tcp_dig_passes_unchanged_probe_with_unique_labels`
  and `test_wire_exact_a_nodata_and_refusal_without_resolver`; other domain/class →
  the latter wire test; malformed packet/frame →
  `test_malformed_datagrams_and_frames_are_bounded_and_service_survives`;
  bad baseline → `test_bad_baselines_still_fail_without_retry`.
- Actual fixture CLI and real loopback `dig` exercise all four lab DNS predicates
  unchanged, plus local SOA inspection. Probe application lookup, HTTP, direct
  canary and embedded DNS I/O are synthetic; no retained runtime was used.
- No live retry/verdict, resource/package change, baseline adoption, commit or
  push. Original live FAIL and private evidence/resource dispositions preserved.
- Initial implementation ceiling (subsequently corrected): serial TCP could delay
  UDP by two seconds. Review B1 replaces this with stdlib daemon TCP workers;
  each request retains its two-second absolute deadline.

### Final coordinating verification — 2026-10-20

- Blind, edge-case and verification-gap reviews completed in three separate
  worktrees. Every finding has a disposition above; all accepted findings were
  patched, nothing deferred. The stale fallback handoff claim is superseded by
  actual review completion.
- Final full suite: **98 tests PASS in 27.272 seconds, no skips**. Bash syntax and
  whitespace checks PASS. Eleven new DNS tests supplement the original 87.
- B1/B2/B3/B4/B5/B6 and E1/V1/V2 corrections cover independent UDP/TCP response,
  fixed-port restart, EDNS OPT, non-default address, paced absolute deadlines and
  active-backend metadata. Existing matrix checks all ran and passed.
- `probes()`, `probe_report()` and controller source remain unchanged. Bad
  baselines still fail; saved-shape mismatch reproduction still fails at the
  observed stage, while the replacement lab DNS passes all four positive checks.
- `done` means offline diagnosis, implementation and review only. No live claim,
  retained-resource/evidence mutation, subsequent commit/push or adoption.

### Subsequent publication authorization

- After completion, the user said “proceed” to the offered commit/push next step.
  This separately authorizes publishing the verified fix on the existing branch;
  the earlier no-subsequent-commit/push statement describes implementation only.
  No live operation, PR, merge or release is authorized.
