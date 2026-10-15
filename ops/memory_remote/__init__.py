"""Consumer side of the remote Memory MCP transport (ADR-0053, CANONICAL_LAW §8.10).

Lives outside ``ops/memory`` on purpose: that package is the stdio control-plane
boundary and imports no network module (``tests/ops/memory/test_transport_boundary.py``).
This package is the one consumer module that speaks HTTP to Memory, and only to
the admitted ``memory-remote-mcp/v1`` service.
"""
