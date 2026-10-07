# Autonomy contracts

First-class registry for the L9 autonomy family. `autonomy/` owns the
provider-neutral authorization and bounded-concurrency runtime. Provider
adapters remain thin consumers.

| Concern | Canonical path | Authority |
|---|---|---|
| Authorization/control plane | `autonomy/` | owns no Program state |
| Surface doctrine | `ops/autonomy/surface_profile.yaml` | shared surface policy |
| L4 local gate | `ops/autonomy/l4_local.py` + gates | local execution/merge gate |
| Bounded concurrency runtime | `autonomy/` | provider-neutral admitted execution mechanics |

No provider adapter owns an autonomy or scheduler runtime. Cursor and Claude
Code bind through adapters to the root `autonomy/` implementation.

SessionStart already injects `ops/autonomy/surface_profile.yaml`
`session_start_block` (this registry's surface-doctrine artifact). That block
is the wire: scoped local commit without asking; ask only before push /
`make pr`. Do not add a second activation path.

`skills/l9-pr-remediation` consumes the surface-doctrine and merge-gate
artifacts. It does not own Program state and does not fork
`surface_profile.yaml`. Above-paygrade leftovers become a GitHub issue
plus `l9-issue-remediation`, not a human ask.

Validate with `make autonomy-contracts-validate` or `make autonomy-validate`.
