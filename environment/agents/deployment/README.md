# Deployment

**Path:** `environment/agents/deployment` | **Kind:** subsystem

## Modules

### `__init__.py`

### `receipts.py`

Deployment receipt write/verify helpers via runtime_paths.

- `DeploymentNotReady` — Cursor deployment receipt is missing, invalid, blocked, or stale.
- `def canonical_json_bytes(value) -> bytes`
- `def compute_receipt_digest(receipt) -> str`
- `def with_receipt_digest(receipt) -> dict[str, Any]`
- `def verify_receipt_digest(receipt) -> bool`
- `def workspace_id_for(workspace) -> str`
- `def receipt_path() -> Path`
- `def write_deployment_receipt(receipt) -> Path`
- _+3 more public symbol(s)_

### `reconcile.py`

Reconcile governed Cursor subagent roles into ~/.cursor/agents.

- `def load_contract(path) -> dict[str, Any]`
- `def build_expected() -> tuple[dict[str, str], str, str]`
- `def reconcile_cursor() -> dict[str, Any]` — Materialize managed Cursor agents and emit a deployment receipt.
- `def reconcile() -> dict[str, Any]`
- `def main(argv) -> int`

### `validate.py`

Validate Cursor subagent deployment readiness (effective definition + shadows).

- `def evaluate_role() -> dict[str, Any]` — Evaluate one role's effective runtime definition.
- `def validate_deployment() -> dict[str, Any]` — Return DEPLOYMENT_READY iff every role's effective definition is L9-managed.

## Dependencies

**Internal:** `environment`, `renderers`

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
