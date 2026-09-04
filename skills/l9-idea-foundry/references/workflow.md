<!-- L9_META
l9_schema: 1
parent: l9-idea-foundry
layer: reference
role: workflow
tags: [foundry, resume, recompile]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# Foundry workflow and recovery routing

## Contents

- [State path](#state-path)
- [Earliest-invalid-layer repair](#earliest-invalid-layer-repair)
- [Material progress](#material-progress)
- [Compiled-intent rule](#compiled-intent-rule)
- [Planning rule](#planning-rule)
- [Harvest rule](#harvest-rule)
- [Code-realization depth](#code-realization-depth)
- [Incremental resume and recompile](#incremental-resume-and-recompile)
- [Regulated products](#regulated-products)
- [Scaffold rejection test](#scaffold-rejection-test)

## State path

```text
INTAKE
  -> AUTHORITY_MAP
  -> BENEFICIARY_PROFILE
  -> OPTIONAL_HARVEST
  -> IMPLEMENTATION_MODEL
  -> COMPILED_INTENT
  -> PLAN_SIMPLE
  -> CODE_REALIZATION
  -> LOCAL_VALIDATION
  -> FOUNDRY_INDEX
  -> PAYLOAD_FREEZE
  -> BIRTH_PAYLOAD_COMPILE
  -> LOCAL_BIRTH
  -> OPTIONAL_REMOTE_BIRTH
  -> STOP
```

## Earliest-invalid-layer repair

Route failures to the earliest invalid layer instead of patching downstream symptoms.

| Failure | Return to |
|---|---|
| Missing/contradictory source authority | AUTHORITY_MAP |
| Unknown existing L9 owner / duplicated responsibility risk | BENEFICIARY_PROFILE |
| Bad donor reconstruction / nonportable nugget / beneficiary mismatch | OPTIONAL_HARVEST |
| Wrong ownership, boundary, stack, or first-order direction | IMPLEMENTATION_MODEL |
| Compiled intent differs from accepted authority/architecture | COMPILED_INTENT |
| Plan scope, file binding, dependency, or validation defect | PLAN_SIMPLE |
| Code violates accepted plan/blueprint | CODE_REALIZATION |
| Tests weak, stale, or non-discriminating | LOCAL_VALIDATION |
| Generated index differs from indexed artifacts | FOUNDRY_INDEX |
| Staging tree differs from external freeze receipt | PAYLOAD_FREEZE |
| Birth payload contract mismatch | BIRTH_PAYLOAD_COMPILE |
| Template/chassis/org local gate failure | LOCAL_BIRTH or template owner |
| Remote org attestation/enrollment failure | preserve template-observed remote state |

## Material progress

Progress is new discriminating evidence, corrected source authority, clarified upstream ownership, a qualified Harvest disposition, improved architecture, changed compiled intent, validated plan improvement, changed implementation, stronger validation, or a resolved blocker.

More narration, repeated validation without state change, and adding TODOs are not progress.

## Compiled-intent rule

After `IMPLEMENTATION_BLUEPRINT.yaml` is accepted:

- treat it as `PRE_CODE_SSOT`,
- use raw source files only as evidence cited by the blueprint/authority map,
- do not let Plan Simple, code realization, or a later model independently reconstruct product intent from the full raw pack,
- re-enter the earliest invalid layer when a new user instruction, source change, or contradiction invalidates compiled intent.

This reduces repeated context and prevents semantic forks.

## Planning rule

Nontrivial idea-to-code work requires a validated `l9-plan-simple` `PLAN_DOCUMENT` before material code realization.

Prefer first-class `EMBEDDED` planning when the live Plan Simple contract proves it exists. Otherwise use the bounded `EMBEDDED_PRE_BIRTH` compatibility path and mark it explicitly. Never fabricate a stacked PR or PR URL during pre-birth planning.

If Plan Simple cannot be invoked or validated under an authorized mode, block at planning rather than creating a parallel planner inside Foundry.

## Harvest rule

Harvest is conditional, not ceremonial. Run it when donor semantics and beneficiary fit are material. Skip it when the pack is already a direct implementation spec and semantic transfer produces no new decision evidence.

A Harvest result may change reuse, architecture, acceptance tests, or plan scope. It cannot override pack authority.

## Code-realization depth

Choose depth from locked idea scope:

- **Seed:** one real core primitive and repository shape.
- **Vertical slice:** preferred default; one end-to-end user outcome.
- **MVP compile:** only when MVP scope is explicitly locked and requested.

A roadmap is not permission to implement the roadmap.

## Incremental resume and recompile

When `docs/idea-origin/FOUNDRY_INDEX.json` already exists, read [recompile.md](recompile.md) before repeating completed work.

The index exists to reuse verified intermediate results whose inputs are unchanged. It never authorizes reuse when external ownership evidence is stale, a Plan Simple baseline no longer matches, current operator intent changed, or the exact payload state changed.

Do not regenerate downstream artifacts merely to obtain new timestamps or formatting. Reuse stable semantic results and invalidate only from the earliest changed layer.

After remote birth, stop using Foundry as the normal development workflow. The index remains origin evidence and a fast context hydrator; current repository law and ground truth own future implementation.

## Regulated products

For legal, tax, finance, health, safety, or other regulated domains:

- encode authority/version/provenance boundaries before advisory logic,
- keep deterministic rule engines separate from model-mediated interpretation,
- gate unsupported jurisdictions or rule versions closed,
- use synthetic/de-identified fixtures in local acceptance tests,
- do not manufacture a license, reviewer, jurisdiction, policy, or approval,
- continue independent infrastructure that does not rely on the unresolved regulated fact.

## Scaffold rejection test

Code realization fails when the selected slice cannot be demonstrated without reading TODO comments, mentally supplying missing behavior, or accepting a local copy of an upstream responsibility as "integration."
