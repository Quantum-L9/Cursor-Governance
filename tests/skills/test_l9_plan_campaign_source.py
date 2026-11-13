"""l9-plan renders a PLAN_DOCUMENT as a campaign-source.v2 that make campaign admits.

PROGRAM_EXECUTION_PLANNER_V1. The renderer's self-check is Program Execution's
own front door, compiler and launchability (inference off), so these tests
assert on PE's verdict rather than on a second validator: an admitted render is
one `make campaign` takes on its direct route with nothing synthesized.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "l9-plan"
FIXTURE = SKILL / "fixtures" / "plan_campaign.json"


def _module():
    spec = importlib.util.spec_from_file_location(
        "l9_plan_render_campaign_source_under_test",
        SKILL / "scripts" / "render_campaign_source.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


render = _module()


def _plan() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _write(tmp_path: Path, plan: dict) -> Path:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


def _run(tmp_path: Path, plan: dict, *extra: str) -> tuple[int, Path]:
    out = tmp_path / "CAMPAIGN_SOURCE.yaml"
    code = render.main(
        [str(_write(tmp_path, plan)), "--out", str(out), "--repo-root", str(REPO), *extra]
    )
    return code, out


def test_the_fixture_plan_is_admitted_by_program_execution(tmp_path: Path) -> None:
    code, out = _run(tmp_path, _plan())
    assert code == 0
    source = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert source["schema"] == "l9.program-execution.campaign-source.v2"
    assert source["metadata"]["campaign_id"] == "l9-plan-render-proof"
    assert source["targets"][0]["repository_id"] == "Quantum-L9/Cursor-Governance"
    # The front door classifies it as the direct v2 route.
    pe = REPO / "environment" / "program-execution" / "scripts"
    sys.path.insert(0, str(pe))
    spec = importlib.util.spec_from_file_location(
        "l9_plan_test_campaign_input", pe / "campaign_input.py"
    )
    campaign_input = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = campaign_input
    spec.loader.exec_module(campaign_input)
    found = campaign_input.classify(out)
    assert found.kind is campaign_input.CampaignInputKind.CAMPAIGN_SOURCE_V2
    assert campaign_input.preflight(found) == []


def test_the_plans_own_ordering_scope_and_validation_survive(tmp_path: Path) -> None:
    source = render.render(_plan(), target="Quantum-L9/Cursor-Governance", campaign_id="x-plan")
    assert source["dependency_edges"] == [{"from": "TASK-001", "to": "TASK-002"}]
    assert [(w["id"], w["task_ids"], w["predecessor_wave_ids"]) for w in source["waves"]] == [
        ("W0", ["TASK-001"], []),
        ("W1", ["TASK-002"], ["W0"]),
    ]
    first, second = source["tasks"]
    assert first["paths"] == ["docs/program-execution/l9-plan-render-proof/NOTE.md"]
    assert [v["command_or_inspection"] for v in second["validation"]] == [
        "test -s docs/program-execution/l9-plan-render-proof/SUMMARY.md"
    ]
    for task in source["tasks"]:
        ceiling = task["authorization_ceiling"]
        assert not any(
            ceiling[key] for key in ("push", "pull_request", "merge", "deploy_or_migrate")
        )
        assert "dependencies" not in task and "depends_on" not in task


def test_a_writing_todo_without_validation_is_refused(tmp_path: Path) -> None:
    plan = _plan()
    del plan["todos"][1]["validation"]
    with pytest.raises(render.RenderError) as caught:
        render.render(plan, target="Quantum-L9/Cursor-Governance", campaign_id="x-plan")
    assert "declares no validation command" in str(caught.value)


def test_an_unresolved_blocking_unknown_is_refused() -> None:
    plan = _plan()
    plan["unknowns"] = [
        {"id": "U1", "question": "q", "decision_effect": "e", "resolution": "block"}
    ]
    with pytest.raises(render.RenderError) as caught:
        render.render(plan, target="Quantum-L9/Cursor-Governance", campaign_id="x-plan")
    assert "U1" in str(caught.value)


def test_a_dependency_on_an_unknown_todo_is_refused() -> None:
    plan = copy.deepcopy(_plan())
    plan["todos"][1]["dependencies"] = ["T9"]
    with pytest.raises(render.RenderError) as caught:
        render.render(plan, target="Quantum-L9/Cursor-Governance", campaign_id="x-plan")
    assert "unknown todo 'T9'" in str(caught.value)


@pytest.mark.parametrize("campaign_id", ["X", "pe-0123abcd", "Bad_Id"])
def test_an_inadmissible_campaign_id_is_refused(campaign_id: str) -> None:
    with pytest.raises(render.RenderError):
        render.resolve_campaign_id({"title": "t"}, campaign_id)


def test_an_inadmissible_validation_command_is_refused_by_program_execution(
    tmp_path: Path,
) -> None:
    plan = _plan()
    plan["todos"][0]["validation"] = ["test -s a.md && test -s b.md"]
    code, out = _run(tmp_path, plan)
    assert code == 1
    # Refused by PE's own preflight; the file it rendered is not a usable plan.


def test_the_target_comes_from_the_checkouts_origin_when_undeclared() -> None:
    plan = _plan()
    del plan["campaign"]["target_repository"]
    assert render.resolve_target(plan, None, REPO) == "Quantum-L9/Cursor-Governance"
