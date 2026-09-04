"""l9-plan-simple handoff modes: cursor-build (default) and embedded.

One planner, one schema, one validator, one renderer — `--execute-via` is the
only axis that differs. These tests pin both halves of that: the embedded
projection carries no execution authority, and adding it changed nothing about
the cursor-build or pe-campaign projections.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "l9-plan"
RENDERER = SKILL / "scripts" / "render_plan_pe_autonomy.py"
FIXTURE = SKILL / "fixtures" / "plan_pass.json"
SIMPLE = ROOT / "skills" / "l9-plan-simple"

# Live execution/publication authority that embedded mode must never project.
FORBIDDEN_IN_EMBEDDED = (
    "Press **Build**",
    "PR_STACK=auto",
    "PR_REMEDIATE=0",
    "make pr",
    "display the PR URL",
    "agent_worktree_start.sh",
    "make campaign",
    "Program Lock",
    "Controller lease",
)


def _render(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RENDERER), str(FIXTURE), *args],
        cwd=SKILL,
        check=False,
        capture_output=True,
        text=True,
    )


def _ok(*args: str) -> str:
    proc = _render(*args)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_renderer_accepts_embedded() -> None:
    assert "## Handoff to Caller" in _ok("--execute-via=embedded")


def test_embedded_frontmatter_is_machine_identifiable() -> None:
    out = _ok("--execute-via=embedded")
    head = out.split("---", 2)[1]
    assert "kind: simple" in head
    assert "execute_via: embedded" in head


def test_embedded_projection_hands_control_to_caller() -> None:
    out = _ok("--execute-via=embedded")
    assert "## Handoff to Caller" in out
    assert "validated planning evidence" in out
    assert "caller MUST establish and enforce its own execution authority" in out
    assert "pipeline: embedded" in out


def test_embedded_projection_carries_no_execution_authority() -> None:
    out = _ok("--execute-via=embedded")
    leaked = [needle for needle in FORBIDDEN_IN_EMBEDDED if needle in out]
    assert not leaked, f"embedded projection leaked execution authority: {leaked}"


def test_embedded_projection_carries_no_pe_or_build_execute_path() -> None:
    out = _ok("--execute-via=embedded")
    assert "## Execute via @environment/program-execution" not in out
    assert "Execute via Cursor Build" not in out


def test_cursor_build_projection_is_unchanged() -> None:
    out = _ok("--execute-via=cursor-build")
    assert "## Execute via Cursor Build" in out
    assert "kind: simple" in out
    assert "execute_via: cursor-build" in out
    assert "PR_STACK=auto" in out
    assert "make pr" in out
    assert "PR URL" in out
    assert "**never** branch from `origin/main`" in out
    assert "## Execute via @environment/program-execution" not in out


def test_pe_campaign_projection_is_unchanged() -> None:
    out = _ok("--execute-via=pe-campaign")
    assert "## Execute via @environment/program-execution" in out
    assert "kind: pe" in out
    assert "execute_via: pe-campaign" in out
    assert "@autonomy" in out


def test_renderer_default_mode_remains_pe_campaign() -> None:
    """l9-plan owns the renderer default; embedded must not have moved it."""
    assert _ok() == _ok("--execute-via=pe-campaign")


def test_invalid_execute_via_still_fails() -> None:
    proc = _render("--execute-via=not-a-mode")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr


def test_l9_plan_simple_default_invocation_remains_cursor_build() -> None:
    skill = (SIMPLE / "SKILL.md").read_text(encoding="utf-8")
    workflow = (SIMPLE / "references" / "plan-workflow-simple.md").read_text(encoding="utf-8")
    for text in (skill, workflow):
        assert (
            "`cursor-build` | **default**" in text or "**`cursor-build` is the default.**" in text
        )
    assert "Absent an explicit embedded request, plan in `cursor-build`" in skill


def test_l9_plan_simple_documents_both_modes_and_forbids_silent_fallback() -> None:
    skill = (SIMPLE / "SKILL.md").read_text(encoding="utf-8")
    assert "--execute-via=embedded" in skill
    assert "Never infer embedded from capability absence." in skill
    assert "no** silent fallback" in skill
    for surface in (
        SIMPLE / "references" / "plan-workflow-simple.md",
        SIMPLE / "references" / "validation-checklist.md",
        SIMPLE / "agents" / "meta.yaml",
    ):
        assert "embedded" in surface.read_text(encoding="utf-8"), surface


def _sole_owner(basename: str, owner: str) -> None:
    """`basename` may exist exactly once under skills/, at `owner`."""
    found = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").rglob(basename))
    assert found == [owner], f"{basename} must exist only at {owner}, found {found}"


def test_no_duplicate_planner_schema_validator_or_renderer() -> None:
    """Embedded is a mode on the shared axis, never a second planning engine.

    Scoped to the artifacts the contract forbids duplicating. l9-plan-simple may
    own unrelated tooling of its own; what it must never own is a second
    PLAN_DOCUMENT schema, plan validator, projection renderer, or planner skill.
    """
    assert not (ROOT / "skills" / "l9-plan-embedded").exists()
    _sole_owner("plan-document.schema.json", "skills/l9-plan/schemas/plan-document.schema.json")
    _sole_owner("validate_plan_document.py", "skills/l9-plan/scripts/validate_plan_document.py")
    _sole_owner("render_plan_pe_autonomy.py", "skills/l9-plan/scripts/render_plan_pe_autonomy.py")
    # The executable-plan template stays a symlink to the first-class SSOT.
    forked = [
        p.relative_to(ROOT).as_posix()
        for p in SIMPLE.rglob("*.plan.md")
        if p.is_file() and not p.is_symlink()
    ]
    assert not forked, f"l9-plan-simple must not fork the executable-plan template: {forked}"
