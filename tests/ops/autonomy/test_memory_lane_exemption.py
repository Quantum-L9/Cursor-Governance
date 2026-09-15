"""Memory invocations are never blocked by a repository-write precondition.

ADR-0033 B8 / INV-03b: agents are first-class memory writers on the agent
lane. ``l9-memory …``, ``python -m ops.memory.cli …`` and the
``memory_prefetch.py`` repair are memory actions, not repository writes, so
the Claude hydration gate exempts them exactly the way it exempts ``git``.

Scope is the executable: a compound that also does something else is not
exempt, heredoc bodies are data, and a parse fault degrades to a narrow plain
match rather than to a denial.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
AUTONOMY = REPO / "ops" / "autonomy"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))

import memory_lane_exemption as exemption  # noqa: E402

EXEMPT = [
    "l9-memory health",
    'l9-memory write "gate writeback contract requires X" --kind insight',
    "l9-memory search 'writeback' --limit 5",
    "l9-memory hydrate --task 'continue'",
    "/Users/x/.cursor-governance/.venv/bin/l9-memory health",
    "python -m ops.memory.cli health",
    "python3 -m ops.memory.cli --surface plan-prefetch hydrate --task t",
    ".venv/bin/python -m ops.memory.cli write 'fact' --kind lesson",
    "L9_MEMORY_AGENT_ID=cursor .venv/bin/python -m ops.memory.cli conflicts --task t",
    "environment/agents/adapters/claude-code/hooks/memory_prefetch.py --session-id abc",
    "L9_MEMORY_AGENT_ID=unknown-agent "
    "environment/agents/adapters/claude-code/hooks/memory_prefetch.py --session-id abc",
    ".venv/bin/python environment/agents/adapters/claude-code/hooks/memory_prefetch.py "
    "--session-id abc",
    "cd /some/repo && l9-memory health",
    "l9-memory health; l9-memory search q",
    'bash -c "l9-memory health"',
    "  l9-memory health  ",
]

NOT_EXEMPT = [
    "",
    "   ",
    "git push",
    "make pr",
    "python -m ops.other.cli health",
    "python -m ops.memory.cli_extra health",
    "python memory_prefetch_helper.py",
    "l9-memory-fake health",
    "l9-memory health && git commit -m x",
    "l9-memory health && printf x > skills/x/SKILL.md",
    "l9-memory health || rm -f skills/x/SKILL.md",
    "python -m ops.memory.cli write x | tee out.txt",
    "cat <<EOF\nl9-memory write\nEOF",
    "echo l9-memory health",
    "bash -c 'l9-memory health && touch skills/x'",
    "l9-memory health > skills/x",
    'l9-memory health "$(printf x > skills/x)"',
]


@pytest.mark.parametrize("command", EXEMPT)
def test_memory_invocations_are_exempt(command: str) -> None:
    assert exemption.command_is_memory_lane(command) is True


@pytest.mark.parametrize("command", NOT_EXEMPT)
def test_everything_else_still_goes_through_governance(command: str) -> None:
    assert exemption.command_is_memory_lane(command) is False


def test_event_is_scoped_to_shell_tools() -> None:
    inp = {"command": "l9-memory health"}
    assert exemption.event_is_memory_lane("Bash", inp) is True
    assert exemption.event_is_memory_lane("Shell", {"cmd": "l9-memory health"}) is True
    assert exemption.event_is_memory_lane("Edit", inp) is False
    assert exemption.event_is_memory_lane("mcp__l9-graphite-memory__write_agent", inp) is False
    assert exemption.event_is_memory_lane("Bash", None) is False
    assert exemption.event_is_memory_lane("Bash", {"file_path": "x"}) is False


def test_parse_fault_degrades_to_a_narrow_plain_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fault in the structural parser must never turn into a denial."""

    def boom(command: str) -> list[str]:
        raise RuntimeError("tokenizer fault")

    monkeypatch.setattr(exemption, "split_segments", boom)
    assert exemption.command_is_memory_lane("l9-memory health") is True
    assert exemption.command_is_memory_lane("l9-memory health && git commit -m x") is False
    assert exemption.command_is_memory_lane("git push") is False


def test_the_gate_exempts_before_it_classifies() -> None:
    """The Claude hydration gate consults the exemption ahead of its contract.

    Position matters: the exemption sits before contract load and before the
    fail-closed handler, so neither an unreadable contract nor a classify
    fault can deny a memory invocation.
    """
    gate = REPO / "environment/agents/adapters/claude-code/hooks/memory_gate.py"
    text = gate.read_text(encoding="utf-8")
    assert "event_is_memory_lane" in text
    git_at = text.index("if event_is_git_or_gh(tool_name, tool_input):")
    mem_at = text.index("if event_is_memory_lane(tool_name, tool_input):")
    contract_at = text.index("contract = st.load_contract()")
    assert git_at < mem_at < contract_at
