# N2 — controlled VPN failure containment and recovery

**Next validation preparation:** [offline readiness and three separate gates](linux-docker-trial/baseline-dns-validation-readiness.md).
Published source `2293a9943a570ff627e07856581d3fea2f2df85f` inspected; fresh
**98 offline tests PASS**. No runtime inspection, new reference acceptance or
live authority/window. Request read-only reconciliation first; the old zero-zombie
inputs are historical. Original baseline FAIL / cleanup PASS remain unchanged.

**Latest fix follow-up:** [offline DNS fix](#follow-up--offline-baseline-dns-fixture-fix-2026-10-20)
diagnosed the missing-AA AAAA mismatch; **98 offline tests PASS**, independent
review complete. Fix publication authorized; original live FAIL remains.

## Latest — authorized baseline-only attempt FAIL; supervised cleanup PASS

- User explicitly authorized the prepared baseline-only scope, scoped capture,
  exclusive LD01 reuse and supervised transient-file cleanup, then launched from
  their authenticated terminal. Fixed window: `2026-10-20T14:07:06Z`–`14:37:06Z`,
  cleanup by `14:27:06Z`. This single attempt is complete; no retry is authorized.
- Task `cvpn309ee7be4837`; controller `14:07:06.328692Z`–`14:08:18.294694Z`.
  **Baseline FAIL:** both joined shells report `validate-dns-baseline`,
  `positive DNS/embedded rejection mismatch`. Partial probe responses and private
  stage diagnostics survived. Lab UDP/TCP A answers succeeded; UDP/TCP AAAA
  responses were NOERROR with no answers. This identifies the failed stage and
  observations, not yet the root cause or proof of the historical failure's cause.
- **Cleanup PASS** at `14:08:07.927968Z`, no cleanup errors. A restoration PASS;
  final controller checks found no A/host/B route/rule/resolver or retained
  container configuration/endpoint drift. Capture stopped: 92 captured/received,
  zero kernel drops. Final VM evidence lists no task units or task listeners.
- **Residuals:** A contains state-Z python3 PID 198 and openvpn PID 219, parent
  PID 1. These are defunct children, not active VPN processes; no container restart
  or recreation was performed. The accepted zero-zombie input is now historical
  and must not be reused unchanged for another admission. New VM PKI/audit/source
  and private attempt evidence remain retained; historical material is preserved.
- Private approval: `/home/rat/.local/state/termux-vm-private/baseline-live-20261020T140706Z-approval/authorization.json`.
  Private evidence: `/home/rat/.local/state/termux-vm-private/baseline-live-20261020T140706Z-attempt1/`.
- No injection/reconnect, company material, retained-resource recreation/deletion,
  or second controller. Follow-up here read only the attempt files; no independent
  Docker/GCP audit or runtime cleanup retry was run. Offline verification remains
  the prior 87-PASS result; source remains uncommitted in this worktree.

## Latest — user accepted baseline; private inputs prepared, no live approval

- User explicitly accepted the inspected post-reboot running reference and asked
  for private inputs only; receipt `2026-10-20T13:48:45Z` (not an execution window).
- Private baseline directory:
  `/home/rat/.local/state/termux-vm-private/baseline-20261020T134845Z/`, mode 0700,
  all ten JSON files 0600. Includes resources/image/runtime/full-endpoint metadata,
  exact current network/NAT observations, zero-zombie/retained-journal residuals,
  input paths and adoption/provenance hashes. Prior inventories remain unchanged.
- Local schema, saved-snapshot reconcile, network/peer and permission checks PASS;
  no runtime commands, credentials, live approval file/window or attempt created.
- Accepted differences are new empty scratch, current endpoints/Docker DNS NAT,
  zero zombies and retained inactive PASS/off A journal. This is a new reference,
  not recovered historical evidence; B8 and the old baseline probe cause remain
  unresolved. Current runtime state was not re-inspected during this preparation.
- Next gate: fresh explicit baseline-only live authorization (max 30 minutes with
  ten-minute cleanup reserve), separate from acceptance. No VPN or diagnostic ran.
- [Private input manifest and validation](linux-docker-trial/baseline-adopted.md).

## Latest — authorized scratch replacement/original A/B start, adoption pending

- User approved new empty scratch at the existing LD01 bind path and starting
  the original A/B, followed by inspection only. No VPN/diagnostic authorization.
- Completed `2026-10-20T13:44:59Z`–`13:45:00Z`: original A/B running, IDs/image/
  Config/HostConfig/mounts/home-volume metadata preserved. New scratch is empty,
  0700/1001:1001; old scratch contents remain lost. Docker network IDs unchanged.
- Private inventory: `/home/rat/.local/state/termux-vm-private/start-originals-20261020T134459Z/`.
  Earlier `start-originals-20261020T134426Z` preserves a pre-mutation mount-order
  guard failure; keyed comparison proved no actual mount drift.
- **46 reconciliation checks PASS.** No VPN process/tunnel/zombie entries; A has
  no task chains and its resolver/routes/rules/filter match surviving restore
  metadata. Docker embedded DNS NAT high ports regenerated; exact new state recorded.
- A retained `/run/ld01-cvpnb76f5884442f` journal remains inactive, cleanup PASS,
  intent off; hashes captured without deleting/editing material. B firewall reads
  unavailable by design (no NET_ADMIN); original raw helper false check is qualified
  in separate offline assessment. No extra privileges or GCP mutation occurred.
- **No baseline adopted.** Await explicit acceptance of the new running reference
  before generating baseline inputs; a later diagnostic still needs a fresh window.
- [Running-state report](linux-docker-trial/originals-started.md).

## Latest — authorized read-only post-reboot inventory, no baseline adopted

- Inspection completed 2026-10-20 at `13:34Z` under explicit user authorization;
  source/owner branch remains `fix/n2-baseline-diagnostic` in this durable worktree.
- Private inventory: `/home/rat/.local/state/termux-vm-private/inspection-20261020T133405Z/`
  (0700; files 0600). Earlier `inspection-20261020T133251Z` preserves failed strict
  SSH host-key lookup; selecting the existing Google Compute known-hosts file
  allowed read-only GCP inspection, with no trust/key-policy change.
- **41 source comparisons match; three observed differences:** original A and B
  are stopped (exit 137, finished `12:42:39Z`), and the historical shared scratch
  host directory is missing. Original container IDs, image, homes, documented
  runtime settings/capabilities/devices/labels and network configuration remain.
- No known task VPN process/tunnel/VM service/listener or host forward listener
  remains active. VM retained packages and all three task-directory sets remain;
  12 disposition/permission checks pass. No credentials/profiles were opened.
- Current in-container state/zombies/journals are unavailable while stopped.
  Historical full-metadata/endpoint equality remains unverified due to lost private
  evidence. **No baseline adopted**, no new execution approval file/window made.
- User decision required for missing scratch data/path and any start of the
  original stopped containers. None was started, restarted, recreated or deleted;
  no VPN connection/deployment/capture occurred. Company material untouched.
- [Redacted findings and exact scope](linux-docker-trial/post-reboot-inspection.md).

## Current task — recovered source, offline baseline-only diagnostic

- Owner: OpenCode, 2026-10-20; branch `fix/n2-baseline-diagnostic`.
- Durable worktree: `/home/rat/Git/termux-vm-n2-baseline-diagnostic`, base
  `dc1a192619471c74692833e65122d4fa4ebeeec1`.
- User authorized offline preparation/verification only. No live window is open;
  all earlier timestamps below are expired historical records. No commit/push.
- Source recovery replayed 105 successful recorded source patches into eight
  implementation/test/doc files. Recovered trial.py matches independent blob
  `3033de41d7693bfe0e688f9c0b9f1e7e70166446`; all 76 recovered tests passed.
- **Private raw evidence, credentials and baseline metadata were not recovered.**
  The restored summaries below record earlier observations, not current proof or
  files guaranteed to exist. Do not infer current resources/zombies from them.
- Baseline-only mode prepares one connection/check/off with staged private errors,
  disables injection, and requires durable external evidence paths plus explicitly
  reconciled current metadata/residuals. Missing metadata fails before external
  commands. No automatic adoption/deletion of retained resources is permitted.
- [Diagnostic implementation/readiness](linux-docker-trial/baseline-diagnostic.md)
  and [task spec](implementation-artifacts/spec-n2-baseline-diagnostic.md).
- During this task no Docker/GCP/resource inspection, connection, deployment,
  capture or fault injection occurred. Future read-only post-reboot reconciliation
  and any live test need separate approval. Company VPN material remains forbidden.
- Offline preparation complete: **87 tests PASS in 15.202 seconds**, no skips;
  Bash syntax, CLI help and whitespace checks pass. No live approval file/window
  was created. Diagnostic spec is done for offline preparation only; historical
  N2 live acceptance remains incomplete. Changes are uncommitted in this durable
  worktree; the main checkout and stale worktree metadata were left intact.

## Recovered historical N2 handoff — pre-reboot observations only

**Latest disposition — operator attempt 1 FAIL, halted:** task `cvpnb76f5884442f`,
`2026-10-20T10:42:01.745910Z`–`10:43:15.924575Z`. Verified VPN initialized, but
positive-baseline worker exited before injection. **F1/F2 NOT RUN.** A restoration
PASS at `10:42:53.617213Z`; original overall cleanup FAIL on a blank capture line.
Read-only `post-attempt-audit.json` passes all 20 restoration/resource/inactive-task
checks. No VPN/tunnel/forward/capture/VM task service remains active. New A zombie
PIDs 1923/1944 join four historical zombies; root A material and new VM audit/PKI/
source remain retained. No restart/recreation or cleanup retry. Private evidence:
`/tmp/opencode/n2-20261020T103830Z-attempt1/`. Executed source archived privately
before offline parser/error-retention fixes; 76 sandbox tests pass. Primary worker
cause remains unknown because original stderr was discarded. New admission must
reconcile six disclosed zombies/journals and receive fresh scope/window approval;
do not rerun the old command. [Detailed verdict/evidence](linux-docker-trial/n2-results.md#operator-attempt-1--fail-before-fault-injection).

**Historical operator-launched window, 2026-10-20:** user authorized the same scoped campaign from their authenticated host terminal. Receipt `10:38:30Z`; absolute hard stop `11:23:30Z`, cleanup by `11:13:30Z`, no injection at/after `11:08:30Z`. Private approval/metadata/source hashes: `/tmp/opencode/n2-20261020T103830Z-approval/` (0700/0600). Attempt above used `/tmp/opencode/n2-20261020T103830Z-attempt1`. Stop at its unexpected failure; no automatic retry. Company-material and resource-preservation boundaries remain.

**Live window authorized 2026-10-20, admission BLOCKED:** receipt `10:25:44Z`; absolute hard stop `11:10:44Z`, cleanup begins by `11:00:44Z`, no injection at/after `10:55:44Z`. User expressly approved scoped F1/F2, capture/probes, supervised off and exclusive LD01 reuse with no overlapping worker/session. Retained reconciliation passed, but host `sudo -n true` failed and `sudo -n -l` reports interactive authentication required; tcpdump has no file capabilities. **HALTED before deployment/capture/connection/injection; F1/F2 NOT RUN.** Private admission record: `/tmp/opencode/n2-20261020T102544Z-approval/admission-failure.json`; approval/metadata retained there, 0700/0600. No task runtime resources or fresh credentials created; no cleanup required. No automatic retry or host privilege changes. Earlier offline-only statements below are historical, superseded only for this scoped authorization. Retained resources/evidence and company-material prohibition remain in force.

- Owner: OpenCode — N2 offline implementation, 2026-10-20.
- Branch: `feat/n2-vpn-failure-containment`.
- Worktree: `/tmp/opencode/termux-vm-n2-vpn-failure-containment`.
- Base: freshly fetched `origin/main`, `dc1a192619471c74692833e65122d4fa4ebeeec1`, including merged PR #4.
- Scope: use `bmad-build` for the bounded controlled IPv4 split-lab N2 increment. Approved [N2 spec](implementation-artifacts/spec-n2-vpn-failure-containment.md); policy/campaign: [N2 proposal](linux-docker-trial/n2-proposal.md).
- Status: **OFFLINE IMPLEMENTATION/REVIEW VERIFIED — LIVE ACCEPTANCE PENDING. P1–P3 accepted and full spec approved-and-continued on 2026-10-20. Live execution is not authorized.** Accepted: fault-latched prefix/all-A classic-DNS containment, explicit off → connect recovery, supervised trial-off design, two-case campaign with scoped capture/counters and maximum 45-minute future window. No Docker/GCP runtime inspection, credential/evidence access, connection, failure injection or resource mutation occurred during planning, implementation or review. Spec remains `in-review` until separately authorized live acceptance; all offline review findings have recorded dispositions.
- Authorization: offline implementation/tests/review only. Historical connection/publication approvals do not authorize N2 execution. Obtain explicit failure-injection/observation scope approval and a fresh fixed execution window before deployment/testing; no rolling deadline or automatic live retries. Company VPN material is forbidden.
- Preservation: retain LD01 image, container IDs/configuration/capabilities, homes, networks, labels, project, four disclosed defunct children and all local/VM historical private evidence/material. No restart/recreation, relabeling, package changes or deletion proposed. Prior scoped LD01 reuse is historical coordination; confirm exclusive reuse/no overlap before new runtime work. Reconcile identities and full endpoints before mutation; B8 remains deferred/unverified.
- Implementation: fault-latched prefix/DNS rules, checked daemon/watch retirement, generation archives, bounded F1/F2 capture/probe/recovery orchestration and fresh-authorization-gated supervised off are implemented in `controlled-vpn/`. Final verification: **74 sandbox tests PASS in 14.873 seconds**, `bash -n` and `git diff --check` pass. Three review layers and corrections are complete. [Offline results and remaining live gates](linux-docker-trial/n2-results.md). No live window, deployment, capture or injection was started.
- Git: source, tests and N2 artifacts edited only in this worktree. No commit/push/PR/merge/tag authorization for N2.
- Review corrections: B/E/V and coordinating C1 fixes verified; frozen intent preserved. Tests cover cancellation/publication and gate races, inherited reuse flock, watcher loss, transport observation, strict capture/protocol accounting, controller off/reconnect verdicts, expiry boundaries, archival failures and slow-command supervised cleanup. Review B8 refuted; historical LD01 B8 remains deferred. No live operation/window authorized or started. Exact checks/bounds: [final verification](linux-docker-trial/n2-results.md#final-coordinating-verification-and-c1-correction).

## Previous completed task — controlled VPN trial on GCP

**Fresh execution window completed:** user explicitly selected “Authorize fresh window” after review fixes; receipt `2026-10-20T07:31:09Z`, fixed hard stop `2026-10-20T10:31:09Z` including disconnect/cleanup. Revised-source live attempt 1 and both cycles PASS; cleanup PASS at `07:36:31.392240Z`. Four terminated A child entries remain as explicit residuals. Coordinating verification passed and spec is done; original records remain historical.

- Owner: OpenCode — controlled VPN trial session, 2026-10-20.
- Branch: `feat/controlled-vpn-trial`.
- Worktree: `/tmp/opencode/termux-vm-controlled-vpn-trial`.
- Base: fetched `origin/main` at `7e37565174b54105293c75c214c0b8b97202ff21`, containing merged PR #3. Its two handoff files match the prior continuation branch after squash merge.
- Task: implement a separate controlled VPN on supplied GCP VM `free-vm`, issue a private client profile and demonstrate VPN-only internal services using LD01 A. Company VPN credentials/resources are out of scope.
- Coordination: the same continuation owner carries forward the user's relayed exclusive LD01 reuse acknowledgement below. The prior worktree is clean; new edits belong here. Existing resource ownership labels remain unchanged.
- Reconciliation: fresh predeployment checks passed against the retained baseline and original controlled run's full Config/HostConfig/NetworkSettings/endpoints and destination-keyed mounts. No old task daemon/tunnel/listener/unit or overlapping controller remained. VM Debian 12, public IPv6/no public IPv4; retained LD01 networks IPv4-only. Source/context hashes stayed unchanged during execution. This later endpoint comparison does not supply the earlier historical baseline missing in B8.
- Proposed scope: stock OpenVPN over a controller-managed IAP/SSH TCP forward, fresh private lab material, tunnel-only service/DNS and separate non-VPN heartbeat forwarding. No new public ingress/IPv4 or local VM is needed for this proposal. See [implementation spec](implementation-artifacts/spec-controlled-vpn-trial.md).
- Status: **DONE — review fixes, 31 fresh predeployment sandbox tests/Bash syntax, revised-source live trial, scoped cleanup and coordinating evidence verification PASS**. New live run `2026-10-20T07:34:59.838456Z`–`07:36:40.236169Z`, task `cvpn152283967635`, exit 0. Both joined-shell cycles passed lab DNS/HTTP, embedded-resolver UDP/TCP rejection, host/B HTTP/UDP/TCP DNS negatives and exact restoration. Host/B held sockets retained identities across 53/52 sequenced acknowledgements with zero reconnects/errors. No live fault injection or trial implementation fix was needed. Details and exact audit dispositions: [controlled-vpn-results.md](linux-docker-trial/controlled-vpn-results.md).
- New profile/evidence: `/tmp/opencode/controlled-vpn-20261020T0736Z-attempt1/` (0700, files 0600), private `client.ovpn`, `evidence.json`, `cleaned.json`, archived A rollback state and logs. Audit records: `/tmp/opencode/controlled-vpn-20261020T0733Z-audit/preflight.json` (inspection self-match FAIL, preserved), `/tmp/opencode/controlled-vpn-20261020T0735Z-audit/preflight.json` (PASS), new run's `post-run-audit.json` (name-only zombie check FAIL, preserved) and `post-run-audit-2.json` (19 state-aware checks PASS). No live connection/deployment attempt failed. Original `/tmp/opencode/controlled-vpn-20261019T2153Z/` profile/evidence/state/cleanup hashes are unchanged; historical 43/42 counts are not reused as new proof.
- Final disposition: original A/B IDs/configuration/capabilities/mounts/full endpoints remain; no recreation. Exact A routes/rules/resolver/filter/nat/IPv6 state restored; no active client/watcher/tunnel, forwards, VM task listeners/units or task unit files; new A material removed after explicit PASS. **Residuals:** A has defunct state-Z OpenVPN PIDs 1037/1325 and watcher PIDs 1006/1294, all parent PID 1 (`sleep infinity`, not reaping). No active VPN/socket is retained by them; no restart/recreation was performed. VM retains both `/var/lib/ld01-cvpn-cvpn7a1a8819b397` and `/var/lib/ld01-cvpn-cvpn152283967635`, both `/tmp/ld01-upload-cvpn7a1a8819b397` and `/tmp/ld01-upload-cvpn152283967635`, and the six unchanged native packages/config/apt directories inventoried in results. Old rollback script hash/mtime unchanged; new cancellation marker set. Company/native-UDP/full-tunnel/live-IPv6/account/S1–N3/restricted daily-control acceptance remains unclaimed. B8 remains deferred, medium/unverified; spec is `done` after coordinating verification.
- Final proof: `python3 /tmp/opencode/controlled-vpn-final-proof.py` passed against raw private evidence and current implementation/original-evidence hashes. All acceptance and matrix checks are accounted for. Spec status is `done`; B8 stays deferred/unverified.
- Git handling: implementation/execution originally prohibited commit/push/PR. After completion, the user explicitly confirmed proceeding with committing these changes, pushing `feat/controlled-vpn-trial` and opening a PR against `main`. This subsequent publication authorization supersedes the original restriction only for this scoped work. Source and redacted results stay under `_bmad-output`; secrets/private evidence stay outside Git. No merge/tag authorization. SSH remote access works; GitHub CLI currently reports an invalid token, so PR creation requires restored authentication.

## Previous continuation record — merged PR #3

- Owner: OpenCode — VPN trial continuation session, 2026-10-19.
- Branch: `docs/vpn-trial-continuation`.
- Worktree: `/tmp/opencode/termux-vm-vpn-trial-continuation`.
- Base: freshly fetched `origin/main` at `8bd49ab74adcfcfb0917f20dab78ee8059b2aba5` (merged LD01 baseline and VPN readiness handoff).
- Task: continue the VPN trial handoff and coordinate retained LD01 reuse; the user subsequently redirected execution to a separate controlled VPN on the supplied GCP VM.
- Coordination: user selected **Owner cleared scoped reuse** in this session, relaying the prior Linux Docker trial owner's acknowledgement for exclusive continuation reuse of `tvm-share-ld01-*` and `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM`, with no overlapping runtime or artifact edits. This is scoped reuse, not ownership transfer. The prior worktree was clean when inspected and remains the historical handoff; continuation edits belong in this worktree.
- Retained resources: reuse the frozen image, A/B containers, respective home volumes, separate networks and scratch project listed in [execution-results.md](linux-docker-trial/execution-results.md). Preserve labels `task=linux-docker-sharing-trial`, `trial=ld01`, `owner=opencode-linux-trial-preparation`. No resources have been recreated, relabeled or mutated in this continuation. Reconcile exact retained IDs, image, mounts and capabilities with private baseline evidence before any later runtime change; their current state has not been rechecked in this session.
- Original evaluation boundary: `tvm-eval-dhlrhsji-*` and original staging remain under the original evaluation owner. Earlier scoped staged-material read/private-adaptation/read-only-mount clearance remains as recorded below; it does not authorize modifying original staging/resources.
- Historical company-session authorization: user approved immediate start, then confirmed no other session used the certificate and allowed up to three hours. Recorded at `2026-10-19T16:19:16Z`, with a hard stop at `2026-10-19T19:19:16Z` UTC including disconnect/cleanup. The later instruction not to use the company VPN supersedes this connection authorization.
- Current scope: do not use the company VPN, certificate or staged profile. The user supplied GCP VM `free-vm`, accessible with `gcloud compute ssh free-vm --tunnel-through-iap`, for a separate VPN that issues a client configuration and provides access to internal test services. GCP access/networking and the controlled server/client/service/DNS/heartbeat design have not been inspected or implemented. A controlled fixture would prove only its own mechanism, not company VPN compatibility. See [vpn-stage-readiness.md](linux-docker-trial/vpn-stage-readiness.md).
- Execution status: **NOT RUN**. Preserve retained LD01 resources and historical evidence; reconcile their exact baseline before later reuse. The controlled VPN implementation is follow-on work, with fresh lab credentials kept outside Git. The historical company-session window is not a rolling authorization for future execution.
- Evidence status: LD01-T/LD01-F and the `2026-10-19T15:38:37Z` bounded material checks are prior **PASS** results, not new checks or VPN acceptance. No baseline rerun, credential access, private config adaptation, credential mount, container recreation or VPN connection occurred in this session. LD01-J/LD01-C and S1–N3 VPN/account checks remain **BLOCKED/NOT RUN**.
- Git handling: user explicitly requested committing and pushing this continuation handoff and opening a PR. Stage only these redacted handoff updates. Prior branch-specific authorization below is historical. Credentials and private generated evidence remain outside Git.

## Previous task record — historical authorization and evidence

The following records the prior preparation session; references to “this session” below refer to that owner, not the continuation above.

- Owner: OpenCode — Linux Docker trial preparation session, 2026-10-19.
- Branch: `docs/linux-docker-trial-preparation`.
- Worktree: `/tmp/opencode/termux-vm-linux-docker-trial-preparation`.
- Base: `main` at `c6dc04f`.
- Task: prepare the smallest next Linux Docker increment from the environment-sharing research; identify inputs/permissions and keep imported evidence separate from unrun acceptance.
- Handoff, read-only: `/tmp/opencode/termux-vm-environment-sharing-evaluation/_bmad-output/task-owner.md`, linking its research and additional-trials plan.
- Original trial owner: OpenCode, isolated-terminal evaluation task, branch `docs/isolated-terminal-evaluation`, worktree `/home/rat/Git/termux-vm-isolated-terminal-evaluation`.
- Coordination: user first selected **Fresh resources (Recommended)**. On continuation, user selected **Owner cleared scoped reuse**, relaying the original owner's acknowledgement for reading the existing staged export/four files, making a separate private adapted configuration and read-only mounting into A. This is scoped material reuse, not ownership transfer or permission to change the original staging/resources.
- Ownership boundary: this session owns this worktree and `tvm-share-ld01-*`. Original `tvm-eval-dhlrhsji-*` containers/volumes/networks and scratch project remain untouched. Existing source/results/image may be reused read-only, and staged material may now be checked/read and separately adapted under the user's relayed acknowledgement. Coordinate any broader reuse/modification with the original owner first.
- Resource labels: `task=linux-docker-sharing-trial`, `trial=ld01`, `owner=opencode-linux-trial-preparation`. This session created and owns only the new LD01 image, A/B containers, home volumes, networks and scratch directory recorded in [execution-results.md](linux-docker-trial/execution-results.md). No retained resources transferred.
- Authorization update: build/baseline permission remains recorded. User now selected **Authorize scoped VPN stage**: current material checks, separate private adapted configuration, later A recreation with existing home/network/project, read-only credential mount and NET_ADMIN plus SETUID/SETGID for configured OpenVPN privilege dropping; connection/disconnection is conditional on all ownership/policy/target prerequisites. Ordinary shells stay non-root. Runtime changes/connections have not occurred under this extension.
- Remaining inputs: user selected **Approved single-session window** but supplied no time/window or confirmation that conflicting sessions are absent; user selected **Targets not available yet**. These are blockers, not permission for concurrent same-certificate sessions. See [vpn-stage-readiness.md](linux-docker-trial/vpn-stage-readiness.md).
- Status: tooling build/fresh baseline **PASS**; scoped current-material metadata/openability and CA/client expiry checks **PASS** at `2026-10-19T15:38:37Z`. This does not establish container daemon readability or server acceptance. VPN/account trials remain **NOT RUN/BLOCKED**; no config adaptation, A recreation or credential mounting yet. New resources are retained idle; no host VPN/daemon configuration changes made.
- Evidence/status record: [readiness.md](linux-docker-trial/readiness.md).
- Private evidence: `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/` outside Git. Runnable source: `linux-docker-trial/tooling/Dockerfile` and `linux-docker-trial/spot-check.py`.
- Git handling: user explicitly authorized committing the trial source and redacted handoff/results and pushing `docs/linux-docker-trial-preparation`. No PR requested. Credentials, token-bearing state and raw/private generated evidence stay outside Git; stage only the reviewed task artifacts.

## Follow-up — offline baseline DNS fixture fix, 2026-10-20

- Owner OpenCode; branch `fix/n2-baseline-diagnostic`, same durable worktree.
  Checkpoint `84d21ccf9e92c63eeafb7408f1042318f3a9c1eb` is already published;
  this subsequent fix is prepared for authorized commit/push. The frozen approved intent in
  [DNS fixture spec](implementation-artifacts/spec-baseline-dns-fixture-fix.md)
  is preserved; its `context:` list was empty.
- Diagnosis from both retained probe results/stderr: lab AAAA NOERROR/NODATA lacks
  required AA; lab A is correct and embedded DNS gives no reply. Synthetic
  saved-shape replay reproduces only the lab UDP/TCP AAAA failures at the recorded
  worker stage. This does not establish the older stderr-lost failure's cause.
- Added bounded stdlib authoritative/non-forwarding UDP/TCP DNS to the existing
  fixture and wired the existing DNS unit to the tunnel address/53. Exact private
  A and authoritative AAAA NODATA/SOA pass the unchanged probe. Bad answers,
  missing AA, error status and embedded replies still fail. Malformed input is
  bounded/dropped or closed; each TCP request has a two-second absolute deadline.
  Review corrections use stdlib daemon TCP threads to keep UDP/other TCP queries
  responsive, enable pre-bind address reuse for immediate restart, and return
  minimal EDNS response OPT records. `server.json` now identifies the active
  `fixtures.py:dns` backend and Python executable/version while retaining package
  version evidence.
  Probe/controller acceptance, containment, abort, lifecycle and packages remain
  intact. No new dependency or package operation.
- Initial implementation: **93 offline tests PASS in 25.993 seconds, no skips.**
  Six new DNS tests use synthetic saved-shaped I/O and disposable
  loopback fixture processes/ports; real lab `dig` traverses the unchanged probe.
  Other probe dependencies are mocked. Review corrections: **19 focused tests PASS
  in 16.910 seconds, no skips; Bash syntax and whitespace PASS.** Regression proofs
  add concurrent incomplete-TCP/healthy-UDP/TCP, fixed-port restart, EDNS/plain
  responses, exact-wire `127.0.0.2` answers, paced absolute-deadline enforcement,
  delayed valid fragmentation/subsequent health, and active DNS/Python metadata.
  Final coordinating verification: **98 tests PASS in 27.272 seconds, no skips**;
  Bash syntax and whitespace PASS. Three independent review layers completed in
  separate worktrees; all accepted corrections verified, nothing deferred.
  Portable fallback handoffs were replaced by actual reviews. Spec is `done` for
  offline diagnosis/implementation/review only, with no new live acceptance.
- **Original live baseline FAIL and cleanup PASS remain unchanged.** No new live
  verdict, retry, adoption or Docker/GCP/VPN operation. Two recorded A zombies,
  retained VM PKI/audit/source, private attempt evidence and original resources
  retain their documented dispositions; none was re-inspected or mutated.
  [Appended diagnosis/verification](linux-docker-trial/baseline-diagnostic.md#offline-dns-fixture-fix--2026-10-20).
- After offline completion, the user's subsequent “proceed” authorized publishing
  this verified fix on the existing task branch. This supersedes the earlier
  uncommitted/unpushed disposition only; no live operation or PR is authorized.
