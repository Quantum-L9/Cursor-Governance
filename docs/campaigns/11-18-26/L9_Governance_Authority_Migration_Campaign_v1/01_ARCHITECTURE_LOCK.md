# Frozen architecture and ownership decision

## Why this campaign exists

On inspected main revisions, `Quantum-L9/.github/semantics/authority_model.yaml` assigns global governance, control and distribution authority to `.github`, while `Cursor-Governance/ORG_INVARIANTS.yaml` still declares `canonical: true` and a Cursor-Governance canonical path. Its assertion registry, release schema, docs, `CANONICAL_LAW.md` and `AGENTS.md` likewise claim organization authority. This is an authority collision, not a missing agent rule.

## Authority and physical owners

| Concern | Single owner | Consumer / execution boundary | Rule |
| --- | --- | --- | --- |
| Cross-domain L9 semantics, global invariants, authority, admission | `.github/semantics/*` | Verified projections, explicit admission | Leave global law canonical here; do not restate `L9-ORG-*` as global constitutional invariants. |
| Organization operational requirements, assertion meaning, policy grammar and releases | `.github/policies/` or evidence-justified equivalent existing `.github` policy owner | Read-only immutable releases and locally verified bindings | Migrate intact `L9-ORG-001..013` meaning, correcting contradictions through one reviewed successor. |
| Organization repository inventory/class | `.github/semantics/repository_registry.yaml` and class policy owner | Organization inventory and class-aware controls | Membership inventory and enforceable policy scope are separate evaluations. |
| CTO, architect, planner, coding agents, agent adapters, autonomy, skills, hooks and publication | `Cursor-Governance` | Applies upstream law to real operating actions | Local `CANONICAL_LAW` remains operative only in this subordinate scope. |
| Required CI workflow, orchestrator and trust boundary | `l9-ci-core` | Already-required `Analyze (central Core)` where eligible | Integrate policy assertion at the existing required job if safely possible; no parallel CI governor. |
| Technical gate semantics and evidence | `l9-ci-sdk` | Core consumes | Read only in this campaign. |
| Required-workflow attachment and bypass configuration | GitHub org ruleset; `.github/rulesets/*` holds intended config | Actual GitHub API state and merge failures | A committed ruleset JSON cannot prove deployment. |
| Legacy owner invariant check | `L9-Ops-MCP` | Its existing `scripts/validate_org_invariants.py` | Adapt generated mirror to upstream policy without breaking its founder/birth check. |

## No-copy / no-self-admission law

- Current `l9.projection/cursor-governance-operating-plane@2` carries global semantics through its existing eight source classes. That profile does **not** include an organization-policy source class. A dedicated local org-policy release binding is preferable to gratuitously versioning the semantic profile. Reverify profile and bundle currentness independently.
- `Cursor-Governance` may keep a derived, read-only `ORG_INVARIANTS.yaml` at its old path for compatibility, but its `canonical` state, source and provenance must truthfully identify `.github`; its schema and validator must not keep reclassifying it as canonical.
- `governance/ASSERTION_TYPES.yaml`, `schemas/org-invariants.schema.json` and `releases/POLICY_RELEASE.schema.yaml` must not remain competing organization-wide normative sources. Preserve only compatible read-only snapshots or consumer verifier contracts if truly required by existing callers.
- An upstream policy release must be admitted by the true `.github` owner on the exact subject; an agent, validation, PR creation or authored ADR cannot admit itself. Release and distribution are distinct.
- Never invent new shared identity, admission, receipt, CI, attestation, runtime or action-routing layers to solve a file ownership mismatch. Reuse existing source/validator/release mechanisms unless a concrete counterexample proves insufficiency.

## Authorization and human involvement

Maintain L9-ORG-007's intended rule: a single authenticated authorized human owner may authorize the exact governance change and may also be its author; there is no automatic two-human approval tax. Neither a CTO agent nor its own credentials manufacture owner authorization. Upstream global authority also requires a digest- or exact-revision-bound owner decision. A general launch instruction starts work but does not stand in for a later exact-head decision if required by the live release contract.

Do not turn this migration into an autonomy rollback. Agents may make bounded decisions and keep executing within their grants; only owner-only governance admission, bypass and unverifiable external permissions escalate. The external required check controls merges independently of the operating agent.

## Controlled cutover states

1. `CURRENT_LEGACY`: Cursor policy canonical in source, upstream source absent. No future claim about .github ownership until admitted.
2. `UPSTREAM_ADMITTED`: exactly one `.github` source of normative policy, but no assertion that downstream release is usable until immutable release proof exists.
3. `RELEASED`: signed/attested immutable bundle and owner decision verified, content/metadata digests bound.
4. `CONSUMERS_BOUND`: Cursor and legacy consumer use sealed upstream release, and stale/missing/unknown is not silently accepted.
5. `ENFORCED`: independent required CI and/or other applicable control proves failing cases prevent relevant operations, with live platform evidence.
6. `CLOSED`: every mandatory invariant/control either evidenced or classified as an unresolved blocker; only an all-green, exact-scope proof supports `PASS`.

These are campaign operational labels, **not new L9 canonical lifecycle or result enums**. A stage label is evidence bookkeeping and never an admission decision.

## Explicit exclusions

No restructuring the global Semantic Foundation; no new product/market domain semantics; no rewriting Core/SDK technical scoring; no replacement CI architecture; no mass editing agent skills, per-consumer workflows, or random repositories; no repository creation; no changes to provider secrets/credentials except using an already-approved trusted process; no direct publishing bypass.
