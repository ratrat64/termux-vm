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

## Continuation verification

- PASS: seven Markdown artifacts, 27 local/file link targets, whitespace/final newlines and the bounded five-file/two-certificate private evidence record checked; evidence file mode is 0600.
- PASS, read-only runtime comparison: existing A/B container IDs, image IDs, capability grants and destination-keyed mount metadata match the final baseline. An initial order-sensitive mount-list comparison flagged apparent drift; follow-up inspections demonstrated Docker can reorder the mount array while the full destination-keyed mount entries remain identical. No actual configuration drift was observed. No container mutation or baseline probe rerun was needed.
- BLOCKED: connection until actual window/conflicting-session confirmation, targets/policy and daemon/resolver/control configuration are supplied. No original private key content, profile details or company endpoint was emitted. No commit/push/PR requested or performed.
