# Original LD01 containers started — reconciliation pending

**Subsequent user decision:** the inspected running state was explicitly accepted
and [private baseline inputs prepared](baseline-adopted.md). The no-adoption
statements below describe this earlier start/inspection checkpoint. No live
diagnostic authorization follows from baseline acceptance.

**2026-10-20: authorized empty scratch creation and original A/B start complete.
No baseline adopted; no VPN/diagnostic run.**

The user expressly authorized new empty scratch at the existing bind path,
starting the original A/B containers, and inspection before baseline adoption.
Homes, IDs and retained evidence must remain; no VPN connection or diagnostic
execution was authorized. Owner/branch: OpenCode, `fix/n2-baseline-diagnostic`.

## Attempts and durable private evidence

Parent `/home/rat/.local/state/termux-vm-private/`, directories 0700/files 0600:

| Record | Result |
|---|---|
| `start-originals-20261020T134426Z` | Pre-mutation guard stopped on A mount-array ordering. Destination-keyed comparison proved exact mount metadata equality. No directory/container mutation occurred. Original failed check retained. |
| `start-originals-20261020T134459Z` | Empty scratch created, both original containers started exactly once, state inspected. Initial helper categorized B's firewall permission denial as a failed check; the separate offline assessment correctly records it UNAVAILABLE. No extra capability granted. |
| Same directory, `assessment.json` | **46 checks PASS**, no baseline adopted; one B firewall inspection unavailable. Current differences and residual hashes recorded. |

Exact start command, run only under the user's one-time authorization:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/start-retained.py \
  --authorized-start-originals \
  --inspection /home/rat/.local/state/termux-vm-private/inspection-20261020T133405Z/inventory.json
```

The source retains strict pre-start absence/stopped/identity guards and has no
automatic retry, restart, recreate or removal path. The mount comparison now
uses destination keys, so array order alone is not treated as drift. The running
state was assessed offline without another start:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/assess-started.py \
  /home/rat/.local/state/termux-vm-private/start-originals-20261020T134459Z/inventory.json
```

## Verified preservation and new data

- Original A ID `3aca8c213551fa528142eb38b69990e797135e2d4d13b3273e44ecee6857e32b`
  and B ID `99f9f43eb98c3a4c8be3d96c59d77b9ddb5296841fd9b93d5062f9b8e48c0abd`
  are running, unpaused, on the same frozen image.
- Full Config/HostConfig and destination-keyed mounts match the stopped
  post-reboot inventory, including daily identity, capabilities/devices, labels,
  limits and no-new-privileges. No container/image recreation or settings change.
- Both home volume metadata records are identical before/after; their contents
  were not overwritten or copied. Read-only inside stat confirms UID/GID 1001.
- New **empty** scratch was created at
  `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/project`, UID/GID 1001:1001,
  mode 0700, at `2026-10-20T13:44:59.771783Z`. Both `/project` mounts have the
  same inode as that host directory. This is replacement data, **not recovery**
  of the lost scratch contents. Its path is still temporary because the user
  authorized preserving the existing bind configuration.
- Existing home volumes and Docker network identities are unchanged from the
  read-only inspection. A/B now have distinct live network namespaces. Current
  addresses/gateways are A `172.16.0.34/28` via `172.16.0.33`, B `172.16.0.50/28`
  via `172.16.0.49`. Full new endpoints are private inventory observations,
  not equality claims against the lost historical endpoint baseline.

## Running VPN-off state and retained material

- No OpenVPN process or `ld01tun` in either container. No state-Z entries in
  either process inventory; the old six zombie PIDs are not used as a current
  allowlist. No host task listener on 20990/20991/20992.
- A IPv4/IPv6 filter/nat reads succeeded. No LDC task chain remains; resolver
  bytes, routes/rules and filter policies match A's surviving old restore journal.
- A's Docker DNS high-port mapping changed from TCP/UDP `40121/34112` to
  `44993/46041`. Offline normalization of **only those embedded-resolver
  high-port fields** makes the remaining NAT configuration identical. The new
  exact NAT is retained as current state; old journal content was not modified.
- Retained A directory `/run/ld01-cvpnb76f5884442f` remains, with no active marker;
  `cleanup.json` says PASS/empty errors and `intent.json` says off. Its restore,
  cleanup and intent SHA256 digests are recorded privately for future comparison.
  No old rollback/cleanup was invoked and no profile/key content opened.
- B has no task journal. Its root account still lacks NET_ADMIN, so firewall
  queries return permission denial. That is **UNAVAILABLE**, not a finding of
  stale rules or proof of firewall equivalence. No capability was added to inspect it.
- GCP was not modified or re-inspected by this start operation. Its earlier
  read-only inactive-task disposition is in [post-reboot inspection](post-reboot-inspection.md).

## Baseline decision required

These observations can be proposed as a **new post-reboot running reference**:
same original IDs/homes/configuration, newly empty scratch, current endpoints/
Docker DNS NAT and no zombies, plus the retained inactive A journal hashes.
They do not restore lost raw evidence or close historical B8 endpoint proof.

**No baseline accepted/adopted yet.** Await the user's explicit decision before
publishing baseline-format input files. No new execution window or diagnostic
approval exists; even after adoption, a VPN baseline-only run requires a separate
bounded authorization and the authenticated operator terminal.
