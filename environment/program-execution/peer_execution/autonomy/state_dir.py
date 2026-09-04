#!/usr/bin/env python3
"""Resolve ``L9_AUTONOMY_STATE_DIR`` the way every consumer must agree on.

``Path.expanduser()`` expands ``~`` and nothing else, so a ``$HOME``-spelled
value survives as a literal path component. That is not a cosmetic difference:
``ops/autonomy/l4_local.py`` substitutes ``$HOME``/``${HOME}`` before calling
``expanduser()``, so with a ``$HOME`` spelling L4 resolved to the real home
directory while these modules resolved to ``<workspace>/$HOME/.l9/autonomy`` —
autonomy state split across two roots, one of them a junk directory written
inside the repository working tree.

The canonical spelling is ``~`` (``web/environment.env.example``,
``settings.template.json``), because the account variables field stores literal
text and never shell-expands. This helper accepts either spelling anyway, so a
future paste of the other one cannot re-open the split.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["expand_state_dir"]


def expand_state_dir(raw: str | None, default: str = ".l9/autonomy") -> Path:
    """Expand a configured state directory to a path, ``~`` or ``$HOME`` alike.

    The result may still be relative — the caller decides what a relative value
    is relative to, because that differs by consumer.
    """
    text = (raw or "").strip() or default
    home = str(Path.home())
    text = text.replace("${HOME}", home).replace("$HOME", home)
    return Path(text).expanduser()
