#!/usr/bin/env python3
"""In-process bind of an inventory secret — use, never export.

The capability broker is an abandoned experiment. This module is the local
replacement for GET fetchers and other in-process consumers: resolve one
already-inventoried env-var name, hold the bytes for the caller, and never put
them on stdout, stderr, ``os.environ``, a file, or a receipt.

Resolution order:

1. The name is already in the process environment (operator / CI import).
2. Infisical over HTTP (``infisical_http``) as this surface's machine identity
   (``infisical_cli_login.machine_identity``): ``L9_INFISICAL_CLIENT_ID`` +
   ``L9_INFISICAL_CLIENT_SECRET`` in the environment — the one bootstrap
   secret — or an operator's ``~/.infisical/l9-machine.json``.

AWS is not on this path at all. ``source=aws`` is a fault.
Only names listed in ``infisical-cursor-governance.yaml`` ``root_env_keys``
(plus the documented aliases ``GH_TOKEN`` / ``SONARCLOUD_TOKEN``) are accepted.
``INFISICAL_CLIENT_SECRET`` and the bootstrap ``L9_INFISICAL_CLIENT_SECRET`` are
refused even if asked: the identity is used, never handed out.

Usage:
  capability_bind.py --check SEMGREP_APP_TOKEN   # names + source only
"""

from __future__ import annotations

import argparse
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
        "L9_INFISICAL_CLIENT_SECRET",
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
    """This surface's machine identity (environment, then workstation file)."""
    global _PROFILE, _PROFILE_LOADED
    if _PROFILE_LOADED:
        return _PROFILE
    _PROFILE_LOADED = True
    import infisical_cli_login as machine_login

    _PROFILE = machine_login.machine_identity()[1]
    return _PROFILE


def _ua_token(profile: dict[str, str]) -> str | None:
    global _UA_TOKEN
    if _UA_TOKEN:
        return _UA_TOKEN
    from infisical_http import universal_auth_login

    token = universal_auth_login(
        profile["host"], profile["client_id"], profile["client_secret"], retries=HTTP_RETRIES
    )
    if not token:
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
    """One secret as this surface's machine identity, over Infisical HTTP."""
    profile = _machine_profile()
    if profile is None:
        return None
    token = _ua_token(profile)
    if not token:
        return None
    from infisical_http import infisical_req

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
            source, value = (SOURCE_INFISICAL, resolved) if resolved else (SOURCE_UNBOUND, None)
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
