# Autonomy contracts (first-class)

Cursor-primary registry for the **L9 autonomy family**. Runtime brains stay in
their live homes; this tree registers, documents, and fail-closes discovery.

| Path | Role |
|------|------|
| [`MANIFEST.yaml`](MANIFEST.yaml) | First-class autonomy family registry |
| [`meta/`](meta/) | Per-artifact metadata sidecars (`first_class_artifact: true`) |

## Family map (SSOT per concern)

| Concern | Canonical path | Notes |
|---------|----------------|-------|
| Control plane (campaigns, leases, gateway) | `autonomy/` | PE provider `root-autonomy-control-plane`; `owns_program_state: false` |
| Surface doctrine + A4 velocity | `ops/autonomy/surface_profile.yaml` | Do not fork prose into adapters/skills |
| L4 local gate / merge gate | `ops/autonomy/l4_local.py` + gates | All surfaces; mid-exec push denied until release |
| Claude bounded scheduler | `environment/agents/adapters/claude-code/autonomy/` | E14 sibling — not a copy of root `autonomy/` |

## Law

1. **Program Execution is the controller.** Autonomy is subordinate and must not
   outlive a Program lease (`environment/agents/PEER_EXECUTION.md`).
2. This directory is **repo SSOT for the family registry** — not a second
   control plane and not a place to relocate Python runtimes.
3. Skill/command paths may **point here**; they must not invent a parallel
   `surface_profile.yaml` or revive `environment/claude-code/autonomy/`.
4. Validate with `make autonomy-contracts-validate` (wired into
   `make autonomy-validate` and `make program-execution-conformance`).

## Execute path

```text
.plan.md instance
  → @environment/program-execution
  → @autonomy (subordinate Program lease; family MANIFEST)
  → PE adapter
```

Related: executable plan template lives under `environment/contracts/execution/` when promoted;
see CANONICAL_LAW §1 and skill `l9-plan`.
