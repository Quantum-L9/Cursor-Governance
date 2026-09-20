# Tools

**Path:** `environment/agents/tools` | **Kind:** subsystem

## Modules

### `render_principals.py`

Render agent grants + validate ADR-0031 door/signing secrets.

- `def fail(msg) -> None`
- `def require_basename(name) -> str` — Reject anything that is not a single path segment (basename only).
- `def under_root(root, rel) -> Path` — Join basename under trusted ``root``; refuse escapes (Sonar-recognized pattern).
- `def load_yaml(path) -> dict`
- `def write_namespaces_for(agent, role, workspace) -> list[str]` — Compute write namespace grants for one agent role.
- `def grants_for(agent, role_def, workspace) -> tuple[list[str], list[str], list[str]]` — Derive read/write/promote namespace globs for one agent.
- `def require_unique(value, seen_ids) -> None`
- `def require_signing_key(agent_id, keys, tokens_path, seen_keys) -> str` — Per-agent HMAC signing key — MUST be unique (ADR-0031 spoof prevention).
- _+5 more public symbol(s)_

### `validate_agents.py`

N-agent registry and adapter validator (peer of validate_claude_env.py).

- `def err(rule, msg) -> None`
- `def check_registry(root) -> dict`
- `def check_one_agent(key, agent, roles, seen) -> None`
- `def check_agents(reg) -> None`
- `def check_one_adapter(key, agent, root, production_url) -> None`
- `def check_adapters(reg, root) -> None`
- `def check_secrets(root) -> None`
- `def main() -> int`

### `validate_executable_peers.py`

- `ExecutablePeerModel`
- `def validate_bindings_schema(repo_root) -> dict[str, Any]`
- `def validate(repo_root) -> dict[str, Any]`
- `def main(argv) -> int`

## Dependencies

**External:** `jsonschema`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
