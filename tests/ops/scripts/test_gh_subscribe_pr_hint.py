"""#888: the GraphQL-less subscribe hint names the session tool that exists.

On a surface without GraphQL, `gh_subscribe_pr` skips and tells the agent what to
call instead. It named `mcp__github__subscribe_pr_activity`, which no surface
exposes; the Claude Code session tool is
`mcp__claude-code-remote__subscribe_pr_activity`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[3] / "ops" / "scripts" / "lib" / "gh_subscribe_pr.sh"

_SCRIPT = f"""
set -u
source "{LIB}"
gh() {{ echo PR_node_1; }}
gh_graphql() {{ GH_GRAPHQL_UNSUPPORTED=1; GH_GRAPHQL_CLASSIFICATION=SURFACE_UNSUPPORTED_GRAPHQL; return 1; }}
gh_subscribe_pr Quantum-L9 Cursor-Governance 7
"""


def test_graphqlless_hint_names_the_session_subscribe_tool() -> None:
    proc = subprocess.run(
        ["bash", "-c", _SCRIPT], capture_output=True, text=True, timeout=30, check=False
    )
    assert proc.returncode == 0, proc.stderr
    assert (
        "mcp__claude-code-remote__subscribe_pr_activity "
        "{owner: Quantum-L9, repo: Cursor-Governance, pullNumber: 7}" in proc.stdout
    )
    assert "mcp__github__subscribe_pr_activity" not in proc.stdout
