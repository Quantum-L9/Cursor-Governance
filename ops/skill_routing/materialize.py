"""Materialize a RouteDecision into exact, validated canonical skill resources.

VSP-P1-003: the router returns *names*; the model must never rediscover a
routed skill. This layer turns each name into the one canonical ``SKILL.md``
under the governance skills root, or fails closed.

Security contract (every candidate):
  * resolved under the canonical ``skills/`` root (symlink escapes rejected)
  * regular file named exactly ``SKILL.md``
  * registry-declared path only — no absolute paths, no parent traversal
  * digest matches the registry (a corrupt or edited-out-of-band resource
    fails materialization; regenerate the registry to bless the change)
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Any

from .registry import SKILLS_REL, Registry, RegistryError, skill_index

MAX_SUPPORTING = 2


class MaterializationError(ValueError):
    """A routed skill could not be resolved to a valid canonical resource."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_skill_root(root: Path) -> Path:
    return (root / SKILLS_REL).resolve()


def resolve_skill_resource(
    name: str,
    record: dict[str, Any],
    root: Path,
    *,
    verify_digest: bool = True,
) -> dict[str, str]:
    """Resolve one registry record to a validated resource or raise."""
    declared = str(record.get("skill_md") or "")
    if not declared:
        raise MaterializationError(f"{name}: registry record has no skill_md")
    pure = PurePosixPath(declared)
    if pure.is_absolute() or declared.startswith(("/", "\\")):
        raise MaterializationError(f"{name}: foreign absolute path rejected: {declared}")
    if ".." in pure.parts:
        raise MaterializationError(f"{name}: parent traversal rejected: {declared}")
    if pure.name != "SKILL.md":
        raise MaterializationError(f"{name}: resource must be SKILL.md: {declared}")
    if pure.parts[:2] != (SKILLS_REL.as_posix(), name):
        raise MaterializationError(f"{name}: resource must live at skills/{name}/SKILL.md")

    skills_root = canonical_skill_root(root)
    candidate = root / Path(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise MaterializationError(f"{name}: canonical resource missing: {candidate}") from exc
    if not resolved.is_relative_to(skills_root):
        raise MaterializationError(f"{name}: resource escapes canonical skill root: {resolved}")
    if resolved.name != "SKILL.md" or not resolved.is_file():
        raise MaterializationError(f"{name}: resource is not a regular SKILL.md: {resolved}")

    expected = str(record.get("skill_sha256") or "")
    if verify_digest:
        actual = _sha256_file(resolved)
        if actual != expected:
            raise MaterializationError(
                f"{name}: SKILL.md digest {actual[:12]} != registry {expected[:12]} "
                "(regenerate ops/generated/skill-registry.json)"
            )
    return {
        "name": name,
        "skill_md": str(resolved),
        "invocation": str(record.get("invocation") or ""),
        "sha256": expected,
    }


def materialize_route(
    decision: dict[str, Any],
    registry: Registry | dict[str, Any],
    root: Path | None = None,
    *,
    verify_digest: bool = True,
) -> dict[str, Any]:
    """Return ``{"primary": resource, "supporting": [resource, ...]}``.

    ``root`` defaults to ``registry.root`` for a ``Registry``; a raw dict
    registry requires an explicit root.
    """
    if root is None:
        if isinstance(registry, Registry):
            root = registry.root
        else:
            raise MaterializationError("materialize_route requires a governance root")
    index = skill_index(registry)

    primary_name = str(decision.get("primary") or "")
    if not primary_name:
        raise MaterializationError("decision has no primary")
    supporting_names = [str(item) for item in decision.get("supporting", []) or []]
    if len(supporting_names) > MAX_SUPPORTING:
        raise MaterializationError(f"decision names {len(supporting_names)} supports (> 2)")
    if primary_name in supporting_names or len(set(supporting_names)) != len(supporting_names):
        raise MaterializationError("decision primary/supporting overlap")

    def record_for(name: str) -> dict[str, Any]:
        try:
            return index[name]
        except KeyError as exc:
            raise MaterializationError(f"unknown skill: {name!r}") from exc

    try:
        primary = resolve_skill_resource(
            primary_name, record_for(primary_name), root, verify_digest=verify_digest
        )
        supporting = [
            resolve_skill_resource(name, record_for(name), root, verify_digest=verify_digest)
            for name in supporting_names
        ]
    except RegistryError as exc:
        raise MaterializationError(str(exc)) from exc
    return {"primary": primary, "supporting": supporting}


__all__ = [
    "MAX_SUPPORTING",
    "MaterializationError",
    "canonical_skill_root",
    "materialize_route",
    "resolve_skill_resource",
]
