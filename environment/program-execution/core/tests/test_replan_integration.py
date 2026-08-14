"""Long-chain bounded replanning and deterministic resume (TASK-006).

End-to-end proof: a recoverable verified discovery produces a bounded Replan
Revision, receives independent verification, is activated by the Controller,
and future execution continues under the adapted plan — without mutating the
Program Lock. Restarting from durable typed state alone (a fresh process, no
conversation) reconstructs the same authoritative next-execution contract.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[1]
TEMPLATE = CORE / "program-execution-controller-template"
sys.path.insert(0, str(TEMPLATE / "scripts"))

from pec.controller import bootstrap, next_tasks, status  # noqa: E402
from pec.replan import (  # noqa: E402
    activate,
    current_plan_revision,
    plan_adaptation,
    propose,
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
  id: fixture-long-chain
  name: Long Chain Fixture
  version: 1.0.0
  owner: fixture-owner
  definition_status: draft
  objective: Exercise long-chain bounded replanning.
  contracts:
    pair: program-execution-system.v2
    blueprint: program-execution-blueprint.v2
    controller: program-execution-controller.v2
  authority_order: []
  operating_rules:
  - program_lock_is_maximum_runtime_planning_authority
  - failed_replan_preserves_previous_valid_plan
  - unknown_blocks_only_named_dependencies
  - durable_typed_state_is_execution_authority
  terminal_verdicts: [CONVERGED, CONVERGED_WITH_NON_BLOCKING_RISKS, NOT_CONVERGED, INCONCLUSIVE]
"""

TASK_CARDS = """\
tasks:
- id: T1
  title: First task
  definition_status: ready
  wave_id: W0
  workstream_id: WS-01
  target_id: TARGET-001
  execution_kind: program_control
  objective: Seed the chain.
  risk:
    tier: T1
- id: T2
  title: Second task
  definition_status: ready
  wave_id: W0
  workstream_id: WS-01
  target_id: TARGET-001
  execution_kind: program_control
  objective: Depends on T1 in the locked plan.
  risk:
    tier: T1
- id: T3
  title: Third task
  definition_status: ready
  wave_id: W0
  workstream_id: WS-01
  target_id: TARGET-001
  execution_kind: program_control
  objective: Depends on T2 in the locked plan.
  risk:
    tier: T1
"""

EMPTY_SOURCES = {
    "EXECUTION_TARGETS.yaml": (
        "targets:\n"
        "- id: TARGET-001\n"
        "  kind: git_repository\n"
        "  repository_id: Quantum-L9/example\n"
        "  execution_mode: repo_local\n"
        "  mutability: reversible\n"
        "  environments: [local]\n"
    ),
    "AUTHORITY_REGISTRY.yaml": "authorities: []\n",
    "DECISION_REGISTER.yaml": "decisions: []\n",
    "UNKNOWN_REGISTER.yaml": "unknowns: []\n",
    "RISK_REGISTER.yaml": "risks: []\n",
    "WAIVER_REGISTER.yaml": "waivers: []\n",
    "EVIDENCE_CATALOG.yaml": "evidence: []\n",
    "DO_NOT_BUILD.yaml": "do_not_build: []\n",
    "CURRENT_STATE_DELTA.yaml": "{}",
    "WORKSTREAMS.yaml": "workstreams:\n- id: WS-01\n  name: Chain\n  owner: fixture\n",
    "DEPENDENCY_GRAPH.yaml": (
        "edges:\n- from: T1\n  to: T2\n  blocking: true\n- from: T2\n  to: T3\n  blocking: true\n"
    ),
    "EXECUTION_WAVES.yaml": "waves:\n- id: W0\n  name: all\n  task_ids: [T1, T2, T3]\n",
    "CONVERGENCE_GATES.yaml": "gates: []\n",
    "OBSERVABILITY_PLAN.yaml": "{}",
    "CUTOVER_AND_ROLLBACK.yaml": "{}",
    "SOURCE_TRACEABILITY.yaml": "{}",
}


def _write_blueprint(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "EXECUTION_INDEX.yaml").write_text(INDEX, encoding="utf-8")
    (root / "PROGRAM.yaml").write_text(PROGRAM, encoding="utf-8")
    (root / "TASK_CARDS.yaml").write_text(TASK_CARDS, encoding="utf-8")
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


def _blockers(view: dict, task_id: str) -> list[str]:
    for item in view["blocked"]:
        if item["id"] == task_id:
            return item["blockers"]
    return []


def _propose(
    workspace: Path, revision_id: str, *, classes: list[str], operations: list[dict]
) -> None:
    propose(
        workspace,
        revision_id=revision_id,
        program_id="fixture-long-chain",
        trigger_evidence_ids=["EVID-001"],
        affected_future_task_ids=["T2", "T3"],
        delta={"classes": classes, "operations": operations},
        expected_validation_effect="deterministic_local_validation",
        proposer_actor="worker-a",
    )
    verify(workspace, revision_id, verifier_actor="verifier-a")
    activate(workspace, revision_id, actor="controller")


def _pec_cli(workspace: Path, command: str) -> dict:
    """Drive the Controller CLI in a fresh process: durable state only."""
    proc = subprocess.run(
        [sys.executable, str(TEMPLATE / "scripts/pec.py"), command, "--workspace", str(workspace)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_recoverable_discovery_adapts_future_execution(runtime):
    before = next_tasks(runtime)
    assert [item["id"] for item in before["ready"]] == ["T1"]
    assert "dependency_not_complete:T1" in _blockers(before, "T2")
    assert "dependency_not_complete:T2" in _blockers(before, "T3")

    # Verified evidence discovers T2's dependency on T1 was spurious; the
    # revision is independently verified and Controller-activated.
    _propose(
        runtime,
        "rev-reorder",
        classes=["reorder_where_deps_permit"],
        operations=[
            {
                "op": "reorder",
                "target_task_id": "T2",
                "remove_dependencies": ["T1"],
                "note": "verified evidence: T2 reads no T1 artifact",
            }
        ],
    )

    plan = current_plan_revision(runtime)
    assert plan["active_replan_revision_id"] == "rev-reorder"
    # The Program Lock itself is untouched: T2 still lists T1 in the lock.
    lock = json.loads((runtime / "runtime/program-lock.json").read_text(encoding="utf-8"))
    locked_t2 = next(t for t in lock["tasks"] if t["id"] == "T2")
    assert locked_t2["dependencies"] == ["T1"]

    after = next_tasks(runtime)
    assert "dependency_not_complete:T1" not in _blockers(after, "T2")
    assert "dependency_not_complete:T2" in _blockers(after, "T3")
    adaptation = plan_adaptation(runtime)
    assert adaptation["dependency_overrides"]["T2"] == {"add": [], "remove": ["T1"]}


def test_scoped_unknown_blocks_only_named_dependencies(runtime):
    _propose(
        runtime,
        "rev-unknown",
        classes=["scoped_runtime_unknown"],
        operations=[
            {
                "op": "add_unknown",
                "target_task_id": "T3",
                "unknown_id": "UNK-RT-1",
                "blocked_task_ids": ["T3"],
                "note": "runtime discovery scoped to T3",
            }
        ],
    )
    view = next_tasks(runtime)
    assert "scoped_runtime_unknown:UNK-RT-1" in _blockers(view, "T3")
    assert _blockers(view, "T2") == ["dependency_not_complete:T1"]


def test_future_task_split_appears_under_parent_authority(runtime):
    _propose(
        runtime,
        "rev-split",
        classes=["split_task_into_children"],
        operations=[{"op": "split", "target_task_id": "T3", "child_task_ids": ["T3a", "T3b"]}],
    )
    view = next_tasks(runtime)
    children = view["runtime_split_children"]
    assert [child["id"] for child in children] == ["T3a", "T3b"]
    for child in children:
        assert child["runtime_only"] is True
        assert child["parent_task_id"] == "T3"
        assert child["parent_authority"] == {}
    status_view = status(runtime)
    assert status_view["plan_revision"]["active_replan_revision_id"] == "rev-split"


def test_crash_resume_reconstructs_same_authority_from_durable_state(runtime):
    _propose(
        runtime,
        "rev-reorder",
        classes=["reorder_where_deps_permit"],
        operations=[{"op": "reorder", "target_task_id": "T2", "remove_dependencies": ["T1"]}],
    )
    in_process = {
        "plan_revision": current_plan_revision(runtime)["plan_revision"],
        "active": current_plan_revision(runtime)["active_replan_revision_id"],
        "next": next_tasks(runtime),
    }
    # Fresh process: only the workspace path is known; no conversation.
    resumed_plan = _pec_cli(runtime, "plan-revision")
    resumed_next = _pec_cli(runtime, "next")
    assert resumed_plan["plan_revision"] == in_process["plan_revision"]
    assert resumed_plan["active_replan_revision_id"] == in_process["active"]
    assert resumed_next["ready"] == in_process["next"]["ready"]
    assert resumed_next["blocked"] == in_process["next"]["blocked"]
    assert resumed_next["runtime_split_children"] == in_process["next"]["runtime_split_children"]


def test_historical_receipts_are_immutable_across_resume(runtime):
    _propose(
        runtime,
        "rev-1",
        classes=["reversible_implementation_strategy"],
        operations=[{"op": "adapt_strategy", "target_task_id": "T2", "note": "fixture"}],
    )
    revision_path = runtime / "runtime/replan-revisions/rev-1.json"
    ledger_path = runtime / "ledger/events.jsonl"
    before = (revision_path.read_bytes(), ledger_path.read_bytes())
    _pec_cli(runtime, "status")
    _pec_cli(runtime, "next")
    after = (revision_path.read_bytes(), ledger_path.read_bytes())
    assert after == before
