"""Mission Program admission: design-time pairing, not scheduling.

Authority: ADR-0024, ADR-0026; ``MISSION_AUTHORITY_SCOPE_BUDGET_CONTRACT``.

Admission pairs one **already-parsed immutable Mission Revision** with one
**already-parsed Program Intent** and produces the two things design-time
compilation needs from a Mission:

* exact Mission identity — id, revision, digest — as minimal provenance;
* the Mission authority ceiling, so resolution can intersect with it.

Everything else about the Mission stays in the Mission. Objective, acceptance
criteria, budgets, constraints, scope, targets, lifecycle, owner, and metadata
are deliberately not carried: a copy of Mission semantics inside a Blueprint is
a second source of Mission truth, and supersession cannot correct a copy.

What this module is **not**:

* It does not decompose a Mission into Programs. The Program Intent arrives
  explicitly, authored elsewhere; nothing here invents, splits, or schedules
  one.
* It does not enforce aggregate Mission budgets (``max_programs``,
  ``max_parallel_programs``, cost, tokens, gate calls, duration). Those are
  ceilings over a whole Mission and need the durable cross-Program admission
  ledger, which is not built. Claiming enforcement without that ledger would be
  worse than declaring the gap.
* It does not check semantic Mission scope subset. Mission v1 scope is
  declarative; Program Execution has no machine selector grammar yet.
* It creates no runtime state, no lease, no scheduler, and no Controller.

Mission identity is read off the parsed ``Mission``, never off a caller
argument, for the same reason ``bind_mission_to_program`` does it: a
caller-supplied digest is an authority claim, and an admission that accepted one
would let a Program claim a Mission it was never admitted to.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from jsonschema import Draft202012Validator

from .intent import Intent
from .policy import CEILING_KEYS

MODULE_ROOT = Path(__file__).resolve().parent
PE_ROOT = MODULE_ROOT.parent
MISSION_ROOT = PE_ROOT / "mission"

if str(MISSION_ROOT) not in sys.path:
    sys.path.insert(0, str(MISSION_ROOT))

from mission import Mission  # noqa: E402 — official Mission model (contract §17 reuse)

SCHEMA_PATH = MODULE_ROOT / "schemas" / "mission-context.schema.json"

SCHEMA_ID = "program-execution.mission-context.v1"

#: The whole of the Mission context. Named as a tuple so a test can assert the
#: projection did not quietly grow a field.
MISSION_CONTEXT_FIELDS = ("schema", "mission_id", "mission_revision", "mission_digest")


class MissionAdmissionError(ValueError):
    """A Mission could not be admitted for design-time compilation."""


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_mission_context(context: dict[str, Any]) -> dict[str, Any]:
    """Validate a Mission context projection, or fail closed."""
    errors = sorted(_validator().iter_errors(context), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "<root>"
        raise MissionAdmissionError(f"mission_context invalid at {location}: {first.message}")
    return context


@dataclass(frozen=True)
class MissionAdmission:
    """An immutable design-time admission record.

    Frozen, and both containers are ``MappingProxyType``: a caller holding
    ``authority_ceiling`` must not be able to flip ``push`` to ``True`` between
    admission and resolution.
    """

    mission_id: str
    mission_revision: int
    mission_digest: str
    authority_ceiling: MappingProxyType
    intent: Intent

    def mission_context(self) -> dict[str, Any]:
        """The exact minimal projection, as a fresh plain dict each call."""
        return {
            "schema": SCHEMA_ID,
            "mission_id": self.mission_id,
            "mission_revision": self.mission_revision,
            "mission_digest": self.mission_digest,
        }

    def authority_reference(self) -> str:
        """Stable provenance reference naming the exact revision."""
        return f"MISSION:{self.mission_id}@{self.mission_revision}"


def admit(mission: Mission, intent: Intent) -> MissionAdmission:
    """Admit an explicit Program Intent under an exact Mission Revision.

    Both inputs must already be parsed. A raw mapping is rejected rather than
    parsed here: parsing at the admission boundary would accept whatever
    identity the caller wrote down.
    """
    if not isinstance(mission, Mission):
        raise MissionAdmissionError(
            "admission requires an already-parsed immutable Mission Revision"
        )
    if not isinstance(intent, Intent):
        raise MissionAdmissionError(
            "admission requires an explicit already-parsed Program Intent; "
            "this slice does not derive Programs from a Mission"
        )

    ceiling = {key: bool(mission.authority_ceiling[key]) for key in CEILING_KEYS}

    admission = MissionAdmission(
        mission_id=mission.mission_id,
        mission_revision=mission.mission_revision,
        mission_digest=mission.mission_digest,
        authority_ceiling=MappingProxyType(ceiling),
        intent=intent,
    )
    validate_mission_context(admission.mission_context())
    return admission


def mission_narrowed_ceiling(
    ceiling: dict[str, bool], admission: MissionAdmission
) -> dict[str, bool]:
    """Intersect an existing ceiling with the Mission ceiling, action by action.

    ``AND`` is the whole point: it can only clear bits, so a Mission that
    declares ``push: true`` cannot hand a Program push authority the policy
    profile or the Program Intent withheld. Mission narrows or leaves alone; it
    never widens.
    """
    return {
        key: bool(ceiling[key]) and bool(admission.authority_ceiling[key]) for key in CEILING_KEYS
    }


__all__ = [
    "MISSION_CONTEXT_FIELDS",
    "SCHEMA_ID",
    "MissionAdmission",
    "MissionAdmissionError",
    "admit",
    "mission_narrowed_ceiling",
    "validate_mission_context",
]
