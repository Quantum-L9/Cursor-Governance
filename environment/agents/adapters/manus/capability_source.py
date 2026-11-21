#!/usr/bin/env python3
"""Derive the Manus adapter's capability manifest from the canonical registry.

``ops/secrets/capabilities.yaml`` is the single source of truth for what a
capability *is*: its upstream host, permitted verbs, allow-listed paths, caller
parameters, secret reference, response sanitizer and admissible surfaces. The
adapter's ``infisical_capabilities.json`` used to restate one of those entries by
hand, which is drift by construction — the registry could change and the
connector would never know.

This module is the only place that translates registry vocabulary into the
adapter's ``Capability`` shape. It is deliberately **not** imported by
``infisical_mcp_server.py``: the connector keeps consuming the rendered JSON, so
it still starts with no repository import, no network and no credentials.

Shape mismatch, and the decision taken
--------------------------------------
The registry models one capability as *many* methods over *many* paths. The
adapter models one capability as exactly one method over exactly one path,
pinned to ``api.github.com``, ``GET`` and the ``GITHUB_TOKEN`` inventory key,
behind a named bounded response filter. The two are not mechanically
interchangeable.

Widening the adapter to the registry's cardinality was rejected. Rendering
``github.mcp`` faithfully would publish 21 endpoints — including
``/search/code``, ``/user/repos`` and ``/gists`` — behind a ``passthrough``
sanitizer, turning a bounded single-object read into a general GitHub proxy with
a live credential behind it. The adapter stays narrow.

Instead every adapter capability is an explicit :class:`Projection` of exactly
one registry endpoint. A projection supplies *selection and stricter policy*
(which endpoint, which argument patterns, which response fields). Every
security-relevant fact — host, verb, path, secret reference, caller-parameter
sanction, surface admission — is read from the registry at render time and
verified against it. A projection that no longer matches the registry raises
:class:`DerivationError`; it never degrades into a silent drop.

Every registry entry that is not rendered appears in ``exclusions`` with a
machine-derived reason plus the exact methods and paths that are not being
rendered, so an operator can see *why* a capability is missing instead of
assuming it does not exist. Where the adapter is deliberately stricter than the
registry, the difference is recorded in ``narrowings`` rather than left implicit.

Nothing here reads a secret value. ``secret_refs`` are names, and the module
performs no I/O of its own: the caller passes the registry and the source digest.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Any

#: The adapter's fixed upstream allowlist. Mirrors the host check in
#: ``Capability.validate()`` and ``GITHUB_API_ORIGIN`` in the server; a test
#: pins all three together so they cannot drift apart.
ADAPTER_ORIGIN = "https://api.github.com"
ADAPTER_HOST = "api.github.com"

#: The only inventory key the adapter is permitted to resolve. Mirrors the
#: ``secret_key`` check in ``Capability.validate()``.
ALLOWED_SECRET_REF = "GITHUB_TOKEN"

#: The adapter's only read verb. The server refuses anything else.
ALLOWED_METHOD = "GET"

#: Trust class that admits the Manus surface. ``surface_trust.classify("manus")``
#: returns ``model-controlled``; ``capabilities.yaml`` speaks trust classes, not
#: adapter names, so that is the literal to match. A test pins the two together.
MANUS_TRUST_CLASS = "model-controlled"

#: The one Manus surface id, used only for provenance in the rendered file.
MANUS_SURFACE_ID = "manus"

REGISTRY_RELATIVE = Path("ops/secrets/capabilities.yaml")

#: Named response filters the adapter actually implements. The registry's
#: ``sanitizer`` field names a filter; a name with no entry here has no bounded
#: implementation in this adapter and therefore cannot be rendered.
SANITIZERS: Mapping[str, tuple[str, ...]] = {
    "github_repository_metadata": (
        "id",
        "node_id",
        "name",
        "full_name",
        "private",
        "html_url",
        "description",
        "fork",
        "archived",
        "disabled",
        "visibility",
        "default_branch",
        "created_at",
        "updated_at",
        "pushed_at",
        "license",
    ),
}

#: Reason precedence. The first code that applies is the one reported, so an
#: exclusion always names the most fundamental blocker rather than the last one
#: checked.
_REASON_PRECEDENCE = (
    "surface_not_admissible",
    "unsupported_upstream_host",
    "unsupported_secret_ref",
    "non_read_method",
    "multiple_methods",
    "multiple_paths",
    "no_sanitizer_implementation",
    "not_projected",
)


class DerivationError(Exception):
    """A projection cannot be honoured against the registry as it stands.

    Raised instead of dropping the capability, so a registry edit that
    invalidates a projection fails the build rather than silently shrinking the
    connector's surface.
    """


@dataclass(frozen=True)
class Projection:
    """One adapter capability, expressed as a selection of one registry endpoint.

    ``capability_id`` is the adapter-local invocation key. ``registry_id``,
    ``method`` and ``path`` select the registry endpoint. ``arguments`` and
    ``description`` are adapter-owned policy: the registry sanctions *which*
    parameters a caller may influence, the adapter decides how strictly it will
    accept them.
    """

    capability_id: str
    registry_id: str
    method: str
    path: str
    sanitizer: str
    description: str
    arguments: Mapping[str, str]

    def placeholders(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    field_name
                    for _, field_name, _, _ in Formatter().parse(self.path)
                    if field_name is not None
                }
            )
        )


#: The complete adapter surface. Adding a capability is a registry entry plus a
#: projection here, never a hand-edited JSON file.
PROJECTIONS: tuple[Projection, ...] = (
    Projection(
        capability_id="github.get_repository",
        registry_id="github.mcp",
        method="GET",
        path="/repos/{owner}/{repo}",
        sanitizer="github_repository_metadata",
        description=(
            "Read repository metadata from the GitHub REST API using the configured "
            "GITHUB_TOKEN. This capability cannot modify GitHub resources."
        ),
        arguments={
            "owner": "[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?",
            "repo": "[A-Za-z0-9._-]{1,100}",
        },
    ),
)


@dataclass(frozen=True)
class Derivation:
    """The rendered capability set plus everything deliberately left out."""

    capabilities: Mapping[str, dict[str, Any]]
    exclusions: tuple[dict[str, Any], ...]
    narrowings: tuple[dict[str, Any], ...]
    source_sha256: str
    source_schema_version: str

    def manifest(self) -> dict[str, Any]:
        """The on-disk manifest, in a fixed key order for byte-stable output."""
        return {
            "schema": "l9.manus.infisical-capabilities.v1",
            "generated": {
                "do_not_edit": True,
                "generator": "render_infisical_capabilities.py",
                "source": REGISTRY_RELATIVE.as_posix(),
                "source_schema_version": self.source_schema_version,
                "source_sha256": self.source_sha256,
                "surface": MANUS_SURFACE_ID,
                "trust_class": MANUS_TRUST_CLASS,
                "renderer_module": "capability_source.py",
            },
            "capabilities": dict(self.capabilities),
            "exclusions": list(self.exclusions),
            "narrowings": list(self.narrowings),
        }


def source_digest(registry_path: Path) -> str:
    """Digest the registry bytes.

    Digesting the whole file — not just the fields we read — is intentional:
    any registry edit, including a new entry or a changed comment, invalidates
    the rendered manifest and forces a reviewed re-render. That is the drift
    alarm, and a no-op re-render is a one-line diff.
    """
    return hashlib.sha256(registry_path.read_bytes()).hexdigest()


def derive(
    registry: Any,
    *,
    source_sha256: str,
    source_schema_version: str = "1.0.0",
    projections: Sequence[Projection] = PROJECTIONS,
    sanitizers: Mapping[str, tuple[str, ...]] = SANITIZERS,
) -> Derivation:
    """Render every projection and account for every registry entry.

    ``registry`` is any object exposing ``ids()`` and ``get(id)`` returning a
    spec with the ``capability_registry.CapabilitySpec`` attributes. It is
    injected rather than loaded here so this module stays free of I/O and
    import-time side effects.
    """
    specs = {capability_id: registry.get(capability_id) for capability_id in registry.ids()}
    rendered: dict[str, dict[str, Any]] = {}
    selected: dict[str, list[Projection]] = defaultdict(list)
    narrowings: list[dict[str, Any]] = []

    for projection in projections:
        spec = specs.get(projection.registry_id)
        if spec is None:
            raise DerivationError(
                f"projection '{projection.capability_id}' selects registry id "
                f"'{projection.registry_id}', which the registry does not declare"
            )
        if projection.capability_id in rendered:
            raise DerivationError(f"duplicate adapter capability id '{projection.capability_id}'")
        rendered[projection.capability_id] = _render(projection, spec, sanitizers)
        selected[projection.registry_id].append(projection)
        narrowings.extend(_narrowings(projection, spec))

    exclusions = tuple(
        _exclusion(spec, selected.get(spec.id, ()), sanitizers)
        for spec in sorted(specs.values(), key=lambda item: item.id)
    )

    return Derivation(
        capabilities=rendered,
        exclusions=exclusions,
        narrowings=tuple(narrowings),
        source_sha256=source_sha256,
        source_schema_version=source_schema_version,
    )


def _render(
    projection: Projection, spec: Any, sanitizers: Mapping[str, tuple[str, ...]]
) -> dict[str, Any]:
    """Verify one projection against its registry entry, then render it."""
    origin = _origin(spec)
    if origin != ADAPTER_ORIGIN:
        raise DerivationError(
            f"projection '{projection.capability_id}' resolves to origin '{origin}' but the "
            f"adapter only reaches '{ADAPTER_ORIGIN}'"
        )
    if projection.method.upper() not in spec.methods:
        raise DerivationError(
            f"projection '{projection.capability_id}' uses {projection.method} but "
            f"'{spec.id}' permits {sorted(spec.methods)}"
        )
    if projection.method.upper() != ALLOWED_METHOD:
        raise DerivationError(
            f"projection '{projection.capability_id}' uses {projection.method}; the adapter is "
            f"read-only and permits only {ALLOWED_METHOD}"
        )
    if projection.path not in spec.paths:
        raise DerivationError(
            f"projection '{projection.capability_id}' uses path '{projection.path}', which "
            f"'{spec.id}' does not allow-list"
        )
    if tuple(spec.secret_refs) != (ALLOWED_SECRET_REF,):
        raise DerivationError(
            f"projection '{projection.capability_id}' resolves '{spec.id}' whose secret_refs "
            f"{list(spec.secret_refs)} are not exactly ['{ALLOWED_SECRET_REF}']"
        )
    if MANUS_TRUST_CLASS not in spec.surfaces:
        raise DerivationError(
            f"projection '{projection.capability_id}' resolves '{spec.id}' whose surfaces "
            f"{sorted(spec.surfaces)} do not admit '{MANUS_TRUST_CLASS}'"
        )
    if projection.sanitizer not in sanitizers:
        raise DerivationError(
            f"projection '{projection.capability_id}' names sanitizer "
            f"'{projection.sanitizer}', which the adapter does not implement"
        )

    placeholders = projection.placeholders()
    if placeholders != tuple(sorted(projection.arguments)):
        raise DerivationError(
            f"projection '{projection.capability_id}' path placeholders {list(placeholders)} "
            f"do not match its declared arguments {sorted(projection.arguments)}"
        )
    for name in placeholders:
        rule = spec.params.get(name)
        if not isinstance(rule, Mapping) or rule.get("source") != "caller":
            raise DerivationError(
                f"projection '{projection.capability_id}' exposes path parameter '{name}', "
                f"which '{spec.id}' does not declare as caller-controlled"
            )

    return {
        "description": projection.description,
        "secret_key": ALLOWED_SECRET_REF,
        "origin": origin,
        "method": projection.method.upper(),
        "path_template": projection.path,
        "arguments": {name: projection.arguments[name] for name in placeholders},
        "response_fields": list(sanitizers[projection.sanitizer]),
        "provenance": {
            "registry_id": spec.id,
            "registry_method": projection.method.upper(),
            "registry_path": projection.path,
            "registry_secret_ref": ALLOWED_SECRET_REF,
            "registry_sanitizer": spec.sanitizer,
            "adapter_sanitizer": projection.sanitizer,
        },
    }


def _origin(spec: Any) -> str:
    base_path = spec.base_path or ""
    if base_path and not base_path.startswith("/"):
        raise DerivationError(
            f"registry entry '{spec.id}' has base_path '{base_path}' without a leading slash"
        )
    return f"https://{spec.upstream_host}{base_path}"


def _blocking_codes(spec: Any, sanitizers: Mapping[str, tuple[str, ...]]) -> list[str]:
    """Every reason this entry cannot be rendered as a whole, most fundamental first."""
    codes: list[str] = []
    if MANUS_TRUST_CLASS not in spec.surfaces:
        codes.append("surface_not_admissible")
    if spec.upstream_host != ADAPTER_HOST:
        codes.append("unsupported_upstream_host")
    if tuple(spec.secret_refs) != (ALLOWED_SECRET_REF,):
        codes.append("unsupported_secret_ref")
    if ALLOWED_METHOD not in spec.methods:
        codes.append("non_read_method")
    if len(spec.methods) != 1:
        codes.append("multiple_methods")
    if len(spec.paths) != 1:
        codes.append("multiple_paths")
    if spec.sanitizer not in sanitizers:
        codes.append("no_sanitizer_implementation")
    return [code for code in _REASON_PRECEDENCE if code in codes]


def _reason_text(
    code: str, spec: Any, sanitizers: Mapping[str, tuple[str, ...]] = SANITIZERS
) -> str:
    if code == "surface_not_admissible":
        return (
            f"surfaces {sorted(spec.surfaces)} do not admit the Manus trust class "
            f"'{MANUS_TRUST_CLASS}'"
        )
    if code == "unsupported_upstream_host":
        return (
            f"upstream_host '{spec.upstream_host}' is not the adapter's fixed allowlisted "
            f"host '{ADAPTER_HOST}'"
        )
    if code == "unsupported_secret_ref":
        return (
            f"secret_refs {list(spec.secret_refs)} are not exactly the adapter's allowlisted "
            f"secret reference ['{ALLOWED_SECRET_REF}']"
        )
    if code == "non_read_method":
        return f"methods {sorted(spec.methods)} are not read-only {ALLOWED_METHOD}"
    if code == "multiple_methods":
        return (
            f"declares {len(spec.methods)} methods {sorted(spec.methods)}; the adapter models "
            "exactly one method per capability"
        )
    if code == "multiple_paths":
        return (
            f"declares {len(spec.paths)} allow-listed paths; the adapter models exactly one "
            "path template per capability"
        )
    if code == "no_sanitizer_implementation":
        return (
            f"sanitizer '{spec.sanitizer}' has no bounded implementation in the adapter "
            f"(implemented: {sorted(sanitizers)})"
        )
    if code == "not_projected":
        return (
            "every field is representable on this surface, but no reviewed projection in "
            "capability_source.PROJECTIONS selects this entry; add one, or record why it "
            "stays out"
        )
    raise DerivationError(f"unknown exclusion reason code: {code}")


def _exclusion(
    spec: Any,
    projections: Iterable[Projection],
    sanitizers: Mapping[str, tuple[str, ...]] = SANITIZERS,
) -> dict[str, Any]:
    """Account for everything in one registry entry that is not being rendered."""
    selected = list(projections)
    rendered_paths = {projection.path for projection in selected}
    rendered_methods = {projection.method.upper() for projection in selected}
    unrendered_paths = sorted(set(spec.paths) - rendered_paths)
    unrendered_methods = sorted(set(spec.methods) - rendered_methods)

    if selected:
        disposition = "partially_rendered"
        reason_code = "endpoint_not_projected"
        rendered_ids = [projection.capability_id for projection in selected]
        reason = (
            f"renders {len(rendered_paths)} of {len(spec.paths)} registry paths as "
            f"{', '.join(rendered_ids)}; the remaining {len(unrendered_paths)} path(s) and "
            f"{len(unrendered_methods)} method(s) are not representable in a "
            "one-method/one-path capability"
        )
    else:
        disposition = "excluded"
        codes = _blocking_codes(spec, sanitizers)
        # A representable entry with no projection is a decision someone has not
        # made yet, not a shape problem. Name it rather than crashing or hiding it.
        codes = codes or ["not_projected"]
        reason_code = codes[0]
        rendered_ids = []
        reason = _reason_text(reason_code, spec, sanitizers)
        unrendered_paths = sorted(spec.paths)
        unrendered_methods = sorted(spec.methods)

    record: dict[str, Any] = {
        "registry_id": spec.id,
        "disposition": disposition,
        "rendered_capability_ids": rendered_ids,
        "reason_code": reason_code,
        "reason": reason,
        "unrendered_methods": unrendered_methods,
        "unrendered_paths": unrendered_paths,
    }
    if not selected:
        record["blocking_reason_codes"] = codes
    return record


def _narrowings(projection: Projection, spec: Any) -> list[dict[str, Any]]:
    """Record where the adapter is deliberately stricter than the registry."""
    rows: list[dict[str, Any]] = []

    def row(field: str, registry_value: str, adapter_value: str) -> dict[str, Any]:
        return {
            "registry_id": spec.id,
            "capability_id": projection.capability_id,
            "field": field,
            "registry": registry_value,
            "adapter": adapter_value,
        }

    if set(spec.methods) != {projection.method.upper()}:
        rows.append(row("method", ", ".join(sorted(spec.methods)), projection.method.upper()))
    if set(spec.paths) != {projection.path}:
        rows.append(row("paths", f"{len(spec.paths)} allow-listed paths", projection.path))
    if spec.sanitizer != projection.sanitizer:
        rows.append(row("sanitizer", spec.sanitizer, projection.sanitizer))
    for name in projection.placeholders():
        rule = spec.params.get(name) or {}
        described = str(rule.get("validate") or "unspecified")
        if rule.get("max_bytes"):
            described = f"{described} (max_bytes={rule['max_bytes']})"
        rows.append(row(f"param.{name}", described, f"regex {projection.arguments[name]}"))
    return rows


__all__ = [
    "ADAPTER_HOST",
    "ADAPTER_ORIGIN",
    "ALLOWED_METHOD",
    "ALLOWED_SECRET_REF",
    "Derivation",
    "DerivationError",
    "MANUS_SURFACE_ID",
    "MANUS_TRUST_CLASS",
    "PROJECTIONS",
    "Projection",
    "REGISTRY_RELATIVE",
    "SANITIZERS",
    "derive",
    "source_digest",
]
