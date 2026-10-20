# Post-reboot retained-resource inspection — 2026-10-20

**Subsequent authorized action:** the user later approved empty scratch replacement
and starting the original A/B. [Running-state reconciliation](originals-started.md)
records those changes; baseline adoption remains pending. The stopped-container
findings below describe this earlier read-only inspection, not the new state.

**Read-only inspection complete; differences require a human decision. No new
baseline adopted, no execution window opened.** The user authorized inventory
and comparison only, prohibiting VPN connections, deployment, packet capture,
restart/recreation/deletion and company VPN material access.

Owner: OpenCode, branch `fix/n2-baseline-diagnostic`, durable worktree
`/home/rat/Git/termux-vm-n2-baseline-diagnostic`.

## Private evidence and command dispositions

Private parent: `/home/rat/.local/state/termux-vm-private/`, mode 0700. Inventory
directories are 0700 and their JSON files 0600; none is in Git.

| Inspection | Disposition |
|---|---|
| `inspection-20261020T133251Z` | Local inventory succeeded; GCP SSH exit 255 because strict checking used the default known-hosts file, which lacked the Google Compute alias. No remote command ran. Failed command and error retained. |
| `inspection-20261020T133405Z` | Local and GCP inventory commands exit 0. Existing `google_compute_known_hosts` explicitly selected with strict checking; existing SSH identity reused with `--plain`/BatchMode, no key provisioning or trust change. `inventory.json`, individual command records, `summary.json` and offline `assessment.json` retained. |

Source-only helpers under this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/inspect-retained.py \
  --authorized-read-only --private-parent /home/rat/.local/state/termux-vm-private
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/assess-retained.py \
  /home/rat/.local/state/termux-vm-private/inspection-20261020T133405Z/inventory.json
```

The first command ran at `13:32:51Z`; the complete second inventory began
`13:34:05Z`. Assessment reads those files offline, without Docker/GCP calls.
The commands above document this inspection, not standing permission to rerun it
or execute a VPN trial. No application/controller implementation was changed.

## Matches to available historical records

**41 bounded source comparisons MATCH.** Against committed/recovered redacted
records, the following remain consistent:

- Original A/B full container IDs and frozen image
  `sha256:8a217d4d275127cbf908b9c1821feb93c888bcf35988e6d0d7d3cbc744bab050`.
- Ownership labels, UID/GID 1001:1001, `sleep infinity`, no automatic restart,
  512 MiB memory/no additional swap, one CPU and 128 PID limits.
- All capabilities dropped, A-only NET_ADMIN and exact rw TUN device mapping;
  B has neither added capabilities nor devices. No privileged mode; both retain
  no-new-privileges.
- Both home volume names/labels and both configured mount destinations.
- Configured scratch bind source remains the historical path (but that host
  directory is missing; configuration equality does not establish data retention).
- Separate network attachments, network labels, bridge driver, IPv4 subnets
  `172.16.0.32/28` and `172.16.0.48/28`, IPv6 disabled on these Docker networks.

These are bounded comparisons, not whole Config/HostConfig equality against the
lost private report. Home volume contents were not read; retained volume metadata
does not prove application-state content equality.

## Differences and admission blockers

| Item | Historical observation | Current observation |
|---|---|---|
| A runtime | Running | **Exited**, exit 137, finished `2026-10-20T12:42:39.433172202Z` |
| B runtime | Running | **Exited**, exit 137, finished `2026-10-20T12:42:39.430146128Z` |
| Shared scratch host path | Existing private scratch directory | **Missing:** `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/project` |

Stopped containers have empty IP/MAC/gateway fields and no active peers on their
respective Docker networks. Their configured network attachments remain. This
does not provide equality to former live endpoints or establish endpoint drift
while running. Exit timing is consistent with the reported reboot; this inventory
does not independently determine its cause.

No container was started or entered. Current in-container resolver/routes/rules,
task journals and zombie identities are **UNAVAILABLE**, not reconciled to the old
four/six-PID list or automatically replaced by an empty list. An eventual running
baseline needs its own authorized observations. The missing scratch path blocks
ordinary use of the retained bind mounts and the prepared diagnostic preflight.

## Controlled GCP disposition

Read-only SSH/IAP inspection of `free-vm` found:

- All 15 known task/service combinations across the three task IDs inactive;
  no retained task unit file, task tunnel `ld01srv`, active OpenVPN process or
  task listener on ports 11940/19090/19091.
- The native package `openvpn.service` remains `active (exited)`, MainPID 0;
  that scaffolding is not a live VPN daemon.
- All six inventoried native packages retain the documented versions:
  OpenVPN `2.6.14-0+deb12u2`, dnsmasq-base `2.90-4~deb12u2`, libjansson4
  `2.14-2`, liblzo2-2 `2.10-2`, libnftables1 `1.0.6-2+deb12u2`,
  libpkcs11-helper1 `1.29.0-1`.
- Both `/var/lib/ld01-cvpn-<task>` and `/tmp/ld01-upload-<task>` exist for
  `cvpn7a1a8819b397`, `cvpn152283967635` and `cvpnb76f5884442f`. All six
  directories are 0700; the three `/var/lib` roots are root-owned. File metadata
  and source-script hashes were inventoried; keys, profiles, certificates and
  raw logs were not opened or copied.
- Host ports 20990/20991/20992 are closed. No task forward or capture was started
  by this inspection.

All **12 disposition/permission checks PASS** in `assessment.json`. This is a
point-in-time inactive-task inventory, not a VPN/functionality or cleanup rerun.

## Unverified and decision required

- Historical full configuration, endpoint, network-ID and volume-metadata equality
  cannot be established from the lost private baseline. Historical B8 stays
  deferred/unverified. Current full Docker metadata is retained privately, but has
  not been labeled or adopted as the new accepted baseline.
- Original local scratch contents and raw private reports remain unavailable.
  VM material retention does not reconstruct the lost local reports.
- Home data and current in-container state were not inspected; stopped-container
  inspection cannot establish daily shell, DNS or VPN behavior.

**Stop here as authorized.** Before any baseline-only live run, the user must
decide how to handle the missing scratch data/path and whether to authorize
starting the original stopped containers. Any empty replacement would be new
scratch data, not recovery of its previous contents. No restart, bind-layout
change, recreation or deletion is approved by this inspection. Baseline adoption
must follow an explicit decision and any needed authorized reconciliation.
