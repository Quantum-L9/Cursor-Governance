#!/usr/bin/env python3
"""In-process bind of an inventory secret — use, never export.

The capability broker is an abandoned experiment. This module is the local
replacement for GET fetchers and other in-process consumers: resolve one
already-inventoried env-var name, hold the bytes for the caller, and never put
them on stdout, stderr, ``os.environ``, a file, or a receipt.

Resolution order:

1. The name is already in the process environment (operator / CI import).
2. ``~/.infisical/l9-machine.json`` via the Infisical HTTP client
   (``port_aws_to_infisical.infisical_req``). The Infisical CLI keyring
   session is disconnected — it has no login on this surface.

AWS Secrets Manager is **not** a bind path. ``source=aws`` is a fault.
Only names listed in ``infisical-cursor-governance.yaml`` ``root_env_keys``
(plus the documented aliases ``GH_TOKEN`` / ``SONARCLOUD_TOKEN``) are accepted.
``INFISICAL_CLIENT_SECRET`` is refused even if asked.

Usage:
  capability_bind.py --check SEMGREP_APP_TOKEN   # names + source only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

INVENTORY = HERE / "infisical-cursor-governance.yaml"
HTTP_RETRIES = 2

#: Names that must never be bound, even if they appear in an inventory edit.
REFUSED_NAMES = frozenset(
    {
        "INFISICAL_CLIENT_SECRET",
        "INFISICAL_TOKEN",
        "INFISICAL_PASSWORD",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    }
)

SOURCE_ENV = "env"
SOURCE_INFISICAL = "infisical"
SOURCE_INFISICAL_ABSENT = "infisical-machine-absent"
SOURCE_UNBOUND = "unbound"
SOURCE_REFUSED = "refused"
SOURCE_AWS = "aws"  # never produced; leftover is a fault in the reporter

_VALUES: dict[str, str] = {}
_SOURCES: dict[str, str] = {}
_PROFILE: dict[str, str] | None = None
_PROFILE_LOADED = False
_UA_TOKEN: str | None = None

InfisicalFn = Callable[[str], str | None]


def _inventory() -> dict:
    if yaml is None:
        return {}
    raw = yaml.safe_load(INVENTORY.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


def allowed_names() -> frozenset[str]:
    inv = _inventory()
    keys = {str(name) for name in (inv.get("root_env_keys") or []) if name}
    keys.update({"GH_TOKEN", "SONARCLOUD_TOKEN"})
    return frozenset(keys)


def reset_cache() -> None:
    """Test hook. Never call from a fetcher to 'retry' a miss with a paste."""
    global _PROFILE, _PROFILE_LOADED, _UA_TOKEN
    _VALUES.clear()
    _SOURCES.clear()
    _PROFILE = None
    _PROFILE_LOADED = False
    _UA_TOKEN = None


def _accepted_secret(name: str, value: str) -> bool:
    if not value or "\n" in value:
        return False
    lowered = value.lower()
    if lowered in {"null", "none", "undefined"}:
        return False
    if name in value and ("secret" in lowered or "infisical" in lowered):
        return False
    return True


def _machine_profile() -> dict[str, str] | None:
    """Load the SessionStart machine profile. Never logs values."""
    global _PROFILE, _PROFILE_LOADED
    if _PROFILE_LOADED:
        return _PROFILE
    _PROFILE_LOADED = True
    import infisical_cli_login as machine_login

    path = machine_login.profile_path()
    if not path.is_file():
        _PROFILE = None
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _PROFILE = None
        return None
    if not isinstance(raw, dict):
        _PROFILE = None
        return None
    if not all(str(raw.get(key) or "").strip() for key in machine_login.REQUIRED):
        _PROFILE = None
        return None
    _PROFILE = {
        "host": str(raw.get("host") or machine_login.DEFAULT_HOST).strip()
        or machine_login.DEFAULT_HOST,
        "project_id": str(raw["project_id"]).strip(),
        "environment": str(raw.get("environment") or machine_login.DEFAULT_ENV).strip()
        or machine_login.DEFAULT_ENV,
        "client_id": str(raw["client_id"]).strip(),
        "client_secret": str(raw["client_secret"]).strip(),
    }
    return _PROFILE


def _ua_token(profile: dict[str, str]) -> str | None:
    global _UA_TOKEN
    if _UA_TOKEN:
        return _UA_TOKEN
    from port_aws_to_infisical import infisical_req

    status, payload = infisical_req(
        profile["host"],
        "POST",
        "/api/v1/auth/universal-auth/login",
        body={"clientId": profile["client_id"], "clientSecret": profile["client_secret"]},
        retries=HTTP_RETRIES,
    )
    token = str((payload or {}).get("accessToken") or "").strip()
    if status != 200 or not token:
        return None
    _UA_TOKEN = token
    return _UA_TOKEN


def _secret_from_payload(payload: dict, name: str) -> str | None:
    secret = payload.get("secret")
    if isinstance(secret, dict) and str(secret.get("secretKey") or "") == name:
        value = str(secret.get("secretValue") or "").strip()
        return value or None
    for item in payload.get("secrets") or []:
        if isinstance(item, dict) and str(item.get("secretKey") or "") == name:
            value = str(item.get("secretValue") or "").strip()
            return value or None
    return None


def _from_machine_profile(name: str) -> str | None:
    """One secret via l9-machine.json + Infisical HTTP. CLI keyring is unused."""
    profile = _machine_profile()
    if profile is None:
        return None
    token = _ua_token(profile)
    if not token:
        return None
    from port_aws_to_infisical import infisical_req

    query = urllib.parse.urlencode(
        {
            "workspaceId": profile["project_id"],
            "environment": profile["environment"],
            "secretPath": "/",
            "viewSecretValue": "true",
            "include_imports": "false",
            "recursive": "false",
        }
    )
    path = f"/api/v3/secrets/raw/{urllib.parse.quote(name, safe='')}?{query}"
    status, payload = infisical_req(
        profile["host"],
        "GET",
        path,
        token,
        retries=HTTP_RETRIES,
    )
    raw_value = _secret_from_payload(payload if isinstance(payload, dict) else {}, name)
    if status != 200 or not raw_value or not _accepted_secret(name, raw_value):
        return None
    return raw_value


def _resolve(
    name: str,
    *,
    infisical_cli: InfisicalFn | None = None,
) -> tuple[str, str | None]:
    if name in REFUSED_NAMES:
        source, value = SOURCE_REFUSED, None
    elif name not in allowed_names():
        source, value = SOURCE_UNBOUND, None
    else:
        present = (os.environ.get(name) or "").strip()
        if present:
            source, value = SOURCE_ENV, present
        elif infisical_cli is None and _machine_profile() is None:
            source, value = SOURCE_INFISICAL_ABSENT, None
        else:
            fetch = infisical_cli or _from_machine_profile
            resolved = fetch(name)
            source, value = (
                (SOURCE_INFISICAL, resolved) if resolved else (SOURCE_UNBOUND, None)
            )
    return source, value


def bind(
    name: str,
    *,
    infisical_cli: InfisicalFn | None = None,
) -> str | None:
    """Return the bound value, or None. Never prints. Never writes ``os.environ``."""
    if name in _VALUES:
        return _VALUES[name]
    source, value = _resolve(name, infisical_cli=infisical_cli)
    _SOURCES[name] = source
    if value:
        _VALUES[name] = value
        return value
    return None


def bind_first(
    *names: str,
    infisical_cli: InfisicalFn | None = None,
) -> str | None:
    """Bind the first name that resolves. Used by fetchers with alias env tuples."""
    for name in names:
        value = bind(name, infisical_cli=infisical_cli)
        if value:
            return value
    return None


def bind_status(name: str) -> dict[str, str | bool]:
    """Availability only. The value is never included."""
    if name not in _SOURCES:
        bind(name)
    source = _SOURCES.get(name, SOURCE_UNBOUND)
    bound = source in {SOURCE_ENV, SOURCE_INFISICAL}
    return {"name": name, "bound": bound, "source": source}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bind an inventory secret in-process (never print it)."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        required=True,
        help="report bound/source; never values",
    )
    parser.add_argument("names", nargs="+", help="inventory env-var names")
    args = parser.parse_args(argv)

    exit_code = 0
    for name in args.names:
        status = bind_status(name)
        label = "bound" if status["bound"] else status["source"]
        print(f"{status['name']}: {label} source={status['source']}")
        if not status["bound"]:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
