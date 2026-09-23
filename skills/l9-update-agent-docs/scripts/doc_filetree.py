#!/usr/bin/env python3
"""Deterministic root filetree.md inventory owned by l9-update-agent-docs.

Walks the live tree in code, writes filetree.md, and exposes the module
index used to diagnose missing module/submodule README files. Does not
call an LLM or the donor repo.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from doc_owned_write import Admission, apply_owned_write
from doc_policy import repo_slug, resolve_under_root
from source_facts import load_source_evidence_registry, source_language

FILETREE_FILENAME = "filetree.md"
FILETREE_SURFACE_ID = "filetree"
FILETREE_MARKER = "<!-- l9-filetree: generated-from-tree -->"
MODULE_MARKERS = {"SKILL.md", "__init__.py"}
INTEREST_NAMES = MODULE_MARKERS | {"README.md"}
# Document/config mix that is not a code module. Names are generic so any
# repo can match; do not add repository-specific paths here.
CORPUS_SUFFIXES = {".md", ".markdown", ".yaml", ".yml", ".json", ".toml", ".sql", ".csv"}
CORPUS_DIR_NAMES = frozenset(
    {
        "audits",
        "config",
        "configs",
        "contracts",
        "docs",
        "examples",
        "learning",
        "pipeline",
        "policies",
        "profiles",
        "prompts",
        "protocols",
        "registry",
        "reports",
        "schema",
        "schemas",
        "security",
        "telemetry",
    }
)
# Never a README target at any depth (typed by the name, or campaign residue).
# Structural names only: a repository-specific path here would make the
# inventory an allowlist instead of a rule.
SKIP_LEAF_NAMES = frozenset(
    {
        "assets",
        "deliverables",
        "drafts",
        "fixtures",
        "generated",
        "handoff",
        "node_modules",
        "receipts",
    }
)
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".l9",
    ".claude",
}
# One normalized set so exclusion is decided once, for every path segment,
# before any classification runs. Membership of a parent excludes the whole
# subtree (INV-RD-003): `foo/fixtures/positive` is as excluded as `foo/fixtures`.
EXCLUDED_SEGMENTS = frozenset(
    {name.lower() for name in SKIP_LEAF_NAMES}
    | {name.lower() for name in SKIP_DIR_NAMES}
    | {"tests", "_archived"}
)
DEFAULT_SKIP_PREFIXES = (
    "WIP",
    "docs",
    "tests",
    "environment/generated",
    "ops/generated",
    "skills/_archived",
    "commands/_archived",
    "workflows/_archived",
)
# `submodule` is legacy: it was a hierarchy relation, never a renderer
# identity, and is now emitted as `module`. Parsing still accepts it so an
# inventory written by an older revision stays readable.
MODULE_ROW_RE = re.compile(
    r"^\|\s+`([^`]+)`\s+\|\s+"
    r"(skill|module|submodule|subsystem|corpus|index)"
    r"\s+\|\s+(\d+)\s+\|\s+(present|missing)\s+\|\s*$"
)
#: A directory with this many direct source files is a subsystem rather than
#: a single module: the renderer must keep the files apart.
SUBSYSTEM_SOURCE_THRESHOLD = 2
ROOT_FILE_RE = re.compile(r"^- `([^`]+)`\s*$")


@dataclass
class ModuleRow:
    path: str
    kind: str
    sources: int
    readme: str
    files: list[str] = field(default_factory=list)


@dataclass
class FiletreeInventory:
    root_files: list[str] = field(default_factory=list)
    modules: list[ModuleRow] = field(default_factory=list)
    tree_dirs: list[str] = field(default_factory=list)


def skip_prefixes(extra: list[str] | None = None) -> tuple[str, ...]:
    values = [str(item).strip("/").replace("\\", "/") for item in extra or []]
    return tuple(dict.fromkeys((*DEFAULT_SKIP_PREFIXES, *values)))


def is_excluded_path(rel: str, prefixes: tuple[str, ...]) -> bool:
    """Whole-subtree exclusion, decided before any classification.

    Matching is on whole path segments, never substrings: `generated-data`
    is a real directory and must survive while `generated` is excluded. A
    descendant of an excluded directory is excluded too, so admitting a
    module before applying leaf exclusion — the defect that put generated
    READMEs under `fixtures/` — is structurally impossible here.
    """
    posix = rel.replace("\\", "/").strip("/")
    if not posix:
        return True
    parts = tuple(Path(posix).parts)
    if any(part.startswith(".") for part in parts):
        return True
    if any(part.lower() in EXCLUDED_SEGMENTS for part in parts):
        return True
    return any(posix == prefix or posix.startswith(prefix + "/") for prefix in prefixes)


def skipped_rel(rel: str, prefixes: tuple[str, ...]) -> bool:
    """Compatibility alias of :func:`is_excluded_path`."""
    return is_excluded_path(rel, prefixes)


def interest_files(path: Path) -> list[str]:
    names: list[str] = []
    try:
        children = sorted(path.iterdir(), key=lambda item: item.name)
    except OSError:
        return names
    registry = load_source_evidence_registry()
    for child in children:
        if not child.is_file() or child.name.startswith("."):
            continue
        if child.name.startswith("test_"):
            continue
        if child.name in INTEREST_NAMES or source_language(child, registry):
            names.append(child.name)
    return names


def corpus_files(path: Path) -> list[str]:
    names: list[str] = []
    try:
        children = sorted(path.iterdir(), key=lambda item: item.name)
    except OSError:
        return names
    for child in children:
        if not child.is_file() or child.name.startswith("."):
            continue
        if child.name.startswith("test_") or child.name == "README.md":
            continue
        if child.suffix.lower() in CORPUS_SUFFIXES:
            names.append(child.name)
    return names


def is_module_dir(path: Path) -> bool:
    registry = load_source_evidence_registry()
    for name in interest_files(path):
        if name in MODULE_MARKERS:
            return True
        if source_language(path / name, registry):
            return True
    return False


def is_skill_root(path: Path) -> bool:
    """A directory whose own `SKILL.md` is the authoritative contract."""
    return (path / "SKILL.md").is_file()


def direct_source_count(path: Path) -> int:
    registry = load_source_evidence_registry()
    return sum(1 for name in interest_files(path) if source_language(path / name, registry))


def code_kind(path: Path) -> str | None:
    """Documentation kind for a directory holding implementation material.

    A skill root is a skill however much code sits beside `SKILL.md`; the
    contract, not the AST, is what a reader needs. Otherwise the split is
    between one module and a coherent multi-module boundary, because those
    two want different renderings, not different facts.
    """
    if is_skill_root(path):
        return "skill"
    if not is_module_dir(path):
        return None
    if direct_source_count(path) >= SUBSYSTEM_SOURCE_THRESHOLD:
        return "subsystem"
    return "module"


def under_skill_pack(root: Path, rel: str) -> bool:
    current = root
    for part in Path(rel).parts[:-1]:
        current = current / part
        if (current / "SKILL.md").is_file():
            return True
    return False


def is_corpus_dir(root: Path, rel: str, path: Path) -> bool:
    """A document/config folder worth a type index.

    An empty directory never qualifies. The previous rule admitted a bare
    generic name at depth 0, which produced READMEs whose only statement
    was that the directory was reserved and had no files — a target the
    reader gains nothing from.
    """
    name = Path(rel).name.lower()
    if under_skill_pack(root, rel) and Path(rel).name != "scripts":
        return False
    if is_skill_root(path) or is_module_dir(path):
        return False
    files = corpus_files(path)
    if not files:
        return False
    depth = rel.count("/")
    if len(files) >= 2:
        return True
    if depth == 0:
        return True
    return name in CORPUS_DIR_NAMES and depth <= 1


def walk_inventory(root: Path, extra_skip: list[str] | None = None) -> FiletreeInventory:
    root = root.resolve()
    prefixes = skip_prefixes(extra_skip)
    inventory = FiletreeInventory()
    inventory.root_files = sorted(
        child.name for child in root.iterdir() if child.is_file() and not child.name.startswith(".")
    )
    found: list[ModuleRow] = []
    seen: dict[str, Path] = {}
    for current, dirnames, _filenames in root.walk():
        try:
            rel = current.relative_to(root).as_posix()
        except ValueError:
            dirnames[:] = []
            continue
        if rel != "." and is_excluded_path(rel, prefixes):
            dirnames[:] = []
            continue
        # Prune before descending so no descendant of an excluded directory
        # is ever classified (INV-RD-003).
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not is_excluded_path(f"{rel}/{name}" if rel != "." else name, prefixes)
        )
        if rel == ".":
            continue
        inventory.tree_dirs.append(rel)
        seen[rel] = current
        files = interest_files(current)
        kind = code_kind(current)
        if kind is not None:
            found.append(
                ModuleRow(
                    path=rel,
                    kind=kind,
                    sources=direct_source_count(current),
                    readme="present" if "README.md" in files else "missing",
                    files=files,
                )
            )
    code_paths = {row.path for row in found}
    # Corpus candidacy is decided but not committed: a directory that also
    # parents two or more qualifying children is an index, because its
    # children are the structure a reader came for. `skills/` holds a
    # manifest or two and 59 skill packs; listing the manifests and hiding
    # the packs answers the wrong question.
    corpus_candidates = {
        rel
        for rel, current in seen.items()
        if rel not in code_paths and is_corpus_dir(root, rel, current)
    }
    qualifying = code_paths | corpus_candidates
    indexes: set[str] = set()
    # Deepest first. Parent qualification depends only on already-qualified
    # direct children, so one bottom-up pass reaches the fixed point: a
    # parent-first pass left every index whose children qualified later
    # permanently unqualified.
    for rel in sorted(seen, key=lambda item: (len(Path(item).parts), item), reverse=True):
        if rel in code_paths or rel in indexes:
            continue
        if under_skill_pack(root, rel) and Path(rel).name != "scripts":
            continue
        immediate = [
            child
            for child in qualifying
            if child.startswith(rel + "/") and "/" not in child[len(rel) + 1 :]
        ]
        if len(immediate) < 2:
            continue
        indexes.add(rel)
        qualifying.add(rel)
        found.append(
            ModuleRow(
                path=rel,
                kind="index",
                sources=len(immediate),
                readme="present" if (seen[rel] / "README.md").is_file() else "missing",
                files=corpus_files(seen[rel]),
            )
        )
    for rel in sorted(corpus_candidates - indexes):
        current = seen[rel]
        files = corpus_files(current)
        found.append(
            ModuleRow(
                path=rel,
                kind="corpus",
                sources=len(files),
                readme="present" if (current / "README.md").is_file() else "missing",
                files=files,
            )
        )
    inventory.modules = sorted(found, key=lambda row: row.path)
    return inventory


def render_filetree(inventory: FiletreeInventory, title: str) -> str:
    root_lines = [f"- `{name}`" for name in inventory.root_files] or ["_none_"]
    module_lines = [
        "| Path | Kind | Sources | README |",
        "| --- | --- | --- | --- |",
    ]
    if inventory.modules:
        module_lines.extend(
            f"| `{row.path}` | {row.kind} | {row.sources} | {row.readme} |"
            for row in inventory.modules
        )
    else:
        module_lines.append("| _none_ | module | 0 | missing |")
    tree_lines = ["```", "."]
    files_by_dir = {row.path: row.files for row in inventory.modules}
    for rel in inventory.tree_dirs:
        depth = rel.count("/")
        indent = "  " * depth
        tree_lines.append(f"{indent}{Path(rel).name}/")
        for name in files_by_dir.get(rel, []):
            tree_lines.append(f"{indent}  {name}")
    tree_lines.append("```")
    return "\n".join(
        [
            "# Filetree",
            "",
            f"**Repository:** `{title}`",
            "",
            "Projection only. Generated from the live tree. Not authority.",
            "",
            FILETREE_MARKER,
            "",
            "## Root files",
            "",
            *root_lines,
            "",
            "## Modules",
            "",
            *module_lines,
            "",
            "## Tree",
            "",
            *tree_lines,
            "",
        ]
    )


def validate_filetree(text: str) -> list[str]:
    errors: list[str] = []
    if not text.startswith("# Filetree\n"):
        errors.append(f"{FILETREE_FILENAME} must begin with '# Filetree'")
    if FILETREE_MARKER not in text:
        errors.append(f"{FILETREE_FILENAME} missing generator marker")
    for heading in ("## Root files", "## Modules", "## Tree"):
        if heading not in text:
            errors.append(f"{FILETREE_FILENAME} missing {heading}")
    return errors


def parse_inventory(text: str) -> FiletreeInventory:
    inventory = FiletreeInventory()
    section = ""
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section == "Root files":
            match = ROOT_FILE_RE.match(line)
            if match:
                inventory.root_files.append(match.group(1))
        elif section == "Modules":
            match = MODULE_ROW_RE.match(line)
            if match:
                inventory.modules.append(
                    ModuleRow(
                        path=match.group(1),
                        kind=match.group(2),
                        sources=int(match.group(3)),
                        readme=match.group(4),
                    )
                )
            elif line.startswith("| `_none_`"):
                continue
        elif section == "Tree" and line.endswith("/") and not line.startswith("```"):
            name = line.strip()
            if name and name != "./":
                inventory.tree_dirs.append(name.rstrip("/"))
    return inventory


def inventory_from_filetree(root: Path) -> FiletreeInventory | None:
    path = root / FILETREE_FILENAME
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    if validate_filetree(text):
        return None
    parsed = parse_inventory(text)
    if not parsed.modules and "## Modules" in text:
        return parsed
    return parsed


def write_filetree(
    root: Path,
    *,
    write: bool = True,
    extra_skip: list[str] | None = None,
) -> tuple[FiletreeInventory, bool, Admission]:
    inventory = walk_inventory(root, extra_skip=extra_skip)
    rendered = render_filetree(inventory, repo_slug(root))
    findings = validate_filetree(rendered)
    if findings:
        raise ValueError("; ".join(findings))
    target = resolve_under_root(root, FILETREE_FILENAME)
    if target is None:
        raise ValueError(f"{FILETREE_FILENAME} target escaped repository root")
    if not write:
        return inventory, False, "skipped"
    written, admission = apply_owned_write(target, rendered, FILETREE_MARKER)
    return inventory, written, admission


def build_filetree_state(
    root: Path,
    *,
    write: bool = True,
) -> tuple[dict[str, Any], FiletreeInventory, list[str]]:
    mutations: list[str] = []
    inventory, written, admission = write_filetree(root, write=write)
    if written:
        mutations.append(FILETREE_FILENAME)
    missing = sum(1 for row in inventory.modules if row.readme == "missing")
    findings: list[str] = []
    if admission == "preserve":
        findings.append(
            f"{FILETREE_FILENAME} exists without {FILETREE_MARKER}; left unowned file in place"
        )
    state = {
        "status": "PASS",
        "path": FILETREE_FILENAME,
        "written": written,
        "admission": admission,
        "module_count": len(inventory.modules),
        "missing_readme_count": missing,
        "findings": findings,
    }
    return state, inventory, mutations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    inventory, written, admission = write_filetree(root, write=not args.dry_run)
    print(
        f"modules={len(inventory.modules)} written={written} "
        f"admission={admission} path={FILETREE_FILENAME}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
