# VPN-stage input resolution and current-material checks

Date: 2026-10-19. Continues [execution-results.md](execution-results.md); its LD01-T/LD01-F passes remain the completed baseline, not VPN acceptance.

## Human decisions recorded

- **Owner cleared scoped reuse:** user relayed the original evaluation owner's clearance to read the existing export/four staged credential files, produce a separate private adapted config and mount files read-only into A. No original file/resource modification or ownership transfer was requested or authorized.
- **Authorize scoped VPN stage:** user authorized current readability/expiry checks and private adaptation, and conditionally approved recreating A with its existing home/network/project, read-only credential mount, and SETUID/SETGID in addition to NET_ADMIN for OpenVPN privilege dropping. Both daily shells remain non-root. Connection/disconnection remains conditional on resolved policy and targets.
- **Approved single-session window:** selected, but no actual time/window or confirmation of absent conflicting sessions supplied. This does not establish concurrent-session permission.
- **Targets not available yet:** private service/FQDN/expected DNS, VPN-bound prefixes, routing/IPv6 policy and controlled external TCP heartbeat target remain missing.

## Focused proof scope

Check only the five known staged files' current type, ownership/mode and actual openability, plus CA/client certificate expiry. Do not repeat prior certificate/key-match, chain/purpose, private-key integrity or TLS-crypt-format validation. Do not print key/token contents or certificate identity. Store detailed current results privately outside Git and publish only the bounded summary here.

Installed OpenVPN 2.6.19 help confirms `--user`/`--group` drop identity after initialization, `--down` normally runs after that drop, and the available PID/management/up/down options. This is option documentation, not proof that resolver lifecycle or privilege dropping works. The help invocation returned 1 (normal for this binary's help); it did not start a VPN.

## Current result

**PASS — bounded material readiness**, checked `2026-10-19T15:38:37Z`. Private evidence: `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/vpn-material-readiness-20261019T153837288224Z.json`, mode 0600.

| Check | Result | Limit |
|---|---|---|
| Staging directory | PASS | Real directory, current-user owned, 0700. |
| Export plus four staged files | PASS | Regular files, UID 1001, 0600; opened read-only with `O_NOFOLLOW` and zero bytes read for the openability check. This is host-user access, not the container daemon identity. |
| CA expiry | PASS | `openssl x509 -noout -enddate -checkend 0` exited 0; notAfter 2030-03-14. No repeated chain/purpose/key checks. |
| Client certificate expiry | PASS | Same command exited 0; notAfter 2027-06-23. No server acceptance/revocation/concurrency proof. |

The verification command emitted only status/counts and the private evidence path; certificate checks retained expiry-only output privately. No profile/key contents were emitted or keys inspected again. No configuration adaptation, A recreation, credential mount or connection has run in this continuation. Existing LD01 containers/capabilities remain the original baseline configuration.

## Inputs needed before connection

1. Supply the single-session test window, timezone and confirmation that conflicting sessions using this certificate will be absent. A current local inactive NetworkManager VPN alone cannot prove no session on another machine. This agent will not toggle the host VPN.
2. Supply an approved private service/FQDN and expected answer, VPN-bound prefixes, full/split policy and IPv6 routing/blocking policy. If company-private DNS does not exist, state that explicitly; a fixture would prove only its mechanism.
3. Supply a controlled external TCP heartbeat endpoint/protocol usable by host and B over held same sockets, plus approved new-connection/capture targets. Prior public TCP probes do not provide that endpoint or establish continuity.
4. Finalize the private config's resolver integration and connect/disconnect controls against the above policy. Preserve existing TLS/server verification and explicit SHA256; map approved file paths and privilege-drop identity. Verify readability from the actual daemon identity/capability set: current-user host openability does not establish that a capability-restricted root daemon can read UID-1001-owned 0600 bind mounts. Receiving DNS options or having a service account is not proof of working DNS recovery.

Stop after the scoped checks while these inputs are missing. Keep LD01-J/LD01-C and S1–N3 VPN/account checks BLOCKED/NOT RUN, retaining their exact limits; no rerun of the successful foundation/baseline is needed solely for input resolution.

## Prior continuation verification

- PASS: seven Markdown artifacts, 27 local/file link targets, whitespace/final newlines and the bounded five-file/two-certificate private evidence record checked; evidence file mode is 0600.
- PASS, read-only runtime comparison: existing A/B container IDs, image IDs, capability grants and destination-keyed mount metadata match the final baseline. An initial order-sensitive mount-list comparison flagged apparent drift; follow-up inspections demonstrated Docker can reorder the mount array while the full destination-keyed mount entries remain identical. No actual configuration drift was observed. No container mutation or baseline probe rerun was needed.
- BLOCKED: connection until actual window/conflicting-session confirmation, targets/policy and daemon/resolver/control configuration are supplied. No original private key content, profile details or company endpoint was emitted. No commit/push/PR requested or performed.

## Fresh continuation from origin/main — 2026-10-19

- Owner/branch/worktree: [task-owner.md](../task-owner.md); `docs/vpn-trial-continuation`, `/tmp/opencode/termux-vm-vpn-trial-continuation`, based on `origin/main` at `8bd49ab74adcfcfb0917f20dab78ee8059b2aba5`.
- **Retained LD01 reuse coordinated:** user relayed the prior Linux Docker trial owner's acknowledgement for exclusive continuation reuse of the recorded LD01 image, A/B containers, homes, networks and private scratch/evidence directory, with no overlapping runtime or artifact edits. Existing resource labels stay unchanged; this is not ownership transfer or expanded access to the original evaluation resources/staging.
- **Execution remains BLOCKED/NOT RUN.** All four inputs under “Inputs needed before connection” remain unresolved. Reuse acknowledgement supplies no test window, conflict confirmation, target/policy or private configuration decision.
- **Resume boundary:** resolve those inputs, then reconcile exact retained resource IDs, image, capabilities and destination-keyed mounts against the private final baseline before runtime changes. Recheck active host VPN/session state immediately before an approved connection, alongside the supplied conflicting-session confirmation. Follow the existing scoped A-only diagnostic; keep both ordinary shells non-root and preserve the original material/TLS policy.
- This session performed handoff/coordination work only. No runtime inventory, baseline probe, credential check, config adaptation, credential mount, container recreation or VPN connection was run. Prior material-readiness and runtime-comparison passes above are historical, not fresh verification. LD01-J/LD01-C and S1–N3 VPN/account checks remain **BLOCKED/NOT RUN**.

### Subsequent immediate-start approval

User stated “you can start the vpn now, I approve”. This records permission to start now, but supplies no window duration, confirmation of absent conflicting certificate sessions, approved targets or routing/IPv6 policy. Those inputs remain needed; daemon-readable credentials, resolver integration and connect/disconnect controls still require implementation and verification. VPN has not been started; LD01-J/LD01-C and S1–N3 VPN/account checks remain **BLOCKED/NOT RUN**.

### Window/conflicting-session input resolved

User subsequently confirmed that no other session uses the certificate and authorized as long as needed, maximum three hours. Recorded at `2026-10-19T16:19:16Z`; hard stop no later than `2026-10-19T19:19:16Z` UTC, including disconnect/cleanup. Delaying connection does not move this deadline. Recheck current host VPN/session state immediately before connection; request a new window if this one expires.

User asked for a routing-policy recommendation and how to obtain targets. Approved private service/DNS/expected answer, VPN prefixes, full/split and IPv6 policy, controlled external heartbeat endpoint/protocol and approved observation targets remain unresolved. Configuration/readability/resolver/control work remains pending those decisions. No VPN connection has run; LD01-J/LD01-C and S1–N3 VPN/account checks remain **BLOCKED/NOT RUN**.

### Current direction — separate controlled VPN on GCP

The user subsequently instructed **not to use the company VPN** and supplied GCP VM `free-vm`, accessible using `gcloud compute ssh free-vm --tunnel-through-iap`. The new goal is a separate VPN instance that provides a client configuration file and access to internal test services. This supersedes the earlier company-connection authorization; do not use its certificate or staged profile. Historical missing company inputs above are not requirements to obtain company access for the new lab.

The proposed controlled OpenVPN fixture would use fresh lab credentials and its own internal service/DNS and external heartbeat targets. Server access, GCP networking/permissions, route/IPv6 policy, resolver/control integration and usable targets still need investigation and implementation. The VM has not been inspected, no cloud resources or VPN configuration have been changed, and no local VM requirement has been established. The old company-session deadline does not restart or authorize a future run.

Retained LD01 reuse acknowledgement remains scoped as recorded above. Preserve existing labels and reconcile the exact retained baseline before runtime changes. The fixture, if implemented and tested, would prove only the controlled setup's mechanism; it would not establish company-server acceptance, company DNS/routing compatibility or account-sharing acceptance. No new trial result is claimed.

User requested committing/pushing the existing handoff work and opening a PR before proceeding with implementation. This branch records coordination and the changed scope only; controlled VPN setup remains follow-on work.

### Controlled lab planning after merged PR #3

The user confirmed the handoff PR was merged. Fetched `origin/main` at `7e37565174b54105293c75c214c0b8b97202ff21` contains it; a clean `feat/controlled-vpn-trial` worktree was created. Current ownership and scope are at [task-owner.md](../task-owner.md), with the [draft implementation spec](../implementation-artifacts/spec-controlled-vpn-trial.md).

Read-only IAP inspection confirms Debian 12, sudo/TUN availability and observed capacity for a small stock-client fixture. The VM has public IPv6 and no public IPv4; its network currently allows IAP SSH only. LD01 A/B remain running on the frozen image with their recorded mount layout and baseline capabilities; full private-evidence reconciliation is still required before mutation. A host IPv6 route exists, but the retained Docker networks are IPv4-only.

Proposed transport is controller-managed IAP/SSH TCP forwarding, avoiding a new public IPv4/ingress rule. The generated client profile requires the forward; this is not a portable public-endpoint profile or native UDP test. A local VM is not required for this proposal. Approval of the draft spec is pending; no server/client configuration, packages, credentials, firewall rules or VPN connections have been changed. No company material was accessed.

### Controlled lab implemented and exercised — 2026-10-19 UTC

The planning checkpoint above is historical. The user approved the controlled spec
and execution at `2026-10-19T21:43:21Z`, with a fixed maximum-three-hour deadline
`2026-10-20T00:43:21Z`. [Controlled results](controlled-vpn-results.md) record
implementation, the exact invocation, private evidence and resource disposition.

**Historical observed PASS — original controlled IPv4 OpenVPN/IAP run and cleanup only.** Execution ran
`21:53:15Z`–`21:54:56Z`; both persistent UID/GID-1001 A shells resolved
`service.ld01.test` and reached the fixture in both controller-mediated cycles.
Host/B could not reach the private services directly. Their held heartbeat sockets
retained their identities with 43/42 sequenced acknowledgements and no reconnects
or errors; host/B route/rule/resolver state stayed unchanged.

Actual client/server versions are OpenVPN 2.6.19/2.6.14; server DNS is dnsmasq 2.90.
Fresh lab PKI verifies exact TLS peer names with explicit SHA256. A's daemon is
root with only its existing NET_ADMIN capability; actual material access and
running capabilities were checked. No A recreation or SETUID/SETGID additions were
needed. A-only scoped IPv6 traffic blocking and port-53 DNS restrictions accompany
the lab resolver. Exact A resolver/routes/rules/IPv6 state restored on both stops;
task forwards, client material and task VM services were cleaned up.

Private profile: `/tmp/opencode/controlled-vpn-20261019T2153Z/client.ovpn` (0600,
parent 0700). It requires controller-managed forwarding/lifecycle, and the task
services are stopped now. VM packages, private PKI/config/audit/rollback and source
upload were retained as listed in results. The original source passed nine regression
checks, Bash syntax and whitespace checks. No company credentials, profile or staging were accessed.

Historical company material-readiness checks are not controlled-lab prerequisites
or new acceptance. Company/native-UDP/full-tunnel/live-IPv6/account/S1–N3 tests
remain **NOT RUN**; LD01-J/LD01-C company/account acceptance remains unestablished.
The IAP heartbeat proves only that controlled non-VPN path, and controller actions
do not prove restricted daily connect/disconnect permissions.

### Historical review-fix checkpoint — before fresh authorization

Independent review completed with logged findings and source fixes. It is not
pending. The original fixed `2026-10-20T00:43:21Z` deadline expired; at this checkpoint
patched-source live validation and both repeat cycles required a fresh explicit
window. That blocker is resolved by the separately authorized run below. Coordinating offline verification completed at
`2026-10-20T07:25Z`: all 31 sandbox tests, Bash syntax and tracked/untracked
whitespace checks passed. Any live repeat requires new authorization. This patch performs no deployment, reconnection,
runtime mutation or rewrite of original evidence/deployed copies.

Source fixes cover retryable cleanup with retained failed-attempt evidence/journals
and explicit restoration PASS before material deletion; independent resolver
recovery despite netfilter failures; shared/cancelled/bounded server setup/rollback;
generation-locked A actions, atomically registered/gated daemon and forward startup,
explicit watcher retirement/join, independent lease renewal and zombie detection.
Thirty-one focused sandbox tests and Bash syntax pass, including automatic watcher
triggers, race/deadline guards, TERM-to-KILL escalation and tunnel deletion.

Review confirmed the original destination-port-53 filter can be bypassed by Docker
embedded-resolver DNAT to high ports. Revised source matches the original conntrack
DNS tuple and preserves prior filter/nat rule configuration. Future connected
checks include explicit UDP **and TCP** embedded-resolver negatives alongside
working lab DNS, plus TCP DNS negatives on host/B. These had **not run at the
offline checkpoint**; the fresh run below now provides the added live observations.

B8 historical endpoint drift comparison is **deferred, medium/unverified**: the
retained baseline lacks original endpoint IP/MAC/gateway values. Current endpoint
snapshots cannot create that historical baseline. Existing packages/private lab
material/evidence and last observed resource disposition are retained as recorded
in [controlled results](controlled-vpn-results.md); the later fresh disposition follows.

### Fresh revised-source live verification — 2026-10-20 UTC

**PASS — both revised-source cycles and scoped cleanup**, with explicit defunct-PID
residuals below. User receipt `2026-10-20T07:31:09Z`; fixed hard stop
`2026-10-20T10:31:09Z` including cleanup. All 31 sandbox regressions and Bash
syntax passed before deployment with `PYTHONDONTWRITEBYTECODE=1`. Original retained
A/B resources reconciled, including exact comparison with the original controlled
live run's full endpoints. No source/context drift or overlapping controller was
observed; no original task listener/daemon/tunnel/unit remained.

Exact live invocation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py \
  --private-dir /tmp/opencode/controlled-vpn-20261020T0736Z-attempt1
```

Exit 0, task `cvpn152283967635`; started `07:34:59.838456Z`, finished
`07:36:40.236169Z`; cleanup PASS at `07:36:31.392240Z`. Cycle 1:
`07:35:49.989077Z`–`07:36:07.179645Z`; cycle 2:
`07:36:07.179675Z`–`07:36:24.377179Z`. Both same UID/GID-1001 joined shells passed
private DNS/HTTP in each cycle. Explicit embedded-resolver UDP/TCP negatives passed
while lab DNS worked. Host/B HTTP and UDP/TCP DNS negatives passed. Held host/B
sockets retained identity with **53/52 acknowledgements**, zero reconnects/errors.
Exact A resolver/routes/rules/filter/nat/IPv6 state restored after each stop;
host/B state and all retained container configuration/endpoints stayed unchanged.

New private profile: `/tmp/opencode/controlled-vpn-20261020T0736Z-attempt1/client.ovpn`;
same directory contains evidence, cleanup/rollback state, logs and post-run audits.
Directory 0700, files 0600. Fresh profile and CA differ from the original lab;
the original profile/evidence hashes and old VM rollback hash/mtime are preserved.
No trial implementation correction, failed live connection/deployment, or live
repeat was needed. No company material or live fault injection was used.

Audit dispositions remain private and are fully listed in controlled results:
an initial preflight audit self-matched its inspection command (FAIL), corrected
preflight passed, the live run passed, a post-audit's name-only check flagged dead
OpenVPN entries (FAIL), then a state-aware post-audit passed all 19 checks.
Both failed audit records are retained; acceptance was not weakened.

No active task VPN/watcher/forward/tunnel/VM listener/unit remains; A material and
task unit files were removed. **Residuals:** four A entries in state Z, all parent
PID 1: watcher PIDs 1006/1294 and OpenVPN PIDs 1037/1325. They are terminated,
without live sockets/tunnels, and unreaped by A's unchanged `sleep infinity` PID 1.
No restart/recreation was performed. Retained VM lab directories are
`/var/lib/ld01-cvpn-cvpn7a1a8819b397`, `/var/lib/ld01-cvpn-cvpn152283967635`,
`/tmp/ld01-upload-cvpn7a1a8819b397`, `/tmp/ld01-upload-cvpn152283967635`.
Six original native packages, their managed directories and apt/dpkg state remain;
this run changed zero package versions. New upload is cancelled; old scripts are
unchanged. Exact directories and inventory are in [controlled results](controlled-vpn-results.md).

The execution blocker is resolved. Coordinating evidence verification passed via
`python3 /tmp/opencode/controlled-vpn-final-proof.py`; spec is `done`. The proof
checks raw cycle/socket/audit evidence, cleanup/deadline, private permissions and
unchanged current implementation/original-evidence hashes. B8 historical endpoint comparison remains deferred/unverified:
the newer full-endpoint comparison does not manufacture the missing earlier
baseline. Company/native-UDP/full-tunnel/live-IPv6/account/S1–N3 and restricted
daily-control acceptance remain unclaimed; heartbeat scope is the controlled
IAP-forwarded non-VPN path only. No commit/push/PR was performed.
