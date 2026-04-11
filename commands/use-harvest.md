---
name: use-harvest
version: "2.0.0"
description: "TRIGGER ONLY — Invokes use_harvest_executor.py for deployment"
auto_chain: wire
dag_executor: .cursor-commands/workflows/use_harvest_executor.py
---

# /use-harvest — Deploy Harvested Code (v2.0.0)

## THIS IS A TRIGGER ONLY

`/use-harvest` invokes the Use-Harvest Executor DAG. All logic lives in the executor.

## INVOCATION

```bash
python3 .cursor-commands/workflows/use_harvest_executor.py path/to/harvested/
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  READ-TABLE       │ Parse HARVEST_TABLE.md             │
├─────────────────────────────────────────────────────────┤
│  VERIFY-TARGETS   │ Check if targets exist (→ action)  │
├─────────────────────────────────────────────────────────┤
│  DEPLOY-FILES     │ cp to targets (NO manual rewrite)  │
├─────────────────────────────────────────────────────────┤
│  VALIDATE-SYNTAX  │ py_compile on deployed files       │
├─────────────────────────────────────────────────────────┤
│  WIRE-IMPORTS     │ Check __init__.py needs            │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — NO user confirmation gates
- **cp-based deployment** — Uses cp NOT manual rewrite
- **Action detection** — CREATE, REPLACE, or CREATE_DIR
- **Wire hints** — Identifies __init__.py updates needed
- **Auto-report** — Uses canonical report generator

## USAGE

```bash
# Deploy harvested files
python3 .cursor-commands/workflows/use_harvest_executor.py current_work/harvested/01-25-2026/Implementation/

# Check status
python3 .cursor-commands/workflows/use_harvest_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/use_harvest_executor.py --resume
```

## HARVEST_TABLE.md FORMAT

The executor reads this format:

```markdown
| # | Pattern | Source Lines | Target |
|---|---------|--------------|--------|
| 1 | `orchestrator.py` | 27-693 | `core/agents/bootstrap/orchestrator.py` |
| 2 | `models.py` | 702-828 | `core/agents/bootstrap/models.py` |
```

## NEXT STEP

After deployment completes, run:
```bash
python3 .cursor-commands/workflows/wire_executor.py {deployed_module}
```

Or use `/wire` to fix imports and exports.
