"""Mission Program Binding law.

Covers ``MISSION_PROGRAM_BINDING_CONTRACT`` and ADR-0026: an exact immutable
Mission Revision bound to an exact Program / Blueprint identity, with no
circular hashing, no live rebinding, and no Controller mutation path.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

MISSION_ROOT = Path(__file__).resolve().parents[1]
if str(MISSION_ROOT) not in sys.path:
    sys.path.insert(0, str(MISSION_ROOT))
FIXTURES = Path(__file__).resolve().parent / "fixtures"

from binding import (  # noqa: E402
    CONTROLLER_PROJECTION_FIELDS,
    SCHEMA_ID,
    BindingError,
    MissionProgramBinding,
    bind_mission_to_program,
)
from mission import Mission, load_mission, parse_mission  # noqa: E402

BLUEPRINT_DIGEST = "b" * 64
BOUND_AT = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)
BINDING_MODEL_PATH = MISSION_ROOT / "MISSION_PROGRAM_BINDING.yaml"
BINDING_SCHEMA_PATH = MISSION_ROOT / "schemas" / "mission-program-binding.schema.json"


@pytest.fixture
def mission() -> Mission:
    return load_mission(FIXTURES / "valid_mission.yaml")


def _bind(mission: Mission, **overrides: object) -> MissionProgramBinding:
    kwargs = {
        "binding_id": "MPB-GATEWAY-P1",
        "program_id": "PROG-GATEWAY-P1",
        "blueprint_digest": BLUEPRINT_DIGEST,
        "bound_at": BOUND_AT,
    }
    kwargs.update(overrides)
    return bind_mission_to_program(mission, **kwargs)


def _model() -> dict:
    return yaml.safe_load(BINDING_MODEL_PATH.read_text(encoding="utf-8"))


# --- exact identity -------------------------------------------------------


def test_binding_carries_exact_mission_and_program_identity(mission: Mission) -> None:
    binding = _bind(mission)
    assert binding.schema == SCHEMA_ID
    assert binding.binding_id == "MPB-GATEWAY-P1"
    assert binding.mission_id == mission.mission_id
    assert binding.mission_revision == mission.mission_revision
    assert binding.mission_digest == mission.mission_digest
    assert binding.program_id == "PROG-GATEWAY-P1"
    assert binding.blueprint_digest == BLUEPRINT_DIGEST
    assert binding.bound_at == "2026-08-28T12:00:00Z"


@pytest.mark.parametrize("binding_id", ["", "MPB-", "mpb-lowercase", "BINDING-1", "MPB_UNDERSCORE"])
def test_invalid_binding_id_is_rejected(mission: Mission, binding_id: str) -> None:
    with pytest.raises(BindingError):
        _bind(mission, binding_id=binding_id)


@pytest.mark.parametrize("program_id", ["", "   "])
def test_empty_program_id_is_rejected(mission: Mission, program_id: str) -> None:
    with pytest.raises(BindingError):
        _bind(mission, program_id=program_id)


@pytest.mark.parametrize("blueprint_digest", ["", "short", "B" * 64, "g" * 64, "b" * 63, "b" * 65])
def test_invalid_blueprint_digest_is_rejected(mission: Mission, blueprint_digest: str) -> None:
    with pytest.raises(BindingError):
        _bind(mission, blueprint_digest=blueprint_digest)


def test_bound_at_must_be_an_explicit_utc_timestamp(mission: Mission) -> None:
    with pytest.raises(BindingError):
        _bind(mission, bound_at=datetime(2026, 8, 28, 12, 0))  # naive
    with pytest.raises(BindingError):
        _bind(mission, bound_at="2026-08-28T12:00:00Z")

    # A non-UTC offset is accepted and normalized, not silently reinterpreted.
    eastern = datetime(2026, 8, 28, 8, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert _bind(mission, bound_at=eastern).bound_at == "2026-08-28T12:00:00Z"


def test_binding_requires_a_parsed_mission(mission: Mission) -> None:
    """A raw dict would let a caller assert authority nothing validated."""
    with pytest.raises(BindingError):
        bind_mission_to_program(
            mission.as_document(),  # type: ignore[arg-type]
            binding_id="MPB-GATEWAY-P1",
            program_id="PROG-GATEWAY-P1",
            blueprint_digest=BLUEPRINT_DIGEST,
            bound_at=BOUND_AT,
        )


# --- spoof resistance -----------------------------------------------------


def test_mission_digest_cannot_be_supplied_by_the_caller(mission: Mission) -> None:
    with pytest.raises(TypeError):
        bind_mission_to_program(
            mission,
            binding_id="MPB-GATEWAY-P1",
            program_id="PROG-GATEWAY-P1",
            blueprint_digest=BLUEPRINT_DIGEST,
            bound_at=BOUND_AT,
            mission_digest="a" * 64,  # type: ignore[call-arg]
        )


def test_binding_digest_follows_the_mission_it_was_built_from() -> None:
    """A different Mission yields a different binding digest, not a chosen one."""
    document = yaml.safe_load((FIXTURES / "valid_mission.yaml").read_text(encoding="utf-8"))
    first = parse_mission(document)

    widened = yaml.safe_load((FIXTURES / "valid_mission.yaml").read_text(encoding="utf-8"))
    widened["authority_ceiling"]["merge"] = True
    second = parse_mission(widened)

    assert first.mission_digest != second.mission_digest
    assert _bind(first).mission_digest != _bind(second).mission_digest


# --- immutability and supersession ---------------------------------------


def test_binding_is_immutable(mission: Mission) -> None:
    binding = _bind(mission)
    with pytest.raises(Exception):
        binding.program_id = "PROG-OTHER"
    with pytest.raises(Exception):
        binding.mission_digest = "a" * 64


def test_binding_metadata_is_immutable(mission: Mission) -> None:
    binding = _bind(mission, metadata={"note": "admission record"})
    with pytest.raises(TypeError):
        binding.metadata["note"] = "rewritten"


def test_document_copy_cannot_write_back(mission: Mission) -> None:
    binding = _bind(mission, metadata={"note": "admission record"})
    document = binding.as_document()
    document["program_id"] = "PROG-OTHER"
    document["metadata"]["note"] = "rewritten"
    assert binding.program_id == "PROG-GATEWAY-P1"
    assert binding.metadata["note"] == "admission record"


def test_supersession_leaves_the_historical_binding_pinned(mission: Mission) -> None:
    """Revision 2 does not reach back into the Program admitted under revision 1."""
    historical = _bind(mission)

    successor_document = mission.as_document()
    successor_document["mission_revision"] = 2
    successor_document["objective"] = "a superseding objective"
    successor = parse_mission(successor_document)

    assert successor.mission_digest != mission.mission_digest
    assert historical.mission_revision == 1
    assert historical.mission_digest == mission.mission_digest

    # A new Program requires a new binding; the old one is untouched.
    new_binding = _bind(successor, binding_id="MPB-GATEWAY-P2", program_id="PROG-GATEWAY-P2")
    assert new_binding.mission_revision == 2
    assert historical.as_document()["mission_revision"] == 1


# --- controller boundary --------------------------------------------------


def test_controller_projection_is_read_only_and_minimal(mission: Mission) -> None:
    projection = _bind(mission).controller_projection()
    assert tuple(projection) == CONTROLLER_PROJECTION_FIELDS
    assert set(projection) == {
        "mission_id",
        "mission_revision",
        "mission_digest",
        "binding_id",
    }
    with pytest.raises(TypeError):
        projection["mission_digest"] = "a" * 64
    # No objective, ceiling, budget, or acceptance leaks into the Controller.
    assert "authority_ceiling" not in projection
    assert "acceptance_criteria" not in projection


def test_model_declares_what_the_controller_may_not_do() -> None:
    controller = _model()["controller_projection"]
    assert tuple(controller["read_only_fields"]) == CONTROLLER_PROJECTION_FIELDS
    assert set(controller["controller_may_not"]) == {
        "mutate_binding",
        "rebind_program",
        "change_mission_revision",
        "declare_mission_verdict",
    }


def test_model_states_blueprint_may_narrow_but_never_widen() -> None:
    model = _model()
    assert set(model["blueprint_may_not"]) == {
        "widen_mission_scope",
        "widen_mission_authority",
        "weaken_required_mission_acceptance",
        "mutate_mission_definition",
    }
    assert "narrow_authority" in model["blueprint_may"]
    assert "operationalize_a_subset_of_mission_scope" in model["blueprint_may"]


# --- non-circular identity ------------------------------------------------


def test_blueprint_digest_self_reference_is_prohibited() -> None:
    model = _model()
    assert model["blueprint_digest_self_reference"] == "prohibited"
    assert model["mission_context_yaml_added"] is False
    ordering = model["non_circular_ordering"]
    assert ordering.index("compute blueprint_digest") < ordering.index("Mission Program Binding")
    assert ordering.index("Mission Program Binding") < ordering.index("Program Lock")
    assert ordering.index("Program Lock") < ordering.index("Controller")


def test_no_binding_document_is_stored_inside_a_blueprint() -> None:
    """The circular shape the contract names: MISSION_BINDING.yaml in a Blueprint."""
    pe_root = MISSION_ROOT.parent
    offenders = [
        path for path in pe_root.rglob("MISSION_BINDING.yaml") if "blueprint" in str(path).lower()
    ]
    assert offenders == []


def test_binding_schema_pins_the_discriminator_and_digest_format() -> None:
    schema = json.loads(BINDING_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema"]["const"] == SCHEMA_ID
    assert schema["properties"]["binding_id"]["pattern"] == "^MPB-[A-Z0-9-]+$"
    for field in ("mission_digest", "blueprint_digest"):
        assert schema["properties"][field]["pattern"] == "^[a-f0-9]{64}$"
    assert set(schema["required"]) == set(_model()["required_fields"])


def test_binding_creates_no_runtime_concept() -> None:
    text = (MISSION_ROOT / "binding.py").read_text(encoding="utf-8")
    for concept in ("MissionController", "MissionScheduler", "MissionLease", "MissionWorker"):
        assert f"class {concept}" not in text
        assert f"def {concept}" not in text
