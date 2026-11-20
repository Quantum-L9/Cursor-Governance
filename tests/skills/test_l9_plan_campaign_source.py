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


def _run(tmp_path: Path, plan: dict, *extra: str, with_plan_md: bool = True) -> tuple[int, Path]:
    out = tmp_path / "CAMPAIGN_SOURCE.yaml"
    args = [str(_write(tmp_path, plan)), "--out", str(out), "--repo-root", str(REPO)]
    if with_plan_md:
        plan_md = tmp_path / "plan.plan.md"
        if not plan_md.exists():
            plan_md.write_text("---\nname: t\noverview: t\n---\n\n# body\n", encoding="utf-8")
        args += ["--plan-md", str(plan_md)]
    args += list(extra)
    code = render.main(args)
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


def test_a_blocked_todo_is_refused() -> None:
    plan = _plan()
    plan["todos"][0]["files"] = []
    plan["todos"][0]["blocker"] = "awaiting the vendor schema"
    with pytest.raises(render.RenderError) as caught:
        render.render(plan, target="Quantum-L9/Cursor-Governance", campaign_id="x-plan")
    assert "is blocked (awaiting the vendor schema)" in str(caught.value)


def test_a_refused_rerender_keeps_the_admitted_source(tmp_path: Path) -> None:
    code, out = _run(tmp_path, _plan())
    assert code == 0
    admitted = out.read_bytes()
    plan = _plan()
    plan["todos"][0]["validation"] = ["test -s a.md && test -s b.md"]
    code, _ = _run(tmp_path, plan)
    assert code == 1
    assert out.read_bytes() == admitted
    assert not [path for path in out.parent.iterdir() if ".staged-" in path.name]


def test_an_admitting_run_without_plan_md_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "CAMPAIGN_SOURCE.yaml"
    code, _ = _run(tmp_path, _plan(), with_plan_md=False)
    assert code == 1
    assert "must stamp" in capsys.readouterr().err
    assert not out.exists()


def test_the_handoff_names_the_stamped_plan_only_after_the_stamp(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "CAMPAIGN_SOURCE.yaml"
    plan_md = tmp_path / "stamped.plan.md"
    plan_md.write_text("---\nname: t\noverview: t\n---\n\n# body\n", encoding="utf-8")
    code = render.main(
        [
            str(_write(tmp_path, _plan())),
            "--out",
            str(out),
            "--repo-root",
            str(REPO),
            "--plan-md",
            str(plan_md),
            "--json",
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["next"] == [f"make campaign {plan_md.resolve()}"]
    assert (out.parent / "blueprint").is_dir()
    recorded = plan_md.read_text(encoding="utf-8")
    for key in ("campaign_source", "campaign_source_sha256", "campaign_blueprint"):
        assert f"{key}:" in recorded


def test_a_plan_md_without_frontmatter_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "CAMPAIGN_SOURCE.yaml"
    bare = tmp_path / "bare.plan.md"
    bare.write_text("# no frontmatter\n", encoding="utf-8")
    code = render.main(
        [
            str(_write(tmp_path, _plan())),
            "--out",
            str(out),
            "--repo-root",
            str(REPO),
            "--plan-md",
            str(bare),
            "--json",
        ]
    )
    assert code == 1
    result = json.loads(capsys.readouterr().out)
    assert any("frontmatter" in str(error) for error in result["errors"])


def test_persisted_blueprint_keeps_each_validation_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = _plan()
    plan["todos"].append(
        {
            "id": "T3",
            "task": "Confirm the runtime marker is documented",
            "files": [
                "docs/program-execution/l9-plan-render-proof/NOTE.md",
                "docs/program-execution/l9-plan-render-proof/SUMMARY.md",
            ],
            "effort": "S",
            "risk": "medium",
            "dependencies": ["T2"],
            "operation": "Replace",
            "anchor": "existing file",
            "layer": "docs",
            "leverage_rank": 3,
            "shared_root_cause": "prose-only plans",
            "validation": [
                (
                    "grep -q l9_claude_runtime_present "
                    + "docs/program-execution/l9-plan-render-proof/NOTE.md"
                ),
                (
                    "grep -q l9_claude_runtime_present "
                    + "docs/program-execution/l9-plan-render-proof/SUMMARY.md"
                ),
            ],
            "acceptance": "Both docs name the runtime marker.",
        }
    )
    plan_md = tmp_path / "demo.plan.md"
    plan_md.write_text("---\nname: demo\noverview: proof\n---\n\n# body\n", encoding="utf-8")
    out = tmp_path / "CAMPAIGN_SOURCE.yaml"
    code = render.main(
        [
            str(_write(tmp_path, plan)),
            "--out",
            str(out),
            "--repo-root",
            str(REPO),
            "--plan-md",
            str(plan_md),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0, captured.out + captured.err
    result = json.loads(captured.out)
    cards = yaml.safe_load(
        (out.parent / "blueprint" / "TASK_CARDS.yaml").read_text(encoding="utf-8")
    )
    by_id = {task["id"]: task for task in cards["tasks"]}
    expected = {
        "TASK-001": plan["todos"][0]["validation"],
        "TASK-002": plan["todos"][1]["validation"],
        "TASK-003": plan["todos"][2]["validation"],
    }
    for task_id, commands in expected.items():
        found = [
            entry["command_or_inspection"]
            for entry in by_id[task_id]["validation"]
            if entry["method"] == "command"
        ]
        assert found == commands
    recorded = plan_md.read_text(encoding="utf-8")
    assert str(out.resolve()) in recorded
    assert str((out.parent / "blueprint").resolve()) in recorded
    assert "# body" in recorded.split("---", 2)[-1]
    assert result["next"] == [f"make campaign {plan_md.resolve()}"]


def _plan_kernel_gate():
    hooks = REPO / "ops" / "hooks"
    if str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))
    import plan_kernel_gate

    return plan_kernel_gate


def _self_test_module():
    spec = importlib.util.spec_from_file_location(
        "l9_plan_self_test_stamp_under_coverage",
        SKILL / "scripts" / "self_test.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_plan_kernel_gate_self_test_covers_the_campaign_latch(tmp_path: Path) -> None:
    """The root suite must execute the gate's new latch lines.

    ``plan_kernel_gate._self_test`` is the only in-repo exercise of the campaign
    stamp latch. CI coverage is the root pytest run, which never passes
    ``--self-test``, so those new lines were absent from ``coverage.xml``.
    """
    gate = _plan_kernel_gate()
    assert gate._self_test() == 0
    assert gate.plan_frontmatter(tmp_path) == {}
    missing = tmp_path / "missing.plan.md"
    gate.handle_post_tool_use({"cwd": str(tmp_path), "tool_input": {"path": str(missing)}})
    assert not gate.pipeline_required_path(tmp_path).is_file()


def test_skill_self_test_stamp_contract_is_executed(tmp_path: Path) -> None:
    """Cover the stamp checks that live in the skill self-test, which CI does not collect."""
    module = _self_test_module()
    errors: list[str] = []
    plan_md = module.campaign_stamp_plan(str(tmp_path))
    module.campaign_stamp_next_line(
        errors, f"ADMITTED\nmake campaign {plan_md.resolve()}\n", plan_md
    )
    assert errors == []
    module.campaign_stamp_requires_plan_md(errors, str(tmp_path))
    assert errors == []


def test_pipeline_latch_clear_is_best_effort(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = tmp_path / "p.plan.md"
    plan.write_text("---\nname: t\noverview: t\n---\n", encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    original_root = render.GOV_ROOT
    render.GOV_ROOT = empty
    try:
        render._clear_plan_pipeline_latch(plan, tmp_path)
    finally:
        render.GOV_ROOT = original_root

    gate = _plan_kernel_gate()

    def _boom(_workspace: Path, _plan: Path) -> None:
        raise OSError("full")

    original_clear = gate.clear_pipeline_required
    gate.clear_pipeline_required = _boom
    try:
        render._clear_plan_pipeline_latch(plan, tmp_path)
    finally:
        gate.clear_pipeline_required = original_clear

    gov = tmp_path / "gov"
    hooks = gov / "ops" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "plan_kernel_gate.py").write_text("raise RuntimeError('boom')\n", encoding="utf-8")
    saved = sys.modules.pop("plan_kernel_gate", None)
    broken = str(hooks)
    sys.path.insert(0, broken)
    render.GOV_ROOT = gov
    try:
        render._clear_plan_pipeline_latch(plan, tmp_path)
        assert "not checked" in capsys.readouterr().err
    finally:
        render.GOV_ROOT = original_root
        while broken in sys.path:
            sys.path.remove(broken)
        sys.modules.pop("plan_kernel_gate", None)
        if saved is not None:
            sys.modules["plan_kernel_gate"] = saved
