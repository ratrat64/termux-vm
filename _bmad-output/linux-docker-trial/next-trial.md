# LD01 — smallest next Linux Docker trial

Prepared 2026-10-19; execution update the same day. **Tooling build and fresh baseline have now passed; the VPN diagnostic remains unrun.** Owner and coordination: [task-owner.md](../task-owner.md). Current evidence: [readiness.md](readiness.md) and [execution-results.md](execution-results.md).

## Scope and source of truth

Continue the [research](file:///tmp/opencode/termux-vm-environment-sharing-evaluation/_bmad-output/planning-artifacts/research/technical-environment-sharing-2026-10-19/research.md) and [additional-trials plan](file:///tmp/opencode/termux-vm-environment-sharing-evaluation/_bmad-output/planning-artifacts/research/technical-environment-sharing-2026-10-19/additional-trials.md), without repeating the successful foundation campaign.

**Next increment:** derive one credential-free stock-OpenVPN tooling image; create fresh A/B contexts with private homes and one fresh shared scratch project; enter A twice; establish ordinary baseline and held external connections; connect only A using one approved policy, observe it from both shells, deliberately disconnect from the other shell, then reconnect from that shell and disconnect from the first. Observe B/host throughout. No companion, new runtime or launcher is needed for this diagnostic increment.

This is a partial S1/N1 stock-client compatibility check, not complete sharing/VPN acceptance. A successful handshake does not prove private DNS, leak prevention, account sharing, concurrent company sessions, restricted controls or full/split support. Do not inject failures or send real CLI/account traffic in this diagnostic stage before the intended blocking/resolver design is selected.

## Ownership and proposed resources

The user selected fresh resources. The original trial owner has not handed over retained resources. Do not exec into, restart, remount, copy from, remove or relabel `tvm-eval-dhlrhsji-*`, alter its project, or consume its staged credentials without separate coordination. Immutable image reuse and reading source/results do not transfer resource ownership.

| Item | LD01 proposal |
|---|---|
| Foundation image | `sha256:831666c75ae440c43933711269a44181e946e6bec156e7e1dddd3c8002886afb` |
| Tooling tag | `tvm-share-ld01:tooling`; record and use resulting immutable image ID for both contexts |
| Containers | `tvm-share-ld01-a`, `tvm-share-ld01-b` |
| Home volumes | `tvm-share-ld01-home-a`, `tvm-share-ld01-home-b` |
| Networks | `tvm-share-ld01-net-a`, `tvm-share-ld01-net-b`; choose unused, non-overlapping prefixes after current all-table routes and Docker IPAM inspection |
| Scratch project | New `project/` beneath a newly allocated private `/tmp/opencode/linux-docker-sharing-ld01.*` directory, never the original trial project or working repository |
| Labels on new resources | `task=linux-docker-sharing-trial`, `trial=ld01`, `owner=opencode-linux-trial-preparation` |
| Evidence/private config | Outside Git in that private trial directory, `0700`; private files `0600`; publish only redacted summaries |

Reserve nothing by deleting collisions. If names become occupied, stop and coordinate or choose a new ID. Cleanup targets only newly recorded IDs/names after owner approval; retain evidence and volumes until their disposition is agreed. No global prune/flush.

## Required inputs and permissions

Preparation and fresh-resource selection are recorded. **Execution authorization is not inferred from Docker access or earlier task permissions.** Record an affirmative decision and its scope for each applicable row before that phase.

**Execution update:** user explicitly authorized G0/G1 and the A-only TUN/NET_ADMIN baseline portion of G2, including `example.com` DNS and `1.1.1.1:443` public TCP probes. These ran successfully. G3–G5 remain unresolved; no credential access, connection or failure injection occurred. The current A capability set does not include SETUID/SETGID: the later privilege-dropping VPN design needs a concrete least-privilege configuration/permission decision before connection; merely providing `nm-openvpn` in the image does not solve it.

**Subsequent input-resolution update:** user relayed original-owner clearance for staged-material read/readonly-mount/private adaptation, and conditionally authorized the A-only VPN stage including SETUID/SETGID for privilege dropping. Only current host-user material metadata/openability and CA/client expiry checks have now run and passed. The actual single-session window/conflict confirmation, targets/policy, daemon-readable credential layout and resolver/control configuration are still unresolved. No capabilities were added, A recreated, config adapted, credentials mounted or VPN connected. Current details superseding the earlier gate state are in [vpn-stage-readiness.md](vpn-stage-readiness.md).

| Gate | Input/permission needed | Enables |
|---|---|---|
| G0 — image | Approve package-download/build network access and package repositories. Derive from the existing immutable foundation image; install stock OpenVPN, Git, curl, iproute2, iptables, DNS tools, tcpdump, Python 3, CA certificates and OpenSSL. Record package versions and freeze the resulting image ID before runtime. No credentials in build context/layers. | Tooling build and version inventory |
| G1 — disposable runtime | Approve two fresh containers, two homes, fresh scratch storage and Docker-managed bridge/veth/NAT/firewall changes. Select collision-free prefixes, limits and approved public baseline targets. | Fresh A/B and drift spot-check |
| G2 — tunnel privilege | Approve TUN device access and `NET_ADMIN` **only for A's network context**; stock VPN setup/control runs with the required container identity, daily shells remain UID/GID 1001. Keep B capabilities dropped. No privileged container, host networking, Docker/host D-Bus/agent sockets or broad host-home mounts. | A-side stock client; this is setup authority, not restricted product-control acceptance |
| G3 — profile/material | Original owner acknowledges exact export/staged-file use and any separately adapted copy; user approves read-only credential mount and connection. Preserve original files. Supply approved container paths, service user/group, endpoint/bootstrap rules, policy and named test destinations. Recheck current expiry/readability only; do not repeat prior offline key validation or re-export valid material. | Private adapted OpenVPN configuration |
| G4 — provider/session | Confirm whether same-certificate concurrent connections are allowed; otherwise provide an approved single-session window or separate identity. Recheck active host VPN/session state immediately before connection. Do not toggle the host VPN to make room. A controlled endpoint is an explicit alternative scope, not company acceptance. | First company connection without assumed provider independence |
| G5 — observations | Supply approved external TCP heartbeat endpoint reachable from host/B before and during A's operations, new-connection target, private service/FQDN with expected answers and VPN-bound prefixes, full/split selection, IPv6 policy and permitted observation interface/targets. Authorize only scoped canary capture/counters. | Interpretable routing, DNS and same-socket continuity evidence |
| Later account gates | Actual CLI names/versions, complete credential backends/stores, authorized test identities and login permission, acceptable writer downtime for copy. SQLite users additionally need version/WAL/advisory/backport assessment. | Real S1 account check, S2 and S3; not prerequisites for credential-free tooling or stock-client diagnostics |
| Later network gates | Supported intent-sensitive blocking/resolver configuration and daily connect/disconnect interface; B-side authorized VPN/profile/session; approved failure injection. | Complete N1–N3 full/split campaign and restricted control acceptance |

An unavailable company-private-DNS target remains BLOCKED, unless the company has no such DNS requirement (record that explicitly). A controlled private-zone fixture proves only the mechanism. An absent IPv6 route means live IPv6 is NOT RUN, not passed.

## Execution order after applicable gates

1. **Freeze tooling (G0).** Reuse the original [Dockerfile](file:///home/rat/Git/termux-vm-isolated-terminal-evaluation/_bmad-output/planning-artifacts/research/technical-isolated-terminal-sessions-2026-10-19/trial/Dockerfile) as read-only source/reference; keep any derivative source in this worktree under `_bmad-output`. Build once, retain package/client version manifest and image ID. Explicitly provide/adapt the VPN service account; leave default shell user 1001:1001.
2. **Create fresh A/B (G1, G2 for A).** Inspect current routes/rules, Docker IPAM, proxy/underlay and resolver settings first. Use separate networks/home volumes, identical frozen tooling image and only the fresh selected project mount. Size resources for VPN/probes rather than silently inheriting the foundation's 128 MiB limit. Record effective mounts, UID/GID, capabilities and devices. No keys in B. Retain the controller outside both contexts.
3. **Spot-check, not recampaign.** Confirm identical image IDs, distinct host/A/B netns IDs, two non-root shells in A with the same home mount/netns and different PIDs, private A/B markers, and fresh project edit visibility. Check ordinary application DNS plus approved public IPv4 access. Record IPv6 availability. Do not label markers as account proof or repeat foundation restart/recreation tests merely to count more passes.
4. **Prepare config (G3–G5).** Preserve TLS server/name verification, `remote-cert-tls server`, minimum TLS, TLS-crypt and explicit `auth SHA256`. Map the four approved credential paths read-only and adapt `nm-openvpn` identities appropriately. Keep routes, resolver/control files, runtime selection and logs context-local, outside shared application state. Record negotiated cipher; do not weaken policy to obtain a connection. Specify actual DNS integration: receiving OpenVPN DNS options alone is insufficient. Record the intended stop mechanism before connecting; keep secrets out of command output/log summaries.
5. **Baseline continuity.** Hold a controlled external TCP connection from host and B with timestamped, sequence-numbered application heartbeats on each same socket through all A operations; automatic reconnect is disabled. Record socket identity, acknowledgements and reset/reconnect/error counts. Periodically test new connections too. Snapshot effective host/B routes, rules and DNS/upstream/search settings. Failure to establish these baselines blocks a continuity verdict.
6. **Joined-shell diagnostic.** Use the shell-entry commands below. Connect from A1, observe from A2; deliberately disconnect from A2, observe ordinary internet/DNS restoration in both; reconnect from A2 and observe from A1, then deliberately disconnect from A1. Record tunnel state, namespace, effective routes and real application DNS path (resolver file, upstream/interface, public/private answers where supplied). Check intended service reachability and public egress according to the single approved policy. Observe host/B same-socket heartbeats and unchanged pre-existing network settings throughout. Distinguish task-created bridge metadata from pre-existing host state.
7. **Stop and report.** Save redacted observations with exact image/client/policy scope, evidence paths and statuses. If route/DNS restoration or continuity fails, record FAIL and investigate before expansion. No arbitrary latency promise is implied. Do not proceed automatically to fault injection, B VPN, storage-layout changes or account logins.

Daily entry for the now-running fresh containers (the baseline used non-interactive concurrent shell entry):

```bash
docker exec -it tvm-share-ld01-a bash  # run twice, for A1 and A2
docker exec -it tvm-share-ld01-b bash
```

The eventual daily VPN commands remain an execution input. `docker exec --user 0` may provide trial setup authority after approval but cannot establish the restricted controller requirement in N3.

## Stopping rule and next increments

Stop LD01 after tooling/spot-check evidence and this single A-policy diagnostic are recorded, or at the first missing gate/failure. Report only the individual observed subchecks as PASS; S1 stays incomplete without real account identity, and N1 stays incomplete without the complete A/B cycle and required policies. Fault blocking is not inferred from a clean disconnect.

Then follow the existing plan: one complete N1/N2/N3 network campaign per distinct client/policy/resolver architecture; S2 live sharing with real application concurrency; S3 quiescent consistent copy and fresh identity; shell-entry/application-DNS/VPN smoke checks after every layout change. Keep each layout's volumes distinct. WSL2 and other VPN families retain their own acceptance gates. This preparation does not change prior A1–A4/V1–V7/W1 results.
