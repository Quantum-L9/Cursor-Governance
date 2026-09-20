# Distill Queue

**Path:** `ops/graphiti/distill_queue` | **Tier:** discovered

## Purpose

S3-backed redacted distill job queue (SessionEnd enqueue + GHA worker).



## Components

_No public classes in this path._

## Functions

- `def enqueue_enabled() -> bool`
- `def bucket_configured() -> bool`
- `def job_content_hash() -> str`
- `def build_job() -> dict[str, Any]`
- `def object_key(content_hash) -> str`
- `def put_job_s3(job) -> dict[str, Any]` — Put job JSON to S3. Idempotent overwrite on same content_hash key.
- `def enqueue_job() -> dict[str, Any]` — Build + enqueue. Raises on failure when called (caller decides fail-loud).
- `def list_pending_keys() -> list[str]`
- `def get_job_to_path(key, dest) -> dict[str, Any]`
- `def mark_done(key, job) -> None`
- `def already_ingested(content_hash) -> bool`
- `def distill_job(job) -> dict[str, Any]` — LLM distill → SessionSignalPacket-shaped dict.
- `def build_continuation(job, packet) -> ContinuationCapsuleV2` — The distilled PICKUP as the Cursor-owned continuation capsule (plan §12).
- `def ingest_to_memory(job, packet) -> list[dict[str, Any]]` — Admit the continuation capsule and promoted atomics through the control plane.
- `def process_pending() -> dict[str, Any]`
- `def main(argv) -> int`

## Exports

`enqueue_job`, `job_content_hash`, `process_pending`

## Dependencies

`__future__`, `argparse`, `datetime`, `hashlib`, `json`, `ops.graphiti.distill_queue.enqueue`, `ops.graphiti.distill_queue.worker`, `ops.graphiti.hydration.openai_fixed_host`, `ops.graphiti.hydration.openai_key`, `ops.memory.control_plane_client`, `ops.memory.session_contracts`, `os`, `pathlib`, `subprocess`, `sys`, `tempfile`, `time`, `typing`

<!-- l9-module-readme: generated-from-ast -->
