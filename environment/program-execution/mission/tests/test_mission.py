"""Mission definition/boundary and revision/lifecycle law.

Covers the first two contracts of pack CC-PE-MISSION-FOUNDATION-V1:

* ``MISSION_DEFINITION_BOUNDARY_CONTRACT`` — identity, ownership, required
  fields, and structural rejection of planning/runtime prescription.
* ``MISSION_REVISION_LIFECYCLE_CONTRACT`` — Mission Revision (immutable
  contract identity) is a separate object from Mission Lifecycle State
  (mutable status concerning that revision).

The remaining five contracts in the pack (authority/budget, digest and deep
immutability, program binding, acceptance evidence, integration validation)
are not implemented yet, so nothing here asserts their behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

MISSION_ROOT = Path(__file__).resolve().parents[1]
CORE_SCHEMAS = MISSION_ROOT.parent / "core" / "shared" / "schemas"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

MISSION_SCHEMA_PATH = MISSION_ROOT / "schemas" / "mission.schema.json"
MISSION_MODEL_PATH = MISSION_ROOT / "MISSION_MODEL.yaml"

MISSION_LIFECYCLE_VALUES = [
    "PROPOSED",
    "ACTIVE",
    "WAITING",
    "SATISFIED",
    "FAILED",
    "CANCELLED",
    "SUPERSEDED",
]

FORBIDDEN_FIELDS = (
    "tasks",
    "task_cards",
    "waves",
    "worktrees",
    "files_to_edit",
    "worker_prompts",
    "leases",
    "provider",
    "provider_ref",
    "execution_profile",
    "runtime_task_state",
)


def _registry() -> Registry:
    """Resolve ``$ref`` by ``$id`` across the shared Program Execution schemas.

    ``authority_ceiling`` refs the existing action-authorization schema rather
    than restating the ten-action vocabulary, so the action list keeps exactly
    one owner.
    """
    resources = []
    for path in sorted(CORE_SCHEMAS.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        resources.append((document["$id"], Resource.from_contents(document)))
    return Registry().with_resources(resources)


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(MISSION_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry())


@pytest.fixture(scope="module")
def model() -> dict:
    return yaml.safe_load(MISSION_MODEL_PATH.read_text(encoding="utf-8"))


def _fixture(name: str) -> dict:
    return yaml.safe_load((FIXTURES / f"{name}.yaml").read_text(encoding="utf-8"))


def _valid() -> dict:
    return _fixture("valid_mission")


# --- MISSION_DEFINITION_BOUNDARY_CONTRACT ---------------------------------


def test_valid_mission_fixture_validates(validator: Draft202012Validator) -> None:
    assert list(validator.iter_errors(_valid())) == []


def test_schema_discriminator_is_exact(validator: Draft202012Validator) -> None:
    mission = _valid()
    mission["schema"] = "l9.program-execution.mission.v2"
    assert list(validator.iter_errors(mission))


@pytest.mark.parametrize(
    "field",
    [
        "schema",
        "mission_id",
        "mission_revision",
        "mission_owner",
        "objective",
        "acceptance_criteria",
        "authority_ceiling",
    ],
)
def test_required_field_is_required(validator: Draft202012Validator, field: str) -> None:
    mission = _valid()
    del mission[field]
    assert list(validator.iter_errors(mission)), f"{field} must be required"


@pytest.mark.parametrize(
    "mission_id",
    ["MISSION-", "mission-lowercase", "PROGRAM-X", "MISSION_UNDERSCORE", "MISSION-bad"],
)
def test_invalid_mission_id_is_rejected(validator: Draft202012Validator, mission_id: str) -> None:
    mission = _valid()
    mission["mission_id"] = mission_id
    assert list(validator.iter_errors(mission))


def test_mission_revision_is_a_positive_integer(validator: Draft202012Validator) -> None:
    for bad in (0, -1, 1.5, "1"):
        mission = _valid()
        mission["mission_revision"] = bad
        assert list(validator.iter_errors(mission)), f"{bad!r} must be rejected"


def test_mission_owner_must_be_non_empty(validator: Draft202012Validator) -> None:
    mission = _valid()
    mission["mission_owner"] = ""
    assert list(validator.iter_errors(mission))


def test_acceptance_criterion_id_pattern_is_enforced(
    validator: Draft202012Validator,
) -> None:
    mission = _valid()
    mission["acceptance_criteria"][0]["criterion_id"] = "AC-001"
    assert list(validator.iter_errors(mission))


def test_authority_ceiling_reuses_the_ten_action_vocabulary(
    validator: Draft202012Validator,
) -> None:
    mission = _valid()
    del mission["authority_ceiling"]["push"]
    assert list(validator.iter_errors(mission)), "all ten actions are required"

    mission = _valid()
    mission["authority_ceiling"]["teleport"] = True
    assert list(validator.iter_errors(mission)), "unknown actions are rejected"

    mission = _valid()
    mission["authority_ceiling"]["push"] = "yes"
    assert list(validator.iter_errors(mission)), "action values are boolean"


@pytest.mark.parametrize("field", FORBIDDEN_FIELDS)
def test_planning_and_runtime_prescription_is_structurally_rejected(
    validator: Draft202012Validator, field: str
) -> None:
    mission = _valid()
    mission[field] = ["anything"]
    assert list(validator.iter_errors(mission)), f"{field} must be rejected"


@pytest.mark.parametrize("field", FORBIDDEN_FIELDS)
def test_forbidden_fields_are_not_retainable_as_metadata(
    validator: Draft202012Validator, field: str
) -> None:
    mission = _valid()
    mission["metadata"] = {field: ["anything"]}
    assert list(validator.iter_errors(mission)), f"metadata.{field} must be rejected"


def test_invalid_mission_with_tasks_fixture_is_rejected(
    validator: Draft202012Validator,
) -> None:
    errors = list(validator.iter_errors(_fixture("invalid_mission_with_tasks")))
    assert errors
    assert any("tasks" in str(error.message) for error in errors)


def test_unknown_top_level_fields_are_rejected(validator: Draft202012Validator) -> None:
    mission = _valid()
    mission["mission_lifecycle_state"] = "ACTIVE"
    assert list(validator.iter_errors(mission)), (
        "mutable lifecycle state must not live inside an immutable Mission Revision"
    )


def test_model_declares_the_contracted_ownership(model: dict) -> None:
    assert model["ownership"] == {
        "mission_definition": {"canonical_owner": "mission_owner"},
        "mission_revision": {"canonical_owner": "mission_owner"},
        "program_runtime": {"canonical_owner": "Program Execution Controller"},
        "task_runtime": {"canonical_owner": "Program Execution Controller"},
        "program_verdict": {"canonical_owner": "program_owner"},
        "mission_verdict": {"canonical_owner": "mission_owner"},
    }


def test_model_forbidden_field_list_matches_the_schema(model: dict) -> None:
    assert tuple(model["forbidden_planning_and_runtime_fields"]) == FORBIDDEN_FIELDS


def test_model_forbids_a_second_control_plane(model: dict) -> None:
    assert set(model["forbidden_concepts"]) == {
        "MissionController",
        "MissionScheduler",
        "MissionLease",
        "MissionWorkItem",
        "MissionTaskState",
        "MissionWorker",
        "MissionRuntimeTask",
    }


# --- MISSION_REVISION_LIFECYCLE_CONTRACT ----------------------------------


def test_revision_and_lifecycle_state_are_separate_objects(model: dict) -> None:
    separation = model["revision_lifecycle_separation"]
    assert separation["mission_revision"]["embedded_in_revision"] is True
    assert separation["mission_lifecycle_state"]["embedded_in_revision"] is False


def test_lifecycle_values_are_exactly_the_contracted_seven(model: dict) -> None:
    assert model["mission_lifecycle_state"]["values"] == MISSION_LIFECYCLE_VALUES


def test_lifecycle_transitions_match_the_contract(model: dict) -> None:
    assert model["mission_lifecycle_state"]["transitions"] == {
        "PROPOSED": ["ACTIVE", "CANCELLED", "SUPERSEDED"],
        "ACTIVE": ["WAITING", "SATISFIED", "FAILED", "CANCELLED", "SUPERSEDED"],
        "WAITING": ["ACTIVE", "SATISFIED", "FAILED", "CANCELLED", "SUPERSEDED"],
        "SATISFIED": [],
        "FAILED": [],
        "CANCELLED": [],
        "SUPERSEDED": [],
    }


def test_terminal_states_have_no_outbound_transitions(model: dict) -> None:
    lifecycle = model["mission_lifecycle_state"]
    for state in lifecycle["terminal_values"]:
        assert lifecycle["transitions"][state] == []


def test_every_transition_target_is_a_declared_value(model: dict) -> None:
    lifecycle = model["mission_lifecycle_state"]
    values = set(lifecycle["values"])
    assert set(lifecycle["transitions"]) == values
    for targets in lifecycle["transitions"].values():
        assert values.issuperset(targets)


def test_lifecycle_state_constraints_match_the_contract(model: dict) -> None:
    assert model["mission_lifecycle_state"]["constraints"] == {
        "SATISFIED": {"requires": ["mission_verdict_SATISFIED"]},
        "FAILED": {
            "requires": [
                "explicit_authorized_Mission_termination",
                "Mission_not_satisfied",
            ]
        },
        "CANCELLED": {"requires": ["authorized_Mission_cancellation"]},
        "SUPERSEDED": {"requires": ["successor_Mission_revision_exists"]},
    }


def test_lifecycle_laws_are_declared(model: dict) -> None:
    assert model["lifecycle_laws"] == [
        "INCONCLUSIVE_does_not_imply_terminal_state",
        "NOT_SATISFIED_does_not_by_itself_imply_FAILED",
        "Mission_state_change_does_not_directly_mutate_Program_runtime",
        "Mission_supersession_does_not_rebind_existing_Programs",
    ]


def test_lifecycle_does_not_substitute_for_existing_state_domains(model: dict) -> None:
    assert set(model["lifecycle_must_not_substitute_for"]) == {
        "program_definition_state",
        "runtime_task_state",
        "evidence_result",
        "program_verdict",
        "controller_verification_state",
    }


def test_first_pr_defines_laws_without_a_lifecycle_runtime(model: dict) -> None:
    scope = model["non_runtime_scope"]
    assert scope["defines_state_domain_and_laws"] is True
    assert scope["creates_lifecycle_runtime_service"] is False


# --- shared Program Execution core law ------------------------------------

CORE = MISSION_ROOT.parent / "core"


def _core(relative: str) -> dict:
    return yaml.safe_load((CORE / relative).read_text(encoding="utf-8"))


def test_mission_vocabulary_is_canonicalized() -> None:
    terms = {term["term"] for term in _core("CANONICAL_VOCABULARY.yaml")["terms"]}
    assert {
        "Mission",
        "Mission Revision",
        "Mission Lifecycle State",
        "Mission Acceptance Criterion",
    } <= terms


def test_mission_ownership_concerns_are_declared_without_moving_runtime() -> None:
    concerns = {
        item["concern"]: item["canonical_owner"]
        for item in _core("shared/OWNERSHIP_MATRIX.yaml")["concerns"]
    }
    assert concerns["mission_definition"] == "mission_owner"
    assert concerns["mission_revision_identity"] == "mission_owner"
    assert concerns["mission_lifecycle_state"] == "mission_owner"
    assert concerns["mission_verdict"] == "mission_owner"

    # Mission adds an outer ceiling; it never takes runtime or Program verdict.
    assert concerns["task_runtime_state"] == "Program Execution Controller"
    assert concerns["verification_verdict"] == "Program Execution Controller"
    assert concerns["final_program_verdict"] == "program owner"


def test_ownership_matrix_keeps_one_canonical_owner_per_concern() -> None:
    concerns = [item["concern"] for item in _core("shared/OWNERSHIP_MATRIX.yaml")["concerns"]]
    assert len(concerns) == len(set(concerns))


def test_mission_lifecycle_is_a_separate_state_domain() -> None:
    state_model = _core("shared/STATE_MODEL.yaml")
    domain = state_model["domains"]["mission_lifecycle_state"]
    assert domain["owner"] == "mission_owner"
    assert domain["values"] == MISSION_LIFECYCLE_VALUES

    # It is its own domain, not a widening of an existing one.
    assert state_model["domains"]["runtime_task_state"]["owner"] == ("Program Execution Controller")
    assert state_model["domains"]["program_verdict"]["owner"] == "program owner"


def test_state_model_forbids_mission_collapses() -> None:
    collapses = set(_core("shared/STATE_MODEL.yaml")["forbidden_collapses"])
    assert {
        "mission_revision_as_mutable_lifecycle_state",
        "mission_lifecycle_state_as_program_or_runtime_task_state",
        "mission_lifecycle_state_as_evidence_result_or_program_verdict",
        "program_verdict_as_mission_verdict",
    } <= collapses


def test_state_model_and_mission_model_agree_on_the_lifecycle_domain(model: dict) -> None:
    assert (
        _core("shared/STATE_MODEL.yaml")["domains"]["mission_lifecycle_state"]["values"]
        == model["mission_lifecycle_state"]["values"]
    )
