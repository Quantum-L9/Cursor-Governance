"""Tests for ops/graphiti/graphiti_memory_client.py conflict freshness filtering."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "graphiti"))

from graphiti_memory_client import _fresh_conflicts  # noqa: E402


def _edge(**overrides):
    edge = {
        "uuid": "edge-1",
        "group_id": "cursor-governance",
        "name": "IS_CONFLICTED_WITH",
        "fact": "fixture conflict",
        "attributes": {},
    }
    edge.update(overrides)
    return edge


def test_keeps_fresh_and_unmarked_edges() -> None:
    now = datetime.now(UTC)
    data = [
        _edge(uuid="fresh-no-ts"),
        _edge(uuid="future-expiry", expired_at=(now + timedelta(hours=1)).isoformat()),
        _edge(uuid="future-invalid", invalid_at=(now + timedelta(hours=1)).isoformat()),
    ]
    out = _fresh_conflicts(data, now=now)
    assert {e["uuid"] for e in out} == {"fresh-no-ts", "future-expiry", "future-invalid"}


def test_drops_expired_iso_edges() -> None:
    now = datetime.now(UTC)
    data = [
        _edge(uuid="expired", expired_at=(now - timedelta(minutes=5)).isoformat()),
        _edge(uuid="invalidated", invalid_at=(now - timedelta(minutes=5)).isoformat()),
        _edge(uuid="kept"),
    ]
    out = _fresh_conflicts(data, now=now)
    assert {e["uuid"] for e in out} == {"kept"}


def test_drops_expired_numeric_edges() -> None:
    now = datetime.now(UTC)
    past = (now - timedelta(minutes=5)).timestamp()
    data = [
        _edge(uuid="expired-num", expired_at=past),
        _edge(uuid="kept"),
    ]
    out = _fresh_conflicts(data, now=now)
    assert {e["uuid"] for e in out} == {"kept"}


def test_preserves_non_dict_entries() -> None:
    data = [{"uuid": "kept"}, "not-a-dict", 42]
    out = _fresh_conflicts(data)
    assert "not-a-dict" in out and 42 in out
