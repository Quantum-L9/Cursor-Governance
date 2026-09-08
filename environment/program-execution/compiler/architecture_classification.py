"""Deterministic evidence for promoting prose to Architecture Intent v1."""

from __future__ import annotations

import re
from typing import Any

from .architecture_intent import normalize_source, normative_signals, segment

ARCHITECTURE_MIN_NORMATIVE_UNITS = 3
ARCHITECTURE_MIN_HEADINGS = 2
ARCHITECTURE_MIN_FEATURES = 3

_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.M)
_FEATURE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "architecture",
        re.compile(
            r"\b(?:architecture|architectural|control plane|capability plane|"
            r"target architecture)\b",
            re.I,
        ),
    ),
    (
        "authority_ownership",
        re.compile(r"\b(?:authority|ownership|sole owner|owner map|governing invariant)\b", re.I),
    ),
    (
        "implementation",
        re.compile(
            r"\b(?:implementation plan|build sequence|phase\s+\d+|file-by-file|"
            r"target repository structure)\b",
            re.I,
        ),
    ),
    (
        "acceptance_validation",
        re.compile(
            r"\b(?:acceptance|validation|test matrix|pass criteria|release-blocking|"
            r"regression test)\b",
            re.I,
        ),
    ),
    (
        "prohibitions",
        re.compile(r"\b(?:must not|do not|never|forbidden|prohibited|out of scope)\b", re.I),
    ),
    (
        "rollback",
        re.compile(r"\b(?:rollback|revert|recovery)\b", re.I),
    ),
    (
        "implementation_surfaces",
        re.compile(r"\b(?:schema|manifest|registry|adapter|hook|compiler|router|receipt)\b", re.I),
    ),
)


def architecture_prose_evidence(text: str) -> dict[str, Any]:
    """Return explainable deterministic evidence and the promotion verdict.

    Promotion counts normative *source units*, not unique signal names. A design
    with five independent MUST obligations must not collapse to a signal count
    of one merely because every obligation uses the same canonical word.
    """
    normalized = normalize_source(text)
    signals = tuple(normative_signals(normalized))
    units = segment(normalized)
    normative_units = tuple(unit.id for unit in units if unit.normative)
    headings = len(_HEADING_RE.findall(normalized))
    features = tuple(name for name, pattern in _FEATURE_PATTERNS if pattern.search(normalized))
    qualified = (
        len(normative_units) >= ARCHITECTURE_MIN_NORMATIVE_UNITS
        and headings >= ARCHITECTURE_MIN_HEADINGS
        and len(features) >= ARCHITECTURE_MIN_FEATURES
    )
    return {
        "qualified": qualified,
        "normative_unit_count": len(normative_units),
        "normative_units": list(normative_units),
        "signal_types": list(signals),
        "heading_count": headings,
        "feature_count": len(features),
        "features": list(features),
        "thresholds": {
            "normative_units": ARCHITECTURE_MIN_NORMATIVE_UNITS,
            "headings": ARCHITECTURE_MIN_HEADINGS,
            "features": ARCHITECTURE_MIN_FEATURES,
        },
    }


def classification_diagnostic(evidence: dict[str, Any]) -> str:
    return (
        "architecture_auto_promoted: deterministic evidence admitted unchanged prose "
        f"({evidence['normative_unit_count']} normative units, "
        f"{evidence['heading_count']} headings, {evidence['feature_count']} architecture features)"
    )


__all__ = [
    "ARCHITECTURE_MIN_FEATURES",
    "ARCHITECTURE_MIN_HEADINGS",
    "ARCHITECTURE_MIN_NORMATIVE_UNITS",
    "architecture_prose_evidence",
    "classification_diagnostic",
]
