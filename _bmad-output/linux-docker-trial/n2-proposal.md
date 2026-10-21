# N2 — bounded behavior and live-campaign proposal

**P1–P3 and spec approved on 2026-10-20; offline implementation/review verified. No live execution authorization.** Base: `dc1a192619471c74692833e65122d4fa4ebeeec1` (merged PR #4). The prior trial is complete/disconnected. Work used source/documents and sandbox checks only. [Build spec](../implementation-artifacts/spec-n2-vpn-failure-containment.md); [offline results](n2-results.md).

## Historical baseline and the gap addressed

The completed lab uses stock OpenVPN inside retained A, a controller-managed VPN-only IAP/SSH forward, a separate host/B heartbeat forward, and private HTTP/DNS on the server tunnel. DNS rules match conntrack's original destination to cover Docker's embedded resolver DNAT. A IPv6 traffic is firewall-blocked during a connection; no live IPv6 acceptance exists.

At the PR #4 baseline, `trial.py` made deliberate stop, client death, lease expiry and controller failure converge on the same restoration path. That restored ordinary DNS and removed task restrictions. Its DNS exception allowed the lab resolver address without binding it to the tunnel; no IPv4 rule prevented the VPN subnet from using the default route when TUN disappeared. The offline N2 implementation addresses that gap. A failed service request alone cannot distinguish blocking from leaked packets that receive no response.

The historical research's N2 oracle distinguishes unexpected failure from deliberate off. This proposal covers only **A, controlled IPv4 split routing, the existing all-A VPN-DNS architecture, two faults and explicit recovery**. It is a partial N2 increment, not completion of the wider campaign.

## P1 — accepted traffic and DNS contract

| Intent/state | VPN-bound IPv4, including existing flows | DNS | Unrelated traffic |
|---|---|---|---|
| Deliberately off | Exact ordinary baseline; fixture need not be reachable | Exact original resolver restored | Ordinary baseline |
| Connect requested / starting | Install protection before selecting resolver or starting client; VPN subnet may leave only via `ld01tun` | All classic UDP/TCP DNS only to lab resolver via tunnel; no embedded/public fallback | Non-VPN IPv4 stays direct |
| Connected | VPN subnet only through tunnel; literal-IP and named fixture work | Normal application lookup plus UDP/TCP queries use lab resolver | Non-VPN IPv4 stays direct |
| Unexpected client/transport/owner failure | Retain protection regardless of whether daemon/TUN remains; latch fault, retire failed client safely | Keep lab resolver selected; no fallback; queries fail closed | Non-VPN direct-IP traffic continues |
| Explicit disconnect after failure | Stop task client, retire watcher, remove only task protection and verify exact restoration | Original resolver works without repair | Ordinary baseline |

**Accepted DNS tradeoff:** reuse the current all-A DNS replacement. During failure, public DNS lookups also fail. Unrelated direct-IP/held traffic works, but fresh unrelated hostname access is not promised. During deliberately-off state baseline resolver behavior is restored, without an always-private-name rule.

Keep the existing A IPv6 block throughout starting/connected/fault states, restore it on explicit off, and label live IPv6 untested. No DoH/DoT, custom application resolver/proxy or hostile-root containment claim.

## P2 — smallest implementation and recovery

Extend the existing task OUTPUT chain: reject traffic to the collision-checked VPN subnet whenever the outgoing interface is not `ld01tun`, including the resolver IP. Do not exempt established flows before this guard. Keep conntrack-original-destination UDP/TCP DNS rejection. Build/install protection before changing resolver bytes or starting OpenVPN; do not report readiness if any required rule fails. If protection cannot be installed, never start the client; preserve private FAIL evidence and use authorized abort cleanup.

Use the existing generation lock/journal for `starting`, `connected`, `faulted` and explicit `off` intent. Both agent and controller fault paths retain containment; controller `finally`, host watchdog and lease loss cannot silently call ordinary-off restoration. Cancelled/faulted generations cannot accept late start/renew actions. An unresponsive client may be terminated with the existing identity checks while leaving protection installed. Snapshot/archive fault state, bounded daemon logs and probe streams before release or another generation.

Recovery is **explicit off, then connect**, without automatic reconnect acceptance. Retrying a connection while faulted must not transiently remove protection; the smallest interface can reject it and require off first. Existing OpenVPN internal reconnect behavior does not authorize unblocking. Explicit off uses the existing checked restoration/archive path; failed daemon retirement must not release protection. Retryable restoration failures keep evidence/material and remain FAIL.

**Accepted trial-expiry design, requiring later live authorization:** pre-authorize an independent supervisor to record explicit trial-off cleanup on campaign abort or beginning no later than hard stop minus ten minutes. This is a trial teardown action, not a fault handler deciding to unblock. It also handles controller loss; archive what is available before off. No fault injection starts in the last fifteen minutes. Propagate one freshly approved fixed UTC deadline through controller, agent, watcher state and fresh server source. Budget timeouts/lock acquisition so cleanup attempts fit the reserve; failures remain FAIL and are reported, never hidden by extending the window. Do not alter old server source/rollback directories or reuse their deadlines.

No new controller framework, runtime, dependency or image is needed. Modify `trial.py`, its existing tests and the existing fixtures/server setup only. Retain installed VM package versions; omit unconditional apt update/install for this campaign and reject missing prerequisites instead.

## P3 — smallest useful live campaign

**Accepted campaign bound, not a started/authorized window:** one fresh maximum 45-minute window, including ten minutes reserved for cleanup. Start it only after spec approval, implementation, sandbox checks and review are complete. Record affirmative fault/observation authorization, UTC start and absolute hard stop immediately before deployment. Approval to implement is not approval to connect.

### Admission and instrumentation

1. Confirm exclusive LD01 reuse/no overlapping controller or worker. Reconcile recorded immutable image, A/B IDs, full configuration/endpoints, homes/networks/mounts/capabilities and host/B baseline. Account for the four existing state-Z children; identify new processes by PID plus start identity, never by name alone. Preserve original private-evidence and old VM rollback hashes. Use only baseline metadata files, not historical company-material records.
2. Create fresh task ID, PKI and unused private evidence directory outside Git, 0700/0600. Reuse `free-vm`, retained packages and split subnet selection. No new public listener, package change or host route/resolver/firewall mutation. Check deadline/worktree pins consistently. Establish verified server identity and private fixture before judging faults.
3. Keep two non-root A shells throughout. Hold host/B sequenced sockets over the separate non-VPN transport, without reconnects, and periodically open fresh controlled non-VPN connections. Also hold a sequenced VPN-bound socket from A to a heartbeat fixture bound to the server tunnel; fresh requests alone miss existing-flow fallback. An A-only non-VPN heartbeat forward binding provides a direct-path canary; it uses the separate heartbeat transport, not the VPN forward.
4. With explicit observation approval, use a bounded host-side capture at **A's exact veth only**, filtered to A-origin controlled VPN-subnet traffic, classic DNS egress and the approved non-VPN/bootstrap canaries. Capture only headers needed for destination/interface/protocol checks; keep raw output private. No capture capability is added to A. Record interface identity, start/stop/readiness and capture-drop statistics; a positive non-VPN canary verifies capture is observing A. Snapshot rule counters before/after probes. If observation privileges/readiness fail, stop before injection. Timeout-only or rule-text-only evidence cannot establish leak containment.

### Two independent cases

| Case | Authorized injection target | Required sequence |
|---|---|---|
| F1 — abrupt client death | SIGKILL only the recorded task OpenVPN PID after start-time/profile identity checks | Positive baseline → kill → 60 seconds of fault observation → explicit off → verify baseline → reconnect and verify fixture |
| F2 — VPN transport loss | Terminate only the recorded `vpn` SSH/IAP forward process group after identity/specification checks; verify its listener closes | New healthy baseline → remove VPN forward → 60 seconds of observation → explicit off → baseline → recreate only that task forward → reconnect and verify fixture |

The controller remains alive, as do heartbeat forwarding, B and both A shells. A missing/dead VPN forward is tolerated only within F2's expected-fault phase; reserve checks, sibling heartbeats and unrelated errors still abort. Do not mask arbitrary `health()` failures. Observe the interval with a live client but broken transport as well as daemon/TUN disappearance if it occurs. Record measured transitions; 60 seconds is an observation interval, not an unproven detection SLA.

In both cases, begin probes/capture **before injection** and keep them through containment and recovery. Observe:

- Fresh literal-IP HTTP and the pre-existing VPN-bound socket; no unauthorized plaintext to VPN destinations at A's non-tunnel boundary, with no established-flow bypass.
- Ordinary application lookup of unique names in the private zone, plus explicit UDP/TCP DNS to the lab resolver and Docker `127.0.0.11`. Use uncached A/AAAA queries, recording expected private answers or authoritative no-data while connected. Refused/time-out negatives are evidence only alongside boundary observation/counters. Never send these names to an unrelated public test resolver.
- Unrelated A direct-path canary remains live during faults; under P1, public DNS outage is expected. After explicit off verify ordinary DNS with an approved public name (proposed `example.com`) and direct-path access without manual repair. Private names need not resolve while off; do not deliberately query them there.
- Host/B fixture isolation, unchanged routes/rules/resolver bytes and held socket/server identities with complete sequence acknowledgements and zero reconnect/reset/error. Continuity covers this controlled IAP non-VPN path only.

### Stop, recovery and evidence

One attempt per fault case. Stop at the first unexpected failure, drift, missing capture proof, heartbeat break or restoration error; retain failed records and do not automatically rerun. An intentional fault is not permission to introduce another fault. A future retry requires a separately agreed scope/window.

Archive fault evidence before explicit off, deletion or another generation. After each off compare exact A resolver/routes/rules/filter/nat/IPv6 state. End with verified off, scoped server/forward shutdown, no active task client/watcher/listener, and full retained-resource equality. Preserve all old evidence/material and report any new zombies without restarting/recreating A to remove them. New VM private task material remains retained as evidence/rollback. Publish only redacted case results and private paths.

## Deferred scope and claims

Controller SIGKILL, packet blackhole with a still-live forward, auth/first-connect rejection, automatic recovery, B as fault target, B's own VPN, container/network-owner recreation, full tunnel and live IPv6 remain NOT RUN. Keep sandbox coverage for controller loss/lease/deadline, installation failure, startup races and cleanup retries, adapted to the selected policy. Whole-container/owner recreation would end shells/change retained identities and requires a different approval. Two A faults cannot close the full historical N2 matrix or N3 restricted-control acceptance.

## Approval gates

P1–P3 and full spec approval are recorded; offline implementation/review is verified. Next separately authorize the exact F1/F2 injections, scoped capture and targets, exclusive reuse, supervised abort/expiry off, and fresh bounded UTC window. No live operation is authorized by the implementation approval or historical trial approval.
