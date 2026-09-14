from __future__ import annotations
from .models import CandidateRecord, ContextItem, Disposition, WorkContextPacket
from .ports import GraphMemoryQueryPort, TRAVERSABLE_DEFAULT

class ContextBudgetError(RuntimeError):
    pass

class WorkContextCompiler:
    def __init__(self, port: GraphMemoryQueryPort) -> None:
        self.port = port

    @staticmethod
    def _dedupe(records: tuple[CandidateRecord, ...]) -> tuple[CandidateRecord, ...]:
        by_id: dict[str, CandidateRecord] = {}
        for r in records:
            by_id[r.record_id] = r
        return tuple(by_id[k] for k in sorted(by_id))

    @staticmethod
    def _disposition(r: CandidateRecord) -> tuple[Disposition, str]:
        if r.lifecycle in {"retired", "superseded", "archived"}:
            return Disposition.SUPERSEDED, f"lifecycle={r.lifecycle}"
        if r.conflict_ids:
            return Disposition.CONFLICTING, "material conflict attached"
        if r.dependency_necessity >= 4:
            return Disposition.REQUIRED, "required by canonical dependency structure"
        if r.relevance >= 4 and r.authority >= 3:
            return Disposition.REQUIRED, "high task relevance and sufficient authority"
        if r.relevance >= 3:
            return Disposition.SUPPORTING, "materially improves task reasoning"
        if r.relevance >= 2:
            return Disposition.OPTIONAL, "useful if budget permits"
        return Disposition.EXCLUDED, "insufficient task relevance"

    def compile(self, objective: str, graph_snapshot_id: str, budget_tokens: int, *, depth: int = 2, search_limit: int = 100) -> WorkContextPacket:
        focal = self.port.resolve_entities(objective)
        searched = self.port.search(objective, focal, search_limit)
        expanded = self.port.traverse((r.entity_id for r in searched), TRAVERSABLE_DEFAULT, depth)
        candidates = self._dedupe(searched + expanded)
        hydrated = self._dedupe(self.port.hydrate(r.record_id for r in candidates))

        included: list[ContextItem] = []
        excluded: list[ContextItem] = []
        for record in hydrated:
            disposition, reason = self._disposition(record)
            item = ContextItem(record=record, disposition=disposition, reason=reason)
            (excluded if disposition is Disposition.EXCLUDED else included).append(item)

        critical = [i for i in included if i.disposition in {Disposition.REQUIRED, Disposition.CONFLICTING}]
        critical_tokens = sum(i.record.estimated_tokens for i in critical)
        if critical_tokens > budget_tokens:
            raise ContextBudgetError("BLOCKED_CONTEXT_BUDGET: REQUIRED + CONFLICTING exceed budget")

        ordered = sorted(included, key=lambda i: (i.disposition not in {Disposition.REQUIRED, Disposition.CONFLICTING}, -i.record.dependency_necessity, -i.record.relevance, -i.record.authority, -i.record.evidence_quality, i.record.record_id))
        used = 0
        packed: list[ContextItem] = []
        for item in ordered:
            must_keep = item.disposition in {Disposition.REQUIRED, Disposition.CONFLICTING}
            if must_keep or used + item.record.estimated_tokens <= budget_tokens:
                packed.append(item)
                used += item.record.estimated_tokens
            else:
                excluded.append(ContextItem(item.record, Disposition.EXCLUDED, "context budget"))

        return WorkContextPacket(objective=objective, focal_entities=focal, items=tuple(packed), exclusions=tuple(sorted(excluded, key=lambda x: x.record.record_id)), graph_snapshot_id=graph_snapshot_id, budget_tokens=budget_tokens, used_tokens=used)
