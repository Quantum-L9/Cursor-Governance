"""Generic Python-project observation, free of repository policy.

Everything here answers "what does this project declare?". Nothing here
answers "what should it declare?" — that question belongs to the
repository's own Python authorities, and is asked in `pyproject.py`.

The split matters because the two were fused: an analyzer presenting
itself as `python-project-contract-v1` reached for `skills/*/scripts/
self_test.py` and `ops/config/python-contract.json` by name, so a fact
about one repository read as a law about every Python project.
"""

from __future__ import annotations

import ast
import fnmatch
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

__all__ = [
    "PythonProjectState",
    "VersionFloor",
    "inspect_python_project",
    "normalize_pytest_addopts",
    "parse_collection_guards",
    "path_is_collection_guarded",
    "python_floor",
    "pytest_ignored_paths",
]

FloorStatus = Literal["resolved", "unknown", "invalid"]

# PEP 440 version specifier: one operator and one version, comma separated.
_CLAUSE_RE = re.compile(r"^(===|==|!=|~=|<=|>=|<|>)\s*([0-9A-Za-z_.*+!-]+)$")
_RELEASE_RE = re.compile(r"^(\d+(?:\.\d+)*)(?:\.\*)?$")
#: Operators that can establish the lowest supported minor version.
_LOWER_BOUND_OPS = frozenset({">=", "~=", "==", "==="})


@dataclass(frozen=True)
class VersionFloor:
    """Lowest Python minor a specifier supports, or why it cannot be named."""

    value: str | None
    status: FloorStatus
    detail: str = ""


@dataclass(frozen=True)
class PythonProjectState:
    """What the project declares. No judgement, no repository knowledge."""

    requires_python: str | None = None
    floor: VersionFloor = field(default_factory=lambda: VersionFloor(None, "unknown", "absent"))
    ruff_target: str | None = None
    mypy_python_version: str | None = None
    pyright_python_version: str | None = None
    uv_declared: bool = False
    uv_lock_present: bool = False
    pytest_addopts: tuple[str, ...] = ()
    pytest_addopts_resolved: bool = True
    collect_ignore: tuple[str, ...] = ()
    collect_ignore_glob: tuple[str, ...] = ()
    collect_guards_resolved: bool = True
    lock_workflow_declared: bool = False


def _release(raw: str) -> tuple[int, ...] | None:
    """Numeric release segment of a version, wildcard tolerated."""
    match = _RELEASE_RE.match(raw)
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def python_floor(requires_python: str | None) -> VersionFloor:
    """Lowest supported `major.minor`, or UNKNOWN — never a silent pass.

    The previous implementation regex-searched for `>=X.Y` anywhere in the
    string. That reads a floor out of `!=3.12.*`, and reads nothing out of
    `~=3.12` while reporting success either way.
    """
    if requires_python is None or not requires_python.strip():
        return VersionFloor(None, "unknown", "requires-python is absent")

    clauses: list[tuple[str, str]] = []
    for raw in requires_python.split(","):
        candidate = raw.strip()
        if not candidate:
            return VersionFloor(None, "invalid", f"empty clause in {requires_python!r}")
        match = _CLAUSE_RE.match(candidate)
        if match is None:
            return VersionFloor(None, "invalid", f"not a PEP 440 specifier: {candidate!r}")
        if _release(match.group(2)) is None:
            return VersionFloor(None, "invalid", f"unparseable version: {candidate!r}")
        clauses.append((match.group(1), match.group(2)))

    lower: list[tuple[int, int]] = []
    for operator, version in clauses:
        if operator not in _LOWER_BOUND_OPS:
            continue
        release = _release(version)
        assert release is not None
        if len(release) < 2:
            # `>=3` names no minor, so no tool target can be derived from it.
            return VersionFloor(
                None, "unknown", f"{operator}{version} does not name a minor version"
            )
        lower.append((release[0], release[1]))

    if not lower:
        return VersionFloor(
            None,
            "unknown",
            f"{requires_python!r} sets no lower bound a minor version can be read from",
        )

    major, minor = max(lower)
    floor = f"{major}.{minor}"
    for operator, version in clauses:
        # Only a wildcard exclusion removes the whole series. `!=3.12.1`
        # rules out one patch release; the project still supports 3.12, so
        # treating it as an unknown floor would report a spurious
        # misalignment against a correctly pinned Ruff or mypy.
        if operator != "!=" or not version.endswith(".*"):
            continue
        excluded = _release(version)
        if excluded is not None and len(excluded) >= 2 and excluded[:2] == (major, minor):
            return VersionFloor(
                None, "unknown", f"{requires_python!r} excludes the {floor} series it floors at"
            )
    return VersionFloor(floor, "resolved", f"derived from {requires_python!r}")


def normalize_pytest_addopts(value: object) -> tuple[tuple[str, ...], bool]:
    """Tokenize addopts. Returns the tokens and whether they resolved.

    Stringifying the whole table and substring-searching it was enough to
    make a path mentioned anywhere look like a configured exclusion.
    """
    if value is None:
        return (), True
    if isinstance(value, str):
        try:
            return tuple(shlex.split(value)), True
        except ValueError:
            return (), False
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value), True
    return (), False


def pytest_ignored_paths(tokens: tuple[str, ...]) -> set[str]:
    """Paths excluded by `--ignore`, in both the `=` and split spellings."""
    ignored: set[str] = set()
    pending = False
    for token in tokens:
        if pending:
            ignored.add(token.replace("\\", "/").lstrip("./"))
            pending = False
            continue
        if token == "--ignore":
            pending = True
        elif token.startswith("--ignore="):
            ignored.add(token[len("--ignore=") :].replace("\\", "/").lstrip("./"))
    return ignored


def _literal_string_list(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, (ast.List, ast.Tuple)):
        values: list[str] = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                values.append(element.value)
            else:
                return None
        return tuple(values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _literal_string_list(node.left)
        right = _literal_string_list(node.right)
        if left is None or right is None:
            return None
        return left + right
    return None


def parse_collection_guards(text: str) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    """Literal `collect_ignore` / `collect_ignore_glob` from a conftest.

    A dynamically built list resolves to nothing and reports unresolved: a
    guard this analyzer cannot read is not a guard it may assume. A path
    that appears only in a comment is not a guard at all, which is why
    this is an AST walk rather than a substring search.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return (), (), False
    ignore: list[str] = []
    ignore_glob: list[str] = []
    resolved = True
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            continue
        # `collect_ignore: list[str] = [...]` is an AnnAssign, not an Assign,
        # and pytest honours it exactly the same. Skipping it returned an
        # empty guard set marked *resolved*, so a genuinely guarded file was
        # reported unguarded — a fail-open dressed as a clean read.
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = {target.id for target in targets if isinstance(target, ast.Name)}
        if not names & {"collect_ignore", "collect_ignore_glob"}:
            continue
        if node.value is None:
            # A bare annotation declares a name without assigning it. That is
            # not an unreadable guard, it is no guard at all.
            continue
        values = _literal_string_list(node.value)
        if values is None:
            resolved = False
            continue
        if "collect_ignore" in names:
            ignore.extend(values)
        if "collect_ignore_glob" in names:
            ignore_glob.extend(values)
    return tuple(ignore), tuple(ignore_glob), resolved


def path_is_collection_guarded(
    rel: str,
    *,
    addopts_ignored: set[str],
    collect_ignore: tuple[str, ...],
    collect_ignore_glob: tuple[str, ...],
) -> bool:
    normalized = rel.replace("\\", "/")
    if normalized in addopts_ignored:
        return True
    if normalized in {item.replace("\\", "/").lstrip("./") for item in collect_ignore}:
        return True
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in collect_ignore_glob)


def _lock_workflow_declared(root: Path) -> bool:
    """Does the repository itself declare a locked-environment workflow?

    `[tool.uv]` says the project uses uv. It does not say the project
    treats `uv.lock` as a committed contract — plenty of uv projects do
    not. What does say so is the repository running `uv lock --check` or
    `uv sync --locked` in its own automation.
    """
    for name in ("Makefile", "makefile", "GNUmakefile"):
        candidate = root / name
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "uv lock --check" in text or "uv sync --locked" in text:
            return True
    return False


def inspect_python_project(root: Path, data: dict[str, Any]) -> PythonProjectState:
    """Observe a parsed `pyproject.toml` plus the files it points at."""
    project = data.get("project", {})
    tool = data.get("tool", {})
    requires_python = project.get("requires-python")
    requires_python = str(requires_python) if requires_python is not None else None

    pytest_options = tool.get("pytest", {}).get("ini_options", {})
    addopts, addopts_resolved = normalize_pytest_addopts(pytest_options.get("addopts"))

    conftest = root / "conftest.py"
    if conftest.is_file():
        try:
            ignore, ignore_glob, guards_resolved = parse_collection_guards(
                conftest.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError):
            ignore, ignore_glob, guards_resolved = (), (), False
    else:
        ignore, ignore_glob, guards_resolved = (), (), True

    def _tool_value(section: str, key: str) -> str | None:
        value = tool.get(section, {}).get(key)
        return None if value is None else str(value)

    return PythonProjectState(
        requires_python=requires_python,
        floor=python_floor(requires_python),
        ruff_target=_tool_value("ruff", "target-version"),
        mypy_python_version=_tool_value("mypy", "python_version"),
        pyright_python_version=_tool_value("pyright", "pythonVersion"),
        uv_declared="uv" in tool,
        uv_lock_present=(root / "uv.lock").is_file(),
        pytest_addopts=addopts,
        pytest_addopts_resolved=addopts_resolved,
        collect_ignore=ignore,
        collect_ignore_glob=ignore_glob,
        collect_guards_resolved=guards_resolved,
        lock_workflow_declared=_lock_workflow_declared(root),
    )
