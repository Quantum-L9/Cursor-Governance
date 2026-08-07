<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, leverage]
status: active
version: 3.0.0
updated: 2026-08-07
/L9_META -->

# First-Order Leverage

Prefer TODOs that unlock the most future work or remove shared root causes.

Required `leverage` object:

- `ranked_todo_ids` — todos ordered by unlock value (highest first)
- `shared_causes` — root causes fixed once instead of patched repeatedly
- `deletions_or_consolidations` — removals that reduce entropy

Rank using: shared root cause > contract clarification > validation automation > local symptom fix.
