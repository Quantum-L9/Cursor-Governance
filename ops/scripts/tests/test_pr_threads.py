"""Own-PR gate and the three REST review routes for pr_threads.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pr_threads  # noqa: E402
from lib.pr_thread_routes import (  # noqa: E402
    FOOTER_MARK,
    parse_origin_repo,
)

TEMPLATE = REPO / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"


def _write_summary(workspace: Path, **over: object) -> None:
    data: dict[str, object] = {
        "schema": "l9.pr_summary.v1",
        "repo": "o/r",
        "number": 612,
        "state": "open",
    }
    data.update(over)
    path = workspace / ".l9" / "pr" / "pr-summary.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _capture() -> tuple[list[tuple[list[str], str | None]], object]:
    seen: list[tuple[list[str], str | None]] = []

    def fake(argv: list[str], *, input_text: str | None = None) -> str:
        seen.append((argv, input_text))
        if argv[-1].endswith("/resolve"):
            return json.dumps({"comment_ids": [1], "resolved": True})
        return "{}"

    return seen, fake


def test_reply_posts_comment_id_route_and_footer(tmp_path: Path) -> None:
    _write_summary(tmp_path)
    seen, fake = _capture()
    code = pr_threads.execute(
        ["reply", "--pr", "612", "--comment-id", "4053495282"],
        workspace=tmp_path,
        origin="o/r",
        run=fake,
        stdin="Fixed in abc\n",
    )
    assert code == 0
    argv, payload = seen[0]
    assert argv == [
        "gh",
        "api",
        "--method",
        "POST",
        "repos/o/r/pulls/612/comments/4053495282/replies",
        "--input",
        "-",
    ]
    body = json.loads(payload or "")["body"]
    assert body.startswith("Fixed in abc")
    assert FOOTER_MARK in body
    assert "graphql" not in argv
    assert "merge" not in " ".join(argv)
    assert "unresolve" not in " ".join(argv)


def test_resolve_requires_resolved_true(tmp_path: Path) -> None:
    _write_summary(tmp_path)
    seen, _fake = _capture()

    def unresolved(argv: list[str], *, input_text: str | None = None) -> str:
        seen.append((argv, input_text))
        return json.dumps({"resolved": False})

    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["resolve", "--pr", "612", "--comment-id", "9"],
            workspace=tmp_path,
            origin="o/r",
            run=unresolved,
            stdin="",
        )
    assert seen[0][0][-1] == "repos/o/r/pulls/612/ccr/comments/9/resolve"


def test_comment_posts_issue_route(tmp_path: Path) -> None:
    _write_summary(tmp_path)
    seen, fake = _capture()
    pr_threads.execute(
        ["comment", "--pr", "612"],
        workspace=tmp_path,
        origin="o/r",
        run=fake,
        stdin="status",
    )
    argv, payload = seen[0]
    assert argv[-3] == "repos/o/r/issues/612/comments"
    assert FOOTER_MARK in json.loads(payload or "")["body"]


@pytest.mark.parametrize(
    "summary",
    [
        {"number": 7},
        {"repo": "other/repo"},
        {"state": "closed"},
    ],
)
def test_own_pr_mismatches_refuse_before_gh(tmp_path: Path, summary: dict[str, object]) -> None:
    _write_summary(tmp_path, **summary)
    seen, fake = _capture()
    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["resolve", "--pr", "612", "--comment-id", "9"],
            workspace=tmp_path,
            origin="o/r",
            run=fake,
            stdin="",
        )
    assert seen == []


def test_missing_receipt_refuses(tmp_path: Path) -> None:
    seen, fake = _capture()
    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["comment", "--pr", "612"],
            workspace=tmp_path,
            origin="o/r",
            run=fake,
            stdin="status",
        )
    assert seen == []


def test_parse_origin_repo_forms() -> None:
    assert parse_origin_repo("git@github.com:Quantum-L9/Cursor-Governance.git") == (
        "quantum-l9/cursor-governance"
    )
    assert parse_origin_repo("https://github.com/Quantum-L9/Cursor-Governance") == (
        "quantum-l9/cursor-governance"
    )


def test_template_allowlists_the_helper_only() -> None:
    allow = json.loads(TEMPLATE.read_text(encoding="utf-8"))["permissions"]["allow"]
    assert "Bash(python3 ops/scripts/pr_threads.py:*)" in allow
    assert "Bash(python3 -u ops/scripts/pr_threads.py:*)" in allow
    assert "Bash(gh api --method POST:*)" not in allow
    assert "Bash(gh api -X POST:*)" not in allow
