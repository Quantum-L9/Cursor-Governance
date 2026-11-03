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


def _render_plan(tmp_path: Path, plan: dict, mode: str = "cursor-build") -> str:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(RENDERER), "plan.json", f"--execute-via={mode}"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _row(out: str, field: str) -> str:
    return next(line for line in out.splitlines() if line.startswith(f"| {field} |"))


def _converged_plan() -> dict:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan["convergence"]["status"] = "converged"
    plan["convergence"]["remaining_unknown_ids"] = []
    return plan


def test_converged_plan_with_unprovable_property_is_not_ready(tmp_path: Path) -> None:
    out = _render_plan(tmp_path, _converged_plan())  # SP-02 names no validation
    assert "`draft`" in _row(out, "status")
    assert "unprovable success properties: SP-02" in _row(out, "status")
    assert _row(out, "implementation_ready") == "| implementation_ready | `false` |"
    assert _row(out, "current_state") == "| current_state | `draft` |"
    assert "| `open_blocker` | SP-02 |" in out


def test_property_proved_only_by_not_applicable_validation_is_not_ready(tmp_path: Path) -> None:
    plan = _converged_plan()
    plan["success_criteria"] = ["self_test.py PASS", "hook catalog clean per V2"]
    out = _render_plan(tmp_path, plan)  # V2 is not_applicable
    assert "unprovable success properties: SP-02" in _row(out, "status")
    assert _row(out, "implementation_ready") == "| implementation_ready | `false` |"


def test_converged_plan_with_runnable_proofs_is_executable(tmp_path: Path) -> None:
    plan = _converged_plan()
    plan["success_criteria"] = ["self_test.py PASS"]
    out = _render_plan(tmp_path, plan)
    assert _row(out, "status") == (
        "| status | `executable` — every readiness gate in PLAN_DOCUMENT holds |"
    )
    assert _row(out, "implementation_ready") == "| implementation_ready | `true` |"
    assert _row(out, "current_state") == "| current_state | `execution_ready` |"
    assert _row(out, "next_convergence_gate") == "| next_convergence_gate | `complete_when` |"


def test_blocking_unknown_keeps_plan_out_of_executable(tmp_path: Path) -> None:
    plan = _converged_plan()
    plan["success_criteria"] = ["self_test.py PASS"]
    plan["unknowns"] = [
        {"id": "U1", "question": "q", "decision_effect": "e", "resolution": "block"}
    ]
    out = _render_plan(tmp_path, plan)
    assert "blocking unknowns: U1" in _row(out, "status")
    assert _row(out, "implementation_ready") == "| implementation_ready | `false` |"


def test_irreversible_todo_activates_the_gated_write_pipeline(tmp_path: Path) -> None:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan["todos"][1]["risk"] = "irreversible"
    out = _render_plan(tmp_path, plan)
    section = out.split("## Gated write pipeline", 1)[1].split("\n## ")[0]
    assert "Activated — irreversible todo(s): T2." in section
    assert "human approval recorded for T2" in section
    assert "- **receipt_required:** `true`" in section
    assert "- **bounded_write_count:** `1`" in section
    assert "Not activated" not in section


def test_reversible_plan_leaves_the_gated_write_pipeline_inactive() -> None:
    section = _render("cursor-build").split("## Gated write pipeline", 1)[1].split("\n## ")[0]
    assert "Not activated" in section


def test_angle_tokens_projected_from_the_plan_are_not_unfilled(tmp_path: Path) -> None:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan["objective"] = "Replace every <parameter> value the old renderer left behind"
    plan["final_validation"][0]["command"] = "python3 scripts/self_test.py --branch <branch>"
    out = _render_plan(tmp_path, plan)
    assert "<parameter>" in out and "<branch>" in out
    assert unfilled_parameters(out, plan) == []
    # The same tokens without the plan as provenance are template slots.
    assert unfilled_parameters(out) == ["branch", "parameter"]


def test_non_template_angle_token_is_ordinary_content() -> None:
    assert unfilled_parameters("run `tool <not_a_template_slot_xyz>`") == []


def _machine_stub(out: str) -> dict:
    yaml = pytest.importorskip("yaml")
    stub = re.search(r"```yaml\n(.*?)```", out, re.S)
    assert stub
    return yaml.safe_load(stub.group(1))


@pytest.mark.parametrize("mode", SIMPLE_MODES)
def test_declared_owner_reaches_metadata_and_stub(mode: str) -> None:
    owner = json.loads(FIXTURE.read_text(encoding="utf-8"))["owner"]
    out = _render(mode)
    assert _row(out, "owner") == f"| owner | {owner} |"
    assert _machine_stub(out)["metadata"]["owner"] == owner


def test_missing_owner_renders_not_declared(tmp_path: Path) -> None:
    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del plan["owner"]
    out = _render_plan(tmp_path, plan)
    assert _row(out, "owner").startswith("| owner | unknown — not declared in PLAN_DOCUMENT")
    assert _machine_stub(out)["metadata"]["owner"].startswith("unknown — not declared")


def test_owner_is_optional_and_typed_in_the_plan_schema() -> None:
    from plan_sections import json_required_keys, plan_schema_path

    schema = json.loads(plan_schema_path().read_text(encoding="utf-8"))
    assert schema["properties"]["owner"] == {
        **schema["properties"]["owner"],
        "type": "string",
        "minLength": 1,
    }
    assert "owner" not in json_required_keys(schema)
