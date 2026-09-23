#!/usr/bin/env python3
"""Typed README compilation model owned by l9-update-agent-docs.

These contracts are the seam between the four stages of README
compilation: qualification produces :class:`ReadmeTarget`, evidence
compilation produces :class:`ReadmeModel`, validation produces
:class:`QualityFinding`, and reconciliation produces :class:`ReadmePlan`.

Deliberately free of repository-specific filesystem knowledge: nothing
here may import a Cursor-Governance path, policy file, or analyzer. That
keeps the compiler core extractable without carrying consumer policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = [
    "MUTATING_ACTIONS",
    "README_KINDS",
    "DependencyDoc",
    "EvidenceRef",
    "ExtractionIssue",
    "InterfaceDoc",
    "ModuleDoc",
    "PlanAction",
    "QualityFinding",
    "ReadmeKind",
    "ReadmeModel",
    "ReadmePlan",
    "ReadmePlanItem",
    "ReadmeTarget",
    "RelationshipDoc",
    "SourceFact",
]

ReadmeKind = Literal[
    "skill",
    "module",
    "subsystem",
    "corpus",
    "index",
]

README_KINDS: frozenset[str] = frozenset(
    {
        "skill",
        "module",
        "subsystem",
        "corpus",
        "index",
    }
)

PlanAction = Literal[
    "create",
    "refresh",
    "unchanged",
    "preserve",
    "retire",
    "conflict",
]

#: Actions that change bytes on disk. Everything else is an observation.
MUTATING_ACTIONS: frozenset[str] = frozenset({"create", "refresh", "retire"})


@dataclass(frozen=True)
class EvidenceRef:
    """One deterministic repository fact a rendered statement rests on."""

    source: str
    kind: str
    detail: str | None = None


@dataclass(frozen=True)
class ReadmeTarget:
    """A directory the inventory authorized for a generated README.

    ``path`` is structural identity. Configuration may decorate a target
    but must never be able to change the path a renderer prints, which is
    how a generated README came to claim a directory it did not describe.
    """

    path: str
    kind: ReadmeKind
    title: str
    configured_purpose: str | None = None
    configured_description: str | None = None
    tier: str | None = None
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class InterfaceDoc:
    """One public symbol: a class or a module-level function."""

    name: str
    signature: str | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RelationshipDoc:
    """One source-located deterministic relationship for reader navigation."""

    kind: str
    target: str
    source: str
    detail: str | None = None


@dataclass(frozen=True)
class ExtractionIssue:
    """A source that policy admitted but the static extractor could not read."""

    path: str
    language: str
    detail: str


@dataclass(frozen=True)
class ModuleDoc:
    """One source file's public surface.

    Module identity is preserved all the way to the renderer so symbols
    from unrelated files are never flattened into one anonymous API list.
    """

    file: str
    name: str
    purpose: str | None = None
    classes: tuple[InterfaceDoc, ...] = ()
    functions: tuple[InterfaceDoc, ...] = ()
    exports: tuple[str, ...] = ()
    language: str | None = None


@dataclass(frozen=True)
class SourceFact:
    """Language-neutral source evidence before it becomes a README model."""

    path: str
    language: str
    module: ModuleDoc
    imports: tuple[str, ...] = ()
    relative_imports: tuple[str, ...] = ()
    entrypoints: tuple[str, ...] = ()
    relationships: tuple[RelationshipDoc, ...] = ()


@dataclass(frozen=True)
class DependencyDoc:
    """Imports split by origin. Standard library is tracked but not rendered."""

    internal: tuple[str, ...] = ()
    external: tuple[str, ...] = ()
    stdlib: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.internal or self.external)


@dataclass(frozen=True)
class ReadmeModel:
    """The semantic model a renderer projects into Markdown.

    A field left empty means no deterministic evidence supported it. The
    renderer omits the section rather than filling it with generic prose.
    """

    target: ReadmeTarget
    purpose: str | None = None
    description: str | None = None
    responsibilities: tuple[str, ...] = ()
    modules: tuple[ModuleDoc, ...] = ()
    children: tuple[str, ...] = ()
    file_types: tuple[tuple[str, int], ...] = ()
    contents: tuple[str, ...] = ()
    shell_entrypoints: tuple[str, ...] = ()
    dependencies: DependencyDoc = field(default_factory=DependencyDoc)
    authority_links: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()
    source_facts: tuple[SourceFact, ...] = ()
    extraction_issues: tuple[ExtractionIssue, ...] = ()
    relationships: tuple[RelationshipDoc, ...] = ()
    eligible_source_count: int = 0
    extracted_source_count: int = 0
    rendered_symbol_count: int = 0

    @property
    def completeness(self) -> str:
        """Deterministic evidence disposition, never a prose-quality opinion."""
        if self.extraction_issues:
            return "partial"
        if self.eligible_source_count == 0:
            return "minimal-by-design"
        if self.extracted_source_count < self.eligible_source_count:
            return "partial"
        return "complete"


@dataclass(frozen=True)
class QualityFinding:
    """One validation verdict against a compiled model or its rendering."""

    rule_id: str
    severity: Literal["ERROR", "WARN"]
    message: str
    source: str | None = None


@dataclass(frozen=True)
class ReadmePlanItem:
    """One reconciled README destination and the action it requires."""

    path: str
    action: PlanAction
    target: ReadmeTarget | None = None
    desired_content: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class ReadmePlan:
    """The complete desired-vs-owned reconciliation for a repository."""

    items: tuple[ReadmePlanItem, ...] = ()
    findings: tuple[QualityFinding, ...] = ()
    quality: tuple[dict[str, int | str], ...] = ()

    @property
    def mutations(self) -> tuple[ReadmePlanItem, ...]:
        return tuple(item for item in self.items if item.action in MUTATING_ACTIONS)

    @property
    def errors(self) -> tuple[QualityFinding, ...]:
        return tuple(finding for finding in self.findings if finding.severity == "ERROR")

    def counts(self) -> dict[str, int]:
        """Action histogram, every action present so receipts stay stable."""
        tally = {
            "create": 0,
            "refresh": 0,
            "unchanged": 0,
            "preserve": 0,
            "retire": 0,
            "conflict": 0,
        }
        for item in self.items:
            tally[item.action] = tally.get(item.action, 0) + 1
        return tally
