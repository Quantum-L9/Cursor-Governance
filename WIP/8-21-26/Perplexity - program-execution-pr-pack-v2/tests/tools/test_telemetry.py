"""tests/tools/test_telemetry.py — smoke tests for ops/lib/telemetry.py."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ops.lib.telemetry import emit  # noqa: E402


def test_emit_writes_valid_event(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_REPORTS_DIR", str(tmp_path))
    ok = emit("lease_acquired", node_id="EN-010", agent_id="agentA", detail={"scope": "db_branch"})
    assert ok is True
    jsonl = tmp_path / "telemetry" / "program_execution_events.jsonl"
    assert jsonl.exists()
    line = json.loads(jsonl.read_text().strip().splitlines()[-1])
    assert line["event_type"] == "lease_acquired"
    assert line["node_id"] == "EN-010"


def test_emit_rejects_unknown_event_type_without_raising(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_REPORTS_DIR", str(tmp_path))
    ok = emit("not_a_real_event", node_id="EN-010")
    assert ok is False
    jsonl = tmp_path / "telemetry" / "program_execution_events.jsonl"
    assert not jsonl.exists()


def test_emit_appends_multiple_events(tmp_path, monkeypatch):
    monkeypatch.setenv("L9_REPORTS_DIR", str(tmp_path))
    emit("lease_acquired", node_id="EN-010")
    emit("lease_released", node_id="EN-010")
    jsonl = tmp_path / "telemetry" / "program_execution_events.jsonl"
    lines = jsonl.read_text().strip().splitlines()
    assert len(lines) == 2
