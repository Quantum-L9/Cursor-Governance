<!-- L9_META
l9_schema: 1
parent: l9-plan
origin: migrated-from plan command v1.0.0
tags: [plan, todo, risks, estimate, milestones, checkpoints, validation, doc-surface]
status: active
version: 2.2.0
updated: 2026-08-06
/L9_META -->

# Plan Workflow — Execution Planning

Create structured plan before implementation. This file is the **SSOT output template** for plan mode.

## Steps

1. Pre-Validate (mandatory) — baseline gates before recommending edits.
2. Define objective (what, why, falsifiable success criteria).
3. Identify scope (in / out).
4. List TODO items with files, effort, risk — add depth beyond the table.
5. Doc / Root Surface Impact (mandatory) — probe README/AGENTS and related surfaces; Update TODOs or N/A with reason.
6. Map dependencies.
7. Define milestones and checkpoints.
8. Build checklist tied to TODOs (include doc/root items or N/A).
9. Identify risks and mitigations.
10. Define Final Validation (mandatory) — post-implementation gates.
11. Estimate and recommend next skill (`l9-ynp`).

## Output format

```markdown
## PLAN: {title}

### Objective
{what and why}
**Success:** {falsifiable criteria}

### Scope
**In:** {list}
**Out:** {list}

### Pre-Validation (mandatory)
| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| P0 Target bind | {resolve write root} | Single authorized target |
| P1 Baseline inventory | {inspect current state} | Gap list complete |
| P2 Clean gate (code in scope) | `make pr-check` | PASS — changed-files scanners; **no commit, no push** |
| P3 Wiring / env (if applicable) | {project check} | PASS or Skipped with reason |

Halt modification planning if Pre-Validation cannot distinguish a safe baseline.
Record actual results when this plan is executed; for planning-only drafts, list the commands that MUST run before edits.

### TODO Plan
| # | Task | Files | Effort | Risk |
|---|------|-------|--------|------|

### Depth
{behavioral notes, contracts preserved, root-cause vs symptom, evidence sources}

### Doc / Root Surface Impact (mandatory)
Probe (existence-based — do not invent paths). Always consider `README.md`, `AGENTS.md`. If present: `CLAUDE.md`, `ARCHITECTURE.md`, `INVARIANTS.md`, `CHANGELOG.md`, `.claude/README.md`. Governance extras when relevant: `commands/commands-index.md`, skill registries. New root file → include root-file-protection registration.

| Surface | Action | Files / notes |
|---------|--------|---------------|
| {path or group} | Update \| N/A | {TODO ids or one-line reason} |

Unjustified omission of this section fails closed. Prefer chaining `l9-update-agent-docs` / `l9-wire-skill-into-repo` at implementation time for agent/registry rewrites. Plan mode schedules only — does not edit.

### Dependencies
{task graph}

### Milestones
| Milestone | Outcome | Unlocks |
|-----------|---------|---------|

### Checkpoints
| CP | After | Evidence required | No-go action |
|----|-------|-------------------|--------------|

### Checklist
- [ ] {atomic item tied to a TODO}
- [ ] Pre-Validation recorded
- [ ] Doc / Root Surface Impact recorded (Update TODOs or N/A with reason)
- [ ] Final Validation (`make pr-check` when code changed) PASS
- [ ] No commit/push unless user explicitly requested

### Risks
| Risk | Mitigation |
|------|------------|

### Estimate
**Total:** {time}
**GMPs:** {count}

### Final Validation (mandatory)
| Check | Command | Pass criteria |
|-------|---------|---------------|
| V1 Section completeness | Review plan vs this template | All required headings present |
| V2 Clean code / scanners | `make pr-check` (when code in scope) | PASS; changed-files only; **no commit, no push** |
| V3 Doc / Root Surface Impact | Surfaces table complete | Every probed hit is Update or N/A with reason |
| V4 Honesty | Report only checks actually run | Passed / Failed / Skipped / N/A / Unknown |

Do not claim implementation readiness until Final Validation passes (or N/A is justified for pure planning/docs with no code edits).
```

## Gate rules

- **Every plan** MUST include Pre-Validation, Doc / Root Surface Impact, and Final Validation sections.
- **Any plan that will edit code** MUST name `make pr-check` (alias `make pr`; Make is case-sensitive — not `PR-check`) in both gates when the workspace is Cursor-Governance or a consumer using the governance `pr` target.
- Never weaken linters, types, schemas, security scanners, or tests to obtain PASS.
- Do not push or open a PR from plan mode; implementation chains to `l9-gmp-protocol` / user-authorized commit.
- Doc/root updates are scheduled in the plan; actual edits happen under implementation skills/GMP. Append-only / protected roots → flag Risks + KERNEL GMP for deletions/overwrites.

Auto-chain recommendation: load `l9-ynp` (recommends gmp or forge).
