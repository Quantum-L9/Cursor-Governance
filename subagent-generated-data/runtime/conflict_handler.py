"""Conflict detection (law §20): conflicts must be explicit, never silently merged.

Two units in the same scope and class that assert different things conflict. When
the class is high-impact (architecture ownership, policy, invariant) the conflict
is blocking and must stop promotion until resolved (SGD-018).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .classifier import HIGH_RISK_CLASSES
from .models import GeneratedDataClass, GeneratedDataUnit

_WS = re.compile(r"\s+")


def _norm(statement: str) -> str:
    return _WS.sub(" ", statement.strip().lower())


def _scope_key(scope: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in scope.items()))


@dataclass(frozen=True, slots=True)
class Conflict:
    conflict_id: str
    unit_ids: tuple[str, ...]
    conflict_type: str
    blocking: bool
    next_action: str
    unresolved: bool = True


@dataclass
class ConflictResult:
    conflicts: list[Conflict] = field(default_factory=list)

    @property
    def blocking_conflicts(self) -> list[Conflict]:
        return [c for c in self.conflicts if c.blocking]

    def blocking_unit_ids(self) -> set[str]:
        ids: set[str] = set()
        for conflict in self.blocking_conflicts:
            ids.update(conflict.unit_ids)
        return ids


def find_conflicts(units: list[GeneratedDataUnit]) -> ConflictResult:
    groups: dict[tuple[str, tuple[tuple[str, str], ...]], list[GeneratedDataUnit]] = {}
    for unit in units:
        groups.setdefault((unit.primary_class.value, _scope_key(unit.scope)), []).append(unit)

    result = ConflictResult()
    counter = 0
    for (class_value, _scope), grouped in groups.items():
        statements = {_norm(u.statement) for u in grouped}
        if len(statements) <= 1:
            continue  # same scope + class + statement is a dedup case, not a conflict
        counter += 1
        cls = GeneratedDataClass(class_value)
        blocking = cls in HIGH_RISK_CLASSES
        result.conflicts.append(
            Conflict(
                conflict_id=f"conflict-{counter:03d}",
                unit_ids=tuple(sorted(u.unit_id for u in grouped)),
                conflict_type=f"contradictory_{class_value}",
                blocking=blocking,
                next_action=(
                    "route to designated authority for resolution"
                    if blocking
                    else "record both; resolve on recurrence or new evidence"
                ),
            )
        )
    return result
