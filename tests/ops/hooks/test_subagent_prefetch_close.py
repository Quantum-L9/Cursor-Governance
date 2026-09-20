"""Host subagent lifecycle must prefetch then close via existing Graphiti hooks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
START = ROOT / "ops" / "hooks" / "lifecycle-subagent-start.sh"
STOP = ROOT / "ops" / "hooks" / "lifecycle-subagent-stop.sh"
TEMPLATE = ROOT / "ops" / "hooks" / "hooks.json.template"
SETUP = ROOT / "ops" / "scripts" / "setup_workspace_symlinks.sh"


def test_subagent_start_runs_prefetch_after_parent_gate() -> None:
    text = START.read_text(encoding="utf-8")
    assert "graphiti_gate_runner.sh" in text
    assert "graphiti-prefetch.sh" in text
    assert text.index("graphiti_gate_runner.sh") < text.index("graphiti-prefetch.sh")


def test_subagent_stop_runs_session_end_after_compose_stop() -> None:
    text = STOP.read_text(encoding="utf-8")
    assert "compose_stop" in text
    assert "graphiti-session-end.sh" in text
    assert text.index("compose_stop") < text.index("graphiti-session-end.sh")
    assert "printf '%s\\n' \"$REPORT\"" in text


def test_stop_timeout_covers_session_end_budget() -> None:
    data = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    stop = data["hooks"]["subagentStop"][0]
    assert stop["command"] == "./hooks/lifecycle-subagent-stop.sh"
    assert stop["timeout"] == 45
    start = data["hooks"]["subagentStart"][0]
    assert start["timeout"] == 30
    setup = SETUP.read_text(encoding="utf-8")
    assert '"timeout": 45' in setup
    assert '"timeout": 30' in setup
