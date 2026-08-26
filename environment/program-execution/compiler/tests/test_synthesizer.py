"""Gate C — synthesis rules (contract §9-§12, §18 matrix)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from compiler.intent import parse_intent
from compiler.repo_truth import RepoTruth
from compiler.resolver import resolve
from compiler.synthesizer import AUTH_ACTIONS, RuntimeContaminationError, synthesize

AUTH_ACTIONS_SET = set(AUTH_ACTIONS)


def _resolution(tmp_path: Path) -> dict:
    truth = RepoTruth(
        root=tmp_path,
        remote="https://github.com/Quantum-L9/Cursor-Governance.git",
        revision="0123456789abcdef0123456789abcdef01234567",
        owner="Igor Beylin",
        test_command="pytest -q",
        package_manager=None,
        runtime_version="3.12",
        dpk=None,
        constraints_files=[],
        adr_files=[],
        validation_commands=["pytest -q"],
        rollback_defs=[],
        source_priority={"test_command": "prose"},
    )
    return resolve(
        parse_intent(
            {"schema": "program-execution.intent.v1", "objective": "Make repo X achieve Y."}
        ),
        truth=truth,
    )


def _synthesize(tmp_path: Path) -> Path:
    output = tmp_path / "blueprint"
    synthesize(_resolution(tmp_path), output)
    return output


def test_minimal_intent_produces_complete_required_source_set(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    index = yaml.safe_load((root / "EXECUTION_INDEX.yaml").read_text(encoding="utf-8"))
    for rel in index["required_sources"]:
        assert (root / rel).is_file(), f"missing required source: {rel}"
    assert (root / "schemas").is_dir(), "official schemas must ship with the Blueprint"


def test_complete_task_definitions_are_emitted_ready(tmp_path: Path) -> None:
    """ADR-0023: the synthesizer emits every complete task as ready; ordering
    lives in the dependency graph and waves, never in definition status."""
    root = _synthesize(tmp_path)
    cards = yaml.safe_load((root / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    assert cards["tasks"], "synthesizer produced no tasks"
    for task in cards["tasks"]:
        assert task["definition_status"] == "ready", (
            f"{task['id']} emitted {task['definition_status']!r}; complete "
            "definitions must be ready"
        )


def test_task_ceilings_are_exact_and_non_widening(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    cards = yaml.safe_load((root / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    profile = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1] / "policies" / "quantum-l9.safe-autonomy.v1.yaml"
        ).read_text(encoding="utf-8")
    )
    profile_ceiling = profile["authorization_ceiling"]
    for task in cards["tasks"]:
        ceiling = task["authorization_ceiling"]
        assert set(ceiling) == AUTH_ACTIONS_SET, f"{task['id']} ceiling keys not canonical"
        for action, allowed in ceiling.items():
            assert not (allowed and not profile_ceiling[action]), (
                f"{task['id']} widens {action} beyond the policy profile"
            )
    program_control = next(t for t in cards["tasks"] if t["execution_kind"] == "program_control")
    assert program_control["authorization_ceiling"]["local_write"] is False


def test_source_traceability_preserved(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    trace = yaml.safe_load((root / "SOURCE_TRACEABILITY.yaml").read_text(encoding="utf-8"))
    assert trace["sources"], "resolution provenance must be traced"
    for source in trace["sources"]:
        assert source["claims"], "every source must carry claims"


def test_no_controller_runtime_state_emitted(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    forbidden = (
        "attempt_receipts",
        "gate_results",
        "handoff_receipts",
        "recovery_state",
        "runtime_status",
    )
    for path in root.rglob("*.yaml"):
        if path.name == "EXECUTION_INDEX.yaml":
            continue  # official canonical_owners file names runtime owners by design
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} leaks runtime token {token}"


def test_runtime_ownership_contamination_rejected(tmp_path: Path) -> None:
    resolution = _resolution(tmp_path)
    resolution["attempts"] = [{"id": "A-1"}]
    with pytest.raises(RuntimeContaminationError):
        synthesize(resolution, tmp_path / "bp")


def test_acceptance_criteria_are_machine_verifiable(tmp_path: Path) -> None:
    """Reject synthetic criteria like 'looks correct' (contract §12)."""
    root = _synthesize(tmp_path)
    cards = yaml.safe_load((root / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    for task in cards["tasks"]:
        for acceptance in task["acceptance"]:
            text = acceptance["statement"].lower()
            assert "looks correct" not in text
            assert "seems clean" not in text
            assert "good quality" not in text
