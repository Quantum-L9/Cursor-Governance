"""Hook-lane capability envelopes (ADR-0033, INV-03b).

Two lanes reach ``MemoryService``. The *agent lane* is the package's public
``l9-memory`` / MCP surface and Cursor-Governance does not mediate it. The
*hook lane* is automatic machinery — SessionStart / SessionEnd, plan prefetch,
``make pr`` publish, SGD ingest — and it must not carry an agent's open-ended
memory authority. This module is the narrower envelope that lane runs under:
per surface, the operations it may invoke, the record classes it may write,
how many records and how many bytes, and whether provenance is mandatory.

An envelope is enforced *client-side, before a process is spawned*. It is the
same ``MemoryService``, the same admission, the same store; only the
capability is narrower. It is never an alternate path and never a wall in
front of an agent (``tests/ops/memory/test_no_agent_lane_interposition.py``).

The preferred long-term form is a native hook principal on the memory
package's stdio door; until it ships, this envelope is the interim and the
``principal`` stamp on every integration receipt records which lane a call
ran on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
ENVELOPES_PATH = _REPO_ROOT / "ops" / "config" / "memory-hook-envelopes.json"

PRINCIPAL_HOOK = "hook"
PRINCIPAL_OPERATOR = "operator"

#: Error prefix every envelope refusal carries; consumers match on it rather
#: than on prose.
REJECTED_PREFIX = "REJECTED:envelope"


class UnknownHookSurface(ValueError):
    """A caller named a hook surface the envelope registry does not declare.

    Raised at client construction, not at first call: an unregistered surface
    is a wiring fault in the caller and must fail before any memory traffic.
    """


@dataclass(frozen=True)
class HookEnvelope:
    surface: str
    allowed_operations: frozenset[str]
    record_classes: frozenset[str]
    max_records: int
    max_bytes: int
    provenance_required: bool
    callers: tuple[str, ...] = field(default=())
    #: Namespaces this surface may write. Empty = unrestricted (every surface
    #: predating the field). A surface that exists to route material to ONE
    #: namespace — governance friction to cursor-governance — declares it, so
    #: a wiring slip cannot land that material in a repository's namespace.
    namespaces: frozenset[str] = field(default=frozenset())

    def violation(
        self,
        operation: str,
        *,
        memory_class: str | None = None,
        records_used: int = 0,
        records: int = 0,
        byte_size: int | None = None,
        provenance: bool | None = None,
        namespace: str | None = None,
    ) -> str | None:
        """The first reason ``operation`` falls outside this envelope, or ``None``.

        ``records`` is how many records *this* call would commit;
        ``records_used`` how many the client already committed on this
        surface. ``provenance`` is ``None`` when the operation carries no
        provenance concept (reads), ``True``/``False`` when it does.
        """

        if operation not in self.allowed_operations:
            return f"{REJECTED_PREFIX} {self.surface} does not permit operation {operation!r}"
        if memory_class is not None and memory_class not in self.record_classes:
            return (
                f"{REJECTED_PREFIX} {self.surface} does not permit record class "
                f"{memory_class!r} (allowed: {', '.join(sorted(self.record_classes)) or 'none'})"
            )
        if records and records_used + records > self.max_records:
            return (
                f"{REJECTED_PREFIX} {self.surface} exceeds max_records={self.max_records} "
                f"(used {records_used}, requested {records})"
            )
        if byte_size is not None and self.max_bytes and byte_size > self.max_bytes:
            return (
                f"{REJECTED_PREFIX} {self.surface} exceeds max_bytes={self.max_bytes} "
                f"(payload {byte_size})"
            )
        if self.provenance_required and provenance is False:
            return f"{REJECTED_PREFIX} {self.surface} requires provenance on {operation!r}"
        if self.namespaces and records and namespace not in self.namespaces:
            return (
                f"{REJECTED_PREFIX} {self.surface} may write only to "
                f"{', '.join(sorted(self.namespaces))} (requested {namespace!r})"
            )
        return None

    def principal(self) -> dict[str, Any]:
        return {
            "type": PRINCIPAL_HOOK,
            "surface": self.surface,
            "max_records": self.max_records,
            "max_bytes": self.max_bytes,
            "provenance_required": self.provenance_required,
        }


def operator_principal() -> dict[str, Any]:
    """The principal stamp for a client constructed without a surface."""

    return {"type": PRINCIPAL_OPERATOR, "surface": None}


def _parse(document: dict[str, Any]) -> dict[str, HookEnvelope]:
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, dict) or not surfaces:
        raise ValueError("memory-hook-envelopes.json: 'surfaces' must be a non-empty object")
    reads = set(document.get("read_operations") or ())
    writes = set(document.get("write_operations") or ())
    known = reads | writes
    parsed: dict[str, HookEnvelope] = {}
    for surface, spec in surfaces.items():
        if not isinstance(spec, dict):
            raise ValueError(f"memory-hook-envelopes.json: surface {surface!r} is not an object")
        ops = frozenset(str(op) for op in spec.get("allowed_operations") or ())
        unknown = ops - known
        if unknown:
            raise ValueError(
                f"memory-hook-envelopes.json: surface {surface!r} names operations the "
                f"registry does not declare: {sorted(unknown)}"
            )
        max_records = int(spec.get("max_records", 0))
        max_bytes = int(spec.get("max_bytes", 0))
        if (ops & writes) and max_records <= 0:
            raise ValueError(
                f"memory-hook-envelopes.json: surface {surface!r} permits writes but "
                "declares max_records<=0"
            )
        if not (ops & writes) and (max_records or max_bytes or spec.get("record_classes")):
            raise ValueError(
                f"memory-hook-envelopes.json: read-only surface {surface!r} must declare "
                "no record classes, max_records=0 and max_bytes=0"
            )
        parsed[surface] = HookEnvelope(
            surface=surface,
            allowed_operations=ops,
            record_classes=frozenset(str(c) for c in spec.get("record_classes") or ()),
            max_records=max_records,
            max_bytes=max_bytes,
            provenance_required=bool(spec.get("provenance_required", True)),
            callers=tuple(str(c) for c in spec.get("callers") or ()),
            namespaces=frozenset(str(n) for n in spec.get("namespaces") or ()),
        )
    return parsed


@lru_cache(maxsize=4)
def load_envelopes(path: Path | str = ENVELOPES_PATH) -> dict[str, HookEnvelope]:
    """Every declared hook surface. Raises on a malformed registry."""

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("memory-hook-envelopes.json must be an object")
    return _parse(document)


def envelope_for(surface: str, *, path: Path | str = ENVELOPES_PATH) -> HookEnvelope:
    envelopes = load_envelopes(path)
    try:
        return envelopes[surface]
    except KeyError:
        raise UnknownHookSurface(
            f"unknown hook surface {surface!r}; declared: {', '.join(sorted(envelopes))}"
        ) from None


def hook_surfaces(path: Path | str = ENVELOPES_PATH) -> tuple[str, ...]:
    return tuple(sorted(load_envelopes(path)))


__all__ = [
    "ENVELOPES_PATH",
    "PRINCIPAL_HOOK",
    "PRINCIPAL_OPERATOR",
    "REJECTED_PREFIX",
    "HookEnvelope",
    "UnknownHookSurface",
    "envelope_for",
    "hook_surfaces",
    "load_envelopes",
    "operator_principal",
]
