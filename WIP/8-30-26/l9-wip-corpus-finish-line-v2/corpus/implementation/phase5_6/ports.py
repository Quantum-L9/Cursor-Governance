"""Provider-neutral query port. Implement in l9-cognitive-runtime using existing memory SDK/client."""
from __future__ import annotations
from typing import Protocol, Iterable
from .models import CandidateRecord

TRAVERSABLE_DEFAULT = frozenset({
    "DEPENDS_ON", "BLOCKED_BY", "IMPLEMENTS", "PRODUCES", "CONSUMES",
    "SUPERSEDES", "GOVERNED_BY", "VALIDATED_BY", "OWNED_BY", "MEMBER_OF",
})

class GraphMemoryQueryPort(Protocol):
    def resolve_entities(self, objective: str) -> tuple[str, ...]: ...
    def search(self, objective: str, focal_entities: tuple[str, ...], limit: int) -> tuple[CandidateRecord, ...]: ...
    def traverse(self, entity_ids: Iterable[str], edge_types: frozenset[str], depth: int) -> tuple[CandidateRecord, ...]: ...
    def hydrate(self, record_ids: Iterable[str]) -> tuple[CandidateRecord, ...]: ...
