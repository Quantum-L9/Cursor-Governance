"""A registered /lcto swarm child never merges, whatever the merge-authority switch says.

The role narrows authority (L9-MONOTONIC-001): it is checked before the ``disabled``
short-circuit, which otherwise allows every merge outside the never-waive set.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import merge_gate  # noqa: E402
import session_role  # noqa: E402

CHILD = "local-child-merge"
MERGES = [
    ("Bash", {"command": "gh pr merge 12 --merge"}),
    ("Bash", {"command": "gh api -X PUT repos/o/r/pulls/12/merge -f merge_method=merge"}),
    ("Bash", {"command": "python3 ops/autonomy/stack_safe_merge.py --repo o/r --pr 1 --run"}),
    ("mcp__github__merge_pull_request", {"owner": "o", "repo": "r", "pullNumber": 12}),
    ("mcp__github__enable_pr_auto_merge", {"owner": "o", "repo": "r", "pullNumber": 12}),
]


@pytest.fixture
def child(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("L9_SESSION_ROLE_DIR", str(tmp_path / "roles"))
    session_role.register_child("session_cto", session_id=CHILD)
    return CHILD


@pytest.mark.parametrize("mode", ["disabled", "strict"])
@pytest.mark.parametrize(("tool", "tool_input"), MERGES)
def test_a_swarm_child_is_denied_every_merge_transport(
    child: str, monkeypatch: pytest.MonkeyPatch, mode: str, tool: str, tool_input: dict
) -> None:
    monkeypatch.setenv("L9_MERGE_AUTHORITY_MODE", mode)
    reason = merge_gate.evaluate(tool, tool_input, event={"session_id": child})
    assert reason == merge_gate.SWARM_CHILD_MERGE_REASON


def test_a_non_child_session_is_unaffected_while_disabled(
    child: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_MERGE_AUTHORITY_MODE", "disabled")
    reason = merge_gate.evaluate(
        "Bash", {"command": "gh pr merge 12 --merge"}, event={"session_id": "the-cto"}
    )
    assert reason is None


def test_a_child_may_still_run_non_merge_commands(child: str) -> None:
    for command in ("git status", "gh api repos/o/r/pulls/12", "make pr"):
        assert (
            merge_gate.evaluate("Bash", {"command": command}, event={"session_id": child}) is None
        )


def test_a_swarm_child_cannot_reach_across_sessions(child: str) -> None:
    import swarm_role_gate  # noqa: PLC0415

    event = {"session_id": child}
    for tool in ("send_message", "create_session", "send_later", "create_trigger"):
        name = f"mcp__claude-code-remote__{tool}"
        assert swarm_role_gate.evaluate(name, event) == swarm_role_gate.REASON, tool
    for tool in ("get_session", "list_events", "list_sessions"):
        assert swarm_role_gate.evaluate(f"mcp__claude-code-remote__{tool}", event) is None
    assert swarm_role_gate.evaluate("mcp__claude-code-remote__send_message", {}) is None
    assert (
        swarm_role_gate.evaluate("mcp__claude-code-remote__send_message", {"session_id": "the-cto"})
        is None
    )
