# LD01 Gate 4 — offline private inputs verified and reviewed

**Offline construction and read-only revalidation PASS. Final-source live
validation: NOT RUN.** Reconciliation is limited to the exact accepted saved Gate 3
reference. All four independent workflow review layers completed; no unresolved
implementation finding remains.

Owner: OpenCode. Branch: `chore/ld01-gate4-private-inputs`. Worktree:
`/home/rat/Git/termux-vm-ld01-gate4-private-inputs`. Exact base:
`111162f9ec05f767e01879449ebcef64725e992a`.

## Work and verification

- [Task spec, verification and review triage](../implementation-artifacts/spec-ld01-gate4-private-inputs.md).
  Current input consumers and the historical preparation script were read-only
  format references; no implementation source or tests changed.
- Replayed the offline evidence audit: **435 saved JSON files / 1,364 checks PASS**.
  The exact accepted summary, prior-inspection hashes, Gate 2/3 provenance,
  separate retention continuation and final explicit-residual validation agree.
- Created one exclusive private directory with 19 files: mode 0700, every file
  regular/nonsymlink and 0600. Required resources/image/baseline/full retained
  metadata/residuals and supporting saved observations, provenance and hashes pass.
- Current `diagnostic_inputs()` and saved-data `reconcile()` read-back pass, with
  original IDs/image/configuration/mounts, exact network peers/IPAM, volume labels,
  full retained endpoints and exact residual schema. Additional journal source/intent
  hashes and process/start context remain in separate provenance.
- **31 in-memory negative checks PASS**, covering integrity/acceptance/schema/drift,
  observation time, invented host-link metadata, private permissions, process/network
  audit traps and denied runtime helpers. Read-only revalidation additionally passes
  two write-open/mkdir guard checks using audit events without filesystem mutation.
- Original observations/command times, acceptance, differences and limitations are
  preserved privately. The empty replacement scratch is new data, not recovered
  history. Completion flags were set only after successful saved-data reconciliation.

Saved host links are copied byte-for-byte, with accepted peer/index/endpoint
comparisons preserved and no inferred `linkinfo` value. **Detailed live veth-kind
validation is UNVERIFIED and remains required at fresh Gate 5 admission.** It is
not an input-schema requirement; the task spec records the corrected scope.

## Exact private paths

New private baseline directory:

`/home/rat/.local/state/termux-vm-private/ld01-gate4-private-inputs-20261021T140731404796Z/`

Files under that directory:

- `input-paths.json`: exact baseline/retained-metadata paths, residuals and offline
  reconciliation flag; not execution authorization.
- `resources.json`, `image.json`, `baseline.json`, `retained-metadata.json`,
  `residuals.json`: required controller inputs.
- `containers.json`, `networks.json`, `volumes.json`, `network-state.json`,
  `host-snapshot.json`, `host-links.json`, `container-links.json`, `vm-retained.json`:
  supporting saved observations.
- `provenance.json`, `evidence-hashes.json`, `validation.json`, `adoption.json`:
  original acceptance/observation provenance, source/output hashes, limitations and
  completed offline validation. Full contents and new digests remain outside Git.
- `prepare-offline.py`: retained runnable checker source, identical to
  `/tmp/opencode/ld01-gate4-offline.py`.

Read-only rerun, already executed successfully:

```sh
python3 /home/rat/.local/state/termux-vm-private/ld01-gate4-private-inputs-20261021T140731404796Z/prepare-offline.py \
  --verify-existing /home/rat/.local/state/termux-vm-private/ld01-gate4-private-inputs-20261021T140731404796Z
```

It rechecks evidence, all 19 outputs, hashes, permissions, provenance, consumers
and negatives, with filesystem-write/process/network traps. It creates no output.

Original summary and acceptance remain respectively under the private siblings
`ld01-gate3-retention-continuation-20261021T132743138902Z/` and
`ld01-gate3-accepted-validation-20261021T133326030075Z/`.

## Publication and remaining live gates

Four independent review layers completed; no implementation patch or deferred item
was required. Coordinating and independent read-only validation PASS. Only this
handoff and the new task spec are publishable changes; diff/redaction and whitespace
checks pass. Publication is authorized only on `chore/ld01-gate4-private-inputs`;
the completion report supplies the actual final commit and push result.

No runtime command, live controller/preflight/idle check, resource or scratch change,
credentials/profiles, execution authorization/window or attempt occurred. Gate 5
requires separate final-source approval, fresh admission (including detailed veth
kind) and explicit live authorization. No freshness, live-admission, B-firewall
equality or historical-repair claim is made. Historical **baseline FAIL / cleanup
PASS** and later **baseline FAIL / cleanup FAIL** remain unchanged; historical
**124 offline tests PASS** was not rerun or presented as new proof.
