<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: output_contract
tags: [recursive, output, deliverables]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-07
/L9_META -->

# Output Contracts

## Purpose

Define deliverable shape per mode so agents do not mix audit reports with partial rewrites.

## Alignment Mode

Deliver:

1. Full alignment report (all sections in [alignment-protocol.md](alignment-protocol.md))
2. Violation table with id, severity, evidence, correction
3. Ordered correction roadmap
4. Convergence block

Do NOT deliver rewritten source files unless user explicitly requests copy-paste-ready corrections inline.

## Improvement Mode

Deliver:

1. Complete revised artifact group (every touched file in full)
2. Revised folder tree if pack-based
3. Short change summary (intent preserved, what strengthened, what removed)
4. Convergence block

Do NOT deliver summary-only when pack contract requires complete files.

## Optimize Mode

Deliver:

1. Alignment report (abbreviated if converged with zero critical/high — still list passes run)
2. **Delta table** — file/section, severity, before, after, rationale
3. Revised artifact sections for every improvement (full file only when `persist=apply`)
4. Before/after violation count if alignment ran twice
5. Convergence block

## Presentation Order

```text
1. Mode + scope boundary (one paragraph)
2. Primary deliverable (report and/or revised artifacts)
3. Correction roadmap or change summary
4. Convergence block (always last)
```

## Self-Documenting Output

State: mode used, passes run, what was checked vs changed, and single recommended next action (or invoke `l9-ynp`).
