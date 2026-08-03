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

---

<!-- Appended by wave CG-ORG-POLICY-SIBLINGS-001: policy-model-aligned operator
     reference for the l9_schema: 2 canonical policy and its normative siblings. -->

# Quantum-L9 Organization Invariants

## Purpose

`ORG_INVARIANTS.yaml` is the canonical machine-readable organization policy.

It defines mandatory outcomes. It does not, by itself, prove that every outcome
is currently enforced.

## Related files

| File | Responsibility |
|---|---|
| `CANONICAL_LAW.md` | Constitutional governance authority |
| `ORG_INVARIANTS.yaml` | Mandatory organization policy |
| `governance/ASSERTION_TYPES.yaml` | Versioned assertion semantics |
| `schemas/org-invariants.schema.json` | Structural policy grammar |
| `governance/POLICY_MODEL.md` | Policy, control, and assurance model |
| `governance/TRUST_MODEL.md` | Trust and authority boundaries |
| `governance/CHANGE_PROCESS.md` | Policy-change procedure |
| `releases/POLICY_RELEASE.schema.yaml` | Immutable release-record contract |
| `ops/scripts/validate_org_policy.py` | Repository-local normative validation |

## Invariant anatomy

An invariant normally includes:

- a stable ID;
- title;
- domain;
- severity;
- lifecycle state;
- requirement;
- applicability;
- versioned assertion;
- violation behavior;
- control requirements;
- assurance state.

Released invariant IDs must not be reused for different meanings.

## Policy and enforcement

Policy answers: what must be true?

Implementation answers: what mechanism attempts to make it true?

Assurance answers: what current evidence proves the mechanism is effective?

These are separate claims. A policy can require blocking enforcement while
assurance truthfully reports that current enforcement is unverified or absent.

## Assertion vocabulary

Assertions resolve through `governance/ASSERTION_TYPES.yaml`.

Unknown critical or high-severity assertion semantics fail closed.

Changing evaluation semantics requires a new assertion version.

## Failure behavior

For critical decisions:

- unsupported semantics block;
- missing identity produces unknown;
- incomplete evidence prevents a verified claim;
- incomplete inventory prevents a complete-coverage pass;
- downstream weakening is prohibited.

`unknown` must not be silently converted to pass.

## Exemptions and bypasses

An exemption changes applicability for a scoped, approved, temporary case.

A bypass overrides an enforcement mechanism during an emergency.

They are not interchangeable. Canonical policy defines their constraints.
Platform-specific records and audit events belong in the systems that own those
deployments.

## Release process

An approved release binds the policy to:

- an immutable commit;
- policy, schema, and assertion-registry digests;
- independent approval;
- compatibility metadata;
- optional signature or attestation evidence.

Mutable branch references are insufficient for immutable blocking consumption.

## Repository ownership

Cursor-Governance owns normative policy and policy meaning.

It does not own:

- GitHub organization ruleset deployment;
- organization repository inventory;
- generalized CI execution;
- assurance reduction;
- consumer application implementation.

Those systems consume this policy through approved releases.

## Local validation

```bash
python3 ops/scripts/validate_org_policy.py
python3 -m unittest discover -s tests/org_policy -p 'test_*.py'
```

The validator checks:

- YAML and JSON parsing;
- schema structure;
- unique invariant and control IDs;
- assertion registry resolution;
- critical invariant completeness;
- control references;
- unsupported enforcement claims;
- release-schema safety.

It does not claim that external platform enforcement is active.
