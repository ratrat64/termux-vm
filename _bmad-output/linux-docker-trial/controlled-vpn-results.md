# Controlled OpenVPN lab — execution results

**Current result: revised-source live trial PASS; cleanup PASS, with four defunct A child entries retained.**
Fresh receipt `2026-10-20T07:31:09Z`; fixed hard stop `2026-10-20T10:31:09Z`.
Both cycles, added DNS negatives and same-socket continuity passed; cleanup finished
`07:36:31.392240Z`. Coordinating verification passed; spec is `done`.
Exact invocation, audit dispositions and residuals are in “Fresh authorized revised-source run” below.

**Historical observed PASS — original controlled IPv4/IAP run.** Executed on 2026-10-19 UTC in
`feat/controlled-vpn-trial`, worktree `/tmp/opencode/termux-vm-controlled-vpn-trial`.
Implementation: [controlled-vpn/](controlled-vpn/); approved intent:
[spec-controlled-vpn-trial.md](../implementation-artifacts/spec-controlled-vpn-trial.md).

The original `2026-10-20T00:43:21Z` window expired. Its evidence and rollback
scripts are preserved. Independent review and the offline source patch preceded
the separate fresh authorization/run documented below; original observations
are not substituted for revised-source live verification.

## Invocation and private outputs

From the designated worktree, the exact live command was:

```bash
python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py \
  --private-dir /tmp/opencode/controlled-vpn-20261019T2153Z
```

It returned exit 0 and `PASS: /tmp/opencode/controlled-vpn-20261019T2153Z/evidence.json`.
Started `2026-10-19T21:53:15.538918Z`; finished `2026-10-19T21:54:56.712677Z`.
Scoped cleanup finished `2026-10-19T21:54:47.595581Z`, before the fixed approval
hard stop `2026-10-20T00:43:21Z` (approval receipt `2026-10-19T21:43:21Z`).
That original run used its fixed deadline; the fresh authorization below supplied
a separate deadline. Reconnecting never extends either window.

- **Private client profile:** `/tmp/opencode/controlled-vpn-20261019T2153Z/client.ovpn`.
- **Private evidence/rollback state:** the same directory's `evidence.json`,
  `state.json`, `cleaned.json`, `host-heartbeat.jsonl`, `b-heartbeat.jsonl`,
  `server-openvpn.log`, setup/forward/watchdog logs. No profile or key is logged.
- Directory mode verified 0700; all immediate files verified 0600. No secrets or
  raw/private evidence are in the worktree.
- VM task: `cvpn7a1a8819b397`, on the supplied `free-vm` through IAP SSH.
  VM-private PKI/config/audit/rollback directory:
  `/var/lib/ld01-cvpn-cvpn7a1a8819b397` (root-owned 0700; files 0600,
  `rollback.sh` 0700). Source-only upload:
  `/tmp/ld01-upload-cvpn7a1a8819b397` (0700, files 0600).

The profile **requires the controller's SSH forward and resolver/IPv6 lifecycle**.
It is not a standalone public-endpoint profile. The services and forwards are
stopped now; importing the retained profile alone does not provide access.

## Original run: transport, versions and observed policy

- Frozen LD01 client: **OpenVPN 2.6.19**, image
  `sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050`.
  No image rebuild or container recreation was needed.
- Native Debian 12 VM packages: **OpenVPN 2.6.14**
  (`2.6.14-0+deb12u2`), **dnsmasq 2.90** (`2.90-4~deb12u2`). The
  `dnsmasq-base` package supplies the binary without a global dnsmasq service.
- Fresh, two-day lab CA/server/client certificates, RSA-2048/SHA256 and fresh
  TLS-crypt material. Both peers verify certificate purpose and exact peer name;
  client requires `lab.ld01.test`, server requires `ld01-lab-client`.
  Explicit `auth SHA256`; observed TLS 1.3 and AES-256-GCM data channel.
- Collision-checked split subnet `10.231.0.0/24`, server `10.231.0.1`, client
  `10.231.0.2`. No default-route or unrelated IPv4-route changes in A.
- OpenVPN listens only at VM `127.0.0.1:11940`; HTTP only at
  `10.231.0.1:8080`; DNS TCP/UDP only at `10.231.0.1:53`; heartbeat only at
  VM `127.0.0.1:19090`. No cloud firewall/public-ingress/IPv4 allocation changes.
- VPN SSH transport forwards `172.16.0.33:20990` to VM `127.0.0.1:11940`.
  A **separate SSH transport** forwards `127.0.0.1:20991` and LD01 B's
  bridge `172.16.0.49:20991` to VM `127.0.0.1:19090`. Both use
  `gcloud compute ssh free-vm --tunnel-through-iap`, `-N -T`,
  `ControlMaster=no`, `ControlPath=none`, `ExitOnForwardFailure=yes`, and bounded
  SSH keepalives. No SSH key, agent or host socket enters either container.
- While connected, A's resolver contains only `10.231.0.1`; A-only scoped
  filter rules attempted to reject other TCP/UDP port-53 destinations. Review
  confirmed Docker's embedded-resolver DNAT to high ports bypasses that original
  destination-port match; the original run did not establish embedded-resolver
  exclusion. Revised source matches conntrack's original DNS destination/port;
  the fresh run below now verifies that fix. The lab resolver
  serves the private zone and uses the VM's existing resolver for other names.
- IPv6 **traffic is disabled by A-only INPUT/OUTPUT/FORWARD drop rules**. Docker's
  `/proc/sys` is read-only, so no sysctl remount or host change was needed.
  IPv6 sysctl values remain unchanged; the rules and temporary tunnel IPv6
  addresses/routes are removed on stop. Live IPv6 connectivity is **NOT RUN**.
- OpenVPN starts as root with **only NET_ADMIN** (`CapEff=0x1000`),
  `NoNewPrivs=1`. Its root-owned 0600 inline profile was actually opened under
  this identity/capability set, and the running daemon's capabilities were checked.
  No privilege-drop account or SETUID/SETGID grants were needed. Daily shells
  remain UID/GID 1001 with zero effective capabilities; B remains capability-free.

## Acceptance evidence

| Check | Result and evidence |
|---|---|
| Ownership/config reconciliation | PASS before deployment: immutable image, retained A/B IDs, labels, limits, capabilities, devices, exact destination-keyed mounts, network IDs/IPAM/peers and home-volume ownership. Full preflight retained privately. |
| Joined shells | PASS: persistent Bash shell PIDs 306 and 307, RPC worker PIDs 318 and 319; both UID/GID 1001 in `net:[4026533548]`. |
| Cycle 1 | PASS, `21:54:13.676621Z`–`21:54:27.023476Z`: A1 requests controller connect; A1/A2 both resolve the private name and receive the exact fixture identity; A2 requests controller disconnect. |
| Cycle 2 | PASS, `21:54:27.023525Z`–`21:54:40.441994Z`: A2 requests controller reconnect; the same A1/A2 shells both pass DNS/HTTP; A1 requests controller disconnect. |
| Private DNS/HTTP | All four shell probes return `service.ld01.test = 10.231.0.1` and `{"fixture":"cvpn7a1a8819b397","service":"service.ld01.test"}`. `dig` identifies `10.231.0.1#53` as resolver. TLS exact-name verification and initialization are in private daemon logs for both cycles. |
| Host/B negative access | Historical PASS in both cycles: direct private HTTP connection and UDP DNS response unavailable from host and B. TCP DNS negatives were omitted then and are verified separately in the fresh run below. |
| Host/B continuity | PASS: host 43 sequenced acknowledgements, B 42, each on one held socket with unchanged local/peer/inode and server-generated connection ID. Zero reconnects/errors. Both sockets span preparation and both cycles. |
| Host/B unaffected | PASS during both cycles and afterward: host/B IPv4/IPv6 routes, rules and exact resolver bytes unchanged; host resolved DNS/domains and NetworkManager connection types/states unchanged. Only RA `expires` countdowns are normalized. Retained A/B Config/HostConfig/NetworkSettings and destination-keyed mounts compare equal afterward. |
| A restoration | PASS after each disconnect: exact resolver bytes, original IPv4/IPv6 routes/rules, IPv4/IPv6 filter policies/rules and IPv6 sysctl values restored; task daemon/tunnel gone. Final scoped root material removed. |
| Final cleanup | PASS, empty cleanup-error list; local task listeners closed, no loaded task VM units or task VM listeners; post-cleanup A check confirms no lab directory, tunnel or OpenVPN process. |

These are **controller-mediated** connect/disconnect requests from the joined
shells, not proof that ordinary users have restricted daily VPN administration.
The continuity verdict covers the controlled **IAP-forwarded non-VPN path** only;
it does not establish arbitrary Internet-flow continuity.

## Regression and source checks

```bash
python3 -m unittest discover -s _bmad-output/linux-docker-trial/controlled-vpn -p 'test_*.py' -v
bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh
git diff --check
```

For the original source, **nine regression checks passed**, plus Bash syntax and diff whitespace checks.
Tests cover identity/capability/mount/limit/ownership drift, mount-order tolerance,
expired-window rejection before deployment, occupied-port rejection, failed-startup
restoration through the actual root agent against a private filesystem/netfilter
transport, guaranteed controller restoration, cleanup failure blocking PASS,
real fixture socket identity/sequence, and sequence-gap rejection. Failure tests
are synthetic; no live fault injection occurred.

Matrix coverage: preflight mismatch → rejection regressions; connection → the
two successful TLS/DNS/HTTP live cycles; stop/failure → both live disconnects plus
startup/restoration/cleanup-failure regressions; continuity → real fixture test,
gap-rejection regression and the two held live sockets.

The original implementation armed A/controller watchdogs and VM `RuntimeMaxSec`.
Review found cleanup retry, lifecycle races, late deployment and lease gaps in
those paths. Revised behavior is covered by the sandbox checks below; the original
normal-disconnect observation is not proof of automatic failure handling.
No live fault injection was performed.

## Independent review fixes — historical offline checkpoint

Independent review is finished and its findings are logged in the spec's triage
log. Coordinating offline verification completed at `2026-10-20T07:25Z`: all 31
sandbox regressions, Bash syntax and tracked/untracked whitespace checks passed.
Live acceptance was blocked at that checkpoint; the fresh authorization/run below
resolves that execution blocker without reusing the expired window.

- Cleanup caches only PASS, preserves each failed attempt and rollback journal,
  and archives A rollback evidence before deleting material. Deletion requires an
  explicit restoration PASS. Firewall inspections/deletions, resolver recovery
  and each restoration comparison are attempted independently, including after
  a netfilter timeout.
- Server setup/rollback share the source-upload lifecycle lock. Rollback publishes
  cancellation before waiting for setup termination; late setup cannot proceed.
  A server-side timeout bounds the whole setup, with positive cleanup-reserve
  checks before unit creation/start. The fixed deadline is unchanged.
- A prepare/block/start/restore use one lifecycle lock and generation checks.
  Daemon/watcher children wait behind a pipe gate until their PID identity is
  atomically recorded. Watchers are generation-bound, cancelled, and explicitly
  joined before material deletion or the next cycle. Cancelled startup is rejected.
- Lease renewal runs independently during controller work and stops before
  cleanup. Controller/deadline detection remains independent; zombies count as
  dead rather than retaining an apparently live controller identity.
- SSH forwarding children receive their exec gate only after fsynced registration;
  EOF before registration cancels the child without starting SSH.
- DNS restrictions match conntrack's **original** TCP/UDP destination port/address,
  covering Docker's embedded-resolver high-port DNAT. Prior filter and nat rule
  configuration is compared across restoration. Future connected cycles now
  include explicit embedded-resolver UDP/TCP negatives as well as working lab DNS;
  host/B negatives now include TCP DNS.

Focused checks for the edited implementation: **31 sandbox tests passed** and
`bash -n` passed. Invocation:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s _bmad-output/linux-docker-trial/controlled-vpn -p test_trial.py -v
bash -n _bmad-output/linux-docker-trial/controlled-vpn/setup-server.sh
```

These checks exercise healthy and triggered watchdogs, controller loss/deadline
cleanup, independent lease renewal, lifecycle serialization/generation rejection,
retryable failed cleanup/journal retention, TERM-ignoring task-child KILL escalation,
sandbox tunnel deletion, real held-socket later-reply corruption, forward gates,
and server cancellation/timeout/reserve guards. They never mutate Docker or GCP.

Dispositions at that checkpoint (superseded by the fresh run where stated):

- **Former execution blocker, now resolved:** patched-source live validation and
  both repeat live cycles required a fresh explicit window. The user supplied it
  at `2026-10-20T07:31:09Z`; exact new results follow below.
- **Offline verification complete:** coordinator confirmed all 31 sandbox tests,
  Bash syntax, tracked/untracked whitespace and untracked secret-marker checks.
  Generated test bytecode was removed. Independent review is complete.
- **B8 deferred, medium/unverified:** historical endpoint IP/MAC/gateway drift
  comparison needs authoritative original endpoint evidence. Original baseline
  files omit those fields; the original run's current snapshot supplies no missing
  historical baseline. See [deferred work](../implementation-artifacts/deferred-work.md).
- **Retained:** the original private profile/evidence, VM packages, root-private
  PKI/config/log/rollback and source upload below. This source patch does not update
  the retained deployed scripts or re-inspect runtime disposition.

## Last observed resource disposition and remaining scope

The following disposition was observed after the original run. This patch leaves
it untouched and does not claim a fresh runtime inspection.

- Original A ID remains
  `3aca8c213551fa528142eb38b69990e797135e2d4d13b3273e44ecee6857e32b`;
  B remains `99f9f43eb98c3a4c8be3d96c59d77b9ddb5296841fd9b93d5062f9b8e48c0abd`.
  Both remain running, with the original homes, project, networks, labels,
  limits and capabilities. No replacement identity exists.
- All four `ld01-cvpn7a1a8819b397-{vpn,http,dns,heartbeat}.service` units were
  stopped and their task unit files removed. No task server tunnel/listener,
  local task forward or client daemon remains active.
- VM packages are **retained**: `openvpn`, `dnsmasq-base`, `libjansson4`,
  `liblzo2-2`, `libnftables1`, `libpkcs11-helper1`; no pre-existing package was
  removed/replaced. Package-managed files/default OpenVPN service scaffolding
  and apt metadata remain. The package's default `openvpn.service` is
  `active (exited)`, `ExecStart=/bin/true`, with no VPN process/listener.
  Rollback removes task services, not package state.
- VM root-only lab PKI/config/log/rollback directory and source-only upload are
  intentionally retained for evidence/rollback. Local private profile/evidence
  remains at the path above. The VM scoped rollback command is
  `sudo bash /var/lib/ld01-cvpn-cvpn7a1a8819b397/rollback.sh`; it stops/removes only
  that task's units and retains its audit material. It has already run successfully.
- No new VM, paid IPv4, public VPN ingress, host VPN/resolver/daemon changes,
  company material access or unrelated workload mutation was performed.
- This historical disposition does not cover later source changes. Company VPN compatibility, native UDP,
  full tunnel, live IPv6, account logins/sharing and S1–N3 acceptance remain
  **NOT RUN**. LD01-J/LD01-C company/account acceptance is not promoted by this lab.
- Independent review and coordinating offline verification completed with logged
  fixes; the newly authorized repeat live trial is recorded below. Spec status is `in-review`.
- No commit, push, PR, merge, tag or VCS remote change was requested/performed.

## Fresh authorized revised-source run — 2026-10-20 UTC

**PASS, exit 0; two cycles PASS; scoped cleanup PASS.** User receipt
`2026-10-20T07:31:09Z`, fixed hard stop `2026-10-20T10:31:09Z`, including cleanup.
Controller, A agent and server guards use that deadline. No reconnect extended it.

From `/tmp/opencode/termux-vm-controlled-vpn-trial`:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/controlled-vpn/trial.py \
  --private-dir /tmp/opencode/controlled-vpn-20261020T0736Z-attempt1
```

- Started `2026-10-20T07:34:59.838456Z`; finished `2026-10-20T07:36:40.236169Z`.
  Cleanup completed `2026-10-20T07:36:31.392240Z`, well before the hard stop.
- Fresh task `cvpn152283967635`; fresh CA/server/client/TLS-crypt material.
  CA fingerprint differs from the old lab CA, and the private profile differs
  from the old profile. Neither key nor profile content was logged.
- **New profile:** `/tmp/opencode/controlled-vpn-20261020T0736Z-attempt1/client.ovpn`.
  **Evidence:** the same directory's `evidence.json`, `cleaned.json`, `state.json`,
  sequenced heartbeat JSONL files, archived A rollback/cleanup records and logs.
  Directory 0700; files 0600. The profile requires controller-managed IAP forwarding
  and resolver/IPv6 lifecycle; all task services/forwards are stopped now.
- Before deployment, all **31 sandbox regressions passed** in 7.582 seconds, and
  Bash syntax passed (`07:32:21Z` invocation). Tests ran with
  `PYTHONDONTWRITEBYTECODE=1` using the focused command above. No image rebuild,
  container recreation or trial implementation fix was needed for this run.
- Before runtime mutation, A/B reconciled against the retained immutable-image,
  container/network/volume/mount/capability/limit baseline. Full Config,
  HostConfig, NetworkSettings (including endpoint IP/MAC/gateway) and destination-
  keyed mounts also match the **original controlled live run's** captured metadata.
  Source/context hashes remained unchanged through execution; the process scan
  found no overlapping controller. No old task daemon/tunnel/listener/unit remained.
- This newer full-endpoint comparison covers the original controlled run to this
  run. It does **not** fill the earlier historical baseline's missing endpoint
  fields. **B8 remains deferred, medium/unverified.**

### Live observations

| Check | Revised-source result |
|---|---|
| Joined shells | Same persistent Bash shells 935/936, workers 948/947; UID/GID 1001, zero daily effective capabilities, shared `net:[4026533548]`. B remains capability-free. |
| Cycle 1 | PASS `07:35:49.989077Z`–`07:36:07.179645Z`: A1 requests connect, both shells pass DNS/HTTP, A2 requests disconnect. Daemon PID 1037; generation `91f2cd2d90054fc2be589613dec307f9`. |
| Cycle 2 | PASS `07:36:07.179675Z`–`07:36:24.377179Z`: A2 requests reconnect, both shells pass DNS/HTTP, A1 requests disconnect. Daemon PID 1325; generation `b025a28ee24847d59212a2dbcce932b4`. |
| Private DNS/HTTP | Four shell probes resolve `service.ld01.test` to `10.231.0.1`, use `10.231.0.1#53` and return fixture `cvpn152283967635`. Both connections log exact TLS server-name verification, TLS 1.3 and AES-256-GCM. Client remains OpenVPN 2.6.19; server 2.6.14 and dnsmasq 2.90. |
| Embedded resolver rejection | PASS in both connected cycles: explicit UDP **and TCP** DNS to `127.0.0.11` unavailable while lab DNS/HTTP work. Conntrack-original-destination enforcement covers the retained Docker DNAT to high ports. |
| Host/B private negatives | PASS in both cycles for HTTP, UDP DNS **and TCP DNS**. No direct access to the private fixture. |
| Host continuity | 53 acknowledgements, one socket inode 7726179, server connection `dcb26e534ae646fea61e1b116e1f25b9`; zero reconnects/errors/resets. |
| B continuity | 52 acknowledgements, one socket inode 7722544, server connection `6fffce0791094f8a86dab10d7e67d135`; zero reconnects/errors/resets. |
| Restoration | PASS after each stop: exact A resolver bytes, IPv4/IPv6 routes/rules, filter and nat configuration, and IPv6 sysctl state. Watchers retired/joined; root lab material removed only after explicit restoration PASS. |
| Host/B preservation | Exact routes/rules/resolver comparisons pass during and after both cycles; all retained container IDs/configuration/mounts/full endpoints remain unchanged. Post-run audit also matches the fresh predeployment host/B/A snapshots. |
| Final cleanup | Empty cleanup-error list. Both forwarding transports/listeners closed. No active task VPN, watcher, server tunnel, VM task service/listener or task unit file remains. Four terminated A child entries remain as explicit residuals below. |

### All attempt and audit dispositions

| Record | UTC interval | Disposition |
|---|---|---|
| `/tmp/opencode/controlled-vpn-20261020T0733Z-audit/preflight.json` | `07:34:06.225339Z`–`07:34:12.966334Z` | Audit FAIL, before deployment: the private audit's command-line substring selector matched its own remote Python inspection as a fixture. Failed record retained; selector corrected to match an actual fixture script argument. No trial/resource mutation. |
| `/tmp/opencode/controlled-vpn-20261020T0735Z-audit/preflight.json` | `07:34:40.680867Z`–`07:34:46.204740Z` | Audit PASS: baseline/full endpoint reconciliation, no leftovers/overlap, original-file and source hashes, retained VM inventory. |
| `/tmp/opencode/controlled-vpn-20261020T0736Z-attempt1/evidence.json` | `07:34:59.838456Z`–`07:36:40.236169Z` | Live attempt 1 PASS; both cycles and cleanup PASS. **No failed live connection/deployment attempt and no live repeat needed.** |
| Same directory, `post-run-audit.json` | `07:38:34.015656Z`–`07:38:39.536274Z` | Audit FAIL: a name-only OpenVPN process check counted terminated zombie entries as active. All other comparisons passed. Original audit retained; process states/parentage examined explicitly. |
| Same directory, `post-run-audit-2.json` | `07:40:43.410328Z`–`07:40:48.924494Z` | State-aware audit PASS, 19 checks: exact restoration, no active task resources, source/original-file preservation, fresh credentials, permissions, package/VM listener restoration and cancellation. Zombie residuals are retained in the record, not hidden or removed. |

The private audit helpers were corrected; trial acceptance was not weakened and
the trial implementation was unchanged. No live fault injection occurred.

### Final retained resources and residuals

Both original container IDs listed above remain running, with original homes,
networks, project, image, labels, limits, capabilities and full endpoints. A's
post-run process inspection found **four defunct, state-Z entries, all parent PID 1**:
OpenVPN PIDs **1037, 1325**, and watcher Python PIDs **1006, 1294**. The recorded
watcher journals and daemon evidence identify them as this task's terminated
children. They have no live socket/tunnel or running VPN/watch loop, but retain
PID-table slots because A's unchanged PID 1 is `sleep infinity` and does not reap
them. They are an explicit residual, not an active VPN. No container restart or
recreation was performed to clear them.

All VM task/material/source directories retained after both runs:

| VM path | Disposition |
|---|---|
| `/var/lib/ld01-cvpn-cvpn7a1a8819b397` | Original root-owned 0700 PKI/profile/config/log/package inventory/rollback directory. Original rollback hash and mtime unchanged; old script not invoked or edited in this run. Files 0600, rollback script 0700. |
| `/tmp/ld01-upload-cvpn7a1a8819b397` | Original 0700 source/setup-log directory, files 0600; untouched by fresh deployment/rollback. |
| `/var/lib/ld01-cvpn-cvpn152283967635` | New root-owned 0700 PKI/profile/config/log/package inventory/rollback directory. Files 0600, rollback script 0700. Scoped rollback succeeded; all four task units stopped and removed. |
| `/tmp/ld01-upload-cvpn152283967635` | New 0700 source/setup-log/lifecycle-lock/cancellation directory, files 0600. Cancellation marker set; no setup worker remains. |

Six native packages from the original run remain installed at the same versions:
`openvpn 2.6.14-0+deb12u2`, `dnsmasq-base 2.90-4~deb12u2`,
`libjansson4 2.14-2`, `liblzo2-2 2.10-2`,
`libnftables1 1.0.6-2+deb12u2`, `libpkcs11-helper1 1.29.0-1`.
The new deployment added/changed/removed **zero packages**. Package-managed
configuration/binaries/libraries/docs/locales remain, including `/etc/openvpn`
(`client`, `server`), `/usr/lib/openvpn`,
`/usr/lib/x86_64-linux-gnu/openvpn/plugins`, `/usr/share/openvpn`,
`/usr/share/dnsmasq-base`, `/usr/include/openvpn`, `/var/log/openvpn`,
native systemd/init/network-hook directories and package documentation directories.
The complete package directory list is retained as `vm_after.package_directories`
in `post-run-audit-2.json`, including shared parent/library/doc/locale paths.
Apt/dpkg directories `/var/lib/apt/lists`, `/var/cache/apt`, `/var/lib/dpkg` remain.
The default package `openvpn.service` remains `active (exited)`, `/bin/true`, with
no VPN process/listener. No task unit files or task VM listeners remain.

All local evidence/profile directories retained: the original
`/tmp/opencode/controlled-vpn-20261019T2153Z`, both new audit directories in the
attempt table, and `/tmp/opencode/controlled-vpn-20261020T0736Z-attempt1`.
Original profile/evidence/state/cleanup hashes are unchanged. No key/profile/raw
private evidence is in Git; no company material, accounts, host sockets/agents,
host VPN/resolver/daemon changes, public ingress, extra VM or paid IPv4 were used.

**Final coordinating verification:** `python3 /tmp/opencode/controlled-vpn-final-proof.py`
passed: both cycles, four same-shell probes, TLS exact-name verification, all added
DNS negatives, 53/52 complete socket/server-identity sequences, 19 audit checks,
cleanup before deadline, unchanged implementation/original-evidence hashes,
private permissions and the four disclosed zombies. Source is the tested/live
implementation; no further implementation changes followed. Spec is `done`.

**Remaining:** B8 is still deferred/unverified. Live automatic
failure injection was not performed; failure paths retain sandbox coverage only.
Company/native-UDP/full-tunnel/live-IPv6/account/S1–N3 and restricted daily-control
acceptance remain unclaimed. IAP heartbeat continuity proves only its controlled
non-VPN path. No commit/push/PR was performed.
