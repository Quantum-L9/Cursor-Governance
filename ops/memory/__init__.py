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
- ``mcp_instantiation``    — per-machine Cursor MCP file; the memory entry is delegated
- ``cli``                  — ``python -m ops.memory.cli``: the operator/workflow front door
- ``legacy_reconciliation`` — provider-only history admitted through canonical ingress

Campaign stage: C12 (complete). The provider client is a tombstone, the
provider env plane and shadow reader are deleted, the egress scanner enforces,
and CANONICAL_LAW §8.2 / ADR-0030 name this package the single front door.
"""

from __future__ import annotations

__all__ = [
    "control_plane_client",
    "diagnostics",
    "hydration",
    "mcp_instantiation",
    "namespace_context",
    "receipts",
    "runtime_binding",
    "session_contracts",
    "session_state",
]
