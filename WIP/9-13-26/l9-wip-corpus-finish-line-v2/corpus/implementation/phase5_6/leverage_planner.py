from __future__ import annotations
from dataclasses import replace
from .models import LeverageDimensions, PriorityClass, WorkUnit

class LeveragePlanner:
    @staticmethod
    def classify(d: LeverageDimensions, blocked: bool) -> PriorityClass:
        d.validate()
        if blocked:
            return PriorityClass.WAITING
        if d.unknown_burden >= 4:
            return PriorityClass.UNKNOWN
        if d.dependency_centrality >= 4 and d.unblock_fanout >= 4:
            return PriorityClass.FOUNDATIONAL_UNLOCK
        if d.capability_unlock >= 4 and d.effort <= 2 and d.risk <= 2:
            return PriorityClass.QUICK_HIGH_LEVERAGE
        if d.dependency_centrality >= 4:
            return PriorityClass.DEPENDENCY_REQUIRED
        if d.readiness >= 4 and d.strategic_alignment >= 3:
            return PriorityClass.READY_VALUE
        if d.strategic_alignment >= 4 and d.capability_unlock >= 4:
            return PriorityClass.STRATEGIC_BET
        if d.strategic_alignment <= 1 and d.capability_unlock <= 1:
            return PriorityClass.LOW_RETURN
        return PriorityClass.READY_VALUE

    def apply(self, unit: WorkUnit, dimensions: LeverageDimensions) -> WorkUnit:
        return replace(unit, dimensions=dimensions, priority_class=self.classify(dimensions, bool(unit.blockers)))

    @staticmethod
    def counterfactual_unlock(unit_id: str, units: tuple[WorkUnit, ...]) -> tuple[str, ...]:
        """Return work units whose explicit prerequisite set becomes satisfied if unit_id completes.

        This is intentionally pure and conservative. Production code should evaluate against current
        completion state supplied by the planning input, never mutate canonical corpus/memory state.
        """
        unlocked = []
        for u in units:
            if unit_id in u.prerequisites and len(u.prerequisites) == 1 and not u.blockers:
                unlocked.append(u.work_unit_id)
        return tuple(sorted(unlocked))
