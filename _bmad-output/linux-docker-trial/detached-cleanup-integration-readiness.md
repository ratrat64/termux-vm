# Detached cleanup integration and fresh baseline-only admission

**Integrated; read-only admission complete; live execution pending.** Owner
OpenCode. Continue in `/home/rat/Git/termux-vm-n2-baseline-diagnostic`, branch
`fix/n2-baseline-diagnostic`, integrated source revision
`62c6da520f827b00d4b10b53b3fcba6c70e67946`. Both task branches originally started
at `2293a9943a570ff627e07856581d3fea2f2df85f`.

The [offline fix](../implementation-artifacts/spec-detached-cleanup-authority.md)
is done, including three independent reviews and 116 passing offline tests.
The reviewed fix's pre-commit staged binary diff SHA256 was
`c921281a077cb7a61cf35cd6bfb92dc1a8c45b3df07f20346bf0bf0d11f6510f`;
it exactly matches `/tmp/opencode/detached-cleanup-final-20261020.diff`.
The approved fix checkpoint is `cf114ce51b85afca775229635fcc3eec56123f40`.
The integrated suite was rerun: **116 tests PASS in 38.906 seconds, no skips**;
Bash syntax, CLI help and whitespace PASS. This document is a separate handoff.

## 1. Preserve the baseline preparation before integration

Destination worktree `/home/rat/Git/termux-vm-n2-baseline-diagnostic`, branch
`fix/n2-baseline-diagnostic`, matched its local remote-tracking ref at the original
base. Remote freshness has not been checked. The following file contents were
preserved in checkpoint `54afe9dd399b704f2cc0c373d88616f57881c3a3` before the
merge. Paths are relative to `_bmad-output/`:

| Existing preparation file | SHA256 before integration |
|---|---|
| `implementation-artifacts/spec-baseline-dns-validation-preparation.md` (untracked) | `fc4b127a34b9626d8f211dc3f0f989f44dadd57ce8151fe45a0aaa9469fdb46d` |
| `linux-docker-trial/baseline-dns-validation-readiness.md` (untracked) | `70306fa3e4e6026f13a137defadfe936d7cf116f22bb2bee21015cb748f82676` |
| `linux-docker-trial/baseline-diagnostic.md` (modified) | `82f38286ba86efdfcbdbe8eb86a66cb02319ca4c21d2f6ef6dc033c872419507` |
| `task-owner.md` (modified) | `0aa95b0d1082b2e49c202f29d19405500bd77e57cd6c414c8b092d6baae02cd4` |

Its original index was empty; tracked preparation diff SHA256 was
`b05f1f14c0269824c3e20f180574b780adc3ee24a6b098f8872f3b4fc740464f`.
An existing untracked `controlled-vpn/__pycache__/trial.cpython-314.pyc` has
SHA256 `a8a8f1796cdfa0b52824bb4c66ad92221673477b27078ba638fb2c7d10abe4e4`.
Leave that file alone and exclude it from staging.

Integration rehearsal and actual merge:

- The four staged fix paths other than `task-owner.md` pass `git apply --check`
  in the destination, without applying anything.
- **Correction:** the earlier owner-file rehearsal was incorrectly reported
  clean: its pipeline returned `git hash-object` success while masking
  `git merge-file`'s conflict result. Blob `60b30053...` was not a clean merge.
  The actual merge paused on the owner conflict. The user then explicitly
  approved preserving both sections and the baseline's follow-up heading.
  Resolved owner blob: `79d919ff4180b7d3ddb5379c4668eee27d221f33`.
  Merge commit: `62c6da520f827b00d4b10b53b3fcba6c70e67946`.
  All three non-owner preparation documents and the existing bytecode remained
  byte-identical; all five controlled-vpn file hashes below match.

**Approved integration sequence, completed through step 5's checks:**

1. Recheck status, staged/working diffs, recent history and all preservation hashes.
   Stop on any changed input or concurrent owner activity; never stash/reset work.
2. Commit only the five already-staged fix files on `fix/detached-cleanup-authority`
   (`fix(trial): retain detached capture cleanup authority`). Keep this new runbook
   separate from the reviewed fix checkpoint.
3. With explicit permission to checkpoint the previously uncommitted preparation,
   stage only the four preparation documents listed above in the baseline worktree
   and commit them (`docs(trial): preserve baseline validation preparation`).
   This records their exact existing bytes before integration.
4. With explicit merge permission, merge the fix branch into the baseline branch
   using a normal merge; do not rebase its published history or force-push. Check
   that the three non-owner preparation files are byte-identical to their hashes,
   and that the merged owner matches the rehearsed blob above. If a conflict or
   new drift occurs, stop and retain it for a human decision.
5. Compare all five controlled-vpn file hashes below in the destination; run the
   full offline suite there once to verify the integrated checkout, plus Bash
   syntax, CLI help and whitespace checks. Bring this runbook forward separately
   after approval and record the actual fix/integration commit IDs here.

The user approved checkpoints/integration and read-only admission with “approve
all”, then separately approved the owner conflict resolution. Publication still
needs separate permission naming
the branch(es); remote advancement must be checked before any push. Any eventual
PR targets `main` under the repository policy; this diagnostic-branch integration
does not authorize a main merge, PR, release or tag.

## 2. Fresh content pins, integrated revision recorded

All paths below are relative to `_bmad-output/linux-docker-trial/controlled-vpn/`:

| File | Candidate SHA256 |
|---|---|
| `trial.py` | `5d8fece5237af95babf1213ad89ec42b9a6870db18af83f59402b9c7208937ab` |
| `fixtures.py` | `ca02ae49493df6bf2fdd3bfa1ea787f900a515c6641c78062f702dd559916ee3` |
| `setup-server.sh` | `1d1f96f9efb9829139e0ca9fa9735e9395dadb6215d07f6e4af75d353e562609` |
| `test_baseline.py` | `8861b50f2ad63397775f55160009f01a11ed67d4a634fb954239783eb787dc46` |
| `test_trial.py` | `d54ea469eb9beb7f4e7b3b5efce6437785c7bd62ef06f8fd6376b5f286fade42` |

`2293a99` is the base, **not the fixed source revision**. Code integration is
`62c6da520f827b00d4b10b53b3fcba6c70e67946`; after this documentation-only handoff
commit, pin the exact final checkout revision plus these content hashes in the new private
receipt and operator command. Recompute and compare immediately before launch;
any mismatch blocks. The controller does not itself enforce these source hashes.
Do not reuse a launcher/receipt pinned to the old revision or old `trial.py` hash.

Fresh offline checks in this preparation: Bash syntax, CLI help, staged/working
whitespace and non-owner patch rehearsal PASS. The owner rehearsal correction is
recorded above. Subsequent approved admission used metadata-only Docker/host and
strict-trust IAP/SSH reads; no live controller, capture or VPN was started.

## 3. Correct reference and current-state admission

The later private accepted reference is
`/home/rat/.local/state/termux-vm-private/baseline-home-20261020T194810Z/`,
accepted at `2026-10-20T19:48:10Z`. It records the home uplink/DNS/IPv6 reference,
two disclosed A zombies and four retained VM tasks. Saved `validation.json`
records PASS, including 13 input hashes and 37 evidence-source hashes. That saved
result establishes neither current state nor approval of the changed source.
During this preparation, all 13 saved input hashes and the adoption hash were
independently rechecked PASS against `adoption.json`/the saved validation record;
the directory is 0700 and all 14 checked files are 0600. These are fresh local
integrity/permission checks only, not new runtime observations.

The `baseline-dns-live-20261020T201014Z-approval/` record expired at
`2026-10-20T20:40:14Z`. Its operator diagnosis confirms normal-terminal root/tool
probe PASS and detached sudo FAIL; no controller was launched. Neither it nor the
older zero-zombie reference/old approval may authorize the next attempt. Preserve
all old receipts and adoption provenance unchanged, including their old source
pins. Bind the new code to the accepted data in a separate new receipt.

Ask for **read-only current-state admission and exclusive LD01 access** before
Docker/host or strict-trust IAP/SSH VM inspection. Save individual command results
in a new private 0700 directory, files 0600; evaluate each exit before continuing.
Reuse the readers and checklist in the existing baseline readiness document's
gate 1, with the later home reference above as the comparator. Do not run the
historical inspector wholesale: it continues after errors and omits the fourth
task. Omit the known-unavailable B firewall reads rather than grant capabilities.

Required comparisons before mutation:

- Original running A/B IDs, image, full Config/HostConfig/NetworkSettings/endpoints,
  destination-keyed mounts, volumes, networks/IPAM/peers, labels, namespaces,
  capability/device/limit settings and scratch identity/type/mode/ownership.
- Exact current host/A/B routes, rules and resolvers; A filter/NAT/IPv6 settings;
  home uplink/DNS/IPv6 versus accepted metadata, not an older network environment.
- `IDLE_A`/`check_idle_a` exact zombie PID/start identities and journal inventory;
  independently check inactive markers, cleanup PASS, intent off and source/
  rollback/restore/cleanup/intent hashes. Do not assume the recorded two zombies
  still match, or restart A to remove them. No active client/watcher/task chains
  or `ld01tun` may remain.
- No competing controller, independent supervisor, capture, task SSH forward or
  listener; planned host A bridge ports 20990/20992, B bridge/loopback 20991 and
  VM loopback 11940/19090 are free. Identify A's fresh exact veth/ifindex/endpoint.
- VM `free-vm` identity, no task tunnel/listeners/services/unit files; enumerate
  all task matches, explicitly including `cvpn7a1a8819b397`, `cvpn152283967635`,
  `cvpnb76f5884442f`, `cvpn309ee7be4837`. Preserve retained PKI/audit/upload metadata
  and old source/rollback hashes without opening keys/profiles. Required tools
  and package versions remain unchanged.

First unexpected failure/drift blocks; report it without repair, input editing
or retry. If state still matches the accepted reference, bind the new admission
evidence and input hashes in the new receipt. If it differs, obtain explicit
disposition/acceptance before creating new sibling baseline inputs; preserve all
older inputs. Active/failed task state is a blocker, not implicit repair authority.
Validate any new inputs with `diagnostic_inputs()` and saved-data `reconcile()`
with external command functions trapped. Never use the zero-zombie input builder
unchanged or relabel historical adoption source hashes as new source approval.

## 4. Fixed UTC window and single-attempt authorization

**Window confirmed for preparation only; execution not yet approved.** The user
confirmed the host/VM UTC date and fixed schedule below. A private draft will pin
the final published handoff commit and file hashes; its observation gate remains
false and it is not an executable authorization. Ask again before live execution.
Use these absolute timestamps without moving them:

| Boundary | Required absolute value when approved |
|---|---|
| Start | `2026-10-20T22:45:00Z` |
| Latest launch/deploy/capture | strictly before `2026-10-20T23:00:00Z` |
| Cleanup begins by | `2026-10-20T23:05:00Z` |
| Cleanup and final read-only audit finished by | `2026-10-20T23:15:00Z` |

The operator confirmed the date/window after host and VM clocks agreed. A missed
boundary expires this one attempt; never slide the deadline or reuse the receipt.
The host `date -u` observation during preparation was `2026-10-20T21:35:33Z`,
while session context dated this continuation 2026-10-21. The subsequent operator
confirmation resolves the date for the fixed schedule; no clock was changed.
Carry forward the known deferred limitation: arbitrary SIGTERM/SIGKILL of the
privileged capture wrapper itself is not covered by the fix;
controller-loss cleanup and wrapper expiry are separate exercised paths. Do not
signal the wrapper as an operator abort or claim arbitrary worker-loss safety.

The execution approval must explicitly cover one **baseline-only normal
connect/check/off**, exclusive retained LD01 reuse, controlled lab IAP/SSH
forwards/services/private PKI, A lifecycle and two non-root joined shells, existing
lab/embedded DNS/HTTP/canary/example.com-off checks, host/B negatives/continuity,
the fixed window, supervised off/abort/expiry/controller-loss cleanup and bounded
final read-only audit. No injection, reconnect, package changes, company material,
resource recreation/relabeling or automatic retry. Capture remains inbound on
only A's fresh veth, 96-byte snaplen, existing narrow filter/canary/zero-drop/count
contract. Preserve all prior evidence, resources, journals and VM material.

Only after that approval create a new sibling private approval directory (0700,
files 0600), new receipt and `authorization.json`. Retain the controller's exact
baseline-only fields/targets from the existing readiness gate 3, use the accepted
current input paths and exact residual lists, the integrated revision/content
hashes, and approved absolute `start`/`deadline`. Set reconciliation true only on
the strength of completed comparisons/acceptance. Reserve a new unused durable
attempt pathname under the private parent; let the controller create it.

From the authenticated **baseline worktree operator terminal**, authenticate
normally with `sudo -v`, then run the existing noninteractive root/tcpdump probe
before deployment. This best-effort check does not prove arbitrary sudo command
grants; denial of the exact capture invocation remains a failure. Detached sudo
is no longer a capture-stop prerequisite. Never weaken sudo policy or run a root
controller. Repeat the full current-state/preservation admission immediately
before deployment within the approved window, plus source/input/approval hashes.
Admission time consumes the same window.

Only once all gates pass, the existing command shape is:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py \
  --baseline-only --authorization "$NEW_APPROVAL/authorization.json" \
  --private-dir "$NEW_UNUSED_ATTEMPT"
```

No actual approval or attempt paths have been allocated. Follow the existing
runbook's identity-checked controller-only SIGTERM abort once; if it is gone,
observe its registered independent supervisor. Never start another cleanup worker.
Require the matching capture completion receipt and statistics, `cleaned.json`,
final `evidence.json` and any supervisor result. Complete the authorized bounded
final inactivity/restoration/preservation/residual audit by the hard stop; controller PASS
alone is insufficient. Report baseline, capture, cleanup and audit independently.
Historical baseline FAIL / cleanup PASS remain unchanged; this run is NOT RUN.

## 5. Approved read-only admission results

Current-state observations span `2026-10-20T22:12:38Z`–approximately `22:28Z`.
Private evidence parent: `/home/rat/.local/state/termux-vm-private/`.

- `admission-detached-cleanup-20261020T221238Z/`: first reader halted on an
  offline schema assumption (`State` is absent from retained-metadata.json).
  Preserve the failure. The saved full inspection, whose provenance hash is
  verified, supplies start time; saved current Docker output was reused.
- `admission-detached-cleanup-20261020T221306Z/`: **62 checks PASS**, 32 successful
  commands, original saved Docker inspection reused rather than retried. Exact
  containers/configuration/endpoints/mounts/start times/image/networks/volumes/
  scratch, accepted input hashes, A residuals/journal intent, A/B routes/rules/
  resolvers, A firewall/NAT/IPv6 and host home-state snapshot match. No competitor
  or planned host listener found. No new baseline was adopted.
- `admission-detached-remaining-20261020T221911Z/`: halted on permission denied
  reading A `/proc/1/ns/net`. No capabilities were added. User explicitly approved
  a fresh continuation reading each Docker exec reader's `/proc/self/ns/*`.
- `admission-detached-remaining-20261020T222112Z/`: **16 checks PASS** before
  stopping on filtered `systemctl list-unit-files` exit 1 with empty output.
  Distinct A/B namespaces, no live client/watcher/tunnel, required container tools,
  exact fresh A veth, VM identity/boot/tools, all four retained VM task directory
  metadata/source/rollback hashes and no loaded task units were verified.
- `admission-detached-remaining-20261020T222758Z/`: user explicitly approved the
  unfiltered-listing continuation; **7 checks PASS**, seven successful commands.
  Successful full listing contains no task unitfiles; no matching disk unit
  files/processes/tunnel/planned listeners; VM links/listener endpoint set and
  retained package versions match. VM IPv4 routes saved. Prior failed reads were
  neither erased nor counted as successes.

Host and VM both observed `2026-10-20` UTC (VM `22:21:17.973589Z`); the operator
subsequently confirmed the exact date/window above for preparation only.
The combined 85 successful checks establish this read-only snapshot, not a live
approval or proof of future state. B firewall and historical lost-baseline
equality remain unavailable/unverified as before. Operator-terminal normal sudo
root/tcpdump admission remains required; it was not attempted in the agent runner.

Repeat bounded current-state/source/input/approval checks inside the confirmed
fixed window. Keep the existing reference if those comparisons still match; any
new drift blocks. No executable authorization.json, attempt directory, deployment,
capture, VPN or cleanup retry has been created or launched. The user separately
approved committing this redacted handoff/owner update and pushing only
`fix/n2-baseline-diagnostic`; publication does not approve execution.
