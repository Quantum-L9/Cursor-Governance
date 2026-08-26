"""Architecture Semantic IR: candidate interpretation with enforced provenance.

Everything in this module treats extractor output as a *claim about the source*,
never as authority. A claim survives only if it cites source units that exist,
and only if the words of the claim are actually grounded in the text of those
units. That second check is what stops a fluent model from laundering an
invention through a real unit id: "Perplexity is the primary reasoning provider"
citing a unit that says the opposite shares an id but not a vocabulary.

Confidence is carried through for reporting and is deliberately not consulted
anywhere a decision is made. A high-confidence ungrounded item dies exactly as
fast as a low-confidence one.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
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

#: Kinds that become executable campaign work rather than context.
EXECUTABLE_KINDS = frozenset(
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
        "implementation_seam",
        "file_seam",
        "acceptance",
        "validation",
        "negative_case",
        "dependency",
        "ordering",
        "deferral",
    }
)

MATERIALITY = ("material", "informational")
CONFIDENCE = ("high", "medium", "low")

#: Below this share of distinctive statement tokens appearing in the cited
#: units, the item is not a reading of the source — it is a new claim.
GROUNDING_THRESHOLD = 0.65

_STOPWORDS = frozenset(
    """
    a an and are as at be been being but by can cannot could did do does doing for from
    had has have how if in into is it its may might must not of on only or other our
    should so some such than that the their them then there these they this those to
    upon use used using was were what when where which while who will with within would
    you your shall never always also each every more most much very when whether
    """.split()
)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_./-]{2,}")
_NEGATIONS = frozenset({"not", "never", "no", "cannot", "without", "forbidden", "prohibited"})


class SemanticIRError(ValueError):
    """Structurally invalid semantic IR (not a rejected candidate — a broken one)."""


@dataclass(frozen=True)
class SemanticItem:
    id: str
    kind: str
    statement: str
    source_refs: tuple[str, ...]
    materiality: str = "material"
    confidence: str = "medium"
    subject: str = ""
    target: str = ""
    rationale: str = ""
    implementation_hint: str = ""
    suggested_paths: tuple[str, ...] = ()
    suggested_tests: tuple[str, ...] = ()
    related_semantic_ids: tuple[str, ...] = ()
    contradicts: tuple[str, ...] = ()
    probeable: bool = False
    extra: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def material(self) -> bool:
        return self.materiality == "material"

    @property
    def executable(self) -> bool:
        return self.material and self.kind in EXECUTABLE_KINDS

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "statement": self.statement,
            "source_refs": list(self.source_refs),
            "materiality": self.materiality,
            "confidence": self.confidence,
        }
        for name in (
            "subject",
            "target",
            "rationale",
            "implementation_hint",
        ):
            value = getattr(self, name)
            if value:
                data[name] = value
        for name in (
            "suggested_paths",
            "suggested_tests",
            "related_semantic_ids",
            "contradicts",
        ):
            value = getattr(self, name)
            if value:
                data[name] = list(value)
        if self.probeable:
            data["probeable"] = True
        return data


@dataclass(frozen=True)
class RejectedItem:
    """A candidate that never acquired authority, and exactly why."""

    kind: str
    statement: str
    reason: str
    source_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "statement": self.statement,
            "reason": self.reason,
            "source_refs": list(self.source_refs),
        }


def distinctive_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in _TOKEN_RE.findall(text)
        if token.lower() not in _STOPWORDS and len(token) >= 3
    }


def grounding_score(statement: str, unit_texts: Iterable[str]) -> float:
    """Share of the statement's distinctive tokens present in the cited source.

    1.0 for a verbatim reading, 0.0 for a claim that shares no vocabulary with
    what it cites. Not a semantic judgement — a provenance one.
    """
    tokens = {_stem(token) for token in distinctive_tokens(statement)}
    if not tokens:
        return 0.0
    corpus = {_stem(token) for token in distinctive_tokens(" \n".join(unit_texts))}
    if not corpus:
        return 0.0
    return sum(1 for token in tokens if token in corpus) / len(tokens)


def _stem(token: str) -> str:
    """Symmetric, conservative suffix folding. Never prefix matching: a prefix
    rule makes "run" match "runtime" and grounding stops discriminating."""
    for suffix in ("ing", "ies", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return token


def normalize_statement(statement: str) -> str:
    return re.sub(r"\s+", " ", statement).strip()


def _negation_free(statement: str) -> str:
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", statement.lower())
        if word not in _NEGATIONS and word not in _STOPWORDS
    ]
    return " ".join(words)


def parse_items(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise SemanticIRError("semantic items must be a list")
    parsed: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise SemanticIRError("each semantic item must be an object")
        parsed.append(entry)
    return parsed


def admit(
    raw_items: Iterable[dict[str, Any]],
    *,
    unit_texts: dict[str, str],
    grounding_threshold: float = GROUNDING_THRESHOLD,
) -> tuple[list[SemanticItem], list[RejectedItem]]:
    """Filter candidates down to those the source can actually vouch for."""
    accepted: list[SemanticItem] = []
    rejected: list[RejectedItem] = []
    for entry in raw_items:
        kind = str(entry.get("kind") or "").strip()
        statement = normalize_statement(str(entry.get("statement") or ""))
        refs = tuple(
            str(ref).strip() for ref in (entry.get("source_refs") or []) if str(ref).strip()
        )
        if kind not in SEMANTIC_KINDS:
            rejected.append(RejectedItem(kind, statement, f"unknown semantic kind {kind!r}", refs))
            continue
        if not statement:
            rejected.append(RejectedItem(kind, statement, "empty statement", refs))
            continue
        if not refs:
            rejected.append(
                RejectedItem(
                    kind, statement, "no source provenance; cannot acquire authority", refs
                )
            )
            continue
        unknown_refs = [ref for ref in refs if ref not in unit_texts]
        if unknown_refs:
            rejected.append(
                RejectedItem(
                    kind,
                    statement,
                    f"source_refs name units that do not exist: {sorted(unknown_refs)}",
                    refs,
                )
            )
            continue
        materiality = str(entry.get("materiality") or "material").strip()
        if materiality not in MATERIALITY:
            materiality = "material"
        confidence = str(entry.get("confidence") or "medium").strip()
        if confidence not in CONFIDENCE:
            confidence = "medium"
        score = grounding_score(statement, [unit_texts[ref] for ref in refs])
        if materiality == "material" and score < grounding_threshold:
            rejected.append(
                RejectedItem(
                    kind,
                    statement,
                    "not grounded in cited source units "
                    f"(score {score:.2f} < {grounding_threshold})",
                    refs,
                )
            )
            continue
        accepted.append(
            SemanticItem(
                id=str(entry.get("id") or "").strip() or "SEM-PENDING",
                kind=kind,
                statement=statement,
                source_refs=refs,
                materiality=materiality,
                confidence=confidence,
                subject=normalize_statement(str(entry.get("subject") or "")),
                target=str(entry.get("target") or "").strip(),
                rationale=normalize_statement(str(entry.get("rationale") or "")),
                implementation_hint=normalize_statement(
                    str(entry.get("implementation_hint") or "")
                ),
                suggested_paths=tuple(
                    str(item).strip()
                    for item in (entry.get("suggested_paths") or [])
                    if str(item).strip()
                ),
                suggested_tests=tuple(
                    str(item).strip()
                    for item in (entry.get("suggested_tests") or [])
                    if str(item).strip()
                ),
                related_semantic_ids=tuple(
                    str(item).strip()
                    for item in (entry.get("related_semantic_ids") or [])
                    if str(item).strip()
                ),
                contradicts=tuple(
                    str(item).strip()
                    for item in (entry.get("contradicts") or [])
                    if str(item).strip()
                ),
                probeable=bool(entry.get("probeable")),
            )
        )
    return accepted, rejected


def dedupe(
    items: Iterable[SemanticItem], unit_order: dict[str, int] | None = None
) -> list[SemanticItem]:
    """Merge equivalent claims and mint stable ids in source order.

    Two extraction chunks that both saw a requirement restated across sections
    must not produce two obligations, and the merged item must cite both units.
    """
    order = unit_order or {}
    merged: dict[tuple[str, str], SemanticItem] = {}
    for item in items:
        key = (item.kind, _negation_free(item.statement) or item.statement.lower())
        current = merged.get(key)
        if current is None:
            merged[key] = item
            continue
        refs = tuple(
            sorted(
                set(current.source_refs) | set(item.source_refs),
                key=lambda r: (order.get(r, 10**6), r),
            )
        )
        merged[key] = replace(
            current,
            source_refs=refs,
            materiality="material"
            if "material" in {current.materiality, item.materiality}
            else current.materiality,
            subject=current.subject or item.subject,
            target=current.target or item.target,
            rationale=current.rationale or item.rationale,
            implementation_hint=current.implementation_hint or item.implementation_hint,
            suggested_paths=tuple(sorted(set(current.suggested_paths) | set(item.suggested_paths))),
            suggested_tests=tuple(sorted(set(current.suggested_tests) | set(item.suggested_tests))),
            related_semantic_ids=tuple(
                sorted(set(current.related_semantic_ids) | set(item.related_semantic_ids))
            ),
            contradicts=tuple(sorted(set(current.contradicts) | set(item.contradicts))),
            probeable=current.probeable or item.probeable,
        )

    def sort_key(entry: SemanticItem) -> tuple[int, str, str]:
        first = min((order.get(ref, 10**6) for ref in entry.source_refs), default=10**6)
        return (first, entry.kind, entry.statement.lower())

    ordered = sorted(merged.values(), key=sort_key)
    renumbered: list[SemanticItem] = []
    remap: dict[str, str] = {}
    for index, entry in enumerate(ordered, start=1):
        new_id = f"SEM-{index:03d}"
        remap[entry.id] = new_id
        renumbered.append(replace(entry, id=new_id))
    return [
        replace(
            entry,
            related_semantic_ids=tuple(remap.get(ref, ref) for ref in entry.related_semantic_ids),
            contradicts=tuple(remap.get(ref, ref) for ref in entry.contradicts),
        )
        for entry in renumbered
    ]


_POLARITY = {
    "requirement": 1,
    "constraint": 1,
    "scope_include": 1,
    "decision": 1,
    "prohibition": -1,
    "scope_exclude": -1,
}


@dataclass(frozen=True)
class Contradiction:
    left_id: str
    right_id: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"left": self.left_id, "right": self.right_id, "reason": self.reason}


def contradictions(items: Iterable[SemanticItem]) -> list[Contradiction]:
    """Deterministic contradiction detection over material items.

    Three signals, all mechanical: an explicit `contradicts` reference, the same
    declared subject with opposite polarity, and statements that become
    identical once negation is stripped while their kinds disagree in polarity.
    """
    material = [item for item in items if item.material]
    index = {item.id: item for item in material}
    found: dict[tuple[str, str], Contradiction] = {}

    def record(left: SemanticItem, right: SemanticItem, reason: str) -> None:
        key = tuple(sorted((left.id, right.id)))
        if key[0] == key[1] or key in found:
            return
        found[key] = Contradiction(left_id=key[0], right_id=key[1], reason=reason)

    for item in material:
        for ref in item.contradicts:
            other = index.get(ref)
            if other is not None:
                record(item, other, "extractor declared these items contradictory")
    for left_pos, left in enumerate(material):
        for right in material[left_pos + 1 :]:
            left_polarity = _POLARITY.get(left.kind, 0)
            right_polarity = _POLARITY.get(right.kind, 0)
            opposed = left_polarity and right_polarity and left_polarity != right_polarity
            if left.subject and left.subject.lower() == right.subject.lower() and opposed:
                record(left, right, f"same subject {left.subject!r} with opposite polarity")
                continue
            if opposed and _negation_free(left.statement) == _negation_free(right.statement):
                record(left, right, "identical statement modulo negation with opposite polarity")
    return sorted(found.values(), key=lambda entry: (entry.left_id, entry.right_id))


__all__ = [
    "CONFIDENCE",
    "EXECUTABLE_KINDS",
    "GROUNDING_THRESHOLD",
    "MATERIALITY",
    "SEMANTIC_KINDS",
    "Contradiction",
    "RejectedItem",
    "SemanticIRError",
    "SemanticItem",
    "admit",
    "contradictions",
    "dedupe",
    "distinctive_tokens",
    "grounding_score",
    "normalize_statement",
    "parse_items",
]
