"""Planner mode: opt-in binding of the strategic-planning projections and Plan Keeper context."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))
sys.path.insert(0, str(REPO / "tools" / "authority"))

import architect_mode  # noqa: E402
import cto_mode  # noqa: E402
import planner_mode  # noqa: E402
import produce_projection_bundle  # noqa: E402
import projection_mode  # noqa: E402

MODE = planner_mode.MODE
OK = projection_mode.ADMITTED
SID = "planner-session"
CONTEXT = "l9.projection/strategic-planning-context@2"
# Required domains of l9.domain-consumer-binding/strategic-planner@1 (.github v3.36.0,
# ADR-033), in the binding's declared order, then the read-only Plan Keeper context.
SELECTED = [
    *(
        f"l9.projection/{name}@1"
        for name in (
            "strategic-value",
            "architecture",
            "signals",
            "governance",
            "evidence-provenance",
            "capabilities-dependencies",
        )
    ),
    CONTEXT,
]
EXCLUDED = {
    "l9.projection/cursor-governance-operating-plane@2",
    "l9.projection/technical-coordination@1",
    "l9.projection/coding-agent-execution@1",
    "l9.projection/strategic-planner-value@1",
    "l9.projection/strategic-planner-interaction@1",
    "l9.projection/strategic-metacognition@2",
    "l9.projection/contracts-conformance@1",
    "l9.projection/identity-attribution@1",
}


@pytest.fixture(autouse=True)
def _isolate_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for env in projection_mode.SESSION_ENVS:
        monkeypatch.delenv(env, raising=False)


@pytest.fixture
def contract() -> dict[str, Any]:
    return MODE.load_contract()


def statuses(**overrides: str):
    """A verifier stub: ADMITTED_AND_CURRENT unless the binding file name is overridden."""

    def verifier(binding: Path, _root: Path | None) -> dict[str, str]:
        status = overrides.get(binding.stem, OK)
        return {"status": status, "reason": status}

    return verifier


def bindings(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        entry["ref"]: yaml.safe_load((REPO / entry["binding"]).read_text())
        for entry in contract["selection"]["projections"]
    }


def test_selection_is_the_planner_binding_plus_read_only_plan_keeper_context(
    contract: dict[str, Any],
) -> None:
    activation = contract["activation"]
    assert not any(
        activation[key]
        for key in (
            "default",
            "always_enabled",
            "repository_presence_alone_activates",
            "skill_presence_alone_activates",
        )
    )
    entries = contract["selection"]["projections"]
    assert [e["ref"] for e in entries] == SELECTED
    assert {e["required"] for e in entries} == {True}
    assert EXCLUDED.isdisjoint(e["ref"] for e in entries)
    assert contract["intended_consumer"]["skill"] == "skills/l9-strategic-plan/SKILL.md"


def test_scope_never_confers_strategic_authority(contract: dict[str, Any]) -> None:
    forbidden = {
        "self_admit_a_plan_revision_or_mutate_the_plan_without_strategic_authority",
        "substitute_strategic_value_for_plan_keeper_strategic_authority",
        "invent_numerical_priority_weights",
        "grant_coding_agents_plan_graph_access",
        "substitute_agent_reported_progress_for_target_evidence",
    }
    assert forbidden <= set(contract["behavioral_scope"]["must_not"])
    discipline = contract["scope_discipline"]
    assert discipline["labels_are_mode_local"] is True
    assert sorted(discipline["labels"]) == ["ADVANCE", "ESCALATE", "PARK"]
    assert len(contract["views"]) == 7
    assert "planner_mode" in contract["plan_access"]["full_plan_graph_readers"]
    assert "coding_agents" in contract["plan_access"]


def test_every_binding_matches_its_lock_and_admits_exactly_its_pins(
    contract: dict[str, Any],
) -> None:
    for ref, binding in bindings(contract).items():
        pins = binding["input"]["authority"]
        lock_path = REPO / binding["input"]["bundle"]["path"] / "bundle.lock.json"
        lock = json.loads(lock_path.read_text())
        expected_pairs = {
            (ref, pins["projection_profile_digest"]),
            (pins["composition_profile_ref"], pins["composition_profile_digest"]),
        }
        recorded_pairs = {
            (d["candidate_ref"], d["candidate_digest"]) for d in binding["admission"]["decisions"]
        }
        assert recorded_pairs == expected_pairs, ref
        assert (lock["projection_profile"]["ref"], lock["projection_profile"]["digest"]) == (
            ref,
            pins["projection_profile_digest"],
        ), ref
        assert lock["composition_profile"]["digest"] == pins["composition_profile_digest"], ref
        assert [c["source_class"] for c in lock["components"]] == pins["expected_source_classes"], (
            ref
        )
        condition = binding["load_condition"]
        assert "planner_mode_active" in condition["when"], ref
        assert condition["repository_presence_alone_loads"] is False, ref


def test_plan_keeper_context_is_planner_only(contract: dict[str, Any]) -> None:
    context = bindings(contract)[CONTEXT]
    assert context["input"]["authority"]["projection_profile_consumer"] == "plan_keeper"
    assert context["load_condition"]["when"] == ["planner_mode_active"]
    for sibling in (architect_mode, cto_mode):
        sibling_refs = {e["ref"] for e in sibling.load_contract()["selection"]["projections"]}
        assert CONTEXT not in sibling_refs


def test_producer_and_ci_know_every_planner_bundle(contract: dict[str, Any]) -> None:
    workflows = [
        (REPO / ".github/workflows" / name).read_text()
        for name in ("l9-projection-bundle-verify.yml", "l9-projection-bundle-trusted-replay.yml")
    ]
    for ref, binding in bindings(contract).items():
        registered = produce_projection_bundle.BUNDLES[ref]
        assert registered["output"] == Path(binding["input"]["bundle"]["path"]), ref
        assert (
            registered["composition_profile"]
            == binding["input"]["authority"]["composition_profile_ref"]
        ), ref
    assert all("strategic_planning_context" in text for text in workflows)


def test_lifecycle_off_active_and_released(tmp_path: Path) -> None:
    assert MODE.evaluate(tmp_path, verify=statuses(), session_id=SID)["mode"] == "OFF"
    MODE.request(tmp_path, session_id=SID)
    active = MODE.evaluate(tmp_path, verify=statuses(), session_id=SID)
    assert active["mode"] == "ACTIVE"
    assert [item["ref"] for item in active["load"]] == SELECTED
    assert all(Path(item["composed_view"]).is_file() for item in active["load"])
    elsewhere = MODE.evaluate(tmp_path, verify=statuses(), session_id="another-session")
    assert elsewhere["mode"] == "OFF"
    assert MODE.release(tmp_path) is True
    assert MODE.evaluate(tmp_path, verify=statuses(), session_id=SID)["mode"] == "OFF"


def test_stale_plan_keeper_context_blocks_with_no_partial_load(tmp_path: Path) -> None:
    MODE.request(tmp_path, session_id=SID)
    report = MODE.evaluate(
        tmp_path, verify=statuses(**{"strategic-planning-context": "STALE"}), session_id=SID
    )
    assert (report["mode"], report["load"]) == ("BLOCKED", [])
    assert [blocker["ref"] for blocker in report["blockers"]] == [CONTEXT]


def test_planner_state_is_isolated_from_sibling_modes(tmp_path: Path) -> None:
    MODE.request(tmp_path, session_id=SID)
    assert (tmp_path / ".l9" / "planner-mode" / "session.json").is_file()
    for sibling in (architect_mode, cto_mode):
        assert sibling.evaluate(tmp_path, verify=statuses(), session_id=SID)["mode"] == "OFF"
    MODE.release(tmp_path)
    assert sorted(p.name for p in (tmp_path / ".l9").iterdir()) == ["planner-mode"]


def test_cli_resolves_admission_only_against_an_authority_checkout(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO / "ops" / "autonomy" / "planner_mode.py"),
            "on",
            "--session-id",
            SID,
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(result.stdout)
    assert result.returncode == 3, result.stderr
    assert (report["mode"], report["load"]) == ("BLOCKED", [])
    assert {p["reason"] for p in report["projections"]} == {"AUTHORITY_ROOT_REQUIRED"}
