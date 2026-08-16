#!/usr/bin/env python3
"""Loader for ops/secrets/capabilities.yaml — shared by the client and the broker.

Both sides parse the same file so a capability cannot mean one thing to the
caller and another to the enforcer. The asymmetry that matters is in *use*, not
in the schema: the model-side client reads this to know which ids exist and what
it may pass; the broker reads it to know which host, method, path, credential
and sanitizer it will accept — and refuses anything not spelled out here.

``secret_refs`` are names only. This module never resolves them, and importing
it gives a caller no path to a value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_REGISTRY = HERE / "capabilities.yaml"

try:
    import yaml
except ImportError:  # pragma: no cover - the locked env always has pyyaml
    yaml = None  # type: ignore[assignment]


@dataclass(frozen=True)
class CapabilitySpec:
    """One registered capability. Every field is a constraint, not a hint."""

    id: str
    summary: str
    secret_refs: tuple[str, ...]
    upstream_host: str
    base_path: str
    methods: frozenset[str]
    paths: tuple[str, ...]
    params: dict[str, dict[str, Any]]
    repository_scope: str
    sanitizer: str
    audit_class: str
    failure_semantics: str
    surfaces: frozenset[str]
    max_response_bytes: int
    max_requests_per_minute: int
    execution: str = "broker"
    requires: tuple[str, ...] = field(default_factory=tuple)
    platform_proxy_preferred: bool = False

    @property
    def is_advisory(self) -> bool:
        """Advisory capabilities degrade; authority-bearing ones deny (contract §18)."""
        return self.failure_semantics == "degrade"

    def caller_params(self) -> tuple[str, ...]:
        """Params the caller MAY supply. Everything else is broker-derived."""
        return tuple(
            name for name, rule in self.params.items() if rule.get("source") == "caller"
        )

    def allows(self, method: str, path: str) -> bool:
        """Fixed upstream contract check. No wildcards, no prefix matching."""
        return method.upper() in self.methods and path in self.paths


class CapabilityRegistry:
    def __init__(self, specs: dict[str, CapabilitySpec]) -> None:
        self._specs = specs

    def get(self, capability_id: str) -> CapabilitySpec | None:
        return self._specs.get(capability_id)

    def ids(self) -> list[str]:
        return sorted(self._specs)

    def secret_refs(self) -> set[str]:
        """Every secret name the plane can reach. Names only — used by validators."""
        return {ref for spec in self._specs.values() for ref in spec.secret_refs}

    def __len__(self) -> int:
        return len(self._specs)

    def __contains__(self, capability_id: object) -> bool:
        return capability_id in self._specs


def load_registry(path: Path | None = None) -> CapabilityRegistry:
    """Parse the registry, applying declared defaults. Fails closed on bad input."""
    source = path or DEFAULT_REGISTRY
    if yaml is None:
        raise RuntimeError("pyyaml unavailable — cannot load the capability registry")
    raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}

    defaults = raw.get("defaults") or {}
    default_limits = defaults.get("limits") or {}
    default_surfaces = defaults.get("surfaces") or ["model-controlled"]
    default_failure = defaults.get("failure_semantics", "degrade")

    specs: dict[str, CapabilitySpec] = {}
    for entry in raw.get("capabilities") or []:
        capability_id = str(entry.get("id") or "").strip()
        if not capability_id:
            raise ValueError("capability entry without an id")
        limits = entry.get("limits") or {}
        specs[capability_id] = CapabilitySpec(
            id=capability_id,
            summary=str(entry.get("summary") or ""),
            secret_refs=tuple(entry.get("secret_refs") or ()),
            upstream_host=str(entry.get("upstream_host") or ""),
            base_path=str(entry.get("base_path") or ""),
            methods=frozenset(m.upper() for m in (entry.get("methods") or ())),
            paths=tuple(entry.get("paths") or ()),
            params=dict(entry.get("params") or {}),
            repository_scope=str(entry.get("repository_scope") or "workspace"),
            sanitizer=str(entry.get("sanitizer") or ""),
            audit_class=str(entry.get("audit_class") or "unclassified"),
            failure_semantics=str(entry.get("failure_semantics") or default_failure),
            surfaces=frozenset(entry.get("surfaces") or default_surfaces),
            max_response_bytes=int(
                limits.get("max_response_bytes", default_limits.get("max_response_bytes", 1 << 22))
            ),
            max_requests_per_minute=int(
                limits.get(
                    "max_requests_per_minute", default_limits.get("max_requests_per_minute", 30)
                )
            ),
            execution=str(entry.get("execution") or "broker"),
            requires=tuple(entry.get("requires") or ()),
            platform_proxy_preferred=bool(entry.get("platform_proxy_preferred", False)),
        )
    return CapabilityRegistry(specs)


__all__ = ["CapabilityRegistry", "CapabilitySpec", "DEFAULT_REGISTRY", "load_registry"]
