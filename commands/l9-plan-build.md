---
name: l9-plan-build
version: "1.0.0"
description: "Plan via /l9-plan-simple, Improve then Validate & Repair, execute via Cursor Build /gmp"
auto_chain: ynp
dag: plan-simple-build-v1
dag_file: workflows/dags/plan_simple_build_dag.py
---

# /l9-plan-build — plan, harden, Build/GMP

**DAG-ENFORCED.** Execute `plan-simple-build-v1` at `workflows/dags/plan_simple_build_dag.py` (`SESSION_GUIDANCE`).

Composes existing owners. Do not invent a second skill.

## Usage

```
/l9-plan-build
/l9-plan-build <objective>
```

## EXECUTION

1. Read each node's `action` path in graph order. Domain files own the work.
2. Do not skip Improve → Validate & Repair before Build/GMP.
3. Do not run `make campaign`. Do not admit a Program Lock.

## Key files

- Graph: `workflows/dags/plan_simple_build_dag.py`
- Plan: `skills/l9-plan-simple/SKILL.md`
- Upstream: `skills/l9-global-architect/SKILL.md`
- Receipt: `skills/l9-plan-simple/scripts/validate_plan_section_receipt.py`
- Kernels: `kernels/Improve.md`, `kernels/Validate & Repair.md`
- Build execute: `skills/l9-plan-simple/references/plan-workflow-simple.md`
- GMP: `commands/gmp.md` → `workflows/gmp_executor.py`
