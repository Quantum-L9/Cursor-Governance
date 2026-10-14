"""The SessionStart warm path reuses a verdict only after verifying it this ceremony.

``install.sh --reuse-if-verified`` may skip only the projection apply, and only
when the previous receipt is READY for the same governance revision, workspace
and inputs key AND this run's projection ``--check`` is clean. A fingerprint
match alone never reuses a verdict (acceptance B02). The shared bootstrap is
never skipped: its secrets plane, leak check, publish-path probe, repository
identity and git excludes are session-scoped state no inputs key covers. The
receipt names the mode and the source ceremony, and anything that does not
verify runs the full projection apply.
"""

from __future__ import annotations

from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parents[1]
INSTALL = (CLAUDE_DIR / "install.sh").read_text(encoding="utf-8")
HOOK = (CLAUDE_DIR / "hooks" / "session_start_claude_governance.sh").read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    return text[text.index(start) : text.index(end, text.index(start))]


def test_session_start_requests_verified_reuse_on_both_launch_paths() -> None:
    assert HOOK.count("--reuse-if-verified") == 2


def test_reuse_requires_a_ready_complete_receipt_for_the_same_inputs() -> None:
    guard = _between(INSTALL, "previous_reusable_id() {", "\nREUSEPY\n")
    for condition in (
        'data.get("overall") == "READY"',
        'data.get("stage") == "receipt"',
        'not data.get("interrupted_by")',
        'data.get("governance_revision") == head',
        'data.get("workspace") == workspace',
        'data.get("inputs_key") == key',
        'age < float(data.get("ttl_seconds") or 0)',
    ):
        assert condition in guard, condition


def test_reuse_is_decided_by_checks_run_this_ceremony() -> None:
    decision = _between(INSTALL, 'stage "reuse-verify"', 'stage "shared-bootstrap"')
    assert "--check --no-receipt" in decision
    assert "projection=ok" in decision
    assert "REUSE=1" in decision
    # Check mode never reuses, and reuse is opt-in.
    assert '[ "$REUSE_REQUESTED" = "1" ] && [ "$CHECK" != "1" ]' in decision


def test_inputs_key_covers_revision_toolchain_roots_and_hosted_flags() -> None:
    key = _between(INSTALL, "compute_inputs_key() {", "\nKEYPY\n")
    for material in (
        "governance_revision",
        ".l9-uv-fingerprint",
        "covered_roots",
        "CLAUDE_CODE_REMOTE",
        "SKIP_PLUGIN_MARKETPLACE",
        "L9_MEMORY_INTERPRETER",
    ):
        assert material in key, material


def test_receipt_names_the_reuse_and_its_source() -> None:
    assert "echo verified_reuse" in INSTALL
    assert '"reused_from"' in INSTALL and '"inputs_key"' in INSTALL


def test_session_scoped_stages_still_run_on_reuse() -> None:
    # None of these is gated on REUSE: session-scoped verdicts are always fresh.
    for stage in (
        'stage "shared-bootstrap"',
        'stage "memory-readiness"',
        'stage "structural-validate"',
    ):
        body = _between(INSTALL, stage, "\nstage ")
        assert "REUSE" not in body, stage
