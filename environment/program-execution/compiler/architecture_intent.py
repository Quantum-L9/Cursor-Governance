"""Architecture Intent v1: deterministic source model for long-form architecture prose.

`l9.program-execution.architecture-intent.v1` is operator-authored long-form
architecture text (a design, microscope audit, technical review, or dense
implementation plan). This module owns everything about that source that must
be deterministic and model-free:

- canonical normalization (LF line endings, preserved text)
- SHA-256 identity for the whole source and for every source unit
- deterministic segmentation into stable, whole-boundary source units
- deterministic normative-signal detection (a coverage guard, not authority)

Nothing here interprets meaning. Semantic interpretation is the extractor's
candidate output (`architecture_extractor`), audited by `architecture_coverage`.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a hard dependency of the gate
    yaml = None  # type: ignore[assignment]

ARCHITECTURE_INTENT_SCHEMA = "l9.program-execution.architecture-intent.v1"
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)

# Deterministic lexical materiality signals (§ coverage guard). A unit that
# carries one of these MUST NOT silently disappear from semantic compilation:
# it must end up mapped, or explicitly classified non-normative with a reason.
# The signals themselves carry no semantic authority.
NORMATIVE_SIGNALS: tuple[str, ...] = (
    "MUST NOT",
    "MUST",
    "NEVER",
    "DO NOT",
    "REQUIRED",
    "INVARIANT",
    "ACCEPTANCE",
    "FAIL CLOSED",
    "FAILS CLOSED",
    "OUT OF SCOPE",
    "PROHIBITED",
    "FORBIDDEN",
    "PRESERVE",
    "DEFER",
    "DEFERRED",
    "RESEARCH-ONLY",
    "RESEARCH ONLY",
)

_SIGNAL_RES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (
        signal,
        re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(signal).replace(r"\ ", r"\s+") + r"(?![A-Za-z0-9])",
            re.I,
        ),
    )
    for signal in NORMATIVE_SIGNALS
)

_FENCE_RE = re.compile(r"^(```+|~~~+)")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_BLOCKQUOTE_RE = re.compile(r"^\s*>")


class ArchitectureIntentError(RuntimeError):
    """Terminal architecture-intent source failure. Nothing has executed."""


@dataclass(frozen=True)
class SourceUnit:
    """One deterministic slice of the architecture source."""

    id: str
    line_start: int
    line_end: int
    sha256: str
    kind: str
    text: str
    signals: tuple[str, ...] = ()

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "sha256": self.sha256,
            "kind": self.kind,
            "signals": list(self.signals),
        }
        if include_text:
            payload["text"] = self.text
        return payload


@dataclass(frozen=True)
class SourceDocument:
    """Canonical architecture source plus its stable unit ledger."""

    path: str
    sha256: str
    media_type: str
    text: str
    units: tuple[SourceUnit, ...] = field(default_factory=tuple)

    def unit_ids(self) -> set[str]:
        return {unit.id for unit in self.units}

    def unit_by_id(self) -> dict[str, SourceUnit]:
        return {unit.id: unit for unit in self.units}

    def signal_unit_ids(self) -> set[str]:
        return {unit.id for unit in self.units if unit.signals}

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        return {
            "source": {
                "path": self.path,
                "sha256": self.sha256,
                "media_type": self.media_type,
            },
            "units": [unit.to_dict(include_text=include_text) for unit in self.units],
        }


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_source(text: str) -> str:
    """Canonicalize line endings to LF. The original bytes are otherwise kept."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def unit_signals(text: str) -> tuple[str, ...]:
    """Deterministic normative-signal scan for one unit. Order is stable."""
    found: list[str] = []
    for signal, pattern in _SIGNAL_RES:
        if pattern.search(text):
            # "MUST NOT" subsumes "MUST"; keep only the most specific token.
            if signal == "MUST" and "MUST NOT" in found:
                continue
            if signal == "DEFER" and "DEFERRED" in found:
                continue
            found.append(signal)
    return tuple(found)


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    match = FRONTMATTER_RE.match(text)
    if match is None or yaml is None:
        return None
    try:
        raw = yaml.safe_load(match.group(1))
    except Exception:
        return None
    return raw if isinstance(raw, dict) else None


def declares_architecture_intent(text: str) -> bool:
    frontmatter = parse_frontmatter(text)
    if not isinstance(frontmatter, dict):
        return False
    return str(frontmatter.get("schema") or "").strip() == ARCHITECTURE_INTENT_SCHEMA


def frontmatter_target(text: str) -> str:
    frontmatter = parse_frontmatter(text) or {}
    return str(frontmatter.get("target") or "").strip()


def _line_kind(line: str, *, in_fence: bool) -> str:
    if in_fence:
        return "code"
    if not line.strip():
        return "blank"
    if _FENCE_RE.match(line.strip()):
        return "fence"
    if _HEADING_RE.match(line):
        return "heading"
    if _TABLE_RE.match(line):
        return "table"
    if _BLOCKQUOTE_RE.match(line):
        return "blockquote"
    if _LIST_ITEM_RE.match(line):
        return "list_item"
    return "prose"


def segment_source(
    text: str,
    *,
    path: str = "<memory>",
    media_type: str = "text/markdown",
) -> SourceDocument:
    """Deterministically segment normalized source into stable source units.

    Boundaries respect headings, paragraphs, list items, table blocks, code
    fences, blockquote sections, and YAML frontmatter. Equivalent canonical
    source always yields identical source and unit identities; changing any
    material text changes the affected digests.
    """
    canonical = normalize_source(text)
    if not canonical.strip():
        raise ArchitectureIntentError("architecture source is empty; nothing to compile")
    lines = canonical.split("\n")

    blocks: list[tuple[int, int, str]] = []  # (start_index, end_index inclusive, kind)

    index = 0
    total = len(lines)

    frontmatter = FRONTMATTER_RE.match(canonical)
    if frontmatter is not None:
        fm_line_count = canonical[: frontmatter.end()].rstrip("\n").count("\n") + 1
        blocks.append((0, fm_line_count - 1, "frontmatter"))
        index = fm_line_count

    while index < total:
        line = lines[index]
        kind = _line_kind(line, in_fence=False)
        if kind == "blank":
            index += 1
            continue
        if kind == "fence":
            fence_token = line.strip()[:3]
            end = index + 1
            while end < total and not lines[end].strip().startswith(fence_token):
                end += 1
            end = min(end, total - 1)
            blocks.append((index, end, "code_fence"))
            index = end + 1
            continue
        if kind == "heading":
            end = index
            probe = index + 1
            while probe < total:
                probe_kind = _line_kind(lines[probe], in_fence=False)
                if probe_kind != "prose":
                    break
                end = probe
                probe += 1
            blocks.append((index, end, "heading_and_paragraph" if end > index else "heading"))
            index = end + 1
            continue
        if kind == "table":
            end = index
            while end + 1 < total and _line_kind(lines[end + 1], in_fence=False) == "table":
                end += 1
            blocks.append((index, end, "table"))
            index = end + 1
            continue
        if kind == "blockquote":
            end = index
            while end + 1 < total and _line_kind(lines[end + 1], in_fence=False) == "blockquote":
                end += 1
            blocks.append((index, end, "blockquote"))
            index = end + 1
            continue
        if kind == "list_item":
            end = index
            probe = index + 1
            item_indent = len(line) - len(line.lstrip())
            while probe < total:
                probe_line = lines[probe]
                probe_kind = _line_kind(probe_line, in_fence=False)
                probe_indent = len(probe_line) - len(probe_line.lstrip())
                if probe_kind == "list_item" and probe_indent <= item_indent:
                    break
                if probe_kind in {"blank", "heading", "fence", "table"}:
                    break
                end = probe
                probe += 1
            blocks.append((index, end, "list_item"))
            index = end + 1
            continue
        # prose paragraph
        end = index
        probe = index + 1
        while probe < total and _line_kind(lines[probe], in_fence=False) == "prose":
            end = probe
            probe += 1
        blocks.append((index, end, "paragraph"))
        index = end + 1

    units: list[SourceUnit] = []
    for position, (start, end, kind) in enumerate(blocks, start=1):
        unit_text = "\n".join(lines[start : end + 1])
        signals = () if kind in {"frontmatter", "code_fence"} else unit_signals(unit_text)
        units.append(
            SourceUnit(
                id=f"SRC-{position:04d}",
                line_start=start + 1,
                line_end=end + 1,
                sha256=sha256_text(unit_text),
                kind=kind,
                text=unit_text,
                signals=signals,
            )
        )
    if not units:
        raise ArchitectureIntentError("architecture source produced no source units")
    return SourceDocument(
        path=path,
        sha256=sha256_text(canonical),
        media_type=media_type,
        text=canonical,
        units=tuple(units),
    )


def load_source(path: Path) -> SourceDocument:
    path = Path(path)
    if not path.is_file():
        raise ArchitectureIntentError(f"architecture source not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ArchitectureIntentError(f"architecture source cannot be read: {path}: {exc}") from exc
    media_type = "text/markdown" if path.suffix.lower() in {".md", ".markdown"} else "text/plain"
    return segment_source(raw, path=str(path), media_type=media_type)
