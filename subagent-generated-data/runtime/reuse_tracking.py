"""Reuse event tracking (law §24): storage is not leverage; behavior change is.

A unit counts as reused only when a later governed action consumes it and it
changes behavior (SGD-012). This ledger records reuse events and computes the
effective-reuse rate used by observability (law §30).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Outcomes that count as an observable behavioral effect (law §24).
EFFECTIVE_OUTCOMES: frozenset[str] = frozenset(
    {
        "reduced_discovery",
        "accelerated_execution",
        "improved_scope_control",
        "improved_validation",
        "prevented_failure",
        "prevented_repeated_rejected_work",
        "improved_context",
        "improved_routing",
        "improved_architecture_understanding",
        "improved_contract_precision",
        "improved_next_action_selection",
    }
)

_NULL_OUTCOMES: frozenset[str] = frozenset(
    {"no_observable_value", "caused_confusion", "stale", "incorrect"}
)


@dataclass(frozen=True, slots=True)
class ReuseEvent:
    unit_id: str
    consuming_campaign: str
    consuming_action: str
    consuming_agent_role: str
    injection_method: str
    outcome: str
    validity_confirmed: bool
    correction_required: bool = False

    @property
    def effective(self) -> bool:
        return self.outcome in EFFECTIVE_OUTCOMES and self.validity_confirmed


@dataclass
class ReuseLedger:
    events: list[ReuseEvent] = field(default_factory=list)

    def record(self, event: ReuseEvent) -> None:
        self.events.append(event)

    def reused_unit_ids(self) -> set[str]:
        return {e.unit_id for e in self.events}

    def effective_unit_ids(self) -> set[str]:
        return {e.unit_id for e in self.events if e.effective}

    def reuse_rate(self, promoted_unit_ids: set[str]) -> float:
        if not promoted_unit_ids:
            return 0.0
        return len(self.reused_unit_ids() & promoted_unit_ids) / len(promoted_unit_ids)

    def effective_reuse_rate(self) -> float:
        reused = self.reused_unit_ids()
        if not reused:
            return 0.0
        return len(self.effective_unit_ids()) / len(reused)

    def repeatedly_valueless(self, threshold: int = 2) -> set[str]:
        """Units whose reuse never produced value at least ``threshold`` times."""

        counts: dict[str, int] = {}
        for event in self.events:
            if event.outcome in _NULL_OUTCOMES:
                counts[event.unit_id] = counts.get(event.unit_id, 0) + 1
        return {uid for uid, n in counts.items() if n >= threshold}
