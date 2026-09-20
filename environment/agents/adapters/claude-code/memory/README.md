# Memory

**Path:** `environment/agents/adapters/claude-code/memory` | **Kind:** subsystem

## Modules

### `errors.py`

Shared exception types for the memory enforcement modules.

- `MemoryErrorBase` — Base class for every memory-subsystem error.
- `MemoryWriteDenied` — Raised when a memory write is refused by attribution policy.

### `memory_bridge.py`

Thin Claude adapter → canonical memory control plane (campaign stage C8).

- `def find_governance_root() -> Path`
- `def ensure_importable(root) -> Path` — Put the governance root first on ``sys.path`` so ``ops.memory`` imports.
- `def bind_session_env(env, session_id) -> dict[str, str]` — Force the memory session id to the caller's session (no setdefault).
- `def memory_client(session_id) -> Any` — A canonical client bound to this checkout's memory runtime.
- `def hydrate(task) -> dict[str, Any]` — Canonical hydration for one repository (integration-receipt shape).
- `def conflicts() -> dict[str, Any]` — Memory conflicts are evidence, never a mutex.

Exports: `BOUNDARY_REL`, `bind_session_env`, `conflicts`, `ensure_importable`, `find_governance_root`, `hydrate`, `memory_client`

### `memory_state.py`

Local state + contract matching shared by the memory enforcement hooks.

- `def load_contract() -> dict[str, Any]`
- `def workspace_root() -> Path` — Resolve the session workspace root that anchors ``.l9/memory``.
- `def extract_chat_id(event) -> tuple[str, str]` — Per-chat discriminator for the write-gate receipt. Never the session id.
- `def extract_writer_agent_id(event) -> str`
- `def receipt_identity() -> tuple[str, str]` — The two RAW components of a writer receipt key: ``(writer_agent, chat)``.
- `def compose_receipt_id(writer_agent, chat) -> str` — ``<writer_agent>__<chat>`` — the one place the receipt key is spelled.
- `def resolve_receipt_id() -> str` — Writer-scoped receipt key. Distinct from SessionStart's session id.
- `def resolve_session_id() -> str` — SessionStart session id only. Never a write-gate receipt key.
- _+14 more public symbol(s)_

## Dependencies

**Internal:** `errors`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
