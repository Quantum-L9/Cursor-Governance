"""The operating-plane@2 consumer adapter at SessionStart: report-only renderings, both hooks.

The adapter's verification is the shared verifier's (covered by its own suite); these
tests pin the SessionStart surface: a line/markdown rendering that always prints, never
releases payload, exits 0, and is wired into both SessionStart hooks the same way the
coding projection is.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ADAPTER = REPO / "ops/scripts/operating_plane_v2_projection.py"
CURSOR_HOOK = REPO / "ops/hooks/session_start_bootstrap.sh"
CLAUDE_HOOK = (
    REPO / "environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh"
)
PROFILE = "l9.projection/cursor-governance-operating-plane@2"


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ADAPTER), "--repo-root", str(cwd), *args],
        capture_output=True,
        text=True,
        env={**os.environ, "L9_AUTHORITY_ROOT": str(cwd / "absent")},
        cwd=str(cwd),
        check=False,
    )


def test_line_format_is_report_only_and_always_prints(tmp_path: Path) -> None:
    completed = _run("--format", "line", cwd=tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("operating-plane projection: UNVERIFIED — ")
    assert completed.stdout.rstrip().endswith("(report-only)")


def test_markdown_format_names_the_profile_and_exits_zero(tmp_path: Path) -> None:
    completed = _run("--format", "markdown", cwd=tmp_path)
    assert completed.returncode == 0, completed.stderr
    lines = completed.stdout.splitlines()
    assert lines[0] == "### operating-plane projection"
    assert lines[1].startswith("- UNVERIFIED: ")
    assert lines[2] == f"- profile: {PROFILE} (consumer verifier; report-only)"


def test_report_only_formats_never_release_a_source_class(tmp_path: Path) -> None:
    completed = _run("--format", "line", "--source-class", "invariants", cwd=tmp_path)
    assert completed.returncode == 2 and "report-only" in completed.stderr


def test_json_format_keeps_the_status_exit_code(tmp_path: Path) -> None:
    completed = _run("--format", "json", cwd=tmp_path)
    assert completed.returncode == 3  # UNVERIFIED: no binding in an empty tree
    assert '"status": "UNVERIFIED"' in completed.stdout


def test_both_session_start_hooks_report_the_operating_plane_projection() -> None:
    cursor = CURSOR_HOOK.read_text(encoding="utf-8")
    assert "ops/scripts/operating_plane_v2_projection.py" in cursor
    assert '--mode admitted --workspace "$WS_ROOT" --format markdown' in cursor
    assert cursor.index("${CODING_PROJECTION_MD}") < cursor.index("${OPERATING_PLANE_MD}")
    claude = CLAUDE_HOOK.read_text(encoding="utf-8")
    assert "emit_operating_plane_projection() {" in claude
    assert '--mode admitted --workspace "$WORKSPACE" --format line' in claude
    assert claude.index('emit_coding_projection "$PY"') < claude.index(
        'emit_operating_plane_projection "$PY"'
    )
