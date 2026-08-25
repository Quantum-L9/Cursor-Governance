# Autonomy contracts

First-class registry for the L9 autonomy family. Program Execution remains the
controller; autonomy and Peer Execution concurrency are subordinate.

| Concern | Canonical path | Authority |
|---|---|---|
| Authorization/control plane | `autonomy/` | owns no Program state |
| Surface doctrine | `ops/autonomy/surface_profile.yaml` | shared surface policy |
| L4 local gate | `ops/autonomy/l4_local.py` + gates | local execution/merge gate |
| Bounded concurrency runtime | `environment/program-execution/peer_execution/autonomy/` | shared execution mechanics only |

No provider adapter owns an autonomy or scheduler runtime. The former Claude
bounded scheduler has been promoted upstream into shared Peer Execution
infrastructure and no longer receives an adapter exemption.

SessionStart already injects `ops/autonomy/surface_profile.yaml`
`session_start_block` (this registry's surface-doctrine artifact). That block
is the wire: scoped local commit without asking; ask only before push /
`make pr`. Do not add a second activation path.

Validate with `make autonomy-contracts-validate` or `make autonomy-validate`.
