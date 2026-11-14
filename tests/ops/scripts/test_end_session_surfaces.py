"""No end-session surface instructs a push, a broad add, or a retired memory path.

The /end-session command, its skill, the skill's reference and the
end-session.yaml protocol each carry executable steps. Those steps once ran
``git add -A`` + ``git push`` on the governance clone (forbidden by
CANONICAL_LAW §5.1 and rules/49), wrote PICKUP records that never stamp a close
receipt, set a Redis session context, and hard-coded ``--agent-id cursor``
(refused as identity drift on Claude Code). Prose that *names* those as retired
is allowed; an executable step is not.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MARKDOWN = (
    "commands/end-session.md",
    "skills/l9-end-session/SKILL.md",
    "skills/l9-end-session/references/end-session-protocol.md",
)
FORBIDDEN = {
    "broad add": re.compile(r"\bgit\s+add\s+(-A|--all|\.)(\s|$)"),
    "push": re.compile(r"\bgit\s+push\b"),
    "backup push script": re.compile(r"backup_to_github\.sh"),
    "configured identity": re.compile(r"--agent-id\s+\S|L9_MEMORY_AGENT_ID=\S"),
    "PICKUP write": re.compile(r"pickup_context|PICKUP\|"),
    "Redis context": re.compile(r"cache_set_session_context"),
    "memory-bank write": re.compile(r"memory-bank/"),
}
_FENCE = re.compile(r"```(?:bash|sh|shell)\n(.*?)```", re.DOTALL)


def _yaml_commands(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "command" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_yaml_commands(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_yaml_commands(item))
    return found


def _executable_steps() -> list[tuple[str, str]]:
    steps: list[tuple[str, str]] = []
    for rel in MARKDOWN:
        text = (ROOT / rel).read_text(encoding="utf-8")
        steps.extend((rel, block) for block in _FENCE.findall(text))
    for doc in yaml.safe_load_all((ROOT / "end-session.yaml").read_text(encoding="utf-8")):
        steps.extend(("end-session.yaml", command) for command in _yaml_commands(doc))
    return steps


def test_the_step_bearing_surfaces_still_carry_their_steps() -> None:
    """The skill is the contract and carries no shell; the command, the reference
    and the protocol carry the steps this test inspects."""
    sources = {rel for rel, _ in _executable_steps()}
    assert sources >= {
        "commands/end-session.md",
        "skills/l9-end-session/references/end-session-protocol.md",
        "end-session.yaml",
    }, "a step-bearing surface lost its steps, so the checks below would be vacuous"


@pytest.mark.parametrize("label", sorted(FORBIDDEN))
def test_no_executable_step_does_a_retired_or_forbidden_thing(label: str) -> None:
    pattern = FORBIDDEN[label]
    offenders = [rel for rel, step in _executable_steps() if pattern.search(step)]
    assert offenders == [], f"{label} in an executable end-session step: {offenders}"


def test_the_repair_is_repair_write() -> None:
    for rel, step in _executable_steps():
        if "ops.memory.cli write" in step:
            pytest.fail(f"{rel}: ops.memory.cli write stamps no close receipt; use repair-write")
    assert any("repair-write" in step for _rel, step in _executable_steps())
