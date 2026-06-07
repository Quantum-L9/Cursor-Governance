<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: mode_router
tags: [recursive, alignment, improvement, optimization, routing]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-07
/L9_META -->

# Mode Routing

## Purpose

Select align, improve, or optimize before running passes.

## Mode Table

| Mode | User intent | Mutates source | Primary output |
|------|-------------|----------------|----------------|
| **align** | audit, check compliance, alignment report, harden review | no | violation report + correction roadmap |
| **improve** | make better, strengthen, dedupe, clarify, densify | yes | revised artifact group |
| **optimize** | recursive optimization, full harden, align then fix | yes (after audit) | report + revised artifacts when fixed |

## Trigger Phrases

| Phrase | Mode |
|--------|------|
| recursive alignment, align against contract, alignment audit | align |
| recursive improvement, improve this pack/prompt, strengthen enforceability | improve |
| recursive optimization, recursively optimize/harden/converge | optimize |
| fix violations / implement corrections | improve or optimize + `persist=apply` |
| generate delta, what improved | optimize + report-only (default persist) |

## Decision Rules

1. Explicit mode in user message wins.
2. "Report only" or "do not change files" → **align**.
3. "Rewrite", "improve every section", "return revised pack" → **improve**.
4. No mode stated → **optimize**.
5. PlasticOS artifact with no L9 node context → skip L9 transport/Gate passes; still run generic alignment/improvement passes.

## Optimize Sub-sequence

1. Run full alignment protocol → produce violation inventory.
2. If zero critical/high violations and user did not request improvement → deliver alignment report only; convergence `converged`.
3. If violations exist → run improvement protocol on affected sections only.
4. Re-run alignment on changed sections; escalate severity if regression detected.
5. Stop when alignment finds no new material issues, improvement passes add no leverage, or 3 align→improve cycles complete (whichever first).

## Conflicts

| Conflict | Resolution |
|----------|------------|
| User wants align but also "fix it" | optimize |
| User wants improve but forbids file changes | align only; note conflict |
| Partial folder scope | state scope boundary in context lock; do not infer whole-repo |
