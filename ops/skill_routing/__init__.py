"""Cursor-primary shared skill-routing ingress (CANONICAL_LAW §2.1).

Surface hooks (Cursor beforeSubmitPrompt, Claude UserPromptSubmit) are thin
I/O adapters over this package. Do not implement scoring under
environment/claude-code/.
"""

from __future__ import annotations

from .route_prompt import (
    REGISTRY_REL,
    load_registry,
    resolve_root,
    route_prompt,
)

__all__ = [
    "REGISTRY_REL",
    "load_registry",
    "resolve_root",
    "route_prompt",
]
