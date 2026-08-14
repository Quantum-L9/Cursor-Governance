"""Controller handoff export with replan evidence (TASK-007)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

CORE = Path(__file__).resolve().parents[1]
REPO_ROOT = CORE.parents[2]
TEMPLATE = CORE / "program-execution-controller-template"
sys.path.insert(0, str(TEMPLATE / "scripts"))

from pec.controller import bootstrap, export_handoff  # noqa: E402
from pec.replan import activate, propose, verify  # noqa: E402
from test_replan_integration import (  # noqa: E402
    _write_blueprint,
)


@pytest.fixture()
def runtime(tmp_path: Path):
    _write_blueprint(tmp_path / "blueprint")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    bootstrap(workspace, tmp_path / "blueprint", TEMPLATE)
    return workspace


def _activate_revision(workspace: Path, revision_id: str) -> None:
    propose(
        workspace,
        revision_id=revision_id,
        program_id="fixture-long-chain",
        trigger_evidence_ids=["EVID-001"],
        affected_future_task_ids=["T2"],
        delta={
            "classes": ["reversible_implementation_strategy"],
            "operations": [{"op": "adapt_strategy", "target_task_id": "T2", "note": "fixture"}],
        },
        expected_validation_effect="deterministic_local_validation",
        proposer_actor="worker-a",
    )
    verify(workspace, revision_id, verifier_actor="verifier-a")
    activate(workspace, revision_id, actor="controller")


def test_handoff_carries_replan_and_rollback_sections(runtime):
    _activate_revision(runtime, "rev-1")
    propose(
        runtime,
        revision_id="rev-2",
        program_id="fixture-long-chain",
        trigger_evidence_ids=["EVID-001"],
        affected_future_task_ids=["T2"],
        delta={
            "classes": ["reversible_implementation_strategy"],
            "operations": [{"op": "adapt_strategy", "target_task_id": "T2", "note": "bad"}],
        },
        expected_validation_effect="deterministic_local_validation",
        proposer_actor="worker-b",
    )
    verify(runtime, "rev-2", verifier_actor="verifier-a")
    from pec.replan import reject as reject_revision

    reject_revision(runtime, "rev-2", actor="controller", reason="flawed trigger evidence")

    output = runtime / "handoff.json"
    receipt = export_handoff(runtime, "controller", output)
    assert receipt["replan"]["plan_revision"] == "plan-rev-0+rev-1"
    assert receipt["replan"]["active_replan_revision_id"] == "rev-1"
    assert len(receipt["replan"]["revisions"]) == 2
    # Failed revisions remain visible; never hidden from the owner.
    assert receipt["replan"]["failed_revisions_visible"] == ["rev-2"]
    assert len(receipt["replan"]["contract_digest"]) == 64
    assert receipt["peer_parity"]["status"] == "NOT_RUN"
    assert receipt["rollback_state"]["strategy"] == "restore_source_worktree_from_program_lock_base"
    assert receipt["rollback_state"]["program_lock_digest"] == receipt["program_digest"]
    assert receipt["rollback_state"]["worktree_isolation"] is True
    assert output.is_file()
    assert (runtime / "receipts/handoffs" / f"{receipt['handoff_id']}.json").is_file()


def test_controller_recommends_but_never_declares_convergence(runtime):
    receipt = export_handoff(runtime, "controller", runtime / "handoff.json")
    # Zero completed tasks: a controller that declared convergence here would
    # be wrong; INCONCLUSIVE is the only legal recommendation.
    assert receipt["recommended_program_verdict"] == "INCONCLUSIVE"


def test_handoff_without_projection_is_capped_at_inconclusive(runtime):
    _activate_revision(runtime, "rev-1")
    receipt = export_handoff(
        runtime, "controller", runtime / "handoff.json", repository_root=REPO_ROOT
    )
    assert receipt["peer_parity"]["status"] == "BLOCKED"
    assert "peer_accounting_missing" in receipt["peer_parity"]["failures"]
    assert receipt["recommended_program_verdict"] == "INCONCLUSIVE"


def test_handoff_with_parity_pass_records_full_peer_coverage(runtime):
    _activate_revision(runtime, "rev-1")
    from pec.replan import project

    accounting = project(
        runtime, repository_root=Path(REPO_ROOT), actor="controller", replan_revision_id="rev-1"
    )
    assert accounting["status"] == "ACTIVE"
    receipt = export_handoff(
        runtime, "controller", runtime / "handoff.json", repository_root=REPO_ROOT
    )
    assert receipt["peer_parity"]["status"] == "PASS"
    bindings = yaml.safe_load(
        (Path(REPO_ROOT) / "environment/agents/PEER_RUNTIME_BINDINGS.yaml").read_text(
            encoding="utf-8"
        )
    )
    declared = set(bindings["peers"])
    assert set(receipt["peer_parity"]["peer_coverage"]) == declared
    assert receipt["peer_parity"]["semantic_revision_digest"] is not None
    # Tasks are not completed, so the verdict stays advisory.
    assert receipt["recommended_program_verdict"] == "INCONCLUSIVE"
