"""Shared Program Execution compilation policy.

This module owns defaults that must not drift between ingress compilers.
Operator input may override an explicit field, but an omitted representational
field is compiler work rather than a reason to block execution.
"""

from __future__ import annotations

DEFAULT_PROGRAM_OWNER = "Quantum AI Partners"


def resolve_program_owner(value: object | None = None) -> str:
    """Return the explicit owner or the canonical Program Execution default."""
    owner = str(value or "").strip()
    return owner or DEFAULT_PROGRAM_OWNER


__all__ = ["DEFAULT_PROGRAM_OWNER", "resolve_program_owner"]
