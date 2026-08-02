<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: migrated-from plan command v1.0.0
tags: [plan, todo, risks, estimate, milestones, checkpoints, validation, kernels, ccp]
status: active
version: 2.2.0
updated: 2026-08-02
/L9_META -->

# Plan Workflow — Execution Planning

> **Doctrine:** Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

Create structured plan before implementation. This file is the **SSOT output template** for plan mode.

Orchestration: [kernel-pass-pipeline.md](kernel-pass-pipeline.md) (kernel paths + log). Patterns: [ccp-plan-patterns.md](ccp-plan-patterns.md). Conditional gates provenance: `key components/` (concepts only — no CLIs).

## Steps

1. Pre-Validate (mandatory) — baseline gates + lesson corpus recall when `learning/failures/` present.
2. Gather — objective, success criteria; ask before build.
3. Identify scope — **inspection** vs **modification** lists separately; in / out.
4. Declare Planning Mode + justification ([ccp-plan-patterns.md](ccp-plan-patterns.md)).
5. List TODO items with files, effort, risk — Depth beyond the table.
6. Map dependencies and execution waves (only when write/contract-independent).
7. Define milestones and checkpoints.
8. Build checklist tied to TODOs.
9. Identify risks; Unknown register; Decision register.
10. Define Validation matrix + Final Validation.
11. **VALIDATE_PLAN** — template + CCP + conditional key-component gates complete.
12. **Kernel Pass Pipeline** — apply [kernel-pass-pipeline.md](kernel-pass-pipeline.md); attach Kernel Pass Log.
13. Set `plan_status`, Minimum Safe Next Action, handoff profile; recommend `l9-ynp`.

## Output format

```markdown
## PLAN: {title}

### Doctrine
Proper planning prevents piss poor performance. A minute spent planning is an hour saved debugging.

### Planning Mode
**Mode:** Quick | Standard | Deep | Release
**Justification:** {one line — why this mode; escalate if security/migration/shared contracts}

### plan_status
Ready | ConditionallyReady | Partial | Blocked | Failed

### Objective
{what and why}
**Success:** {falsifiable criteria}

### Scope
**Inspection:** {what was/will be inspected}
**Modification:** {what may change}
**In:** {list}
**Out:** {list}

### Pre-Validation (mandatory)
| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| P0 Target bind | {resolve write root} | Single authorized target |
| P1 Baseline inventory | {inspect current state} | Gap list complete |
| P2 Clean gate (code in scope) | `make pr-check` | PASS — changed-files scanners; **no commit, no push** |
| P3 Wiring / env (if applicable) | {project check} | PASS or Skipped with reason |
| P4 Lesson corpus | Scan `learning/failures/repeated-mistakes.md` (+ `learning/patterns/quick-fixes.md` if present) | Matches listed or `None matched` |

Halt modification planning if Pre-Validation cannot distinguish a safe baseline.
Record actual results when this plan is executed; for planning-only drafts, list the commands that MUST run before edits.

### Lesson matches (from corpus)
| Lesson / pattern | Relevance | Action in this plan |
|------------------|-----------|---------------------|
| {id or None matched} | … | … |

### TODO Plan
| # | Task | Files | Effort | Risk | Rollback (Med/High) |
|---|------|-------|--------|------|---------------------|
| | | | | | {procedure or N/A + reason} |

### Depth
{behavioral notes, root-cause vs symptom, evidence class: Observed|Derived|Hypothesis|Unknown}

**Preserved invariants:** {list}
**Prohibited changes:** {list — include refactor default: no silent auto-apply when category=refactor}

#### Failure-path map (required when mutating multi-step skills/workflows)
| Entrypoint | Expected I/O | Failure paths |
|------------|--------------|---------------|
| … | … | … |
| N/A — trigger not met | | |

#### Reusable Patterns (required when modification scope includes skills/prompts/commands/workflows)
| Preserve | Extract | Avoid |
|----------|---------|-------|
| … | … | … |
| N/A — trigger not met | | |

#### Unknown-file disposition (required for file-move/reorg plans)
**Quarantine/inbox path for orphans:** {path or N/A — trigger not met}

### Dependencies
{task graph}

#### Execution waves
| Wave | Items | Parallel OK? | Write/contract conflicts |
|------|-------|--------------|--------------------------|
| W1 | … | yes/no | none / describe |

### Unknown register
| ID | Unknown | Blocks | Resolution step |
|----|---------|--------|-----------------|
| | None | | |

### Decision register
| ID | Decision | Options | Blocks | Needed by |
|----|----------|---------|--------|-----------|
| | None | | | |

### Validation matrix (mandatory)
| Level | Check | Structural vs behavioral | Pass criteria |
|-------|-------|--------------------------|---------------|
| Targeted | … | … | … |
| Integration | … | … | … |
| Final | `make pr-check` (when code in scope) | structural/scanners | PASS; no commit/push |
| Final | Secret-surface (when secrets/config-auth in scope) | no hardcoded secrets; authoritative secret paths | PASS or N/A — trigger not met |
| Final | Drift watch (when config/schema/policy in scope) | paths to watch post-change | Named paths or N/A — trigger not met |

### Milestones
| Milestone | Outcome | Unlocks |
|-----------|---------|---------|

### Checkpoints
| CP | After | Evidence required | No-go action |
|----|-------|-------------------|--------------|

### Checklist
- [ ] {atomic item tied to a TODO}
- [ ] Pre-Validation recorded (incl. lesson corpus)
- [ ] Planning Mode + plan_status set
- [ ] Unknown + Decision registers present
- [ ] Validation matrix complete; conditional sections present or N/A — trigger not met
- [ ] Kernel Pass Log complete (five Applied/Blocked rows)
- [ ] Final Validation (`make pr-check` when code changed) PASS
- [ ] MSNA + handoff profile set
- [ ] No commit/push unless user explicitly requested
- [ ] Implementation-ready not claimed as merge/release-ready

### Risks
| Risk | Mitigation |
|------|------------|

### Estimate
**Total:** {time}
**GMPs:** {count}

### Kernel Pass Log (mandatory)
| Kernel | Path | Status | Material deltas |
|--------|------|--------|-----------------|
| Improve | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Leverage | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Recursive Alignment | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Recursive Leverage | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |
| Validate & Repair | (see kernel-pass-pipeline.md) | Applied \| Blocked | … |

Exact paths and order: [kernel-pass-pipeline.md](kernel-pass-pipeline.md) (sole path SSOT).

### Final Validation (mandatory)
| Check | Command | Pass criteria |
|-------|---------|---------------|
| V1 Section completeness | Review plan vs this template | All required headings + conditional gates satisfied |
| V2 Clean code / scanners | `make pr-check` (when code in scope) | PASS; changed-files only; **no commit, no push** |
| V3 Honesty | Report only checks actually run | Passed / Failed / Skipped / N/A / Unknown |
| V4 Drift watch | {paths when config/schema/policy changed} | Named or N/A — trigger not met |

Do not claim implementation readiness until Final Validation passes (or N/A is justified for pure planning/docs with no code edits).
Do not infer MergeReady / ReleaseReady / DeploymentReady from implementation-ready alone.

### Minimum Safe Next Action
{exactly one action}

### Handoff profile
AUDIT | CHANGE | BUILD | RELEASE | USER_DECISION | VALIDATION
**Maps to:** {e.g. CHANGE → l9-gmp-protocol}
```

## Conditional section triggers (key components — concepts only)

Provenance: `key components/` cards. Do not resurrect CLIs.

| Section | Trigger |
|---------|---------|
| Lesson corpus (P4 + Lesson matches) | Always when `learning/failures/repeated-mistakes.md` is accessible; else Skipped with reason |
| Reusable Patterns | Modification scope includes skills, prompts, commands, or workflows |
| Failure-path map | Plan mutates multi-step skill/workflow packs |
| Refactor no silent auto-apply | Plan category is refactor |
| Secret-surface rows | Secrets, credentials, or config auth in modification scope |
| Unknown-file disposition | File-move / reorg plans |
| Drift-watch paths | Config, schema, or policy in modification scope |

When a trigger is not met, write `N/A — trigger not met` for that section (do not omit the heading if the template lists it under Depth/Validation — use N/A row).

## Gate rules

- **Every plan** MUST include Pre-Validation, Final Validation, Planning Mode, `plan_status`, Unknown register, Decision register, Validation matrix, milestones, checkpoints, checklist, Kernel Pass Log, MSNA, and handoff profile.
- **Any plan that will edit code** MUST name `make pr-check` (alias `make pr`; Make is case-sensitive — not `PR-check`) when the workspace is Cursor-Governance or a consumer using the governance `pr` target.
- Never weaken linters, types, schemas, security scanners, or tests to obtain PASS.
- Do not push or open a PR from plan mode; implementation chains to `l9-gmp-protocol` / user-authorized commit.
- Kernel path strings: cite [kernel-pass-pipeline.md](kernel-pass-pipeline.md) only — do not maintain a second path list.
- Fail-closed: missing Kernel Pass Log, Ready with blocking Unknown, Quick mode for security/migration/shared contracts, or omitted conditional section when trigger matches → plan incomplete.
- Ticket mode: Kernel Pass Log = `N/A — ticket mode` only.

Auto-chain recommendation: load `l9-ynp` (recommends gmp or forge).
