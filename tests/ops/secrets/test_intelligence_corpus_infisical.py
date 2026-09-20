"""Intelligence corpus HMAC keys are Infisical-native, not an AWS overlay."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import capability_bind as cb  # noqa: E402

HMAC_NAMES = ("L9_INTELLIGENCE_PATH_KEY", "L9_INTELLIGENCE_PSEUDONYM_KEY")
OVERLAY_ID = "openclaw-igorbot/l9-intelligence-corpus"


def test_hmac_names_are_inventoried_for_infisical_bind() -> None:
    allowed = cb.allowed_names()
    for name in HMAC_NAMES:
        assert name in allowed


def test_hmac_pair_is_not_an_aws_overlay() -> None:
    overlay = yaml.safe_load((SECRETS_DIR / "registry.overlays.yaml").read_text(encoding="utf-8"))
    ids = {str(entry.get("secret_id") or "") for entry in (overlay or {}).get("overlays") or []}
    assert OVERLAY_ID not in ids


def test_inventory_note_does_not_wait_on_aws_sm() -> None:
    inv = yaml.safe_load(
        (SECRETS_DIR / "infisical-cursor-governance.yaml").read_text(encoding="utf-8")
    )
    notes = "\n".join(str(n) for n in (inv or {}).get("notes") or [])
    assert "L9_INTELLIGENCE_PATH_KEY" in notes
    assert "stays unprovisioned" not in notes
    assert "resolve_secret.py --check" not in notes
    assert "Infisical-native" in notes
    assert "at least 32 bytes" in notes
    assert "MUST differ" in notes
    assert "stable across producers" in notes
    keys = {str(name) for name in (inv or {}).get("root_env_keys") or []}
    assert set(HMAC_NAMES) <= keys
