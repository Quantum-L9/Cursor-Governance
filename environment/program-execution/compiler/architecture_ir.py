"""Architecture Semantic IR: typed candidate interpretation with mandatory provenance.

Semantic items are the extractor's *candidate* reading of the architecture
source. They own no authority: an item enters executable campaign authority
only when it cites real source units, survives deterministic support checks,
and passes the coverage audit. Items without provenance are rejected here,
before any lowering.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SEMANTIC_KINDS: tuple[str, ...] = (
    "objective",
    "requirement",
    "constraint",
    "prohibition",
    "decision",
    "assumption",
    "unknown",
    "risk",
    "scope_include",
    "scope_exclude",
    "evidence_requirement",
    "implementation_seam",
    "file_seam",
    "acceptance",
    "validation",
    "negative_case",
    "dependency",
    "ordering",
    "deferral",
    "informational",
)

MATERIALITIES = ("material", "informational")
CONFIDENCES = ("high", "medium", "low")

# Kinds whose material items must acquire a campaign mapping to reach PASS.
EXECUTABLE_KINDS: frozenset[str] = frozenset(
    {
        "objective",
        "requirement",
        "constraint",
        "prohibition",
        "decision",
        "unknown",
        "risk",
        "scope_include",
        "scope_exclude",
        "evidence_requirement",
        "acceptance",
        "validation",
        "negative_case",
        "dependency",
        "ordering",
        "deferral",
        "assumption",
    }
)

# Supporting kinds refine tasks but need no standalone campaign mapping.
SUPPORTING_KINDS: frozenset[str] = frozenset({"implementation_seam", "file_seam"})

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_./-]{2,}")
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "that",
        "this",
        "must",
        "not",
        "never",
        "always",
        "shall",
        "should",
        "will",
        "into",
        "from",
        "are",
        "was",
        "were",
        "being",
        "been",
        "its",
        "any",
        "all",
        "only",
        "when",
        "where",
        "which",
        "while",
        "does",
        "did",
        "has",
        "have",
        "had",
        "can",
        "cannot",
        "may",
        "might",
        "one",
        "two",
        "per",
        "via",
        "than",
        "then",
        "them",
        "they",
        "their",
        "there",
        "here",
        "such",
        "each",
        "every",
        "both",
        "remain",
        "remains",
        "become",
        "becomes",
        "existing",
        "current",
        "initially",
        "explicit",
        "explicitly",
        "whether",
        "already",
        "once",
        "also",
        "still",
    }
)


class SemanticIrError(RuntimeError):
    pass


@dataclass(frozen=True)
class SemanticItem:
    """One extracted candidate semantic fact, bound to its source units."""

    id: str
    kind: str
    statement: str
    source_refs: tuple[str, ...]
    materiality: str = "material"
    confidence: str = "medium"
    related_semantic_ids: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()
    suggested_paths: tuple[str, ...] = ()
    suggested_tests: tuple[str, ...] = ()
    predecessor_ids: tuple[str, ...] = ()
    successor_ids: tuple[str, ...] = ()
    probeable: bool | None = None
    options: tuple[str, ...] = ()
    selected_option: str = ""
    command: str = ""
    target: str = ""
    rationale: str = ""
    risk: str = ""
    implementation_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "statement": self.statement,
            "source_refs": list(self.source_refs),
            "materiality": self.materiality,
            "confidence": self.confidence,
        }
        optional: dict[str, Any] = {
            "related_semantic_ids": list(self.related_semantic_ids),
            "conflicts_with": list(self.conflicts_with),
            "suggested_paths": list(self.suggested_paths),
            "suggested_tests": list(self.suggested_tests),
            "predecessor_ids": list(self.predecessor_ids),
            "successor_ids": list(self.successor_ids),
            "options": list(self.options),
        }
        for key, value in optional.items():
            if value:
                payload[key] = value
        for key in (
            "selected_option",
            "command",
            "target",
            "rationale",
            "risk",
            "implementation_hint",
        ):
            value = getattr(self, key)
            if value:
                payload[key] = value
        if self.probeable is not None:
            payload["probeable"] = self.probeable
        return payload


def _tuple_of_strings(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(item).strip() for item in raw if str(item).strip())


def parse_semantic_item(raw: Any) -> SemanticItem:
    """Parse and structurally validate one candidate semantic item."""
    if not isinstance(raw, dict):
        raise SemanticIrError(f"semantic item must be a mapping, got {type(raw).__name__}")
    item_id = str(raw.get("id") or "").strip()
    kind = str(raw.get("kind") or "").strip()
    statement = " ".join(str(raw.get("statement") or "").split())
    if kind not in SEMANTIC_KINDS:
        raise SemanticIrError(f"semantic item {item_id or '<unnamed>'}: unknown kind {kind!r}")
    if not statement:
        raise SemanticIrError(f"semantic item {item_id or '<unnamed>'}: empty statement")
    materiality = str(raw.get("materiality") or "material").strip()
    if materiality not in MATERIALITIES:
        raise SemanticIrError(f"semantic item {item_id}: invalid materiality {materiality!r}")
    confidence = str(raw.get("confidence") or "medium").strip()
    if confidence not in CONFIDENCES:
        confidence = "medium"
    probeable_raw = raw.get("probeable")
    return SemanticItem(
        id=item_id or "SEM-UNASSIGNED",
        kind=kind,
        statement=statement,
        source_refs=_tuple_of_strings(raw.get("source_refs")),
        materiality=materiality,
        confidence=confidence,
        related_semantic_ids=_tuple_of_strings(raw.get("related_semantic_ids")),
        conflicts_with=_tuple_of_strings(raw.get("conflicts_with")),
        suggested_paths=_tuple_of_strings(raw.get("suggested_paths")),
        suggested_tests=_tuple_of_strings(raw.get("suggested_tests")),
        predecessor_ids=_tuple_of_strings(raw.get("predecessor_ids")),
        successor_ids=_tuple_of_strings(raw.get("successor_ids")),
        probeable=bool(probeable_raw) if isinstance(probeable_raw, bool) else None,
        options=_tuple_of_strings(raw.get("options")),
        selected_option=str(raw.get("selected_option") or "").strip(),
        command=str(raw.get("command") or "").strip(),
        target=str(raw.get("target") or "").strip(),
        rationale=" ".join(str(raw.get("rationale") or "").split()),
        risk=" ".join(str(raw.get("risk") or "").split()),
        implementation_hint=" ".join(str(raw.get("implementation_hint") or "").split()),
    )


def salient_tokens(text: str) -> set[str]:
    """Content words a claim rests on. Deterministic, lowercase, stopword-free."""
    tokens = set()
    for raw in _WORD_RE.findall(text.lower()):
        token = raw.strip("./-_")
        if len(token) >= 3 and token not in _STOPWORDS:
            tokens.add(token)
    return tokens


def provenance_supported(item: SemanticItem, units_text: str) -> bool:
    """Deterministic support probe: do the cited units actually carry the claim?

    This is a guard against extractor invention, not a semantic proof: an item
    whose salient vocabulary is mostly absent from its cited source units is
    an unsupported candidate and must be repaired or discarded. Paraphrase can
    legitimately fail this probe — that routes the item into a repair round,
    never into silent acceptance.
    """
    claim = salient_tokens(item.statement)
    if not claim:
        return False
    cited = salient_tokens(units_text)
    if not cited:
        return False
    overlap = len(claim & cited) / len(claim)
    return overlap >= 0.4


def dedupe_key(item: SemanticItem) -> tuple[str, str]:
    normalized = " ".join(sorted(salient_tokens(item.statement))) or item.statement.lower()
    return (item.kind, normalized)


def merge_items(existing: SemanticItem, incoming: SemanticItem) -> SemanticItem:
    """Merge a duplicate: union provenance and hints, keep the first statement."""

    def union(a: tuple[str, ...], b: tuple[str, ...]) -> tuple[str, ...]:
        merged = list(a)
        for value in b:
            if value not in merged:
                merged.append(value)
        return tuple(merged)

    return SemanticItem(
        id=existing.id,
        kind=existing.kind,
        statement=existing.statement,
        source_refs=union(existing.source_refs, incoming.source_refs),
        materiality=(
            "material"
            if "material" in (existing.materiality, incoming.materiality)
            else existing.materiality
        ),
        confidence=existing.confidence,
        related_semantic_ids=union(existing.related_semantic_ids, incoming.related_semantic_ids),
        conflicts_with=union(existing.conflicts_with, incoming.conflicts_with),
        suggested_paths=union(existing.suggested_paths, incoming.suggested_paths),
        suggested_tests=union(existing.suggested_tests, incoming.suggested_tests),
        predecessor_ids=union(existing.predecessor_ids, incoming.predecessor_ids),
        successor_ids=union(existing.successor_ids, incoming.successor_ids),
        probeable=existing.probeable if existing.probeable is not None else incoming.probeable,
        options=existing.options or incoming.options,
        selected_option=existing.selected_option or incoming.selected_option,
        command=existing.command or incoming.command,
        target=existing.target or incoming.target,
        rationale=existing.rationale or incoming.rationale,
        risk=existing.risk or incoming.risk,
        implementation_hint=existing.implementation_hint or incoming.implementation_hint,
    )


@dataclass
class Reconciliation:
    """Deterministic merge result across chunks and repair rounds."""

    items: list[SemanticItem] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "rejected": list(self.rejected),
        }


def reconcile(
    candidates: list[SemanticItem],
    *,
    unit_text_by_id: dict[str, str],
) -> Reconciliation:
    """Normalize, dedupe, renumber, and provenance-check candidate items.

    Rejection here is loss of *candidacy*, never a runtime blocker: an item is
    dropped when it has no provenance, cites unknown source units, or fails the
    deterministic support probe. Everything else is renumbered SEM-001..N in
    first-seen order so identical extractions yield identical IR.
    """
    merged: dict[tuple[str, str], SemanticItem] = {}
    rejected: list[dict[str, Any]] = []
    original_ids: dict[tuple[str, str], list[str]] = {}
    for candidate in candidates:
        refs = tuple(ref for ref in candidate.source_refs if ref in unit_text_by_id)
        unknown_refs = tuple(ref for ref in candidate.source_refs if ref not in unit_text_by_id)
        if not candidate.source_refs:
            rejected.append(
                {
                    "item": candidate.to_dict(),
                    "reason": "no_source_provenance",
                }
            )
            continue
        if not refs:
            rejected.append(
                {
                    "item": candidate.to_dict(),
                    "reason": "unknown_source_refs",
                    "unknown_refs": list(unknown_refs),
                }
            )
            continue
        cited_text = "\n".join(unit_text_by_id[ref] for ref in refs)
        bounded = SemanticItem(
            **{**candidate.__dict__, "source_refs": refs}  # drop unknown refs, keep valid ones
        )
        if candidate.kind != "informational" and not provenance_supported(bounded, cited_text):
            rejected.append(
                {
                    "item": candidate.to_dict(),
                    "reason": "unsupported_by_cited_source",
                }
            )
            continue
        key = dedupe_key(bounded)
        if key in merged:
            merged[key] = merge_items(merged[key], bounded)
        else:
            merged[key] = bounded
        original_ids.setdefault(key, []).append(candidate.id)

    # Renumber deterministically and remap cross-references.
    id_map: dict[str, str] = {}
    renumbered: list[SemanticItem] = []
    for position, (key, item) in enumerate(merged.items(), start=1):
        new_id = f"SEM-{position:03d}"
        for old in original_ids.get(key, []):
            id_map.setdefault(old, new_id)
        id_map.setdefault(item.id, new_id)
        renumbered.append(SemanticItem(**{**item.__dict__, "id": new_id}))

    def remap(values: tuple[str, ...]) -> tuple[str, ...]:
        mapped = [id_map.get(value, "") for value in values]
        return tuple(dict.fromkeys(value for value in mapped if value))

    final: list[SemanticItem] = []
    for item in renumbered:
        final.append(
            SemanticItem(
                **{
                    **item.__dict__,
                    "related_semantic_ids": tuple(
                        ref for ref in remap(item.related_semantic_ids) if ref != item.id
                    ),
                    "conflicts_with": tuple(
                        ref for ref in remap(item.conflicts_with) if ref != item.id
                    ),
                    "predecessor_ids": tuple(
                        ref for ref in remap(item.predecessor_ids) if ref != item.id
                    ),
                    "successor_ids": tuple(
                        ref for ref in remap(item.successor_ids) if ref != item.id
                    ),
                }
            )
        )
    return Reconciliation(items=final, rejected=rejected)
