"""INV-03b, agent lane: nothing in Cursor-Governance interposes on an agent's
memory write, search or hydrate (ADR-0033 B8).

An agent's ordinary write is one call to the memory package's public surface
(``mcp__l9-graphite-memory__write_agent`` or ``l9-memory write``) and is
immediately visible to another agent's ``hydrate`` / ``search``. Every
pre-execution hook, matcher, deny list and effect gate in this repository is
inspected here so that none of them can name a memory tool for denial or make
a memory invocation wait on a phase, a receipt, a session close or a PR gate.

Post-execution observers (``graphiti-mark-ok.sh``) may match memory tools:
they cannot deny.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
AUTONOMY = REPO / "ops" / "autonomy"
CLAUDE = REPO / "environment" / "agents" / "adapters" / "claude-code"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))

import local_execution_gate  # noqa: E402
import memory_lane_exemption  # noqa: E402
import merge_gate  # noqa: E402

#: The public agent-lane surface. If the memory package grows a tool it is
#: still under this prefix, so the prefix is what matchers must never name.
MEMORY_MCP_PREFIX = "mcp__l9-graphite-memory__"
MEMORY_MCP_TOOLS = [
    f"{MEMORY_MCP_PREFIX}{name}"
    for name in (
        "write_agent",
        "write_governed",
        "search",
        "hydrate",
        "get",
        "conflicts",
        "phase_lock",
        "ingest",
        "close",
        "health",
    )
]

#: Shell forms of the same lane.
MEMORY_SHELL_COMMANDS = [
    'l9-memory write "gate writeback contract requires X" --kind insight',
    "l9-memory search 'writeback'",
    "l9-memory hydrate --task continue",
    ".venv/bin/python -m ops.memory.cli write 'fact' --kind lesson",
    ".venv/bin/python -m ops.memory.cli search q",
]


def _claude_pretooluse_matchers() -> list[str]:
    settings = json.loads((CLAUDE / "settings.template.json").read_text(encoding="utf-8"))
    return [
        str(entry.get("matcher", ""))
        for entry in settings.get("hooks", {}).get("PreToolUse", [])
        if entry.get("matcher")
    ]


def _cursor_pre_hooks() -> list[dict]:
    template = json.loads((REPO / "ops/hooks/hooks.json.template").read_text(encoding="utf-8"))
    hooks = template.get("hooks", template)
    out: list[dict] = []
    for phase, entries in hooks.items():
        if not str(phase).lower().startswith("before"):
            continue
        for entry in entries or []:
            out.append({"phase": phase, **entry})
    return out


@pytest.mark.parametrize("tool", MEMORY_MCP_TOOLS)
def test_no_claude_pretooluse_matcher_covers_a_memory_mcp_tool(tool: str) -> None:
    """A gate that never runs cannot deny. The template is the projection source."""
    for matcher in _claude_pretooluse_matchers():
        assert not re.fullmatch(matcher, tool), (
            f"Claude PreToolUse matcher {matcher!r} covers {tool}; "
            "the agent lane is never a hook subject (ADR-0033 B8)"
        )


def test_no_cursor_before_hook_names_a_memory_tool() -> None:
    for entry in _cursor_pre_hooks():
        matcher = str(entry.get("matcher", ""))
        command = str(entry.get("command", ""))
        for needle in ("l9-graphite-memory", "memory.", "l9-memory", "ops.memory"):
            assert needle not in matcher, (
                f"Cursor {entry['phase']} matcher {matcher!r} names the memory lane"
            )
        assert "memory" not in Path(command).name.lower() or "prefetch" in command, (
            f"Cursor {entry['phase']} hook {command!r} looks like a memory interposition"
        )


def test_the_cursor_mcp_gate_only_knows_code_graph_tools() -> None:
    sys.path.insert(0, str(REPO / "skills/l9-code-graph-rag-mcp/scripts"))
    import code_graph_plasticos_gate as cg  # noqa: PLC0415

    for name in cg.MCP_DENY_TOOLS | cg.MCP_ASK_TOOLS:
        assert not name.startswith(("memory", "write", "hydrate", "search_memory", "l9-memory")), (
            f"{name} in the code-graph MCP gate would interpose on the agent lane"
        )


def test_the_memory_enforcement_contract_names_no_memory_tool_or_command() -> None:
    contract = json.loads(
        (CLAUDE / "memory" / "memory-enforcement.contract.json").read_text(encoding="utf-8")
    )
    for rule in contract.get("rules", []):
        match = rule.get("match", {})
        for tool in match.get("tools", []):
            assert not str(tool).startswith(MEMORY_MCP_PREFIX), (
                f"rule {rule['id']} governs {tool}: a hydration gate on a memory tool"
            )
        for pattern in match.get("command_patterns", []):
            for command in MEMORY_SHELL_COMMANDS:
                assert not re.search(pattern, command), (
                    f"rule {rule['id']} pattern {pattern!r} matches {command!r}"
                )


@pytest.mark.parametrize("command", MEMORY_SHELL_COMMANDS)
def test_effect_gates_do_not_deny_memory_shell_invocations(command: str, tmp_path: Path) -> None:
    assert local_execution_gate.evaluate("Bash", {"command": command}, root=tmp_path) is None
    assert merge_gate.evaluate("Bash", {"command": command}) is None
    assert memory_lane_exemption.command_is_memory_lane(command) is True


@pytest.mark.parametrize("tool", MEMORY_MCP_TOOLS)
def test_effect_gates_do_not_deny_memory_mcp_tools(tool: str, tmp_path: Path) -> None:
    assert local_execution_gate.evaluate(tool, {}, root=tmp_path) is None
    assert merge_gate.evaluate(tool, {}) is None


def test_the_hydration_gate_exempts_the_memory_lane_before_its_contract() -> None:
    text = (CLAUDE / "hooks" / "memory_gate.py").read_text(encoding="utf-8")
    exempt_at = text.index("if event_is_memory_lane(tool_name, tool_input):")
    contract_at = text.index("contract = st.load_contract()")
    assert exempt_at < contract_at


# --------------------------------------------------------------------------- #
# The residue validator's agent-lane-interposition class (make pr / pre-commit)
# --------------------------------------------------------------------------- #

VALIDATOR = REPO / "ops" / "scripts" / "validate_legacy_doctrine_residue.py"


def _load_validator():
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("residue", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_validator(root: Path) -> tuple[int, str]:
    import subprocess  # noqa: PLC0415

    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_the_validator_finds_no_interposition_in_the_real_tree() -> None:
    residue = _load_validator()
    failures, _warnings = residue.agent_lane_findings(REPO)
    assert failures == []
    assert residue.hook_matcher_findings(REPO) == []


def test_a_claude_matcher_that_covers_a_memory_tool_fails(tmp_path: Path) -> None:
    settings = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Bash|mcp__l9-graphite-memory__.*", "hooks": []},
            ]
        }
    }
    _write(
        tmp_path,
        "environment/agents/adapters/claude-code/settings.template.json",
        json.dumps(settings),
    )
    rc, out = _run_validator(tmp_path)
    assert rc == 1, out
    assert "covers mcp__l9-graphite-memory__write_agent [agent-lane-interposition]" in out


def test_a_cursor_before_hook_that_names_the_memory_lane_fails(tmp_path: Path) -> None:
    template = {
        "hooks": {
            "beforeMCPExecution": [
                {"command": "./hooks/x.sh", "matcher": "l9-graphite-memory", "timeout": 5}
            ]
        }
    }
    _write(tmp_path, "ops/hooks/hooks.json.template", json.dumps(template))
    rc, out = _run_validator(tmp_path)
    assert rc == 1, out
    assert "beforeMCPExecution matcher 'l9-graphite-memory' names the memory lane" in out


def test_a_contract_rule_on_a_memory_tool_or_command_fails(tmp_path: Path) -> None:
    contract = {
        "rules": [
            {"id": "mem-tool", "match": {"tools": ["mcp__l9-graphite-memory__write_agent"]}},
            {
                "id": "mem-shell",
                "match": {"tools": ["Bash"], "command_patterns": [r"\bl9-memory\s+write\b"]},
            },
        ]
    }
    _write(
        tmp_path,
        "environment/agents/adapters/claude-code/memory/memory-enforcement.contract.json",
        json.dumps(contract),
    )
    rc, out = _run_validator(tmp_path)
    assert rc == 1, out
    assert "rule mem-tool governs mcp__l9-graphite-memory__write_agent" in out
    assert "rule mem-shell pattern" in out


@pytest.mark.parametrize(
    ("body", "finding"),
    [
        (
            "Use `memory.phase_lock` -> `memory.write_governed`. That is the only model write.\n",
            "only-model-write",
        ),
        (
            "Agents must phase-lock and obtain a governance receipt before any memory write.\n",
            "ceremony-before-write",
        ),
        (
            "`write_agent` requires a phase_lock and a receipt.\n",
            "write-agent-gated",
        ),
    ],
)
def test_doctrine_that_gates_the_agent_write_fails_on_a_converged_surface(
    tmp_path: Path, body: str, finding: str
) -> None:
    _write(tmp_path, "skills/l9-graphiti-memory/SKILL.md", "# memory\n\n" + body)
    rc, out = _run_validator(tmp_path)
    assert rc == 1, out
    assert f"[agent-lane-interposition/{finding}]" in out, out


def test_superseded_or_optional_wording_is_allowed(tmp_path: Path) -> None:
    body = (
        "# memory\n\n"
        "ADR-0030 once named `memory.phase_lock` -> `memory.write_governed` as the only "
        "model write; that sentence is superseded by ADR-0033. `memory.write_agent` is the "
        "ordinary write and the governed pair is optional.\n"
    )
    _write(tmp_path, "skills/l9-graphiti-memory/SKILL.md", body)
    _rc, out = _run_validator(tmp_path)
    assert "[agent-lane-interposition/" not in out, out


def test_no_doctrine_makes_an_agent_write_wait_on_a_ceremony() -> None:
    """Live doctrine may describe ``write_governed`` as optional, never as the
    only agent write, and may not make ``write_agent`` wait on a lock, receipt,
    close, or PR state. Historical additive-only paragraphs are superseded by
    named fragments and are excluded by that marker.
    """
    forbidden = [
        re.compile(r"phase_lock\s*(→|->)\s*memory\.write_governed[^.\n]*\bonly model write\b"),
        re.compile(
            r"\bwrite_agent\b[^.\n]*\brequires?\b[^.\n]*\b(phase[_ -]lock|receipt|make pr)\b"
        ),
        re.compile(r"\bl9-memory write\b[^.\n]*\b(denied|blocked)\b[^.\n]*\buntil\b"),
    ]
    surfaces = [
        REPO / "skills/l9-graphiti-memory/SKILL.md",
        REPO / "skills/l9-end-session/SKILL.md",
        REPO / "docs/MEMORY_PIPELINE_MAP.md",
        REPO / "ops/memory/README.md",
        REPO / "environment/agents/adapters/claude-code/memory/memory-enforcement.contract.json",
        *sorted((REPO / "rules").glob("*.mdc")),
    ]
    offenders: list[str] = []
    for path in surfaces:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in forbidden:
            for match in pattern.finditer(text):
                offenders.append(f"{path.relative_to(REPO)}: {match.group(0)[:100]!r}")
    assert offenders == [], "\n".join(offenders)
