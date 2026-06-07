---
name: l9-forge
description: autonomous high-velocity execution with zero pauses — batch gmp runs, auto-fix validation, deliver code tests and reports. use when user invokes /forge or requests maximum-velocity autonomous delivery.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, forge, autonomous, gmp, velocity]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
disable-model-invocation: true
---

# Forge — Autonomous Execution

## Purpose

Maximum-velocity autonomous delivery: execute scoped work without manual checkpoints, auto-fix validation failures where safe, and deliver code + tests + GMP reports.

## Core Contract

| Rule | Behavior |
|------|----------|
| NO PAUSES | Execute; do not ask unless stop condition hit |
| AUTO-FIX | Fix validation failures within scope; proceed |
| BATCH | Multiple GMPs per forge when scoped |
| COMPLETE | Code + tests + reports required |

Load [references/forge-workflow.md](references/forge-workflow.md) for execution steps and output format.

## Authority Order

1. User forge scope and modification lock.
2. [l9-gmp-protocol](../l9-gmp-protocol/SKILL.md) for phased runs.
3. Repo protected paths (`.cursor/rules/`, `pipeline_v2.py` never activated).

## Resource Map

- [references/forge-workflow.md](references/forge-workflow.md) — scope lock, GMP batch, deliverables, stop conditions.

## Validation

Each GMP in scope MUST end with evidence report in `reports/` when using GMP protocol.

## Failure Handling

| Condition | Action |
|-----------|--------|
| Protected file change needed | STOP → request KERNEL approval |
| Destructive op | STOP → explicit approval |
| Circular dependency | STOP → report |

Everything else → auto-fix within scope and proceed.
