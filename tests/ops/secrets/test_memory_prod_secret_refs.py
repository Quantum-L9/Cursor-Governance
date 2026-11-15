"""Memory prod secret names are inventoried and stay outside the bind gate."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"

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


def _allowed_names() -> frozenset[str]:
    spec = importlib.util.spec_from_file_location(
        "capability_bind", SECRETS_DIR / "capability_bind.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.allowed_names()


def test_five_prod_names_are_registered_outside_the_bind_gate() -> None:
    refs = _inventory()["memory_prod_secret_refs"]
    assert refs["project"]["slug"] == "l9-graphite-memory-4b-bv"
    assert refs["environment"] == "prod"
    assert refs["secret_path"] == "/"
    assert refs["added"] == list(ADDED)
    assert refs["already_present"] == ["L9_MEMORY_POSTGRES_DSN"]
    assert refs["absent_on_purpose"] == list(ABSENT)
    bindable = _allowed_names()
    for name in (*ADDED, "L9_MEMORY_POSTGRES_DSN", *ABSENT):
        assert name not in bindable
