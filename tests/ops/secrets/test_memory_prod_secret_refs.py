"""Memory prod secret names are inventoried and stay outside the bind gate."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import capability_bind as cb  # noqa: E402

ADDED = (
    "L9_MEMORY_LOCAL_ORGANIZATION_ID",
    "L9_MEMORY_LOCAL_TENANT_ID",
    "L9_MEMORY_LOCAL_WORKSPACE_ID",
    "L9_MEMORY_OAUTH_ACTORS_JSON",
    "L9_MEMORY_OAUTH_GRANTS_JSON",
)
ABSENT = ("L9_MEMORY_HTTP_AUTH_MODE", "L9_MEMORY_HTTP_OAUTH_ISSUER")


def _inventory() -> dict:
    loaded = yaml.safe_load(
        (SECRETS_DIR / "infisical-cursor-governance.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(loaded, dict)
    return loaded


def test_five_prod_names_are_registered_outside_the_bind_gate() -> None:
    refs = _inventory()["memory_prod_secret_refs"]
    assert refs["project"]["slug"] == "l9-graphite-memory-4b-bv"
    assert refs["environment"] == "prod"
    assert refs["secret_path"] == "/"
    assert refs["added"] == list(ADDED)
    assert refs["already_present"] == ["L9_MEMORY_POSTGRES_DSN"]
    assert refs["absent_on_purpose"] == list(ABSENT)
    bindable = cb.allowed_names()
    for name in (*ADDED, "L9_MEMORY_POSTGRES_DSN", *ABSENT):
        assert name not in bindable
