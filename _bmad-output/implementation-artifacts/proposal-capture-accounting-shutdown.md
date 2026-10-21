# Capture-accounting shutdown — offline fix proposal

- Date: 2026-10-21. Owner: OpenCode.
- Branch/worktree: `fix/n2-baseline-diagnostic`,
  `/home/rat/Git/termux-vm-n2-baseline-diagnostic`.
- Source: `243d1a9fa61e2ee47f8e3a9676efa7dce5bb9f9f`.
- Status: **approved; offline implementation and review completed**.
- User accepted the qualified diagnosis as the basis for this proposal. That
  acceptance does not authorize implementation, publication or runtime work.

## Evidence and confidence

The saved `baseline-dns-live-20261020T224500Z-attempt1` evidence independently
replays as 176 parsed headers / 176 processed / 180 received / zero kernel drops.
All five executed source/test hashes match the execution receipt and source
revision. The requested, identity-matched, non-forced completion receipt is valid;
the unchanged strict capture proof still rejects the counts.

Static inspection confirms the installed tcpdump/libpcap mechanism:

| Artifact | Observation |
|---|---|
| `/usr/bin/tcpdump`, 4.99.6-1 | SIGINT registration at `0x32dbb–0x32dc7` selects the handler at `0x35cf0`, which calls `pcap_breakloop()` at `0x35d30`. |
| `/usr/lib/x86_64-linux-gnu/libpcap.so.1.10.6`, 1.10.6-1ubuntu1.1 | Linux break handler at `0x8520` sets the break flag and wakes the reader. The ring reader checks that flag before packet callbacks and can return the break result with packets unread (`0xa5b5`, `0xa688–0xa74f`). |
| tcpdump live completion, `0x33620–0x33669` | Reports statistics, closes and exits without another read pass. |
| libpcap Linux statistics, `0x8a0b–0x8a4b` | Reads kernel `SOL_PACKET/PACKET_STATISTICS`; these receive/drop counts are separate from tcpdump's callback counter. |

Both installed binaries match package checksums. Available package logs place
these versions before the attempt and record no subsequent change. The attempt
did not pin executable/library hashes, resolved executable path or runtime backend;
the package history supports, but does not prove, historical binary identity.

The last saved packet is at `22:50:03.495495Z`. Both off-canary replies complete
around `03.816Z`; the stop marker's saved filesystem mtime is `03.818845Z` and the
completed statistics file's mtime is `03.849252Z`. Earlier short canary flows have
six recorded packets each; the final two have three each. An unread shutdown tail
is the leading historical explanation. The exact four packets and their times
cannot be recovered from these files. Filtering/direction rejection before a
callback is another reason the receive and processed counters can differ.

**Established defect boundary:** the stop handshake guarantees bounded process
retirement, not a drained capture. **Not established:** that the four unprocessed
packets were particular canary packets or harmless post-protection traffic.

## Proposed scope

Keep the existing privileged wrapper, unique stop request, registration, child
identity checks and completion receipt. Change the shared capture path so normal
controller stop and detached supervisor stop receive the same behavior:

1. Request tcpdump immediate delivery explicitly with `--immediate-mode`, retaining
   inbound A-veth scope, the exact filter, timestamps, text format and snaplen 96.
   `-l` remains stdout line buffering; it is not a capture-drain guarantee.
2. On a valid requested stop after readiness, allow a short, bounded accounting
   convergence phase while tcpdump continues reading. Use identity-checked SIGUSR1
   statistics from the existing child, not new sudo authority or another capture.
   Require fresh complete samples; stale, partial or missing output cannot show
   convergence. Repeated equal positive receive/processed counts with zero drops
   are a stop hint only, never the final acceptance result.
3. Finish through the existing identity-checked SIGINT/reap/escalation path. Record
   whether convergence completed or timed out. Timeout, expiry, premature exit,
   forced retirement or failed accounting cannot yield capture success, even if
   final counters happen to agree.
4. Distinguish progress samples from terminal statistics. Bind the final complete
   statistics block to post-interrupt completion; neither the first matching
   sample nor the last earlier complete sample can substitute for missing terminal
   statistics. Continue requiring exact final
   `parsed == captured == received > 0`, zero kernel/interface drops, positive
   interval canaries and unchanged underlay checks.

The convergence budget must fit inside the existing caller wait and fixed capture
expiry/cleanup reserve, leaving time for retirement. Start with at most two seconds
and shorten/skip it when retirement needs the remaining budget. Do not extend
authorization, wait indefinitely for quiet traffic or retry teardown. A packet
arriving between a progress sample and interruption must still cause FAIL if it
leaves the final counts unequal. This proposal reduces the shutdown race; it does
not promise every future run will satisfy strict acceptance.

Implementation must resolve the statistics plumbing before editing: inspect the
installed SIGUSR1 output format, keep progress and terminal blocks unambiguous,
and use the wrapper's already-owned streams or validated descriptors without
introducing arbitrary privileged path reads. If this cannot fit the existing
wrapper safely and narrowly, stop and revise the proposal with the user.

## Files and verification

Expected implementation is confined to
`_bmad-output/linux-docker-trial/controlled-vpn/trial.py` and `test_trial.py`, with
a redacted completion note after authorization. No fixture/server change or new
dependency is proposed. Relevant shared callers are `baseline()`, `cycle()` and
`cleanup_owned()`; all route through `stop_capture_owned()` and `CAPTURE`.

Extend the existing ordinary-user disposable-worker harness to exercise:

- A delayed synthetic receive tail converges before requested interruption.
- Late arrivals after apparent convergence still fail final strict equality.
- Progress equality cannot mask terminal mismatch, drops or missing statistics.
- Missing/stale/partial progress, continuous arrivals and convergence timeout stay
  bounded and fail closed; expiry never acquires a successful requested verdict.
- Controller-loss supervisor uses the same stop path without shutdown-time sudo.
- Registration/command drift, gate, premature-exit, forced-stop and clock-rollback
  guards remain effective. Historical-shaped 176/180/0 evidence still fails.

These checks prove implementation behavior under controlled synthetic conditions,
not the historical packet identities or live capture acceptance. Offline tests may
use disposable ordinary-user workers and files only after implementation approval;
no real packet capture or Docker/GCP/VPN operations are included.

## Preserved dispositions and approval gate

- This attempt remains **baseline FAIL / cleanup FAIL**. Its A-restoration PASS is
  narrower; no `cleaned.json` is manufactured. Earlier **baseline FAIL / cleanup
  PASS** and all other historical verdicts remain separate and unchanged.
- Preserve private evidence and the current uncommitted owner/result updates and
  existing untracked files. Do not retry cleanup, alter retained resources, start
  containers, recreate scratch, adopt a reference or launch an attempt.
- Stopped A/B and missing scratch remain separate runtime blockers. No future live
  permission, execution window, commit, push, PR or merge is implied here.

**Requested next authorization:** implement and verify this scoped change offline
only. Until explicitly approved, this document is the sole new task artifact.

## Subsequent authorization and completion

The user explicitly approved implementation and verification, then confirmed
continuing in the existing dirty worktree while preserving its prior files.
Offline implementation/review is recorded in
[spec-capture-accounting-shutdown.md](spec-capture-accounting-shutdown.md):
**124 tests PASS**, independent review corrections verified. This supersedes the
proposal's pending-implementation gate only; runtime/publication gates and
historical verdicts remain unchanged.
