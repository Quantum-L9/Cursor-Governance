<!-- --- L9_META ---
l9_schema: 1
artifact_type: operations
component: memory_aggregator_operations_layer
tags: [operations, memory, aggregator, learning, governance]
retrieval: on_demand
status: active
--- /L9_META --- -->

Version: 1.0.0
Canonical-Source: 10X Governance Suite
Generated: 2025-10-06T17:10:32Z

# Memory Aggregator — OPS Canonical

## Objective
Aggregate chat exports and system logs into a structured Governance Memory Ledger.

## Function
- Ingests `/ops/logs/chat_exports/*`.
- Extracts methodologies, outcomes, and reasoning patterns.
- Updates `/ops/logs/memory_index.json`.

## Scoring Rubric
- Success = +1.0 weight
- Partial = +0.5 weight
- Failure = -1.0 weight

## Policy
`.cursor/rules.json` → `apply_best_known_method`

## Output
Summarized learnings appended to `/ops/logs/memory_index.json` with timestamps.
