---
name: gmp
version: "8.2.0"
description: "TRIGGER ONLY — Invokes gmp_executor.py for enforced phased execution"
before_chain: rules
auto_chain: ynp
dag: gmp-execution-v1
dag_executor: .cursor/workflows-synced/gmp_executor.py
---

# /gmp — Governance Managed Process (v8.1.0)

## THIS IS A TRIGGER ONLY

`/gmp` invokes the GMP Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 .cursor/workflows-synced/gmp_executor.py "task description" --tier RUNTIME
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  MEMORY_READ      │ Load context from memory substrate │
├─────────────────────────────────────────────────────────┤
│  SCOPE_LOCK       │ Lock TODO plan (Phase 0)           │
├─────────────────────────────────────────────────────────┤
│  USER_GATE        │ Confirm scope before proceeding    │
├─────────────────────────────────────────────────────────┤
│  BASELINE         │ Phase 1 — Verify current state     │
├─────────────────────────────────────────────────────────┤
│  IMPLEMENT        │ Phase 2 — Execute changes          │
├─────────────────────────────────────────────────────────┤
│  GENERATE_TESTS   │ Phase 3 — Auto-generate tests      │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ Phase 4 — Run tests + lint         │
├─────────────────────────────────────────────────────────┤
│  MEMORY_WRITE     │ Phase 5 — Record lessons learned   │
├─────────────────────────────────────────────────────────┤
│  GENERATE_REPORT  │ Phase 6 — Create GMP report        │
├─────────────────────────────────────────────────────────┤
│  COMMIT_GATE      │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Phased execution** — Enforced GMP v1.7 phases 0-6
- **Memory integration** — Reads context, writes lessons
- **Tier classification** — KERNEL, RUNTIME, INFRA, UX
- **Auto-report** — Uses canonical report generator
- **Safe commit** — Commits locally, does NOT push

## USAGE

```bash
# Start new GMP
python3 .cursor/workflows-synced/gmp_executor.py "add validation to registry" --tier RUNTIME

# Resume interrupted GMP
python3 .cursor/workflows-synced/gmp_executor.py --resume

# Check current status
python3 .cursor/workflows-synced/gmp_executor.py --status

# Reset state (start fresh)
python3 .cursor/workflows-synced/gmp_executor.py --reset
```

## TIERS

| Tier | Scope | Examples |
|---|---|---|
| KERNEL | Core execution, safety | executor.py, kernel_loader.py |
| RUNTIME | Services, tools, agents | task_queue.py, tool_registry.py |
| INFRA | Deployment, docker, k8s | docker-compose.yml, Dockerfile |
| UX | Frontend, docs, scripts | React components, README |

## STATE FILE

Execution state is persisted to `.gmp_executor_state.json`

If interrupted, resume with `--resume`.

## OUTPUT

The executor produces:
1. Terminal progress for each step
2. GMP report at `reports/GMP-Report-*.md`
3. Local commit (no push)

## ENFORCEMENT

The DAG is MANDATORY. The slash command is just a trigger.

All step ordering, validation, and reporting is handled by the executor.
