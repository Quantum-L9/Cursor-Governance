"""Session state as gate evidence (stage C8): hydration-only, never a grant."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ops.memory import session_state as ss


@pytest.fixture
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(ss.ENV_STATE_DIR, str(tmp_path / "state"))
    return tmp_path / "state"


def _state(**overrides: object) -> dict:
    base = {
        "schema": ss.STATE_SCHEMA,
        "authority": "none",
        "session_id": "s1",
        "task_signature": "abc123",
        ss.SATISFIED_KEY: [],
        "memory_status": "OK",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    base.update(overrides)
    return base


def test_fresh_hydration_satisfies_and_stale_does_not() -> None:
    assert ss.memory_satisfied(_state())
    old = (datetime.now(UTC) - timedelta(minutes=45)).isoformat()
    assert not ss.memory_satisfied(_state(timestamp=old))
    assert ss.memory_satisfied(_state(timestamp=old), ttl_minutes=60)


def test_memory_that_did_not_answer_never_satisfies() -> None:
    for status in ("BINDING_FAILED", "CANONICAL_UNAVAILABLE", "TIMEOUT", None):
        assert not ss.hydration_is_fresh(_state(memory_status=status))
    assert ss.hydration_is_fresh(_state(memory_status="NO_HITS"))


def test_explicit_satisfaction_outlives_freshness() -> None:
    old = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    state = _state(timestamp=old, **{ss.SATISFIED_KEY: ["abc123"]})
    assert ss.memory_satisfied(state)
    assert not ss.memory_satisfied(state, task_signature="other")


def test_empty_or_missing_state_is_not_satisfied() -> None:
    assert not ss.memory_satisfied(None)
    assert not ss.memory_satisfied({})


def test_task_change_clears_explicit_satisfactions(state_dir: Path) -> None:
    ss.set_task_signature("s1", "sig-a")
    assert ss.mark_satisfied("s1")
    data = ss.read_session_state("s1")
    assert data[ss.SATISFIED_KEY] == ["sig-a"]
    assert data["authority"] == "none"
    # Same task: nothing changes; a stub without memory_status satisfies nothing.
    ss.set_task_signature("s1", "sig-a")
    assert ss.read_session_state("s1")[ss.SATISFIED_KEY] == ["sig-a"]
    assert not ss.hydration_is_fresh(ss.read_session_state("s1"))
    ss.set_task_signature("s1", "sig-b")
    assert ss.read_session_state("s1")[ss.SATISFIED_KEY] == []


def test_mark_satisfied_without_state_or_signature_is_false(state_dir: Path) -> None:
    assert not ss.mark_satisfied("nobody")
    path = ss.state_path("s2")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_state(session_id="s2", task_signature=None)), encoding="utf-8")
    assert not ss.mark_satisfied("s2")


def test_foreign_schema_is_ignored(state_dir: Path) -> None:
    path = ss.state_path("s3")
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"prefetch_ts": "2099-01-01", "task_signature": "x"}))
    assert ss.read_session_state("s3") is None
