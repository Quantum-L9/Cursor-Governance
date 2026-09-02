"""Mission definition/boundary and revision/lifecycle law.

Covers the first two contracts of pack CC-PE-MISSION-FOUNDATION-V1:

* ``MISSION_DEFINITION_BOUNDARY_CONTRACT`` — identity, ownership, required
  fields, and structural rejection of planning/runtime prescription.
* ``MISSION_REVISION_LIFECYCLE_CONTRACT`` — Mission Revision (immutable
  contract identity) is a separate object from Mission Lifecycle State
  (mutable status concerning that revision).
* ``MISSION_AUTHORITY_SCOPE_BUDGET_CONTRACT`` — ceiling, scope, aggregate
  budgets, termination.
* ``MISSION_DIGEST_IMMUTABILITY_CONTRACT`` — parser, digest identity, deep
  immutability.
* ``MISSION_ACCEPTANCE_EVIDENCE_CONTRACT`` — acceptance shape and the evidence
  plane it extends.
* ``MISSION_CORE_INTEGRATION_VALIDATION_CONTRACT`` — shared core-law
  integration and the architectural negatives.

Binding lives in ``test_binding.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

MISSION_ROOT = Path(__file__).resolve().parents[1]
# APPEND, never insert(0): a module file outranks a namespace directory
# regardless of order (see compiler.mission_admission).
if str(MISSION_ROOT) not in sys.path:
    sys.path.append(str(MISSION_ROOT))
CORE_SCHEMAS = MISSION_ROOT.parent / "core" / "shared" / "schemas"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

from mission import (  # noqa: E402
    DIGEST_FIELDS,
    Mission,
    MissionError,
    canonical_json,
    compute_mission_digest,
    format_checker,
    load_mission,
    normalize_text,
    parse_mission,
    schema_registry,
)

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


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(MISSION_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        registry=schema_registry(),
        format_checker=format_checker(),
    )


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


def test_acceptance_criterion_requires_the_required_flag(
    validator: Draft202012Validator,
) -> None:
    mission = _valid()
    del mission["acceptance_criteria"][0]["required"]
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
    assert concerns["mission_identity_objective_and_acceptance"] == "mission owner"
    assert concerns["mission_program_membership"] == "mission owner"
    assert concerns["mission_acceptance_evaluation"] == "mission owner"
    assert concerns["mission_authorization_ceiling"] == "Mission Revision"
    assert concerns["mission_lifecycle_state"] == "mission owner"

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
        "mission_state_as_program_runtime_state",
        "mission_lifecycle_state_as_evidence_result_or_program_verdict",
        "program_verdict_as_mission_verdict",
        "task_completion_as_mission_acceptance",
        "mission_acceptance_as_controller_verification",
    } <= collapses


def test_state_model_and_mission_model_agree_on_the_lifecycle_domain(model: dict) -> None:
    assert (
        _core("shared/STATE_MODEL.yaml")["domains"]["mission_lifecycle_state"]["values"]
        == model["mission_lifecycle_state"]["values"]
    )


# --- MISSION_DIGEST_IMMUTABILITY_CONTRACT: parser -------------------------


@pytest.fixture
def mission() -> Mission:
    return load_mission(FIXTURES / "valid_mission.yaml")


def test_valid_fixture_parses(mission: Mission) -> None:
    assert mission.mission_id == "MISSION-L9-GATEWAY-001"
    assert mission.mission_revision == 1
    assert len(mission.targets) == 4
    assert len(mission.acceptance_criteria) == 3
    assert mission.required_criterion_ids() == (
        "MAC-GATEWAY-CONTRACT-SURFACE",
        "MAC-GATEWAY-AUTHORITY-CEILING",
        "MAC-GATEWAY-NO-SECOND-PLANE",
    )
    assert mission.constraints["max_programs"] == 8
    assert mission.budgets["max_parallel_programs"] == 3
    assert mission.termination["mode"] == "mission_acceptance"


def test_invalid_fixture_fails_closed() -> None:
    with pytest.raises(MissionError):
        load_mission(FIXTURES / "invalid_mission_with_tasks.yaml")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "l9.program-execution.mission.v2"),
        ("mission_id", "mission-lowercase"),
        ("mission_revision", 0),
        ("mission_owner", "   "),
        ("objective", "   "),
    ],
)
def test_parser_rejects_invalid_identity_and_prose(field: str, value: object) -> None:
    document = _valid()
    document[field] = value
    with pytest.raises(MissionError):
        parse_mission(document)


def test_parser_rejects_whitespace_only_acceptance_statement() -> None:
    document = _valid()
    document["acceptance_criteria"][0]["statement"] = "  \t "
    with pytest.raises(MissionError):
        parse_mission(document)


def test_parser_rejects_duplicate_criterion_ids_after_normalization() -> None:
    document = _valid()
    document["acceptance_criteria"][1]["criterion_id"] = "  MAC-GATEWAY-CONTRACT-SURFACE  "
    with pytest.raises(MissionError, match="duplicate criterion_id"):
        parse_mission(document)


def test_parser_rejects_unsupported_fields() -> None:
    document = _valid()
    document["mission_lifecycle_state"] = "ACTIVE"
    with pytest.raises(MissionError):
        parse_mission(document)


def test_parser_normalizes_intended_human_strings() -> None:
    document = _valid()
    document["mission_owner"] = "  L9   architecture \n"
    assert parse_mission(document).mission_owner == "L9 architecture"
    assert normalize_text("  a \n b  ") == "a b"


def test_date_time_format_validation_is_actually_enabled() -> None:
    """A bare FormatChecker silently passes unknown formats; this one does not."""
    assert format_checker().conforms("2026-08-28T12:00:00Z", "date-time")
    assert not format_checker().conforms("not-a-date", "date-time")

    document = _valid()
    document.setdefault("constraints", {})["deadline"] = "not-a-date"
    with pytest.raises(MissionError):
        parse_mission(document)

    document = _valid()
    document.setdefault("constraints", {})["deadline"] = "2026-12-31T23:59:59Z"
    assert parse_mission(document).constraints["deadline"] == "2026-12-31T23:59:59Z"


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("budgets", "max_parallel_programs"), 0),
        (("budgets", "max_model_cost_usd"), -1),
        (("budgets", "max_agent_tokens"), -5),
        (("constraints", "max_programs"), 0),
        (("termination", "mode"), "whenever"),
    ],
)
def test_budget_and_termination_validation(path: tuple[str, str], value: object) -> None:
    document = _valid()
    document.setdefault(path[0], {})[path[1]] = value
    with pytest.raises(MissionError):
        parse_mission(document)


def test_parser_rejects_non_finite_numbers() -> None:
    for bad in (float("nan"), float("inf"), float("-inf")):
        document = _valid()
        document["budgets"]["max_model_cost_usd"] = bad
        with pytest.raises(MissionError, match="non-finite"):
            parse_mission(document)


def test_canonical_json_refuses_nan() -> None:
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


# --- MISSION_DIGEST_IMMUTABILITY_CONTRACT: digest identity ----------------


def test_digest_is_deterministic(mission: Mission) -> None:
    assert load_mission(FIXTURES / "valid_mission.yaml").mission_digest == (mission.mission_digest)
    assert len(mission.mission_digest) == 64
    assert compute_mission_digest(_valid()) == mission.mission_digest


def test_digest_covers_exactly_the_authoritative_fields() -> None:
    assert DIGEST_FIELDS == (
        "schema",
        "mission_id",
        "mission_revision",
        "mission_owner",
        "objective",
        "targets",
        "acceptance_criteria",
        "authority_ceiling",
        "constraints",
        "budgets",
        "termination",
    )
    assert "metadata" not in DIGEST_FIELDS


@pytest.mark.parametrize("field", list(DIGEST_FIELDS))
def test_every_authoritative_change_moves_the_digest(field: str, mission: Mission) -> None:
    changed = _valid()
    mutations = {
        "schema": lambda d: d.__setitem__("schema", "l9.program-execution.mission.v1"),
        "mission_id": lambda d: d.__setitem__("mission_id", "MISSION-OTHER-001"),
        "mission_revision": lambda d: d.__setitem__("mission_revision", 2),
        "mission_owner": lambda d: d.__setitem__("mission_owner", "someone else"),
        "objective": lambda d: d.__setitem__("objective", "a different outcome"),
        "targets": lambda d: d["targets"].append("ops/scripts"),
        "acceptance_criteria": lambda d: d["acceptance_criteria"][0].__setitem__("required", False),
        "authority_ceiling": lambda d: d["authority_ceiling"].__setitem__("merge", True),
        "constraints": lambda d: d["constraints"].__setitem__("max_programs", 9),
        "budgets": lambda d: d["budgets"].__setitem__("max_gate_calls", 6000),
        "termination": lambda d: d["termination"].__setitem__("mode", "authority_boundary"),
    }
    mutations[field](changed)
    if field == "schema":  # the discriminator is fixed; identity still holds
        assert compute_mission_digest(changed) == mission.mission_digest
        return
    assert compute_mission_digest(changed) != mission.mission_digest


def test_metadata_is_excluded_from_identity(mission: Mission) -> None:
    changed = _valid()
    changed["metadata"] = {"note": "completely different annotation", "extra": [1, 2, 3]}
    assert compute_mission_digest(changed) == mission.mission_digest
    del changed["metadata"]
    assert compute_mission_digest(changed) == mission.mission_digest


# --- MISSION_DIGEST_IMMUTABILITY_CONTRACT: deep immutability --------------


def test_top_level_replacement_is_refused(mission: Mission) -> None:
    with pytest.raises(Exception):
        mission.mission_owner = "someone else"


def test_authority_ceiling_cannot_be_widened_through_a_retained_reference(
    mission: Mission,
) -> None:
    ceiling = mission.authority_ceiling
    with pytest.raises(TypeError):
        ceiling["push"] = True
    with pytest.raises(TypeError):
        mission.authority_ceiling["merge"] = True
    assert mission.authority_ceiling["merge"] is False


@pytest.mark.parametrize(
    "attribute", ["authority_ceiling", "constraints", "budgets", "termination", "metadata"]
)
def test_authoritative_mappings_are_immutable(mission: Mission, attribute: str) -> None:
    with pytest.raises(TypeError):
        getattr(mission, attribute)["injected"] = True


@pytest.mark.parametrize("attribute", ["targets", "acceptance_criteria"])
def test_authoritative_sequences_are_immutable(mission: Mission, attribute: str) -> None:
    value = getattr(mission, attribute)
    assert isinstance(value, tuple)
    with pytest.raises(TypeError):
        value[0] = "replaced"


def test_nested_collections_are_transitively_immutable(mission: Mission) -> None:
    with pytest.raises(TypeError):
        mission.acceptance_criteria[0]["required"] = False
    assert isinstance(mission.constraints["scope"]["include"], tuple)
    with pytest.raises(AttributeError):
        mission.constraints["scope"]["include"].append("everything")
    with pytest.raises(TypeError):
        mission.constraints["scope"]["include"][0] = "everything"
    with pytest.raises(TypeError):
        mission.acceptance_criteria[0]["evidence_requirements"][0]["evidence_type"] = "other"


def test_as_document_copy_cannot_write_back(mission: Mission) -> None:
    document = mission.as_document()
    document["authority_ceiling"]["push"] = False
    document["targets"].append("anything")
    assert mission.authority_ceiling["push"] is True
    assert len(mission.targets) == 4


def test_source_document_cannot_write_back(mission: Mission) -> None:
    document = _valid()
    parsed = parse_mission(document)
    document["authority_ceiling"]["merge"] = True
    document["acceptance_criteria"][0]["required"] = False
    assert parsed.authority_ceiling["merge"] is False
    assert parsed.acceptance_criteria[0]["required"] is True


# --- MISSION_AUTHORITY_SCOPE_BUDGET_CONTRACT ------------------------------


def _authority_model() -> dict:
    return yaml.safe_load(
        (MISSION_ROOT / "MISSION_AUTHORITY_MODEL.yaml").read_text(encoding="utf-8")
    )


def test_mission_ceiling_is_an_intersection_term_not_a_grant() -> None:
    model = _authority_model()
    assert model["authorization_ceiling"]["nature"].startswith("ceiling")
    intersection = model["effective_permission_intersection"]
    assert "mission_authority_ceiling" in intersection
    # Mission is one term among several, and never the only one.
    assert len(intersection) > 1
    assert "blueprint_authorization_ceiling" in intersection


def test_authority_laws_narrow_and_never_widen() -> None:
    laws = _authority_model()["laws"]
    assert "lower_layer_may_narrow_never_widen" in laws
    assert "blueprint_authority_must_remain_within_mission_authority" in laws
    assert "controller_authority_must_remain_within_blueprint_authority" in laws
    assert "capability_or_credential_availability_is_not_authorization" in laws
    assert "mission_ceiling_grants_no_new_remote_mutation_authority" in laws


def test_scope_claims_no_semantic_subset_checking() -> None:
    """v1 has no selector grammar; claiming subset enforcement would be false."""
    scope = _authority_model()["scope"]
    assert scope["semantic_subset_checking_claimed"] is False
    assert _authority_model()["admission_ledger_built"] is False


def test_aggregate_budgets_are_mission_wide() -> None:
    model = _authority_model()
    assert set(model["aggregate_budgets"]) == {
        "max_model_cost_usd",
        "max_agent_tokens",
        "max_gate_calls",
        "max_duration_seconds",
        "max_parallel_programs",
    }
    assert model["constraint_budgets"] == ["max_programs"]
    assert "Mission Admission determines" in model["admission_law"]


def test_termination_modes_and_digest_participation() -> None:
    termination = _authority_model()["termination"]
    assert set(termination["modes"]) == {"mission_acceptance", "authority_boundary"}
    assert termination["participates_in_digest_identity"] is True
    assert termination["mutable_lifecycle_state_remains_separate"] is True


# --- MISSION_ACCEPTANCE_EVIDENCE_CONTRACT ---------------------------------


def _acceptance_model() -> dict:
    return yaml.safe_load(
        (MISSION_ROOT / "MISSION_ACCEPTANCE_MODEL.yaml").read_text(encoding="utf-8")
    )


def test_criterion_result_states_and_unknown_is_non_passing() -> None:
    result = _acceptance_model()["criterion_result"]
    assert set(result["values"]) == {
        "UNSATISFIED",
        "PARTIALLY_SATISFIED",
        "SATISFIED",
        "WAIVED",
        "BLOCKED",
        "UNKNOWN",
    }
    assert result["unconditionally_passing"] == ["SATISFIED"]
    assert "UNKNOWN" in result["non_passing"]
    assert "WAIVED" in result["conditionally_passing"]


def test_criterion_result_and_verdict_bind_mission_digest() -> None:
    model = _acceptance_model()
    assert "mission_digest" in model["criterion_result"]["binds"]
    assert "mission_digest" in model["mission_verdict"]["binds"]


def test_mission_verdict_is_mission_owned_and_controller_is_advisory() -> None:
    verdict = _acceptance_model()["mission_verdict"]
    assert set(verdict["values"]) == {
        "SATISFIED",
        "NOT_SATISFIED",
        "INCONCLUSIVE",
        "CANCELLED",
    }
    assert verdict["canonical_owner"] == "mission_owner"
    assert verdict["controller_recommendation"] == "advisory_only"
    assert "validly WAIVED" in verdict["satisfied_requires"]


def test_program_and_task_completion_do_not_imply_mission_satisfaction() -> None:
    shortcuts = set(_acceptance_model()["prohibited_acceptance_shortcuts"])
    assert {
        "program_CONVERGED_implies_mission_SATISFIED",
        "program_ACCEPTED_implies_mission_SATISFIED",
        "task_COMPLETED_implies_mission_SATISFIED",
        "local_verification_implies_mission_SATISFIED",
        "worker_claim_is_mission_acceptance_evidence_by_itself",
        "unverified_model_statement_is_mission_acceptance_evidence",
    } <= shortcuts


def test_mission_evidence_extends_rather_than_forks_the_plane() -> None:
    integration = _acceptance_model()["evidence_integration"]
    assert integration["parallel_mission_evidence_plane"] is False
    assert integration["reuses_schema"] == "program-execution-system/evidence-reference.v2"
    assert "UNKNOWN_is_non_passing" in integration["preserved_properties"]


# --- MISSION_CORE_INTEGRATION_VALIDATION_CONTRACT -------------------------


def test_mission_ceiling_reaches_the_shared_authorization_model() -> None:
    model = _core("shared/AUTHORIZATION_MODEL.yaml")
    assert "mission_authority_ceiling" in model["effective_permission_intersection"]
    # The action vocabulary stays singular — Mission reuses it, never forks it.
    assert len(model["actions"]) == 10
    assert "blueprint_authority_must_remain_within_mission_authority" in model["laws"]


def test_shared_evidence_model_is_extended_not_replaced() -> None:
    model = _core("shared/EVIDENCE_MODEL.yaml")
    assert model["schema"] == "program-execution-system.evidence-model.v2"
    assert "mission" in model["classes"]
    for legacy in ("planning", "execution", "verification", "governance"):
        assert legacy in model["classes"]
    assert model["mission_acceptance"]["parallel_mission_evidence_plane"] is False
    assert model["mission_acceptance"]["binds_exact_state_via"] == "mission_digest"


def test_singular_authorization_vocabulary_across_mission_and_core() -> None:
    core_actions = set(_core("shared/AUTHORIZATION_MODEL.yaml")["actions"])
    schema = json.loads(
        (CORE_SCHEMAS / "action-authorization.schema.json").read_text(encoding="utf-8")
    )
    assert core_actions == set(schema["required"])
    mission_schema = json.loads(MISSION_SCHEMA_PATH.read_text(encoding="utf-8"))
    ceiling = mission_schema["properties"]["authority_ceiling"]
    assert ceiling["$ref"] == schema["$id"], "Mission must $ref the vocabulary, not restate it"


def test_mission_vocabulary_covers_the_integration_terms() -> None:
    terms = {term["term"] for term in _core("CANONICAL_VOCABULARY.yaml")["terms"]}
    assert {
        "Mission",
        "Mission Revision",
        "Mission Acceptance Criterion",
        "Mission Program Binding",
        "Mission Verdict",
    } <= terms
    # Existing Program Execution terms are not redefined.
    assert {"Execution Program", "Program Execution Controller", "Task Card"} <= terms


ARCHITECTURAL_NEGATIVES = (
    "MissionController",
    "MissionScheduler",
    "MissionLease",
    "MissionWorkItem",
    "MissionTaskState",
    "MissionWorker",
    "MissionRuntimeTask",
)


@pytest.mark.parametrize("concept", ARCHITECTURAL_NEGATIVES)
def test_no_second_control_plane_is_implemented(concept: str) -> None:
    """The names may be *named* as prohibitions; none may be defined."""
    for path in sorted(MISSION_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert f"class {concept}" not in text, f"{concept} defined in {path}"
        assert f"def {concept}" not in text, f"{concept} defined in {path}"


def test_mission_defines_no_compiler_or_runtime_service() -> None:
    assert not (MISSION_ROOT.parent / "compiler" / "mission_to_intent.py").exists()
    modules = {path.name for path in MISSION_ROOT.rglob("*.py")}
    assert modules == {"mission.py", "binding.py", "test_mission.py", "test_binding.py"}
