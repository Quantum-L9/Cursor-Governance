#!/usr/bin/env python3
"""Closed-world source evidence extraction for repository README compilation.

The policy owns which filenames are admitted; this module owns a small static
set of extractors for those declared language labels.  It never executes a
source file and records extraction failures as evidence rather than silently
pretending the file was absent.
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
import xml.etree.ElementTree as element_tree
from pathlib import Path
from typing import Any

import yaml
from readme_model import ExtractionIssue, InterfaceDoc, ModuleDoc, RelationshipDoc, SourceFact

PACK = Path(__file__).resolve().parents[1]
POLICY_PATH = PACK / "references" / "doc-surface-policy.yaml"

# Static by design. Policy entries may select only these extractors; no dynamic
# import, entry-point discovery, or repository-provided parser is allowed.
EXTRACTOR_LANGUAGES = frozenset(
    {"python", "shell", "javascript", "typescript", "terraform", "xml", "dockerfile"}
)

_JS_EXPORT_RE = re.compile(
    r"^\s*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]*)",
    re.MULTILINE,
)
_JS_IMPORT_RE = re.compile(r"\b(?:import|export)\b[\s\S]*?\bfrom\s+[\"']([^\"']+)[\"']")
_JS_REQUIRE_RE = re.compile(r"\brequire\(\s*[\"']([^\"']+)[\"']\s*\)")
_JS_ENV_RE = re.compile(r"\bprocess\.env\.([A-Za-z_][A-Za-z0-9_]*)")
_SHELL_FUNCTION_RE = re.compile(
    r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*\{", re.MULTILINE
)
_SHELL_SOURCE_RE = re.compile(r"^\s*(?:source|\.)\s+([^\s;]+)", re.MULTILINE)
_SHELL_ENV_RE = re.compile(r"\$\{?([A-Z][A-Z0-9_]*)\}?")
_SHELL_ASSIGNMENT_RE = re.compile(
    r"^\s*(?:(?:local|readonly)\s+|declare(?:\s+-[A-Za-z]+)?\s+)?"
    r"([A-Z][A-Z0-9_]*)=(.*)$",
    re.MULTILINE,
)
_TERRAFORM_BLOCK_RE = re.compile(
    r'^\s*(resource|data|module|variable)\s+"([^"]+)"(?:\s+"([^"]+)")?\s*\{', re.MULTILINE
)
_DOCKER_FROM_RE = re.compile(
    r"^\s*FROM(?:\s+--[A-Za-z][A-Za-z0-9-]*(?:=[^\s]+)?)*\s+([^\s]+)",
    re.MULTILINE | re.IGNORECASE,
)
_DOCKER_ENTRYPOINT_RE = re.compile(
    r"^\s*(?:ENTRYPOINT|CMD)\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE
)
_COMMENT_RE = re.compile(r"^\s*(?://|#(?!\!))\s*(.+?)\s*$", re.MULTILINE)


def load_source_evidence_registry() -> dict[str, Any]:
    """Load the one policy-owned source-evidence registry."""
    raw = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    registry = raw.get("source_evidence") if isinstance(raw, dict) else None
    if not isinstance(registry, dict):
        raise ValueError("doc-surface-policy.yaml missing source_evidence registry")
    return registry


def source_language(path: Path, registry: dict[str, Any] | None = None) -> str | None:
    """Return the policy-declared language for a file, if supported."""
    registry = registry or load_source_evidence_registry()
    by_name = registry.get("filenames") if isinstance(registry.get("filenames"), dict) else {}
    by_extension = (
        registry.get("extensions") if isinstance(registry.get("extensions"), dict) else {}
    )
    entry = by_name.get(path.name) or by_extension.get(path.suffix.lower())
    language = entry.get("language") if isinstance(entry, dict) else None
    return str(language) if isinstance(language, str) and language in EXTRACTOR_LANGUAGES else None


def source_patterns(registry: dict[str, Any] | None = None) -> tuple[str, ...]:
    """Return canonical impact patterns from the policy-owned registry."""
    registry = registry or load_source_evidence_registry()
    patterns: list[str] = []
    for group in ("extensions", "filenames"):
        entries = registry.get(group) if isinstance(registry.get(group), dict) else {}
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            raw = entry.get("patterns")
            if isinstance(raw, list):
                patterns.extend(str(value) for value in raw if str(value).strip())
    return tuple(dict.fromkeys(patterns))


def supported_source_files(directory: Path, registry: dict[str, Any] | None = None) -> list[Path]:
    """Direct supported source files in deterministic order."""
    registry = registry or load_source_evidence_registry()
    try:
        children = directory.iterdir()
    except OSError:
        return []
    return sorted(
        (
            child
            for child in children
            if child.is_file()
            and not child.name.startswith("test_")
            and source_language(child, registry)
        ),
        key=lambda item: item.name,
    )


def _summary(text: str | None, limit: int = 260) -> str | None:
    if not text or not text.strip():
        return None
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    boundary = max(
        cleaned.rfind(". ", 0, limit), cleaned.rfind("! ", 0, limit), cleaned.rfind("? ", 0, limit)
    )
    if boundary > 0:
        return cleaned[: boundary + 1]
    cut = cleaned.rfind(" ", 0, limit)
    return (cleaned[:cut] if cut > 0 else cleaned[:limit]).rstrip(" ,;:-–—…")


def _leading_comment(text: str) -> str | None:
    match = _COMMENT_RE.search(text[:1200])
    return _summary(match.group(1)) if match else None


def _shell_environment_names(text: str) -> list[str]:
    """Return uppercase inputs not established as shell-local variables.

    A bare uppercase expansion is evidence of an external environment input only
    when the script does not assign that name. An assignment that reads its own
    prior value (``NAME=${NAME:-default}``) is an explicit environment-default
    declaration, so it remains an input even though it also creates a local
    value for later lines.
    """
    assignments = list(_SHELL_ASSIGNMENT_RE.finditer(text))
    local_names = {match.group(1) for match in assignments}
    external = {name for name in _SHELL_ENV_RE.findall(text) if name not in local_names}
    for assignment in assignments:
        name = assignment.group(1)
        if name in _SHELL_ENV_RE.findall(assignment.group(2)):
            external.add(name)
    return sorted(external)


def _python_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    names = [arg.arg for arg in node.args.args if arg.arg != "self"]
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returned = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({', '.join(names)}){returned}"


def _public(name: str) -> bool:
    return not name.startswith("_")


def _python_environment_relations(tree: ast.AST, source: str) -> list[RelationshipDoc]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            base = node.func.value
            if (
                isinstance(base, ast.Name)
                and base.id == "os"
                and node.func.attr == "getenv"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                values.add(node.args[0].value)
            elif (
                isinstance(base, ast.Attribute)
                and isinstance(base.value, ast.Name)
                and base.value.id == "os"
                and base.attr == "environ"
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                values.add(node.args[0].value)
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "os"
            and node.value.attr == "environ"
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            values.add(node.slice.value)
    return [
        RelationshipDoc(kind="configures", target=value, source=source) for value in sorted(values)
    ]


def _extract_python(path: Path, text: str, rel: str) -> SourceFact:
    tree = ast.parse(text, filename=rel)
    classes: list[InterfaceDoc] = []
    functions: list[InterfaceDoc] = []
    exports: list[str] = []
    imports: list[str] = []
    relative: set[str] = set()
    relationships: list[RelationshipDoc] = []
    entrypoints: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
                relationships.append(RelationshipDoc(kind="imports", target=alias.name, source=rel))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if node.module:
                    relative.add(node.module.split(".", 1)[0])
                    relationships.append(
                        RelationshipDoc(
                            kind="imports", target=node.module, source=rel, detail="relative"
                        )
                    )
                else:
                    relative.update(alias.name for alias in node.names)
                    relationships.extend(
                        RelationshipDoc(
                            kind="imports", target=alias.name, source=rel, detail="relative"
                        )
                        for alias in node.names
                    )
            elif node.module:
                imports.append(node.module)
                relationships.append(
                    RelationshipDoc(kind="imports", target=node.module, source=rel)
                )
        elif isinstance(node, ast.ClassDef) and _public(node.name):
            classes.append(InterfaceDoc(name=node.name, summary=_summary(ast.get_docstring(node))))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and _public(node.name):
            functions.append(
                InterfaceDoc(
                    name=node.name,
                    signature=_python_signature(node),
                    summary=_summary(ast.get_docstring(node)),
                )
            )
            if node.name == "main":
                entrypoints.append("main")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    and isinstance(node.value, (ast.List, ast.Tuple))
                ):
                    exports.extend(
                        value.value
                        for value in node.value.elts
                        if isinstance(value, ast.Constant) and isinstance(value.value, str)
                    )
    relationships.extend(_python_environment_relations(tree, rel))
    return SourceFact(
        path=rel,
        language="python",
        module=ModuleDoc(
            file=path.name,
            name=path.stem,
            purpose=_summary(ast.get_docstring(tree)),
            classes=tuple(classes),
            functions=tuple(functions),
            exports=tuple(sorted(set(exports))),
            language="python",
        ),
        imports=tuple(imports),
        relative_imports=tuple(sorted(relative)),
        entrypoints=tuple(entrypoints),
        relationships=tuple(relationships),
    )


def _import_relation(raw: str, source: str) -> RelationshipDoc:
    return RelationshipDoc(
        kind="imports",
        target=raw,
        source=source,
        detail="local" if raw.startswith((".", "/")) else None,
    )


def _extract_javascript(path: Path, text: str, rel: str, language: str) -> SourceFact:
    exports = sorted(set(_JS_EXPORT_RE.findall(text)))
    imports = sorted(set((*_JS_IMPORT_RE.findall(text), *_JS_REQUIRE_RE.findall(text))))
    functions = tuple(InterfaceDoc(name=name) for name in exports)
    relationships = [_import_relation(value, rel) for value in imports]
    relationships.extend(
        RelationshipDoc(kind="configures", target=value, source=rel)
        for value in sorted(set(_JS_ENV_RE.findall(text)))
    )
    return SourceFact(
        path=rel,
        language=language,
        module=ModuleDoc(
            file=path.name,
            name=path.stem,
            purpose=_leading_comment(text),
            functions=functions,
            exports=tuple(exports),
            language=language,
        ),
        imports=tuple(imports),
        relationships=tuple(relationships),
    )


def _extract_shell(path: Path, text: str, rel: str) -> SourceFact:
    names = sorted(set(_SHELL_FUNCTION_RE.findall(text)))
    sourced = sorted(set(_SHELL_SOURCE_RE.findall(text)))
    relationships = [_import_relation(value, rel) for value in sourced]
    relationships.extend(
        RelationshipDoc(kind="configures", target=value, source=rel)
        for value in _shell_environment_names(text)
    )
    return SourceFact(
        path=rel,
        language="shell",
        module=ModuleDoc(
            file=path.name,
            name=path.stem,
            purpose=_leading_comment(text),
            functions=tuple(InterfaceDoc(name=name, signature=f"{name}()") for name in names),
            language="shell",
        ),
        imports=tuple(sourced),
        entrypoints=(path.name,),
        relationships=tuple(relationships),
    )


def _extract_terraform(path: Path, text: str, rel: str) -> SourceFact:
    interfaces: list[InterfaceDoc] = []
    relationships: list[RelationshipDoc] = []
    for kind, first, second in _TERRAFORM_BLOCK_RE.findall(text):
        name = ".".join(value for value in (kind, first, second) if value)
        if kind == "module":
            relationships.append(RelationshipDoc(kind="uses_module", target=first, source=rel))
        elif kind == "variable":
            relationships.append(RelationshipDoc(kind="configures", target=first, source=rel))
        else:
            interfaces.append(InterfaceDoc(name=name))
    return SourceFact(
        path=rel,
        language="terraform",
        module=ModuleDoc(
            file=path.name,
            name=path.stem,
            purpose=_leading_comment(text),
            functions=tuple(interfaces),
            language="terraform",
        ),
        relationships=tuple(relationships),
    )


def _extract_xml(path: Path, text: str, rel: str) -> SourceFact:
    root = element_tree.fromstring(text)
    direct = sorted({child.tag.split("}")[-1] for child in root})
    return SourceFact(
        path=rel,
        language="xml",
        module=ModuleDoc(
            file=path.name,
            name=path.stem,
            purpose=f"XML document rooted at `{root.tag.split('}')[-1]}`.",
            functions=tuple(InterfaceDoc(name=name) for name in direct[:24]),
            language="xml",
        ),
    )


def _extract_dockerfile(path: Path, text: str, rel: str) -> SourceFact:
    images = sorted(set(_DOCKER_FROM_RE.findall(text)))
    entrypoints = tuple(_DOCKER_ENTRYPOINT_RE.findall(text))
    return SourceFact(
        path=rel,
        language="dockerfile",
        module=ModuleDoc(
            file=path.name,
            name=path.name.lower(),
            purpose=_leading_comment(text),
            language="dockerfile",
        ),
        entrypoints=entrypoints,
        relationships=tuple(
            RelationshipDoc(kind="base_image", target=image, source=rel) for image in images
        ),
    )


def extract_source_fact(
    path: Path, root: Path, registry: dict[str, Any] | None = None
) -> tuple[SourceFact | None, ExtractionIssue | None]:
    """Extract one supported source file without executing it."""
    registry = registry or load_source_evidence_registry()
    language = source_language(path, registry)
    if language is None:
        return None, None
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return None, ExtractionIssue(
            path=path.name,
            language=language,
            detail="source path is outside the repository root",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, ExtractionIssue(
            path=rel, language=language, detail=f"unreadable source: {exc}"
        )
    try:
        if language == "python":
            return _extract_python(path, text, rel), None
        if language == "shell":
            return _extract_shell(path, text, rel), None
        if language in {"javascript", "typescript"}:
            return _extract_javascript(path, text, rel, language), None
        if language == "terraform":
            return _extract_terraform(path, text, rel), None
        if language == "xml":
            return _extract_xml(path, text, rel), None
        if language == "dockerfile":
            return _extract_dockerfile(path, text, rel), None
    except (
        SyntaxError,
        ValueError,
        element_tree.ParseError,
        json.JSONDecodeError,
        tomllib.TOMLDecodeError,
    ) as exc:
        return None, ExtractionIssue(path=rel, language=language, detail=f"parse failure: {exc}")
    return None, ExtractionIssue(path=rel, language=language, detail="no registered extractor")


def compile_source_facts(
    root: Path, rel: str, registry: dict[str, Any] | None = None
) -> tuple[tuple[SourceFact, ...], tuple[ExtractionIssue, ...]]:
    """Compile every direct, policy-authorized source file for one target."""
    registry = registry or load_source_evidence_registry()
    facts: list[SourceFact] = []
    issues: list[ExtractionIssue] = []
    for path in supported_source_files(root / rel, registry):
        fact, issue = extract_source_fact(path, root, registry)
        if fact is not None:
            facts.append(fact)
        if issue is not None:
            issues.append(issue)
    return tuple(facts), tuple(issues)
