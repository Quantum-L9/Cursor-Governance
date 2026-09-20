# Hydration

**Path:** `ops/graphiti/hydration` | **Tier:** discovered

## Purpose

Session hydration + close pipeline over the canonical memory control plane (C4/C6).



## Components

### `IdentityError`

Missing or cross-surface writer identity.

- File: `ops/graphiti/hydration/identity.py` (L9–10)
- Methods: _none_

## Functions

- `def pending_root() -> Path`
- `def bucket_name() -> str`
- `def object_key(conversation_id) -> str`
- `def extract_turns(path) -> list[dict[str, Any]]`
- `def build_document() -> dict[str, Any]`
- `def resolve_source() -> Path | None`
- `def write_pending(doc) -> Path`
- `def put_s3(doc) -> dict[str, Any]`
- `def mark_done(pending_path, result) -> None`
- `def archive_one() -> dict[str, Any]`
- `def file_times(path) -> dict[str, str | None]`
- `def iter_live_jsonl() -> list[Path]`
- `def live_jsonl_meta(path) -> dict[str, Any]`
- `def sync_raw() -> dict[str, Any]`
- `def backfill() -> dict[str, Any]`
- `def main(argv) -> int`
- `def re_safe(session_id) -> str`
- `def already_closed(project_dir, session_id, head_hash) -> bool`
- `def write_receipt(project_dir, session_id, payload) -> None` — Persist the close obligation with taint-safe scalars only (plan §16).
- `def memory_client(session_id) -> MemoryControlPlaneClient` — The bound memory runtime under the close surface's envelope.

## Exports

`close_session`, `compile_session_packet`, `fallback_pickup_write`, `redact_pii`, `repair_close`, `repair_pickup_write`, `retry_close`

## Dependencies

`__future__`, `argparse`, `datetime`, `hashlib`, `json`, `logging`, `ops.graphiti.hydration`, `ops.graphiti.hydration.identity`, `ops.graphiti.hydration.redaction`, `ops.graphiti.hydration.session_latches`, `ops.graphiti.hydration.transcript`, `ops.memory.agent_lane`, `ops.memory.control_plane_client`, `ops.memory.hydration`, `ops.memory.namespace_context`, `ops.memory.runtime_binding`, `ops.memory.session_contracts`, `ops.memory.session_state`, `os`, `pathlib`, `re`, `shutil`, `socket`, `subprocess`

<!-- l9-module-readme: generated-from-ast -->
