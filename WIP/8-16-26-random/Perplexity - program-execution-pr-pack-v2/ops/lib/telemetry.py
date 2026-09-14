"""ops/lib/telemetry.py — shared in-process telemetry emitter.

Import this from tools/agent_git.py, tools/check_feature_tree.py,
tools/environment_lease.py, and tools/semantic_merge_probe.py to emit
program_execution_event records without shelling out to
ops/scripts/emit_program_execution_metrics.py on every call.

Usage (see wiring/ob-010-instrumentation-diffs.md for exact call sites):

    from ops.lib.telemetry import emit
    emit("lease_acquired", node_id=args.node_id, agent_id=args.agent_id,
         detail={"scope": scope})

Fails soft: telemetry must never abort the underlying git/lease/tree
operation. Any error in emit() is caught and printed to stderr only.
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

try:
    import jsonschema
except ImportError:
    jsonschema = None

VALID_EVENT_TYPES = {
    "queue_enqueued", "queue_wait_seconds", "queue_batch_result",
    "lease_acquired", "lease_reclaimed", "lease_released",
    "scope_violation", "rebase_failure", "push_retry_exhausted",
    "semantic_conflict_detected", "test_impact_selected",
    "remediation_time_seconds",
}


def _reports_dir() -> Path:
    override = os.environ.get("L9_REPORTS_DIR")
    if override:
        return Path(override)
    return Path("reports") / time.strftime("%Y-%m-%d")


def _schema_path() -> Path:
    return Path(os.environ.get(
        "L9_TELEMETRY_SCHEMA",
        "ops/schemas/program_execution_event.schema.json",
    ))


def emit(event_type: str, node_id: str, agent_id: str | None = None, detail: dict | None = None) -> bool:
    """Append a program_execution_event. Returns True on success, False on
    any failure (never raises — telemetry must not break the caller)."""
    try:
        if event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"unknown event_type: {event_type}")

        event = {
            "event_type": event_type,
            "node_id": node_id,
            "timestamp": time.time(),
            "agent_id": agent_id,
            "detail": detail or {},
        }

        schema_path = _schema_path()
        if jsonschema is not None and schema_path.exists():
            schema = json.loads(schema_path.read_text())
            jsonschema.validate(event, schema)

        out_dir = _reports_dir() / "telemetry"
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "program_execution_events.jsonl", "a") as f:
            f.write(json.dumps(event) + "\n")
        return True
    except Exception as e:  # noqa: BLE001 — telemetry must fail soft
        print(f"telemetry warning: failed to emit {event_type}: {e}", file=sys.stderr)
        return False
