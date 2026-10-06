"""Compile absent root documents from repository evidence.

Creates ``AGENTS.md``, ``CLAUDE.md``, and ``INVARIANTS.md`` only when the
file is missing. An existing file is left untouched: an unowned operating
document is not a template, and this module does not fold one into a pointer.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from doc_owned_write import apply_owned_write
from surface_analyzers.python_project import inspect_python_project
from surface_analyzers.workflow import analyze as analyze_workflow

ROOT_MARKER = "<!-- l9-root-doc: generated-by=l9-update-agent-docs -->"
ORG_PROFILE_URL = "https://github.com/Quantum-L9/.github"

# Closed observation set. A path is listed only when it exists.
_OBSERVED = (
    "README.md",
    "CANONICAL_LAW.md",
    "ARCHITECTURE.md",
    "docs/architecture.md",
    "INVARIANTS.md",
    "ORG_INVARIANTS.yaml",
    "Makefile",
    "pyproject.toml",
    ".pre-commit-config.yaml",
    "llm.txt",
    "filetree.md",
)

_ENFORCING = (
    ("ORG_INVARIANTS.yaml", "machine organization policy"),
    (".pre-commit-config.yaml", "pre-commit enforcement"),
)


def _org_url(policy: dict[str, Any]) -> str:
    binding = policy.get("external_bindings", {}).get("org_profile", {})
    url = binding.get("url")
    return url if isinstance(url, str) and url else ORG_PROFILE_URL


def _existing(root: Path) -> list[str]:
    return [rel for rel in _OBSERVED if (root / rel).is_file()]


def _workflows(root: Path) -> list[str]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted(
        path.relative_to(root).as_posix()
        for path in directory.iterdir()
        if path.is_file() and path.suffix in {".yml", ".yaml"}
    )


def repository_description(root: Path) -> str | None:
    """The package's own description, when the manifest states one."""
    path = root / "package.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    description = data.get("description") if isinstance(data, dict) else None
    if not isinstance(description, str) or not description.strip():
        return None
    return " ".join(description.split())


def _command_names(root: Path) -> list[str]:
    """Script names only. Command strings are never rendered; they can hold secrets."""
    names: set[str] = set()
    try:
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        package = None
    scripts = package.get("scripts") if isinstance(package, dict) else None
    if isinstance(scripts, dict):
        names.update(key for key in scripts if isinstance(key, str))
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            data = None
        if isinstance(data, dict):
            state = inspect_python_project(root, data)
            names.update(name for name, _value in state.project_scripts)
    return sorted(names)


def _readme_relpath(path: str) -> str:
    return "README.md" if path in {"", "."} else f"{path}/README.md"


def _commands_section(root: Path) -> str:
    names = _command_names(root)
    if not names:
        return ""
    lines = "\n".join(f"- `{name}`" for name in names)
    return f"## Commands\n\n{lines}\n\n"


def _module_map(readme_models: tuple[Any, ...]) -> str:
    rows: list[str] = []
    for model in readme_models:
        rel = _readme_relpath(model.target.path)
        purpose = model.purpose or "compiled from repository evidence"
        rows.append(f"- [`{rel}`]({rel}): {purpose}")
    if not rows:
        return ""
    return "## Module map\n\n" + "\n".join(rows) + "\n\n"


def render_agents(
    root: Path,
    policy: dict[str, Any],
    readme_models: tuple[Any, ...] = (),
) -> str:
    url = _org_url(policy)
    observed = _existing(root)
    surface_lines = [f"- `{rel}`" for rel in observed] or ["- _none yet_"]
    skills = "- `skills/` is present.\n" if (root / "skills").is_dir() else ""
    description = repository_description(root)
    repository = f"## Repository\n\n{description}\n\n" if description else ""
    return (
        "# AGENTS.md — operating instructions\n\n"
        "## Mission\n\n"
        "This file is the operating-instruction source for this repository. "
        "A lower document does not override it.\n\n" + repository + "## Authority\n\n"
        "1. `CANONICAL_LAW.md`, when this repository contains it.\n"
        "2. This file.\n"
        "3. Task procedures under `skills/`, when this repository contains them.\n\n"
        f"Organization semantics are cited from {url}. Do not copy that tree "
        "into this repository.\n\n"
        "## Repository surfaces\n\n"
        + "\n".join(surface_lines)
        + "\n\n"
        + skills
        + _module_map(readme_models)
        + _commands_section(root)
        + "## Publication\n\n"
        "Publish through the ceremony this repository already uses. "
        "This file does not add a second one.\n\n"
        "## Change policy\n\n"
        "Once this file exists, later updates are surgical and additive. "
        "Do not replace it from a template.\n\n"
        f"{ROOT_MARKER}\n"
    )


def render_claude(root: Path, policy: dict[str, Any]) -> str:
    del root
    url = _org_url(policy)
    return (
        "# CLAUDE.md — authority pointer\n\n"
        "This file is a load pointer. It names the authority chain. "
        "It does not carry doctrine.\n\n"
        "## Authority chain\n\n"
        "1. `CANONICAL_LAW.md` — constitution, when this repository contains it.\n"
        "2. `AGENTS.md` — operating instructions for this repository.\n"
        "3. `skills/` — task procedures, when this repository contains them.\n\n"
        "Maps, not authority: `ARCHITECTURE.md`, `docs/architecture.md`, and "
        "`INVARIANTS.md`, when present.\n\n"
        f"Organization semantics: {url}. Cite only. Do not copy that tree.\n\n"
        f"{ROOT_MARKER}\n"
    )


def _workflow_line(root: Path, rel: str) -> str:
    result = analyze_workflow(root, root / rel)
    name = result["name"] or Path(rel).stem
    jobs = result["jobs"]
    listed = ", ".join(f"`{job}`" for job in jobs)
    if listed:
        return f"- `{rel}` — workflow `{name}` jobs {listed}."
    return f"- `{rel}` — workflow `{name}`."


def render_invariants(root: Path, policy: dict[str, Any]) -> str:
    url = _org_url(policy)
    lines = [f"- `{rel}` — {role}." for rel, role in _ENFORCING if (root / rel).is_file()]
    lines.extend(_workflow_line(root, rel) for rel in _workflows(root))
    body = (
        "\n".join(lines)
        if lines
        else (
            "This repository does not yet contain a local enforcing source "
            "(`ORG_INVARIANTS.yaml`, `.pre-commit-config.yaml`, or "
            "`.github/workflows/`)."
        )
    )
    return (
        "# INVARIANTS.md — enforcement index\n\n"
        "This file indexes enforcing sources that exist in this repository. "
        "It does not copy their bodies.\n\n"
        "## Enforcing sources\n\n"
        f"{body}\n\n"
        f"Organization policy is cited from {url}. Do not copy it here.\n\n"
        f"{ROOT_MARKER}\n"
    )


_COMPILERS = (
    ("invariants", "INVARIANTS.md", render_invariants),
    ("claude", "CLAUDE.md", render_claude),
    ("agents", "AGENTS.md", render_agents),
)


def compile_missing_root_docs(
    root: Path,
    policy: dict[str, Any],
    *,
    refresh_owned: bool = False,
    readme_models: tuple[Any, ...] = (),
) -> tuple[list[str], dict[str, str]]:
    """Create absent core files. Optionally refresh files this skill already marked.

    An existing file without ``ROOT_MARKER`` is left untouched. That keeps a
    repository's own operating text in place. ``refresh_owned`` updates a
    file this compiler wrote when its evidence has changed.
    """
    mutations: list[str] = []
    admissions: dict[str, str] = {}
    surfaces = policy.get("surfaces", {})
    for surface, filename, render in _COMPILERS:
        spec = surfaces.get(surface, {})
        if spec.get("create_policy") != "create_if_absent":
            continue
        path = root / filename
        if path.is_file():
            if not refresh_owned:
                continue
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if ROOT_MARKER not in existing:
                continue
        rendered = (
            render(root, policy, readme_models) if render is render_agents else render(root, policy)
        )
        _wrote, admission = apply_owned_write(path, rendered, ROOT_MARKER)
        if admission in {"create", "refresh"}:
            mutations.append(filename)
            admissions[filename] = admission
    return mutations, admissions
