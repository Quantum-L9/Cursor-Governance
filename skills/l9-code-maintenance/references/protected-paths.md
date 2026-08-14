<!-- L9_META
l9_schema: 1
parent: l9-code-maintenance
layer: reference
role: protected_paths
tags: [governance, protected, fail-closed]
owner: igor_beylin
status: active
version: 3.0.0
updated: 2026-08-06
/L9_META -->

# Protected Paths

Any hit on these paths during a sweep or migrate dry-run forces **GMP REQUIRED**.

## Law / activation

- `CANONICAL_LAW.md`
- `AGENTS.md`
- `ORG_INVARIANTS.yaml`
- `ops/hooks/session_start_bootstrap.sh`
- `ops/scripts/resolve_governance_paths.sh`
- `ops/scripts/backup_to_github.sh`

## Program / campaign execution contracts

- `environment/program-execution/core/shared/`
- `environment/program-execution/core/**/schemas/`
- paths matching `program-execution-*.schema.json` or schema `$id` containing `program-execution`

## Autonomy packages (do not casually move)

- `autonomy/` (root Python package — import path locked)
- `environment/program-execution/peer_execution/autonomy/`

## Executor legacy protected set (PlasticOS-oriented)

- `core/agents/executor.py`
- `runtime/websocket_orchestrator.py`
- `memory/substrate_service.py`
- `docker-compose.yml`
- `Dockerfile`
