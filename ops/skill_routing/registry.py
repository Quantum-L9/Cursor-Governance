"""Skill registry loading and validation — the runtime side of registry v2.

Ownership (CANONICAL_LAW §2.1, VSP-P1-005):
  * generation:  ops/scripts/build_claude_skill_registry.py (hashes the corpus)
  * loading:     this module (schema, record shape, name index, generation id)
  * scoring:     route_prompt.py (never here)
  * resolution:  materialize.py (exact SKILL.md resources; never here)

The registry is validated once per load. Corpus hashing is a generation / CI
concern — a prompt hook must never re-digest the skill tree.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REGISTRY_REL = Path("ops/generated/skill-registry.json")
SKILLS_REL = Path("skills")
SCHEMA_VERSION = 2

_NAME_RE = re.compile(r"^l9-[a-z0-9][a-z0-9-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_INVOCATIONS = frozenset({"model_allowed", "explicit_only"})
_REQUIRED_TOP = (
    "schema_version",
    "generation_id",
    "source_manifest_sha256",
    "source_skill_corpus_sha256",
    "routing",
    "skills",
)
_REQUIRED_RECORD = ("name", "path", "skill_md", "skill_sha256", "invocation")


class RegistryError(ValueError):
    """The registry is missing, corrupt, wrong-schema, or shape-invalid."""


def resolve_governance_root(start: Path | None = None) -> Path:
    """Resolve the governance root that carries the generated registry.

    Order: ``L9_GOVERNANCE_DIR`` → ``~/.cursor-governance`` → ancestors of
    ``start`` (default: this file). The last fallback returns the home clone
    even when absent so callers fail with a clear "registry missing" error.
    """
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if (candidate / REGISTRY_REL).is_file():
            return candidate
    home = Path.home() / ".cursor-governance"
    if (home / REGISTRY_REL).is_file():
        return home
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        if (parent / REGISTRY_REL).is_file():
            return parent
    return home


@dataclass(frozen=True)
class Registry:
    """Validated registry with a name index and generation identity."""

    root: Path
    path: Path
    data: dict[str, Any]
    generation_id: str
    source_manifest_sha256: str
    source_skill_corpus_sha256: str
    index: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def routing(self) -> dict[str, Any]:
        return self.data["routing"]

    @property
    def skills(self) -> list[dict[str, Any]]:
        return self.data["skills"]

    @property
    def skills_root(self) -> Path:
        return self.root / SKILLS_REL

    def identity(self) -> dict[str, str]:
        return {
            "generation_id": self.generation_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_skill_corpus_sha256": self.source_skill_corpus_sha256,
            "path": REGISTRY_REL.as_posix(),
        }

    def resolve_skill_record(self, name: str) -> dict[str, Any]:
        """Return the record for ``name`` or raise ``RegistryError``."""
        try:
            return self.index[name]
        except KeyError as exc:
            raise RegistryError(f"unknown skill: {name!r}") from exc


def _validate_record(record: Any, position: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RegistryError(f"skills[{position}] is not an object")
    missing = [key for key in _REQUIRED_RECORD if key not in record]
    if missing:
        raise RegistryError(f"skills[{position}] missing {missing}")
    name = record["name"]
    if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
        raise RegistryError(f"skills[{position}] invalid name: {name!r}")
    if record["path"] != f"skills/{name}":
        raise RegistryError(f"{name}: path must be skills/{name}, got {record['path']!r}")
    if record["skill_md"] != f"skills/{name}/SKILL.md":
        raise RegistryError(f"{name}: skill_md must be skills/{name}/SKILL.md")
    digest = record["skill_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise RegistryError(f"{name}: skill_sha256 must be a hex sha256")
    if record["invocation"] not in _INVOCATIONS:
        raise RegistryError(f"{name}: invocation must be one of {sorted(_INVOCATIONS)}")
    return record


def validate_registry(data: Any, *, root: Path | None = None, check_files: bool = False) -> None:
    """Raise ``RegistryError`` unless ``data`` is a well-formed v2 registry.

    ``check_files=True`` additionally stats every ``skill_md`` under ``root``
    (CI / generation use; a prompt hook must not pay this per prompt).
    """
    if not isinstance(data, dict):
        raise RegistryError("registry is not an object")
    missing = [key for key in _REQUIRED_TOP if key not in data]
    if missing:
        raise RegistryError(f"registry missing top-level keys: {missing}")
    if data["schema_version"] != SCHEMA_VERSION:
        raise RegistryError(
            f"registry schema_version {data['schema_version']!r} != {SCHEMA_VERSION}"
        )
    for key in ("generation_id", "source_manifest_sha256", "source_skill_corpus_sha256"):
        value = data[key]
        if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
            raise RegistryError(f"registry {key} must be a hex sha256")
    if not isinstance(data["routing"], dict):
        raise RegistryError("registry routing must be an object")
    routes = data["routing"].get("routes", [])
    if not isinstance(routes, list):
        raise RegistryError("registry routing.routes must be a list")
    skills = data["skills"]
    if not isinstance(skills, list) or not skills:
        raise RegistryError("registry skills must be a non-empty list")
    seen: set[str] = set()
    for position, record in enumerate(skills):
        name = _validate_record(record, position)["name"]
        if name in seen:
            raise RegistryError(f"duplicate skill name: {name}")
        seen.add(name)
    for route in routes:
        if not isinstance(route, dict) or not route.get("primary"):
            raise RegistryError(f"route without primary: {route!r}")
        if route["primary"] not in seen:
            raise RegistryError(f"route {route.get('id')!r} names unknown primary")
        for support in route.get("supporting", []):
            if support not in seen:
                raise RegistryError(f"route {route.get('id')!r} names unknown support")
    if check_files:
        if root is None:
            raise RegistryError("check_files requires root")
        for record in skills:
            if not (root / record["skill_md"]).is_file():
                raise RegistryError(f"{record['name']}: primary resource missing")


def load_registry(root: Path | None = None, *, check_files: bool = False) -> Registry:
    """Load and validate the registry under ``root``; raise ``RegistryError``."""
    root = (root or resolve_governance_root()).resolve()
    path = root / REGISTRY_REL
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistryError(f"registry unreadable: {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"registry corrupt: {path}: {exc}") from exc
    validate_registry(data, root=root, check_files=check_files)
    index = {record["name"]: record for record in data["skills"]}
    return Registry(
        root=root,
        path=path,
        data=data,
        generation_id=data["generation_id"],
        source_manifest_sha256=data["source_manifest_sha256"],
        source_skill_corpus_sha256=data["source_skill_corpus_sha256"],
        index=index,
    )


def skill_index(registry: Registry | dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Name → record index for a ``Registry`` or a raw registry dict."""
    if isinstance(registry, Registry):
        return registry.index
    return {record["name"]: record for record in registry.get("skills", [])}


__all__ = [
    "REGISTRY_REL",
    "SCHEMA_VERSION",
    "SKILLS_REL",
    "Registry",
    "RegistryError",
    "load_registry",
    "resolve_governance_root",
    "skill_index",
    "validate_registry",
]
