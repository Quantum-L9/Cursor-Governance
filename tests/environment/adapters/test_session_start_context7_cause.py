"""Context7 is a failure to fix, never a server to skip — and never a pasted key.

`context7` used to be `_requires_env`-gated, then rendered as an HTTP server with
`Authorization: Bearer ${CONTEXT7_API_KEY}` — a key nothing delivered and that
would have been readable in the environment anyway. It is now a local stdio
bridge (ops/secrets/vault_mcp_bridge.py) that binds the key from Infisical as
this surface's machine identity. It always renders; an unbound key makes the
bridge refuse to start, and SessionStart reports the bind and names the fix.
These tests pin that contract at every layer.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE = REPO_ROOT / "environment" / "agents" / "adapters" / "claude-code"
ADAPTER_HOOK = CLAUDE / "hooks" / "session_start_claude_governance.sh"
PROJECTED_HOOK = REPO_ROOT / ".claude" / "hooks" / "session_start_claude_governance.sh"
TEMPLATE = CLAUDE / "mcp.template.json"


def _context7_block(text: str) -> str:
    start = text.index("# Context7 is rendered unconditionally")
    end = text.index("skill_log=", start)
    return text[start:end]


BRIDGE = {
    "type": "stdio",
    "command": "${HOME}/.cursor-governance/ops/secrets/run_vault_mcp_bridge.sh",
    "args": ["context7"],
}


def test_template_renders_context7_as_the_vault_bridge() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert template["mcpServers"]["context7"] == BRIDGE
    assert "CONTEXT7_API_KEY}" not in json.dumps(template["mcpServers"])


def test_committed_projection_carries_the_bridge() -> None:
    """The governance checkout loads the tracked .mcp.json, so it must carry it."""
    committed = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    assert committed["mcpServers"]["context7"] == BRIDGE


def test_projection_renders_the_bridge_with_the_key_absent() -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts"))
    import claude_projection as projection

    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    rendered = projection.render_mcp(template, {"mcpServers": {}}, environ={})
    assert rendered["mcpServers"]["context7"] == BRIDGE


def test_the_bridge_launcher_exists_and_is_executable() -> None:
    import os

    launcher = REPO_ROOT / "ops" / "secrets" / "run_vault_mcp_bridge.sh"
    assert launcher.is_file() and os.access(launcher, os.X_OK)


def test_hook_reports_the_bind_and_names_the_fix() -> None:
    block = _context7_block(ADAPTER_HOOK.read_text(encoding="utf-8"))
    assert 'capability_bind.py" --check CONTEXT7_API_KEY' in block
    assert "bridged" in block and "NOT bound" in block
    assert "L9_INFISICAL_CLIENT_ID" in block and "L9_INFISICAL_CLIENT_SECRET" in block
    # The marketplace flag is reported as the closed plugin route, not as the cause.
    assert "marketplace plugin route closed" in block
    assert "gated_out_servers" not in block


def test_hook_no_longer_strips_the_key_before_projecting() -> None:
    text = ADAPTER_HOOK.read_text(encoding="utf-8")
    assert "-u CONTEXT7_API_KEY" not in text
    assert 'env -u L9_MEMORY_INTERPRETER"' in text


def test_projected_hook_matches_the_adapter_ssot() -> None:
    assert PROJECTED_HOOK.read_bytes() == ADAPTER_HOOK.read_bytes()


def test_hook_still_parses() -> None:
    assert subprocess.run(["bash", "-n", str(ADAPTER_HOOK)]).returncode == 0
