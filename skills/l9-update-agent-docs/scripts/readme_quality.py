#!/usr/bin/env python3
"""Quality validation for compiled README models and their rendering.

ERROR findings block the run: they mean the compiler would write a
README that is wrong about the repository — unauthorized target, a path
it does not describe, a purpose taken from somewhere that cannot support
it, a link that resolves nowhere. WARN findings are presentation debt and
are reported without blocking.

The validator never repairs. A generated README defect is a compiler
defect, so the fix belongs upstream of the bytes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from readme_model import QualityFinding, ReadmeModel
from readme_renderers import (
    MARKER_VERSION,
    UNREADABLE_MARKER_VERSION,
    marker_for,
    marker_kind,
    marker_version,
    owns_any_marker,
)

__all__ = [
    "FORBIDDEN_PURPOSE_PHRASES",
    "PURPOSE_EVIDENCE_KINDS",
    "retirement_findings",
    "validate_readme_model",
    "validate_readme_models",
]

#: Evidence kinds that may support a rendered directory purpose. Anything
#: else means the purpose reached the model without a deterministic source,
#: which is the failure INV-RD-004 exists to prevent.
PURPOSE_EVIDENCE_KINDS = frozenset({"configured_purpose", "skill_contract", "module_docstring"})

#: Phrases the old templates emitted when they had nothing to say. They
#: are forbidden outright rather than discouraged: a README whose Purpose
#: restates its own file count teaches a reader nothing and costs a read.
FORBIDDEN_PURPOSE_PHRASES = (
    "ast-extracted module documentation",
    "this directory holds",
    "this directory is reserved",
    "index of child modules and document folders",
    "no description",
)
_EMPTY_SECTION_RE = re.compile(r"^##\s+.+\n+_No [^\n]*_\s*$", re.MULTILINE)
_RELATIVE_LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)]+)\)")
_MAX_EXTERNAL_DEPENDENCIES = 24


def _error(rule_id: str, message: str, source: str | None) -> QualityFinding:
    return QualityFinding(rule_id=rule_id, severity="ERROR", message=message, source=source)


def _warn(rule_id: str, message: str, source: str | None) -> QualityFinding:
    return QualityFinding(rule_id=rule_id, severity="WARN", message=message, source=source)


def validate_readme_model(
    repo_root: Path,
    model: ReadmeModel,
    rendered: str,
    *,
    authorized: Iterable[str] = (),
    excluded: Iterable[str] = (),
) -> list[QualityFinding]:
    """Validate one compiled model against its rendering."""
    findings: list[QualityFinding] = []
    target = model.target
    source = f"{target.path}/README.md"
    authorized_set = set(authorized)
    excluded_set = set(excluded)

    if authorized_set and target.path not in authorized_set:
        findings.append(
            _error(
                "readme.target.unauthorized",
                f"{target.path} is not present in the authorized inventory",
                source,
            )
        )
    if target.path in excluded_set:
        findings.append(
            _error(
                "readme.target.excluded",
                f"{target.path} lies beneath an excluded subtree",
                source,
            )
        )

    if f"**Path:** `{target.path}`" not in rendered:
        findings.append(
            _error(
                "readme.path.mismatch",
                f"rendered path metadata does not match target path {target.path}",
                source,
            )
        )

    if marker_for(target.kind) not in rendered:
        recorded = marker_kind(rendered)
        findings.append(
            _error(
                "readme.kind.marker_mismatch",
                f"ownership marker kind {recorded!r} disagrees with target kind {target.kind!r}",
                source,
            )
        )

    lowered = (model.purpose or "").strip().lower()
    for phrase in FORBIDDEN_PURPOSE_PHRASES:
        if phrase in lowered:
            findings.append(
                _error(
                    "readme.generic_purpose",
                    f"purpose falls back to generic filler: {model.purpose!r}",
                    source,
                )
            )
            break

    if model.purpose and not any(ref.kind in PURPOSE_EVIDENCE_KINDS for ref in model.evidence):
        findings.append(
            _error(
                "readme.purpose.unsourced",
                f"purpose {model.purpose!r} carries no evidence reference naming its source",
                source,
            )
        )

    if target.kind == "skill" and "SKILL.md" not in rendered:
        findings.append(
            _error(
                "readme.skill.authority_missing",
                "skill README does not point at SKILL.md as the authoritative contract",
                source,
            )
        )

    if len(model.modules) > 1 and model.purpose and not target.configured_purpose:
        borrowed = [module for module in model.modules if module.purpose == model.purpose]
        if borrowed:
            findings.append(
                _error(
                    "readme.multi_module.purpose_leak",
                    (
                        f"directory purpose is the docstring of {borrowed[0].file} "
                        f"while {len(model.modules)} modules live here"
                    ),
                    source,
                )
            )

    for match in _RELATIVE_LINK_RE.finditer(rendered):
        href = match.group(1).split("#", 1)[0].strip()
        if not href:
            continue
        resolved = repo_root / target.path / href
        if not resolved.exists():
            findings.append(
                _error(
                    "readme.reference.missing",
                    f"relative reference {href!r} resolves to nothing",
                    source,
                )
            )

    # --- WARN: presentation debt ---

    if _EMPTY_SECTION_RE.search(rendered):
        findings.append(
            _warn("readme.empty_section", "a rendered section has no positive content", source)
        )

    if target.kind == "subsystem" and len(model.modules) > 1:
        flattened = "## Public interface" in rendered
        if flattened:
            findings.append(
                _warn(
                    "readme.api.flattened",
                    "symbols from several modules share one anonymous interface list",
                    source,
                )
            )

    if model.dependencies.stdlib and not (
        model.dependencies.internal or model.dependencies.external
    ):
        findings.append(
            _warn(
                "readme.dependencies.noisy",
                "only standard-library imports were found; dependency section omitted",
                source,
            )
        )
    if len(model.dependencies.external) > _MAX_EXTERNAL_DEPENDENCIES:
        findings.append(
            _warn(
                "readme.dependencies.noisy",
                f"{len(model.dependencies.external)} external dependencies rendered",
                source,
            )
        )

    for module in model.modules:
        total = len(module.classes) + len(module.functions)
        if total > 24:
            findings.append(
                _warn(
                    "readme.interface.excessive",
                    f"{module.file} exposes {total} public symbols",
                    source,
                )
            )

    if target.title == target.path and "/" in target.path:
        findings.append(
            _warn("readme.title.raw_path", "title is an unprocessed path", source),
        )

    return findings


def validate_readme_models(
    repo_root: Path,
    pairs: Sequence[tuple[ReadmeModel, str]],
    *,
    authorized: Iterable[str] = (),
    excluded: Iterable[str] = (),
) -> list[QualityFinding]:
    """Validate every compiled model in one pass, deterministically ordered."""
    authorized_set = set(authorized)
    excluded_set = set(excluded)
    findings: list[QualityFinding] = []
    for model, rendered in pairs:
        findings.extend(
            validate_readme_model(
                repo_root,
                model,
                rendered,
                authorized=authorized_set,
                excluded=excluded_set,
            )
        )
    return findings


def retirement_findings(path: str, text: str) -> list[QualityFinding]:
    """Refuse to retire a README this generator does not strongly own.

    Both version-1 markers count: this generator wrote them, so a stale
    one is its own to clean up. What it must not touch is an unmarked
    file, or output from a generator version it does not understand.
    """
    if not owns_any_marker(text):
        return [
            _error(
                "readme.retire.unowned",
                f"{path} carries no generator ownership marker and must not be retired",
                path,
            )
        ]
    version = marker_version(text)
    if version == UNREADABLE_MARKER_VERSION:
        return [
            _error(
                "readme.marker.future_version",
                (
                    f"{path} carries a format version this compiler cannot read; it "
                    f"understands {MARKER_VERSION} and will not rewrite or delete it"
                ),
                path,
            )
        ]
    if version is not None and version > MARKER_VERSION:
        return [
            _error(
                "readme.marker.future_version",
                (
                    f"{path} was written by format version {version}; this compiler "
                    f"understands {MARKER_VERSION} and will not rewrite or delete it"
                ),
                path,
            )
        ]
    return []
