"""Architecture Intent v1: operator long-form architecture prose as compiler input.

`program-execution.intent.v1` stays what it is — a *minimal* goal-level contract
that deliberately refuses tasks, files, waves, and implementation instructions.
This module is the other end of the same problem: an operator hands the front
door a microscope audit, a technical review, or an architecture design that is
already dense with obligations, and the compiler has to preserve every one of
them rather than re-ask the operator to hand-write a campaign.

Nothing here interprets meaning. This layer is deterministic: normalize, hash,
segment into stable source units, and mark which units carry normative weight.
Interpretation happens in `architecture_extractor`, and its output is candidate
material that must cite the unit ids minted here. That split is the whole point:
a model may propose meaning, but it may never be the record of what the source
said.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARCHITECTURE_INTENT_SCHEMA = "l9.program-execution.architecture-intent.v1"
INTENT_PROVENANCE_SCHEMA = "l9.program-execution.intent-provenance.v1"
MEDIA_TYPES = {
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])\s+\S")
TABLE_RE = re.compile(r"^\s{0,3}\|")
QUOTE_RE = re.compile(r"^\s{0,3}>")

# Deterministic materiality signals. These are NOT semantic authority: a signal
# only guarantees that a unit cannot vanish from the compilation without an
# explicit, recorded disposition. Interpretation is the extractor's job.
NORMATIVE_SIGNALS: tuple[str, ...] = (
    "MUST NOT",
    "MUST",
    "NEVER",
    "DO NOT",
    "REQUIRED",
    "REQUIRE",
    "INVARIANT",
    "ACCEPTANCE",
    "TEST",
    "FAIL CLOSED",
    "FAIL-CLOSED",
    "PRIMARY",
    "ONLY",
    "REMOVE",
    "PRESERVE",
    "DEFER",
    "DEFERRED",
    "OUT OF SCOPE",
    "SHALL",
    "FORBIDDEN",
    "PROHIBITED",
    "SHOULD",
)

# Longest-first so "MUST NOT" is reported instead of a bare "MUST".
_SIGNAL_PATTERNS = tuple(
    (
        signal,
        re.compile(r"(?<![A-Za-z])" + re.escape(signal).replace(r"\ ", r"\s+") + r"(?![A-Za-z])"),
    )
    for signal in sorted(NORMATIVE_SIGNALS, key=len, reverse=True)
)

# Lowercase materiality — same canonical names as the uppercase anchors.
# Prohibitions and obligations survive; bare conversational "keep"/"reuse"
# do not, so coverage does not drown (C2 materiality threshold).
_MATERIAL_SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("MUST NOT", re.compile(r"(?i)(?<![A-Za-z])must\s+not(?![A-Za-z])")),
    ("DO NOT", re.compile(r"(?i)(?<![A-Za-z])(?:do\s+not|don't)(?![A-Za-z])")),
    (
        "NEVER",
        re.compile(
            r"(?i)(?<![A-Za-z])(?:must\s+never|never\s+"
            r"(?:replace|grant|create|delete|advertise|serve|push|merge))"
            r"(?![A-Za-z])"
        ),
    ),
    ("SHALL", re.compile(r"(?i)(?<![A-Za-z])shall(?![A-Za-z])")),
    ("MUST", re.compile(r"(?i)(?<![A-Za-z])must(?![A-Za-z])")),
    ("REQUIRED", re.compile(r"(?i)(?<![A-Za-z])required(?![A-Za-z])")),
    ("REQUIRE", re.compile(r"(?i)(?<![A-Za-z])require(?![A-Za-z])")),
    ("PRESERVE", re.compile(r"(?i)(?<![A-Za-z])preserve(?![A-Za-z])")),
    ("FORBIDDEN", re.compile(r"(?i)(?<![A-Za-z])forbidden(?![A-Za-z])")),
    ("PROHIBITED", re.compile(r"(?i)(?<![A-Za-z])prohibited(?![A-Za-z])")),
    (
        "KEEP",
        re.compile(r"(?i)(?<![A-Za-z])keep\s+(?:the|existing|current)(?![A-Za-z])"),
    ),
    (
        "PRESERVE",
        re.compile(r"(?i)(?<![A-Za-z])reuse\s+(?:the|existing|current)(?![A-Za-z])"),
    ),
)

UNIT_KINDS = (
    "frontmatter",
    "heading",
    "paragraph",
    "list_item",
    "table",
    "code_fence",
    "blockquote",
)


class ArchitectureIntentError(ValueError):
    """The architecture source cannot be read as Architecture Intent v1."""


@dataclass(frozen=True)
class SourceUnit:
    """One addressable, hashed span of the operator's document."""

    id: str
    kind: str
    line_start: int
    line_end: int
    sha256: str
    text: str
    signals: tuple[str, ...] = ()

    @property
    def normative(self) -> bool:
        return bool(self.signals)

    def to_dict(self, *, include_text: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "sha256": self.sha256,
        }
        if self.signals:
            data["signals"] = list(self.signals)
        if include_text:
            data["text"] = self.text
        return data


@dataclass(frozen=True)
class ArchitectureIntent:
    """A normalized, hashed, segmented architecture document."""

    path: Path
    text: str
    sha256: str
    media_type: str
    units: tuple[SourceUnit, ...]
    frontmatter: dict[str, Any]
    target: str
    title: str
    declared: bool

    @property
    def schema(self) -> str:
        return ARCHITECTURE_INTENT_SCHEMA

    @property
    def material_units(self) -> tuple[SourceUnit, ...]:
        return tuple(unit for unit in self.units if unit.normative)

    def unit(self, unit_id: str) -> SourceUnit | None:
        return self._index.get(unit_id)

    @property
    def _index(self) -> dict[str, SourceUnit]:
        return {unit.id: unit for unit in self.units}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "target": self.target,
            "title": self.title,
            "declared": self.declared,
            "source": {
                "path": str(self.path),
                "sha256": self.sha256,
                "media_type": self.media_type,
                "lines": self.text.count("\n") + (0 if self.text.endswith("\n") else 1),
            },
            "units": [unit.to_dict(include_text=False) for unit in self.units],
        }


def normalize_source(raw: str) -> str:
    """LF line endings, no BOM, trailing newline. Identity is computed on this."""
    text = raw.replace("﻿", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text and not text.endswith("\n"):
        text += "\n"
    return text


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normative_signals(text: str) -> tuple[str, ...]:
    """Deterministic lexical materiality signals present in `text`.

    Upper-case MUST / MUST NOT remain high-confidence anchors. Lower-case
    must / don't / never / preserve are material prohibitions and obligations
    with the same canonical names so they cannot vanish. Bare conversational
    "keep" is not a signal unless it names an existing object.
    """
    found: list[str] = []
    for signal, pattern in _SIGNAL_PATTERNS:
        if pattern.search(text) and not any(signal in seen for seen in found):
            found.append(signal)
    for signal, pattern in _MATERIAL_SIGNAL_PATTERNS:
        if pattern.search(text) and not any(signal in seen for seen in found):
            found.append(signal)
    return tuple(sorted(found))


def parse_frontmatter(text: str) -> tuple[dict[str, Any], int]:
    """Return (frontmatter mapping, line count consumed). Never raises on prose."""
    match = FRONTMATTER_RE.match(text)
    if match is None:
        return {}, 0
    try:
        import yaml

        raw = yaml.safe_load(match.group(1))
    except Exception:
        return {}, 0
    consumed = match.group(0).count("\n")
    return (raw if isinstance(raw, dict) else {}), consumed


def segment(text: str) -> tuple[SourceUnit, ...]:
    """Split normalized source into stable units on structural boundaries.

    Deterministic by construction: the same bytes always produce the same unit
    ids, spans, and digests, so a semantic item that cites SRC-0017 cites the
    same 5 lines on every machine and every rerun.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    units: list[SourceUnit] = []
    index = 0
    total = len(lines)
    counter = 0

    def emit(kind: str, start: int, end: int) -> None:
        nonlocal counter
        body = "\n".join(lines[start : end + 1])
        if not body.strip():
            return
        counter += 1
        units.append(
            SourceUnit(
                id=f"SRC-{counter:04d}",
                kind=kind,
                line_start=start + 1,
                line_end=end + 1,
                sha256=digest(body),
                text=body,
                signals=normative_signals(body),
            )
        )

    # Frontmatter is a unit like any other so downstream line numbers need no
    # offset arithmetic; it is simply never normative.
    if lines and lines[0].strip() == "---":
        for close in range(1, total):
            if lines[close].strip() == "---":
                emit("frontmatter", 0, close)
                index = close + 1
                break

    while index < total:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)[0] * 3
            for probe in range(index + 1, total):
                if lines[probe].lstrip().startswith(marker):
                    close = probe
                    break
            else:
                close = total - 1
            emit("code_fence", index, close)
            index = close + 1
            continue
        if HEADING_RE.match(line):
            emit("heading", index, index)
            index += 1
            continue
        if TABLE_RE.match(line):
            close = index
            while close + 1 < total and TABLE_RE.match(lines[close + 1]):
                close += 1
            emit("table", index, close)
            index = close + 1
            continue
        if QUOTE_RE.match(line):
            close = index
            while close + 1 < total and QUOTE_RE.match(lines[close + 1]):
                close += 1
            emit("blockquote", index, close)
            index = close + 1
            continue
        if LIST_RE.match(line):
            close = index
            while close + 1 < total:
                nxt = lines[close + 1]
                if not nxt.strip() or LIST_RE.match(nxt) or _starts_block(nxt):
                    break
                close += 1
            emit("list_item", index, close)
            index = close + 1
            continue
        close = index
        while close + 1 < total:
            nxt = lines[close + 1]
            if not nxt.strip() or LIST_RE.match(nxt) or _starts_block(nxt):
                break
            close += 1
        emit("paragraph", index, close)
        index = close + 1
    return tuple(units)


def _starts_block(line: str) -> bool:
    return bool(
        HEADING_RE.match(line)
        or FENCE_RE.match(line)
        or TABLE_RE.match(line)
        or QUOTE_RE.match(line)
    )


def load_architecture_intent(
    path: Path,
    *,
    target: str | None = None,
    forced: bool = False,
) -> ArchitectureIntent:
    """Read, normalize, hash, and segment an architecture source.

    `forced` is the `campaign-architecture` route: the operator selected this
    interpretation explicitly, so an unchanged assistant transcript needs no
    frontmatter edit. Without it the document must declare its own schema.
    """
    path = Path(path)
    if not path.is_file():
        raise ArchitectureIntentError(f"no such architecture intent file: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ArchitectureIntentError(f"architecture source is unreadable: {path}: {exc}") from exc
    text = normalize_source(raw)
    if not text.strip():
        raise ArchitectureIntentError(f"architecture source is empty: {path}")
    frontmatter, _ = parse_frontmatter(text)
    declared = str(frontmatter.get("schema") or "").strip() == ARCHITECTURE_INTENT_SCHEMA
    if not declared and not forced:
        raise ArchitectureIntentError(
            f"{path} does not declare schema {ARCHITECTURE_INTENT_SCHEMA}; pass it through "
            "`make campaign-architecture` or add the frontmatter"
        )
    units = segment(text)
    if not units:
        raise ArchitectureIntentError(f"architecture source segmented to zero units: {path}")
    resolved_target = str(target or frontmatter.get("target") or "").strip()
    if not resolved_target:
        raise ArchitectureIntentError(
            "architecture intent has no target repository: pass TARGET=<owner/repo> or "
            "declare `target:` in the document frontmatter"
        )
    return ArchitectureIntent(
        path=path.resolve(),
        text=text,
        sha256=digest(text),
        media_type=MEDIA_TYPES.get(path.suffix.lower(), "text/plain"),
        units=units,
        frontmatter=frontmatter,
        target=resolved_target,
        title=str(frontmatter.get("title") or "").strip() or _title_from_units(units, path),
        declared=declared,
    )


def _title_from_units(units: tuple[SourceUnit, ...], path: Path) -> str:
    for unit in units:
        if unit.kind == "heading":
            return unit.text.lstrip("#").strip()
    return path.stem.replace("-", " ").replace("_", " ").strip()


_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(value: str, *, limit: int = 48) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_STRIP.sub("-", text.lower()).strip("-")
    if len(slug) <= limit:
        return slug
    cut = slug[:limit]
    return cut.rsplit("-", 1)[0].strip("-") or cut.strip("-")


def architecture_campaign_id(
    intent: ArchitectureIntent, existing_ids: set[str] | None = None
) -> str:
    """A readable, deterministic campaign id — never a hash-program id.

    Collision safety comes from an explicit `-vN` suffix against ids that
    actually exist, not from preregistration: the question is "does this id
    already exist", never "is this id permitted to exist".
    """
    base = slugify(intent.title) or slugify(intent.path.stem) or "architecture-intent"
    if not base.endswith("-v1"):
        base = f"{base}-v1"
    taken = {str(item) for item in (existing_ids or set())}
    if base not in taken:
        return base
    stem = base[:-3] if base.endswith("-v1") else base
    for version in range(2, 1000):
        candidate = f"{stem}-v{version}"
        if candidate not in taken:
            return candidate
    raise ArchitectureIntentError(f"cannot allocate a free campaign id for {base}")


__all__ = [
    "ARCHITECTURE_INTENT_SCHEMA",
    "INTENT_PROVENANCE_SCHEMA",
    "NORMATIVE_SIGNALS",
    "UNIT_KINDS",
    "ArchitectureIntent",
    "ArchitectureIntentError",
    "SourceUnit",
    "architecture_campaign_id",
    "digest",
    "load_architecture_intent",
    "normalize_source",
    "normative_signals",
    "parse_frontmatter",
    "segment",
    "slugify",
]
