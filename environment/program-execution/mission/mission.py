"""Mission Revision parser, digest, and deep-immutability model.

Authority: ADR-0024, ADR-0025, ADR-0027;
``MISSION_DIGEST_IMMUTABILITY_CONTRACT``, ``MISSION_AUTHORITY_SCOPE_BUDGET_CONTRACT``.

This module parses a Mission document into a transitively immutable object and
computes ``mission_digest``: local Program Execution contract identity for v1.
It resolves no mutable Mission state, and it is not a runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

MISSION_ROOT = Path(__file__).resolve().parent
CORE_SCHEMAS = MISSION_ROOT.parent / "core" / "shared" / "schemas"
SCHEMA_PATH = MISSION_ROOT / "schemas" / "mission.schema.json"

SCHEMA_ID = "l9.program-execution.mission.v1"
MISSION_ID_RE = re.compile(r"^MISSION-[A-Z0-9-]+$")
CRITERION_ID_RE = re.compile(r"^MAC-[A-Z0-9-]+$")

#: Digest-covered authoritative semantics. ``metadata`` is deliberately absent:
#: it cannot change authorization, scope, acceptance, budgets, termination, or
#: ownership, so it must not change identity either.
DIGEST_FIELDS = (
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

#: Strings a human authored, normalized before they reach identity so that an
#: invisible whitespace or Unicode-form difference is not a different Mission.
NORMALIZED_STRING_FIELDS = ("mission_owner", "objective")


class MissionError(ValueError):
    """A Mission document is not a valid Mission Revision."""


def format_checker() -> FormatChecker:
    """A checker that really validates ``date-time``.

    ``jsonschema`` treats an unknown format as valid, and ``date-time`` is only
    registered when ``rfc3339-validator`` is installed. Declaring
    ``format: date-time`` in the schema and passing a bare ``FormatChecker``
    would therefore claim a check that never runs.
    """
    checker = FormatChecker()

    @checker.checks("date-time", raises=(TypeError, ValueError))
    def _date_time(value: object) -> bool:
        if not isinstance(value, str):
            return True
        datetime.fromisoformat(value)
        return True

    return checker


def schema_registry() -> Registry:
    """Resolve ``$ref`` by ``$id`` across the shared Program Execution schemas.

    ``authority_ceiling`` refs the existing action-authorization schema rather
    than restating the ten actions, so the vocabulary keeps one owner.
    """
    resources = []
    for path in sorted(CORE_SCHEMAS.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        resources.append((document["$id"], Resource.from_contents(document)))
    return Registry().with_resources(resources)


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        registry=schema_registry(),
        format_checker=format_checker(),
    )


def normalize_text(value: str) -> str:
    """NFC, collapsed inner whitespace, stripped ends."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def freeze(value: Any) -> Any:
    """Recursively convert to immutable containers.

    A frozen outer dataclass is not enough: a caller holding the parsed
    ``authority_ceiling`` dict could still flip ``push`` to True.
    """
    if isinstance(value, dict):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    return value


def thaw(value: Any) -> Any:
    """Plain JSON-able copy of a frozen structure, for canonical rendering."""
    if isinstance(value, (MappingProxyType, dict)):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


def _reject_non_finite(value: Any, where: str) -> None:
    """NaN and infinities have no canonical JSON rendering."""
    if isinstance(value, bool):
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise MissionError(f"non-finite numeric value at {where}: {value!r}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{where}[{index}]")


def canonical_json(payload: Any) -> str:
    """Deterministic rendering. RFC 8785 is not required for local v1 identity."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def compute_mission_digest(document: dict[str, Any]) -> str:
    """SHA-256 over the authoritative semantics only."""
    payload = {key: thaw(document[key]) for key in DIGEST_FIELDS if key in document}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Mission:
    """A parsed, transitively immutable Mission Revision.

    Every authoritative container is a ``MappingProxyType`` or a tuple, so
    ``mission.authority_ceiling["push"] = True`` raises rather than silently
    widening authority through a retained reference.
    """

    schema: str
    mission_id: str
    mission_revision: int
    mission_owner: str
    objective: str
    targets: tuple[str, ...]
    acceptance_criteria: tuple[MappingProxyType, ...]
    authority_ceiling: MappingProxyType
    constraints: MappingProxyType
    budgets: MappingProxyType
    termination: MappingProxyType
    metadata: MappingProxyType
    mission_digest: str

    def required_criterion_ids(self) -> tuple[str, ...]:
        return tuple(
            str(item["criterion_id"]) for item in self.acceptance_criteria if item["required"]
        )

    def as_document(self) -> dict[str, Any]:
        """Plain-dict copy. Mutating it cannot affect this Mission."""
        return {
            key: thaw(getattr(self, key))
            for key in (*DIGEST_FIELDS, "metadata")
            if getattr(self, key, None) not in (None, {}, ())
            or key in ("schema", "mission_id", "mission_revision")
        }


def _normalize_document(raw: dict[str, Any]) -> dict[str, Any]:
    document = dict(raw)
    for field in NORMALIZED_STRING_FIELDS:
        if isinstance(document.get(field), str):
            document[field] = normalize_text(document[field])
    criteria = document.get("acceptance_criteria")
    if isinstance(criteria, list):
        normalized = []
        for item in criteria:
            if not isinstance(item, dict):
                normalized.append(item)
                continue
            entry = dict(item)
            for field in ("criterion_id", "statement"):
                if isinstance(entry.get(field), str):
                    entry[field] = normalize_text(entry[field])
            normalized.append(entry)
        document["acceptance_criteria"] = normalized
    termination = document.get("termination")
    if isinstance(termination, dict) and isinstance(termination.get("statement"), str):
        termination = dict(termination)
        termination["statement"] = normalize_text(termination["statement"])
        document["termination"] = termination
    return document


def _check_semantics(document: dict[str, Any]) -> None:
    """Laws the schema cannot express."""
    if document.get("schema") != SCHEMA_ID:
        raise MissionError(f"unsupported mission schema {document.get('schema')!r}")
    if not MISSION_ID_RE.match(str(document.get("mission_id", ""))):
        raise MissionError(f"invalid mission_id {document.get('mission_id')!r}")

    # Whitespace-only survives minLength before normalization.
    for field in NORMALIZED_STRING_FIELDS:
        if not str(document.get(field, "")).strip():
            raise MissionError(f"{field} must not be empty after normalization")

    seen: set[str] = set()
    for index, item in enumerate(document.get("acceptance_criteria", [])):
        criterion_id = str(item.get("criterion_id", ""))
        if not CRITERION_ID_RE.match(criterion_id):
            raise MissionError(f"invalid criterion_id {criterion_id!r}")
        if not str(item.get("statement", "")).strip():
            raise MissionError(f"acceptance_criteria[{index}] statement is empty")
        if criterion_id in seen:
            raise MissionError(f"duplicate criterion_id after normalization: {criterion_id}")
        seen.add(criterion_id)


def parse_mission(raw: dict[str, Any]) -> Mission:
    """Validate, normalize, and freeze a Mission document."""
    if not isinstance(raw, dict):
        raise MissionError("mission document must be a mapping")
    document = _normalize_document(raw)

    # Before the schema: NaN and the infinities have no canonical JSON rendering
    # at all, so "less than the minimum of 0" would be a misleading diagnosis of
    # a value that can never reach a digest.
    _reject_non_finite(document, "mission")

    errors = sorted(_validator().iter_errors(document), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.path) or "<root>"
        raise MissionError(f"schema validation failed at {location}: {first.message}")

    _check_semantics(document)

    return Mission(
        schema=document["schema"],
        mission_id=document["mission_id"],
        mission_revision=int(document["mission_revision"]),
        mission_owner=document["mission_owner"],
        objective=document["objective"],
        targets=freeze(document.get("targets", [])),
        acceptance_criteria=freeze(document["acceptance_criteria"]),
        authority_ceiling=freeze(document["authority_ceiling"]),
        constraints=freeze(document.get("constraints", {})),
        budgets=freeze(document.get("budgets", {})),
        termination=freeze(document.get("termination", {})),
        metadata=freeze(document.get("metadata", {})),
        mission_digest=compute_mission_digest(document),
    )


def load_mission(path: Path) -> Mission:
    """Parse a Mission from a YAML or JSON file."""
    import yaml

    return parse_mission(yaml.safe_load(path.read_text(encoding="utf-8")))
