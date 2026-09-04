from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .bindings import load_peer_bindings
from .schema_registry import SchemaRegistry

_SUPPORTED_CONTEXT_POLICIES = {"contract-minimal-v1"}


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML document must be an object: {path}")
    return value


def load_profile_registry(subsystem_root: str | Path) -> dict[str, Any]:
    root = Path(subsystem_root).expanduser().resolve()
    value = _load_yaml(root / "registry/EXECUTION_PROFILE_REGISTRY.yaml")
    errors = SchemaRegistry(root).validate_execution_profile_registry(value)
    if errors:
        raise ValueError(f"execution profile registry schema errors: {errors}")
    default_ref = value["default_profile_ref"]
    if default_ref not in (value.get("profiles") or {}):
        raise ValueError(f"default execution profile does not exist: {default_ref}")
    return value


def load_profile(subsystem_root: str | Path, profile_ref: str) -> dict[str, Any]:
    if not isinstance(profile_ref, str) or not profile_ref.strip():
        raise ValueError("execution profile reference must be a non-empty string")
    registry = load_profile_registry(subsystem_root)
    profiles = registry.get("profiles") or {}
    profile = profiles.get(profile_ref)
    if not isinstance(profile, dict):
        raise ValueError(f"unknown execution profile: {profile_ref}")
    retry_policy = profile.get("retry_policy") or {}
    if retry_policy.get("max_attempts") != 1:
        raise ValueError(
            "execution profiles may not enable retries until Peer Execution Core "
            "implements canonical retry receipts"
        )
    context_policy_ref = profile.get("context_policy_ref")
    if context_policy_ref not in _SUPPORTED_CONTEXT_POLICIES:
        raise ValueError(f"unsupported context policy: {context_policy_ref!r}")
    return {"profile_ref": profile_ref, **profile}


def resolve_profile_for_provider(
    subsystem_root: str | Path,
    repository_root: str | Path,
    provider_ref: str,
    execution_profile_ref: str | None = None,
    *,
    fallback_profile_ref: str | None = None,
) -> dict[str, Any]:
    """Explicit ref, else the provider's unique peer binding, else the fallback.

    `fallback_profile_ref` is the adapter's own registry default; without one
    the subsystem-wide `default_profile_ref` applies.
    """
    subsystem = Path(subsystem_root).expanduser().resolve()
    if not isinstance(provider_ref, str) or not provider_ref.strip():
        raise ValueError("provider_ref must be a non-empty string")
    if execution_profile_ref:
        return load_profile(subsystem, execution_profile_ref)
    bindings = load_peer_bindings(repository_root)
    refs: set[str] = set()
    for peer in (bindings.get("peers") or {}).values():
        for binding in (peer.get("execution") or {}).get("bindings") or []:
            if binding.get("provider_ref") == provider_ref:
                refs.add(binding["execution_profile_ref"])
    if len(refs) > 1:
        raise ValueError(
            f"provider {provider_ref} has multiple profiles; explicit binding is required"
        )
    if refs:
        return load_profile(subsystem, next(iter(refs)))
    if fallback_profile_ref:
        return load_profile(subsystem, fallback_profile_ref)
    registry = load_profile_registry(subsystem)
    return load_profile(subsystem, registry["default_profile_ref"])
