#!/usr/bin/env python3
"""Module, corpus, and index README generator owned by l9-update-agent-docs.

Walks the repository for code modules (AST) and document/config folders
(type index). Never writes the repository-root README.md. Does not call
an LLM or the donor repo.
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
    corpus_files,
    inventory_from_filetree,
    walk_inventory,
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
# Directories that may appear in the filetree but must never receive a
# generated README.
#
# `rules/` is a budgeted surface: check_rules_standard.py fails on any
# `rules/*.md` that is not a RULES-MANIFEST, so emitting `rules/README.md`
# turns governance-self-check red. Archived and completed trees document
# retired material, and the live compiler skip never rewrites them, so a
# README written there keeps whatever stale `Path:` it was born with.
README_SKIP_PREFIXES = ("rules",)
README_SKIP_DIR_NAMES = frozenset({"archive", "_archived", "COMPLETED"})
ROOT_README = Path("README.md")
FORBIDDEN_RELATIVE_PATHS = {"", ".", ".."}
GENERATED_MARKER = "<!-- l9-module-readme: generated-from-ast -->"
FOLDER_MARKER = "<!-- l9-folder-readme: generated-from-tree -->"
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
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
# Pre-marker contract of scripts/generate_subsystem_readmes.py: a README whose
# front matter (or first 400 bytes) declares `auto_generated: false` is
# handwritten; everything that generator wrote carries the README_TEMPLATE
# header line and section set below, but no marker.
LEGACY_HANDWRITTEN_RE = re.compile(r"^auto_generated:\s*false\b", re.MULTILINE | re.IGNORECASE)
LEGACY_HEADER_RE = re.compile(r"^\*\*Path:\*\* `[^`\n]+` \| \*\*Tier:\*\* \S.*$", re.MULTILINE)
LEGACY_REQUIRED_HEADINGS = ("Purpose", "Components", "Functions", "Exports", "Dependencies")
ReadmeOwnership = Literal["missing", "generated", "legacy_generated", "handwritten"]

README_TEMPLATE = (
    """# {title}

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
    + GENERATED_MARKER
    + "\n"
)
FOLDER_TEMPLATE = (
    """# {title}

**Path:** `{path}` | **Kind:** {kind}

## Purpose

{purpose}

## File types

{file_types}

## Contents

{contents}

"""
    + FOLDER_MARKER
    + "\n"
)


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
    if node is None:
        return None
    return ast.unparse(node)


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
        if not path.is_file():
            continue
        if _skip_nested(module_dir, path):
            continue
        if path.name.startswith("test_"):
            continue
        files.append(path)
    return files


def _iter_python_files(root: Path) -> list[Path]:
    return _iter_direct_files(root, "*.py")


def _iter_shell_files(root: Path) -> list[Path]:
    return _iter_direct_files(root, "*.sh")


def _extract_all(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                value = node.value
                if isinstance(value, (ast.List, ast.Tuple)):
                    for elt in value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            names.append(elt.value)
    return names


def _extract_constants(tree: ast.Module) -> list[tuple[str, str, int]]:
    found: list[tuple[str, str, int]] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant):
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
    facts = ModuleFacts(path=subsystem_path)
    full = repo_root / subsystem_path
    if not full.exists():
        return facts
    imports: list[str] = []
    exports: list[str] = []
    constants: list[tuple[str, str, int]] = []
    for py_file in _iter_python_files(full):
        rel = str(py_file.relative_to(repo_root))
        facts.files.append(rel)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        if not isinstance(tree, ast.Module):
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
    for sh_file in _iter_shell_files(full):
        rel = str(sh_file.relative_to(repo_root))
        if rel not in facts.files:
            facts.files.append(rel)
    facts.imports = sorted(set(imports))
    facts.exports = sorted(set(exports))
    facts.constants = constants
    return facts


def _first_line(text: str, fallback: str) -> str:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    return line or fallback


def render_components(facts: ModuleFacts) -> str:
    blocks: list[str] = []
    for cls in facts.classes[:12]:
        summary = _first_line(cls.docstring, "No description")
        methods = ", ".join(f"`{name}`" for name in cls.methods[:8]) or "_none_"
        blocks.append(
            f"### `{cls.name}`\n\n"
            f"{summary}\n\n"
            f"- File: `{cls.file}` (L{cls.line_start}–{cls.line_end})\n"
            f"- Methods: {methods}"
        )
    shells = [path for path in facts.files if path.endswith(".sh")]
    if shells:
        listed = "\n".join(f"- `{path}`" for path in shells[:20])
        blocks.append(f"### Shell entrypoints\n\n{listed}")
    if not blocks:
        return "_No public classes in this path._"
    return "\n\n".join(blocks)


def render_functions(facts: ModuleFacts) -> str:
    if not facts.functions:
        return "_No public module-level functions._"
    lines = []
    # The same signature can be defined in several modules of one package
    # (`analyze()` is the common case); one row per distinct signature.
    seen: set[str] = set()
    for func in facts.functions:
        if func.signature in seen:
            continue
        seen.add(func.signature)
        summary = _first_line(func.docstring, "")
        extra = f" — {summary}" if summary else ""
        lines.append(f"- `{func.signature}`{extra}")
        if len(lines) == 20:
            break
    return "\n".join(lines)


def render_exports(facts: ModuleFacts) -> str:
    if not facts.exports:
        return "_No `__all__` exports._"
    shown = facts.exports[:20]
    body = ", ".join(f"`{name}`" for name in shown)
    if len(facts.exports) > 20:
        body += f" (+{len(facts.exports) - 20} more)"
    return body


def render_dependencies(facts: ModuleFacts) -> str:
    if not facts.imports:
        return "_No imports parsed._"
    first_party = [name for name in facts.imports if not name.startswith((".",))]
    shown = first_party[:24] or facts.imports[:24]
    return ", ".join(f"`{name}`" for name in shown)


def _fill(template: str, values: dict[str, str]) -> str:
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", value)
    return out


def generate_readme(
    name: str,
    config: dict[str, Any],
    facts: ModuleFacts,
    defaults: dict[str, Any],
) -> str:
    del name, defaults
    purpose = str(config.get("purpose") or config.get("description") or "").strip()
    description = str(config.get("description") or "").strip()
    if facts.module_docstrings and not purpose:
        purpose = next(iter(facts.module_docstrings.values())).splitlines()[0]
    return _fill(
        README_TEMPLATE,
        {
            "title": str(config.get("title") or config["path"]),
            "path": str(config["path"]),
            "tier": str(config.get("tier") or "unknown"),
            "purpose": purpose or "AST-extracted module documentation.",
            "description": description,
            "components": render_components(facts),
            "functions": render_functions(facts),
            "exports": render_exports(facts),
            "dependencies": render_dependencies(facts),
        },
    )


def _generate_folder_readme(rel: str, kind: str, folder: Path, spec: dict[str, Any]) -> str:
    files = corpus_files(folder)
    counts: dict[str, int] = {}
    for name in files:
        label = CORPUS_TYPE_LABELS.get(Path(name).suffix.lower(), "Other")
        counts[label] = counts.get(label, 0) + 1
    if kind == "index":
        purpose = (
            str(spec.get("purpose") or "").strip() or "Index of child modules and document folders."
        )
        children = sorted(
            child.name
            for child in folder.iterdir()
            if child.is_dir() and not child.name.startswith(".")
        )
        file_types = "_No files in this directory; see child folders._"
        contents = (
            "\n".join(f"- `{name}/`" for name in children) if children else "_No child folders._"
        )
    elif files:
        labels = ", ".join(f"{count} {label}" for label, count in sorted(counts.items()))
        purpose = str(spec.get("purpose") or "").strip() or f"This directory holds {labels}."
        file_types = "\n".join(f"- {label}: {count}" for label, count in sorted(counts.items()))
        contents = "\n".join(f"- `{name}`" for name in files)
    else:
        purpose = (
            str(spec.get("purpose") or "").strip()
            or "This directory is reserved. It has no files yet."
        )
        file_types = "_No files yet._"
        contents = "_Empty._"
    return _fill(
        FOLDER_TEMPLATE,
        {
            "title": str(spec.get("title") or _titleize(Path(rel).name)),
            "path": rel,
            "kind": kind,
            "purpose": purpose,
            "file_types": file_types,
            "contents": contents,
        },
    )


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
    if dest == root:
        return None
    return dest


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

    ``generated``: carries GENERATED_MARKER or FOLDER_MARKER, so this generator owns it.
    ``legacy_generated``: written by the pre-marker generator (README_TEMPLATE
    header line plus its section set) and not opted out with
    ``auto_generated: false``; a refresh migrates it to the marker.
    ``handwritten``: everything else; never overwritten without ``--force``.
    """
    if GENERATED_MARKER in text or FOLDER_MARKER in text:
        return "generated"
    if _legacy_handwritten(text):
        return "handwritten"
    if _legacy_generated_shape(text):
        return "legacy_generated"
    return "handwritten"


def classify_readme(path: Path) -> ReadmeOwnership:
    if not path.is_file():
        return "missing"
    return classify_readme_text(path.read_text(encoding="utf-8"))


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


def validate_subsystem_config(
    key: str, config: dict[str, Any], repo_root: Path | None = None
) -> list[str]:
    errors: list[str] = []
    for field_name in ("path", "title", "tier", "description"):
        if not config.get(field_name):
            errors.append(f"{key}: missing {field_name}")
    path = str(config.get("path") or "")
    if path and repo_root is not None and resolve_under_root(repo_root, path) is None:
        errors.append(f"{key}: path {path!r} is not a module directory under the repo")
    return errors


def normalize_heading(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "", cleaned).lower()


def validate_sections(
    repo_root: Path, key: str, config: dict[str, Any], defaults: dict[str, Any]
) -> list[str]:
    module_dir = resolve_under_root(repo_root, str(config.get("path") or ""))
    if module_dir is None:
        return [f"{key}: refuses to treat {config.get('path')!r} as a module target"]
    dest = module_dir / "README.md"
    if is_root_readme(repo_root, dest):
        return [f"{key}: refuses to treat root README.md as a module target"]
    if dest.is_file() and is_handwritten(dest):
        return []
    if not dest.is_file():
        return [f"{key}: README.md missing at {dest.relative_to(repo_root)}"]
    sections = config.get("sections") or defaults.get("sections") or {}
    required = [
        name for name, spec in sections.items() if isinstance(spec, dict) and spec.get("required")
    ]
    found = {
        normalize_heading(match.group(1))
        for match in HEADING_RE.finditer(dest.read_text(encoding="utf-8"))
    }
    missing = [name for name in required if normalize_heading(name) not in found]
    if missing:
        return [f"{key}: missing required sections: {', '.join(missing)}"]
    return []


def _skip_prefixes(config: dict[str, Any]) -> tuple[str, ...]:
    extra = config.get("defaults", {}).get("skip_prefixes") or []
    values = [str(item).strip("/").replace("\\", "/") for item in extra]
    return tuple(dict.fromkeys((*DEFAULT_SKIP_PREFIXES, *README_SKIP_PREFIXES, *values)))


def _skipped_rel(rel: str, prefixes: tuple[str, ...]) -> bool:
    posix = rel.replace("\\", "/").strip("/")
    if not posix:
        return True
    parts = set(Path(posix).parts)
    if parts & SKIP_DIR_NAMES:
        return True
    if parts & README_SKIP_DIR_NAMES:
        return True
    if "tests" in parts:
        return True
    return any(posix == prefix or posix.startswith(prefix + "/") for prefix in prefixes)


# str.title() alone produced `Github` and, for a leading-underscore folder
# like `_runtime`, a heading that started with a space.
TITLE_CASING = {
    "api": "API",
    "aws": "AWS",
    "cli": "CLI",
    "github": "GitHub",
    "ide": "IDE",
    "json": "JSON",
    "l9": "L9",
    "mcp": "MCP",
    "pe": "PE",
    "pr": "PR",
    "sdk": "SDK",
    "ssot": "SSOT",
    "ui": "UI",
    "wip": "WIP",
    "yaml": "YAML",
}


def _titleize(name: str) -> str:
    words = [word for word in name.replace("_", " ").replace("-", " ").split() if word]
    return " ".join(TITLE_CASING.get(word.lower(), word.title()) for word in words)


def spec_for_path(rel: str, config: dict[str, Any]) -> dict[str, Any]:
    posix = rel.replace("\\", "/").strip("/")
    for spec in (config.get("subsystems") or {}).values():
        if isinstance(spec, dict) and str(spec.get("path") or "").strip("/") == posix:
            return dict(spec)
    title = _titleize(Path(posix).name)
    return {
        "path": posix,
        "title": title,
        "tier": "discovered",
        "description": "",
        "purpose": "",
    }


def discover_module_paths(
    repo_root: Path,
    config: dict[str, Any] | None = None,
    *,
    inventory: FiletreeInventory | None = None,
) -> list[str]:
    config = config if config is not None else load_config(repo_root)
    prefixes = _skip_prefixes(config)
    found: set[str] = set()
    source = inventory if inventory is not None else inventory_from_filetree(repo_root)
    if source is None:
        source = walk_inventory(repo_root, extra_skip=list(prefixes))
    found.update(row.path for row in source.modules if not _skipped_rel(row.path, prefixes))
    for spec in (config.get("subsystems") or {}).values():
        if not isinstance(spec, dict) or spec.get("skip"):
            continue
        path = str(spec.get("path") or "").strip("/")
        if path and not _skipped_rel(path, prefixes):
            found.add(path)
    return sorted(found)


def write_missing_module_readmes(
    repo_root: Path,
    *,
    write: bool = True,
    regenerate: bool = False,
    backup: bool = False,
    changed: list[str] | None = None,
    inventory: FiletreeInventory | None = None,
) -> list[str]:
    if not write:
        return []
    config = load_config(repo_root)
    defaults = config.get("defaults") or {}
    prefixes = _skip_prefixes(config)
    source = inventory if inventory is not None else inventory_from_filetree(repo_root)
    if source is None:
        source = walk_inventory(repo_root, extra_skip=list(prefixes))
    discovered = discover_module_paths(repo_root, config, inventory=source)
    kinds = {row.path: row.kind for row in source.modules}
    # Optional CLI scope only. repo_docs.py must not pass `changed` — existing
    # modules without a README stay in the gap fill until they have one.
    if changed is not None:
        discovered = [
            rel
            for rel in discovered
            if any(path == rel or path.startswith(rel + "/") for path in changed)
        ]
    mutations: list[str] = []
    for rel in discovered:
        module_dir = resolve_under_root(repo_root, rel)
        if module_dir is None or not module_dir.exists():
            continue
        dest = module_dir / "README.md"
        if is_root_readme(repo_root, dest):
            continue
        if dest.is_file():
            if is_handwritten(dest):
                continue
            if not regenerate:
                continue
        spec = spec_for_path(rel, config)
        kind = kinds.get(rel, "module")
        if kind in {"corpus", "index"}:
            content = _generate_folder_readme(rel, kind, module_dir, spec)
        else:
            facts = extract_subsystem_facts(repo_root, rel)
            content = generate_readme(rel.replace("/", "_"), spec, facts, defaults)
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_readme(dest, content, backup=backup)
        mutations.append(f"{rel}/README.md")
    return mutations


def list_subsystems(config: dict[str, Any], repo_root: Path | None = None) -> None:
    if repo_root is not None:
        for path in discover_module_paths(repo_root, config):
            spec = spec_for_path(path, config)
            print(f"{path.replace('/', '_')}\t{path}\t{spec.get('title')}\tdiscovered")
        return
    items = config.get("subsystems") or {}
    for key, spec in items.items():
        flag = "skip" if spec.get("skip") else "live"
        print(f"{key}\t{spec.get('path')}\t{spec.get('title')}\t{flag}")


def report_gaps(repo_root: Path, config: dict[str, Any]) -> int:
    stale: list[str] = []
    handwritten: list[str] = []
    legacy: list[str] = []
    missing: list[str] = []
    for rel in discover_module_paths(repo_root, config):
        module_dir = resolve_under_root(repo_root, rel)
        if module_dir is None:
            stale.append(f"{rel}\tinvalid")
            continue
        if not module_dir.exists():
            stale.append(f"{rel}\tmissing")
            continue
        ownership = classify_readme(module_dir / "README.md")
        if ownership == "missing":
            missing.append(rel)
        elif ownership == "handwritten":
            handwritten.append(rel)
        elif ownership == "legacy_generated":
            legacy.append(rel)
    for row in stale:
        print(f"stale\t{row}")
    for row in missing:
        print(f"missing\t{row}")
    for row in legacy:
        print(f"legacy\t{row}")
    for row in handwritten:
        print(f"handwritten\t{row}")
    if not stale and not missing and not legacy and not handwritten:
        print("gaps\tnone")
    return 1 if stale else 0


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
    defaults = config.get("defaults") or {}
    items = config.get("subsystems") or {}
    if path:
        cleaned = path.rstrip("/")
        name = cleaned.replace("/", "_")
        spec = spec_for_path(cleaned, config)
        if title:
            spec["title"] = title
        spec.setdefault("tier", "operations")
        spec.setdefault("description", defaults.get("description") or path)
        spec.setdefault("purpose", "")
        return [(name, spec)]
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
        for rel in discover_module_paths(repo_root, config):
            spec = spec_for_path(rel, config)
            if spec.get("skip") and not force:
                continue
            if tier and spec.get("tier") not in {tier, "discovered"}:
                continue
            selected.append((rel.replace("/", "_"), spec))
        return selected
    selected = []
    for key, spec in items.items():
        if spec.get("skip"):
            continue
        if tier and spec.get("tier") != tier:
            continue
        selected.append((key, spec))
    return selected


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
    missing_only = not args.regenerate and not args.subsystem and not args.path
    for name, spec in targets:
        module_dir = resolve_under_root(repo_root, str(spec.get("path") or ""))
        if module_dir is None:
            print(f"skip {name}: refuses path {spec.get('path')!r}")
            skipped += 1
            continue
        dest = module_dir / "README.md"
        if is_root_readme(repo_root, dest):
            print(f"skip {name}: refuses to write root README.md")
            skipped += 1
            continue
        if not module_dir.exists():
            print(f"skip {name}: path missing ({spec['path']})")
            skipped += 1
            continue
        if dest.is_file() and is_handwritten(dest) and not args.force:
            print(f"skip {name}: handwritten README")
            skipped += 1
            continue
        if dest.is_file() and missing_only and not args.force:
            print(f"skip {name}: README already present")
            skipped += 1
            continue
        facts = extract_subsystem_facts(repo_root, spec["path"])
        if args.verbose:
            print(
                f"{name}: files={len(facts.files)} "
                f"classes={len(facts.classes)} functions={len(facts.functions)}"
            )
        content = generate_readme(name, spec, facts, defaults)
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
