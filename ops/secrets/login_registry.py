#!/usr/bin/env python3
"""Cursor-Governance Infisical login registry — inventory names only.

The committed registry file must not contain the historical AWS object name.
This module is the only map from the inventory id to that AWS Secrets Manager
object. App keys are Infisical names via ``capability_bind``.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REGISTRY_FILENAME = "infisical-login.registry.yaml"
DEFAULT_REGISTRY = HERE / REGISTRY_FILENAME

NAMESPACE = "cursor-governance"
INVENTORY_LOGIN_SECRET = "cursor-governance/infisical-login"
# Historical AWS SM object. Not written to the registry file.
AWS_SM_LOGIN_SECRET = "openclaw-igorbot/infisical-cursor-governance"
AWS_SM_PREFIX = "openclaw-igorbot/"
AWS_SM_ALLOWLIST = frozenset({AWS_SM_LOGIN_SECRET})
INVENTORY_ALLOWLIST = frozenset({INVENTORY_LOGIN_SECRET})


def to_inventory_id(secret_id: str) -> str:
    if secret_id == AWS_SM_LOGIN_SECRET:
        return INVENTORY_LOGIN_SECRET
    return secret_id


def to_aws_sm_id(secret_id: str) -> str:
    if secret_id == INVENTORY_LOGIN_SECRET:
        return AWS_SM_LOGIN_SECRET
    return secret_id


def is_login_secret(secret_id: str) -> bool:
    return secret_id in {INVENTORY_LOGIN_SECRET, AWS_SM_LOGIN_SECRET}
