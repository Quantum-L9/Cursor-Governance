"""Session authored ledger — never porcelain, never a foreign workspace."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from session_authored_ledger import (  # noqa: E402
    is_shell_event,
    load_ledger,
    record_event,
    shell_written_rels,
)

HOOK = REPO / "ops" / "hooks" / "session_authored_paths.py"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def _git_repo(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "sub").mkdir()
    (root / "tracked.md").write_text("base\n", encoding="utf-8")
    (root / "sub" / "old.md").write_text("old\n", encoding="utf-8")
    _git(root, "add", "--", "tracked.md", "sub/old.md")
    _git(root, "commit", "-q", "-m", "base")


def _age(*paths: Path) -> None:
    stamp = time.time() - 100.0
    for path in paths:
        os.utime(path, (stamp, stamp))


def _shell_event(ws: Path, command: str, duration_ms: int = 40) -> dict:
    return {
        "hook_event_name": "afterShellExecution",
        "conversation_id": "conv-shell",
        "workspace_roots": [str(ws)],
        "command": command,
        "output": "",
        "duration": duration_ms,
    }


def test_records_in_workspace_path(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "mine.md").write_text("a", encoding="utf-8")
    home = tmp_path / "ledgers"
    result = record_event(
        {
            "session_id": "conv-1",
            "workspace_roots": [str(ws)],
            "tool_input": {"path": str(ws / "mine.md")},
        },
        home=home,
    )
    assert result["ok"] is True
    assert result["paths"] == ["mine.md"]
    ledger = load_ledger("conv-1", home=home)
    assert ledger["paths"] == ["mine.md"]
    assert Path(ledger["workspace"]) == ws.resolve()


def test_ignores_foreign_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    other = tmp_path / "other"
    ws.mkdir()
    other.mkdir()
    (other / "theirs.md").write_text("b", encoding="utf-8")
    home = tmp_path / "ledgers"
    record_event(
        {
            "session_id": "conv-1",
            "workspace_roots": [str(ws)],
            "tool_input": {"path": str(ws / "mine.md")},
        },
        home=home,
    )
    # First event had no file; bind workspace with a real in-tree path.
    (ws / "mine.md").write_text("a", encoding="utf-8")
    record_event(
        {
            "session_id": "conv-1",
            "workspace_roots": [str(ws)],
            "tool_input": {"path": str(ws / "mine.md")},
        },
        home=home,
    )
    denied = record_event(
        {
            "session_id": "conv-1",
            "workspace_roots": [str(other)],
            "tool_input": {"path": str(other / "theirs.md")},
        },
        home=home,
    )
    assert denied["ok"] is False
    assert denied["reason"] == "workspace_mismatch"
    assert load_ledger("conv-1", home=home)["paths"] == ["mine.md"]


def test_does_not_record_path_outside_workspace(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    home = tmp_path / "ledgers"
    result = record_event(
        {
            "session_id": "conv-2",
            "workspace_roots": [str(ws)],
            "tool_input": {"path": "/etc/passwd"},
        },
        home=home,
    )
    assert result["ok"] is True
    assert result["paths"] == []
    assert load_ledger("conv-2", home=home)["paths"] == []


def test_shell_event_shape_is_recognised() -> None:
    assert is_shell_event({"hook_event_name": "afterShellExecution"})
    assert is_shell_event({"command": "make x", "duration": 12})
    assert not is_shell_event({"hook_event_name": "beforeShellExecution", "command": "make x"})
    assert not is_shell_event({"tool_input": {"path": "a.md"}})


def test_shell_event_attributes_window_writes_and_deletions_not_foreign_dirt(
    tmp_path: Path,
) -> None:
    ws = tmp_path / "ws"
    _git_repo(ws)
    (ws / "foreign.md").write_text("another chat\n", encoding="utf-8")
    (ws / "sub" / "foreign-tracked.md").write_text("x\n", encoding="utf-8")
    _git(ws, "add", "--", "sub/foreign-tracked.md")
    _git(ws, "commit", "-q", "-m", "more")
    _age(
        ws / "foreign.md",
        ws / "tracked.md",
        ws / "sub" / "old.md",
        ws / "sub" / "foreign-tracked.md",
    )
    _age(ws / "sub", ws)
    # The shell command of this conversation: writes, rewrites, deletes.
    (ws / "new.md").write_text("new\n", encoding="utf-8")
    (ws / "tracked.md").write_text("rewritten\n", encoding="utf-8")
    (ws / "sub" / "old.md").unlink()
    home = tmp_path / "ledgers"
    result = record_event(_shell_event(ws, "make generate && rm sub/old.md"), home=home)
    assert result["ok"] is True
    assert result["paths"] == ["new.md", "sub/old.md", "tracked.md"]
    assert "foreign.md" not in load_ledger("conv-shell", home=home)["paths"]
    assert "sub/foreign-tracked.md" not in load_ledger("conv-shell", home=home)["paths"]


def test_shell_event_ignores_dirt_older_than_the_window(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    _git_repo(ws)
    (ws / "stale.md").write_text("stale\n", encoding="utf-8")
    _age(ws / "stale.md", ws / "tracked.md", ws / "sub" / "old.md", ws / "sub", ws)
    assert shell_written_rels(_shell_event(ws, "echo hi"), ws) == []
    result = record_event(_shell_event(ws, "echo hi"), home=tmp_path / "ledgers")
    assert result["ok"] is True
    assert result["paths"] == []


def test_shell_event_in_non_git_workspace_records_nothing(tmp_path: Path) -> None:
    ws = tmp_path / "plain"
    ws.mkdir()
    (ws / "a.md").write_text("a\n", encoding="utf-8")
    result = record_event(_shell_event(ws, "touch a.md"), home=tmp_path / "ledgers")
    assert result["ok"] is True
    assert result["paths"] == []


def test_hook_records_shell_payload_and_continues(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    _git_repo(ws)
    _age(ws / "tracked.md", ws / "sub" / "old.md", ws / "sub", ws)
    (ws / "gen.md").write_text("gen\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    env = dict(os.environ, HOME=str(home))
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(_shell_event(ws, "python3 gen.py")),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == {"continue": True}
    ledger = home / ".cursor" / "l9" / "sessions" / "conv-shell" / "authored.json"
    assert json.loads(ledger.read_text(encoding="utf-8"))["paths"] == ["gen.md"]


def test_hook_fails_open_with_diagnostic_when_ledger_home_unwritable(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.md").write_text("a\n", encoding="utf-8")
    not_a_dir = tmp_path / "home-is-a-file"
    not_a_dir.write_text("", encoding="utf-8")
    env = dict(os.environ, HOME=str(not_a_dir))
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(
            {
                "session_id": "conv-x",
                "workspace_roots": [str(ws)],
                "tool_input": {"path": str(ws / "a.md")},
            }
        ),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == {"continue": True}
    assert "ledger not updated" in proc.stderr


def test_ledger_file_is_session_scoped(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "a.md").write_text("a", encoding="utf-8")
    home = tmp_path / "ledgers"
    record_event(
        {
            "session_id": "aaa",
            "workspace_roots": [str(ws)],
            "tool_input": {"file_path": "a.md"},
        },
        home=home,
    )
    assert (home / "aaa" / "authored.json").is_file()
    assert not (home / "bbb" / "authored.json").exists()
    data = json.loads((home / "aaa" / "authored.json").read_text(encoding="utf-8"))
    assert data["session_id"] == "aaa"
