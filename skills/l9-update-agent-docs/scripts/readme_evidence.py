#!/usr/bin/env python3
"""Deterministic evidence compilation for README targets.

AST and filesystem facts are *evidence*. They establish which symbols a
file exposes and what it imports; they do not establish what a directory
is for. This module keeps that distinction: it compiles facts into a
typed :class:`ReadmeModel`, and leaves a field empty whenever no
deterministic source supports it. Nothing here renders Markdown.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

import yaml
from doc_filetree import corpus_files, is_excluded_path, skip_prefixes
from readme_model import (
    DependencyDoc,
    EvidenceRef,
    ExtractionIssue,
    ModuleDoc,
    ReadmeModel,
    ReadmeTarget,
    RelationshipDoc,
    SourceFact,
)
from source_facts import compile_source_facts, supported_source_files

__all__ = [
    "CORPUS_TYPE_LABELS",
    "MAX_INTERFACES_PER_MODULE",
    "MAX_MODULES_RENDERED",
    "SkillContract",
    "classify_dependencies",
    "compile_source_evidence",
    "compile_module_docs",
    "compile_readme_model",
    "read_skill_contract",
    "repository_module_names",
    "summarize_docstring",
]

CORPUS_TYPE_LABELS = {
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".sql": "SQL",
    ".csv": "CSV",
}
#: Presentation bounds. These cap how much is rendered, never what is
#: compiled: truncation is a readability decision, not a semantic one.
MAX_INTERFACES_PER_MODULE = 8
MAX_MODULES_RENDERED = 12
MAX_RESPONSIBILITIES = 6
MAX_CONTENTS = 40

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{2,3})\s+(.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[-*]\s+(.+?)\s*$", re.MULTILINE)
_SKILL_PURPOSE_HEADINGS = ("purpose",)
#: Only a section that actually states boundaries. `## Canonical contract`
#: holds machine-authority file pointers, which render as a list of paths
#: under a heading promising responsibilities.
_SKILL_RESPONSIBILITY_HEADINGS = ("ownership boundaries",)
#: A skill `description` is two things joined: what the skill does, then
#: the routing clause that tells a router when to pick it. Only the first
#: half is a purpose a reader wants.
_ROUTING_CLAUSE_RE = re.compile(r"\.\s+use when\b|\buse when\b", re.IGNORECASE)


class SkillContract:
    """Structural reading of a `SKILL.md`. Never a full Markdown parse."""

    __slots__ = ("description", "purpose", "responsibilities", "version")

    def __init__(
        self,
        *,
        description: str | None = None,
        purpose: str | None = None,
        responsibilities: tuple[str, ...] = (),
        version: str | None = None,
    ) -> None:
        self.description = description
        self.purpose = purpose
        self.responsibilities = responsibilities
        self.version = version


#: Trailing characters that joined a clause to the one removed after it.
_DANGLING_TAIL = " \t,;:-–—…"


def _first_sentence(text: str, limit: int = 320, hard_limit: int = 480) -> str:
    """Collapse whitespace and cut where a reader would.

    A sentence boundary inside the limit is the natural cut. Failing that,
    one long sentence is kept whole up to the hard limit rather than
    published as a fragment — a Purpose ending in an ellipsis reads as
    broken output, which is exactly what the caller is trying to avoid.
    """
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    boundary = max(
        cleaned.rfind(". ", 0, limit),
        cleaned.rfind("! ", 0, limit),
        cleaned.rfind("? ", 0, limit),
    )
    if boundary > 0:
        return cleaned[: boundary + 1]
    if len(cleaned) <= hard_limit:
        return cleaned
    cut = cleaned.rfind(" ", 0, hard_limit)
    head = cleaned[:cut] if cut > 0 else cleaned[:hard_limit]
    return head.rstrip(_DANGLING_TAIL) + "…"


def _strip_routing_clause(description: str) -> str:
    """Keep what the skill does; drop the router's when-to-pick-it clause.

    The two halves are usually joined by punctuation, so the cut leaves it
    behind: `… asks for AWS —` reads as a truncated sentence rather than a
    deliberate one.
    """
    match = _ROUTING_CLAUSE_RE.search(description)
    if match is None:
        return description.strip().rstrip(_DANGLING_TAIL)
    head = description[: match.start()].strip().rstrip(".").rstrip(_DANGLING_TAIL).strip()
    return head or description.strip().rstrip(_DANGLING_TAIL)


def _section_body(text: str, wanted: tuple[str, ...]) -> str | None:
    """Body of the first heading whose title matches, up to the next heading."""
    matches = list(_HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(2).strip().lower() not in wanted:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            return body
    return None


def read_skill_contract(skill_md: Path) -> SkillContract:
    """Extract only what is structurally unambiguous from a skill contract."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return SkillContract()
    description: str | None = None
    version: str | None = None
    front = _FRONTMATTER_RE.match(text)
    if front:
        try:
            meta = yaml.safe_load(front.group(1))
        except yaml.YAMLError:
            meta = None
        if isinstance(meta, dict):
            raw = meta.get("description")
            if isinstance(raw, str) and raw.strip():
                description = _first_sentence(_strip_routing_clause(raw)) or None
            metadata = meta.get("metadata")
            if isinstance(metadata, dict) and metadata.get("version"):
                version = str(metadata["version"])
    purpose_body = _section_body(text, _SKILL_PURPOSE_HEADINGS)
    purpose = None
    if purpose_body:
        paragraph = purpose_body.split("\n\n", 1)[0].strip()
        if paragraph and not paragraph.startswith(("```", "|", "-", "*")):
            purpose = _first_sentence(paragraph)
    responsibilities: tuple[str, ...] = ()
    boundary_body = _section_body(text, _SKILL_RESPONSIBILITY_HEADINGS)
    if boundary_body:
        # A bullet ending in a colon introduces a nested list the top-level
        # pattern does not capture, so keeping it leaves a dangling stem.
        bullets = [
            _first_sentence(match.group(1), 200, 260)
            for match in _BULLET_RE.finditer(boundary_body)
            if not match.group(1).rstrip().endswith(":")
        ]
        responsibilities = tuple(bullets[:MAX_RESPONSIBILITIES])
    return SkillContract(
        description=description,
        purpose=purpose,
        responsibilities=responsibilities,
        version=version,
    )


def _public(name: str) -> bool:
    return not name.startswith("_")


def _signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [arg.arg for arg in node.args.args if arg.arg != "self"]
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({', '.join(args)}){returns}"


def summarize_docstring(doc: str | None, limit: int = 200, hard_limit: int = 260) -> str | None:
    """First sentence of a docstring, not its first physical line.

    A one-sentence summary wrapped across two source lines was being cut
    at the newline, which publishes half a clause ending in `;`.
    """
    if not doc or not doc.strip():
        return None
    paragraph = doc.strip().split("\n\n", 1)[0]
    return _first_sentence(paragraph, limit, hard_limit) or None


def _summary(node: ast.AST) -> str | None:
    return summarize_docstring(ast.get_docstring(node))  # type: ignore[arg-type]


def _direct_source_files(module_dir: Path, suffix: str) -> list[Path]:
    found = [
        child
        for child in module_dir.iterdir()
        if child.is_file() and child.suffix == suffix and not child.name.startswith("test_")
    ]
    return sorted(found, key=lambda item: item.name)


def compile_source_evidence(
    repo_root: Path, rel: str
) -> tuple[tuple[SourceFact, ...], tuple[ExtractionIssue, ...]]:
    """Compatibility-facing access to the policy-owned static extractors."""
    return compile_source_facts(repo_root, rel)


def compile_module_docs(
    repo_root: Path, rel: str
) -> tuple[tuple[ModuleDoc, ...], list[str], set[str]]:
    """Compatibility projection of static source facts into legacy outputs.

    The complete source facts, extraction issues, entrypoints, and relations
    live on :class:`ReadmeModel`; this function stays for callers that only
    need modules plus dependency inputs.
    """
    facts, _issues = compile_source_evidence(repo_root, rel)
    return (
        tuple(fact.module for fact in facts),
        [item for fact in facts for item in fact.imports],
        {item for fact in facts for item in fact.relative_imports},
    )


def repository_module_names(repo_root: Path, paths: list[str]) -> frozenset[str]:
    """Top-level names an import could resolve to inside this repository.

    Conservative by construction: only directory names and direct source
    stems of inventory-authorized paths count, so an unknown import stays
    external rather than being claimed as internal.
    """
    names: set[str] = set()
    for rel in paths:
        directory = repo_root / rel
        if not directory.is_dir():
            continue
        names.add(Path(rel).name)
        for child in supported_source_files(directory):
            names.add(child.stem)
    return frozenset(names)


def classify_dependencies(
    imports: list[str],
    internal_names: frozenset[str],
    relative_names: frozenset[str] | set[str] = frozenset(),
) -> DependencyDoc:
    """Split imports into internal, external and standard library.

    Standard library is compiled but not rendered by default: a dependency
    list dominated by `json` and `pathlib` states nothing a reader of the
    directory did not already assume.

    `relative_names` are internal by construction — a relative import can
    only resolve inside this package — so they are admitted before the
    standard-library test, which a local `json.py` would otherwise lose to.
    """
    stdlib = sys.stdlib_module_names
    internal: set[str] = set(relative_names)
    external: set[str] = set()
    standard: set[str] = set()
    for raw in imports:
        top = raw.split(".", 1)[0]
        if not top:
            continue
        if top in stdlib:
            standard.add(top)
        elif top in internal_names:
            internal.add(top)
        else:
            external.add(top)
    return DependencyDoc(
        internal=tuple(sorted(internal)),
        external=tuple(sorted(external)),
        stdlib=tuple(sorted(standard)),
    )


def _child_directories(module_dir: Path, rel: str) -> tuple[str, ...]:
    """Child directories worth linking to.

    Excluded subtrees are filtered by the one exclusion predicate rather
    than listed: an index that links `_archived/` and `fixtures/` sends a
    reader into exactly the residue the compiler refuses to document.
    """
    prefixes = skip_prefixes()
    try:
        children = [
            child.name
            for child in module_dir.iterdir()
            if child.is_dir() and not is_excluded_path(f"{rel}/{child.name}", prefixes)
        ]
    except OSError:
        return ()
    return tuple(sorted(children))


def _file_type_counts(names: list[str]) -> tuple[tuple[str, int], ...]:
    counts: dict[str, int] = {}
    for name in names:
        label = CORPUS_TYPE_LABELS.get(Path(name).suffix.lower(), "Other")
        counts[label] = counts.get(label, 0) + 1
    return tuple(sorted(counts.items()))


def _resolve_purpose(
    module_dir: Path,
    target: ReadmeTarget,
    modules: tuple[ModuleDoc, ...],
    contract: SkillContract | None,
) -> tuple[str | None, EvidenceRef | None]:
    """Purpose precedence from target-local, deterministic evidence only."""
    if target.configured_purpose:
        return target.configured_purpose, EvidenceRef(
            source="config/subsystems/readme_config.yaml",
            kind="configured_purpose",
            detail=target.path,
        )
    if contract is not None:
        native = contract.description or contract.purpose
        if native:
            return native, EvidenceRef(
                source=f"{target.path}/SKILL.md",
                kind="skill_contract",
                detail="frontmatter description" if contract.description else "## Purpose",
            )
    package_doc = module_dir / "__init__.py"
    if package_doc.is_file():
        try:
            purpose = summarize_docstring(
                ast.get_docstring(ast.parse(package_doc.read_text("utf-8")))
            )
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            purpose = None
        if purpose:
            return purpose, EvidenceRef(
                source=f"{target.path}/__init__.py",
                kind="package_docstring",
                detail="target package docstring",
            )
    for name in (
        "package.json",
        "pyproject.toml",
        "manifest.json",
        "manifest.yaml",
        "manifest.yml",
    ):
        manifest = module_dir / name
        if not manifest.is_file():
            continue
        try:
            raw = manifest.read_text(encoding="utf-8")
            if name in {"package.json", "manifest.json"}:
                data = json.loads(raw)
            elif name == "pyproject.toml":
                parsed = tomllib.loads(raw)
                data = parsed.get("project") if isinstance(parsed, dict) else None
            else:
                data = yaml.safe_load(raw)
        except (
            OSError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
            tomllib.TOMLDecodeError,
            yaml.YAMLError,
        ):
            continue
        description = data.get("description") if isinstance(data, dict) else None
        if isinstance(description, str) and (purpose := _first_sentence(description)):
            return purpose, EvidenceRef(
                source=f"{target.path}/{name}",
                kind="manifest_description",
                detail="target-local manifest description",
            )
    if len(modules) == 1 and modules[0].purpose:
        return modules[0].purpose, EvidenceRef(
            source=f"{target.path}/{modules[0].file}",
            kind="module_docstring",
            detail="single-module target",
        )
    return None, None


def compile_readme_model(
    repo_root: Path,
    target: ReadmeTarget,
    *,
    internal_names: frozenset[str] = frozenset(),
) -> ReadmeModel:
    """Compile deterministic evidence for one authorized target."""
    module_dir = repo_root / target.path
    evidence: list[EvidenceRef] = list(target.evidence)
    contract: SkillContract | None = None
    authority_links: list[str] = []
    if target.kind == "skill":
        skill_md = module_dir / "SKILL.md"
        if skill_md.is_file():
            contract = read_skill_contract(skill_md)
            authority_links.append("SKILL.md")

    modules: tuple[ModuleDoc, ...] = ()
    dependencies = DependencyDoc()
    shell_entrypoints: tuple[str, ...] = ()
    source_facts: tuple[SourceFact, ...] = ()
    extraction_issues: tuple[ExtractionIssue, ...] = ()
    relationships: tuple[RelationshipDoc, ...] = ()
    eligible_source_count = 0
    if target.kind in {"module", "subsystem", "skill"}:
        source_facts, extraction_issues = compile_source_evidence(repo_root, target.path)
        modules = tuple(fact.module for fact in source_facts)
        imports = [
            item for fact in source_facts if fact.language == "python" for item in fact.imports
        ]
        relative = {item for fact in source_facts for item in fact.relative_imports}
        dependencies = classify_dependencies(imports, internal_names, relative)
        if source_facts:
            evidence.append(
                EvidenceRef(
                    source=target.path,
                    kind="source_facts",
                    detail=f"{len(source_facts)} extracted source file(s)",
                )
            )
        for issue in extraction_issues:
            evidence.append(
                EvidenceRef(source=issue.path, kind="source_extraction_issue", detail=issue.detail)
            )
        shell_entrypoints = tuple(
            sorted({entrypoint for fact in source_facts for entrypoint in fact.entrypoints})
        )
        relationships = tuple(
            sorted(
                {relation for fact in source_facts for relation in fact.relationships},
                key=lambda item: (item.kind, item.target, item.source, item.detail or ""),
            )
        )
        eligible_source_count = (
            len(supported_source_files(module_dir)) if module_dir.is_dir() else 0
        )

    contents: tuple[str, ...] = ()
    file_types: tuple[tuple[str, int], ...] = ()
    children: tuple[str, ...] = ()
    if target.kind == "corpus" and module_dir.is_dir():
        names = corpus_files(module_dir)
        contents = tuple(names)
        file_types = _file_type_counts(names)
        evidence.append(
            EvidenceRef(source=target.path, kind="source_tree", detail=f"{len(names)} file(s)")
        )
    elif target.kind == "index" and module_dir.is_dir():
        children = _child_directories(module_dir, target.path)
        # An index may also hold direct files. They are listed rather than
        # dropped: being a parent does not make a manifest beside it invisible.
        names = corpus_files(module_dir)
        contents = tuple(names)
        file_types = _file_type_counts(names)
        evidence.append(
            EvidenceRef(
                source=target.path, kind="source_tree", detail=f"{len(children)} child(ren)"
            )
        )
    elif target.kind == "skill" and module_dir.is_dir():
        children = _child_directories(module_dir, target.path)

    purpose, purpose_evidence = _resolve_purpose(module_dir, target, modules, contract)
    if purpose_evidence is not None:
        evidence.append(purpose_evidence)

    responsibilities = contract.responsibilities if contract is not None else ()

    return ReadmeModel(
        target=target,
        purpose=purpose,
        description=target.configured_description or None,
        responsibilities=responsibilities,
        modules=modules,
        children=children,
        file_types=file_types,
        contents=contents,
        shell_entrypoints=shell_entrypoints,
        dependencies=dependencies,
        authority_links=tuple(authority_links),
        evidence=tuple(evidence),
        source_facts=source_facts,
        extraction_issues=extraction_issues,
        relationships=relationships,
        eligible_source_count=eligible_source_count,
        extracted_source_count=len(source_facts),
        rendered_symbol_count=sum(
            len(module.classes) + len(module.functions) + len(module.exports) for module in modules
        ),
    )
