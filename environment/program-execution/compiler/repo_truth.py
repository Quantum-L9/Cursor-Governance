"""Repository truth discovery for the Intent Resolver (contract §8, ADR-0008)."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
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


DISPOSITIONS = (
    "ALREADY_SATISFIED",
    "KEEP",
    "MERGE_WITH_EXISTING",
    "HARDEN_WIRE_EXISTING",
    "CREATE",
    "DELETE_SUPERSEDED",
    "MIGRATION_CONTEXT",
    "UNKNOWN",
)

_PATH_TOKEN = re.compile(
    r"\b((?:[\w.-]+/)+[\w.-]+\.(?:py|md|yaml|yml|json|toml|sh))\b"
)
_IDENT_TOKEN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{3,})\b")


@dataclass(frozen=True)
class RequirementDisposition:
    """One obligation classified against repository evidence before lowering."""

    requirement_id: str
    statement: str
    disposition: str
    path: str | None
    symbol: str | None
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "statement": self.statement,
            "disposition": self.disposition,
            "path": self.path,
            "symbol": self.symbol,
            "evidence": self.evidence,
        }


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


def classify_dispositions(
    requirements: Sequence[str],
    truth: RepoTruth,
) -> list[RequirementDisposition]:
    """Classify each requirement against path and symbol evidence.

    Does not replace ``discover``. Unknown stays UNKNOWN. Existing paths are
    never blindly CREATE.
    """
    rows: list[RequirementDisposition] = []
    for index, raw in enumerate(requirements, start=1):
        statement = str(raw).strip()
        if not statement:
            continue
        req_id = f"REQ-{index:03d}"
        path, symbol, evidence = _ground_requirement(statement, truth)
        lowered = statement.lower()
        create_intent = any(token in lowered for token in ("create", "add new", "introduce"))
        forbid_create = any(
            token in lowered for token in ("do not create", "don't create", "must not create")
        )
        if create_intent and forbid_create:
            disposition = "UNKNOWN"
        elif path and any(token in lowered for token in ("harden", "wire", "extend")):
            disposition = "HARDEN_WIRE_EXISTING"
        elif path and any(token in lowered for token in ("already", "existing", "current")):
            disposition = "KEEP"
        elif path and "merge" in lowered:
            disposition = "MERGE_WITH_EXISTING"
        elif path and any(token in lowered for token in ("delete", "supersede", "remove")):
            disposition = "DELETE_SUPERSEDED"
        elif path and any(token in lowered for token in ("migrate", "migration")):
            disposition = "MIGRATION_CONTEXT"
        elif path:
            disposition = "KEEP"
        elif create_intent:
            disposition = "CREATE"
        else:
            disposition = "UNKNOWN"
        rows.append(
            RequirementDisposition(
                requirement_id=req_id,
                statement=statement,
                disposition=disposition,
                path=path,
                symbol=symbol,
                evidence=evidence,
            )
        )
    return rows


def _ground_requirement(
    statement: str, truth: RepoTruth
) -> tuple[str | None, str | None, str]:
    root = truth.root
    for match in _PATH_TOKEN.finditer(statement):
        rel = match.group(1)
        if (root / rel).exists():
            return rel, None, f"path_exists:{rel}"
    compiler_root = None
    for candidate in (root / "environment/program-execution/compiler", root / "compiler"):
        if candidate.is_dir():
            compiler_root = candidate
            break
    if compiler_root is not None:
        for match in _IDENT_TOKEN.finditer(statement):
            ident = match.group(1)
            exact = compiler_root / f"{ident}.py"
            if exact.is_file():
                rel = str(exact.relative_to(root))
                return rel, ident, f"symbol_match:{ident}->{rel}"
    return None, None, "no_path_or_symbol_evidence"


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


__all__ = [
    "DISPOSITIONS",
    "PRIORITY",
    "RepoTruth",
    "RequirementDisposition",
    "classify_dispositions",
    "discover",
]
