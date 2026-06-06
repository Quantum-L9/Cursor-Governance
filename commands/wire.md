---
name: wire
version: "12.3.0"
description: "TRIGGER ONLY — governance workspace wiring OR wire_executor.py for code components"
before_chain: rules
auto_chain: ynp
dag_executor: .cursor/workflows-synced/wire_executor.py
---

# /wire — Component Wiring (v12.3.0)

## THIS IS A TRIGGER ONLY

`/wire` invokes either **governance workspace wiring** (special case) or the **Wire Executor DAG** for code components.

## GOVERNANCE WORKSPACE (run first on new/existing repos)

Ensures `.cursor-commands` points at Dropbox GlobalCommands SSOT and `sessionEnd` backup hook is active.

```bash
# Check only (exit 1 if miswired)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/check_governance_wiring.sh" "$(pwd)"

# Repair + re-check (what /wire governance runs)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/wire_governance_workspace.sh" "$(pwd)"
```

**Aliases:** `/wire governance`, `/wire governance-workspace`, `/wire .cursor-commands`

**Does NOT use `wire_executor.py`.** Runs `setup_workspace_symlinks.sh` (symlinks + hook install) then `check_governance_wiring.sh`.

**Auto-chained from `/start-session`** when the check fails — session cannot proceed until PASS.

## CODE COMPONENT WIRING

## INVOCATION

```bash
python3 .cursor/workflows-synced/wire_executor.py <component>
```

## WHAT THE DAG DOES (AUTONOMOUS)

```
┌─────────────────────────────────────────────────────────┐
│  DISCOVERY        │ Find ALL references with rg        │
├─────────────────────────────────────────────────────────┤
│  ANALYSIS         │ Classify component type            │
├─────────────────────────────────────────────────────────┤
│  PLAN             │ Create surgical action list        │
├─────────────────────────────────────────────────────────┤
│  EXECUTE          │ Apply fixes (NO user confirmation) │
├─────────────────────────────────────────────────────────┤
│  VALIDATE         │ py_compile + import test           │
├─────────────────────────────────────────────────────────┤
│  RE-DISCOVERY     │ Confirm all refs fixed             │
├─────────────────────────────────────────────────────────┤
│  CONFIRM-WIRING   │ Full verification pass             │
├─────────────────────────────────────────────────────────┤
│  GENERATE-REPORT  │ GMP report via script              │
├─────────────────────────────────────────────────────────┤
│  COMMIT           │ Stage + commit (NO PUSH)           │
└─────────────────────────────────────────────────────────┘
```

## FEATURES

- **Fully autonomous** — No user confirmation gates
- **Protected file detection** — Auto-escalates to /gmp
- **Semantic refusals** — Blocks dangerous patterns
- **Auto-report** — Uses canonical report generator
- **Safe commit** — Commits locally, does NOT push

## USAGE

```bash
# Wire a module
python3 .cursor-commands/workflows/wire_executor.py core/tools/registry.py

# Wire by import path
python3 .cursor-commands/workflows/wire_executor.py memory.substrate_service

# Check status
python3 .cursor-commands/workflows/wire_executor.py --status

# Resume if interrupted
python3 .cursor-commands/workflows/wire_executor.py --resume

# Reset state
python3 .cursor-commands/workflows/wire_executor.py --reset
```

## STATE FILE

Execution state is persisted to `.wire_executor_state.json`

If interrupted, resume with `--resume`.

## PROTECTED FILES (AUTO-ESCALATE)

If these files need changes, executor auto-escalates to /gmp:
- `core/agents/executor.py`
- `runtime/websocket_orchestrator.py`
- `memory/substrate_service.py`
- `docker-compose.yml`
- `Dockerfile`

## OUTPUT

The executor produces:
1. Terminal progress for each step
2. GMP report at `reports/GMP-Report-*.md`
3. Local commit (no push)

## ENFORCEMENT

The DAG is MANDATORY. The slash command is just a trigger.

All step ordering, validation, and reporting is handled by the executor.
