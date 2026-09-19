"""SessionStart names WHY Context7 is absent, from the evidence that decided it.

`claude_projection.project_mcp` records every template server it left out of
`.mcp.json` as `gated_out_servers` in the projection receipt: a server whose
`_requires_env` variable the platform did not proxy. That is the cause. The
hook used to print "Context7 (hosted skip)" keyed on SKIP_PLUGIN_MARKETPLACE —
a correlate — and sent readers to the plugin catalog instead of the account
variable. The line must be decided by the receipt first, with the marketplace
wording kept only as the fallback when the receipt says nothing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_HOOK = (
    REPO_ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "session_start_claude_governance.sh"
)
PROJECTED_HOOK = REPO_ROOT / ".claude" / "hooks" / "session_start_claude_governance.sh"


def _context7_block(text: str) -> str:
    start = text.index('_ctx7_gated="$(')
    end = text.index("skill_log=", start)
    return text[start:end]


def test_context7_line_is_keyed_on_the_projection_receipt_first() -> None:
    block = _context7_block(ADAPTER_HOOK.read_text(encoding="utf-8"))
    assert "projection-receipt.json" in block
    assert "gated_out_servers" in block
    assert "CONTEXT7_API_KEY" in block
    # The receipt decides; the marketplace flag is the fallback branch only.
    assert block.index('"$_ctx7_gated" = "gated"') < block.index("SKIP_PLUGIN_MARKETPLACE")
    assert "elif" in block


def test_projected_hook_matches_the_adapter_ssot() -> None:
    assert PROJECTED_HOOK.read_bytes() == ADAPTER_HOOK.read_bytes()


def test_receipt_probe_reads_the_shape_claude_projection_writes(tmp_path: Path) -> None:
    """Run the embedded python exactly as the hook does, against both receipt shapes."""
    block = _context7_block(ADAPTER_HOOK.read_text(encoding="utf-8"))
    # The heredoc opener line carries a redirect after <<'PY'; the program starts
    # on the next line and ends at the bare PY terminator.
    program = block.split("<<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n", 1)[0]

    def probe(doc: object) -> str:
        receipt = tmp_path / "projection-receipt.json"
        receipt.write_text(json.dumps(doc), encoding="utf-8")
        proc = subprocess.run(
            ["python3", "-", str(receipt)],
            input=program,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        return proc.stdout.strip()

    gated_list = {
        "domains": [
            {"domain": "mcp", "status": "ok", "detail": {"gated_out_servers": ["context7"]}}
        ]
    }
    gated_dict = {"domains": {"mcp": {"detail": {"gated_out_servers": ["context7"]}}}}
    rendered = {"domains": [{"domain": "mcp", "status": "ok", "detail": {}}]}
    assert probe(gated_list) == "gated"
    assert probe(gated_dict) == "gated"
    assert probe(rendered) == ""
    assert probe([]) == ""
    missing = subprocess.run(
        ["python3", "-", str(tmp_path / "absent.json")],
        input=program,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 0 and missing.stdout == ""
