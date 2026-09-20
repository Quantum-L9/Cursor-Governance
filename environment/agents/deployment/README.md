# Deployment

**Path:** `environment/agents/deployment` | **Tier:** discovered

## Purpose

Deployment receipt write/verify helpers via runtime_paths.



## Components

### `DeploymentNotReady`

Cursor deployment receipt is missing, invalid, blocked, or stale.

- File: `environment/agents/deployment/receipts.py` (L27–28)
- Methods: _none_

## Functions

- `def canonical_json_bytes(value) -> bytes`
- `def compute_receipt_digest(receipt) -> str`
- `def with_receipt_digest(receipt) -> dict[str, Any]`
- `def verify_receipt_digest(receipt) -> bool`
- `def workspace_id_for(workspace) -> str`
- `def receipt_path() -> Path`
- `def write_deployment_receipt(receipt) -> Path`
- `def read_deployment_receipt() -> dict[str, Any] | None`
- `def source_manifest_digest(repo_root) -> str`
- `def require_cursor_deployment_ready(workspace, repo_root) -> dict[str, Any]` — Read the Cursor receipt; do not write agents.
- `def load_contract(path) -> dict[str, Any]`
- `def build_expected() -> tuple[dict[str, str], str, str]`
- `def reconcile_cursor() -> dict[str, Any]` — Materialize managed Cursor agents and emit a deployment receipt.
- `def reconcile() -> dict[str, Any]`
- `def main(argv) -> int`
- `def evaluate_role() -> dict[str, Any]` — Evaluate one role's effective runtime definition.
- `def validate_deployment() -> dict[str, Any]` — Return DEPLOYMENT_READY iff every role's effective definition is L9-managed.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `datetime`, `environment.agents.deployment`, `environment.agents.deployment.renderers`, `hashlib`, `importlib.util`, `json`, `pathlib`, `renderers`, `subprocess`, `sys`, `typing`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
