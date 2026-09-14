"""SessionEnd preserve — this conversation only. Never porcelain. Never delete."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import session_end_preserve  # noqa: E402
from session_authored_ledger import record_event  # noqa: E402
from session_end_preserve import _git, run  # noqa: E402

OLD = 100.0  # seconds: pre-existing dirt is older than any shell window


def _age(*paths: Path) -> None:
    stamp = time.time() - OLD
    for path in paths:
        os.utime(path, (stamp, stamp))


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    (root / "tracked.md").write_text("base\n", encoding="utf-8")
    git(root, "add", "--", "tracked.md")
    git(root, "commit", "-m", "base")
    return root


def _event(ws: Path, session_id: str = "sess-1") -> dict:
    return {
        "session_id": session_id,
        "workspace_roots": [str(ws)],
        "reason": "window_close",
    }


def test_parks_only_ledger_paths_and_leaves_foreign_dirt(repo: Path, tmp_path: Path) -> None:
    home = tmp_path / "ledgers"
    (repo / "mine.md").write_text("mine-bytes\n", encoding="utf-8")
    (repo / "other-chat.md").write_text("foreign\n", encoding="utf-8")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(repo)],
            "tool_input": {"path": str(repo / "mine.md")},
        },
        home=home,
    )
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True
    assert receipt["paths"] == ["mine.md"]
    assert "other-chat.md" not in receipt["paths"]
    assert (repo / "mine.md").is_file()
    assert (repo / "other-chat.md").is_file()
    blob = git(repo, "show", f"{receipt['ref']}:mine.md")
    assert blob == "mine-bytes"
    ls = git(repo, "ls-tree", "-r", "--name-only", receipt["ref"])
    assert "mine.md" in ls.splitlines()
    assert "other-chat.md" not in ls.splitlines()
    status = git(repo, "status", "--porcelain")
    assert "mine.md" in status
    assert "other-chat.md" in status


def test_empty_ledger_skips_without_touching_tree(repo: Path, tmp_path: Path) -> None:
    home = tmp_path / "ledgers"
    (repo / "stray.md").write_text("stray\n", encoding="utf-8")
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is False
    assert receipt["skipped"] == "empty_ledger"
    assert (repo / "stray.md").is_file()
    refs = subprocess.run(
        ["git", "-C", str(repo), "for-each-ref", "refs/l9/preserved/session"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert refs.stdout.strip() == ""


def test_workspace_mismatch_skips(repo: Path, tmp_path: Path) -> None:
    home = tmp_path / "ledgers"
    other = tmp_path / "other-ws"
    other.mkdir()
    (repo / "mine.md").write_text("x\n", encoding="utf-8")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(other)],
            "tool_input": {"path": str(other / "mine.md")},
        },
        home=home,
    )
    (other / "mine.md").write_text("x\n", encoding="utf-8")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(other)],
            "tool_input": {"path": str(other / "mine.md")},
        },
        home=home,
    )
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is False
    assert receipt["skipped"] == "workspace_mismatch"
    assert (repo / "mine.md").is_file()


def test_kill_switch(repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_SESSION_PRESERVE", "0")
    receipt = run(_event(repo), ledger_home=tmp_path / "ledgers")
    assert receipt["skipped"] == "L9_SESSION_PRESERVE=0"
    assert receipt["applied"] is False


def test_background_agent_skips(repo: Path, tmp_path: Path) -> None:
    event = _event(repo)
    event["is_background_agent"] = True
    receipt = run(event, ledger_home=tmp_path / "ledgers")
    assert receipt["skipped"] == "background agent session"


def test_deletion_only_ledger_is_preserved_against_head(repo: Path, tmp_path: Path) -> None:
    """A session that only deleted a tracked file still gets a ref: a real
    deletion against HEAD, with the worktree, the real index, and foreign
    paths untouched."""
    home = tmp_path / "ledgers"
    head = git(repo, "rev-parse", "HEAD")
    (repo / "other-chat.md").write_text("foreign\n", encoding="utf-8")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(repo)],
            "tool_name": "Delete",
            "tool_input": {"path": str(repo / "tracked.md")},
        },
        home=home,
    )
    (repo / "tracked.md").unlink()
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True, receipt
    assert receipt["paths"] == []
    assert receipt["deleted"] == ["tracked.md"]
    assert receipt["parent"] == head
    ref = receipt["ref"]
    assert git(repo, "rev-parse", f"{ref}^") == head
    assert "tracked.md" not in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()
    assert "other-chat.md" not in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()
    assert git(repo, "diff", "--name-status", f"{ref}^", ref) == "D\ttracked.md"
    # Nothing in the workspace changed: file stays deleted, real index still
    # lists it, foreign dirt is still on disk.
    assert not (repo / "tracked.md").exists()
    assert "tracked.md" in git(repo, "ls-files").splitlines()
    status = [line.strip() for line in git(repo, "status", "--porcelain").splitlines()]
    assert "D tracked.md" in status
    assert "?? other-chat.md" in status
    assert (repo / "other-chat.md").is_file()


def test_write_plus_delete_is_exactly_this_sessions_delta(repo: Path, tmp_path: Path) -> None:
    home = tmp_path / "ledgers"
    (repo / "mine.md").write_text("mine\n", encoding="utf-8")
    (repo / "other-chat.md").write_text("foreign\n", encoding="utf-8")
    for rel in ("mine.md", "tracked.md"):
        record_event(
            {
                "session_id": "sess-1",
                "workspace_roots": [str(repo)],
                "tool_input": {"path": str(repo / rel)},
            },
            home=home,
        )
    (repo / "tracked.md").unlink()
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True, receipt
    assert receipt["paths"] == ["mine.md"]
    assert receipt["deleted"] == ["tracked.md"]
    ref = receipt["ref"]
    assert git(repo, "diff", "--name-status", f"{ref}^", ref).splitlines() == [
        "A\tmine.md",
        "D\ttracked.md",
    ]
    assert git(repo, "show", f"{ref}:mine.md") == "mine"


def test_deleted_directory_ledger_path_tombstones_its_files(repo: Path, tmp_path: Path) -> None:
    """The Delete tool records the folder; the tree holds blobs, so each file
    beneath it is the deletion that gets preserved."""
    home = tmp_path / "ledgers"
    (repo / "pkg").mkdir()
    (repo / "pkg" / "a.md").write_text("a\n", encoding="utf-8")
    (repo / "pkg" / "b.md").write_text("b\n", encoding="utf-8")
    git(repo, "add", "--", "pkg/a.md", "pkg/b.md")
    git(repo, "commit", "-m", "pkg")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(repo)],
            "tool_name": "Delete",
            "tool_input": {"path": str(repo / "pkg")},
        },
        home=home,
    )
    (repo / "pkg" / "a.md").unlink()
    (repo / "pkg" / "b.md").unlink()
    (repo / "pkg").rmdir()
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True, receipt
    assert receipt["deleted"] == ["pkg/a.md", "pkg/b.md"]
    ref = receipt["ref"]
    assert git(repo, "diff", "--name-status", f"{ref}^", ref).splitlines() == [
        "D\tpkg/a.md",
        "D\tpkg/b.md",
    ]
    assert "tracked.md" in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines()


def test_absent_ledger_path_never_tracked_is_not_a_tombstone(repo: Path, tmp_path: Path) -> None:
    home = tmp_path / "ledgers"
    (repo / "scratch.md").write_text("x\n", encoding="utf-8")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(repo)],
            "tool_input": {"path": str(repo / "scratch.md")},
        },
        home=home,
    )
    (repo / "scratch.md").unlink()
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is False
    assert receipt["skipped"] == "ledger_paths_absent"
    assert receipt["deleted"] == []
    refs = git(repo, "for-each-ref", "refs/l9/preserved/session")
    assert refs == ""


def test_ledger_pathspecs_are_literal(repo: Path, tmp_path: Path) -> None:
    """`notes[1].md` in the ledger must not glob-match a foreign `notes1.md`."""
    home = tmp_path / "ledgers"
    (repo / "notes[1].md").write_text("mine\n", encoding="utf-8")
    (repo / "notes1.md").write_text("foreign\n", encoding="utf-8")
    record_event(
        {
            "session_id": "sess-1",
            "workspace_roots": [str(repo)],
            "tool_input": {"path": str(repo / "notes[1].md")},
        },
        home=home,
    )
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True, receipt
    assert receipt["paths"] == ["notes[1].md"]
    names = git(repo, "ls-tree", "-r", "--name-only", receipt["ref"]).splitlines()
    assert "notes[1].md" in names
    assert "notes1.md" not in names


def test_ignored_ledger_path_is_reported_not_fatal(repo: Path, tmp_path: Path) -> None:
    home = tmp_path / "ledgers"
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    git(repo, "add", "--", ".gitignore")
    git(repo, "commit", "-m", "ignore logs")
    (repo / "run.log").write_text("noise\n", encoding="utf-8")
    (repo / "mine.md").write_text("mine\n", encoding="utf-8")
    for rel in ("run.log", "mine.md"):
        record_event(
            {
                "session_id": "sess-1",
                "workspace_roots": [str(repo)],
                "tool_input": {"path": str(repo / rel)},
            },
            home=home,
        )
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True, receipt
    assert receipt["ignored"] == ["run.log"]
    assert receipt["paths"] == ["mine.md"]


def test_shell_write_is_preserved_and_unrelated_dirt_is_not(repo: Path, tmp_path: Path) -> None:
    """Shell-authored writes reach the ledger through the afterShellExecution
    payload; pre-existing dirt from another chat does not."""
    home = tmp_path / "ledgers"
    (repo / "other-chat.md").write_text("foreign\n", encoding="utf-8")
    _age(repo / "other-chat.md", repo / "tracked.md")
    # The shell command: a generator writes gen/out.md and rewrites tracked.md.
    (repo / "gen").mkdir()
    (repo / "gen" / "out.md").write_text("generated\n", encoding="utf-8")
    (repo / "tracked.md").write_text("rewritten\n", encoding="utf-8")
    result = record_event(
        {
            "hook_event_name": "afterShellExecution",
            "conversation_id": "sess-1",
            "workspace_roots": [str(repo)],
            "command": "python3 gen.py > gen/out.md && sed -i s/base/rewritten/ tracked.md",
            "output": "",
            "duration": 40,
        },
        home=home,
    )
    assert result["ok"] is True
    assert result["paths"] == ["gen/out.md", "tracked.md"]
    receipt = run(_event(repo), ledger_home=home)
    assert receipt["applied"] is True, receipt
    assert receipt["paths"] == ["gen/out.md", "tracked.md"]
    assert git(
        repo, "diff", "--name-status", f"{receipt['ref']}^", receipt["ref"]
    ).splitlines() == [
        "A\tgen/out.md",
        "M\ttracked.md",
    ]
    assert (repo / "other-chat.md").is_file()
    assert "other-chat.md" in git(repo, "status", "--porcelain")


def test_git_timeout_is_a_nonzero_result(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _hang(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["git"], timeout=1)

    monkeypatch.setattr(session_end_preserve.subprocess, "run", _hang)
    monkeypatch.setenv("L9_SESSION_PRESERVE_GIT_TIMEOUT", "1")
    proc = _git(repo, "status")
    assert proc.returncode == 124
    assert "timed out" in proc.stderr


def test_template_retired_hygiene_and_has_ledger_hook() -> None:
    data = json.loads((REPO / "ops" / "hooks" / "hooks.json.template").read_text(encoding="utf-8"))
    ends = [e.get("command") for e in data["hooks"]["sessionEnd"]]
    assert "./hooks/session-end-repo-hygiene.sh" not in ends
    assert "./hooks/governance-backup.sh" in ends
    posts = [e.get("command") for e in data["hooks"]["postToolUse"]]
    assert "./hooks/session-authored-paths.py" in posts
    after_shell = [e.get("command") for e in data["hooks"]["afterShellExecution"]]
    assert "./hooks/session-authored-paths.py" in after_shell


def test_backup_hook_does_not_call_github_or_gate() -> None:
    text = (REPO / "ops" / "hooks" / "session_end_governance_backup.sh").read_text(encoding="utf-8")
    assert 'PRESERVE="$GLOBAL_COMMANDS/ops/scripts/session_end_preserve.py"' in text
    assert "backup_to_github.sh" not in [
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    ]
    assert "backup_gate.sh" not in text
    assert "git add" not in [
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    ]
