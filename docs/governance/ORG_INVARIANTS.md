<!-- --- L9_META ---
l9_schema: 1
artifact_type: governance_doc
component: org_invariants_ssot
tags: [governance, org-invariant, ssot, quantum-l9]
retrieval: on_demand
status: active
--- /L9_META --- -->

# Org Invariants — Single Source of Truth

The canonical Quantum-L9 organization invariant policy lives here:

- **Canonical file:** [`ORG_INVARIANTS.yaml`](../../ORG_INVARIANTS.yaml) (repo root of `Quantum-L9/Cursor-Governance`).

This is the governance control plane, so the org invariant policy is canonical
here and mirrored into consumer repos. It is **policy, not enforcement** — the
enforcement lives in each consumer's deterministic gate.

## The invariant

All repository routing/birth stays under `https://github.com/Quantum-L9/`.
Personal-account owners (e.g. `cryptoxdog`, `personal_accounts`) are
`forbidden_owners`; violations are `BLOCKED` (fail-closed).

## Topology

```text
Quantum-L9/Cursor-Governance/ORG_INVARIANTS.yaml   (CANONICAL — edit here)
        │  synced (byte-identical org_invariants block)
        ▼
Quantum-L9/L9-Ops-MCP/ORG_INVARIANTS.yaml          (MIRROR — do not edit here)
        └── enforced by scripts/validate_org_invariants.py  (CI gate)
```

## Change process

1. Edit the `org_invariants` block in the canonical file (this repo).
2. Re-sync each consumer's mirror so its `org_invariants` block is
   **byte-identical** (in the same PR or an immediate follow-up).
3. Consumer gates (e.g. `L9-Ops-MCP/scripts/validate_org_invariants.py`) continue
   to validate their local mirror — no network dependency in CI.

## Adding a consumer

Add the repo under `provenance.consumers` in the canonical file, copy the
`org_invariants` block into that repo (with a mirror-provenance header), and wire
its gate to validate the local copy.

> Enforcement stays deterministic and repo-local. This SSOT governs **where the
> policy is authored**, not how it is checked.
