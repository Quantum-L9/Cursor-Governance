---
name: l9-code-analysis
description: rapidly analyze, deeply evaluate, or combine analysis and evaluation for code targets. use when exploring unfamiliar code, auditing structure, mapping flows, identifying hotspots, or assessing quality before edits.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, analysis, evaluate, structure, hotspots, compliance]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
---

# Code Analysis

## Purpose

Explore and audit code targets before acting: rapid structure mapping, deep compliance evaluation, or combined cross-referenced analysis. Read-only by default unless the user explicitly requests fixes.

## Core Contract

| Mode | Speed | Depth | Load |
|------|-------|-------|------|
| analyze | ~30s | surface | [references/analyze-workflow.md](references/analyze-workflow.md) |
| evaluate | 2–5min | deep audit | [references/evaluate-workflow.md](references/evaluate-workflow.md) |
| analyze+evaluate | combined | cross-referenced | [references/analyze-evaluate-workflow.md](references/analyze-evaluate-workflow.md) |

Optional accelerators: [parallel-subagent-patterns.md](references/parallel-subagent-patterns.md), [dependency-analysis.md](references/dependency-analysis.md), [pattern-alignment.md](references/pattern-alignment.md).

## Authority Order

1. Explicit user request and named target path(s).
2. Verified repo ground truth — actual files, imports, tests, conventions.
3. Repo invariants — `AGENTS.md`, `.cursor/rules/*.mdc`, module rules when present.
4. This skill's references.
5. `Unknown` — label and stop rather than invent structure or compliance scores.

## Compact Workflow

1. **Classify target** — MODULE | SERVICE | AGENT | ROUTER | TOOL | KERNEL | CONFIG.
2. **Route mode** — analyze (understand) | evaluate (audit) | analyze+evaluate (both).
3. **Execute** — structure map → flow trace → hotspots → health (analyze) or tier/L9/gap checks (evaluate).
4. **Recommend** — continue, `/evaluate`, `/gmp`, or load parallel/dependency refs for large scope.

## Resource Map

- [references/analyze-workflow.md](references/analyze-workflow.md) — rapid exploration output format.
- [references/evaluate-workflow.md](references/evaluate-workflow.md) — deep evaluation, anti-patterns, GMP TODOs.
- [references/analyze-evaluate-workflow.md](references/analyze-evaluate-workflow.md) — combined cross-reference, impact, auto-fix candidates.
- [references/parallel-subagent-patterns.md](references/parallel-subagent-patterns.md) — parallel explore / four-lens review.
- [references/dependency-analysis.md](references/dependency-analysis.md) — module graph, cycles, blast radius.
- [references/pattern-alignment.md](references/pattern-alignment.md) — extract_align vs repo standards.

## Validation

Before delivering analysis: every hotspot or gap MUST cite a file path (or `Unknown`). Compliance scores MUST trace to observable evidence, not assumptions.

## Failure Handling

- Target path missing → STOP; ask user or search repo.
- Ambiguous scope → present options; default to analyze unless audit requested.
- Protected paths touched in recommendations → route to KERNEL GMP; do not auto-fix.
- Confidence in findings <70% → gather more files before evaluate mode.
