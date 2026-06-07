<!-- L9_META
skill_schema: 1
parent: l9-recursive-optimization
layer: reference
role: convergence_schema
tags: [recursive, convergence, output]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-06-06
/L9_META -->

# Convergence Block

## Purpose

Required closing section for every recursive optimization delivery. Proves whether another pass would add material value.

## Required Fields (all modes)

```yaml
convergence_status: converged | partial | blocked
recursive_passes_run: <integer>
same_output_after_multiple_passes: true | false
remaining_unknowns: []
minimum_safe_next_action: <string>
```

## Alignment Mode — Additional Fields

```yaml
alignment_score: <0-100 or qualitative with justification>
critical_violations_remaining: <integer>
high_violations_remaining: <integer>
blocks_release: true | false
```

## Improvement Mode — Additional Fields

```yaml
files_or_sections_improved:
  - <item>
source_intent_preserved: true | false
scope_drift_detected: true | false
pack_coherence_improved: true | false
enforceability_improved: true | false
reuse_value_improved: true | false
execution_readiness: pass | partial | fail
```

## Optimize Mode — Additional Fields

Include alignment fields plus improvement fields when artifacts were revised.

```yaml
alignment_then_improvement_cycles: <integer>
violations_fixed_in_session: <integer>
violations_deferred: <integer>
```

## Convergence Status Rules

| Status | When |
|--------|------|
| **converged** | No material improvement on full re-pass; critical violations zero or explicitly accepted by user |
| **partial** | Improvement made but known gaps remain; deferred items documented |
| **blocked** | Cannot converge without missing source, user decision, or external dependency |

## Convergence Rule

Stop only when another full pass produces no material improvement. If convergence cannot be reached without invention, halt with `blocked` and state the exact blocker.

Do not show intermediate passes in final delivery unless user requests them.
