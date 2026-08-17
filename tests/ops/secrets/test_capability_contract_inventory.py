"""Inventory and adapter-doc contract tests (no broker/cryptography import)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
if str(SECRETS_DIR) not in sys.path:
    sys.path.insert(0, str(SECRETS_DIR))

import validate_capability_contract as vcc  # noqa: E402
from capability_registry import load_registry  # noqa: E402


def test_inventory_lists_every_capability_secret_ref() -> None:
    assert vcc.scan_inventory_refs(REPO_ROOT) == []


def test_adapter_examples_do_not_teach_aws_fallback() -> None:
    assert vcc.scan_aws_fallback_docs(REPO_ROOT) == []


def test_packages_capability_uses_github_token() -> None:
    registry = load_registry()
    spec = registry.get("github.packages_read")
    assert spec is not None
    assert spec.secret_refs == ("GITHUB_TOKEN",)
    assert spec.upstream_host == "npm.pkg.github.com"


def test_authed_npm_refuses_model_controlled_surface() -> None:
    result = subprocess.run(  # noqa: S603
        ["bash", str(SECRETS_DIR / "authed_npm.sh"), "npm", "--version"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
        env={**os.environ, "CURSOR_AGENT": "1", "L9_GOVERNANCE_SURFACE": "cursor"},
    )
    assert result.returncode != 0
    assert "PRIVATE_REGISTRY_UNREACHABLE" in result.stderr
    assert "npm_config_" not in result.stdout
