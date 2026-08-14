"""Compatibility shim. Canonical implementation: peer_execution/receipts.py."""

from __future__ import annotations

import peer_execution.receipts as _canonical

__all__ = list(
    getattr(_canonical, "__all__", None)
    or [name for name in dir(_canonical) if not name.startswith("_")]
)
globals().update({name: getattr(_canonical, name) for name in __all__})
