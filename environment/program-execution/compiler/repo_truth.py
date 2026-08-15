"""Repository truth discovery for the Intent Resolver (contract §8, ADR-0008)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Evidence priority (contract §8):
#   verified runtime/current-state > machine-readable contracts > structure/code
#   > ADR material > human prose > inference
PRIORITY = [
    "runtime",
    "machine_contract",
    "structure",
    "adr",
    "prose",
    "inference",
]

DPK_FILES = (
    ".ai/manifest.yaml",
    ".ai/repository-map.yaml",
    ".ai/constraints.yaml",
    ".ai/execution-package.yaml",
)


@dataclass
class RepoTruth:
    root: Path
    remote: str | None
    revision: str | None
    owner: str | None
    test_command: str | None
    package_manager: str | None
    runtime_version: str | None
    dpk: dict[str, Any] | None
    constraints_files: list[str] = field(default_factory=list)
    adr_files: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    rollback_defs: list[str] = field(default_factory=list)
    source_priority: dict[str, str] = field(default_factory=dict)


def discover(root: Path) -> RepoTruth:
    root = root.resolve()
    dpk = _load_dpk(root)
    remote, revision = _git_state(root)
    truth = RepoTruth(
        root=root,
        remote=remote,
        revision=revision,
        owner=None,
        test_command=None,
        package_manager=None,
        runtime_version=None,
        dpk=dpk,
        constraints_files=[],
        adr_files=[],
        validation_commands=[],
        rollback_defs=[],
    )
    truth.owner = _resolve_owner(root, truth)
    truth.test_command, truth.package_manager = _resolve_test_command(root, truth)
    truth.runtime_version = _resolve_runtime_version(root, truth)
    truth.adr_files = sorted(str(p.relative_to(root)) for p in root.rglob("*") if _is_adr(p))
    truth.validation_commands = _validation_commands(root, truth)
    truth.rollback_defs = _rollback_defs(root, truth)
    return truth


def _load_dpk(root: Path) -> dict[str, Any] | None:
    manifest = root / ".ai" / "manifest.yaml"
    if not manifest.is_file():
        return None
    data: dict[str, Any] = {}
    for rel in DPK_FILES:
        path = root / rel
        if path.is_file():
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(loaded, dict):
                data[rel] = loaded
    return data or None


def _git_state(root: Path) -> tuple[str | None, str | None]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
        )
        remote = completed.stdout.strip() or None
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        revision = head.stdout.strip() or None
        return remote, revision
    except OSError:
        return None, None


def _resolve_owner(root: Path, truth: RepoTruth) -> str | None:
    if truth.dpk:
        for loaded in truth.dpk.values():
            owner = loaded.get("owner") or loaded.get("metadata", {}).get("owner")
            if owner:
                truth.source_priority["owner"] = "machine_contract"
                return str(owner)
    for name in ("AGENTS.md", "CANONICAL_LAW.md"):
        path = root / name
        if path.is_file():
            owner = _owner_from_prose(path)
            if owner:
                truth.source_priority["owner"] = "prose"
                return owner
    return None


NON_PERSON_OWNERS = {
    "platform",
    "organization",
    "organisation",
    "org",
    "system",
    "none",
    "unknown",
    "unassigned",
    "committee",
    "governing body",
}


def _owner_from_prose(path: Path) -> str | None:
    import re

    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in (r"^\s*owner:\s*(.+)$", r"\bOwner:\s*([^\n]+)"):
        for match in re.finditer(pattern, text, flags=re.MULTILINE | re.IGNORECASE):
            value = match.group(1).strip().strip('"').strip("'")
            if value and value.lower() not in NON_PERSON_OWNERS:
                return value
    return None


def _resolve_test_command(root: Path, truth: RepoTruth) -> tuple[str | None, str | None]:
    if truth.dpk:
        for rel in ("execution-package.yaml", "manifest.yaml"):
            loaded = truth.dpk.get(f".ai/{rel}") or {}
            command = loaded.get("test_command") or loaded.get("commands", {}).get("test")
            if command:
                truth.source_priority["test_command"] = "machine_contract"
                return str(command), loaded.get("package_manager")
    agpath = root / "AGENTS.md"
    if agpath.is_file():
        import re

        text = agpath.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"(?:test command|run tests)[:：]\s*`([^`]+)`", text, flags=re.IGNORECASE)
        if match:
            truth.source_priority["test_command"] = "prose"
            return match.group(1).strip(), None
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "pytest" in text:
            truth.source_priority["test_command"] = "structure"
            return "pytest -q", "uv"
    return None, None


def _resolve_runtime_version(root: Path, truth: RepoTruth) -> str | None:
    if truth.dpk:
        loaded = truth.dpk.get(".ai/manifest.yaml") or {}
        version = loaded.get("runtime_version") or loaded.get("versions", {}).get("python")
        if version:
            truth.source_priority["runtime_version"] = "machine_contract"
            return str(version)
    for name in (".python-version",):
        path = root / name
        if path.is_file():
            truth.source_priority["runtime_version"] = "structure"
            return path.read_text(encoding="utf-8").strip()
    return None


def _is_adr(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix == ".md" and (
        name.startswith("adr") or "/adr" in str(path).lower() or name.endswith(".adr.md")
    )


def _validation_commands(root: Path, truth: RepoTruth) -> list[str]:
    if truth.test_command:
        return [truth.test_command]
    commands: list[str] = []
    if (root / ".pre-commit-config.yaml").is_file():
        commands.append("pre-commit run --all-files")
    return commands


def _rollback_defs(root: Path, truth: RepoTruth) -> list[str]:
    rollbacks: list[str] = []
    if (root / "CUTOVER_AND_ROLLBACK.yaml").is_file():
        rollbacks.append("CUTOVER_AND_ROLLBACK.yaml")
    return rollbacks


__all__ = ["PRIORITY", "RepoTruth", "discover"]
