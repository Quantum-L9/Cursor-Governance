"""Planner mode: opt-in binding of the strategic-planning projections and Plan Keeper context."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import architect_mode  # noqa: E402
import cto_mode  # noqa: E402
import planner_mode  # noqa: E402

SID = "session-p"
# The required domains of l9.domain-consumer-binding/strategic-planner@1
# (Quantum-L9/.github v3.36.0, ADR-033), in the binding's declared order.
PLANNER_REQUIRED = [
    "strategic-value",
    "architecture",
    "signals",
    "governance",
    "evidence-provenance",
    "capabilities-dependencies",
]
DOMAINS = [f"l9.projection/{n}@1" for n in PLANNER_REQUIRED]
CONTEXT = "l9.projection/strategic-planning-context@2"
SELECTED = [*DOMAINS, CONTEXT]
NOT_SELECTED = [
    "l9.projection/cursor-governance-operating-plane@2",
    "l9.projection/technical-coordination@1",
    "l9.projection/coding-agent-execution@1",
    "l9.projection/strategic-planner-value@1",
    "l9.projection/strategic-planner-interaction@1",
    "l9.projection/strategic-metacognition@2",
    "l9.projection/contracts-conformance@1",
    "l9.projection/identity-attribution@1",
]


@pytest.fixture(autouse=True)
def _no_ambient_session(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in planner_mode.SESSION_ENVS:
        monkeypatch.delenv(name, raising=False)


def _verify(status: str):
    def verify(_binding: Path, _root: Path | None) -> dict:
        return {
            "status": status,
            "reason": "ADMITTED" if status == planner_mode.ADMITTED else "X",
        }

    return verify


def _binding(ref: str) -> dict:
    entry = next(
        p for p in planner_mode.load_contract()["selection"]["projections"] if p["ref"] == ref
    )
    return yaml.safe_load((REPO / entry["binding"]).read_text())


def test_contract_is_opt_in_and_selects_the_planner_binding_plus_plan_keeper_context() -> None:
    doc = planner_mode.load_contract()
    assert doc["activation"]["default"] is False
    assert doc["activation"]["always_enabled"] is False
    assert doc["activation"]["repository_presence_alone_activates"] is False
    assert doc["activation"]["skill_presence_alone_activates"] is False
    projections = doc["selection"]["projections"]
    assert [p["ref"] for p in projections] == SELECTED
    assert all(p["required"] is True for p in projections)
    refs = {p["ref"] for p in projections}
    assert refs.isdisjoint(NOT_SELECTED)
    assert doc["intended_consumer"]["skill"] == "skills/l9-strategic-plan/SKILL.md"


def test_contract_never_confers_strategic_authority() -> None:
    doc = planner_mode.load_contract()
    must_not = set(doc["behavioral_scope"]["must_not"])
    assert {
        "self_admit_a_plan_revision_or_mutate_the_plan_without_strategic_authority",
        "substitute_strategic_value_for_plan_keeper_strategic_authority",
        "invent_numerical_priority_weights",
        "grant_coding_agents_plan_graph_access",
        "substitute_agent_reported_progress_for_target_evidence",
    } <= must_not
    assert doc["scope_discipline"]["labels_are_mode_local"] is True
    assert set(doc["scope_discipline"]["labels"]) == {"ADVANCE", "PARK", "ESCALATE"}
    assert len(doc["views"]) == 7
    assert "coding_agents" in doc["plan_access"]
    assert "planner_mode" in doc["plan_access"]["full_plan_graph_readers"]


@pytest.mark.parametrize("ref", SELECTED)
def test_each_binding_pins_its_committed_bundle_and_records_admission(ref: str) -> None:
    binding = _binding(ref)
    pins = binding["input"]["authority"]
    lock = json.loads((REPO / binding["input"]["bundle"]["path"] / "bundle.lock.json").read_text())
    assert lock["projection_profile"] == {
        "ref": ref,
        "digest": pins["projection_profile_digest"],
    }
    assert lock["composition_profile"] == {
        "ref": pins["composition_profile_ref"],
        "digest": pins["composition_profile_digest"],
    }
    assert [c["source_class"] for c in lock["components"]] == pins["expected_source_classes"]
    decided = {
        (d["candidate_ref"], d["candidate_digest"]) for d in binding["admission"]["decisions"]
    }
    assert decided == {
        (ref, pins["projection_profile_digest"]),
        (pins["composition_profile_ref"], pins["composition_profile_digest"]),
    }
    assert binding["load_condition"]["repository_presence_alone_loads"] is False
    assert "planner_mode_active" in binding["load_condition"]["when"]


def test_plan_keeper_context_is_bound_only_by_planner_mode() -> None:
    binding = _binding(CONTEXT)
    assert binding["input"]["authority"]["projection_profile_consumer"] == "plan_keeper"
    assert binding["load_condition"]["when"] == ["planner_mode_active"]
    for other in (architect_mode, cto_mode):
        refs = {p["ref"] for p in other.load_contract()["selection"]["projections"]}
        assert CONTEXT not in refs


def test_bundles_are_registered_with_the_producer() -> None:
    sys.path.insert(0, str(REPO / "tools" / "authority"))
    import produce_projection_bundle as producer

    for ref in DOMAINS:
        name = ref.split("/")[1].split("@")[0]
        assert producer.BUNDLES[ref] == {
            "composition_profile": f"l9.compose/{name}@1",
            "output": Path(f"generated/governance/domain_{name.replace('-', '_')}"),
        }
    assert producer.BUNDLES[CONTEXT] == {
        "composition_profile": "l9.compose/strategic-planning-context@2",
        "output": Path("generated/governance/strategic_planning_context"),
    }


def test_ci_verifies_the_plan_keeper_context_bundle() -> None:
    for workflow in (
        "l9-projection-bundle-verify.yml",
        "l9-projection-bundle-trusted-replay.yml",
    ):
        text = (REPO / ".github/workflows" / workflow).read_text()
        assert "strategic_planning_context" in text, workflow


def test_off_by_default(tmp_path: Path) -> None:
    report = planner_mode.evaluate(tmp_path, verify=_verify(planner_mode.ADMITTED), session_id=SID)
    assert report["mode"] == "OFF"


def test_active_loads_every_composed_view(tmp_path: Path) -> None:
    planner_mode.request(tmp_path, session_id=SID)
    report = planner_mode.evaluate(tmp_path, verify=_verify(planner_mode.ADMITTED), session_id=SID)
    assert report["mode"] == "ACTIVE"
    assert [item["ref"] for item in report["load"]] == SELECTED
    assert all(Path(item["composed_view"]).is_file() for item in report["load"])


def test_an_unadmitted_plan_keeper_context_blocks_the_mode(tmp_path: Path) -> None:
    planner_mode.request(tmp_path, session_id=SID)

    def verify(binding: Path, root: Path | None) -> dict:
        stale = binding.name == "strategic-planning-context.yaml"
        status = "STALE" if stale else planner_mode.ADMITTED
        return {"status": status, "reason": status}

    report = planner_mode.evaluate(tmp_path, verify=verify, session_id=SID)
    assert report["mode"] == "BLOCKED"
    assert [b["ref"] for b in report["blockers"]] == [CONTEXT]
    assert report["load"] == []


def test_request_from_another_session_is_off(tmp_path: Path) -> None:
    planner_mode.request(tmp_path, session_id=SID)
    report = planner_mode.evaluate(
        tmp_path, verify=_verify(planner_mode.ADMITTED), session_id="session-other"
    )
    assert report["mode"] == "OFF"


def test_modes_keep_separate_state(tmp_path: Path) -> None:
    planner_mode.request(tmp_path, session_id=SID)
    assert (tmp_path / ".l9/planner-mode/session.json").is_file()
    for other in (architect_mode, cto_mode):
        report = other.evaluate(tmp_path, verify=_verify(other.ADMITTED), session_id=SID)
        assert report["mode"] == "OFF"
    assert planner_mode.release(tmp_path) is True
    assert not (tmp_path / ".l9/architect-mode").exists()
    assert not (tmp_path / ".l9/cto-mode").exists()


def test_cli_without_authority_checkout_blocks_admission(tmp_path: Path) -> None:
    script = REPO / "ops/autonomy/planner_mode.py"
    on = subprocess.run(
        [sys.executable, str(script), "on", "--workspace", str(tmp_path), "--session-id", SID],
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(on.stdout)
    # Admission is resolved against an authority checkout; without one nothing is loaded.
    assert on.returncode == 3, on.stdout + on.stderr
    assert report["mode"] == "BLOCKED"
    assert {p["reason"] for p in report["projections"]} == {"AUTHORITY_ROOT_REQUIRED"}
    assert report["load"] == []
