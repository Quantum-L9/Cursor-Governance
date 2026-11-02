"""The plan projection fills every template section from PLAN_DOCUMENT.

Regression for the renderer that emitted seed sections, then appended the raw
template body as a "fill guide" full of `<parameter>` slots, and stamped
`quality_gate | observe .pre-commit-config.yaml catalog` as the proof of every
success property regardless of what the property was.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SIMPLE_SCRIPTS = REPO / "skills" / "l9-plan-simple" / "scripts"
RENDERER = REPO / "skills" / "_archived" / "l9-plan" / "scripts" / "render_plan_pe_autonomy.py"
FIXTURE = REPO / "skills" / "_archived" / "l9-plan" / "fixtures" / "plan_pass.json"

sys.path.insert(0, str(SIMPLE_SCRIPTS))

from plan_sections import (  # noqa: E402
    HEADING_RE,
    md_required_headings,
    missing_labels,
    unfilled_parameters,
)

SIMPLE_MODES = ("cursor-build", "embedded")


def _render(mode: str, *extra: str, plan: Path = FIXTURE) -> str:
    proc = subprocess.run(
        [sys.executable, str(RENDERER), str(plan), f"--execute-via={mode}", *extra],
        cwd=REPO,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


@pytest.mark.parametrize("mode", SIMPLE_MODES)
def test_simple_projection_leaves_no_template_parameter(mode: str) -> None:
    assert unfilled_parameters(_render(mode)) == []


@pytest.mark.parametrize("mode", SIMPLE_MODES)
def test_projection_is_one_filled_document_not_seed_plus_template(mode: str) -> None:
    out = _render(mode)
    titles = [m.group(1).strip() for m in HEADING_RE.finditer(out)]
    assert not any(t.startswith("Template body") for t in titles), titles
    assert not any("(seed" in t or "(from PLAN_DOCUMENT)" in t for t in titles), titles
    assert out.count("\n# PLAN: ") == 1
    for required in md_required_headings(mode=mode):
        assert titles.count(required) == 1 or any(t.startswith(f"{required} ") for t in titles), (
            required
        )


def test_success_proof_comes_from_the_property_not_a_constant() -> None:
    out = _render("cursor-build")
    assert "observe .pre-commit-config.yaml catalog" not in out
    sp01 = next(line for line in out.splitlines() if line.startswith("| SP-01 |"))
    assert "`quality_gate`" in sp01
    assert "V1: `python3 scripts/self_test.py`" in sp01
    sp02 = next(line for line in out.splitlines() if line.startswith("| SP-02 |"))
    assert "unbound" in sp02
    assert "V1" not in sp02 and "V2" not in sp02


def test_criterion_naming_a_validation_id_binds_to_it(tmp_path: Path) -> None:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan["success_criteria"] = ["hook catalog clean per V2"]
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(RENDERER), "plan.json", "--execute-via=cursor-build"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    sp01 = next(line for line in proc.stdout.splitlines() if line.startswith("| SP-01 |"))
    assert "V2: `.pre-commit-config.yaml`" in sp01


def test_plan_document_data_reaches_the_template_sections() -> None:
    out = _render("cursor-build")
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for todo in plan["todos"]:
        assert re.search(rf"^\| {todo['id']} \| `filesystem_mutation` \|", out, re.M)
    for milestone in plan["milestones"]:
        assert f"| {milestone['id']} | {milestone['outcome']} |" in out
    for question in plan["stress_test"]["disconfirming_questions"]:
        assert f"- {question}" in out
    assert "**write_deny:** `src/constellation_node_sdk/`" in out
    assert "| E-V1 | SP-01 |" in out


def test_machine_stub_is_valid_yaml_bound_to_the_mode() -> None:
    yaml = pytest.importorskip("yaml")
    for mode, pipeline in (("cursor-build", "cursor-build"), ("embedded", "embedded")):
        out = _render(mode)
        stub = re.search(r"```yaml\n(.*?)```", out, re.S)
        assert stub, mode
        data = yaml.safe_load(stub.group(1))
        assert data["execute_via"]["pipeline"] == pipeline
        assert [t["id"] for t in data["todos"]] == ["T1", "T2"]


def test_workspace_binds_the_immutable_baseline() -> None:
    out = _render("cursor-build", "--workspace", ".")
    assert re.search(r"^\| commit_sha \| `[0-9a-f]{40}` \|", out, re.M)
    assert "unbound — re-render" not in out.split("## Immutable baseline", 1)[1].split("## ")[0]


def test_unbound_baseline_is_explicit_without_workspace() -> None:
    out = _render("cursor-build")
    section = out.split("## Immutable baseline", 1)[1].split("\n## ")[0]
    assert "| commit_sha | unbound — re-render with `--workspace .`" in section


def test_unfilled_parameter_fails_the_receipt() -> None:
    out = _render("cursor-build").replace("| T1 |", "| <todo_id> |", 1)
    unfilled = unfilled_parameters(out)
    assert unfilled == ["todo_id"]
    labels = missing_labels({}, {}, {}, {"handoff_heading": True}, True, unfilled)
    assert any(label.startswith("G_UNFILLED_PARAMETER") for label in labels)


def test_quoted_slot_in_a_prohibition_is_not_unfilled() -> None:
    assert unfilled_parameters("- Do not write `Lock: origin/main = <sha>`.") == []
    assert unfilled_parameters("| commit_sha | `<commit_sha>` |") == ["commit_sha"]
