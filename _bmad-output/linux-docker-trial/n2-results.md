# N2 — offline implementation and verification

> **Recovery notice, 2026-10-20:** this redacted summary was recovered from
> persistent source-edit records after `/tmp/opencode` was emptied during reboot.
> The referenced raw evidence/private metadata is unavailable, and the observations
> below are historical. Do not infer current resource disposition or a live PASS
> from recovered prose. Source is now in a durable worktree; see
> [baseline-only diagnostic](baseline-diagnostic.md). No new live run has started.

**2026-10-20: OPERATOR LIVE ATTEMPT FAILED DURING POSITIVE BASELINE, BEFORE INJECTION. A NETWORK RESTORATION AND POST-RUN DISPOSITION AUDIT PASS; ORIGINAL OVERALL CLEANUP VERDICT FAIL. F1/F2 NOT RUN.**

Latest: one operator-launched attempt ran `10:42:01.745910Z`–`10:43:15.924575Z`.
No automatic retry. The capture-parser defect is fixed offline and private shell
error retention added; 76 sandbox tests pass. The original baseline worker's
exception was not retained and remains undiagnosed. Details follow at the end.

Owner: OpenCode, `feat/n2-vpn-failure-containment`, worktree
`/tmp/opencode/termux-vm-n2-vpn-failure-containment`.
Baseline: `dc1a192619471c74692833e65122d4fa4ebeeec1`.
Authority: [approved build spec](../implementation-artifacts/spec-n2-vpn-failure-containment.md),
with [P1–P3 context](n2-proposal.md). Implementation approval starts no live window.
The previous controlled-trial verdicts and deployed rollback sources remain historical.

## Implemented

- A's task OUTPUT chain rejects the VPN prefix on any interface except `ld01tun`,
  ahead of established-flow handling. Conntrack-original UDP/TCP DNS restrictions
  also require the tunnel interface. IPv6 blocking and DNS replacement precede
  client startup; incomplete protection cannot start a client.
- Durable `starting`, `connected`, `faulted`, and explicit `off` intent separates
  failure from restoration. Client death, stale leases, deadline loss, startup
  errors, and ordinary controller cleanup latch containment. Faulted/obsolete
  generations cannot start or renew. Off retires the identity-checked daemon and
  watchers before releasing rules; failed retirement retains protection.
- Fault journals and bounded daemon-log tails are archived before off or another
  generation. Exact resolver bytes, routes/rules, filter/nat and IPv6 settings are
  compared during restoration. Failed attempts retain journals/material for an
  explicit retry; only PASS permits scoped A material removal.
- The future campaign runs F1 (checked client SIGKILL) and F2 (checked VPN-only
  forward termination), once each: healthy baseline, at least 60 seconds of fault
  observation, explicit off, baseline DNS/direct-IP checks, and a fresh verified
  reconnect. Two non-root shells, host/B held sockets, and an independent A
  direct-IP socket persist across the cases. Fresh host/B canaries supplement
  held sockets; unrelated health failures still abort F2.
- A tunnel-bound heartbeat exercises an existing VPN flow without reconnects.
  Unique private names cover application A/AAAA and explicit UDP/TCP queries to
  the tunnel resolver and Docker embedded resolver. Literal and named private
  HTTP check the exact task fixture. Public DNS failure is expected during a
  fault; off probes query only the approved public name, never private names.
- Header-only capture uses A's checked veth ingress, scoped to VPN-prefix/DNS
  traffic and approved bootstrap/direct canaries. It includes packets retaining
  a VPN source address after tunnel loss. Readiness, positive canaries, process
  identity, protected intervals, header counts, kernel drops and rule-counter
  growth gate PASS. Forbidden headers abort during observation. Raw headers,
  statistics, profiles and journals stay private.
- One fresh authorization fixes the same UTC deadline across controller,
  supervisor, agent, capture and newly uploaded server source. Maximum window:
  45 minutes. Injection requires more than 15 minutes remaining; supervised off
  begins by the ten-minute cleanup reserve. Controller/agent failure alone
  cannot release protection. An admitted campaign explicitly pre-authorizes the
  independent supervisor's abort/expiry off. Server setup uses retained packages
  and local-only private DNS; no apt action or new dependency is introduced.

## Offline attempts and commands

No Docker/GCP inspection, connection, deployment, packet capture or fault injection
was executed. Tests use synthetic netfilter/routes, temporary files, disposable
Python children and loopback-only fixtures. They do not use retained LD01 runtime,
credentials, old private reports or company material.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p test_trial.py -v
bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh
git diff --check
```

- First adapted run: 31 tests, two test-clock stub errors (`monotonic` absent).
  Corrected the sandbox clock; the 31-test run passed.
- Expanded run: 47 tests, one incorrect exception assertion for a synthetic
  netfilter timeout. Kept the real `TimeoutExpired` behavior and corrected that
  assertion.
- Expanded run: **51 tests passed**, approximately 11 seconds. Syntax and
  whitespace checks passed. No skipped tests.
- Completion checks exposed reused F2 forward bindings and teardown retry/retention
  edge cases. Retired forwards are now excluded from final listener checks; a
  failed explicit off cannot be retried implicitly by abort/supervisor cleanup;
  failed server stops preserve unit definitions. Private record publication is
  atomic so the supervisor cannot read half-written cleanup results.
- Final run after those fixes: **55 tests passed in 11.424 seconds**; server shell
  syntax and `git diff --check` passed. Independent multi-reviewer review is pending.

Matrix coverage: admission rejection (`RejectionTests`, authorization checks);
positive-baseline abort and both recovery sequences (`AdmissionAndObservationTests`);
fresh/held prefix and DNS rejection (`ContainmentTests`, `DNSTests`);
ordinary/unauthorized cleanup versus pre-authorized supervised off (`WatchdogTests`);
retryable teardown failure and preservation (`RestorationTests`). Real disposable
socket checks cover heartbeat sequence corruption, one-socket fault probing and
direct-path continuity. Capture proof checks reject absent readiness/canaries,
loss/count mismatches, forbidden VPN-source headers and missing counter growth.

## Bounds and evidence locations for a future authorized run

Measured offline only: the capture-helper sandbox exits at its half-second test
expiry; the server worker sandbox times out with one second left above its
cleanup reserve. The fault-orchestration tests advance a synthetic monotonic
clock through at least 60 seconds. These are **not live detection/cleanup SLAs**.
Agent and server-worker lifecycle locks wait at most eight seconds; root commands
inside the agent have two-second subprocess limits. Server setup is capped at
80 seconds plus a five-second kill grace. Server rollback waits at most 90
seconds for setup, then stops only the five fresh task units. No teardown error
can produce PASS or delete failed A rollback material.

No campaign evidence directory or authorized UTC start/hard stop exists for this
implementation session. A later invocation requires a new unused direct child
of `/tmp/opencode`, mode 0700; runtime files are 0600. The authorization file
must also be outside Git, 0600 in a 0700 directory. Its required JSON fields are:

| Field | Required content |
|---|---|
| `start`, `deadline` | Fresh fixed UTC timestamps, `YYYY-MM-DDTHH:MM:SSZ`, at most 45 minutes apart |
| `injection`, `observation`, `exclusive_reuse`, `supervised_off` | Each exactly `true`, affirmatively authorized by the human |
| `cases` | `["F1", "F2"]` |
| `targets` | `["tvm-share-ld01-a", "free-vm", "A-veth", "example.com"]` |
| `retained_metadata` | Private metadata-only JSON path keyed by retained A/B names, containing full inspect configuration/endpoints/mounts for pre-mutation reconciliation |

Do not create or populate a live approval from this example. Later execution
must separately approve the exact injections, capture/filter/targets, exclusive
reuse and supervised off, after offline review. Future private evidence includes
`state.json`, `evidence.json`, `fault-evidence-F1.json`, `fault-evidence-F2.json`,
`capture-*.headers`, `capture-*.stats`, per-generation A archives, sequenced
heartbeat/probe streams and all failed cleanup attempts. New VM task material is
retained under `/var/lib/ld01-cvpn-<task>` and fresh source under
`/tmp/ld01-upload-<task>`; old deployment directories are not reused.

## Residuals and pending acceptance

- Independent review corrections and offline verification are complete. Live F1/F2 boundary proof, actual tcpdump permissions/output/drop accounting,
  exact retained endpoint metadata, fixture DNS behavior on the retained package
  versions, host/B continuity and real teardown timing await separate live
  authorization and execution. Offline mocks prove control flow/rule semantics, not kernel
  packet behavior. Missing prerequisites or observation proof reject the run;
  the code does not install packages or relax checks.
- The P1 all-A DNS tradeoff remains: public DNS also fails while faulted, while
  unrelated direct-IP traffic continues. Off restores ordinary DNS; there is no
  always-private-name rule. Live IPv6 is untested.
- B8, wider N2/N3, company material, full tunnel, native UDP, controller kill as a
  live case, blackhole and owner/container recreation remain deferred/NOT RUN.
  The four historical defunct A children remain disclosed. A later run records
  process listings before/after and must report additional zombies without
  restarting or recreating A.

No commits, pushes, PRs, merges or tags were made.

## Independent review

The implementation worker could not launch reviewers and returned to the
coordinating session. The coordinator ran blind, edge-case and verification-gap
reviews in separate review worktrees. Findings, refutations and correction
dispositions are recorded individually in the spec's Review Triage Log.

## Review correction pass — 2026-10-20

The implementation worker applied the coordinator's B/E/V patch list without
editing the frozen spec or its coordinator-owned triage log:

- F2 exercises fresh HTTP/application/DNS probes from both shells, the held VPN
  socket and capture while the client is still live, before forced fault retirement.
  That stage shares the observation deadline measured from injection; it does not
  start another 60-second interval. Missing live-client/held-flow proof fails the
  case. Lease, deadline, watcher, heartbeat and sibling-forward failures remain
  independent abort conditions.
- Injection requires a live matching forward PID/start/specification/process
  group and more than 900 seconds remaining. Teardown remains idempotent. Client
  injection rechecks identity and reserve after its fault snapshot.
- Capture gates expire even when the controller leaves stdin open without a byte.
  EOF/timeout retires the gated child. PASS requires received packets, captured
  packets and complete parsed headers to be equal, with zero drops; buffered or
  otherwise unaccounted packets fail closed.
- Agent preparation installs protection before publishing `starting` or watcher
  readiness. Watchers retry transient lifecycle-lock contention; status checks
  validate the registered watcher identity/completion and latch unexpected loss.
- The existing cleanup lock serializes controller mutations with teardown. A short
  publication lock orders cancellation, unique staged state writes and gate/client
  release. The supervisor publishes cancellation first and reloads the latest
  state after acquiring ownership. Stale controller saves and starts are rejected.
- The supervisor inherits the existing exclusive-reuse flock through controller
  death and cleanup. Preflight rejects unresolved A journals/chains and active
  clients while recognizing the four disclosed zombies as the retained baseline.
- Fault hold accepts only transport exceptions as blocked outcomes; malformed,
  oversized or invalid protocol responses fail. Fault archives retain bounded
  current network/counter/process observations and independent observation errors.
  Malformed non-authoritative attempt records are retained as raw evidence;
  restoration/identity journals remain strict. Cleanup attempts publish atomically.
- No new retry interface was added for rejected review finding B8: direct root
  restoration remains human-retryable. Historical LD01 B8 remains deferred.

Focused verification ran from `_bmad-output/linux-docker-trial/controlled-vpn`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_trial.ReviewPatchTests test_trial.AdmissionAndObservationTests test_trial.ContainmentTests test_trial.WatchdogTests test_trial.RestorationTests test_trial.FaultFixtureTests test_trial.ForwardGateTests test_trial.ContinuityTests test_trial.DNSTests test_trial.RejectionTests -v
```

**66 tests passed in 12.431 seconds, no skips.** Coverage includes deterministic
ownership/cancellation and gate races, actual supervisor flock inheritance across
disposable controller death, actual watcher loss after readiness, real controller
fault verdicts for each escaping result, real off/fresh-connect transitions,
900/899-second reserve rejection and admitted baseline time consumption, stalled
capture stdin, malformed server replies and malformed attempt preservation.
Earlier patch iterations required adapting prepare-time protection assertions and
isolating synthetic lease RPC from the test's process-global argv/stdout capture;
those harness failures are corrected in the passing run above.

At that checkpoint full coordinating verification and review closure were pending;
the subsequent checks below resolve the offline gates. No live operation or new
window was authorized or executed. Real F2
transport may retire the client before live-interval proof is available, and real
capture backends may report unequal received/header counts; either condition must
fail the campaign rather than relax evidence. The fresh authorization, retained
endpoint/package reconciliation, capture privilege/readiness and measured live
containment/continuity/cleanup gates above still apply.

## Final coordinating verification and C1 correction

- First full post-review checkpoint: **70 tests passed in 14.925 seconds**;
  Bash syntax and whitespace checks passed. The 66-test worker run above was a
  focused subset excluding the four server lifecycle checks.
- Coordinator found C1: eight-second supervisor acquisition could abandon cleanup
  while a serialized connect/deploy/off command was still running. Correction
  publishes a cancellation-request marker before waiting, rejects subsequent
  admitted commands/results, caps each in-flight admitted command at 100 seconds,
  and allows 110 seconds for supervisor publication/ownership acquisition.
- Fault latch and explicit supervisor off share one 300-second teardown budget,
  shortened to leave 20 seconds before the absolute hard stop. The two lock waits,
  teardown budget and margin total at most 540 seconds of the ten-minute reserve.
  Lock/command budget exhaustion produces private FAIL evidence; it never extends
  the window or permits a new campaign attempt. These are source/sandbox bounds,
  not a live completion guarantee under unavailable Docker/GCP services.
- Added four deterministic C1 tests covering real supervisor cleanup during slow
  connect/deploy, lock-failure evidence, command cancellation and shared deadline
  budgeting. First 74-test run exposed two exhausted finite clock stubs in the
  older watchdog test; the stub now retains its final simulated remaining time
  for cleanup-budget checks. No implementation expectation was weakened.
- **Final: all 74 tests passed in 14.873 seconds, no skips** using the full discover
  command above. `bash -n` and `git diff --check` passed. All review findings have
  recorded dispositions: corrections verified, B8 refuted, historical LD01 B8 still
  deferred/unverified. No unresolved offline review correction remains.

Spec stays `in-review` because live acceptance is still NOT RUN. No new private
campaign directory, credentials, authorization timestamps or live window exists.
Retained runtime resources and private evidence were not accessed or changed.

## Fresh authorized window — admission blocked before deployment

User explicitly authorized scoped F1/F2, capture/probes, supervised off and
exclusive LD01 reuse with no overlapping worker/session. Receipt/controller UTC
`2026-10-20T10:25:44Z`; fixed hard stop `11:10:44Z`, cleanup by `11:00:44Z`, no
injection at/after `10:55:44Z`. Reconnects cannot extend this window.

Metadata-only preflight command:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 /tmp/opencode/n2-live-preflight.py
```

**BLOCKED, exit 1 at the host capture-privilege check.** Source preflight completed
retained image/container/home/network/capability/mount/full-endpoint reconciliation,
idle-A/zombie and task collision checks. Read-only host/A/B snapshots and retained
VM task inventory were collected; no runtime mutation or deployment was attempted.
Current full endpoint metadata was compared with the prior successful controlled
run, not substituted for the missing earlier historical B8 baseline.

The script then failed on `sudo -n true`; `sudo -n -l` confirmed interactive
authentication is required. `/usr/bin/tcpdump` exists without file capabilities.
The planned scoped host capture cannot run through the implemented noninteractive
helper. No policy, capability, package or host authentication setting was changed.

Private 0700 directory `/tmp/opencode/n2-20261020T102544Z-approval/` retains 0600
`authorization.json`, metadata-only `retained-metadata.json` and
`admission-failure.json`. Baseline snapshots/hash inventories were held in the
preflight process and were not published after its exception; they are not
represented as a retained complete audit report. The separate failure record
preserves that distinction. No fresh PKI/profile or live-attempt directory exists.

**F1 NOT RUN; F2 NOT RUN.** No VPN, task server, forward, watcher or capture was
started, so no disconnect/cleanup action was needed. Retained LD01 resources,
historical private evidence and VM material were preserved; company material was
not accessed. Stop at this missing admission gate; no automatic retry. User-side
host sudo authentication and renewed instruction/window are needed before another
admission attempt.

## Fresh operator-launched window — historical launch handoff

The user authenticated sudo in their own terminal, but the agent's separate
noninteractive sudo context still required authentication. No privilege policy
was changed. The user then explicitly authorized a separate fresh 45-minute
window and elected to launch the existing controller from that terminal.

- Receipt/controller UTC: `2026-10-20T10:38:30Z`.
- Fixed hard stop: `2026-10-20T11:23:30Z`, including disconnect/cleanup.
- Cleanup starts by `11:13:30Z`; no injection at/after `11:08:30Z`.
- Same authorized F1/F2, scoped A-veth capture/probes, exclusive reuse and
  supervised abort/expiry off. One attempt per case, stop at unexpected failure;
  no automatic rerun. The earlier blocked admission remains preserved.
- New 0700/0600 approval/metadata/source-hash directory:
  `/tmp/opencode/n2-20261020T103830Z-approval/`.
- Reserved unused private attempt directory:
  `/tmp/opencode/n2-20261020T103830Z-attempt1`.

Exact operator command, from the N2 worktree:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py \
  --authorization /tmp/opencode/n2-20261020T103830Z-approval/authorization.json \
  --private-dir /tmp/opencode/n2-20261020T103830Z-attempt1
```

**At handoff: launch pending; F1/F2 NOT RUN.** The controller would perform current
reconciliation before deployment. The agent has prepared approval files only;
no new profile/PKI, runtime service, capture or connection was created here.

## Operator attempt 1 — FAIL before fault injection

The operator ran the exact command above from their authenticated terminal.
Private evidence: `/tmp/opencode/n2-20261020T103830Z-attempt1/` (0700/0600).
Task: `cvpnb76f5884442f`; started `2026-10-20T10:42:01.745910Z`, finished
`10:43:15.924575Z`, before the fixed `11:23:30Z` hard stop.

- Preflight and deployment succeeded; verified OpenVPN initialized in A.
- The first F1 positive-baseline shell probe then failed with **`joined shell exited`**.
  No `injected_at` exists; no fault observations or recovery cycle occurred.
  **F1 injection NOT RUN; F2 NOT RUN.** This is not a containment/recovery PASS.
- Root restoration recorded **PASS**, empty errors, release time
  `2026-10-20T10:42:53.617213Z`. Its resolver/routes/rules/filter/nat match baseline.
- Overall cleanup recorded **FAIL** at `10:43:02.516669Z` solely on
  `capture stop: unparsed capture header`; the supervisor retained failed teardown
  without retry and reported FAIL. Original failed records are preserved.
- Inspection proves the capture parser rejected a tcpdump shutdown **blank line**.
  The actual packet summary is 100 captured, 100 received, zero kernel drops.
  There is no nonblank malformed header in this capture.
- The primary worker exception cannot be recovered from existing evidence:
  `Shell.request()` noticed EOF but `close()` discarded collected stderr. This
  explains the loss of diagnostic detail, not which baseline check failed.
  Do not infer a DNS/service cause or claim that correcting the capture parser
  fixes the primary baseline failure.

### Read-only post-attempt audit

`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/opencode/n2-post-attempt-audit.py`
performed inspection only, with no restoration/redeployment/reconnection.
Private `post-attempt-audit.json`: **20 checks PASS**, no audit errors:

- Exact host/B routes/rules/resolver and retained A/B IDs/image/configuration/
  capabilities/mounts/full endpoints preserved.
- Exact A resolver/routes/rules/IPv4 filter/IPv6 filter/nat restored, with the
  root cleanup journal explicitly PASS and no remaining tunnel/active OpenVPN.
- Both task forwards and capture inactive; their ports closed. All five VM task
  units inactive and unit files removed; VM task ports closed.
- Executed source hashes still matched the pre-run approval manifest at audit
  time; private attempt permissions are 0700/0600.

**Residuals:** A retains new defunct watcher PID **1923** and OpenVPN PID **1944**,
both state-Z, parent PID 1, in addition to historical PIDs 1006/1037/1294/1325.
No container restart/recreation was performed. New root material/journals remain
at `/run/ld01-cvpnb76f5884442f` because overall cleanup did not PASS; the state file's
`prepared`/`a_material`/`deployed` flags remain true and are not evidence of an active
VPN. New VM audit/PKI/source directories remain at
`/var/lib/ld01-cvpn-cvpnb76f5884442f` and `/tmp/ld01-upload-cvpnb76f5884442f`.
No cleanup was rerun to delete these records.

Held host/B/A-direct sockets completed 10/9/8 consecutive acknowledgements,
respectively, with stable socket/server identity and zero errors/reconnects.
This covers only the short failed-baseline interval and the controlled non-VPN
path; it supplies no injected-fault continuity verdict.

### Offline corrections and evidence interpretation

Before editing, all four executed implementation/test files were hash-verified
and archived as private `source-at-run-*` files. Existing evidence and verdicts
were not rewritten.

1. `capture_rows()` now ignores whitespace-only separators; every nonblank
   unrecognized record still fails, as do packet/header count mismatches/drops.
2. On joined-shell EOF, the controller now saves bounded stderr, action, exit
   code and time in a fresh private 0600 `shell-failure-*.json` before raising.
   No private stderr is included in the terminal error message.
3. Two targeted regressions cover a real subprocess failure with private stderr
   retention and tcpdump blank-line handling while preserving malformed-header
   rejection. Full sandbox suite: **76 tests PASS in 16.382 seconds**; whitespace
   checks PASS. These patches have not been run live.

The corrected parser was applied **offline** to the retained capture. Private
`offline-capture-recheck.json` confirms all 100 headers are accounted for, zero
drops, a positive A-veth canary and no forbidden egress in the recorded protected
baseline interval. This does **not** change the original FAIL verdict, establish
fault blocking or prove the primary baseline is fixed.

### Next gate

Remain stopped. Primary baseline diagnosis needs the missing worker-level error;
another live attempt requires renewed scope/window authorization. Admission must
also explicitly reconcile the six now-disclosed zombies and retained A journals:
the current four-zombie baseline guard deliberately rejects this changed residual
set. Do not simply rerun the old command, clear resources, or weaken evidence to
obtain PASS. Spec remains `in-review`; fault acceptance remains NOT RUN.
