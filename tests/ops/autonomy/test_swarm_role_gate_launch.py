"""Launch side of the swarm role gate (ops/autonomy/swarm_role_gate.py).

A child registers itself, so a child launched with a hand-written brief was never
gated. The gate now denies any create_session whose append_system_prompt lacks the
CTO child prompt's REPORTING rule, so every launched coding agent carries "never
message any session; report only in your own transcript" from its first turn.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import session_role  # noqa: E402
import swarm_role_gate  # noqa: E402

CREATE = "mcp__claude-code-remote__create_session"
SEND = "mcp__claude-code-remote__send_message"


@pytest.fixture
def cto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_SESSION_ROLE_DIR", str(tmp_path / "roles"))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "cto-1")
    monkeypatch.delenv("CURSOR_SESSION_ID", raising=False)
    monkeypatch.delenv("L9_UNBRIEFED_LAUNCH_AUTHORIZED", raising=False)


def _launch(prompt: str | None) -> dict:
    tool_input = {"prompt": "do lane A"}
    if prompt is not None:
        tool_input["append_system_prompt"] = prompt
    return {"session_id": "cto-1", "tool_input": tool_input}


def test_the_sentinel_matches_the_mode_contract() -> None:
    mode = (ROOT / "governance" / "cto-mode" / "MODE.yaml").read_text(encoding="utf-8")
    assert swarm_role_gate.CHILD_REPORTING_SENTINEL in mode


def test_a_hand_written_brief_is_denied(cto: None) -> None:
    assert swarm_role_gate.evaluate(CREATE, _launch(None)) == swarm_role_gate.LAUNCH_REASON
    assert (
        swarm_role_gate.evaluate(CREATE, _launch("Report via send_message."))
        == swarm_role_gate.LAUNCH_REASON
    )


def test_a_launch_carrying_the_child_prompt_is_allowed(cto: None) -> None:
    prompt = (
        "ROLE ...\n"
        + swarm_role_gate.CHILD_REPORTING_SENTINEL
        + ": never call a cross-session tool."
    )
    assert swarm_role_gate.evaluate(CREATE, _launch(prompt)) is None


def test_a_bare_flag_is_not_a_breakglass(cto: None, monkeypatch: pytest.MonkeyPatch) -> None:
    for flag in ("1", "true", "yes", " "):
        monkeypatch.setenv("L9_UNBRIEFED_LAUNCH_AUTHORIZED", flag)
        assert swarm_role_gate.evaluate(CREATE, _launch(None)) == swarm_role_gate.LAUNCH_REASON


def test_a_human_reason_authorizes_one_unbriefed_launch(
    cto: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_UNBRIEFED_LAUNCH_AUTHORIZED", "operator: ad-hoc research session")
    assert swarm_role_gate.evaluate(CREATE, _launch(None)) is None


def test_a_cto_may_still_message_its_children(cto: None) -> None:
    assert swarm_role_gate.evaluate(SEND, {"session_id": "cto-1", "tool_input": {}}) is None


def test_a_registered_child_is_denied_every_cross_session_tool(cto: None) -> None:
    session_role.register_child("session_cto_0")
    prompt = swarm_role_gate.CHILD_REPORTING_SENTINEL
    assert swarm_role_gate.evaluate(SEND, {"session_id": "cto-1"}) == swarm_role_gate.REASON
    assert swarm_role_gate.evaluate(CREATE, _launch(prompt)) == swarm_role_gate.REASON
