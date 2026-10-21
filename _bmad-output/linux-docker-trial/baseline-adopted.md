# Accepted post-reboot diagnostic baseline — private inputs prepared

**2026-10-20: baseline adopted by explicit user acceptance; private preparation
complete. No execution authorization, live window, VPN connection or diagnostic.**

Owner: OpenCode, branch `fix/n2-baseline-diagnostic`, durable worktree
`/home/rat/Git/termux-vm-n2-baseline-diagnostic`.

## Authority and provenance

The user accepted the inspected post-reboot running state, including empty
replacement scratch, current endpoints/NAT, no zombies and the retained inactive
A journal, and requested **private baseline inputs only**. Receipt/controller UTC:
`2026-10-20T13:48:45Z`. This timestamp is an adoption receipt, not a live window.

The inputs derive solely from the accepted durable inspection:
`/home/rat/.local/state/termux-vm-private/start-originals-20261020T134459Z/inventory.json`
and its 46-PASS `assessment.json`, with frozen-image and volume metadata from the
referenced earlier private read-only inventory. Original inspection records were
not rewritten. `adoption.json` records their SHA256 provenance and every generated
input's hash.

This is a **new post-reboot reference**, not recovered historical raw evidence or
proof of historical endpoint equality. Historical B8 remains unverified. The old
failed baseline cause remains unknown; adopting inputs does not resolve it.

## Durable private files

Directory: `/home/rat/.local/state/termux-vm-private/baseline-20261020T134845Z/`
(0700; all ten files 0600, outside Git).

| File | Purpose |
|---|---|
| `resources.json` | Accepted original A/B IDs, network IDs, frozen image and subnets |
| `image.json` | Retained frozen image metadata |
| `baseline.json` | Checked container runtime/mount/capability/device baseline schema |
| `retained-metadata.json` | Full accepted Config/HostConfig/endpoints and mounts |
| `residuals.json` | Empty A zombie list and exact retained restore/cleanup journal hashes |
| `network-state.json` | Inspected network/resolver/filter/NAT and journal observations; B permission limits retained |
| `volumes.json` | Accepted retained home-volume metadata |
| `networks.json` | Accepted running network metadata and peers |
| `input-paths.json` | Baseline paths/residuals for later use, explicitly not execution authority |
| `adoption.json` | User acceptance, provenance/input hashes, accepted differences, limitations and validation |

No `authorization.json`, live `start`/`deadline`, attempt directory, new PKI/profile
or credential was created. These input files alone cannot authorize execution.
New empty scratch is accepted at its existing temporary bind path; its old contents
remain lost, and another reboot may remove that replacement directory.

## Preparation and local verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 _bmad-output/linux-docker-trial/prepare-baseline-inputs.py \
  --accepted-inventory /home/rat/.local/state/termux-vm-private/start-originals-20261020T134459Z/inventory.json \
  --output /home/rat/.local/state/termux-vm-private/baseline-20261020T134845Z \
  --acceptance-receipt 2026-10-20T13:48:45Z
```

**PASS:** diagnostic input schema/paths, saved-snapshot `reconcile()`, network
ID/IPAM/peer checks, no zombies, inactive PASS/off retained journals, permissions
and provenance/input hashes. Runtime command functions are trapped during
preparation; **zero Docker/GCP/socket/probe operations** occurred. Product code
was unchanged by input preparation.

These checks validate consistency with the accepted saved inventory, not resource
freshness at a later launch. Future preflight must compare current resources to
this accepted reference and reject drift rather than auto-adopt it.

## Remaining gate

The baseline-only implementation remains offline-verified (87 tests). The next
step is separate explicit authorization for one baseline-only normal connect/
check/disconnect from the authenticated operator terminal, scoped capture and
supervised abort/expiry cleanup, within a fresh fixed window of at most 30 minutes
including ten minutes reserved for cleanup. No F1/F2 injection or reconnect is
included. No such approval/window has been requested or created by this action.
