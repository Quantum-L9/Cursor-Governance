"""Host subagent lifecycle must prefetch then close via existing Graphiti hooks."""

from __future__ import annotations

import json
import sys
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


def test_start_and_stop_derive_the_same_child_conversation_id() -> None:
    """The close has to find the receipt the prefetch wrote.

    Native ``subagentStart`` carries ``subagent_id`` / ``tool_call_id`` /
    ``parent_conversation_id``; native ``subagentStop`` carries only
    ``subagent_id``. Both hooks must therefore agree on ``subagent_id``, and
    neither may fall back to the parent.
    """
    sys.path.insert(0, str(ROOT / "ops" / "hooks"))
    import child_conversation  # noqa: PLC0415

    start_payload = {
        "subagent_id": "sub-9",
        "tool_call_id": "call-1",
        "parent_conversation_id": "parent-abc",
        "workspace_roots": ["/tmp/ws"],
    }
    stop_payload = {"subagent_id": "sub-9", "status": "completed", "output": "…"}

    start_id = child_conversation.child_conversation_id(start_payload)
    assert start_id == "sub-9"
    assert start_id == child_conversation.child_conversation_id(stop_payload)
    assert "parent-abc" not in start_id
    assert child_conversation.project_dir(start_payload) == "/tmp/ws"
    assert child_conversation.child_conversation_id({}) == ""


def test_both_hooks_stamp_the_child_conversation_and_use_the_selected_python() -> None:
    start = START.read_text(encoding="utf-8")
    stop = STOP.read_text(encoding="utf-8")
    for text in (start, stop):
        assert "child_conversation.py" in text
        assert 'export CURSOR_CONVERSATION_ID="$CHILD_CONV"' in text
    # $PY is selected on line 8/9 of each hook; every later parse uses it.
    for text in (start, stop):
        after_py = text.split('PY="$(command -v python3)"', 1)[1]
        assert "python3 -" not in after_py
        assert "python3 -c" not in after_py
    assert stop.index("child_conversation.py") < stop.index("graphiti-session-end.sh")


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
