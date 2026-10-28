"""One projection/receipt verification owner.

The governance checker and the runtime assertion issuer both call
``verify_identity_projection``. The issuer must not copy ``receipt.output.digest``
into a signed assertion until that digest is the SHA-256 of the projection
file bytes, the receipt and projection share source coordinates, those
coordinates match the governing binding, and the resolved actor and surface
are ``current``.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

_COORDINATE_KEYS = (
    "profile_ref",
    "profile_digest",
    "source_repository",
    "source_revision",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def projection_output_digest(projection_bytes: bytes) -> str:
    """SHA-256 of the projection file bytes, prefixed the way receipts are."""

    return "sha256:" + hashlib.sha256(projection_bytes).hexdigest()


def verify_identity_projection(
    projection: Mapping[str, Any],
    receipt: Mapping[str, Any],
    projection_bytes: bytes,
    binding: Mapping[str, Any] | None = None,
    *,
    actor_id: str | None = None,
    surface_id: str | None = None,
) -> list[str]:
    """Fail-closed checks shared by the checker and the assertion issuer.

    ``actor_id`` and ``surface_id`` are the subjects about to be sealed. The
    checker omits them and keeps its own registry walk. An empty surface id
    means the surface is unknown and is not required to be current.
    """

    failures: list[str] = []
    if receipt.get("schema") != "l9.projection-receipt/v1":
        failures.append("invalid identity projection receipt schema")
        return failures
    projected = _mapping(projection.get("projection"))
    receipt_projection = _mapping(receipt.get("projection"))
    if binding is not None:
        generated = _mapping(binding.get("generated_projection"))
        upstream = _mapping(binding.get("upstream"))
        expected_profile = _mapping(upstream.get("projection_profile")).get("artifact_ref")
        if receipt_projection.get("artifact_ref") != generated.get("artifact_ref"):
            failures.append("receipt artifact reference disagrees with binding")
        if projection.get("artifact_id") != generated.get("artifact_ref"):
            failures.append("identity projection artifact disagrees with binding")
        if projected.get("profile_ref") != expected_profile:
            failures.append("identity projection profile disagrees with binding")
    for key in _COORDINATE_KEYS:
        if receipt_projection.get(key) != projected.get(key):
            failures.append(f"receipt {key} disagrees with projection")
    if receipt_projection.get("sources") != projected.get("sources"):
        failures.append("receipt source coordinates disagree with projection")
    output = _mapping(receipt.get("output"))
    if output.get("digest") != projection_output_digest(projection_bytes):
        failures.append("identity projection output digest does not match receipt")
    if actor_id is not None:
        _require_current(projection.get("actors"), actor_id, "actor", failures)
    if surface_id:
        _require_current(projection.get("surfaces"), surface_id, "surface", failures)
    return failures


def _require_current(raw: Any, item_id: str, kind: str, failures: list[str]) -> None:
    found: Mapping[str, Any] | None = None
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping) and item.get("id") == item_id:
                found = item
                break
    if found is None:
        failures.append(f"resolved {kind} {item_id} is not in the identity projection")
        return
    if found.get("status") != "current":
        failures.append(f"resolved {kind} {item_id} is not current in the identity projection")
