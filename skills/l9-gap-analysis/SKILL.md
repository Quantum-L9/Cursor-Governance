---
name: l9-gap-analysis
description: perform read-only delta gap analysis against a target state with scoring and optional actionable recommendations. use when assessing readiness, missing pieces, compliance drift, or percent-complete status.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, gap-analysis, readiness, scoring, delta]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
---

# Gap Analysis

## Purpose

Compare current state against a named target, score dimensional coverage, report gaps as percentages, and STOP. Read-only — no fixes, wiring, refactors, or execution unless the user explicitly requests a follow-up skill.

## Core Contract

| Mode | Fixes | Prioritization | Load |
|------|-------|----------------|------|
| standalone | never | raw % only | [references/gap-analysis-standalone.md](references/gap-analysis-standalone.md) |
| prioritized | never | impact/effort table | [references/gap-analysis-prioritized.md](references/gap-analysis-prioritized.md) |

Default target: `L9_CANON`. Alternatives: `prod-ready`, `scale-ready`, `k8s-ready`, or custom string.

## Authority Order

1. Explicit user paths and target state name.
2. Verified file contents from the repo — static analysis only.
3. Target expectations defined in the selected reference mode.
4. `Unknown` — label dimensions that cannot be scored from available files.

## Compact Workflow

1. **Extract** — role, layer, responsibilities, dependencies per file.
2. **Normalize** — score dimensions (Structure, Lifecycle, Async, Error handling, Observability, Configuration, Tests).
3. **Compare** — Gap % = Target % − Current %; report only Gap % > 0.
4. **Report** — inline markdown table; STOP.

## Resource Map

- [references/gap-analysis-standalone.md](references/gap-analysis-standalone.md) — %-based delta, no fixes, strict STOP.
- [references/gap-analysis-prioritized.md](references/gap-analysis-prioritized.md) — current vs target with priority and GMP recommendations.

## Validation

Every gap row MUST name a dimension and numeric Gap %. No subjective labels without a % backing. Standalone mode MUST NOT propose fixes.

## Failure Handling

- No files provided → STOP; ask for paths.
- Target undefined → default `L9_CANON`; state assumption in report.
- Binary files or unreadable paths → skip with `Unknown`; do not invent coverage.
- User asks for fixes → recommend `l9-plan` or `l9-gmp-protocol`; do not execute in this skill.
