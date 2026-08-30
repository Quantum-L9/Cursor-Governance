from __future__ import annotations
import hashlib
from .models import Disposition, WorkContextPacket, WorkUnit

class WorkUnitCompiler:
    """Reference deterministic grouping. Production implementation may use richer typed work assertions."""

    @staticmethod
    def _id(objective: str, artifacts: tuple[str, ...]) -> str:
        material = objective + "\n" + "\n".join(sorted(artifacts))
        return "wu:" + hashlib.sha256(material.encode()).hexdigest()[:16]

    def compile(self, packet: WorkContextPacket) -> tuple[WorkUnit, ...]:
        groups: dict[str, list] = {}
        for item in packet.items:
            if item.disposition in {Disposition.SUPERSEDED, Disposition.EXCLUDED, Disposition.OPTIONAL}:
                continue
            work_key = str(item.record.metadata.get("work_key") or item.record.metadata.get("project_id") or item.record.entity_id)
            groups.setdefault(work_key, []).append(item)

        units: list[WorkUnit] = []
        for key in sorted(groups):
            items = groups[key]
            artifacts = tuple(sorted({i.record.entity_id for i in items}))
            refs = tuple(sorted({e for i in items for e in i.record.evidence_refs}))
            blockers = tuple(sorted({b for i in items for b in i.record.metadata.get("blockers", ())}))
            prereqs = tuple(sorted({p for i in items for p in i.record.metadata.get("prerequisites", ())}))
            caps = tuple(sorted({c for i in items for c in i.record.metadata.get("capabilities_unlocked", ())}))
            completion = tuple(sorted({c for i in items for c in i.record.metadata.get("completion_evidence", ())}))
            objective = str(items[0].record.metadata.get("work_objective") or f"Resolve bounded work represented by {key}")
            units.append(WorkUnit(work_unit_id=self._id(objective, artifacts), title=str(items[0].record.metadata.get("work_title") or key), objective=objective, artifact_ids=artifacts, evidence_refs=refs, prerequisites=prereqs, blockers=blockers, capabilities_unlocked=caps, completion_evidence=completion))
        return tuple(units)
