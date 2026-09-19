"""REST thread discovery for ingest_signals on GraphQL-less surfaces.

`_paginate_threads` reached `gh api graphql` for the reviewThreads query, so on
a Claude Code Web/Mobile gateway ingestion 403'd before a ledger existed at all
— the resolve fix in reply_threads.py is unreachable without this half.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "l9-pr-remediation" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ingest_signals  # noqa: E402

REST_ENV = ("L9_GITHUB_GRAPHQL_MODE", "CLAUDE_CODE_REMOTE", "GH_GRAPHQL_UNSUPPORTED")


@pytest.fixture
def rest(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REST_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")


@pytest.fixture
def graphql(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REST_ENV:
        monkeypatch.delenv(name, raising=False)


def _fake_gh_json(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, Any]) -> list[str]:
    seen: list[str] = []

    def fake(path: str) -> Any:
        seen.append(path)
        for key, value in mapping.items():
            if path.endswith(key):
                return value
        raise AssertionError(f"unexpected REST path: {path}")

    monkeypatch.setattr(ingest_signals, "_gh_json", fake)
    return seen


THREADS = [
    {"resolved": False, "outdated": False, "path": "a.py", "line": 7, "comment_ids": [11, 12]},
    {"resolved": True, "outdated": False, "path": "b.py", "line": 3, "comment_ids": [21]},
]
COMMENTS = [
    {"id": 11, "body": "first finding\nmore", "path": "a.py", "line": 7, "user": {"login": "bot"}},
    {"id": 12, "body": "reply", "path": "a.py", "line": 7, "user": {"login": "igor"}},
    {"id": 21, "body": "done", "path": "b.py", "line": 3, "user": {"login": "bot"}},
]


def test_rest_discovery_uses_no_graphql(
    rest: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _fake_gh_json(
        monkeypatch, {"ccr/review_threads": THREADS, "/comments": COMMENTS}
    )

    def explode(*_a: Any, **_k: Any) -> str:
        raise AssertionError("_run_gh reached on a REST surface (graphql path)")

    monkeypatch.setattr(ingest_signals, "_run_gh", explode)

    nodes = ingest_signals._paginate_threads("o", "r", 612)

    assert seen == ["repos/o/r/pulls/612/ccr/review_threads", "repos/o/r/pulls/612/comments"]
    assert len(nodes) == 2
    assert [n["isResolved"] for n in nodes] == [False, True]
    assert [n["comment_id"] for n in nodes] == [11, 21]
    assert all(n["id"] is None for n in nodes), "REST cannot supply a GraphQL node id"


def test_rest_nodes_satisfy_from_thread(rest: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """The synthesized shape must feed _from_thread unchanged."""
    _fake_gh_json(monkeypatch, {"ccr/review_threads": THREADS, "/comments": COMMENTS})
    nodes = ingest_signals._paginate_threads("o", "r", 612)

    finding = ingest_signals._from_thread(nodes[0], 0)
    assert finding is not None
    assert finding["author"] == "bot"  # _login reads REST's `user` key
    assert finding["file"] == "a.py"
    assert finding["line"] == 7
    assert finding["message"] == "first finding"
    assert finding["comment_id"] == 11
    assert finding["thread_id"] is None

    # Resolved threads are dropped, same as on GraphQL.
    assert ingest_signals._from_thread(nodes[1], 1) is None


def test_thread_with_no_retrievable_comments_fails_loudly(
    rest: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fake_gh_json(
        monkeypatch,
        {"ccr/review_threads": THREADS, "/comments": []},
    )
    with pytest.raises(SystemExit):
        ingest_signals._paginate_threads("o", "r", 612)


def _rest_node(comment_id: int, *, resolved: bool = False) -> dict[str, Any]:
    return {
        "id": None,
        "comment_id": comment_id,
        "isResolved": resolved,
        "comments": {
            "nodes": [
                {
                    "id": comment_id,
                    "body": "finding",
                    "path": "a.py",
                    "line": 1,
                    "user": {"login": "bot"},
                }
            ]
        },
    }


def _collect(fixtures: Path, nodes: list[dict[str, Any]], tmp: Path) -> dict[str, Any]:
    (fixtures / "pr.json").write_text('{"head_sha": "abc"}', encoding="utf-8")
    (fixtures / "threads.json").write_text(json.dumps({"nodes": nodes}), encoding="utf-8")
    return ingest_signals.collect(
        owner="o",
        repo="r",
        pr=612,
        required_checks=set(),
        fixture_dir=fixtures,
        cwd=tmp,
        scanners={},
    )


def test_rest_completeness_reports_capture(
    rest: None, tmp_path: Path
) -> None:
    fixtures = tmp_path / "fx"
    fixtures.mkdir()
    snap = _collect(fixtures, [_rest_node(11), _rest_node(12)], tmp_path)
    assert snap["completeness"]["unresolved_threads"] == 2
    assert snap["completeness"]["unresolved_threads_captured"] is True


def test_rest_completeness_is_not_vacuously_true(
    rest: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The regression: keyed on "id", every REST node was filtered out.

    `all([])` is True, so a surface that captured nothing reported full
    capture and the `_fail` guard in main() never fired.
    """
    fixtures = tmp_path / "fx"
    fixtures.mkdir()
    monkeypatch.setattr(ingest_signals, "_from_thread", lambda node, index: None)
    snap = _collect(fixtures, [_rest_node(11)], tmp_path)
    assert snap["completeness"]["unresolved_threads"] == 1
    assert snap["completeness"]["unresolved_threads_captured"] is False


def test_graphql_surface_still_uses_graphql(
    graphql: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[list[str]] = []

    def fake_run_gh(argv: list[str], *, input_text: str | None = None) -> str:
        called.append(argv)
        return (
            '{"data":{"repository":{"pullRequest":{"reviewThreads":'
            '{"pageInfo":{"hasNextPage":false},"nodes":[]}}}}}'
        )

    monkeypatch.setattr(ingest_signals, "_run_gh", fake_run_gh)
    ingest_signals._paginate_threads("o", "r", 612)
    assert called and "graphql" in called[0]
