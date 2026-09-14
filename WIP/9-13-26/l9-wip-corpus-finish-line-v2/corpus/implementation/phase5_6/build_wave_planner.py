from __future__ import annotations
from .models import BuildWave, BuildWavePlan, PriorityClass, WorkUnit

_ACTIVE_ORDER = {
    PriorityClass.FOUNDATIONAL_UNLOCK: 0,
    PriorityClass.QUICK_HIGH_LEVERAGE: 1,
    PriorityClass.DEPENDENCY_REQUIRED: 2,
    PriorityClass.READY_VALUE: 3,
    PriorityClass.STRATEGIC_BET: 4,
}

class BuildWavePlanner:
    def compile(self, objective: str, units: tuple[WorkUnit, ...], graph_snapshot_id: str) -> BuildWavePlan:
        by_id = {u.work_unit_id: u for u in units}
        deferred = {u.work_unit_id for u in units if u.priority_class in {
            PriorityClass.WAITING, PriorityClass.LOW_RETURN, PriorityClass.OBSOLETE, PriorityClass.UNKNOWN
        }}
        remaining = {u.work_unit_id for u in units if u.work_unit_id not in deferred}
        done: set[str] = set()
        waves: list[BuildWave] = []
        wave_no = 1

        while remaining:
            ready = [
                by_id[uid] for uid in remaining
                if set(by_id[uid].prerequisites).issubset(done)
            ]
            if not ready:
                deferred.update(remaining)
                break
            ready.sort(key=lambda u: (_ACTIVE_ORDER.get(u.priority_class, 99), u.work_unit_id))
            selected = tuple(u.work_unit_id for u in ready)
            unlocks = tuple(sorted({c for u in ready for c in u.capabilities_unlocked}))
            waves.append(BuildWave(
                wave_id=f"wave-{wave_no}",
                purpose="Execute dependency-ready highest-leverage work",
                work_unit_ids=selected,
                prerequisites=tuple(sorted(done)),
                expected_unlocks=unlocks,
            ))
            done.update(selected)
            remaining.difference_update(selected)
            wave_no += 1

        return BuildWavePlan(
            objective=objective,
            waves=tuple(waves),
            deferred=tuple(sorted(deferred)),
            graph_snapshot_id=graph_snapshot_id,
            reconsideration_triggers=(
                "canonical dependency changed",
                "material blocker changed",
                "strategic objective changed",
                "material unknown resolved",
            ),
        )
