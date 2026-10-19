# LD01 tooling and fresh baseline results

Date: 2026-10-19. Owner: OpenCode — Linux Docker trial preparation. Branch: `docs/linux-docker-trial-preparation`. **LD01-T and LD01-F PASS; VPN/account acceptance remains unrun.**

## Authorization and boundary

The user selected **Build and baseline (Recommended)**: Ubuntu package downloads/build, fresh A/B containers, private homes/scratch storage and Docker-managed networks, A-only TUN/NET_ADMIN, DNS for `example.com` and public TCP to `1.1.1.1:443`. They also approved extending the existing uncommitted worktree. No existing-owner handoff was received. Original containers, homes/project and private staging remained untouched; only original source/results and the shared immutable foundation image were read/reused.

No company endpoint was resolved, no credentials mounted/read, no VPN/account login or failure injection attempted. No host VPN/daemon configuration changed. Docker created this task's bridge/veth/NAT/firewall state as authorized.

## Source and retained resources

- [tooling/Dockerfile](tooling/Dockerfile) derives from the original local foundation tag. Before building with `--pull=false`, its ID was verified as `sha256:831666c75ae440c43933711269a44181e946e6bec156e7e1dddd3c8002886afb`. The resulting image's rootfs layer prefix matched the foundation's layers. Future rebuilds must repeat this identity check; the source tag/package repositories are mutable, so the Dockerfile alone does not promise a byte-identical rebuild.
- The narrow [build context](tooling/.dockerignore) includes only the Dockerfile. No account/credential input was supplied. Existing Docker legacy builder used; no new builder installed.
- Tooling tag: `tvm-share-ld01:tooling`. **Frozen runtime image:** `sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050`, used by both A/B.
- Containers: `tvm-share-ld01-a`, `tvm-share-ld01-b`, retained running with idle `sleep`; no automatic restart. Each has 512 MiB RAM/no extra swap, 1 CPU, 128 PID limit.
- Homes: `tvm-share-ld01-home-a`, `tvm-share-ld01-home-b`.
- Networks: `tvm-share-ld01-net-a` (`172.16.0.32/28`), `tvm-share-ld01-net-b` (`172.16.0.48/28`). Chosen after inspecting current IPv4 routes in all tables and existing Docker IPAM, including null configuration handling.
- Scratch bind: `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/project` → `/project` in both. Parent directory mode `0700`, host/container UID 1001. Only this scratch path and the respective home are mounted.
- Labels: `task=linux-docker-sharing-trial`, `trial=ld01`, `owner=opencode-linux-trial-preparation`.
- [executed-commands.md](executed-commands.md) preserves the build labels/arguments, provisioning, prefix/collision selection, home/scratch initialization and exact host-comparison rules.
- A drops all capabilities then adds only `CAP_NET_ADMIN`, with `/dev/net/tun` read/write access. B drops all capabilities and has no TUN device. Both use no-new-privileges, default UID/GID 1001:1001 and no host sockets/home integration.

Private evidence root: `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/`. Generated JSON/log files are `0600`; no raw private reports are staged. `resources.json` records full created container/network IDs; `image.json` records full image metadata. Cleanup/ownership transfer requires coordination and exact new resource names/IDs; do not prune globally. Temporary storage is not a durable backup.

## Installed tooling scope

`tooling-versions.json` records the complete `dpkg-query` manifest and actual binary output. Selected versions:

| Tool | Version |
|---|---|
| OpenVPN | 2.6.19; Ubuntu package `2.6.19-0ubuntu0.24.04.4` |
| OpenSSL | 3.0.13 |
| Git | 2.43.0 |
| Python | 3.12.3 |
| curl | 8.5.0 |
| iproute2 | 6.1.0 |
| iptables | 1.8.10, nf_tables backend |
| tcpdump | 4.99.4 |

The image provides `nm-openvpn` UID/GID 999:999; privilege dropping and a VPN daemon were not exercised. Current A capabilities omit SETUID/SETGID, so a later daemon configuration must explicitly resolve privilege dropping rather than assume this identity's existence is sufficient. Research references to OpenVPN 2.7 are not runtime certification of this installed 2.6.19 client.

## Observations

Initial positive run: `2026-10-19T15:23:27Z` completion, exact start/end timestamps in `spot-check-20261019T152327577056Z.json`. After the review corrections below, the final source passed again at `2026-10-19T15:29:32Z`: `spot-check-20261019T152932087625Z.json`, additionally retaining bounded runtime configuration and network/volume ownership evidence.

| Check | Result | Exact scope |
|---|---|---|
| Image/mount/privilege inventory | PASS | Both use frozen image; expected labels, exactly two selected mounts, private home volumes; A-only NET_ADMIN/TUN, no privileged/host-network mode; no-new-privileges. |
| Resource ownership/configuration | PASS | Final checker verifies recorded container/network IDs, exact separate-network attachment and home-volume names/labels, complete A TUN host/container mapping and access, memory/swap/CPU/PID limits and restart policy before any marker/probe mutation. Bounded configuration snapshot retained in final positive JSON. |
| Namespace separation | PASS | Host/A/B network namespace identifiers distinct. No adversarial isolation test. |
| Two joined A shells | PASS | Concurrent Bash shell PIDs 74 and 73, both UID 1001, same `/home/session` and A network namespace. No account/VPN state check. |
| Non-root capability baseline | PASS | Effective capabilities zero in ordinary shells in A and B. Root setup authority in A is a different privilege boundary. |
| Private homes/shared scratch | PASS | Distinct synthetic home markers; A's scratch file visible in B and on host. Not authenticated account sharing, copy semantics or Git checkout proof. |
| Application DNS/public TCP | PASS | A/B ordinary `getaddrinfo(example.com)` succeeded; independent TCP connections to `1.1.1.1:443` succeeded. Host post-setup DNS/TCP also succeeded. No VPN/private-DNS or same-socket continuity proof. |
| A TUN usability | PASS | Root setup command created `ld01probe` TUN interface in A, observed it, then deleted it. No tunnel session or route configured. |
| Pre-existing host route/rule/DNS baseline | PASS, bounded | IPv4/IPv6 all-table routes matched after excluding only task-created interface routes; IPv4/IPv6 rules and IPv4 route lookup matched. Resolver DNS/domain output matched after excluding exactly new trial interface rows with empty DNS/domain values. Pre-existing Docker network metadata matched. No whole-firewall equivalence or continuously held connection claim. |
| Underlay observation | RECORDED | NetworkManager listed zero active `vpn` entries before build. Proxy variable names, routes and resolver settings are recorded privately; this does not prove absence of all host tunnels/proxies or a VPN-free egress path. |
| Live IPv6 | NOT RUN | No IPv6 default route in A/B. No live IPv6 reachability or containment pass claimed. |

## Checker corrections and regression proof

The first run stopped before probes because the checker expected `NET_ADMIN`, whereas Docker 29 reports `CAP_NET_ADMIN`. Its failure writer also incorrectly used `Path.open(opener=...)`, masking the assertion. Read-only capability inspection confirmed the intended runtime configuration. Fixed capability-prefix normalization and used built-in `open(..., opener=...)` for exclusive `0600` reports. Preserved the original failed attempt in `initial-check-failure.md`; it produced no JSON report.

After correction the full authorized baseline passed. A deliberate wrong-image invocation then verified fail-fast rejection before marker/probe mutation and successful `0600` FAIL evidence writing: `spot-check-20261019T152420243666Z.json`. That FAIL is an expected negative checker test, not a failed valid-image runtime trial.

The required read-only review found seven actionable source/evidence gaps, all corrected: optimization-removable assertions, missing network ownership/topology checks, missing home-volume ownership checks, incomplete device-mapping validation, empty error messages, missing retained runtime-configuration evidence and missing provisioning/comparison provenance. The checker now raises explicit descriptive errors, with no acceptance logic removed by Python optimization. An optimized (`python3 -O`, `PYTHONOPTIMIZE=1`) wrong-image run proved rejection before mutation and a descriptive `0600` FAIL record: `spot-check-20261019T152927479506Z.json`. Final positive baseline passed with the added guards; no VPN gate was promoted. Review triage is recorded in the [implementation spec](../implementation-artifacts/spec-ld01-build-and-baseline.md).

Runnable spot-check (writes only its own markers/scratch file, creates/removes an A-local test TUN, and repeats the named public probes):

```bash
python3 _bmad-output/linux-docker-trial/spot-check.py \
  --image sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050 \
  --trial-dir /tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM
```

## Next gate at baseline handoff

Stop here as authorized. G3–G5 still require original-owner coordination for staged material, credential-mount/connection permission, company concurrent-session policy or approved test window, named private service/DNS/prefix/IPv6 policy, an approved external heartbeat endpoint, concrete resolver/control configuration and the least-privilege daemon decision. No successful company compatibility, S1 account/VPN, S2/S3, full N1/N2/N3 or WSL2 result is inferred. Prior foundation/research evidence remains separately labeled in [readiness.md](readiness.md).

Later user decisions cleared scoped material reuse and conditional VPN-stage permission; current material checks passed. The remaining window/target/configuration blockers and exact scope are maintained in [vpn-stage-readiness.md](vpn-stage-readiness.md), superseding this baseline handoff's permission state without changing its trial results.
