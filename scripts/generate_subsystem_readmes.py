#!/usr/bin/env python3
"""Generate module READMEs from YAML config plus stdlib AST facts.

Wired to readme-pipeline-v1 (workflows/dags/readme_pipeline_dag.py) and
skill l9-update-agent-docs. Never writes the repository-root README.md.
Does not call external clocks. Does not emit DORA or AI-scope contracts.
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
from typing import Any

import yaml

CONFIG_PATH = Path("config/subsystems/readme_config.yaml")
ROOT_README = Path("README.md")
FORBIDDEN_RELATIVE_PATHS = {"", ".", ".."}
SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}
HANDWRITTEN_RE = re.compile(r"^auto_generated:\s*false\b", re.MULTILINE | re.IGNORECASE)
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

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
    here = Path(__file__).resolve().parents[1]
    if (here / CONFIG_PATH).is_file():
        return here
    cwd = Path.cwd()
    if (cwd / CONFIG_PATH).is_file():
        return cwd
    return here


def load_config(repo_root: Path) -> dict[str, Any]:
    path = repo_root / CONFIG_PATH
    if not path.is_file():
        raise FileNotFoundError(f"config not found: {path}")
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


def _skip_dir(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def _iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for py_file in sorted(root.rglob("*.py")):
        if _skip_dir(py_file):
            continue
        if py_file.name.startswith("test_"):
            continue
        if "tests" in py_file.parts:
            continue
        files.append(py_file)
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
    facts.imports = sorted(set(imports))
    facts.exports = sorted(set(exports))
    facts.constants = constants
    return facts


def _first_line(text: str, fallback: str) -> str:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    return line or fallback


def render_components(facts: ModuleFacts) -> str:
    if not facts.classes:
        return "_No public classes in this path._"
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
    return "\n\n".join(blocks)


def render_functions(facts: ModuleFacts) -> str:
    if not facts.functions:
        return "_No public module-level functions._"
    lines = []
    for func in facts.functions[:20]:
        summary = _first_line(func.docstring, "")
        extra = f" — {summary}" if summary else ""
        lines.append(f"- `{func.signature}`{extra}")
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
    """Replace `{name}` tokens without interpreting braces inside values."""
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
            "purpose": purpose or "_Unknown — no purpose in config or module docstring._",
            "description": description,
            "components": render_components(facts),
            "functions": render_functions(facts),
            "exports": render_exports(facts),
            "dependencies": render_dependencies(facts),
        },
    )


def resolve_under_root(repo_root: Path, rel: str) -> Path | None:
    """Return the resolved directory if `rel` stays inside repo_root and is not root."""
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


def is_handwritten(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    front = text.split("---", 2)
    if len(front) >= 3:
        return bool(HANDWRITTEN_RE.search(front[1]))
    return bool(HANDWRITTEN_RE.search(text[:400]))


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


def list_subsystems(config: dict[str, Any]) -> None:
    items = config.get("subsystems") or {}
    for key, spec in items.items():
        flag = "skip" if spec.get("skip") else "live"
        print(f"{key}\t{spec.get('path')}\t{spec.get('title')}\t{flag}")


def report_gaps(repo_root: Path, config: dict[str, Any]) -> int:
    """Print stale (missing path) and unguarded handwritten READMEs. Exit 1 on stale."""
    stale: list[str] = []
    handwritten: list[str] = []
    for key, spec in (config.get("subsystems") or {}).items():
        path = str(spec.get("path") or "")
        module_dir = resolve_under_root(repo_root, path)
        if module_dir is None:
            stale.append(f"{key}\t{path}\tinvalid")
            continue
        if not module_dir.exists():
            stale.append(f"{key}\t{path}\tmissing")
            continue
        readme = module_dir / "README.md"
        if readme.is_file() and is_handwritten(readme) and not spec.get("skip"):
            handwritten.append(f"{key}\t{path}\thandwritten-unguarded")
    for row in stale:
        print(f"stale\t{row}")
    for row in handwritten:
        print(f"handwritten\t{row}")
    if not stale and not handwritten:
        print("gaps\tnone")
    return 1 if stale else 0


def select_targets(
    config: dict[str, Any],
    *,
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
        spec = {
            "path": cleaned,
            "title": title or path,
            "tier": "operations",
            "description": defaults.get("description") or path,
            "purpose": "",
        }
        return [(name, spec)]
    if subsystem:
        if subsystem not in items:
            raise KeyError(subsystem)
        spec = items[subsystem]
        if spec.get("skip") and not force:
            raise PermissionError(
                f"{subsystem} is skip: true (handwritten); pass --force to generate"
            )
        return [(subsystem, spec)]
    selected: list[tuple[str, dict[str, Any]]] = []
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
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--list", "-l", action="store_true")
    parser.add_argument("--gaps", action="store_true", help="Report missing or invalid config paths")
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
        list_subsystems(config)
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
            print(f"skip {name}: handwritten README (auto_generated: false)")
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
