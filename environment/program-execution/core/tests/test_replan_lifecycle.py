"""Controller Replan Revision lifecycle tests (TASK-003).

Bootstraps a real Program Execution Controller runtime against a minimal
blueprint and exercises propose -> independent verify -> Controller activation,
plus the negative cases: proposer self-verification, unverified activation,
authority containment failure, missing trigger evidence, stale revisions, and
failed-revision preservation of the previous valid plan.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[1]
TEMPLATE = CORE / "program-execution-controller-template"
sys.path.insert(0, str(TEMPLATE / "scripts"))

from pec import replan  # noqa: E402
from pec.controller import ControllerError, bootstrap, status  # noqa: E402
from pec.replan import (  # noqa: E402
    activate,
    current_plan_revision,
    list_revisions,
    propose,
    reject,
    verify,
)

INDEX = """\
schema: program-execution-blueprint.index.v2
schema_version: 2.0.0
blueprint_contract: program-execution-blueprint.v2
required_sources:
- PROGRAM.yaml
- EXECUTION_TARGETS.yaml
- AUTHORITY_REGISTRY.yaml
- DECISION_REGISTER.yaml
- UNKNOWN_REGISTER.yaml
- RISK_REGISTER.yaml
- WAIVER_REGISTER.yaml
- EVIDENCE_CATALOG.yaml
- DO_NOT_BUILD.yaml
- CURRENT_STATE_DELTA.yaml
- WORKSTREAMS.yaml
- DEPENDENCY_GRAPH.yaml
- EXECUTION_WAVES.yaml
- TASK_CARDS.yaml
- CONVERGENCE_GATES.yaml
- OBSERVABILITY_PLAN.yaml
- CUTOVER_AND_ROLLBACK.yaml
- SOURCE_TRACEABILITY.yaml
"""

PROGRAM = """\
schema: program-execution-blueprint.program.v2
program:
  id: fixture-replan-program
  name: Replan Lifecycle Fixture
  version: 1.0.0
  owner: fixture-owner
  definition_status: draft
  objective: Exercise the Controller Replan Revision lifecycle.
  contracts:
    pair: program-execution-system.v2
    blueprint: program-execution-blueprint.v2
    controller: program-execution-controller.v2
  authority_order: []
  operating_rules:
  - program_lock_is_maximum_runtime_planning_authority
  - completed_execution_history_is_immutable
  - failed_replan_preserves_previous_valid_plan
  - worker_claim_is_not_verification
  terminal_verdicts: [CONVERGED, CONVERGED_WITH_NON_BLOCKING_RISKS, NOT_CONVERGED, INCONCLUSIVE]
"""

EMPTY_SOURCES = {
    "EXECUTION_TARGETS.yaml": "targets: []\n",
    "AUTHORITY_REGISTRY.yaml": "authorities: []\n",
    "DECISION_REGISTER.yaml": "decisions: []\n",
    "UNKNOWN_REGISTER.yaml": "unknowns: []\n",
    "RISK_REGISTER.yaml": "risks: []\n",
    "WAIVER_REGISTER.yaml": "waivers: []\n",
    "EVIDENCE_CATALOG.yaml": "evidence: []\n",
    "DO_NOT_BUILD.yaml": "do_not_build: []\n",
    "CURRENT_STATE_DELTA.yaml": "{}",
    "WORKSTREAMS.yaml": "workstreams: []\n",
    "DEPENDENCY_GRAPH.yaml": "edges: []\n",
    "EXECUTION_WAVES.yaml": "waves: []\n",
    "TASK_CARDS.yaml": "tasks: []\n",
    "CONVERGENCE_GATES.yaml": "gates: []\n",
    "OBSERVABILITY_PLAN.yaml": "{}",
    "CUTOVER_AND_ROLLBACK.yaml": "{}",
    "SOURCE_TRACEABILITY.yaml": "{}",
}


def _write_blueprint(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "EXECUTION_INDEX.yaml").write_text(INDEX, encoding="utf-8")
    (root / "PROGRAM.yaml").write_text(PROGRAM, encoding="utf-8")
    for name, content in EMPTY_SOURCES.items():
        (root / name).write_text(content, encoding="utf-8")
    return root


@pytest.fixture()
def runtime(tmp_path: Path):
    blueprint = _write_blueprint(tmp_path / "blueprint")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    bootstrap(workspace, blueprint, TEMPLATE)
    return workspace


def _delta(classes: list[str], operations: list[dict] | None = None) -> dict:
    return {
        "classes": classes,
        "operations": operations
        or [{"op": "adapt_strategy", "target_task_id": "TASK-003", "note": "fixture"}],
    }


def _propose(workspace: Path, revision_id: str = "rev-1", **overrides) -> dict:
    kwargs = dict(
        revision_id=revision_id,
        program_id="fixture-replan-program",
        trigger_evidence_ids=["EVID-001"],
        affected_future_task_ids=["TASK-003"],
        delta=_delta(["reversible_implementation_strategy"]),
        expected_validation_effect="deterministic_local_validation",
        proposer_actor="worker-a",
    )
    kwargs.update(overrides)
    return propose(workspace, **kwargs)


def test_bootstrap_exposes_durable_plan_revision(runtime):
    plan = current_plan_revision(runtime)
    assert plan["plan_revision"] == "plan-rev-0"
    assert plan["active_replan_revision_id"] is None
    view = status(runtime)
    assert view["plan_revision"]["plan_revision"] == "plan-rev-0"


def test_propose_verify_activate_advances_plan_revision(runtime):
    proposed = _propose(runtime)
    assert proposed["status"] == "proposed"
    assert proposed["authority_containment"]["result"] == "PASS"
    assert proposed["previous_plan_revision"] == "plan-rev-0"
    assert proposed["program_lock_digest"] == current_plan_revision(runtime)["program_lock_digest"]

    verified = verify(runtime, "rev-1", verifier_actor="verifier-a")
    assert verified["status"] == "verified"
    assert verified["verifier_actor"] == "verifier-a"

    activated = activate(runtime, "rev-1", actor="controller")
    assert activated["status"] == "activated"
    assert activated["activated_at"] is not None
    plan = current_plan_revision(runtime)
    assert plan["plan_revision"] == "plan-rev-0+rev-1"
    assert plan["active_replan_revision_id"] == "rev-1"
    assert [r["status"] for r in list_revisions(runtime)] == ["activated"]


def test_proposer_may_not_verify_own_revision(runtime):
    _propose(runtime)
    with pytest.raises(ControllerError, match="proposer may not verify"):
        verify(runtime, "rev-1", verifier_actor="worker-a")


def test_activation_requires_verified_revision(runtime):
    _propose(runtime)
    with pytest.raises(ControllerError, match="not verified"):
        activate(runtime, "rev-1", actor="controller")


def test_activation_requires_controller_actor(runtime):
    _propose(runtime)
    verify(runtime, "rev-1", verifier_actor="verifier-a")
    with pytest.raises(ControllerError, match="only the Controller"):
        activate(runtime, "rev-1", actor="worker-a")


def test_authority_widening_delta_fails_closed_at_propose(runtime):
    # authorization_ceiling is the contract's permission-widening class. A
    # hostile delta is rejected before any revision file is written.
    with pytest.raises(ControllerError, match="authority containment failed"):
        _propose(runtime, revision_id="rev-wide", delta=_delta(["authorization_ceiling"]))
    assert [r["revision_id"] for r in list_revisions(runtime)] == []


def test_unknown_delta_class_fails_schema_validation(runtime):
    with pytest.raises(ControllerError, match="schema validation failed"):
        _propose(runtime, revision_id="rev-unknown", delta=_delta(["silent_edit"]))
    assert [r["revision_id"] for r in list_revisions(runtime)] == []


def test_forbidden_classes_pinned_to_canonical_contract():
    import yaml

    contract = yaml.safe_load((CORE / "shared/REPLAN_CONTRACT.yaml").read_text(encoding="utf-8"))
    assert replan.FORBIDDEN == set(contract["forbidden_authority_delta_classes"])


def test_missing_trigger_evidence_fails_closed_at_propose(runtime):
    with pytest.raises(ControllerError, match="schema validation failed"):
        _propose(runtime, trigger_evidence_ids=[])
    assert [r["revision_id"] for r in list_revisions(runtime)] == []


def test_rejection_preserves_previous_valid_plan(runtime):
    _propose(runtime)
    verify(runtime, "rev-1", verifier_actor="verifier-a")
    rejected = reject(runtime, "rev-1", actor="controller", reason="flawed trigger evidence")
    assert rejected["status"] == "rejected"
    assert rejected["rejected_reason"] == "flawed trigger evidence"
    plan = current_plan_revision(runtime)
    assert plan["plan_revision"] == "plan-rev-0"
    assert plan["active_replan_revision_id"] is None


def test_stale_revision_does_not_replace_active_plan(runtime):
    _propose(runtime, revision_id="rev-1")
    verify(runtime, "rev-1", verifier_actor="verifier-a")
    activate(runtime, "rev-1", actor="controller")

    # A revision proposed against the superseded plan revision becomes stale
    # at verification and must never displace the active plan.
    _propose(runtime, revision_id="rev-stale")
    revision = next(r for r in list_revisions(runtime) if r["revision_id"] == "rev-stale")
    assert revision["previous_plan_revision"] == "plan-rev-0+rev-1"
    # Advance the plan with an independent revision so rev-stale no longer matches.
    _propose(runtime, revision_id="rev-2")
    verify(runtime, "rev-2", verifier_actor="verifier-a")
    activate(runtime, "rev-2", actor="controller")
    with pytest.raises(ControllerError, match="stale"):
        verify(runtime, "rev-stale", verifier_actor="verifier-a")
    stale = next(r for r in list_revisions(runtime) if r["revision_id"] == "rev-stale")
    assert stale["status"] == "stale"
    assert stale["rejected_reason"] == "previous_plan_revision_mismatch"
    plan = current_plan_revision(runtime)
    assert plan["plan_revision"] == "plan-rev-0+rev-1+rev-2"


def test_revisions_are_append_only(runtime):
    _propose(runtime, revision_id="rev-1")
    verify(runtime, "rev-1", verifier_actor="verifier-a")
    activate(runtime, "rev-1", actor="controller")
    revision = json.loads(
        (runtime / "runtime/replan-revisions/rev-1.json").read_text(encoding="utf-8")
    )
    assert len(revision["revision_digest"]) == 64
    events = [
        json.loads(line)
        for line in (runtime / "ledger/events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    replan_events = [e for e in events if e["type"].startswith("REPLAN_")]
    assert [e["type"] for e in replan_events] == [
        "REPLAN_PROPOSED",
        "REPLAN_VERIFIED",
        "REPLAN_ACTIVATED",
    ]
    assert all(e["payload"]["revision_id"] == "rev-1" for e in replan_events)
    assert replan_events[2]["payload"]["plan_revision"] == "plan-rev-0+rev-1"
    assert len({e["digest"] for e in replan_events}) == 3
