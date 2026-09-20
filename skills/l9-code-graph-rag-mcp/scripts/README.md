# Scripts

**Path:** `skills/l9-code-graph-rag-mcp/scripts` | **Tier:** discovered

## Purpose

Invoke code-graph-rag-mcp tools via one-shot JSON-RPC CLI (stderr suppressed).



## Components

### Shell entrypoints

- `skills/l9-code-graph-rag-mcp/scripts/code_graph_batch_index.sh`
- `skills/l9-code-graph-rag-mcp/scripts/code_graph_gmp_baseline.sh`
- `skills/l9-code-graph-rag-mcp/scripts/code_graph_health.sh`

## Functions

- `def resolve_bin() -> Path`
- `def resolve_repo() -> Path`
- `def extract_jsonrpc_payload(stdout) -> dict[str, Any]` — Return JSON-RPC response from stdout (pretty-printed or single-line).
- `def call_tool(repo_root, tool_name, arguments) -> dict[str, Any]`
- `def main() -> int`
- `def is_plasticos_repo(repo) -> bool`
- `def normalize_rel_path(path) -> str`
- `def is_high_impact_path(rel_path) -> bool`
- `def is_foundation_path(rel_path) -> bool`
- `def entity_hint_for_path(rel_path) -> str | None`
- `def load_evidence(repo) -> dict[str, Any] | None`
- `def evidence_is_fresh(data) -> bool`
- `def evidence_covers_path(data, rel_path) -> bool`
- `def extract_tool_path(hook_input) -> tuple[str | None, str | None]`
- `def extract_mcp_tool(hook_input) -> tuple[str | None, dict[str, Any]]`
- `def hook_response(permission, user_message, agent_message) -> dict[str, Any]`
- `def check_pre_tool_use(hook_input) -> dict[str, Any]`
- `def check_before_mcp(hook_input) -> dict[str, Any]`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `datetime`, `json`, `os`, `pathlib`, `re`, `subprocess`, `sys`, `typing`

<!-- l9-module-readme: generated-from-ast -->
