<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: distilled-from-l9-coding-control-plane-PLAN
tags: [plan, ccp, adaptive-depth, validation]
status: active
version: 2.2.0
updated: 2026-08-02
/L9_META -->

# CCP Plan Patterns — distilled for `/l9-plan`

Adaptation layer for plan/spec modes. Distills high-leverage rules from the L9 Coding Control Plane **PLAN** kernel without importing CCP runtime.

## Doctrine

> Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

Plan before build. Keep planning separate from implementation. Never report planned work as completed.

## Deep authority (read-only; do not fork contradicting rules)

- `kernels/L9 Coding Control Plane/ai-control-plane/PLAN.md`
- `kernels/L9 Coding Control Plane/ai-control-plane/VALIDATION.md`
- `kernels/L9 Coding Control Plane/ai-control-plane/DEFINITION_OF_DONE.md`
- `kernels/L9 Coding Control Plane/docs/AI_CODING_CONTROL_PLANE.md`
- `kernels/L9 Coding Control Plane/AGENTS.md` (routing + evidence model)

Deep/Release modes: **SHOULD** read this file; **MAY** read CCP `PLAN.md`. Quick/Standard: this distilled file is enough — **MUST NOT** require loading the entire CCP folder.

## Adaptive depth (Planning Mode)

| Mode | Use when | Minimum | Prohibited |
|------|----------|---------|------------|
| **Quick** | Bounded low-risk; explicit expected behavior; small surface | Bind target, scope, artifacts, sequence, targeted validation, completion criteria | Security-sensitive; data migrations; shared-contract changes; disputed ownership; material rollback/deploy risk |
| **Standard** | Normal multi-file feature/defect/refactor/integration | Baseline, responsibilities, workstreams, targeted+final validation, regression, risks, Unknowns, handoff | — |
| **Deep** | Architecture, security, migration, multi-repo, shared contracts, phased rollout | Full surface inventory, ownership map, decisions, failure/rollback/recovery, staged validation, lifecycle gates | Using Quick instead |
| **Release** | Plan includes PR/merge/packaging/release/deploy | Branch/integration state, check order, approvals, provenance, promotion, rollback, post-deploy verify | Treating implementation-ready as merge/release-ready |

**Escalate** when affected surface, ownership boundaries, external contracts, security/data risk, or irreversibility increase. Choose the **shallowest mode that still covers every material risk**.

Every plan/spec **MUST** declare Planning Mode + one-line justification.

## Required registers

### Unknown register

Label missing, ambiguous, inaccessible, stale, contradictory, inferred, or unverified items as Unknown. Unknowns are work — assign a discovery or decision step. May be an empty table with `None`.

### Decision register

Unresolved product/contract/architecture choices that block downstream items. May be `None`.

## Validation matrix schema

At least **targeted** and **final** rows. Distinguish **structural** vs **behavioral/runtime** evidence.

| Level | Scope | Evidence class |
|-------|-------|----------------|
| Targeted | Changed surface | Observed commands/results |
| Integration | Cross-module / contracts | Observed or Derived |
| Final | Mandatory gate set for Done | Observed against exact final state |

`make pr-check` (when code in scope) is a Final/scanner row — it does **not** replace behavioral validation.

**MUST NOT** weaken scanners/tests to obtain PASS. VALIDATION is non-mutating; repairs route to CHANGE / `l9-gmp-protocol`.

## plan_status enum

| Status | Meaning |
|--------|---------|
| Ready | Bound, executable Required items, dependencies valid, risks/Unknowns controlled, closing validation defined, no mandatory gate Failed/Unknown |
| ConditionallyReady | Complete except explicit decisions/approvals/prerequisites that do not require redesign |
| Partial | Useful bounded section planned; inaccessible/excluded areas block completeness |
| Blocked | Required context/authority/evidence unavailable |
| Failed | Objective unsafe or contradictory under constraints |

**MUST NOT** claim Ready while a blocking Unknown or Failed mandatory gate remains.

## Minimum Safe Next Action (MSNA)

Exactly **one** immediate next action: resolve earliest blocker, unlock most required work, or advance critical path. Prefer evidence gathering before implementation when material uncertainty remains.

## Handoff profiles → L9 skills

| Profile | When | Typical next skill |
|---------|------|-------------------|
| AUDIT | Policy/architecture uncertain; need independent assessment | audit / structured analysis skills |
| CHANGE | Authorized implementation of existing target | `l9-gmp-protocol` |
| BUILD | New deliverable / greenfield pack | forge / build skills when applicable |
| RELEASE | Merge/package/deploy in scope | release/ops skills; separate lifecycle auth |
| USER_DECISION | Unresolved product/contract choice | Ask one precise question |
| VALIDATION | Need evidence run without mutation | validation / `make pr-check` |

## Evidence classes

Observed | Derived | Hypothesis | Unknown — label claims in Depth / Pre-Validation.

## Lifecycle readiness ban

Implementation-ready ≠ ReviewReady ≠ MergeReady ≠ ReleaseReady ≠ DeploymentReady. **MUST NOT** infer a later readiness state from an earlier one.

## Anti-patterns (fail-closed)

- Fake or weakened validation; stubs/placeholders as “complete”
- Hidden assumptions inside tasks; dependency cycles collapsed into one task
- Parallelism claimed without write/contract independence
- Quick mode for security, migration, or shared contracts
- Invented paths/APIs/commands
- Reporting planned work as completed
- Aggregate “confidence” overriding mandatory Failed/Unknown gates

## Out of scope for `/plan` (do not import)

- CCP leases, exact-SHA mutation contracts, one-writer schedulers
- RELEASE packaging/deploy *execution*
- Assurance admission pipelines, attestation crypto, producer trust registries
- Full CCP YAML output contracts / quality-gate catalogs
- AUDIT scoring/domain inventory machinery
- BUILD decorative-file policy catalogs
