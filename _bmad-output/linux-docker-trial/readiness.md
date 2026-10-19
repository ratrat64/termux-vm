# LD01 readiness and evidence ledger

Date: 2026-10-19, updated after authorized tooling build and baseline. This non-secret ledger separates original preparation observations from the new bounded runtime results in [execution-results.md](execution-results.md). Runbook: [next-trial.md](next-trial.md).

## Initial preparation observations (before build/baseline authorization)

| Check | Result | Observation and limit |
|---|---|---|
| Dedicated Git ownership | PASS | `docs/linux-docker-trial-preparation`, `/tmp/opencode/termux-vm-linux-docker-trial-preparation`, base `c6dc04f`; owner in [task-owner.md](../task-owner.md). No other task's files edited. |
| Coordination boundary | RECORDED | User chose fresh resources. Original owner has not acknowledged retained-resource/material reuse; no ownership transfer claimed. |
| Docker availability | PASS, preflight only | Read-only `docker version`: client/server 29.1.3. Default context endpoint `unix:///var/run/docker.sock`; `docker info`: Ubuntu 26.04.1 LTS, kernel `7.0.0-38-generic`, AppArmor/seccomp/cgroupns security options. No runtime privilege/containment proof. |
| Host identity/TUN | PASS, preflight only | `uname -srmo`: Linux `7.0.0-38-generic`, x86_64 GNU/Linux. Current UID/GID 1001:1001. `test -c /dev/net/tun` exited 0. Container TUN use remains NOT RUN. |
| Immutable foundation available | PASS, preflight only | `docker image inspect` found `sha256:831666c75ae440c43933711269a44181e946e6bec156e7e1dddd3c8002886afb`, linux/amd64, default user 1001:1001. No tooling/image build ran. |
| Proposed name collision check | PASS, point-in-time only | Filtered container/network/volume listings for `tvm-share-ld01-` returned no resources. Recheck before creation; not a reservation. |

These checks did not read private staged files, execute in retained containers, resolve a company endpoint, install packages, create Docker resources, connect a VPN or modify networking. The current host VPN/routes/DNS, credential readability/expiry and actual CLI backends were not inspected. Historical host underlay state is not a current baseline.

## Imported evidence — previously observed, not rerun

Source: original [foundation-results.md](file:///home/rat/Git/termux-vm-isolated-terminal-evaluation/_bmad-output/planning-artifacts/research/technical-isolated-terminal-sessions-2026-10-19/trial/foundation-results.md), [material validation](file:///home/rat/Git/termux-vm-isolated-terminal-evaluation/_bmad-output/planning-artifacts/research/technical-isolated-terminal-sessions-2026-10-19/sonrisa-material-validation.md), and the extension's [prior-evidence digest](file:///tmp/opencode/termux-vm-environment-sharing-evaluation/_bmad-output/planning-artifacts/research/technical-environment-sharing-2026-10-19/imports/prior-evidence.md), all dated 2026-10-19.

| Prior result | Preserve its actual scope |
|---|---|
| Foundation PASS | Same image; distinct host/A/B network namespaces; non-root shells; private home markers; selected actual shared-file edit/delete visibility; persistence through recorded lifecycle operations. |
| Limited Git PASS | Shared unborn HEAD name only, not committed branch checkout or application/account state. |
| Limited continuity PASS | One B-to-host established TCP connection survived A restart/recreation. Not external host/B session continuity through VPN toggles. |
| Baseline network PASS | Public IPv4 TCP/name resolution and recorded unchanged pre-existing route/DNS settings under the original trial. No live IPv6 route then; no private DNS or VPN failure proof. |
| Offline materials passed | Prior certificate/key match and integrity, chain/purpose and TLS-crypt format; client expiry recorded 2027-06-23. Not current readability, server acceptance, revocation, concurrent-session permission or permission for this task to access/mount them. |

The research extension ran **no new runtime trials**. Its corroborated mechanisms and documentation are not additional runtime passes.

## LD01 and remaining acceptance — current status

`BLOCKED` means a prerequisite is unresolved; the check has not run. Only LD01-T and LD01-F have runtime passes; LD01-M is a separate bounded material-readiness pass. All VPN/account acceptance remains unrun. Use the original trial IDs alongside these narrower subcheck IDs, without overwriting historical results.

| ID | Mode/layout | Status | Prerequisite or exact remaining limit |
|---|---|---|---|
| LD01-T | Common tooling | PASS | Authorized Ubuntu package build; frozen image and exact package inventory in execution results/private evidence. No intended account CLIs selected yet. |
| LD01-F | Fresh private A/B homes + shared scratch | PASS | Authorized fresh contexts: namespaces, non-root joined shells, home separation, scratch visibility, DNS/public IPv4 and A TUN checked. No lifecycle recampaign or VPN proof. |
| LD01-M | Current staged-material readiness | PASS, bounded | After user-relayed owner clearance and scoped permission: host-user metadata/openability for five files and current CA/client expiry checks passed. No daemon-readability, server/session or connection proof; see [vpn-stage-readiness.md](vpn-stage-readiness.md). |
| LD01-J | S1 joined shells, no account acceptance | BLOCKED | Ordinary joined-shell subcheck passed; approved VPN controls/config still missing, so shared connect/disconnect/reconnect NOT RUN. |
| LD01-C | N1 partial, A VPN / B ordinary | BLOCKED | Owner clearance and conditional permission now recorded; actual single-session time/conflict confirmation and G5 targets/policy missing. Config/control/daemon-readable credential layout unresolved; same-socket external continuity NOT RUN. |
| S1 complete | Joined environment | BLOCKED | Intended CLI/version/backend and authorized real account identity checks in both shells missing. |
| S2 | Live-shared app state, independent networking | BLOCKED | Actual tools/stores/concurrency and independent VPN runtime design unspecified; no real application sharing/concurrency trial. |
| S3 | Consistent copied + fresh state | BLOCKED | Complete state set, writer quiescence/export boundary and authorized identities required; no copy/divergence/portability or fresh-account trial. |
| N1 complete | All four A/B VPN combinations, required full/split policies | BLOCKED | B-side session/profile and approved policies/targets required; no cycle executed. Company concurrent-session acceptance stays blocked if only a fixture is available. |
| N2 | DNS/failure blocking/recovery | BLOCKED | Intent-sensitive firewall/resolver design, canaries and fault permissions required. No startup/auth/failure/reconnect, packet containment or existing VPN-bound flow checks. |
| N3 Linux | Restricted controls + persistence | BLOCKED | Narrow target-bound control interface unspecified; unrestricted Docker access is not proof. No VPN-owner/image-replacement persistence checks. |
| W1 / N3 WSL2 | Target Windows/WSL2 | NOT RUN | No Windows/WSL2 target supplied. Linux observations do not close this gate. |
| Other VPN families | Client-specific acceptance | NOT RUN | Stock OpenVPN scope only; no vendor-client behavior inferred. |

## Execution record format

Actual timestamped raw/private baseline evidence is outside Git in `/tmp/opencode/linux-docker-sharing-ld01.r9oRt6uM/`. For subsequent authorized execution, append one redacted row per observed check, never promote an entire block based on a narrower subcheck:

| ID | Mode/layout | Immutable image / client version | Expected policy | Timestamped redacted observation | Evidence path | PASS / FAIL / BLOCKED / NOT RUN | Exact limit |
|---|---|---|---|---|---|---|---|

For continuity retain same-socket identifiers, sequence acknowledgements, timestamps and unexpected reconnect/reset/error counts. For DNS retain application resolver path, upstream/interface and expected/actual answers. For any later leak verdict retain scoped packet/counter evidence and interval; a timeout alone is insufficient.

## Preparation checks

- PASS: Python standard-library assertions checked all three preparation Markdown files, all 12 link targets, trailing whitespace/final newlines, G0–G5 and acceptance-row coverage, and explicit unrun/coordination qualifiers. This included untracked files.
- PASS: `git worktree list`, `git status --short --branch` and `git rev-parse HEAD` confirmed the dedicated branch/worktree at `c6dc04f465fc91aab10e7cc7d5861dd853109420`; only the new untracked `_bmad-output/` is present in this worktree. `git diff --check` passed for tracked changes (none); it does not check untracked files.

Those checks describe the initial documentation-only preparation. The subsequent image build, runnable positive baseline and deliberate negative checker proof are recorded in [execution-results.md](execution-results.md). Credential access, VPN/account testing and WSL2 validation remain unrun.

## Final build/baseline verification

- PASS: all six Markdown artifacts, 23 existing local/file link targets and whitespace/final newlines; Python syntax compiled in memory and AST confirmed no optimization-removable assertions in the runnable checker.
- PASS: final real-image baseline and optimized wrong-image rejection evidence inspected; descriptive negative error and retained bounded runtime configuration present. Private evidence directory is 0700 and all immediate evidence files are 0600.
- PASS: task-labeled A/B remain running on the frozen image; A's final `ip -j tuntap show` returned `[]`, confirming the checker left no test TUN interface. Git reports only this task's untracked `_bmad-output/`; tracked whitespace check passes.
- Required read-only review completed; seven actionable findings patched and verified, none deferred. Implementation spec contains all verdicts and evidence. No commit/push/PR requested or performed.
