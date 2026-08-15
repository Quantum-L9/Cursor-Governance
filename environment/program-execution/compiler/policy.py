"""Autonomy policy profile loading and narrowing (contract §7, ADR-0009)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

POLICIES_DIR = Path(__file__).resolve().parent / "policies"
SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "autonomy-policy.schema.json"

DEFAULT_PROFILE = "quantum-l9.safe-autonomy.v1"

CEILING_KEYS = (
    "inspect",
    "local_write",
    "commit",
    "push",
    "pull_request",
    "merge",
    "publish_or_release",
    "deploy_or_migrate",
    "destructive_change",
    "external_message",
)


def load_policy(profile_id: str) -> dict[str, Any]:
    path = POLICIES_DIR / f"{profile_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"unknown policy profile: {profile_id}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    _validate(data)
    return data


def _validate(data: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        )
        raise ValueError(f"policy profile violates program-execution.autonomy-policy.v1: {details}")


def narrowed_ceiling(policy: dict[str, Any], constraints: dict[str, Any] | None) -> dict[str, bool]:
    """Merge optional user constraints onto the profile ceiling.

    User constraints may only narrow (true -> false). A constraint that would
    widen any action raises ValueError and becomes an authority-bearing
    escalation, never a silent widening.
    """
    ceiling = dict(policy["authorization_ceiling"])
    requested = (constraints or {}).get("permission_ceiling") or {}
    for key, value in requested.items():
        if key not in CEILING_KEYS:
            raise ValueError(f"unknown ceiling action: {key}")
        if not isinstance(value, bool):
            raise ValueError(f"ceiling action {key} must be boolean")
        if value and not ceiling[key]:
            raise ValueError(f"constraint would widen {key} beyond the active policy profile")
        ceiling[key] = value
    return ceiling


__all__ = [
    "CEILING_KEYS",
    "DEFAULT_PROFILE",
    "load_policy",
    "narrowed_ceiling",
]
