"""Freshness and invalidation support (law §22).

Given a promoted unit's declared invalidation conditions and a set of observed
change events, compute the unit's lifecycle state. Invalid, superseded, or
archived units must not enter normal future context (SGD-016).
"""

from __future__ import annotations

from .models import GeneratedDataUnit, LifecycleState

KNOWN_CONDITIONS: frozenset[str] = frozenset(
    {
        "relevant_path_changed",
        "repository_base_changed",
        "schema_version_changed",
        "contract_version_changed",
        "policy_version_changed",
        "architecture_owner_changed",
        "dependency_upgraded",
        "contradictory_evidence_accepted",
        "failed_reuse_reported",
        "expiration_reached",
    }
)

# Change events that require recomputation rather than mere revalidation.
_RECOMPUTE_EVENTS: frozenset[str] = frozenset(
    {"architecture_owner_changed", "contradictory_evidence_accepted", "schema_version_changed"}
)


def evaluate_lifecycle(
    unit: GeneratedDataUnit,
    change_events: frozenset[str],
    *,
    superseded: bool = False,
    contested: bool = False,
) -> LifecycleState:
    if superseded:
        return LifecycleState.SUPERSEDED
    if contested:
        return LifecycleState.CONTESTED

    triggered = set(unit.invalidation_conditions) & change_events
    if not triggered:
        return LifecycleState.VALID
    if triggered & _RECOMPUTE_EVENTS:
        return LifecycleState.STALE_RECOMPUTE_REQUIRED
    return LifecycleState.STALE_REVALIDATABLE


def excluded_from_context(state: LifecycleState) -> bool:
    """Units that must not enter normal future context (law §22, §23)."""

    return state in {
        LifecycleState.INVALID,
        LifecycleState.SUPERSEDED,
        LifecycleState.ARCHIVED,
        LifecycleState.CONTESTED,
    }
