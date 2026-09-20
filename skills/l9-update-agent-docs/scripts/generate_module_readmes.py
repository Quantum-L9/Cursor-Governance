#!/usr/bin/env python3
"""Repository README compiler owned by l9-update-agent-docs.

This file is the CLI, the compatibility surface, and the orchestration of
four stages that live elsewhere: qualification (`doc_filetree`), evidence
(`readme_evidence`), rendering (`readme_renderers`), and validation
(`readme_quality`). It owns none of them.

The pipeline is qualify -> model -> render -> validate -> reconcile ->
apply. Reconciliation compares the authorized desired corpus against the
generator-owned corpus on disk, so a README this generator wrote for a
target it no longer authorizes is retired rather than left behind.
Handwritten files are preserved at every stage. Never writes the
repository-root README.md. Does not call an LLM or the donor repo.
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from doc_filetree import (
    DEFAULT_SKIP_PREFIXES,
    SKIP_DIR_NAMES,
    FiletreeInventory,
    inventory_from_filetree,
    is_excluded_path,
    walk_inventory,
)
from readme_evidence import (
    classify_dependencies,
    compile_readme_model,
    repository_module_names,
    summarize_docstring,
)
from readme_model import (
    MUTATING_ACTIONS,
    README_KINDS,
    EvidenceRef,
    InterfaceDoc,
    ModuleDoc,
    QualityFinding,
    ReadmeModel,
    ReadmePlan,
    ReadmePlanItem,
    ReadmeTarget,
)
from readme_quality import retirement_findings, validate_readme_models
from readme_renderers import (
    LEGACY_FOLDER_MARKER,
    LEGACY_MARKERS,
    LEGACY_MODULE_MARKER,
    MARKER_VERSION,
    marker_version,
    owns_any_marker,
    render_readme,
)

__all__ = [
    "CONFIG_PATH",
    "GENERATED_MARKER",
    "LEGACY_HANDWRITTEN_RE",
    "README_TEMPLATE",
    "ROOT_README",
    "ClassInfo",
    "FunctionInfo",
    "ModuleFacts",
    "classify_readme",
    "discover_module_paths",
    "extract_subsystem_facts",
    "generate_readme",
    "is_generated",
    "is_handwritten",
    "is_legacy_generated",
    "is_root_readme",
    "list_subsystems",
    "load_config",
    "main",
    "report_gaps",
    "resolve_repo_root",
    "resolve_under_root",
    "select_targets",
    "spec_for_path",
    "validate_sections",
    "validate_subsystem_config",
    "write_missing_module_readmes",
    "write_readme",
]

CONFIG_PATH = Path("config/subsystems/readme_config.yaml")
ROOT_README = Path("README.md")
FORBIDDEN_RELATIVE_PATHS = {"", ".", ".."}
#: Overlay keys configuration is allowed to supply. `path` and the target
#: kind are structural and are never taken from configuration.
SUPPORTED_OVERLAY_FIELDS = frozenset(
    {"path", "title", "tier", "description", "purpose", "skip", "sections"}
)

# Legacy ownership markers, re-exported for the published API. The marker
# authority is `readme_renderers`; these names must never diverge from it.
GENERATED_MARKER = LEGACY_MODULE_MARKER
FOLDER_MARKER = LEGACY_FOLDER_MARKER

HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
# Pre-marker contract of scripts/generate_subsystem_readmes.py: a README whose
# front matter (or first 400 bytes) declares `auto_generated: false` is
# handwritten; everything that generator wrote carries the README_TEMPLATE
# header line and section set below, but no marker.
LEGACY_HANDWRITTEN_RE = re.compile(r"^auto_generated:\s*false\b", re.MULTILINE | re.IGNORECASE)
LEGACY_HEADER_RE = re.compile(r"^\*\*Path:\*\* `[^`\n]+` \| \*\*Tier:\*\* \S.*$", re.MULTILINE)
LEGACY_REQUIRED_HEADINGS = ("Purpose", "Components", "Functions", "Exports", "Dependencies")
ReadmeOwnership = Literal["missing", "generated", "legacy_generated", "handwritten"]

#: Retained for the published compatibility surface only. Legacy-shape
#: detection uses LEGACY_HEADER_RE and LEGACY_REQUIRED_HEADINGS, not this
#: string, and the live renderers are in `readme_renderers`.
README_TEMPLATE = """# {title}

**Path:** `{path}` | **Tier:** {tier}

## Purpose

{purpose}

{description}

## Components

{components}

## Functions

{functions}

## Exports

{exports}

## Dependencies

{dependencies}
"""


# --------------------------------------------------------------------------
# Compatibility fact model
#
# `ModuleFacts` aggregates a directory. The compiler no longer renders from
# it, because aggregating before rendering is what let one module's
# docstring speak for a directory of unrelated modules. It stays for the
# published API and for callers that only want the raw AST facts.
# --------------------------------------------------------------------------


@dataclass
class ClassInfo:
    name: str
    file: str
    line_start: int
    line_end: int
    docstring: str
    methods: list[str] = field(default_factory=list)
    method_details: list[dict[str, Any]] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    file: str
    line: int
    signature: str
    docstring: str
    is_async: bool = False
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)


@dataclass
class ModuleFacts:
    path: str
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    constants: list[tuple[str, str, int]] = field(default_factory=list)
    module_docstrings: dict[str, str] = field(default_factory=dict)


def resolve_repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    here = Path(__file__).resolve().parents[3]
    if here.is_dir():
        return here
    return Path.cwd().resolve()


def load_config(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONFIG_PATH
    if not path.is_file():
        return {"defaults": {}, "subsystems": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"config is not a mapping: {path}")
    return data


def _unparse(node: ast.AST | None) -> str | None:
    return None if node is None else ast.unparse(node)


def _public(name: str) -> bool:
    return not name.startswith("_")


def _skip_nested(scan_root: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(scan_root.resolve())
    except ValueError:
        return True
    return any(part in SKIP_DIR_NAMES for part in rel.parts)


def _iter_direct_files(module_dir: Path, pattern: str) -> list[Path]:
    files: list[Path] = []
    for path in sorted(module_dir.glob(pattern)):
        if not path.is_file() or _skip_nested(module_dir, path):
            continue
        if path.name.startswith("test_"):
            continue
        files.append(path)
    return files


def _extract_all(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                value = node.value
                if isinstance(value, (ast.List, ast.Tuple)):
                    names.extend(
                        elt.value
                        for elt in value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    )
    return names


def _extract_constants(tree: ast.Module) -> list[tuple[str, str, int]]:
    found: list[tuple[str, str, int]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                found.append((target.id, repr(node.value.value), node.lineno))
    return found


def _function_info(node: ast.FunctionDef | ast.AsyncFunctionDef, rel: str) -> FunctionInfo:
    args = [arg.arg for arg in node.args.args if arg.arg != "self"]
    ret = _unparse(node.returns)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    ret_s = f" -> {ret}" if ret else ""
    return FunctionInfo(
        name=node.name,
        file=rel,
        line=node.lineno,
        signature=f"{prefix} {node.name}({', '.join(args)}){ret_s}",
        docstring=ast.get_docstring(node) or "",
        is_async=isinstance(node, ast.AsyncFunctionDef),
        return_type=ret,
        decorators=[ast.unparse(d) for d in node.decorator_list],
    )


def extract_subsystem_facts(repo_root: Path, subsystem_path: str) -> ModuleFacts:
    """Aggregate AST facts for a directory. Evidence only; not a README."""
    facts = ModuleFacts(path=subsystem_path)
    full = repo_root / subsystem_path
    if not full.exists():
        return facts
    imports: list[str] = []
    exports: list[str] = []
    constants: list[tuple[str, str, int]] = []
    for py_file in _iter_direct_files(full, "*.py"):
        rel = str(py_file.relative_to(repo_root))
        facts.files.append(rel)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            continue
        doc = ast.get_docstring(tree)
        if doc:
            facts.module_docstrings[rel] = doc
        exports.extend(_extract_all(tree))
        constants.extend(_extract_constants(tree))
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.ClassDef) and _public(node.name):
                methods = [
                    child
                    for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and _public(child.name)
                ]
                facts.classes.append(
                    ClassInfo(
                        name=node.name,
                        file=rel,
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        docstring=ast.get_docstring(node) or "",
                        methods=[m.name for m in methods],
                        method_details=[
                            {
                                "name": m.name,
                                "is_async": isinstance(m, ast.AsyncFunctionDef),
                                "return_type": _unparse(m.returns),
                                "docstring": ast.get_docstring(m) or "",
                                "line_start": m.lineno,
                            }
                            for m in methods[:8]
                        ],
                        decorators=[ast.unparse(d) for d in node.decorator_list],
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _public(node.name):
                facts.functions.append(_function_info(node, rel))
    for sh_file in _iter_direct_files(full, "*.sh"):
        rel = str(sh_file.relative_to(repo_root))
        if rel not in facts.files:
            facts.files.append(rel)
    facts.imports = sorted(set(imports))
    facts.exports = sorted(set(exports))
    facts.constants = constants
    return facts


# --------------------------------------------------------------------------
# Path and ownership primitives
# --------------------------------------------------------------------------


def resolve_under_root(repo_root: Path, rel: str) -> Path | None:
    cleaned = (rel or "").strip()
    if cleaned in FORBIDDEN_RELATIVE_PATHS:
        return None
    raw = Path(cleaned)
    if raw.is_absolute() or ".." in raw.parts:
        return None
    root = repo_root.resolve()
    dest = (root / raw).resolve()
    try:
        dest.relative_to(root)
    except ValueError:
        return None
    return None if dest == root else dest


def is_root_readme(repo_root: Path, dest: Path) -> bool:
    try:
        return dest.resolve() == (repo_root / ROOT_README).resolve()
    except OSError:
        return dest.name == "README.md" and dest.parent.resolve() == repo_root.resolve()


def _legacy_handwritten(text: str) -> bool:
    front = text.split("---", 2)
    if len(front) >= 3 and LEGACY_HANDWRITTEN_RE.search(front[1]):
        return True
    return bool(LEGACY_HANDWRITTEN_RE.search(text[:400]))


def _legacy_generated_shape(text: str) -> bool:
    if not LEGACY_HEADER_RE.search(text):
        return False
    found = {normalize_heading(match.group(1)) for match in HEADING_RE.finditer(text)}
    return all(normalize_heading(name) in found for name in LEGACY_REQUIRED_HEADINGS)


def classify_readme_text(text: str) -> ReadmeOwnership:
    """Ownership of an existing README body.

    ``generated``: carries the current ownership marker, or one of the two
    legacy markers this generator also wrote.
    ``legacy_generated``: written by the pre-marker generator (README_TEMPLATE
    header line plus its section set) and not opted out with
    ``auto_generated: false``; a refresh migrates it to the marker.
    ``handwritten``: everything else; never overwritten without ``--force``.

    The explicit opt-out is checked first and wins over a marker. Someone
    who wrote ``auto_generated: false`` into a file this generator once
    owned has said which of the two is in charge.
    """
    if _legacy_handwritten(text):
        return "handwritten"
    if owns_any_marker(text):
        return "generated"
    if _legacy_generated_shape(text):
        return "legacy_generated"
    return "handwritten"


def classify_readme(path: Path) -> ReadmeOwnership:
    if not path.is_file():
        return "missing"
    try:
        return classify_readme_text(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return "handwritten"


def is_handwritten(path: Path) -> bool:
    return classify_readme(path) == "handwritten"


def is_legacy_generated(path: Path) -> bool:
    return classify_readme(path) == "legacy_generated"


def is_generated(path: Path) -> bool:
    return classify_readme(path) in {"generated", "legacy_generated"}


def write_readme(path: Path, content: str, *, backup: bool) -> None:
    if backup and path.is_file():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(content, encoding="utf-8")


def normalize_heading(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "", cleaned).lower()


# --------------------------------------------------------------------------
# Qualification: the inventory is the sole automatic membership authority
# --------------------------------------------------------------------------


def _skip_prefixes(config: dict[str, Any]) -> tuple[str, ...]:
    extra = config.get("defaults", {}).get("skip_prefixes") or []
    values = [str(item).strip("/").replace("\\", "/") for item in extra]
    return tuple(dict.fromkeys((*DEFAULT_SKIP_PREFIXES, *values)))


def _skipped_rel(rel: str, prefixes: tuple[str, ...]) -> bool:
    return is_excluded_path(rel, prefixes)


#: Tokens `str.title()` gets wrong. Presentation only — this never decides
#: whether a directory is a target, so it is a casing table, not a path
#: allowlist. `github` titlecases to `Github`, which reads as a misspelling
#: of the product in a heading.
TITLE_CASING = {
    "adr": "ADR",
    "adrs": "ADRs",
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "cd": "CD",
    "ci": "CI",
    "cli": "CLI",
    "css": "CSS",
    "dag": "DAG",
    "dags": "DAGs",
    "db": "DB",
    "gcp": "GCP",
    "github": "GitHub",
    "gitlab": "GitLab",
    "gmp": "GMP",
    "html": "HTML",
    "http": "HTTP",
    "https": "HTTPS",
    "id": "ID",
    "ide": "IDE",
    "io": "IO",
    "json": "JSON",
    "llm": "LLM",
    "mcp": "MCP",
    "ml": "ML",
    "npm": "npm",
    "os": "OS",
    "pr": "PR",
    "prs": "PRs",
    "sdk": "SDK",
    "sql": "SQL",
    "ssh": "SSH",
    "tls": "TLS",
    "ui": "UI",
    "uri": "URI",
    "url": "URL",
    "ux": "UX",
    "vm": "VM",
    "yaml": "YAML",
}


def _humanize(posix: str) -> str:
    words = Path(posix).name.replace("_", " ").replace("-", " ").split()
    return " ".join(TITLE_CASING.get(word.lower(), word.title()) for word in words)


def spec_for_path(rel: str, config: dict[str, Any]) -> dict[str, Any]:
    posix = rel.replace("\\", "/").strip("/")
    for spec in (config.get("subsystems") or {}).values():
        if isinstance(spec, dict) and str(spec.get("path") or "").strip("/") == posix:
            return dict(spec)
    return {
        "path": posix,
        "title": _humanize(posix),
        "tier": "discovered",
        "description": "",
        "purpose": "",
    }


def resolve_inventory(
    repo_root: Path,
    config: dict[str, Any] | None = None,
    *,
    inventory: FiletreeInventory | None = None,
) -> FiletreeInventory:
    """The inventory this run treats as the membership authority."""
    config = config if config is not None else load_config(repo_root)
    prefixes = _skip_prefixes(config)
    source = inventory if inventory is not None else inventory_from_filetree(repo_root)
    if source is None:
        source = walk_inventory(repo_root, extra_skip=list(prefixes))
    return source


def _suppressed_paths(config: dict[str, Any]) -> set[str]:
    return {
        str(spec.get("path") or "").strip("/")
        for spec in (config.get("subsystems") or {}).values()
        if isinstance(spec, dict) and spec.get("skip")
    }


def discover_module_paths(
    repo_root: Path,
    config: dict[str, Any] | None = None,
    *,
    inventory: FiletreeInventory | None = None,
) -> list[str]:
    """Inventory-authorized README targets.

    Configuration may suppress a target with ``skip: true`` and decorate
    the rest, but it cannot add one. A config entry used to be enough to
    create a target the inventory had never seen, which made the overlay a
    second topology authority.
    """
    config = config if config is not None else load_config(repo_root)
    prefixes = _skip_prefixes(config)
    source = resolve_inventory(repo_root, config, inventory=inventory)
    suppressed = _suppressed_paths(config)
    return sorted(
        {
            row.path
            for row in source.modules
            if not _skipped_rel(row.path, prefixes) and row.path not in suppressed
        }
    )


def unauthorized_config_paths(
    repo_root: Path,
    config: dict[str, Any] | None = None,
    *,
    inventory: FiletreeInventory | None = None,
) -> list[str]:
    """Configured non-skip paths the inventory does not authorize.

    Reported rather than honoured, so stale configuration stays visible
    instead of quietly creating documentation targets.
    """
    config = config if config is not None else load_config(repo_root)
    authorized = {
        row.path for row in resolve_inventory(repo_root, config, inventory=inventory).modules
    }
    stale = {
        path
        for spec in (config.get("subsystems") or {}).values()
        if isinstance(spec, dict)
        and not spec.get("skip")
        and (path := str(spec.get("path") or "").strip("/"))
        and path not in authorized
    }
    return sorted(stale)


def _normalize_kind(kind: str) -> str:
    # `submodule` was a hierarchy relation, never a renderer identity.
    if kind == "submodule":
        return "module"
    return kind if kind in README_KINDS else "module"


def build_readme_targets(
    repo_root: Path,
    config: dict[str, Any] | None = None,
    *,
    inventory: FiletreeInventory | None = None,
) -> list[ReadmeTarget]:
    """Typed targets for every authorized path, kind carried from inventory."""
    config = config if config is not None else load_config(repo_root)
    source = resolve_inventory(repo_root, config, inventory=inventory)
    kinds = {row.path: _normalize_kind(row.kind) for row in source.modules}
    authorized = discover_module_paths(repo_root, config, inventory=source)
    targets: list[ReadmeTarget] = []
    for rel in authorized:
        spec = spec_for_path(rel, config)
        configured = str(spec.get("path") or "").strip("/") == rel and spec.get("tier") != (
            "discovered"
        )
        targets.append(
            ReadmeTarget(
                path=rel,
                kind=kinds.get(rel, "module"),  # type: ignore[arg-type]
                title=str(spec.get("title") or _humanize(rel)),
                configured_purpose=str(spec.get("purpose") or "").strip() or None,
                configured_description=str(spec.get("description") or "").strip() or None,
                tier=str(spec.get("tier") or "") or None,
                evidence=(
                    EvidenceRef(source="filetree.md", kind="inventory", detail=kinds.get(rel, "")),
                )
                + (
                    (EvidenceRef(source=str(CONFIG_PATH), kind="config_overlay", detail=rel),)
                    if configured
                    else ()
                ),
            )
        )
    return targets


# --------------------------------------------------------------------------
# Modelling and rendering
# --------------------------------------------------------------------------


def compile_readme_outputs(
    repo_root: Path,
    targets: list[ReadmeTarget],
    *,
    internal_paths: list[str] | None = None,
) -> list[tuple[ReadmeModel, str]]:
    """Compile and render every target. Pure: touches no destination file.

    ``internal_paths`` is what counts as first-party for dependency
    classification, and is deliberately wider than the target list:
    suppressing a directory decides whether to document it, not whether
    it is this repository's own code. Reading it off the targets made a
    suppressed `workflows/` import render as an external dependency.
    """
    internal_names = repository_module_names(
        repo_root,
        internal_paths if internal_paths is not None else [target.path for target in targets],
    )
    outputs: list[tuple[ReadmeModel, str]] = []
    for target in targets:
        model = compile_readme_model(repo_root, target, internal_names=internal_names)
        outputs.append((model, render_readme(model)))
    return outputs


def _model_from_facts(target: ReadmeTarget, facts: ModuleFacts) -> ReadmeModel:
    """Regroup aggregate facts back into per-file modules.

    ``ModuleFacts`` already records which file each symbol came from; the
    old renderer simply discarded that. Regrouping restores module
    identity without re-reading the tree, which keeps the compatibility
    renderer honest for callers that pass facts they extracted themselves.
    """
    by_file: dict[str, tuple[list[InterfaceDoc], list[InterfaceDoc]]] = {}
    for path in facts.files:
        if path.endswith(".py"):
            by_file.setdefault(path, ([], []))
    for cls in facts.classes:
        by_file.setdefault(cls.file, ([], []))[0].append(
            InterfaceDoc(name=cls.name, summary=summarize_docstring(cls.docstring))
        )
    for func in facts.functions:
        by_file.setdefault(func.file, ([], []))[1].append(
            InterfaceDoc(
                name=func.name,
                signature=func.signature,
                summary=summarize_docstring(func.docstring),
            )
        )
    modules: list[ModuleDoc] = []
    for path in sorted(by_file):
        classes, functions = by_file[path]
        doc = facts.module_docstrings.get(path) or ""
        modules.append(
            ModuleDoc(
                file=Path(path).name,
                name=Path(path).stem,
                purpose=summarize_docstring(doc),
                classes=tuple(classes),
                functions=tuple(functions),
                exports=tuple(facts.exports) if len(by_file) == 1 else (),
            )
        )
    shells = tuple(Path(path).name for path in facts.files if path.endswith(".sh"))
    purpose = target.configured_purpose
    if purpose is None and len(modules) == 1:
        purpose = modules[0].purpose
    return ReadmeModel(
        target=target,
        purpose=purpose,
        description=target.configured_description,
        modules=tuple(modules),
        shell_entrypoints=shells,
        dependencies=classify_dependencies(list(facts.imports), frozenset()),
    )


def generate_readme(
    name: str,
    config: dict[str, Any],
    facts: ModuleFacts,
    defaults: dict[str, Any],
) -> str:
    """Compatibility renderer for a single directory from extracted facts."""
    del name, defaults
    rel = str(config.get("path") or "").strip("/")
    kind = str(config.get("kind") or "").strip() or "module"
    target = ReadmeTarget(
        path=rel,
        kind=kind if kind in README_KINDS else "module",  # type: ignore[arg-type]
        title=str(config.get("title") or _humanize(rel)),
        configured_purpose=str(config.get("purpose") or "").strip() or None,
        configured_description=str(config.get("description") or "").strip() or None,
        tier=str(config.get("tier") or "") or None,
    )
    repo_root = config.get("__repo_root__")
    if repo_root and target.kind in {"corpus", "index", "skill"}:
        return render_readme(compile_readme_model(Path(str(repo_root)), target))
    return render_readme(_model_from_facts(target, facts))


# --------------------------------------------------------------------------
# Reconciliation
# --------------------------------------------------------------------------

_OWNED_SCAN_SKIP = {".git", ".venv", "node_modules", "__pycache__"}


def discover_owned_readmes(repo_root: Path) -> list[str]:
    """Every README.md on disk this generator owns, excluded subtrees included.

    Deliberately not restricted to authorized paths: a stale README left by
    an earlier, wrong classifier lives exactly where the current rules no
    longer look.
    """
    owned: list[str] = []
    for current, dirnames, filenames in repo_root.walk():
        dirnames[:] = sorted(
            name for name in dirnames if name not in _OWNED_SCAN_SKIP and name != ".git"
        )
        if "README.md" not in filenames:
            continue
        candidate = current / "README.md"
        try:
            rel = candidate.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if rel == "README.md":
            continue
        if classify_readme(candidate) == "generated":
            owned.append(rel)
    return sorted(owned)


def plan_module_readmes(
    repo_root: Path,
    *,
    config: dict[str, Any] | None = None,
    inventory: FiletreeInventory | None = None,
    changed: list[str] | None = None,
    force: bool = False,
    retire: bool = True,
) -> ReadmePlan:
    """Reconcile the authorized desired corpus against what is on disk.

    Pure: computes every action without touching a destination file, so a
    read-only run reports exactly the mutations a write run would make.
    """
    repo_root = repo_root.resolve()
    config = config if config is not None else load_config(repo_root)
    source = resolve_inventory(repo_root, config, inventory=inventory)
    targets = build_readme_targets(repo_root, config, inventory=source)
    if changed is not None:
        targets = [
            target
            for target in targets
            if any(path == target.path or path.startswith(target.path + "/") for path in changed)
        ]
    # First-party names come from the whole inventory plus the repository's
    # own top-level directories, never from the suppressed target list.
    internal_paths = sorted(
        {row.path for row in source.modules}
        | {
            child.name
            for child in repo_root.iterdir()
            if child.is_dir() and not child.name.startswith(".")
        }
    )
    outputs = compile_readme_outputs(repo_root, targets, internal_paths=internal_paths)
    findings: list[QualityFinding] = list(
        validate_readme_models(
            repo_root,
            outputs,
            authorized={target.path for target in targets},
        )
    )
    for stale in unauthorized_config_paths(repo_root, config, inventory=inventory):
        findings.append(
            QualityFinding(
                rule_id="readme.config.unauthorized_target",
                severity="ERROR",
                message=f"configured README metadata has no inventory-authorized target: {stale}",
                source=str(CONFIG_PATH),
            )
        )

    items: list[ReadmePlanItem] = []
    expected: set[str] = set()
    for model, rendered in outputs:
        target = model.target
        module_dir = resolve_under_root(repo_root, target.path)
        if module_dir is None or not module_dir.is_dir():
            continue
        dest = module_dir / "README.md"
        if is_root_readme(repo_root, dest):
            continue
        rel_dest = f"{target.path}/README.md"
        expected.add(rel_dest)
        ownership = classify_readme(dest)
        future = (
            marker_version(dest.read_text(encoding="utf-8")) if ownership == "generated" else None
        )
        if ownership == "missing":
            action, reason = "create", "authorized target has no README"
        elif future is not None and future > MARKER_VERSION:
            action, reason = (
                "conflict",
                f"written by format version {future}; this compiler understands {MARKER_VERSION}",
            )
        elif ownership == "handwritten" and not force:
            action, reason = "preserve", "handwritten README is never overwritten"
        else:
            current = dest.read_text(encoding="utf-8")
            if current == rendered:
                action, reason = "unchanged", "generated bytes already current"
            elif ownership == "legacy_generated":
                action, reason = "refresh", "legacy generated README migrates to the marker"
            elif ownership == "handwritten":
                action, reason = "refresh", "--force overrides handwritten preservation"
            else:
                action, reason = "refresh", "generated bytes are stale"
        items.append(
            ReadmePlanItem(
                path=rel_dest,
                action=action,  # type: ignore[arg-type]
                target=target,
                desired_content=rendered if action in {"create", "refresh"} else None,
                reason=reason,
            )
        )

    if retire and changed is None:
        for rel_dest in discover_owned_readmes(repo_root):
            if rel_dest in expected:
                continue
            text = (repo_root / rel_dest).read_text(encoding="utf-8")
            unowned = retirement_findings(rel_dest, text)
            if unowned:
                findings.extend(unowned)
                items.append(
                    ReadmePlanItem(
                        path=rel_dest,
                        action="conflict",
                        reason="generated shape without a strong ownership marker",
                    )
                )
                continue
            items.append(
                ReadmePlanItem(
                    path=rel_dest,
                    action="retire",
                    reason="generator-owned README at a no-longer-authorized target",
                )
            )

    items.sort(key=lambda item: (item.path, item.action))
    return ReadmePlan(items=tuple(items), findings=tuple(findings))


def apply_module_readme_plan(
    repo_root: Path,
    plan: ReadmePlan,
    *,
    backup: bool = False,
) -> list[str]:
    """Apply only the mutating actions. Returns the paths that changed."""
    repo_root = repo_root.resolve()
    mutated: list[str] = []
    for item in plan.items:
        if item.action not in MUTATING_ACTIONS:
            continue
        dest = resolve_under_root(repo_root, item.path)
        if dest is None or is_root_readme(repo_root, dest):
            continue
        if item.action == "retire":
            if dest.is_file():
                dest.unlink()
                mutated.append(item.path)
            continue
        if item.desired_content is None:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_readme(dest, item.desired_content, backup=backup)
        mutated.append(item.path)
    return mutated


def write_missing_module_readmes(
    repo_root: Path,
    *,
    write: bool = True,
    regenerate: bool = False,
    backup: bool = False,
    changed: list[str] | None = None,
    inventory: FiletreeInventory | None = None,
    config: dict[str, Any] | None = None,
    retire: bool = True,
    force: bool = False,
) -> list[str]:
    """Compatibility entry point over plan/apply.

    ``write=False`` is now a true dry run: the plan is computed in full and
    the mutations it would make are returned, rather than an empty list
    that made a read-only pass look like a clean repository.

    ``regenerate`` is accepted for compatibility. Refresh of a stale
    generator-owned README is unconditional now, because a corpus that only
    converges under a flag never converges.
    """
    del regenerate
    plan = plan_module_readmes(
        repo_root,
        config=config,
        inventory=inventory,
        changed=changed,
        force=force,
        retire=retire,
    )
    if not write:
        return [item.path for item in plan.mutations]
    return apply_module_readme_plan(repo_root, plan, backup=backup)


# --------------------------------------------------------------------------
# Config validation and reporting
# --------------------------------------------------------------------------


def validate_subsystem_config(
    key: str, config: dict[str, Any], repo_root: Path | None = None
) -> list[str]:
    errors: list[str] = []
    for field_name in ("path", "title", "tier", "description"):
        if not config.get(field_name):
            errors.append(f"{key}: missing {field_name}")
    unsupported = sorted(set(config) - SUPPORTED_OVERLAY_FIELDS)
    if unsupported:
        errors.append(f"{key}: unsupported overlay fields: {', '.join(unsupported)}")
    path = str(config.get("path") or "")
    if path and repo_root is not None and resolve_under_root(repo_root, path) is None:
        errors.append(f"{key}: path {path!r} is not a module directory under the repo")
    return errors


def validate_sections(
    repo_root: Path, key: str, config: dict[str, Any], defaults: dict[str, Any]
) -> list[str]:
    """Structural integrity of one target's README.

    The old per-section requirement map is not enforced: with kind-specific
    renderers a section list that every kind must carry does not exist, and
    demanding one is precisely what produced `_No public classes in this
    path._`. What is checked is what every generated README must carry —
    authoritative path metadata and an ownership marker.
    """
    del defaults
    module_dir = resolve_under_root(repo_root, str(config.get("path") or ""))
    if module_dir is None:
        return [f"{key}: refuses to treat {config.get('path')!r} as a module target"]
    dest = module_dir / "README.md"
    if is_root_readme(repo_root, dest):
        return [f"{key}: refuses to treat root README.md as a module target"]
    if not dest.is_file():
        return [f"{key}: README.md missing at {dest.relative_to(repo_root)}"]
    text = dest.read_text(encoding="utf-8")
    if classify_readme_text(text) == "handwritten":
        return []
    errors: list[str] = []
    if f"**Path:** `{config.get('path')}`" not in text and not any(
        marker in text for marker in LEGACY_MARKERS
    ):
        errors.append(f"{key}: README path metadata does not name {config.get('path')!r}")
    return errors


def list_subsystems(config: dict[str, Any], repo_root: Path | None = None) -> None:
    if repo_root is not None:
        for target in build_readme_targets(repo_root, config):
            print(f"{target.path.replace('/', '_')}\t{target.path}\t{target.title}\t{target.kind}")
        return
    for key, spec in (config.get("subsystems") or {}).items():
        flag = "skip" if spec.get("skip") else "live"
        print(f"{key}\t{spec.get('path')}\t{spec.get('title')}\t{flag}")


def report_gaps(repo_root: Path, config: dict[str, Any]) -> int:
    plan = plan_module_readmes(repo_root, config=config)
    buckets: dict[str, list[str]] = {}
    for item in plan.items:
        buckets.setdefault(item.action, []).append(item.path)
    for stale in unauthorized_config_paths(repo_root, config):
        print(f"stale\t{stale}\tunauthorized")
    for action in ("create", "refresh", "retire", "conflict", "preserve"):
        for path in buckets.get(action, []):
            directory = path[: -len("/README.md")] if path.endswith("/README.md") else path
            print(f"{action}\t{directory}")
    if not any(buckets.get(action) for action in ("create", "refresh", "retire", "conflict")):
        print("gaps\tnone")
    return 1 if buckets.get("conflict") else 0


def select_targets(
    config: dict[str, Any],
    *,
    repo_root: Path | None = None,
    subsystem: str | None,
    tier: str | None,
    path: str | None,
    title: str | None,
    force: bool = False,
) -> list[tuple[str, dict[str, Any]]]:
    """Explicit operator selection for the CLI.

    ``--path`` and ``--subsystem`` are manual actions and may name a
    directory the automatic inventory does not authorize. That is an
    operator decision, not configuration creating a target.
    """
    defaults = config.get("defaults") or {}
    items = config.get("subsystems") or {}
    if path:
        cleaned = path.rstrip("/")
        spec = spec_for_path(cleaned, config)
        if title:
            spec["title"] = title
        spec.setdefault("tier", "operations")
        spec.setdefault("description", defaults.get("description") or path)
        spec.setdefault("purpose", "")
        return [(cleaned.replace("/", "_"), spec)]
    if subsystem:
        if subsystem in items:
            spec = items[subsystem]
            if spec.get("skip") and not force:
                raise PermissionError(
                    f"{subsystem} is skip: true (handwritten); pass --force to generate"
                )
            return [(subsystem, spec)]
        guessed = subsystem.replace("_", "/")
        if repo_root is not None and (repo_root / guessed).is_dir():
            return [(subsystem, spec_for_path(guessed, config))]
        raise KeyError(subsystem)
    if repo_root is not None:
        selected: list[tuple[str, dict[str, Any]]] = []
        for target in build_readme_targets(repo_root, config):
            if tier and target.tier not in {tier, "discovered"}:
                continue
            spec = spec_for_path(target.path, config)
            spec["kind"] = target.kind
            selected.append((target.path.replace("/", "_"), spec))
        return selected
    selected = []
    for key, spec in items.items():
        if spec.get("skip"):
            continue
        if tier and spec.get("tier") != tier:
            continue
        selected.append((key, spec))
    return selected


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _print_plan(plan: ReadmePlan, *, verbose: bool) -> None:
    counts = plan.counts()
    ordered = ("create", "refresh", "unchanged", "preserve", "retire", "conflict")
    print(" ".join(f"{name}={counts[name]}" for name in ordered))
    if verbose:
        for item in plan.items:
            if item.action in {"unchanged", "preserve"}:
                continue
            print(f"{item.action}\t{item.path}\t{item.reason}")
    for finding in plan.findings:
        print(f"{finding.severity}\t{finding.rule_id}\t{finding.message}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="repository root")
    parser.add_argument("--subsystem", "-s")
    parser.add_argument("--tier", "-t")
    parser.add_argument("--path", "-p")
    parser.add_argument("--title")
    parser.add_argument("--dry-run", "-n", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--list", "-l", action="store_true")
    parser.add_argument("--plan", action="store_true", help="Report the reconciliation plan")
    parser.add_argument("--no-retire", action="store_true", help="Never retire owned READMEs")
    parser.add_argument(
        "--gaps", action="store_true", help="Report missing or invalid module README paths"
    )
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--validate-sections", action="store_true")
    parser.add_argument(
        "--skip-time-verify",
        action="store_true",
        help="Accepted no-op. This generator does not call external clocks.",
    )
    args = parser.parse_args(argv)
    repo_root = resolve_repo_root(args.root)
    config = load_config(repo_root)
    defaults = config.get("defaults") or {}

    if args.list:
        list_subsystems(config, repo_root)
        return 0

    if args.gaps:
        return report_gaps(repo_root, config)

    if args.validate or args.validate_sections:
        errors: list[str] = []
        for key, spec in (config.get("subsystems") or {}).items():
            errors.extend(validate_subsystem_config(key, spec, repo_root))
            if args.validate_sections and not spec.get("skip"):
                errors.extend(validate_sections(repo_root, key, spec, defaults))
        if errors:
            print("FAIL")
            for item in errors:
                print(f"  - {item}")
            return 1
        print(f"PASS {len(config.get('subsystems') or {})} subsystems")
        return 0

    # Whole-repository reconciliation, unless an explicit target is named.
    if args.plan or not (args.subsystem or args.path):
        plan = plan_module_readmes(
            repo_root,
            config=config,
            force=args.force,
            retire=not args.no_retire,
        )
        if args.plan or args.dry_run:
            _print_plan(plan, verbose=args.verbose or args.plan)
            return 1 if plan.errors else 0
        mutated = apply_module_readme_plan(repo_root, plan, backup=args.backup)
        for path in mutated:
            print(f"wrote {path}")
        _print_plan(plan, verbose=args.verbose)
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"mutated={len(mutated)} at={stamp}")
        return 1 if plan.errors else 0

    try:
        targets = select_targets(
            config,
            repo_root=repo_root,
            subsystem=args.subsystem,
            tier=args.tier,
            path=args.path,
            title=args.title,
            force=args.force,
        )
    except KeyError as exc:
        print(f"unknown subsystem: {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    generated = 0
    skipped = 0
    inventory_kinds = {
        row.path: _normalize_kind(row.kind) for row in resolve_inventory(repo_root, config).modules
    }
    for name, spec in targets:
        rel = str(spec.get("path") or "")
        module_dir = resolve_under_root(repo_root, rel)
        if module_dir is None:
            print(f"skip {name}: refuses path {rel!r}")
            skipped += 1
            continue
        dest = module_dir / "README.md"
        if is_root_readme(repo_root, dest):
            print(f"skip {name}: refuses to write root README.md")
            skipped += 1
            continue
        if not module_dir.exists():
            print(f"skip {name}: path missing ({rel})")
            skipped += 1
            continue
        if dest.is_file() and is_handwritten(dest) and not args.force:
            print(f"skip {name}: handwritten README")
            skipped += 1
            continue
        spec = dict(spec)
        spec["__repo_root__"] = str(repo_root)
        spec.setdefault("kind", inventory_kinds.get(rel.strip("/"), "module"))
        content = generate_readme(name, spec, extract_subsystem_facts(repo_root, rel), defaults)
        if args.dry_run:
            print(f"--- {dest.relative_to(repo_root)} ---")
            print(content[:800])
            generated += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_readme(dest, content, backup=args.backup)
        print(f"wrote {dest.relative_to(repo_root)}")
        generated += 1
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"generated={generated} skipped={skipped} at={stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
