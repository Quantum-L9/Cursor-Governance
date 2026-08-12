"""Ephemeral OpenAI key resolve for Phase B / distill (never long-lived on Mac).

Prefer process env ``OPENAI_API_KEY`` when already set (tests, GHA secrets).
Otherwise resolve AWS Secrets Manager ``l9/OPENAI_API_KEY`` once into memory
and return it — do not write to ``~/.cursor/graphiti.env``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

_SECRET_ID = "l9/OPENAI_API_KEY"
_DEFAULT_REGION = "us-east-1"

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def resolve_openai_api_key(
    *,
    region: str | None = None,
    runner: Any = None,
) -> tuple[str | None, str]:
    """Return (key_or_none, skip_reason). skip_reason empty on success."""
    existing = os.environ.get("OPENAI_API_KEY", "").strip()
    if existing:
        return existing, ""

    if os.environ.get("MEMORY_PHASE_B_RESOLVE_SM", "1").strip() in ("0", "false", "False"):
        return None, "OPENAI_API_KEY absent (SM resolve disabled)"

    try:
        from ops.secrets.resolve_secret import fetch_secret_string
    except ImportError:
        return None, "OPENAI_API_KEY absent (resolve_secret unavailable)"

    aws_region = (
        (region or "").strip()
        or os.environ.get("AWS_REGION", "").strip()
        or os.environ.get("AWS_DEFAULT_REGION", "").strip()
        or _DEFAULT_REGION
    )
    kwargs: dict[str, Any] = {}
    if runner is not None:
        kwargs["runner"] = runner
    value, err = fetch_secret_string(_SECRET_ID, aws_region, **kwargs)
    if err is not None:
        return None, f"OPENAI_API_KEY absent (SM {_SECRET_ID}: {err})"
    key = (value or "").strip()
    if not key:
        return None, f"OPENAI_API_KEY absent (SM {_SECRET_ID} empty)"
    # Ephemeral for this process only — not persisted to disk.
    os.environ["OPENAI_API_KEY"] = key
    return key, ""
