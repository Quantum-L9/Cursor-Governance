# Tools

**Path:** `environment/agents/tools` | **Tier:** discovered

## Purpose

Render l9-graphiti-memory auth_tokens.json from the agent registry.



## Components

### `ExecutablePeerModel`

No description

- File: `environment/agents/tools/validate_executable_peers.py` (L30–79)
- Methods: `entries_for`, `descriptor`, `required_peers`

## Functions

- `def fail(msg) -> None`
- `def require_basename(name) -> str` — Reject anything that is not a single path segment (basename only).
- `def under_root(root, rel) -> Path` — Join basename under trusted ``root``; refuse escapes (Sonar-recognized pattern).
- `def load_yaml(path) -> dict`
- `def write_namespaces_for(agent, role, workspace) -> list[str]` — Compute write namespace grants for one agent role.
- `def grants_for(agent, role_def, workspace) -> tuple[list[str], list[str], list[str]]` — Derive read/write/promote namespace globs for one agent.
- `def require_unique(value, seen_ids) -> None`
- `def require_token(agent_id, token_map, tokens_path, seen_tokens) -> str`
- `def build_principal(agent, role_def) -> dict`
- `def process_agent(key, agent, roles) -> tuple[str, dict] | None`
- `def write_under_root(root, rel, content) -> Path` — Validate relative path under root, then write via open().
- `def main() -> int`
- `def err(rule, msg) -> None`
- `def check_registry(root) -> dict`
- `def check_one_agent(key, agent, roles, seen) -> None`
- `def check_agents(reg) -> None`
- `def check_one_adapter(key, agent, root, production_url) -> None`
- `def check_adapters(reg, root) -> None`
- `def check_secrets(root) -> None`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `json`, `jsonschema`, `os`, `pathlib`, `re`, `sys`, `typing`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
