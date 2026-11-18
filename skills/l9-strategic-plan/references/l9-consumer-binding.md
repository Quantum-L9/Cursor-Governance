# L9 Strategic Plan: repository-owned skill and canonical projection handoff

## Status and authority boundary

**Candidate skill pack, not admitted or installed as a repo consumer.** The installed `strategic-planner` skill was the baseline. The operator selected `Quantum-L9/Cursor-Governance` as the authoritative source for its successor, named `l9-strategic-plan`. An uploaded ChatGPT copy must be distributed from a pinned, published source revision. The naming decision is not a grant to execute or admit strategy.

At preparation, inspected revisions (observations only, re-resolve before handoff):
- `Quantum-L9/.github/main@dd780b957b301acf5443013708105b7a76e3aa7b`, `semantics/domain_consumer_bindings.yaml` and `semantics/projection_profiles.yaml`.
- `Quantum-L9/Cursor-Governance/main@73683ecae82e8ecd30f66cf8c6bb0e10e565410f`, where `skills/l9-plan` and `skills/l9-plan-simple` implement execution planning, not strategic planning.
- `Quantum-L9/l9-graphiti-memory/main@d4775a9222871143782bb2a9ddc035ef96d832a3`.

Semantic owner: `.github` canonical `semantics/` under its admission process. Skill owner: Cursor-Governance `skills/l9-strategic-plan/`. Memory owner: `l9-graphiti-memory`; Plan owner and strategy admission remain separately resolved. **The repository is not registered merely by packaging this skill.**

## Why the old binding cannot be reused as-is

`l9.domain-consumer-binding/strategic-planner@1` is admitted and immutable. It declares `identity: strategic-planner` and `repository_ref: unresolved`, `entrypoint: unresolved`, and `predecessor_migration_dispositions` unresolved. It does not match the successor `l9-strategic-plan` entrypoint identity. Do not edit @1 or fabricate coordinates to make it pass.

Owner-facing handoff after committing this pack to Cursor-Governance:
1. Pin the actual commit and the `skills/l9-strategic-plan/SKILL.md` SHA-256; verify the skill directory and registered GitHub repository coordinate.
2. In `.github`, propose **a versioned successor** (candidate `l9.domain-consumer-binding/strategic-planner@2`, subject to canonical registry/versioning rules) with kind `skill`, identity **`l9-strategic-plan`**, `repository_ref` resolving `l9.repository-registry/global@1#cursor-governance`, and exact `entrypoint.path: skills/l9-strategic-plan/SKILL.md`. Do not assert a future revision or entrypoint digest before commit exists.
3. Preserve the six required domains from @1: `strategic-value@1`, `architecture@1`, `signals@1`, `governance@1`, `evidence-provenance@1`, `capabilities-dependencies@1`. Preserve the conditional `contracts-conformance@1` and `identity-attribution@1` on explicit task requirements. The full IDs carry `l9.projection/` prefixes.
4. Adjudicate all **14** uncovered predecessor selections against exact canonical records and decide `retain`, `equivalent`, or `separately_required`; do not silently discard either authority or game-theory content. See below. A domain-set profile is not a drop-in replacement until the migration proof exists.
5. Use the real Semantic Compiler at an admitted compatible revision to produce the actual domain source projections, composed artifacts, individual receipts and compatibility/provenance evaluation for the binding; no synthetic or ChatGPT-authored PASS receipts.
6. Verify the composed inputs at the installed skill in **both** Cursor-Governance and ChatGPT as distinct host/installation tests, with pinned skill source, artifact digests, canonical source commit, and source-class coverage. Record failures and absent capabilities as BLOCKED. Only after this may the distribution be described as **consumer bound**.
7. Repackage this skill **with the verified projection materials and machine-readable receipt/lock** and upload the exact versioned distribution to ChatGPT. If ChatGPT host integration requires a separate identity or source declaration, record that correspondence instead of assuming it.

Recommended placement for subsequently generated consumer bundle: `generated/l9-strategic-plan/` inside this skill directory. This is a **proposed output location**, not an existing producer contract. Let the real producer determine precise layout and keys. No bundle or receipt is shipped in this candidate ZIP.

## Predecessor migration closure, 14 exact selections

The `.github` evidence at `docs/candidates/domain-projection-architecture-v1/evidence/migration_equivalence.json` identifies **2 authority_model** paths:
- `$.strategic_authority`
- `$.strategic_cognition_authority`

And **12 vocabulary** paths:
- `$.terms.actor_response_model`
- `$.terms.conditional_best_response`
- `$.terms.deviation_gain`
- `$.terms.equilibrium_assessment`
- `$.terms.incentive_bearing_commitment`
- `$.terms.incentive_compatibility`
- `$.terms.information_disclosure_decision`
- `$.terms.policy_exploitability`
- `$.terms.strategic_game_model`
- `$.terms.strategic_interaction`
- `$.terms.strategic_interaction_assessment`
- `$.terms.strategy_profile`

**Candidate disposition, not proof:** retain the legacy `l9.projection/strategic-planner-value@1` and applicable Plan Keeper authority context for the two authority coordinates; retain `l9.projection/strategic-planner-interaction@1` for the twelve game-theory terms when strategic interaction analysis applies. Reconcile source selection by task, prove equivalent or retained coverage, then declare any old selector retired. Do not force all tasks into quantified Strategic Value or GT analysis. The Plan Keeper profile `l9.projection/strategic-planning-context@2` is not automatically the Planner skill's binding.

## Canonical compatibility boundary

The binding references `l9.contract/domain-composition-compatibility@1` and `l9.contract/domain-composition-provenance@1`. Required checks include exact domain profile identities/digests, common governing revision or explicit compatibility, source identity/equivalence, required dependency closure, preserved Unknown, and source/profile/binding/contract/engine provenance. Invalid, missing, or stale inputs must not be treated as compatible. Compiler feature presence is **not presumed** from package version; execute an actual contract test. No duplicate selector engine, composer, or ad hoc profile JSON in this skill.

## Acceptance states

- `SOURCE_NOT_REGISTERED`: Cursor-Governance entrypoint has not been committed/resolved.
- `BINDING_NOT_ADMITTED`: successor is proposed, not admitted.
- `PREDECESSOR_MIGRATION_UNRESOLVED`: some of the fourteen selectors have no proven disposition.
- `PROJECTION_NOT_VERIFIED`: compilation/receipt or consumer replay is absent, failed, or stale.
- `CONSUMER_VERIFIED`: independently verified current source, projection and consumer replay with exact receipts, without asserting strategy admission.

Each blocked state is truthful and useful. Local tests of this ZIP prove **skill packaging and existing scripts only**.
