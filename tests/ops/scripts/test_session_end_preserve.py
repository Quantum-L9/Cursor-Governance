"""SessionEnd preserve — this conversation only. Never porcelain. Never delete."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from session_authored_ledger import record_event  # noqa: E402
from session_end_preserve import run  # noqa: E402


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


def test_template_retired_hygiene_and_has_ledger_hook() -> None:
    data = json.loads((REPO / "ops" / "hooks" / "hooks.json.template").read_text(encoding="utf-8"))
    ends = [e.get("command") for e in data["hooks"]["sessionEnd"]]
    assert "./hooks/session-end-repo-hygiene.sh" not in ends
    assert "./hooks/governance-backup.sh" in ends
    posts = [e.get("command") for e in data["hooks"]["postToolUse"]]
    assert "./hooks/session-authored-paths.py" in posts


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
