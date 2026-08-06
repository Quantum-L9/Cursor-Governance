---
name: l9-plan
description: create an execution plan or implementation specification before building. use when scope is unclear, requirements need decomposition, or the next step should be planned before code changes.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, plan, spec, execution, requirements]
owner: igor_beylin
status: active
version: 2.2.0
updated: 2026-08-06
---

# Execution Planning

## Purpose

Produce a structured plan or full specification before implementation. Planning-only — no code edits unless the user explicitly chains to `l9-gmp-protocol` or another execution skill.

## Core Contract

| Mode | Output | Load |
|------|--------|------|
| plan | Deep TODO plan with pre/final validation, milestones, checkpoints, checklist, doc/root surface impact | [references/plan-workflow.md](references/plan-workflow.md) |
| spec | Full spec document for forge/gmp (must include validation gates) | [references/spec-workflow.md](references/spec-workflow.md) |
| ticket | Engineering ticket structure | [references/engineering-ticket-template.md](references/engineering-ticket-template.md) |

## Authority Order

1. Explicit user objective and constraints.
2. Verified repo ground truth — existing modules, patterns, ADRs.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`.
4. This skill's references.
5. `Unknown` — ask before filling gaps in the spec.

## Compact Workflow

1. **Pre-Validate** — bind target; inventory baseline; run applicable repo gates before planning edits. For Cursor-Governance / governed workspaces with code in scope: `make pr-check` (changed-files scanners; **no commit, no push**). Record PASS/FAIL/SKIPPED with reason.
2. **Gather** — objective, scope in/out, falsifiable success criteria.
3. **Decompose** — TODO table with files (or `TBD` + blocker), effort, risk; add depth beyond the table (behavioral notes, contracts preserved).
4. **Doc / Root Surface Impact** — probe repo-root and agent-facing docs that would go stale if the planned change ships; schedule Update TODOs with paths, or record **N/A** with a one-line reason. Existence-based probe (do not invent paths): always consider `README.md`, `AGENTS.md`; if present also `CLAUDE.md`, `ARCHITECTURE.md`, `INVARIANTS.md`, `CHANGELOG.md`, `.claude/README.md`; governance extras when relevant (`commands/commands-index.md`, skill registries). New root file → plan registration in root-file-protection policy. Prefer chaining `l9-update-agent-docs` for agent-doc rewrites and `l9-wire-skill-into-repo` for skill/registry surfaces. Plan mode schedules only — does not edit.
5. **Dependencies** — task graph; identify blockers.
6. **Milestones** — outcome batches that unlock the next phase.
7. **Checkpoints** — go/no-go evidence gates between milestones.
8. **Checklist** — atomic done/not-done items tied to TODOs (include doc/root surface items or N/A).
9. **Deliver** — plan markdown or `specs/{project}-spec.md` per mode using the required template.
10. **Final Validate** — name the post-implementation gates. For any plan that will edit code: require `make pr-check` before claiming readiness (**no commit, no push** unless the user explicitly asks). Confirm Doc / Root Surface Impact TODOs are listed or N/A is justified.
11. **Recommend** — load `l9-ynp` for gmp vs forge vs continue.

## Resource Map

- [references/plan-workflow.md](references/plan-workflow.md) — execution plan output format (SSOT template).
- [references/spec-workflow.md](references/spec-workflow.md) — full specification generator.
- [references/engineering-ticket-template.md](references/engineering-ticket-template.md) — acceptance criteria, GWT scenarios.
- Related skills (implementation, not plan mode): `l9-update-agent-docs`, `l9-wire-skill-into-repo`.

## Validation

A plan is incomplete (fail-closed — do not present as ready) if any of the following are missing:

- **Pre-Validation** section (commands + pass criteria, or explicit Skipped/N/A with reason)
- **Final Validation** section (commands + pass criteria; `make pr-check` when code is in scope)
- **Doc / Root Surface Impact** section (Update TODOs with files, or **N/A** with reason — unjustified omission fails)
- **Milestones**, **Checkpoints**, and **Checklist**
- Every TODO names files or `TBD` with a blocker note
- Scope out is explicit
- No placeholder "TODO: fill in" without a question to the user

Code written under a plan that implied implementation MUST be clean: run `make pr-check` (alias `make pr`) locally; do not open/push a PR on a failing gate. Never weaken scanners to obtain PASS.

## Failure Handling

- Ambiguous objective → STOP at gather; ask clarifying questions.
- Scope creep detected → move items to Out of scope.
- Protected-path changes planned → flag KERNEL GMP requirement.
- Pre-Validation FAIL on unrelated dirty tree → quarantine unrelated changes or document baseline FAIL; do not claim whole-tree cleanliness.
- Doc/root surfaces would require deletions/overwrites on append-only roots → flag Risks + KERNEL GMP; prefer additive updates.
- User requests immediate implementation → recommend `l9-gmp-protocol`; do not edit files in plan mode.
