# Hooks

**Path:** `environment/agents/adapters/claude-code/hooks` | **Tier:** discovered

## Purpose

Deny first Edit/Write of stack files unless Context7 ran or a PASS receipt exists.



## Components

### Shell entrypoints

- `environment/agents/adapters/claude-code/hooks/bootstrap_capability_preflight.sh`
- `environment/agents/adapters/claude-code/hooks/l9_hook_exec.sh`
- `environment/agents/adapters/claude-code/hooks/session_deps_cloud.sh`
- `environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh`

## Functions

- `def main() -> int`
- `def autonomy_required() -> bool`
- `def authority_from_environment() -> dict[str, Any] | None` — The worker window's root authority, or None when it is incomplete.
- `def persisted_authority(environment_authority) -> tuple[dict[str, Any] | None, str]` — Resolve the window's environment to the grant receipt PE persisted.
- `def authorize(raw) -> int` — 0 when this effect may proceed to the ops gate, 2 when it may not.
- `def main() -> int`
- `def main() -> int`
- `def main() -> int`
- `def main() -> int`
- `def main() -> int`
- `def render(summary) -> str`
- `def main() -> int`
- `def main() -> int`
- `def main() -> int`
- `def skill_from_payload(payload) -> tuple[str, str]`
- `def main() -> int`
- `def load_routing(root)`
- `def find_governance_root() -> Path`
- `def log_recommendation(payload, recommendation) -> None`
- `def main() -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `classify_hydrate_state`, `hashlib`, `importlib.util`, `json`, `memory_bridge`, `memory_state`, `os`, `pathlib`, `re`, `runpy`, `subprocess`, `surface_detect`, `sys`, `time`, `typing`, `workspace_roots`

<!-- l9-module-readme: generated-from-ast -->
