"""Claude Code bootstrap binds identity the same way on both of its surfaces.

Operator decision 2026-11-20: the ``claude-code`` actor has exactly two
surfaces. ``claude-code-cli`` is the local CLI, where SessionStart runs as a
silent hook; ``claude-code-web`` is every hosted cloud session. Both must
reach the same resolver through the same SessionStart chain, and both must
produce an assertion pinned to the revision the memory store verifies.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from ops.memory import agent_identity as ai

ROOT = Path(__file__).resolve().parents[3]
CLAUDE_SURFACES = {"claude-code-cli", "claude-code-web"}
DRIFT = {"claude-code-desktop", "claude-code-ide", "claude-code-mobile"}
HOOK = "session_start_claude_governance.sh"

CLI = {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli"}
CLI_IN_IDE = {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "claude-vscode", "CURSOR_AGENT": "1"}
WEB = {"CLAUDECODE": "1", "CLAUDE_CODE_REMOTE": "true", "CLAUDE_CODE_ENTRYPOINT": "remote_desktop"}
WEB_FROM_PHONE = {**WEB, "CLAUDE_CODE_ENTRYPOINT": "remote_mobile"}


def _session_start_commands(path: Path) -> list[str]:
    settings = json.loads(path.read_text(encoding="utf-8"))
    return [
        hook["command"] for block in settings["hooks"]["SessionStart"] for hook in block["hooks"]
    ]


@pytest.mark.parametrize(
    "settings",
    [
        "environment/agents/adapters/claude-code/settings.template.json",
        ".claude/settings.json",
    ],
)
def test_session_start_chain_reaches_the_identity_block(settings: str) -> None:
    """On the CLI the hook runs unseen, so its wiring is proven here instead."""
    commands = _session_start_commands(ROOT / settings)
    governance = [c for c in commands if "session_start_claude_governance.sh" in c]
    assert len(governance) == 1, "exactly one SessionStart hook runs the identity block"
    assert any("memory_prefetch.py" in c for c in commands)
    hook = ROOT / "environment/agents/adapters/claude-code/hooks" / HOOK
    text = hook.read_text(encoding="utf-8")
    assert "-m ops.memory.agent_identity" in text
    assert "build_runtime_identity_assertion" in text


def test_the_projected_hook_copy_matches_its_source() -> None:
    source = ROOT / "environment/agents/adapters/claude-code/hooks" / HOOK
    projected = ROOT / ".claude/hooks" / HOOK
    assert projected.read_bytes() == source.read_bytes()


@pytest.mark.parametrize(
    ("env", "surface"),
    [
        (CLI, "claude-code-cli"),
        (CLI_IN_IDE, "claude-code-cli"),
        (WEB, "claude-code-web"),
        (WEB_FROM_PHONE, "claude-code-web"),
    ],
)
def test_one_actor_two_surfaces(env: dict[str, str], surface: str) -> None:
    assert ai.resolve_agent_id(env) == "claude-code"
    assert ai.resolve_surface_id(env) == surface


def test_no_resolver_path_emits_a_drifted_surface() -> None:
    emitted = set(ai.LOCAL_ENTRYPOINTS.values()) | set(ai.REMOTE_SURFACE_BY_ENTRYPOINT.values())
    assert emitted == CLAUDE_SURFACES


def test_every_binding_names_only_the_two_surfaces() -> None:
    registry = yaml.safe_load(
        (ROOT / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
    )
    host = yaml.safe_load(
        (ROOT / "governance/host-bindings/claude-code.yaml").read_text(encoding="utf-8")
    )
    peers = yaml.safe_load(
        (ROOT / "environment/agents/PEER_RUNTIME_BINDINGS.yaml").read_text(encoding="utf-8")
    )
    projection = yaml.safe_load(
        (ROOT / "generated/governance/canonical_identity.yaml").read_text(encoding="utf-8")
    )

    def ids(refs: list[str]) -> set[str]:
        return {ref.rsplit("#", 1)[1] for ref in refs}

    assert ids(registry["agents"]["claude-code"]["surface_refs"]) == CLAUDE_SURFACES
    assert ids(host["host"]["surface_refs"]) == CLAUDE_SURFACES
    claude_peer = next(
        v for v in _walk(peers) if isinstance(v, dict) and v.get("agent_ref") == "claude-code"
    )
    assert {b["surface"] for b in claude_peer["execution"]["bindings"]} == CLAUDE_SURFACES
    projected = {s["id"] for s in projection["surfaces"]}
    assert CLAUDE_SURFACES <= projected
    assert not (DRIFT & projected)


def _walk(node: object):
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


@pytest.mark.parametrize(("env", "surface"), [(CLI, "claude-code-cli"), (WEB, "claude-code-web")])
def test_bootstrap_assertion_is_built_in_a_clean_process(env: dict[str, str], surface: str) -> None:
    """The exact probe SessionStart runs, in a process with only host markers."""
    probe = (
        "from ops.memory.print_agent_assertion_env import build_runtime_identity_assertion as b\n"
        "import json\n"
        "a = b()\n"
        "d = a['resolved_dimensions']\n"
        "rev = a['governing_coordinates']['global_identity_authority_revision']\n"
        "print(json.dumps({'surface': d['surface_identity'], 'actor': d['actor_identity'],"
        " 'rev': rev}))"
    )
    clean = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(ROOT),
    }
    out = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env={**clean, **env},
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(out.stdout.strip().splitlines()[-1])
    assert result["actor"] == "l9.actor-registry/global@1#claude-code"
    assert result["surface"] == f"l9.surface-registry/global@1#{surface}"
    pinned = yaml.safe_load(
        (ROOT / "generated/governance/canonical_identity.yaml").read_text(encoding="utf-8")
    )["projection"]["source_revision"]
    assert result["rev"] == pinned
