"""Tests for ops/graphiti/graphiti_memory_client.py conflict freshness filtering."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "graphiti"))

from graphiti_memory_client import (  # noqa: E402
    _conflicts_in_scope,
    _conflicts_matching_task,
    _fresh_conflicts,
    cmd_conflicts,
)


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


def test_conflicts_in_scope_drops_other_group_and_offtree_paths(tmp_path: Path) -> None:
    root = tmp_path / "Cursor-Governance"
    root.mkdir()
    data = [
        _edge(uuid="same-group"),
        _edge(uuid="other-group", group_id="seo-bot"),
        _edge(uuid="off-tree", path="/tmp/unrelated/file.py"),
        _edge(uuid="rel-path", path="ops/secrets/authed_npm.sh"),
    ]
    out = _conflicts_in_scope(data, "cursor-governance", root=root)
    assert {e["uuid"] for e in out} == {"same-group", "rel-path"}


def test_preserves_non_dict_entries() -> None:
    data = [{"uuid": "kept"}, "not-a-dict", 42]
    out = _fresh_conflicts(data)
    assert "not-a-dict" in out and 42 in out


def test_conflicts_matching_task_requires_task_and_marker() -> None:
    data = [
        _edge(uuid="unrelated-token", fact="mentions conflicts_with only"),
        _edge(
            uuid="task-conflict",
            fact="conflicts_with bind RP-002 Gate client on memory-node",
        ),
        _edge(uuid="task-without-marker", name="RELATED_TO", fact="bind RP-002 Gate client"),
    ]
    out = _conflicts_matching_task(data, "bind RP-002 Gate client")
    assert {e["uuid"] for e in out} == {"task-conflict"}


def test_cmd_conflicts_without_task_is_unavailable_not_blocking(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        "graphiti_memory_client.resolve_group_id",
        lambda _p: {"group_id": "cursor-governance"},
    )
    monkeypatch.setattr("graphiti_memory_client.load_env", lambda: None)

    class _Args:
        task = ""
        namespace = ""
        include_expired = False

    rc = cmd_conflicts(_Args())
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["conflicts"] == []
    assert payload["status"] == "unavailable"
    assert "task" in payload["reason"]


def test_cmd_conflicts_clean_graph_has_no_conflicts(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "graphiti_memory_client.resolve_group_id",
        lambda _p: {"group_id": "cursor-governance"},
    )
    monkeypatch.setattr("graphiti_memory_client.load_env", lambda: None)
    monkeypatch.setattr(
        "graphiti_memory_client._search_group_status",
        lambda *_a, **_k: ([], []),
    )

    class _Args:
        task = "hydrate session packet"
        namespace = "cursor-governance"
        include_expired = False

    rc = cmd_conflicts(_Args())
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["conflicts"] == []
    assert payload["status"] == "ok"
    # Former acquire path: empty conflicts means no --force required.
    overlaps = payload.get("conflicts") or []
    assert not overlaps


def test_cmd_conflicts_search_failure_is_unavailable(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "graphiti_memory_client.resolve_group_id",
        lambda _p: {"group_id": "cursor-governance"},
    )
    monkeypatch.setattr("graphiti_memory_client.load_env", lambda: None)
    monkeypatch.setattr(
        "graphiti_memory_client._search_group_status",
        lambda *_a, **_k: ([], ["search_memory_facts: connection refused"]),
    )

    class _Args:
        task = "hydrate session packet"
        namespace = ""
        include_expired = False

    rc = cmd_conflicts(_Args())
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["conflicts"] == []
    assert payload["status"] == "unavailable"
    assert "unreachable" in payload["reason"]
