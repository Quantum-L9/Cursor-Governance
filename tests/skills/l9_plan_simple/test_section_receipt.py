"""l9-plan-simple section receipt and GAR-upstream contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SKILL = REPO / "skills" / "l9-plan-simple"
SCRIPTS = SKILL / "scripts"


def test_skill_requires_gar_upstream() -> None:
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "l9-global-architect" in text
    assert "generate_plan_section_receipt.py" in text
    assert "validate_plan_section_receipt.py" in text


def test_section_receipt_self_test() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "self_test.py")],
        cwd=SKILL,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "PASS: l9-plan-simple self_test" in proc.stdout


def test_dag_also_reads_gar() -> None:
    from workflows.dags.plan_simple_build_dag import PLAN_SIMPLE_BUILD_DAG

    node = next(item for item in PLAN_SIMPLE_BUILD_DAG.nodes if item.id == "plan_simple")
    also_read = node.metadata["also_read"]
    assert "skills/l9-global-architect/SKILL.md" in also_read
