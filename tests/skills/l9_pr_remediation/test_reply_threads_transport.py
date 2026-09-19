"""Transport selection for reply_threads: REST surfaces never reach GraphQL.

The regression these cover: ops/scripts/lib/gh_graphql.sh guards `gh api graphql`
with a bash function, but reply_threads.py execs the `gh` binary via subprocess,
so no shell function was ever in scope. Replies landed (REST-backed tooling) and
resolve 403'd, leaving threads replied-but-unresolved.
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

import reply_threads  # noqa: E402

REST_ENV = ("L9_GITHUB_GRAPHQL_MODE", "CLAUDE_CODE_REMOTE", "GH_GRAPHQL_UNSUPPORTED")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in REST_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Capture every gh argv and answer with a plausible body."""
    seen: list[list[str]] = []

    def fake(argv: list[str], *, input_text: str | None = None) -> str:
        seen.append(argv)
        if argv[-1].endswith("/resolve") or "/resolve" in " ".join(argv):
            return json.dumps({"comment_ids": [1], "resolved": True})
        return "{}"

    monkeypatch.setattr(reply_threads, "_run_gh", fake)
    return seen


def _thread(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "comment_id": 4053495282,
        "thread_id": "PRRT_abc",
        "inspected": True,
        "disposition": "fixed",
        "body": "done",
        "path": "ops/memory/cli.py",
    }
    base.update(over)
    return base


# --- classification --------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("L9_GITHUB_GRAPHQL_MODE", "rest-only"),
        ("CLAUDE_CODE_REMOTE", "true"),
        ("GH_GRAPHQL_UNSUPPORTED", "1"),
    ],
)
def test_rest_only_honors_each_signal(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    assert reply_threads._rest_only() is False
    monkeypatch.setenv(name, value)
    assert reply_threads._rest_only() is True


def test_rest_only_ignores_unrelated_values(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_GITHUB_GRAPHQL_MODE", "graphql")
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "false")
    monkeypatch.setenv("GH_GRAPHQL_UNSUPPORTED", "0")
    assert reply_threads._rest_only() is False


# --- the actual regression -------------------------------------------------


def test_rest_surface_never_builds_graphql_argv(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, calls: list[list[str]]
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    threads = [_thread(), _thread(comment_id=99)]

    reply_threads._reply_rest("o/r", 612, threads)
    reply_threads._resolve_rest("o/r", 612, threads)
    reply_threads._post_summary("o/r", 612, "body")

    assert calls, "no gh calls recorded"
    for argv in calls:
        assert "graphql" not in argv, f"GraphQL argv on a REST surface: {argv}"
        assert argv[:2] != ["gh", "pr"], f"gh pr subcommand on a REST surface: {argv}"


def test_rest_routes_are_the_documented_ones(
    clean_env: None, monkeypatch: pytest.MonkeyPatch, calls: list[list[str]]
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    th = _thread(comment_id=4053495282)

    reply_threads._reply_rest("o/r", 612, [th])
    reply_threads._resolve_rest("o/r", 612, [th])
    reply_threads._post_summary("o/r", 612, "body")

    paths = [argv[-1] if argv[-1] != "-" else argv[-3] for argv in calls]
    assert paths == [
        "repos/o/r/pulls/612/comments/4053495282/replies",
        "repos/o/r/pulls/612/ccr/comments/4053495282/resolve",
        "repos/o/r/issues/612/comments",
    ]


def test_resolve_rejects_unconfirmed_response(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    monkeypatch.setattr(
        reply_threads,
        "_run_gh",
        lambda argv, input_text=None: json.dumps({"resolved": False}),
    )
    with pytest.raises(SystemExit):
        reply_threads._resolve_rest("o/r", 612, [_thread()])


# --- ledger key contract ---------------------------------------------------


def test_rest_ledger_requires_comment_id(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    prs = [{"number": 612, "threads": [_thread(comment_id=None)]}]
    with pytest.raises(SystemExit):
        reply_threads._require_inspected(prs)


def test_graphql_ledger_requires_thread_id(clean_env: None) -> None:
    prs = [{"number": 612, "threads": [_thread(thread_id="")]}]
    with pytest.raises(SystemExit):
        reply_threads._require_inspected(prs)


def test_each_surface_accepts_its_own_key(
    clean_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A REST ledger carries no node id at all — ccr/review_threads cannot emit one.
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")
    reply_threads._require_inspected(
        [{"number": 612, "threads": [_thread(thread_id=None)]}]
    )
    monkeypatch.delenv("CLAUDE_CODE_REMOTE")
    reply_threads._require_inspected(
        [{"number": 612, "threads": [_thread(comment_id=None)]}]
    )


def test_summary_survives_a_ledger_with_no_thread_id(clean_env: None) -> None:
    # _summary_markdown used to index th["thread_id"] unconditionally.
    pr = {"number": 612, "threads": [_thread(thread_id=None, finding=None, path=None)]}
    body = reply_threads._summary_markdown(pr, cycle=1, commit="abc", verify="pass")
    assert "4053495282"[-8:] in body
