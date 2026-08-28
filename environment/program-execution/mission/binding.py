"""Mission Program Binding: exact, immutable, non-circular.

Authority: ADR-0026; ``MISSION_PROGRAM_BINDING_CONTRACT``.

A binding pins one exact Mission Revision to one exact Program / Blueprint
identity. It is constructed from an already-parsed immutable :class:`Mission`,
never from a caller-supplied digest, so a caller cannot claim authority the
Mission does not carry. It resolves no mutable Mission state and creates no
runtime.

Ordering matters and is not decorative::

    Blueprint -> compute blueprint_digest -> Mission Program Binding

The binding references ``blueprint_digest``, so it must exist outside the
content domain that digest covers. Storing it inside the Blueprint would make
the Blueprint's own identity depend on a document that names it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from jsonschema import Draft202012Validator
from mission import Mission, format_checker, freeze, thaw

MISSION_ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = MISSION_ROOT / "schemas" / "mission-program-binding.schema.json"

SCHEMA_ID = "l9.program-execution.mission-program-binding.v1"
BINDING_ID_RE = re.compile(r"^MPB-[A-Z0-9-]+$")
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")

#: What the Controller may read. It may not mutate the binding, rebind the
#: Program, change the Mission revision, or declare a Mission verdict.
CONTROLLER_PROJECTION_FIELDS = (
    "mission_id",
    "mission_revision",
    "mission_digest",
    "binding_id",
)


class BindingError(ValueError):
    """A Mission Program Binding is invalid."""


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=format_checker())


@dataclass(frozen=True)
class MissionProgramBinding:
    """An immutable admission record. Historical bindings never change."""

    schema: str
    binding_id: str
    mission_id: str
    mission_revision: int
    mission_digest: str
    program_id: str
    blueprint_digest: str
    bound_at: str
    metadata: MappingProxyType

    def controller_projection(self) -> MappingProxyType:
        """The read-only view the Controller receives."""
        return MappingProxyType(
            {field: getattr(self, field) for field in CONTROLLER_PROJECTION_FIELDS}
        )

    def as_document(self) -> dict[str, Any]:
        document = {
            field: getattr(self, field)
            for field in (
                "schema",
                "binding_id",
                "mission_id",
                "mission_revision",
                "mission_digest",
                "program_id",
                "blueprint_digest",
                "bound_at",
            )
        }
        if self.metadata:
            document["metadata"] = thaw(self.metadata)
        return document


def bind_mission_to_program(
    mission: Mission,
    *,
    binding_id: str,
    program_id: str,
    blueprint_digest: str,
    bound_at: datetime,
    metadata: dict[str, Any] | None = None,
) -> MissionProgramBinding:
    """Bind a parsed Mission to an exact Program / Blueprint identity.

    Mission identity and digest come from ``mission``, never from the caller:
    that is what makes digest spoofing structurally impossible rather than
    merely discouraged.
    """
    if not isinstance(mission, Mission):
        raise BindingError("binding requires an already-parsed immutable Mission")
    if not BINDING_ID_RE.match(binding_id or ""):
        raise BindingError(f"invalid binding_id {binding_id!r}")
    if not str(program_id or "").strip():
        raise BindingError("program_id must not be empty")
    if not DIGEST_RE.match(blueprint_digest or ""):
        raise BindingError(f"invalid blueprint_digest {blueprint_digest!r}")
    if not isinstance(bound_at, datetime) or bound_at.tzinfo is None:
        raise BindingError("bound_at must be an explicit timezone-aware UTC datetime")

    document = {
        "schema": SCHEMA_ID,
        "binding_id": binding_id,
        "mission_id": mission.mission_id,
        "mission_revision": mission.mission_revision,
        "mission_digest": mission.mission_digest,
        "program_id": str(program_id).strip(),
        "blueprint_digest": blueprint_digest,
        "bound_at": bound_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if metadata:
        document["metadata"] = metadata

    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "<root>"
        raise BindingError(f"schema validation failed at {location}: {first.message}")

    return MissionProgramBinding(
        schema=document["schema"],
        binding_id=document["binding_id"],
        mission_id=document["mission_id"],
        mission_revision=document["mission_revision"],
        mission_digest=document["mission_digest"],
        program_id=document["program_id"],
        blueprint_digest=document["blueprint_digest"],
        bound_at=document["bound_at"],
        metadata=freeze(metadata or {}),
    )
