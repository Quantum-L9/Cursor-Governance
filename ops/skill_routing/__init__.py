"""Cursor-primary shared skill-routing ingress (CANONICAL_LAW §2.1).

Surface hooks (Cursor beforeSubmitPrompt, Claude UserPromptSubmit) are thin
I/O adapters over this package. Do not implement scoring under
environment/claude-code/.

Virtual Skill Plane layers (each owns exactly one concern):
  registry.py         load + validate the generated registry, name index
  route_prompt.py     deterministic selection (the brain)
  materialize.py      route names → exact validated canonical SKILL.md resources
  receipt.py          conversation-scoped, atomically written route receipts
  session_locator.py  one receipt identity per Cursor conversation
"""

from __future__ import annotations

from .materialize import MaterializationError, materialize_route
from .receipt import RECEIPT_SCHEMA, ReceiptError, build_receipt, read_receipt, write_receipt
from .registry import (
    REGISTRY_REL,
    Registry,
    RegistryError,
    resolve_governance_root,
    validate_registry,
)
from .registry import load_registry as load_validated_registry
from .route_prompt import load_registry, resolve_root, route_prompt
from .session_locator import RouteLocator, locator_from_payload

__all__ = [
    "MaterializationError",
    "RECEIPT_SCHEMA",
    "REGISTRY_REL",
    "ReceiptError",
    "Registry",
    "RegistryError",
    "RouteLocator",
    "build_receipt",
    "load_registry",
    "load_validated_registry",
    "locator_from_payload",
    "materialize_route",
    "read_receipt",
    "resolve_governance_root",
    "resolve_root",
    "route_prompt",
    "validate_registry",
    "write_receipt",
]
