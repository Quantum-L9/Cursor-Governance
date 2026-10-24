# pyright: strict
"""The one canonical-JSON digest every Cursor-Governance consumer computes.

Implements ``binding_conventions.canonical_json`` and ``semantic_digest`` from
``Quantum-L9/.github`` ``semantics/projection_engine_contract.yaml`` exactly. That contract
forbids a second digest form (ADR-021), so every tool here that hashes a value imports this
module instead of carrying its own copy.

It also owns ``deterministic_yaml_normalization_v1``: the parse that turns a YAML contract
into the value ``canonical_json`` hashes (``canonical.schema.governance_contract.v1``
``integrity.canonical_serialization``). The parse is PyYAML ``SafeLoader`` with three
deterministic changes, each failing closed rather than guessing:

* implicit timestamps are not resolved: ``2026-08-26`` stays the string it was written as,
  so the quoted and unquoted forms of a date hash identically and the value stays JSON;
* a duplicate mapping key is an error, never last-one-wins;
* exactly one document per source.

Values canonical JSON cannot represent (non-finite floats, dates from an explicit
``!!timestamp`` tag, any other non-JSON type, two keys with the same string form) raise
``CanonicalizationError``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, cast

import yaml

SERIALIZATION_ID = "deterministic_yaml_normalization_v1"
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class CanonicalizationError(ValueError):
    """The value has no canonical-JSON form; nothing may be digested."""


def normalize(value: Any) -> Any:
    """``binding_conventions.canonical_json.normalize``: string keys, sorted; bytes as hex."""
    if isinstance(value, dict):
        mapping = cast(dict[Any, Any], value)
        out: dict[str, Any] = {}
        for key in sorted(mapping, key=str):
            name = str(key)
            if name in out:
                raise CanonicalizationError(f"two keys share the string form {name!r}")
            out[name] = normalize(mapping[key])
        return out
    if isinstance(value, (list, tuple)):
        return [normalize(item) for item in cast(list[Any], value)]
    if isinstance(value, (bytes, bytearray)):
        return {"$bytes_hex": bytes(cast(bytes, value)).hex()}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError(f"non-finite float {value!r}")
        return value
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise CanonicalizationError(f"no canonical-JSON form for {type(value).__name__}")


def canonical_json(value: Any) -> str:
    """``binding_conventions.canonical_json.serialize`` over the normalized value."""
    return json.dumps(normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_digest(value: Any) -> str:
    """``binding_conventions.semantic_digest``: ``sha256:`` + hex over canonical JSON (utf-8)."""
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bytes_digest(data: bytes) -> str:
    """``sha256:`` + hex over raw bytes (the convention's ``source_digest`` form)."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def is_digest(value: object) -> bool:
    return isinstance(value, str) and bool(_DIGEST.match(value))


class _DeterministicLoader(yaml.SafeLoader):
    """SafeLoader without implicit timestamps and without duplicate keys."""


_DeterministicLoader.yaml_implicit_resolvers = {
    first: [(tag, rx) for tag, rx in resolvers if tag != _TIMESTAMP_TAG]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key: Any = loader.construct_object(key_node, deep=True)  # pyright: ignore[reportUnknownMemberType]
        if key in seen:
            raise CanonicalizationError(f"duplicate mapping key {key!r} at {key_node.start_mark}")
        seen.add(key)
    return cast(dict[Any, Any], loader.construct_mapping(node, deep=True))


_DeterministicLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,  # pyright: ignore[reportArgumentType]
)


def load_yaml(text: str) -> Any:
    """Parse one YAML document under ``deterministic_yaml_normalization_v1``."""
    try:
        documents = list(yaml.load_all(text, Loader=_DeterministicLoader))  # noqa: S506
    except yaml.YAMLError as exc:
        raise CanonicalizationError(f"YAML does not parse: {exc}") from exc
    if len(documents) != 1:
        raise CanonicalizationError(f"expected exactly one YAML document, found {len(documents)}")
    value = documents[0]
    normalize(value)
    return value
