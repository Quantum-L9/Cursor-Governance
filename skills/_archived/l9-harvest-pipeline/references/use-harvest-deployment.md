<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-harvest-pipeline
layer: reference
role: use_harvest_deployment_protocol
tags: [l9, harvest, deployment, cp, wire]
owner: igor_beylin
status: active
version: 2.0.1
updated: 2026-06-06
dag_executor: .cursor-commands/workflows/use_harvest_executor.py
auto_chain: wire
--- /SKILL_META ---
-->

# /use-harvest — Deploy Harvested Code

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
