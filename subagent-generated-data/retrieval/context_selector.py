from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from context_query import (
    ContextCandidate,
    ContextQuery,
    ContextQueryResult,
)

VISIBILITY_ORDER = {
    "campaign_local": 0,
    "repository_local": 1,
    "project_group": 2,
    "constellation_internal": 3,
    "restricted": 4,
}
ACTIVE_STATES = {
    "active",
    "accepted",
    "valid",
    "promoted",
}


@dataclass(frozen=True)
class SelectionWeights:
    retrieval_score: float = 1.0
    path_overlap: float = 0.35
    task_match: float = 0.25
    role_match: float = 0.20
    same_sha: float = 0.15
    successful_reuse: float = 0.05
    failed_reuse: float = 0.20
    context_cost: float = 0.00002


@dataclass(frozen=True)
class SelectionExclusion:
    record_id: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "record_id": self.record_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ContextSelection:
    record_id: str
    text: str
    final_score: float
    characters: int
    source: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "text": self.text,
            "final_score": self.final_score,
            "characters": self.characters,
            "source": dict(self.source),
        }


@dataclass(frozen=True)
class ContextSelectionResult:
    selected: tuple[ContextSelection, ...]
    excluded: tuple[SelectionExclusion, ...]
    budget_used_items: int
    budget_used_characters: int
    record_ids: tuple[str, ...]
    context_pack: str
    selection_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": [item.to_dict() for item in self.selected],
            "excluded": [item.to_dict() for item in self.excluded],
            "budget_used": {
                "items": self.budget_used_items,
                "characters": self.budget_used_characters,
            },
            "record_ids": list(self.record_ids),
            "context_pack": self.context_pack,
            "selection_hash": self.selection_hash,
        }


class ContextSelector:
    def __init__(
        self,
        weights: SelectionWeights | None = None,
    ) -> None:
        self.weights = weights or SelectionWeights()

    def select(
        self,
        *,
        query: ContextQuery,
        result: ContextQueryResult,
    ) -> ContextSelectionResult:
        if not result.available:
            raise RuntimeError(f"Context retrieval unavailable: {result.error}")
        excluded: list[SelectionExclusion] = []
        scored: list[tuple[float, ContextCandidate]] = []
        seen_text: set[str] = set()
        for candidate in result.candidates:
            reason = self._exclusion_reason(query, candidate)
            if reason:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        reason,
                    )
                )
                continue
            normalized = " ".join(candidate.text.split()).lower()
            if normalized in seen_text:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        "semantic_duplicate",
                    )
                )
                continue
            seen_text.add(normalized)
            scored.append(
                (
                    self._score(query, candidate),
                    candidate,
                )
            )
        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].record_id,
            )
        )
        selected: list[ContextSelection] = []
        characters = 0
        for score, candidate in scored:
            size = len(candidate.text)
            if len(selected) >= query.budget.max_items:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        "item_budget_exceeded",
                    )
                )
                continue
            if characters + size > query.budget.max_characters:
                excluded.append(
                    SelectionExclusion(
                        candidate.record_id,
                        "character_budget_exceeded",
                    )
                )
                continue
            selected.append(
                ContextSelection(
                    record_id=candidate.record_id,
                    text=candidate.text,
                    final_score=score,
                    characters=size,
                    source=candidate.to_dict(),
                )
            )
            characters += size
        context_pack = "\n\n".join(f"[memory:{item.record_id}]\n{item.text}" for item in selected)
        payload = {
            "query": query.to_dict(),
            "record_ids": [item.record_id for item in selected],
            "context_pack": context_pack,
        }
        selection_hash = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ContextSelectionResult(
            selected=tuple(selected),
            excluded=tuple(excluded),
            budget_used_items=len(selected),
            budget_used_characters=characters,
            record_ids=tuple(item.record_id for item in selected),
            context_pack=context_pack,
            selection_hash=selection_hash,
        )

    def _exclusion_reason(
        self,
        query: ContextQuery,
        candidate: ContextCandidate,
    ) -> str | None:
        if candidate.invalidated:
            return "invalidated"
        if candidate.state.lower() not in ACTIVE_STATES:
            return "inactive_state"
        if candidate.confidence < query.minimum_confidence:
            return "confidence_below_threshold"
        if candidate.epistemic_status == "contested" and not query.include_contested:
            return "contested_excluded"
        if candidate.repository not in {
            "",
            query.repository,
        }:
            return "repository_mismatch"
        if not self._visibility_allowed(
            candidate.visibility,
            query.visibility_ceiling,
        ):
            return "visibility_exceeds_ceiling"
        if not candidate.text.strip():
            return "empty_text"
        return None

    def _score(
        self,
        query: ContextQuery,
        candidate: ContextCandidate,
    ) -> float:
        query_paths = set(query.paths)
        candidate_paths = set(candidate.paths)
        path_overlap = len(query_paths & candidate_paths) / max(1, len(query_paths))
        task_match = 1.0 if query.task_type in candidate.task_types else 0.0
        role_match = 1.0 if query.role in candidate.roles else 0.0
        same_sha = 1.0 if candidate.source_sha == query.base_sha else 0.0
        return (
            candidate.score * self.weights.retrieval_score
            + path_overlap * self.weights.path_overlap
            + task_match * self.weights.task_match
            + role_match * self.weights.role_match
            + same_sha * self.weights.same_sha
            + candidate.successful_reuse_count * self.weights.successful_reuse
            - candidate.failed_reuse_count * self.weights.failed_reuse
            - len(candidate.text) * self.weights.context_cost
        )

    @staticmethod
    def _visibility_allowed(
        item_visibility: str,
        ceiling: str,
    ) -> bool:
        if item_visibility not in VISIBILITY_ORDER:
            return False
        if ceiling not in VISIBILITY_ORDER:
            return False
        return VISIBILITY_ORDER[item_visibility] <= VISIBILITY_ORDER[ceiling]
