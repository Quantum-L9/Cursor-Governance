"""Claude Code SessionEnd parity with Cursor's sessionEnd (session_end_close.py).

Every Claude session, published or not, parks what it authored on
``refs/l9/preserved/session/<sid>`` and closes its continuation under the
``claude-session-end`` envelope. Preserve runs against a real temporary git
repository; only the memory close is stubbed and counted.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOKS = CLAUDE_DIR / "hooks"
REPO_ROOT = CLAUDE_DIR.parents[3]
TEMPLATE = CLAUDE_DIR / "settings.template.json"


def _load() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "session_end_close", HOOKS / "session_end_close.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "kept.txt").write_text("base\n", encoding="utf-8")
    _git(root, "add", "kept.txt")
    _git(root, "commit", "--quiet", "-m", "base")
    return root.resolve()


def _record_write(repo: Path, ledger_home: Path, session: str, rel: str) -> None:
    sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts"))
    from session_authored_ledger import record_event

    (repo / rel).write_text("authored by this session\n", encoding="utf-8")
    event = {
        "session_id": session,
        "cwd": str(repo),
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(repo / rel), "content": "x"},
    }
    assert record_event(event, home=ledger_home)["paths"] == [rel]


def test_preserve_parks_only_this_sessions_paths_and_never_touches_the_tree(
    repo: Path, tmp_path: Path
) -> None:
    hook = _load()
    ledger_home = tmp_path / "ledger"
    _record_write(repo, ledger_home, "sess-1", "authored.txt")
    (repo / "foreign.txt").write_text("another chat's dirt\n", encoding="utf-8")
    status_before = _git(repo, "status", "--porcelain")
    head_before = _git(repo, "rev-parse", "HEAD")

    event = {"session_id": "sess-1", "cwd": str(repo), "reason": "prompt_input_exit"}
    receipt = hook.preserve(event, ledger_home=ledger_home)

    assert receipt["applied"] is True, receipt
    assert receipt["ref"] == "refs/l9/preserved/session/sess-1"
    parked = _git(repo, "ls-tree", "-r", "--name-only", receipt["ref"]).splitlines()
    assert "authored.txt" in parked and "foreign.txt" not in parked
    assert _git(repo, "status", "--porcelain") == status_before
    assert _git(repo, "rev-parse", "HEAD") == head_before
    assert _git(repo, "remote") == ""  # nothing to push to, and nothing pushed


def test_close_runs_every_root_under_claude_session_end_without_a_publication(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = _load()
    calls: list[dict] = []
    fake = types.ModuleType("ops.graphiti.hydration.close_session")
    fake.close_session = lambda **kw: calls.append(kw) or {"status": "closed_canonically"}
    monkeypatch.setitem(sys.modules, "ops.graphiti.hydration.close_session", fake)
    monkeypatch.setattr(hook.st, "bind_identity_env", lambda: "claude-code")
    monkeypatch.setattr(hook.mb, "ensure_importable", lambda: None)
    monkeypatch.setattr(hook, "close_roots", lambda _e, _s: [repo])

    statuses = hook.close(
        {"session_id": "sess-1", "cwd": str(repo), "reason": "clear", "transcript_path": "/t"},
        "sess-1",
    )

    assert statuses == [f"{repo.name}=closed_canonically"]
    (call,) = calls
    assert call["surface"] == "claude-session-end"
    assert call["reason"] == "session_end:clear"
    assert call["session_id"] == "sess-1" and call["agent_id"] == "claude-code"
    assert call["transcript_path"] == "/t"
    assert "publication" not in call and "handoff" not in call


def test_close_writes_nothing_without_a_derived_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    hook = _load()
    monkeypatch.setattr(hook.st, "bind_identity_env", lambda: "")
    monkeypatch.setattr(hook.st, "unresolved_identity_reason", lambda: "no host markers")
    assert hook.close({"session_id": "s"}, "s") == ["identity_unresolved (no host markers)"]


@pytest.mark.parametrize(
    "payload",
    [
        {"session_id": "s", "agent_type": "subagent", "cwd": "/x"},
        {"session_id": "s", "is_background_agent": True, "cwd": "/x"},
        {"cwd": "/x"},
    ],
)
def test_subagents_and_payloads_without_a_session_close_nothing(
    payload: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    hook = _load()
    touched: list[str] = []
    monkeypatch.setattr(hook, "preserve", lambda *_a, **_k: touched.append("preserve") or {})
    monkeypatch.setattr(hook, "close", lambda *_a, **_k: touched.append("close") or [])
    monkeypatch.setattr(hook, "_event", lambda: dict(payload))
    assert hook.main() == 0
    assert touched == []


def test_authored_paths_wrap_records_a_claude_write_into_the_session_ledger(
    repo: Path, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
    payload = {
        "session_id": "sess-wrap",
        "cwd": str(repo),
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": str(repo / "new.py"), "content": "x = 1\n"},
    }
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "session_authored_paths_wrap.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    ledger = json.loads(
        (home / ".cursor" / "l9" / "sessions" / "sess-wrap" / "authored.json").read_text("utf-8")
    )
    assert ledger["paths"] == ["new.py"]


def test_template_registers_session_end_and_authored_path_recording() -> None:
    hooks = json.loads(TEMPLATE.read_text(encoding="utf-8"))["hooks"]
    (end,) = [h for group in hooks["SessionEnd"] for h in group["hooks"]]
    assert "--class observer session_end_close.py" in end["command"]
    # Claude Code caps the SessionEnd budget at 60 s; the default is 1.5 s.
    assert end["timeout"] == 60
    recorders = [
        group
        for group in hooks["PostToolUse"]
        for h in group["hooks"]
        if "session_authored_paths_wrap.py" in h["command"]
    ]
    assert len(recorders) == 1
    assert set(recorders[0]["matcher"].split("|")) >= {"Write", "Edit", "MultiEdit"}
