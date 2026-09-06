"""Cursor-Governance memory boundary — the only sanctioned path to memory.

Every memory byte leaving this repository crosses a public
``l9-graphite-memory`` contract through
:class:`ops.memory.control_plane_client.MemoryControlPlaneClient`, and every
memory byte entering it is retrieved through that same authority. Nothing
under ``ops/memory`` knows how to call Graphiti, holds a provider credential,
ranks, deduplicates, or authorizes a namespace; those concerns belong to
``MemoryService`` inside the memory package.

Modules (import them directly; this package deliberately imports nothing):

- ``runtime_binding``      — prove which exact memory package and CLI will run
- ``control_plane_client`` — thin request → command → typed-receipt adapter
- ``receipts``             — consumer-side parsing of canonical receipts
- ``namespace_context``    — repository identity and namespace *hints* (never grants)
- ``session_contracts``    — the Cursor-owned ContinuationCapsuleV2 schema
- ``hydration``            — canonical SessionStart hydration and typed continuation evidence
- ``session_state``        — local, non-authoritative per-session memory state (plan §22)
- ``diagnostics``          — layered readiness (R0 PACKAGE_BOUND … R9 PROJECTION_READY)

Campaign stage: C4 (canonical hydration is the SessionStart authority; the
legacy provider read survives only as a shadow diagnostic until C11).
"""

from __future__ import annotations

__all__ = [
    "control_plane_client",
    "diagnostics",
    "hydration",
    "namespace_context",
    "receipts",
    "runtime_binding",
    "session_contracts",
    "session_state",
]
