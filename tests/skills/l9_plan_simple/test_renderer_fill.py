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
RENDERER = REPO / "skills" / "l9-plan" / "scripts" / "render_plan_pe_autonomy.py"
FIXTURE = REPO / "skills" / "l9-plan" / "fixtures" / "plan_pass.json"

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


def _render_plan(
    tmp_path: Path, plan: dict, mode: str = "cursor-build", *, allow_draft: bool = False
) -> str:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    cmd = [sys.executable, str(RENDERER), "plan.json", f"--execute-via={mode}"]
    if allow_draft:
        cmd.append("--allow-draft")
    proc = subprocess.run(
        cmd,
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


VALIDATOR = REPO / "skills" / "l9-plan" / "scripts" / "validate_plan_document.py"
NOT_DECLARED_TEXT = "unknown — not declared in PLAN_DOCUMENT"
# Every template slot that once rendered a hardcoded NOT_DECLARED.
DECLARABLE_ROWS = (
    "owner",
    "mode",
    "allowed_services",
    "access",
    "architectural_boundaries_crossed",
    "external_systems_touched",
    "migration_required",
)


def _machine_stub(out: str) -> dict:
    yaml = pytest.importorskip("yaml")
    stub = re.search(r"```yaml\n(.*?)```", out, re.S)
    assert stub
    return yaml.safe_load(stub.group(1))


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _strip_declarations(plan: dict) -> dict:
    for key in ("owner", "execution_envelope", "complexity"):
        plan.pop(key, None)
    for todo in plan["todos"]:
        todo.pop("layer", None)
    return plan


@pytest.mark.parametrize("mode", SIMPLE_MODES)
def test_fully_declared_plan_renders_no_not_declared_slot(mode: str) -> None:
    out = _render(mode)
    assert "not declared" not in out


def test_declarations_reach_the_projection_and_stub() -> None:
    plan = _fixture()
    out = _render("cursor-build")
    assert _row(out, "owner") == f"| owner | {plan['owner']} |"
    assert _row(out, "mode") == "| mode | `none` |"
    assert _row(out, "allowed_services") == "| allowed_services | none |"
    assert _row(out, "access") == "| access | `none` |"
    assert (
        _row(out, "architectural_boundaries_crossed")
        == "| architectural_boundaries_crossed | none |"
    )
    assert _row(out, "external_systems_touched") == "| external_systems_touched | none |"
    assert _row(out, "migration_required") == "| migration_required | `false` |"
    for todo in plan["todos"]:
        assert re.search(rf"^\| {todo['id']} \| `[^`]+` \| `{todo['layer']}` \|", out, re.M)
    stub = _machine_stub(out)
    assert stub["metadata"]["owner"] == plan["owner"]
    assert stub["execution_envelope"]["network"]["mode"] == "none"
    assert stub["execution_envelope"]["secrets"]["access"] == "none"


def test_non_empty_lists_render_as_items(tmp_path: Path) -> None:
    plan = _fixture()
    plan["execution_envelope"]["network"] = {
        "mode": "named_services_only",
        "allowed_services": ["github"],
    }
    plan["complexity"]["external_systems_touched"] = ["GitHub API"]
    out = _render_plan(tmp_path, plan)
    assert _row(out, "allowed_services") == "| allowed_services | `github` |"
    assert _row(out, "external_systems_touched") == "| external_systems_touched | `GitHub API` |"


def test_absent_declarations_keep_the_explicit_marker(tmp_path: Path) -> None:
    out = _render_plan(tmp_path, _strip_declarations(_fixture()), allow_draft=True)
    for row in DECLARABLE_ROWS:
        assert NOT_DECLARED_TEXT in _row(out, row), row
    arch = out.split("| todo_id | bounded_context | layer |", 1)[1].split("\n\n", 1)[0]
    assert arch.count(NOT_DECLARED_TEXT) == len(_fixture()["todos"])
    stub = _machine_stub(out)
    assert stub["metadata"]["owner"].startswith("unknown — not declared")
    assert stub["execution_envelope"]["network"]["mode"].startswith("unknown — not declared")
    assert stub["execution_envelope"]["secrets"]["access"].startswith("unknown — not declared")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p["execution_envelope"]["network"].update(mode="open"),
        lambda p: p["execution_envelope"]["secrets"].update(access="everything"),
        lambda p: p["todos"][0].update(layer="frontend"),
        lambda p: p["complexity"].update(migration_required="maybe"),
        lambda p: p.update(owner=""),
    ],
    ids=["network-mode", "secrets-access", "layer", "migration-required", "empty-owner"],
)
def test_schema_rejects_values_outside_the_template_contract(tmp_path: Path, mutate) -> None:
    plan = _fixture()
    mutate(plan)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "plan.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0, proc.stdout


def test_cli_refuses_a_projection_with_undeclared_fields(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(_strip_declarations(_fixture())), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(RENDERER), "plan.json", "--execute-via=cursor-build"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "unknown — not declared" in proc.stdout
    assert "allow-draft" in proc.stderr


def test_declarations_are_required_in_the_plan_schema() -> None:
    from plan_sections import json_required_keys, plan_schema_path

    schema = json.loads(plan_schema_path().read_text(encoding="utf-8"))
    required = json_required_keys(schema)
    for key in ("owner", "estimate", "execution_envelope", "complexity"):
        assert key in required, key
    assert "layer" in schema["properties"]["todos"]["items"]["required"]


def test_l9_plan_simple_runs_no_archived_asset() -> None:
    assert not (REPO / "skills" / "_archived" / "l9-plan").exists()
    # Tracked files only: bytecode caches and other untracked output are not
    # surfaces (a __pycache__ .pyc embeds the legacy acceptance constant).
    surfaces = subprocess.run(
        [
            "git",
            "ls-files",
            "-z",
            "--",
            "skills/l9-plan-simple",
            "workflows/dags/plan_simple_build_dag.py",
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    legacy_ok = {
        "skills/l9-plan-simple/scripts/plan_sections.py",
        "skills/l9-plan-simple/schemas/plan-section-receipt.schema.json",
    }
    offenders = [
        rel
        for rel in surfaces
        if rel
        and rel not in legacy_ok
        and (REPO / rel).is_file()
        and "_archived/l9-plan" in (REPO / rel).read_text(encoding="utf-8", errors="ignore")
    ]
    assert offenders == []


def _render_titled(tmp_path: Path, plan: dict, mode: str = "cursor-build") -> str:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(RENDERER), "plan.json", f"--execute-via={mode}"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


@pytest.mark.parametrize(
    "title",
    [
        "stack_safe_merge: promotions use merge commits",
        "- leading dash: still a title",
        'quotes "inside" and a back\\slash: here',
        "# hash-led title",
    ],
)
def test_frontmatter_survives_yaml_hostile_titles(tmp_path: Path, title: str) -> None:
    """An unquoted `name:` with ": " broke the whole block (seen in the field)."""
    yaml = pytest.importorskip("yaml")
    from plan_sections import FRONTMATTER_RE, frontmatter_presence, frontmatter_yaml_error

    plan = json.loads(FIXTURE.read_text(encoding="utf-8"))
    plan["title"] = title
    plan["objective"] = 'Objective with "quotes": and a colon'
    out = _render_titled(tmp_path, plan)
    match = FRONTMATTER_RE.match(out)
    assert match, out[:200]
    loaded = yaml.safe_load(match.group(1))
    assert loaded["name"] == title
    assert loaded["overview"] == plan["objective"]
    assert isinstance(loaded["todos"], list) and loaded["todos"]
    assert frontmatter_yaml_error(out) is None
    assert all(frontmatter_presence(out).values()), frontmatter_presence(out)


def test_broken_frontmatter_is_named_not_reported_as_missing_todos() -> None:
    pytest.importorskip("yaml")
    from plan_sections import frontmatter_yaml_error, projection_marker_errors

    good = _render("cursor-build")
    broken = good.replace(good.splitlines()[1], "name: unquoted: colon title", 1)
    error = frontmatter_yaml_error(broken)
    assert error and error.startswith("G_FRONTMATTER_YAML:"), error
    assert "line 1" in error
    assert error in projection_marker_errors(broken)
    assert frontmatter_yaml_error("no frontmatter here\n").startswith("G_FRONTMATTER_YAML:")
