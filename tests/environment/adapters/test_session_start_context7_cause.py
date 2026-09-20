"""Context7 is a failure to fix, never a server to skip.

`context7` used to be `_requires_env`-gated in mcp.template.json and its key was
stripped before projection on governance checkouts, so a missing secret produced
a silently absent server on every hosted session while rule 22 mandated a tool
that did not exist. The server now renders unconditionally; when
`CONTEXT7_API_KEY` is not populated it fails to authenticate, and SessionStart
says so and names the fix (populate the secret). These tests pin that contract
at every layer: template, committed projection, hook, and the hook's wording.
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


def test_template_renders_context7_without_a_gate() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    entry = template["mcpServers"]["context7"]
    assert "_requires_env" not in entry
    assert entry["headers"]["Authorization"] == "Bearer ${CONTEXT7_API_KEY}"
    # No value anywhere: the header references the variable, nothing else.
    assert "CONTEXT7_API_KEY=" not in TEMPLATE.read_text(encoding="utf-8")


def test_committed_projection_carries_context7() -> None:
    """The governance checkout loads the tracked .mcp.json, so it must carry it."""
    committed = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    entry = committed["mcpServers"]["context7"]
    assert entry["url"] == "https://mcp.context7.com/mcp"
    assert entry["headers"]["Authorization"] == "Bearer ${CONTEXT7_API_KEY}"
    assert "_requires_env" not in entry


def test_projection_renders_context7_with_the_key_absent() -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts"))
    import claude_projection as projection

    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    rendered = projection.render_mcp(template, {"mcpServers": {}}, environ={})
    assert "context7" in rendered["mcpServers"]
    assert rendered["mcpServers"]["context7"]["headers"]["Authorization"] == (
        "Bearer ${CONTEXT7_API_KEY}"
    )


def test_hook_reports_the_key_state_and_names_the_fix() -> None:
    block = _context7_block(ADAPTER_HOOK.read_text(encoding="utf-8"))
    assert 'if [ -n "${CONTEXT7_API_KEY:-}" ]' in block
    assert "proxied" in block
    assert "ABSENT" in block and "fail to authenticate" in block
    assert "Infisical CONTEXT7_API_KEY" in block
    assert "do not paste" in block
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
