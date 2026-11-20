"""Own-PR gate and the three REST review routes for pr_threads.py."""

from __future__ import annotations

import json
import subprocess
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


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _checkout(tmp_path: Path, branch: str = "feat/x") -> tuple[Path, str]:
    """A real repository on ``branch`` with one commit; returns (root, HEAD sha)."""
    root = tmp_path / "ws"
    root.mkdir()
    _git(root, "init", "-q", "-b", branch)
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("one\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-q", "-m", "one")
    return root, _git(root, "rev-parse", "HEAD")


def _live(pr: dict[str, object] | None = None, *, get_fails: bool = False):
    seen: list[tuple[list[str], str | None]] = []

    def fake(argv: list[str], *, input_text: str | None = None) -> str:
        seen.append((argv, input_text))
        if "GET" in argv:
            if get_fails:
                raise SystemExit(1)
            return json.dumps(pr)
        if argv[-1].endswith("/resolve"):
            return json.dumps({"comment_ids": [1], "resolved": True})
        return "{}"

    return seen, fake


def _pr(sha: str, **over: object) -> dict[str, object]:
    data: dict[str, object] = {
        "state": "open",
        "head": {"ref": "feat/x", "sha": sha, "repo": {"full_name": "O/R"}},
    }
    head = dict(data["head"])  # type: ignore[arg-type]
    head.update(over.pop("head", {}))  # type: ignore[arg-type]
    data["head"] = head
    data.update(over)
    return data


def _posts(seen: list[tuple[list[str], str | None]]) -> list[list[str]]:
    return [argv for argv, _ in seen if "POST" in argv]


def test_no_receipt_live_proof_admits_this_checkouts_pr(tmp_path: Path) -> None:
    root, sha = _checkout(tmp_path)
    seen, fake = _live(_pr(sha))
    code = pr_threads.execute(
        ["reply", "--pr", "612", "--comment-id", "5"],
        workspace=root,
        origin="o/r",
        run=fake,
        stdin="Fixed",
    )
    assert code == 0
    assert seen[0][0] == ["gh", "api", "--method", "GET", "repos/o/r/pulls/612"]
    assert _posts(seen) == [
        ["gh", "api", "--method", "POST", "repos/o/r/pulls/612/comments/5/replies", "--input", "-"]
    ]


def test_no_receipt_live_proof_accepts_an_unpushed_local_fix(tmp_path: Path) -> None:
    root, pushed = _checkout(tmp_path)
    (root / "f.txt").write_text("two\n", encoding="utf-8")
    _git(root, "commit", "-q", "-am", "fix")
    seen, fake = _live(_pr(pushed))
    pr_threads.execute(
        ["resolve", "--pr", "612", "--comment-id", "5"],
        workspace=root,
        origin="o/r",
        run=fake,
        stdin="",
    )
    assert _posts(seen) == [
        ["gh", "api", "--method", "POST", "repos/o/r/pulls/612/ccr/comments/5/resolve"]
    ]


@pytest.mark.parametrize(
    "over",
    [
        {"state": "closed"},
        {"head": {"repo": {"full_name": "fork/r"}}},
        {"head": {"repo": None}},
        {"head": {"ref": "feat/other"}},
        {"head": {"sha": "0" * 40}},
        {"head": {"sha": ""}},
    ],
    ids=["closed", "foreign-head-repo", "deleted-fork", "other-branch", "unknown-sha", "no-sha"],
)
def test_no_receipt_live_proof_refuses_before_any_post(
    tmp_path: Path, over: dict[str, object]
) -> None:
    root, sha = _checkout(tmp_path)
    seen, fake = _live(_pr(sha, **over))
    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["comment", "--pr", "612"], workspace=root, origin="o/r", run=fake, stdin="status"
        )
    assert _posts(seen) == []


def test_no_receipt_head_sha_ahead_of_checkout_refuses(tmp_path: Path) -> None:
    root, first = _checkout(tmp_path)
    (root / "f.txt").write_text("two\n", encoding="utf-8")
    _git(root, "commit", "-q", "-am", "two")
    later = _git(root, "rev-parse", "HEAD")
    _git(root, "reset", "-q", "--hard", first)
    seen, fake = _live(_pr(later))
    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["comment", "--pr", "612"], workspace=root, origin="o/r", run=fake, stdin="status"
        )
    assert _posts(seen) == []


def test_no_receipt_detached_head_refuses_before_gh(tmp_path: Path) -> None:
    root, sha = _checkout(tmp_path)
    _git(root, "checkout", "-q", "--detach", sha)
    seen, fake = _live(_pr(sha))
    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["comment", "--pr", "612"], workspace=root, origin="o/r", run=fake, stdin="status"
        )
    assert seen == []


def test_no_receipt_get_failure_refuses(tmp_path: Path) -> None:
    root, _sha = _checkout(tmp_path)
    seen, fake = _live(get_fails=True)
    with pytest.raises(SystemExit):
        pr_threads.execute(
            ["comment", "--pr", "612"], workspace=root, origin="o/r", run=fake, stdin="status"
        )
    assert _posts(seen) == []


def test_receipt_present_still_decides_without_a_live_get(tmp_path: Path) -> None:
    root, _sha = _checkout(tmp_path)
    _write_summary(root)
    seen, fake = _live({"state": "closed"})
    pr_threads.execute(
        ["comment", "--pr", "612"], workspace=root, origin="o/r", run=fake, stdin="status"
    )
    assert [argv for argv, _ in seen if "GET" in argv] == []
    assert len(_posts(seen)) == 1


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
    assert "Bash(python3 ~/.cursor-governance/ops/scripts/pr_threads.py:*)" in allow
    assert "Bash(gh api --method POST:*)" not in allow
    assert "Bash(gh api -X POST:*)" not in allow
