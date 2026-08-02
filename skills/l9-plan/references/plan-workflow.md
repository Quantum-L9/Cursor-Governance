<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: planning-playbook-v3
tags: [plan, playbook, shells, validation]
status: active
version: 3.0.0
updated: 2026-08-02
/L9_META -->

# Plan Workflow — Planning Playbook SSOT

> **Doctrine:** Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

This file defines **section shells** for plan mode. Fill them by **Load / Read / apply** per [authority-bindings.md](authority-bindings.md). Do not paste fixture bodies here or into the plan draft.

Also: [kernel-pass-pipeline.md](kernel-pass-pipeline.md) · [ccp-plan-patterns.md](ccp-plan-patterns.md)

## Playbook stages

1. Bind target · 2. Load fixtures (bindings) · 3. Gather · 4. Draft shells · 5. VALIDATE_PLAN · 6. Kernel pipeline · 7. plan_status + MSNA · 8. `/ynp`

Planning-only: modification scope for kernels = **this draft text only**.

## Output format

```markdown
## PLAN: {title}

### Doctrine
Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

### Load log
| Fixture | Path | Status |
|---------|------|--------|
| CCP PLAN | kernels/L9 Coding Control Plane/ai-control-plane/PLAN.md | Read \| Skipped+reason |
| CCP DoD | …/DEFINITION_OF_DONE.md | Read \| Skipped+reason |
| GMP lock | skills/l9-gmp-protocol/references/modification-lock.md | Read \| N/A — not CHANGE |
| GMP phases | …/phase-contracts.md | Read \| N/A — not CHANGE |
| … | … | … |

Fail-closed if any **required** row for this handoff is Skipped without justification.

### Planning Mode
**Mode:** Quick | Standard | Deep | Release
**Justification:** {one line}
**Load:** ccp-plan-patterns.md (+ CCP PLAN.md for Deep/Release)

### plan_status
Ready | ConditionallyReady | Partial | Blocked | Failed
**Load:** CCP PLAN.md plan_statuses / overall_plan_readiness

### Objective
{what and why}
**Success:** {falsifiable criteria}

### Files in scope
**Load:** CCP PLAN.md binding_rules / scope_rules
| Role | Paths / globs |
|------|----------------|
| Inspection | {exact paths or bounded globs} |
| Modification | {exact paths or bounded globs — or N/A — inspection-only} |

### Files out of scope
| Path / area | Why excluded | Risk if mistaken as in-scope |
|-------------|--------------|------------------------------|

Prose-only scope without path tables → incomplete plan.

### Constraints
**Load:** GMP modification-lock.md (CHANGE) + CCP PLAN preserve/stop rules
**MUST:**
- …
**MUST NOT:**
- …

### Modification Lock
**Load:** skills/l9-gmp-protocol/references/modification-lock.md
**May-modify:** {⊆ Files in scope / Modification}
**Must-not-modify:** {Files out of scope ∪ protected ∪ freezes}
N/A — inspection-only / non-CHANGE handoff (state reason).

### Pre-Validation (mandatory)
| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| P0 Target bind | Resolve write root | Single authorized target |
| P1 Baseline | Inventory | Gap list complete |
| P2 Clean gate | `make pr-check` (code in scope) | PASS; no commit/push |
| P3 Lesson corpus | learning/failures/repeated-mistakes.md | Matches or None matched |
| P4 Fixture Loads | authority-bindings.md | Required Reads done |

### Acceptance criteria (plan-level)
**Load:** CCP PLAN.md acceptance_criterion
- [ ] …

### Assumption register
| ID | Assumption | Validate / decide by |
|----|------------|----------------------|
| | None | |

### ADRs consulted
{list | None}
**Load (conditional):** skills/l9-architecture-decision-records

### TODO Plan
When handoff = CHANGE, **Load** phase-contracts.md Phase 0:
| ID | Phase | File | Operation | Anchor | Description | Deps | Effort | Risk | Rollback |
|----|-------|------|-----------|--------|-------------|------|--------|------|----------|

Operations: Insert | Replace | Delete | Wrap | Create. No placeholders / maybe.
Otherwise (non-CHANGE): Files | Effort | Risk | Rollback columns minimum.

### Depth
Evidence class: Observed | Derived | Hypothesis | Unknown
**Preserved invariants / Prohibited changes:** …
Conditional sections (key components triggers — see prior workflow): Failure-path map; Reusable Patterns; Unknown-file disposition — or `N/A — trigger not met`.

### Dependencies / Execution waves
**Load (CHANGE):** pipeline-composition.md — no parallel mutate unless independent
| Wave | Items | Parallel OK? | Conflicts |

### Critical path
1. …

### Unknown register
| ID | Unknown | Blocks | Resolution |
|----|---------|--------|------------|
| | None | | |

### Decision register
| ID | Decision | Options | Blocks |
|----|----------|---------|--------|
| | None | | |

### Validation matrix
| Level | Check | Structural vs behavioral | Pass criteria |
|-------|-------|--------------------------|---------------|
| Targeted | … | … | … |
| Integration | … | … | … |
| Final | `make pr-check` (code in scope) | scanners | PASS; no commit/push |
| Final | Secret-surface / drift-watch | when triggered | PASS or N/A — trigger not met |

### Plan Definition of Done
**Load:** CCP PLAN.md plan_quality_gates
- [ ] Target + path scopes bound
- [ ] Constraints + Lock (if CHANGE) present
- [ ] TODOs executable (Phase-0 shape if CHANGE)
- [ ] Validation matrix + unknowns/decisions explicit
- [ ] Handoff + MSNA set
- [ ] Kernel Pass Log complete
- [ ] plan_status coherent (not Ready with blocking Unknown)

### Post-implementation Definition of Done
**Load:** DEFINITION_OF_DONE.md + GMP Phase 4–5 expectations
Name gates for implementers (do not claim Passed now):
- target/scope verified · implementation complete · no stubs · contracts · no scope drift · mandatory checks green · hygiene · convergence · handoff
- verify-against-lock: only may-modify files changed
- evidence report under GMP when applicable

### Milestones
| Milestone | Outcome | Unlocks |

### Checkpoints
| CP | After | Evidence | No-go |

### Checklist
- [ ] Required Loads recorded
- [ ] Path scopes + Constraints (+ Lock if CHANGE)
- [ ] Plan DoD + Post-impl DoD named
- [ ] Kernel Pass Log PASS shape
- [ ] Final Validation named
- [ ] No commit/push from plan mode

### Risks
| Risk | Mitigation |

### Estimate
**Total:** {time}
**GMPs:** {count}

### Kernel Pass Log (mandatory)
**Load:** kernel-pass-pipeline.md
| Kernel | Path | Status | Material deltas |
|--------|------|--------|-----------------|
| Improve | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Leverage | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Recursive Alignment | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Recursive Leverage | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Validate & Repair | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |

### Final Validation (mandatory)
| Check | Pass criteria |
|-------|---------------|
| V1 Completeness | All shells + required Loads |
| V2 Scanners | `make pr-check` when code in scope |
| V3 Honesty | Passed / Failed / Skipped / N/A / Unknown |
| V4 Lifecycle | Impl-ready ≠ Merge/Release/Deploy ready |

### Minimum Safe Next Action
{exactly one}
**Load:** l9-ynp

### Handoff profile
AUDIT | CHANGE | BUILD | RELEASE | USER_DECISION | VALIDATION
**Maps to:** CHANGE → l9-gmp-protocol / `/gmp` · BUILD → forge when applicable
```

## Gate rules

- Fail-closed if required fixtures for the handoff were not Read.
- Fail-closed if Files in/out lack path tables (unless inspection-only N/A).
- Fail-closed if CHANGE handoff lacks Modification Lock or Phase-0 TODO columns.
- Kernel path strings: only in [kernel-pass-pipeline.md](kernel-pass-pipeline.md).
- Ticket mode: Kernel Pass Log = `N/A — ticket mode`; playbook Loads still apply where relevant.
- Never weaken scanners; never execute GMP Phases 2–6 from plan mode.

Auto-chain: `/ynp` (skill `l9-ynp`).
