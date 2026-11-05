"""Fail-closed simple-plan pipeline: one writer, a real GAR run, admission."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PY = sys.executable
PIPELINE = REPO / "skills" / "l9-plan-simple" / "scripts" / "run_plan_pipeline.py"
ADMIT = REPO / "skills" / "l9-plan-simple" / "scripts" / "admit_plan.py"
VALIDATOR = REPO / "skills" / "l9-plan" / "scripts" / "validate_plan_document.py"
RENDERER = REPO / "skills" / "l9-plan" / "scripts" / "render_plan_pe_autonomy.py"
FIXTURE = REPO / "skills" / "l9-plan" / "fixtures" / "plan_pass.json"
HOLD = REPO / "tests" / "skills" / "l9_plan_simple" / "_pipeline_hold"
GAR_SCRIPTS = REPO / "skills" / "l9-global-architect" / "scripts"
SIMPLE_SCRIPTS = REPO / "skills" / "l9-plan-simple" / "scripts"

sys.path.insert(0, str(SIMPLE_SCRIPTS))
sys.path.insert(0, str(GAR_SCRIPTS))

from admit_plan import check_plan  # noqa: E402
from generate_plan_section_receipt import build_receipt  # noqa: E402
from validate_plan_section_receipt import check_receipt  # noqa: E402
from write_plan_run import write_run  # noqa: E402


def _bound_plan(dest: Path) -> None:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan["success_criteria"] = ["self_test.py PASS"]
    dest.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


def _prefetch(workspace: Path) -> None:
    path = workspace / ".l9" / "memory" / "plan-prefetch.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "test", "status": "HIT"}) + "\n", encoding="utf-8")


def _clear(hold: Path) -> None:
    if not hold.exists():
        return
    for path in sorted(hold.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    hold.rmdir()


def test_v1_pipeline_exits_nonzero_without_a_gar_run(tmp_path: Path) -> None:
    hold = HOLD
    hold.mkdir(parents=True, exist_ok=True)
    plan = hold / "plan.json"
    try:
        _bound_plan(plan)
        _prefetch(hold)
        proc = subprocess.run(
            [
                PY,
                str(PIPELINE),
                "--plan-json",
                str(plan.relative_to(REPO)),
                "--execute-via",
                "cursor-build",
                "--workspace",
                str(hold.relative_to(REPO)),
                "--gar-run",
                str((hold / "missing-gar.json").relative_to(REPO)),
                "--out-md",
                str((hold / "out.plan.md").relative_to(REPO)),
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode != 0
        assert "GAR" in proc.stderr
        assert not (hold / "out.plan.md").exists()
    finally:
        _clear(hold)
        del tmp_path


def test_v2_validator_rejects_a_plan_missing_required_declarations(tmp_path: Path) -> None:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan.pop("owner")
    plan.pop("execution_envelope")
    plan.pop("complexity")
    plan["todos"][0].pop("layer")
    (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    proc = subprocess.run(
        [PY, str(VALIDATOR), "plan.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    blob = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "owner" in blob
    assert "layer" in blob


def test_v3_pipeline_passes_when_the_gar_run_and_declarations_are_present() -> None:
    hold = HOLD
    hold.mkdir(parents=True, exist_ok=True)
    plan = hold / "plan.json"
    gar = hold / "gar-run.json"
    out = hold / "out.plan.md"
    try:
        _bound_plan(plan)
        _prefetch(hold)
        write_run(
            gar,
            governing_cause="agents were emitting a title and a paragraph",
            intervention="one pipeline is the only writer",
            evidence_paths=["skills/l9-plan-simple/SKILL.md"],
            run_id="v3",
        )
        proc = subprocess.run(
            [
                PY,
                str(PIPELINE),
                "--plan-json",
                str(plan.relative_to(REPO)),
                "--execute-via",
                "cursor-build",
                "--workspace",
                str(hold.relative_to(REPO)),
                "--gar-run",
                str(gar.relative_to(REPO)),
                "--out-md",
                str(out.relative_to(REPO)),
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        text = out.read_text(encoding="utf-8")
        assert "unknown — not declared" not in text
        assert "unbound — re-render" not in text
        assert "unbound — no " not in text
        assert "PASS:" in proc.stdout
    finally:
        _clear(hold)


def test_v4_admit_rejects_a_title_and_paragraph() -> None:
    hold = HOLD
    hold.mkdir(parents=True, exist_ok=True)
    thin = hold / "thin_title.plan.md"
    try:
        thin.write_text("# Integration PR publish\n\nShip one PR.\n", encoding="utf-8")
        errors = check_plan(thin)
        assert errors
        assert any(err.startswith("G_ADMIT") for err in errors)
        proc = subprocess.run(
            [PY, str(ADMIT), str(thin.relative_to(REPO))],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode != 0
        assert "G_ADMIT" in proc.stdout
    finally:
        _clear(hold)


def test_v5_receipt_fails_when_invoked_and_the_run_file_is_absent() -> None:
    hold = HOLD
    hold.mkdir(parents=True, exist_ok=True)
    plan = hold / "plan.json"
    md = hold / "out.plan.md"
    receipt_path = hold / "out.section-receipt.json"
    try:
        _bound_plan(plan)
        rendered = subprocess.run(
            [
                PY,
                str(RENDERER),
                str(plan),
                "--execute-via=cursor-build",
                "--workspace",
                ".",
            ],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert rendered.returncode == 0, rendered.stderr
        md.write_text(rendered.stdout, encoding="utf-8")
        receipt = build_receipt(plan, md, gar_invoked=True, gar_run_id="missing")
        receipt["status"] = "pass"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        errors = check_receipt(receipt_path)
        blob = "\n".join(errors)
        assert errors
        assert "G_GAR_UPSTREAM" in blob
        assert "run file" in blob
    finally:
        _clear(hold)


def test_v6_renderer_default_stays_program_execution() -> None:
    proc = subprocess.run(
        [PY, str(RENDERER), str(FIXTURE)],
        cwd=FIXTURE.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "## Execute via @environment/program-execution" in proc.stdout
