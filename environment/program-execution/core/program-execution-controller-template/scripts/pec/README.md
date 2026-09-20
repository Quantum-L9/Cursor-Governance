# Pec

**Path:** `environment/program-execution/core/program-execution-controller-template/scripts/pec` | **Tier:** discovered

## Purpose

Program Execution Controller runtime package.



## Components

### `BlueprintError`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/blueprint.py` (L20–23)
- Methods: _none_

### `RelockRefused`

A relock the Controller discovered it cannot admit. Nothing was written.

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/blueprint.py` (L132–133)
- Methods: _none_

### `ControllerError`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/common.py` (L15–18)
- Methods: _none_

### `ContractError`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py` (L35–36)
- Methods: _none_

### `DispatchError`

Dispatch refused a worker self-verify or a corrupt route.

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/dispatch.py` (L17–18)
- Methods: _none_

### `ExecEnv`

A resolved, reproducible environment for running validation commands.

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/exec_env.py` (L220–248)
- Methods: `bin_dir`, `describe`, `python_version`

### `GateVerdict`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/gates.py` (L73–87)
- Methods: `to_dict`

### `LedgerError`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/ledger.py` (L27–28)
- Methods: _none_

### `EventLedger`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/ledger.py` (L53–187)
- Methods: `file_events`, `events`, `append`, `project_pending`, `verify`

### `StateError`

No description

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py` (L25–28)
- Methods: _none_

### `StateDB`

The canonical runtime store, opened in explicit-transaction mode.

- File: `environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py` (L74–1172)
- Methods: `in_transaction`, `controller_transaction`, `on_commit`, `schema_version`, `close`, `set_meta`, `get_meta`, `upsert_repository`

## Functions

- `def path_fingerprint(worktree, relative) -> str` — Enough of one path's state to tell "changed again" from "unchanged".
- `def capture_baseline(worktree) -> dict[str, str]` — Fingerprints of everything already changed in the worktree, right now.
- `def baseline_artifact_path(workspace, task_id, attempt_id) -> Path`
- `def write_baseline_artifact(workspace) -> tuple[Path, str]` — Persist the baseline atomically; returns (path, digest of the payload).
- `def load_baseline_artifact(path) -> dict[str, str]` — The baseline this attempt was dispatched under, or a fail-closed refusal.
- `def effected_paths(worktree, baseline) -> list[str]` — Paths the attempt created or altered relative to its own baseline.
- `def normalize_blueprint(root) -> dict[str, Any]`
- `def lock_integrity_errors(lock) -> list[str]` — Why this lock body cannot be trusted as evidence of anything.
- `def semantic_delta(lock, current) -> dict[str, Any]` — Everything that differs, semantically, between a lock and a Blueprint.
- `def classify_lock_drift(lock_path) -> dict[str, Any]` — Compare the active Program Lock against the Blueprint on disk, semantically.
- `def relock_tasks(lock_path, task_ids) -> dict[str, Any]` — Adopt edited task definitions the caller is prepared to admit, or refuse.
- `def validate_program_lock_schema(lock) -> list[str]`
- `def build_program_lock(root) -> dict[str, Any]` — Normalize and schema-check a Blueprint into a lock body, writing nothing.
- `def write_program_lock(root, target) -> dict[str, Any]`
- `def verify_program_lock(lock_path) -> tuple[bool, list[str]]`
- `def task_definition_digest(task) -> str` — A fingerprint of one task's definition, independent of the other tasks.
- `def stale_task_ids(lock_path) -> set[str] | None` — Which tasks' own definitions have moved since the lock was written.
- `def print_json(value) -> None`
- `def parser() -> argparse.ArgumentParser`
- `def peek_command(argv) -> str`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `attempts`, `blueprint`, `collections.abc`, `common`, `contextlib`, `contracts`, `controller`, `dataclasses`, `datetime`, `dispatch`, `exec_env`, `fnmatch`, `gates`, `hashlib`, `importlib.util`, `json`, `ledger`, `os`, `pathlib`, `re`, `runtime`, `shutil`

<!-- l9-module-readme: generated-from-ast -->
