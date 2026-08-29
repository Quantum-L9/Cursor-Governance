"""Test-facing semantic expectation format. Not a second Blueprint."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

EXPECTATION_SCHEMA = "l9.pec.conformance-expectation.v1"


@dataclass(frozen=True)
class SemanticExpectation:
    fixture_id: str
    objective_contains: tuple[str, ...] = ()
    preserve: tuple[str, ...] = ()
    prohibitions: tuple[str, ...] = ()
    expected_dispositions: tuple[str, ...] = ()
    unknowns_expected: tuple[str, ...] = ()
    authority_must_not_expand: bool = True
    source_traceability_required: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> SemanticExpectation:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a mapping")
        return cls(
            fixture_id=str(data.get("fixture_id") or path.parent.name),
            objective_contains=tuple(data.get("objective_contains") or ()),
            preserve=tuple(data.get("preserve") or ()),
            prohibitions=tuple(data.get("prohibitions") or ()),
            expected_dispositions=tuple(data.get("expected_dispositions") or ()),
            unknowns_expected=tuple(data.get("unknowns_expected") or ()),
            authority_must_not_expand=bool(data.get("authority_must_not_expand", True)),
            source_traceability_required=bool(data.get("source_traceability_required", True)),
            raw=data,
        )
