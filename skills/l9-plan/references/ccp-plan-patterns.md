<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: planning-playbook-v3
tags: [plan, adaptive-depth]
status: active
version: 3.0.0
updated: 2026-08-02
/L9_META -->

# CCP Plan Patterns — adaptive depth only

Thin pointer file. **Full plan contracts live in fixtures** — Load via [authority-bindings.md](authority-bindings.md).

**Do not** re-host GMP lock/phase catalogs, DoD gate lists, or CCP PLAN body here.

## Doctrine

> Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

## Deep authority (Read these — do not copy)

- `kernels/L9 Coding Control Plane/ai-control-plane/PLAN.md`
- `kernels/L9 Coding Control Plane/ai-control-plane/DEFINITION_OF_DONE.md`
- `skills/l9-gmp-protocol/references/modification-lock.md`
- `skills/l9-gmp-protocol/references/phase-contracts.md`

## Adaptive depth (Planning Mode)

| Mode | Use when | Prohibit |
|------|----------|----------|
| **Quick** | Bounded low-risk; explicit behavior; small surface | Security-sensitive; migrations; shared-contract changes; disputed ownership; material rollback/deploy risk |
| **Standard** | Normal multi-file feature/defect/refactor | — |
| **Deep** | Architecture, security, migration, multi-repo, shared contracts, phased rollout | Using Quick instead |
| **Release** | Plan includes PR/merge/packaging/release/deploy | Treating impl-ready as merge/release-ready |

**Escalate** when surface, ownership boundaries, contracts, security/data risk, or irreversibility increase. Choose the shallowest mode that still covers every material risk.

Every plan/spec **MUST** declare Planning Mode + one-line justification.

Deep/Release: **SHOULD** Read full CCP `PLAN.md`. Quick/Standard: bindings + this table suffice for mode selection.

## Related playbook files

- [authority-bindings.md](authority-bindings.md) — what to Load
- [plan-workflow.md](plan-workflow.md) — section shells
- [kernel-pass-pipeline.md](kernel-pass-pipeline.md) — five-kernel pipeline
