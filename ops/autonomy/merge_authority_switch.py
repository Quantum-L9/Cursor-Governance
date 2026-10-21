"""Top-level switch for the merge-authority system (CANONICAL_LAW §6.2.16).

``ops/config/merge-authority.json`` names the enforcement mode:

- ``strict``   — §6.2.12–§6.2.15 as written: a human grant, a GitHub record or a
                 recorded operator instruction per repo, PR and head.
- ``disabled`` — no merge-permission check on any surface (Cursor and Claude
                 Code alike); the never-waive set (``--admin``, force-push, hard
                 reset) and stack ordering still apply.
- ``chat``     — reserved for agent-attested grants; reads as ``strict`` until
                 implemented.

``L9_MERGE_AUTHORITY_MODE`` overrides the file when it names a known mode (tests
pin ``strict``). A missing, unreadable or unknown value is ``strict``, so
deleting the file restores the full system.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

STRICT = "strict"
DISABLED = "disabled"
MODES = (STRICT, DISABLED)
ENV_OVERRIDE = "L9_MERGE_AUTHORITY_MODE"
SWITCH_FILE = Path(__file__).resolve().parents[2] / "ops" / "config" / "merge-authority.json"


def mode(path: Path | None = None) -> str:
    override = os.environ.get(ENV_OVERRIDE, "").strip().lower()
    if override in MODES:
        return override
    try:
        payload = json.loads((path or SWITCH_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return STRICT
    if not isinstance(payload, dict):
        return STRICT
    value = str(payload.get("enforcement") or "").strip().lower()
    return value if value in MODES else STRICT


def disabled(path: Path | None = None) -> bool:
    return mode(path) == DISABLED
