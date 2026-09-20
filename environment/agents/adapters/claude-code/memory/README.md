# Memory

**Path:** `environment/agents/adapters/claude-code/memory` | **Tier:** discovered

## Purpose

Shared exception types for the memory enforcement modules.



## Components

### `MemoryErrorBase`

Base class for every memory-subsystem error.

- File: `environment/agents/adapters/claude-code/memory/errors.py` (L13–14)
- Methods: _none_

### `MemoryWriteDenied`

Raised when a memory write is refused by attribution policy.

- File: `environment/agents/adapters/claude-code/memory/errors.py` (L17–23)
- Methods: _none_

## Functions

- `def find_governance_root() -> Path`
- `def ensure_importable(root) -> Path` — Put the governance root first on ``sys.path`` so ``ops.memory`` imports.
- `def bind_session_env(env, session_id) -> dict[str, str]` — Force the memory session id to the caller's session (no setdefault).
- `def memory_client(session_id) -> Any` — A canonical client bound to this checkout's memory runtime.
- `def hydrate(task) -> dict[str, Any]` — Canonical hydration for one repository (integration-receipt shape).
- `def conflicts() -> dict[str, Any]` — Memory conflicts are evidence, never a mutex.
- `def load_contract() -> dict[str, Any]`
- `def workspace_root() -> Path` — Resolve the session workspace root that anchors ``.l9/memory``.
- `def extract_chat_id(event) -> tuple[str, str]` — Per-chat discriminator for the write-gate receipt. Never the session id.
- `def extract_writer_agent_id(event) -> str`
- `def receipt_identity() -> tuple[str, str]` — The two RAW components of a writer receipt key: ``(writer_agent, chat)``.
- `def compose_receipt_id(writer_agent, chat) -> str` — ``<writer_agent>__<chat>`` — the one place the receipt key is spelled.
- `def resolve_receipt_id() -> str` — Writer-scoped receipt key. Distinct from SessionStart's session id.
- `def resolve_session_id() -> str` — SessionStart session id only. Never a write-gate receipt key.
- `def graphiti_state_path(session_id) -> Path`
- `def identity_snapshot(contract, session_id) -> dict[str, str]`
- `def workspace_for_target(tool_input) -> Path` — Git root of the file being edited, else the session workspace.
- `def state_root(contract, workspace) -> Path`
- `def resolve_namespaces(contract) -> list[str]`
- `def resolve_writer_identity(contract) -> dict[str, str]` — Resolve the memory writer's identity from the environment.

## Exports

`BOUNDARY_REL`, `bind_session_env`, `conflicts`, `ensure_importable`, `find_governance_root`, `hydrate`, `memory_client`

## Dependencies

`__future__`, `errors`, `json`, `os`, `pathlib`, `re`, `subprocess`, `sys`, `time`, `typing`

<!-- l9-module-readme: generated-from-ast -->
