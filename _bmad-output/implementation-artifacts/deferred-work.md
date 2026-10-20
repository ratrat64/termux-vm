- source_spec: `spec-controlled-vpn-trial.md`
  summary: Verify retained LD01 endpoint IP/MAC/gateway against authoritative original evidence if it becomes available (medium, unverified).
  evidence: Historical resources/final baseline retain exact container/network IDs, IPAM and destination-keyed mounts but omit endpoint fields; current run preserves full endpoint metadata. There is no demonstrated endpoint drift. An original full Docker inspection would settle the comparison.
- source_spec: `spec-detached-cleanup-authority.md`
  summary: Bound capture-child lifetime after arbitrary SIGTERM/SIGKILL loss of the privileged capture wrapper itself (medium, verified pre-existing limitation).
  evidence: Independent reviewer compared base 2293a9943a570ff627e07856581d3fea2f2df85f and changed CAPTURE using ordinary-user processes; both leave the child alive after wrapper-only SIGTERM or SIGKILL. The scoped fix restores SIGINT/exception finalization but does not claim survival of arbitrary privileged-wrapper death. Controller and detached-supervisor death remain bounded while the wrapper survives with its matching child.
