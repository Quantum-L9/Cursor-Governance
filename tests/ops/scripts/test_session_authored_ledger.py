"""Session authored ledger — never porcelain, never a foreign workspace."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from session_authored_ledger import load_ledger, record_event  # noqa: E402


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
