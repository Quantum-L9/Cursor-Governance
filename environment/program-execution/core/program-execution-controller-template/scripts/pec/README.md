# Pec

**Path:** `environment/program-execution/core/program-execution-controller-template/scripts/pec` | **Kind:** subsystem

## Modules

### `__init__.py`

Program Execution Controller runtime package.

### `attempts.py`

Execution-attempt identity and the immutable pre-dispatch effect baseline.

- `def path_fingerprint(worktree, relative) -> str` — Enough of one path's state to tell "changed again" from "unchanged".
- `def capture_baseline(worktree) -> dict[str, str]` — Fingerprints of everything already changed in the worktree, right now.
- `def baseline_artifact_path(workspace, task_id, attempt_id) -> Path`
- `def write_baseline_artifact(workspace) -> tuple[Path, str]` — Persist the baseline atomically; returns (path, digest of the payload).
- `def load_baseline_artifact(path) -> dict[str, str]` — The baseline this attempt was dispatched under, or a fail-closed refusal.
- `def effected_paths(worktree, baseline) -> list[str]` — Paths the attempt created or altered relative to its own baseline.

### `blueprint.py`

- `BlueprintError`
- `RelockRefused` — A relock the Controller discovered it cannot admit. Nothing was written.
- `def normalize_blueprint(root) -> dict[str, Any]`
- `def lock_integrity_errors(lock) -> list[str]` — Why this lock body cannot be trusted as evidence of anything.
- `def semantic_delta(lock, current) -> dict[str, Any]` — Everything that differs, semantically, between a lock and a Blueprint.
- `def classify_lock_drift(lock_path) -> dict[str, Any]` — Compare the active Program Lock against the Blueprint on disk, semantically.
- `def relock_tasks(lock_path, task_ids) -> dict[str, Any]` — Adopt edited task definitions the caller is prepared to admit, or refuse.
- `def validate_program_lock_schema(lock) -> list[str]`
- _+5 more public symbol(s)_

### `cli.py`

- `def print_json(value) -> None`
- `def parser() -> argparse.ArgumentParser`
- `def peek_command(argv) -> str`
- `def require_campaign_tunnel(command) -> None`
- `def main(argv) -> int`

### `common.py`

- `ControllerError`
- `def utc_now() -> str`
- `def canonical_json(value) -> str`
- `def digest_object(value) -> str`
- `def sha256_file(path) -> str`
- `def load_json(path) -> Any`
- `def load_yaml(path) -> Any`
- `def write_json(path, value) -> None`
- _+5 more public symbol(s)_

### `contracts.py`

- `ContractError`
- `def normalize_repo_path(value) -> str`
- `def path_allowed(path, patterns) -> bool`
- `def validate_source_contract(contract, task) -> dict[str, Any]`
- `def draft_source_contract(db, task_id, output) -> Path`
- `def register_source_contract(db, ledger, workspace, task_id, source, actor, replace) -> dict[str, Any]`
- `def render_contract(db, ledger, workspace, task_id) -> dict[str, Any]`

### `controller.py`

- `def write_campaign_status(workspace) -> dict[str, Any]`
- `def closure_receipt_path(workspace, closure_id) -> Path`
- `def complete_campaign(workspace, actor, verdict, evidence) -> dict[str, Any]` — The one Controller operation that turns an active runtime terminal.
- `def ensure_campaign_active(workspace, actor, db, ledger) -> dict[str, Any]`
- `def load_json_or_yaml(path) -> Any`
- `def bootstrap(workspace, blueprint, template_root) -> dict[str, Any]`
- `def relock_definitions(workspace) -> dict[str, Any]` — Adopt edited task definitions without discarding execution history.
- `def admit_resume(workspace) -> dict[str, Any]` — Decide whether a live runtime may resume against the Blueprint on disk.
- _+28 more public symbol(s)_

### `dispatch.py`

Route a rendered contract, probe a provider, and map a pre-submission receipt.

- `DispatchError` — Dispatch refused a worker self-verify or a corrupt route.
- `def pe_root() -> Path`
- `def assert_worker_cannot_self_verify(rendered) -> None`
- `def map_provider_result_to_presubmission(rendered) -> dict[str, Any]`
- `def route_rendered(rendered) -> dict[str, Any]`
- `def dispatch_rendered_contract(rendered) -> dict[str, Any]` — Route, optionally probe/invoke, and map a pre-submission receipt.

### `exec_env.py`

One execution environment for worker-side and controller-side validation.

- `ExecEnv` — A resolved, reproducible environment for running validation commands.
- `def is_l9_isolate_workspace(path) -> bool` — Match ops/scripts/resolve_governance_paths.sh is_l9_isolate_workspace.
- `def is_consumer_task_worktree(path) -> bool` — True for $L9_ROOT/programs/<id>/worktrees/<task> consumer checkouts.
- `def exec_env_root(worktree) -> Path | None` — Where a consumer task worktree's provisioned environment lives.
- `def resolve_exec_env(cwd) -> ExecEnv` — Resolve the single environment both validation sides must use.
- `def run_validation_command(command, cwd) -> dict[str, Any]` — Run one contract-declared validation command and report what happened.
- `def to_attempt_result(result) -> dict[str, Any]` — Shrink a validation result to the attempt-receipt shape.

### `gates.py`

Controller-derived convergence gate evaluation (PEC-P1-005).

- `GateVerdict`
- `def derive_gate_result(db, gate, evidence_ids) -> GateVerdict` — Derive the gate's verdict from its definition and the runtime's evidence.

### `ledger.py`

The append-only event ledger: SQLite is the chain, the file is its projection.

- `LedgerError`
- `EventLedger`
- `def verify_chain(events) -> tuple[bool, str]` — Structural verification of a list of events, wherever they came from.

### `preflight.py`

Compose validate_runtime + task_readiness + receipt/lock into next_action.

- `def preflight(workspace) -> dict[str, Any]`

_+6 further module(s) in this directory._

## Dependencies

**Internal:** `attempts`, `blueprint`, `common`, `contracts`, `controller`, `dispatch`, `exec_env`, `gates`, `ledger`, `runtime`, `state`, `workspace_reset`

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
