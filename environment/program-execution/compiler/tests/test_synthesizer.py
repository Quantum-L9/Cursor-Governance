"""Gate C — synthesis rules (contract §9-§12, §18 matrix)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from compiler.intent import parse_intent
from compiler.repo_truth import RepoTruth
from compiler.resolver import resolve
from compiler.synthesizer import (
    AUTH_ACTIONS,
    MISSION_CONTEXT_FILENAME,
    RuntimeContaminationError,
    synthesize,
)

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


# --- Mission-bound synthesis (ADR-0024, ADR-0026) --------------------------


def _mission(**overrides):
    import sys

    mission_root = Path(__file__).resolve().parents[2] / "mission"
    if str(mission_root) not in sys.path:
        sys.path.append(str(mission_root))
    from mission import parse_mission

    fixture = mission_root / "tests" / "fixtures" / "valid_mission.yaml"
    document = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    document.update(overrides)
    return parse_mission(document)


def _bound_resolution(tmp_path: Path) -> tuple[dict, object]:
    from compiler.mission_admission import admit

    mission = _mission()
    intent = parse_intent(
        {"schema": "program-execution.intent.v1", "objective": "Make repo X achieve Y."}
    )
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
    return resolve(intent, truth=truth, admission=admit(mission, intent)), mission


def test_mission_bound_synthesis_emits_the_exact_minimal_context(tmp_path: Path) -> None:
    resolution, mission = _bound_resolution(tmp_path)
    root = synthesize(resolution, tmp_path / "blueprint")

    context = yaml.safe_load((root / MISSION_CONTEXT_FILENAME).read_text(encoding="utf-8"))
    assert context == {
        "schema": "program-execution.mission-context.v1",
        "mission_id": mission.mission_id,
        "mission_revision": mission.mission_revision,
        "mission_digest": mission.mission_digest,
    }


def test_mission_context_participates_in_blueprint_identity(tmp_path: Path) -> None:
    """Written before write_manifest(), so its bytes reach the digest."""
    resolution, _ = _bound_resolution(tmp_path)
    root = synthesize(resolution, tmp_path / "blueprint")

    manifest = yaml.safe_load((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
    entry = next(e for e in manifest["files"] if e["path"] == MISSION_CONTEXT_FILENAME)
    import hashlib

    assert (
        entry["sha256"]
        == hashlib.sha256((root / MISSION_CONTEXT_FILENAME).read_bytes()).hexdigest()
    )

    from compiler.blueprint_validate import validate

    assert validate(root, mode="instantiated").ok, "a covered context must validate"


def test_mission_planning_and_runtime_semantics_are_not_copied(tmp_path: Path) -> None:
    """The projection is provenance, never a second Mission definition."""
    resolution, mission = _bound_resolution(tmp_path)
    root = synthesize(resolution, tmp_path / "blueprint")
    text = (root / MISSION_CONTEXT_FILENAME).read_text(encoding="utf-8")

    assert mission.objective not in text
    assert mission.mission_owner not in text
    for criterion in mission.acceptance_criteria:
        assert criterion["criterion_id"] not in text
    for absent in (
        "objective",
        "acceptance_criteria",
        "authority_ceiling",
        "budgets",
        "constraints",
        "scope",
        "targets",
        "termination",
        "mission_owner",
        "metadata",
        "tasks",
        "waves",
        "lease",
        "worker",
        "provider",
        "runtime_status",
        "attempts",
    ):
        assert absent not in text


def test_unbound_synthesis_emits_no_mission_context(tmp_path: Path) -> None:
    root = _synthesize(tmp_path)
    assert not (root / MISSION_CONTEXT_FILENAME).exists()

    manifest = yaml.safe_load((root / "MANIFEST.yaml").read_text(encoding="utf-8"))
    assert MISSION_CONTEXT_FILENAME not in {entry["path"] for entry in manifest["files"]}

    from compiler.blueprint_validate import validate

    assert validate(root, mode="instantiated").ok, "unbound behaviour is unchanged"


def _truth(tmp_path: Path, **overrides) -> RepoTruth:
    fields = dict(
        root=tmp_path,
        remote="https://github.com/Other-Org/Some-Repo.git",
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
    fields.update(overrides)
    return RepoTruth(**fields)


def _resolve(tmp_path: Path, **overrides) -> dict:
    return resolve(
        parse_intent(
            {"schema": "program-execution.intent.v1", "objective": "Make repo X achieve Y."}
        ),
        truth=_truth(tmp_path, **overrides),
    )


def test_execution_target_is_the_resolved_repository_not_a_guess(tmp_path: Path) -> None:
    """The path `/x/Quantum-L9/...` used to become `Quantum-L9/Cursor-Governance`."""
    checkout = tmp_path / "Quantum-L9" / "LLM-Router"
    checkout.mkdir(parents=True)
    resolution = _resolve(checkout)
    output = tmp_path / "blueprint"
    synthesize(resolution, output)
    targets = yaml.safe_load((output / "EXECUTION_TARGETS.yaml").read_text(encoding="utf-8"))
    repository_id = targets["targets"][0]["repository_id"]
    assert repository_id == resolution["targets"][0]["repository_id"]
    assert repository_id == "Other-Org/Some-Repo"


def test_unknown_test_command_yields_an_inspection_never_an_invented_shell(
    tmp_path: Path,
) -> None:
    resolution = _resolve(tmp_path, test_command=None, validation_commands=[])
    output = tmp_path / "blueprint"
    synthesize(resolution, output)
    cards = yaml.safe_load((output / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    implementation = [task for task in cards["tasks"] if task["workstream_id"] == "WS-02"]
    assert implementation, cards
    for task in implementation:
        for validation in task["validation"]:
            assert validation["method"] == "inspection", validation
            assert "pytest" not in validation["command_or_inspection"]


def test_unobserved_revision_is_not_reported_in_sync(tmp_path: Path) -> None:
    resolution = _resolve(tmp_path, revision=None)
    output = tmp_path / "blueprint"
    synthesize(resolution, output)
    delta = yaml.safe_load((output / "CURRENT_STATE_DELTA.yaml").read_text(encoding="utf-8"))
    classification = delta["deltas"][0]["classification"]
    assert classification == "UNKNOWN", delta["deltas"][0]
