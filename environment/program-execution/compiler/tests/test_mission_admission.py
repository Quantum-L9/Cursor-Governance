"""Mission Program admission: exact identity, minimal projection, explicit Intent.

Admission is the design-time pairing of an already-parsed Mission Revision with
an already-parsed Program Intent. These tests hold the three properties that
make it safe to carry a Mission through compilation: identity cannot be
claimed, the projection cannot grow, and a Program is never conjured from a
Mission.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest
import yaml
from compiler.intent import Intent, parse_intent
from compiler.mission_admission import (
    MISSION_CONTEXT_FIELDS,
    SCHEMA_ID,
    MissionAdmission,
    MissionAdmissionError,
    admit,
    mission_narrowed_ceiling,
    validate_mission_context,
)
from compiler.policy import CEILING_KEYS

PE_ROOT = Path(__file__).resolve().parents[2]
MISSION_ROOT = PE_ROOT / "mission"
FIXTURE = MISSION_ROOT / "tests" / "fixtures" / "valid_mission.yaml"
SCHEMA_PATH = PE_ROOT / "compiler" / "schemas" / "mission-context.schema.json"

if str(MISSION_ROOT) not in sys.path:
    sys.path.insert(0, str(MISSION_ROOT))

from mission import Mission, load_mission, parse_mission  # noqa: E402


def _mission(**overrides: object) -> Mission:
    document = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    document.update(overrides)
    return parse_mission(document)


def _intent(objective: str = "Make repo X achieve Y.") -> Intent:
    return parse_intent({"schema": "program-execution.intent.v1", "objective": objective})


def test_admission_carries_exact_mission_identity_from_the_parsed_mission() -> None:
    mission = load_mission(FIXTURE)
    admission = admit(mission, _intent())

    assert admission.mission_id == mission.mission_id
    assert admission.mission_revision == mission.mission_revision
    assert admission.mission_digest == mission.mission_digest
    assert admission.authority_reference() == f"MISSION:{mission.mission_id}@1"
    # The ceiling is a total map over the canonical action vocabulary, copied
    # from the Mission — not a subset the caller chose.
    assert set(admission.authority_ceiling) == set(CEILING_KEYS)
    assert dict(admission.authority_ceiling) == {
        key: mission.authority_ceiling[key] for key in CEILING_KEYS
    }


def test_admission_and_its_context_are_immutable() -> None:
    admission = admit(load_mission(FIXTURE), _intent())

    with pytest.raises(dataclasses.FrozenInstanceError):
        admission.mission_digest = "0" * 64  # type: ignore[misc]
    with pytest.raises(TypeError):
        admission.authority_ceiling["push"] = True  # type: ignore[index]

    # mission_context() hands out a fresh copy; mutating it cannot reach back.
    context = admission.mission_context()
    context["mission_digest"] = "0" * 64
    assert admission.mission_context()["mission_digest"] == admission.mission_digest


def test_mission_context_is_exactly_the_four_declared_fields() -> None:
    """A projection that can grow is a second Mission definition waiting to happen."""
    admission = admit(load_mission(FIXTURE), _intent())
    context = admission.mission_context()

    assert tuple(context) == MISSION_CONTEXT_FIELDS
    assert context["schema"] == SCHEMA_ID
    validate_mission_context(context)

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(MISSION_CONTEXT_FIELDS)
    assert set(schema["properties"]) == set(MISSION_CONTEXT_FIELDS)

    # None of the Mission's planning, budget, scope, or lifecycle semantics.
    serialized = json.dumps(context)
    mission = load_mission(FIXTURE)
    for leaked in (
        "objective",
        "acceptance",
        "budget",
        "authority",
        "constraint",
        "scope",
        "target",
        "termination",
        "owner",
        "task",
        "lease",
        "worker",
        "status",
    ):
        assert leaked not in serialized
    assert mission.objective not in serialized


def test_a_field_outside_the_projection_is_rejected() -> None:
    admission = admit(load_mission(FIXTURE), _intent())
    context = admission.mission_context()
    context["authority_ceiling"] = {"push": True}
    with pytest.raises(MissionAdmissionError):
        validate_mission_context(context)


def test_raw_or_spoofed_mission_identity_is_refused() -> None:
    """The whole defence: identity is read off a parsed Mission, never a claim."""
    mission = load_mission(FIXTURE)
    forged = {
        "schema": mission.schema,
        "mission_id": mission.mission_id,
        "mission_revision": mission.mission_revision,
        "mission_digest": "f" * 64,
        "authority_ceiling": dict.fromkeys(CEILING_KEYS, True),
    }
    with pytest.raises(MissionAdmissionError):
        admit(forged, _intent())  # type: ignore[arg-type]

    class LooksLikeAMission:
        mission_id = mission.mission_id
        mission_revision = 1
        mission_digest = "f" * 64
        authority_ceiling = dict.fromkeys(CEILING_KEYS, True)

    with pytest.raises(MissionAdmissionError):
        admit(LooksLikeAMission(), _intent())  # type: ignore[arg-type]

    # A digest that is not canonical cannot survive the schema either.
    with pytest.raises(MissionAdmissionError):
        validate_mission_context(
            {
                "schema": SCHEMA_ID,
                "mission_id": mission.mission_id,
                "mission_revision": 1,
                "mission_digest": "NOT-A-DIGEST",
            }
        )


def test_admission_requires_an_explicit_program_intent() -> None:
    """This slice pairs a Mission with a Program; it never derives one."""
    mission = load_mission(FIXTURE)

    with pytest.raises(MissionAdmissionError) as excinfo:
        admit(mission, None)  # type: ignore[arg-type]
    assert "explicit" in str(excinfo.value)

    raw_intent = {"schema": "program-execution.intent.v1", "objective": "raw"}
    with pytest.raises(MissionAdmissionError):
        admit(mission, raw_intent)  # type: ignore[arg-type]

    intent = _intent()
    assert admit(mission, intent).intent is intent


def test_mission_ceiling_only_ever_narrows() -> None:
    mission = load_mission(FIXTURE)
    admission = admit(mission, _intent())
    assert mission.authority_ceiling["push"] is True, "fixture must offer push to be a real test"

    withheld = dict.fromkeys(CEILING_KEYS, False)
    assert mission_narrowed_ceiling(withheld, admission) == withheld

    granted = dict.fromkeys(CEILING_KEYS, True)
    intersected = mission_narrowed_ceiling(granted, admission)
    assert intersected == {key: bool(mission.authority_ceiling[key]) for key in CEILING_KEYS}
    assert intersected["merge"] is False


def test_a_narrower_mission_narrows_the_program() -> None:
    ceiling = dict.fromkeys(CEILING_KEYS, True)
    ceiling.update({"push": False, "commit": False})
    admission = admit(_mission(authority_ceiling=ceiling, mission_revision=4), _intent())

    assert admission.mission_revision == 4
    resolved = mission_narrowed_ceiling(dict.fromkeys(CEILING_KEYS, True), admission)
    assert resolved["commit"] is False
    assert resolved["push"] is False
    assert resolved["inspect"] is True


def test_admission_creates_no_planning_or_runtime_state() -> None:
    """Admission is not scheduling: no tasks, leases, waves, budgets, or ledger."""
    admission = admit(load_mission(FIXTURE), _intent())
    fields = set(vars(admission))

    assert fields == {
        "mission_id",
        "mission_revision",
        "mission_digest",
        "authority_ceiling",
        "intent",
    }
    for absent in (
        "tasks",
        "waves",
        "lease",
        "leases",
        "workers",
        "budgets",
        "ledger",
        "scheduler",
        "runtime_status",
        "attempts",
        "max_programs",
    ):
        assert not hasattr(admission, absent)


def test_admission_type_is_the_only_admissible_carrier() -> None:
    """MissionAdmission is the type the resolver trusts; nothing else may pass."""
    admission = admit(load_mission(FIXTURE), _intent())
    assert isinstance(admission, MissionAdmission)
    assert type(admission).__name__ == "MissionAdmission"
