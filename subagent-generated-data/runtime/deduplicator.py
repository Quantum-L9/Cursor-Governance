"""Deduplication (law §19): duplicate data must not create parallel truths.

Detects exact and near (normalized) duplicates within the same scope+class and
preserves source lineage. It does not delete evidence — it links duplicates to a
surviving representative so promotion routes a single active truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import GeneratedDataUnit

_WS = re.compile(r"\s+")


def _norm(statement: str) -> str:
    return _WS.sub(" ", statement.strip().lower())


def _scope_key(scope: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in scope.items()))


@dataclass(frozen=True, slots=True)
class DedupLink:
    survivor_id: str
    duplicate_id: str
    relation: str  # exact_duplicate | semantic_duplicate


@dataclass(frozen=True, slots=True)
class DedupResult:
    survivors: tuple[GeneratedDataUnit, ...]
    links: tuple[DedupLink, ...]


def deduplicate(units: list[GeneratedDataUnit]) -> DedupResult:
    survivors: list[GeneratedDataUnit] = []
    links: list[DedupLink] = []
    index: dict[tuple[str, tuple[tuple[str, str], ...], str], GeneratedDataUnit] = {}

    for unit in units:
        key = (unit.primary_class.value, _scope_key(unit.scope), _norm(unit.statement))
        existing = index.get(key)
        if existing is None:
            index[key] = unit
            survivors.append(unit)
            continue
        # Same class + scope + normalized statement -> duplicate. Keep the higher
        # confidence unit as survivor; record lineage either way.
        if unit.confidence > existing.confidence:
            survivors[survivors.index(existing)] = unit
            index[key] = unit
            links.append(DedupLink(unit.unit_id, existing.unit_id, "semantic_duplicate"))
        else:
            links.append(DedupLink(existing.unit_id, unit.unit_id, "semantic_duplicate"))

    return DedupResult(tuple(survivors), tuple(links))
