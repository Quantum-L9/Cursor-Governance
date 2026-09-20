# Scripts

**Path:** `skills/l9-code-graph-rag-mcp/scripts` | **Kind:** subsystem

## Modules

### `code_graph_cli.py`

Invoke code-graph-rag-mcp tools via one-shot JSON-RPC CLI (stderr suppressed).

- `def resolve_bin() -> Path`
- `def resolve_repo() -> Path`
- `def extract_jsonrpc_payload(stdout) -> dict[str, Any]` — Return JSON-RPC response from stdout (pretty-printed or single-line).
- `def call_tool(repo_root, tool_name, arguments) -> dict[str, Any]`
- `def main() -> int`

### `code_graph_plasticos_gate.py`

Shared PlasticOS code-graph gate logic for Cursor hooks and GMP baseline.

- `def is_plasticos_repo(repo) -> bool`
- `def normalize_rel_path(path) -> str`
- `def is_high_impact_path(rel_path) -> bool`
- `def is_foundation_path(rel_path) -> bool`
- `def entity_hint_for_path(rel_path) -> str | None`
- `def load_evidence(repo) -> dict[str, Any] | None`
- `def evidence_is_fresh(data) -> bool`
- `def evidence_covers_path(data, rel_path) -> bool`
- _+6 more public symbol(s)_

## Entrypoints

- `code_graph_batch_index.sh`
- `code_graph_gmp_baseline.sh`
- `code_graph_health.sh`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
