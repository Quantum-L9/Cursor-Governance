"""A failed session close is visible at the next SessionStart, on both hosts.

SessionStart became memory health-only (CANONICAL_LAW §8.9) and with it the only
CLOSE_GAP line disappeared: a sessionEnd close that never landed was reported by
nothing, and /end-session's documented trigger could not occur. The signal is
restored from local close receipts only — no memory call — on Cursor
(``session_start_memory_orchestrator.sh``) and Claude Code (``memory_prefetch.py``).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ORCH = ROOT / "ops" / "hooks" / "session_start_memory_orchestrator.sh"
PREFETCH = (
    ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "memory_prefetch.py"
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ops.graphiti.hydration import session_latches as latches  # noqa: E402
from ops.scripts.classify_hydrate_state import classify_verdict  # noqa: E402


def _closed(project: Path, session_id: str) -> None:
    latches.write_receipt(
        project,
        session_id,
        {
            "status": "closed_canonically",
            "canonical_operation_id": "op-1",
            "write_count": 3,
            "head_hash": "h",
        },
    )


def _orchestrate(project: Path, session_id: str, home: Path) -> str:
    env = {
        **os.environ,
        "HOME": str(home),
        "CURSOR_PROJECT_DIR": str(project),
        "CURSOR_SESSION_ID": session_id,
        "CURSOR_CONVERSATION_ID": session_id,
        "GRAPHITI_MEMORY_ENABLED": "0",
        "L9_MEMORY_GRAPHITI_ENABLED": "0",
    }
    proc = subprocess.run(
        ["bash", str(ORCH)], input="", capture_output=True, text=True, env=env, timeout=120
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hydrate_markdown"]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


def test_cursor_session_start_reports_an_unclosed_prior_session(
    project: Path, tmp_path: Path
) -> None:
    latches.write_open_latch(project, "prior-session")
    markdown = _orchestrate(project, "current-session", tmp_path / "home")
    assert "CLOSE_GAP prior session prior-session has no close receipt" in markdown
    assert "REPAIR: /end-session" in markdown
    verdict = classify_verdict(markdown)
    assert verdict.condition == "CLOSE_GAP"
    assert verdict.degraded is False


def test_cursor_session_start_is_silent_after_a_successful_close(
    project: Path, tmp_path: Path
) -> None:
    latches.write_open_latch(project, "prior-session")
    _closed(project, "prior-session")
    markdown = _orchestrate(project, "current-session", tmp_path / "home")
    assert "CLOSE_GAP" not in markdown


def _prefetch():
    hooks = PREFETCH.parent
    mem = hooks.parent / "memory"
    for path in (str(mem), str(hooks)):
        if path not in sys.path:
            sys.path.insert(0, path)
    spec = importlib.util.spec_from_file_location("memory_prefetch_under_test", PREFETCH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_claude_session_start_opens_the_session_and_names_the_gap(project: Path) -> None:
    prefetch = _prefetch()
    assert prefetch._close_gaps([project], "claude-first") == []
    gaps = prefetch._close_gaps([project], "claude-second")
    assert gaps == ["repo: prior session claude-first has no close receipt"]
    _closed(project, "claude-second")
    assert prefetch._close_gaps([project], "claude-third") == []
