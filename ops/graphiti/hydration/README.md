# Hydration

**Path:** `ops/graphiti/hydration` | **Kind:** subsystem

## Modules

### `__init__.py`

Session hydration + close pipeline over the canonical memory control plane (C4/C6).

Exports: `close_session`, `compile_session_packet`

### `archive_transcript.py`

Archive closed-chat words + timestamps to S3 (no sqlite, no tool dumps).

- `def pending_root() -> Path`
- `def bucket_name() -> str`
- `def object_key(conversation_id) -> str`
- `def extract_turns(path) -> list[dict[str, Any]]`
- `def build_document() -> dict[str, Any]`
- `def resolve_source() -> Path | None`
- `def write_pending(doc) -> Path`
- `def put_s3(doc) -> dict[str, Any]`
- _+8 more public symbol(s)_

### `cli.py`

CLI: ``python -m ops.graphiti.hydration.cli compile|close|retry-close|repair-write``.

- `def main(argv) -> int`

### `close_session.py`

sessionEnd close (campaign stages C5/C6): canonical candidate + memory.close.

- `def re_safe(session_id) -> str`
- `def already_closed(project_dir, session_id, head_hash) -> bool`
- `def write_receipt(project_dir, session_id, payload) -> None` — Persist the close obligation with taint-safe scalars only (plan §16).
- `def memory_client(session_id) -> MemoryControlPlaneClient` — The bound memory runtime under the close surface's envelope.
- `def build_capsule() -> ContinuationCapsuleV2` — The Cursor-owned continuation capsule for this session (plan §12).
- `def session_task_signature(session_id) -> str | None` — The task signature this session hydrated under, from local session state.
- `def close_idempotency_key(namespace, session_id, head_hash) -> str` — Stable operation identity: producer, namespace, session, transcript head.
- `def close_session() -> dict[str, Any]` — Canonical close. Fail-open to hooks; never raises. Never writes a provider.

### `compile_session_packet.py`

Compile SessionHydrationPacket for sessionStart additional_context.

- `def environment_fault_reason(status, error, environment_heal) -> str` — One line naming the bootstrap fault; never calls it memory degradation.
- `def environment_fault_repair(status) -> str`
- `def compile_session_packet() -> dict[str, Any]` — Build a SessionHydrationPacket dict (fail-open; never raises to hooks).
- `def format_additional_context(packet) -> str` — Human-readable hydrate block: one field=value per line, then JSON.
- `def compile_and_format() -> dict[str, Any]`

### `identity.py`

Writer identity for Graphiti episodes (agent_id dual-stamp).

- `IdentityError` — Missing or cross-surface writer identity.
- `def resolve_write_identity() -> dict[str, str]` — Resolve agent_id / user_id for a memory write.
- `def stamp_source_description(agent_id, kind) -> str`
- `def envelope_body(body) -> str` — Prefix a compact attribution envelope; preserve JSON bodies when possible.

### `pickup_write.py`

Canonical close retry and forced ``/end-session`` repair (ADR-0028, stage C6).

- `def retry_close() -> dict[str, Any]` — Discharge a ``close_incomplete`` obligation with the same idempotency key.
- `def repair_close() -> dict[str, Any]` — Forced ``/end-session`` parity: explicit capsule -> candidate -> memory.close.

Exports: `fallback_pickup_write`, `repair_close`, `repair_pickup_write`, `retry_close`

### `redaction.py`

PII redaction for transcript excerpts before they leave the session.

- `def redact_pii(text, enabled) -> str`

Exports: `redact_pii`

### `session_latches.py`

Session open/close latches and the local close obligation (ADR-0028, plan §16).

- `def resolve_session_id() -> str` — Session-scoped id for open, close, and SessionStart compile.
- `def session_pointer_path(project_dir) -> Path` — Where SessionStart records the lifecycle id it generated for this repo.
- `def persisted_session_id(project_dir) -> str` — The lifecycle id an earlier SessionStart persisted, or empty. Never raises.
- `def create_session_id(project_dir) -> tuple[str, str]` — Generate a lifecycle id and try to persist it. Never raises.
- `def resolve_session_lifecycle(project_dir) -> tuple[str, str]` — ONE lifecycle id for open, compile and close, plus its persistence status.
- `def resolve_or_create_session_id(project_dir) -> str` — The session id from :func:`resolve_session_lifecycle`, status dropped.
- `def re_safe(session_id) -> str`
- `def opens_dir(project_dir) -> str`
- _+17 more public symbol(s)_

### `transcript.py`

Transcript load + cap + PII redact for session close.

- `def transcript_char_cap() -> int`
- `def load_transcript_excerpt() -> tuple[str, str]` — Return (excerpt, source_label). Empty excerpt if nothing found.

## Dependencies

**Internal:** `ops`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
