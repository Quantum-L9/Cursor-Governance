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


def test_stale_refusal_surfaces_the_outcome_cause_and_changed_classes(monkeypatch) -> None:
    """A STALE admission refusal names why: the adapter's flattened reason is kept verbatim,
    and the chained Outcome's cause and changed source classes are reported beside it."""
    sys.path.insert(0, str(REPO))
    from ops.scripts import operating_plane_v2_projection as adapter

    class Outcome(Exception):  # the shared verifier's shape: status, reason, **detail
        def __init__(self, status: str, reason: str, **detail: object) -> None:
            super().__init__(reason)
            self.status, self.reason, self.detail = status, reason, detail

    def stale(_bundle: Path) -> dict[str, object]:
        outcome = Outcome(
            "STALE",
            "NOT_CURRENT_AT_AUTHORITY_MAIN",
            authority_main="f" * 40,
            cause="MATERIAL_CHANGE",
            changed=["vocabulary"],
        )
        raise adapter.Rejected(f"{outcome.status} {outcome.reason}") from outcome

    monkeypatch.setattr(adapter, "_binding", lambda _path: {})
    monkeypatch.setattr(adapter, "read_lock", stale)
    result = adapter.classify(repo_root=REPO, mode="admitted")

    assert result["status"] == "REJECTED"
    assert result["reason"] == "STALE NOT_CURRENT_AT_AUTHORITY_MAIN"
    assert result["cause"] == "MATERIAL_CHANGE"
    assert result["changed"] == ["vocabulary"]
    assert "authority_main" not in result  # only diagnostics are lifted, never a verdict
    line = adapter.render_line(result)
    assert "[cause: MATERIAL_CHANGE; changed: ['vocabulary']]" in line
    assert line.endswith("(report-only)")
    assert "cause: MATERIAL_CHANGE" in adapter.render_markdown(result).splitlines()[1]


def test_a_refusal_without_an_outcome_reports_no_diagnosis(monkeypatch) -> None:
    sys.path.insert(0, str(REPO))
    from ops.scripts import operating_plane_v2_projection as adapter

    def rejected(_bundle: Path) -> dict[str, object]:
        raise adapter.Rejected("LOCK_UNREADABLE")

    monkeypatch.setattr(adapter, "_binding", lambda _path: {})
    monkeypatch.setattr(adapter, "read_lock", rejected)
    result = adapter.classify(repo_root=REPO, mode="admitted")

    assert result == {"profile_ref": PROFILE, "status": "REJECTED", "reason": "LOCK_UNREADABLE"}
    assert adapter.render_line(result) == (
        "operating-plane projection: REJECTED — LOCK_UNREADABLE (report-only)"
    )


def test_both_session_start_hooks_autobind_the_operating_plane_without_a_skill() -> None:
    # Each host's SessionStart calls the host binding itself; no skill is involved.
    cursor = CURSOR_HOOK.read_text(encoding="utf-8")
    assert '"$HOST_BINDING_PY"' in cursor
    assert '--host cursor --workspace "$WS_ROOT" --format markdown' in cursor
    assert "--domains-only" not in cursor
    assert cursor.index("${CODING_PROJECTION_MD}") < cursor.index("${DEFAULT_BINDING_MD}")
    claude = CLAUDE_HOOK.read_text(encoding="utf-8")
    assert "emit_operating_plane_projection() {" in claude
    assert '"$control" --host claude-code --workspace "$WORKSPACE" --format line' in claude
    assert claude.index('emit_coding_projection "$PY"') < claude.index(
        'emit_operating_plane_projection "$PY"'
    )
