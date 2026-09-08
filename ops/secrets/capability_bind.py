#!/usr/bin/env python3
"""In-process bind of an inventory secret — use, never export.

The capability broker is an abandoned experiment. This module is the local
replacement for GET fetchers and other in-process consumers: resolve one
already-inventoried env-var name, hold the bytes for the caller, and never put
them on stdout, stderr, ``os.environ``, a file, or a receipt.

Resolution order:

1. The name is already in the process environment (operator / CI import).
2. Infisical CLI user profile (OS keyring login — no Universal Auth in env).
3. AWS Secrets Manager via the mapped ``openclaw-igorbot/<suffix>#<key>`` ref.

Only names listed in ``infisical-cursor-governance.yaml`` ``root_env_keys``
(plus the documented aliases ``GH_TOKEN`` / ``SONARCLOUD_TOKEN``) are accepted.
``INFISICAL_CLIENT_SECRET`` is refused even if asked. This is not a generic
``get_secret`` API and is not the retired broker.

Usage:
  capability_bind.py --check SEMGREP_APP_TOKEN   # names + source only
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import resolve_secret as aws_secret  # noqa: E402
from port_aws_to_infisical import ENV_MAP  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

INVENTORY = HERE / "infisical-cursor-governance.yaml"
CLI_TIMEOUT_SECONDS = 12
AWS_PREFIX = "openclaw-igorbot/"

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

#: CLI env keys that override a logged-in Infisical user profile. Strip them
#: from the child so the OS-keyring session is what runs (Context7: Infisical
#: CLI falls back to the local login when no token is attached).
_CLI_OVERRIDE_KEYS = (
    "INFISICAL_TOKEN",
    "INFISICAL_CLIENT_ID",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_UNIVERSAL_AUTH_CLIENT_ID",
    "INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET",
)

SOURCE_ENV = "env"
SOURCE_INFISICAL = "infisical-cli"
SOURCE_AWS = "aws"
SOURCE_UNBOUND = "unbound"
SOURCE_REFUSED = "refused"

_VALUES: dict[str, str] = {}
_SOURCES: dict[str, str] = {}

InfisicalFn = Callable[[str], str | None]
AwsFn = Callable[[str], str | None]


def _aws_refs() -> dict[str, str]:
    refs = {mapped: f"{AWS_PREFIX}{suffix}#{key}" for (suffix, key), mapped in ENV_MAP.items()}
    refs["GH_TOKEN"] = f"{AWS_PREFIX}github#token"
    refs["SONARCLOUD_TOKEN"] = f"{AWS_PREFIX}sonarcloud#token"
    return refs


def _inventory() -> dict:
    if yaml is None:
        return {}
    raw = yaml.safe_load(INVENTORY.read_text(encoding="utf-8")) or {}
    return raw if isinstance(raw, dict) else {}


def allowed_names() -> frozenset[str]:
    inv = _inventory()
    keys = {str(name) for name in (inv.get("root_env_keys") or []) if name}
    keys.update({"GH_TOKEN", "SONARCLOUD_TOKEN"})
    if yaml is None:
        keys.update(str(mapped) for mapped in ENV_MAP.values() if mapped)
    return frozenset(keys)


def reset_cache() -> None:
    """Test hook. Never call from a fetcher to 'retry' a miss with a paste."""
    _VALUES.clear()
    _SOURCES.clear()


def _cli_child_env() -> dict[str, str]:
    child = {key: value for key, value in os.environ.items() if value}
    for key in _CLI_OVERRIDE_KEYS:
        child.pop(key, None)
    return child


def _from_infisical_cli(name: str) -> str | None:
    """One secret via the logged-in Infisical CLI profile. Never logs stdout."""
    inv = _inventory()
    project = inv.get("project") or {}
    project_id = str(project.get("id") or "").strip()
    environment = str(project.get("environment") or "prod").strip() or "prod"
    if not project_id:
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            [
                "infisical",
                "secrets",
                "get",
                name,
                "--env",
                environment,
                "--projectId",
                project_id,
                "--path",
                "/",
                "--plain",
                "--silent",
            ],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SECONDS,
            env=_cli_child_env(),
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    value = (proc.stdout or "").rstrip("\n")
    if not value:
        return None
    if "\n" in value and "-----BEGIN" not in value:
        return None
    lowered = value.lower()
    if lowered in {"null", "none", "undefined"}:
        return None
    # A table / help dump is not a secret value.
    if name in value and ("secret" in lowered or "infisical" in lowered):
        return None
    return value


def _from_aws(name: str) -> str | None:
    ref = _aws_refs().get(name)
    if not ref:
        return None
    try:
        registry = aws_secret.load_registry(aws_secret.DEFAULT_REGISTRY)
    except SystemExit:
        return None
    secret_id, field = aws_secret.split_id(ref)
    entry = aws_secret.entry_for(registry, secret_id)
    if entry is not None and entry.get("provisioned") is False:
        return None
    region = (
        (entry or {}).get("region")
        or os.environ.get("AWS_REGION")
        or registry.get("region_default")
        or aws_secret.AWS_REGION_DEFAULT
    )
    raw, error = aws_secret.fetch_secret_string(str(secret_id), str(region))
    if error or not raw:
        return None
    if field is None:
        return raw.strip() or None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or field not in parsed:
        return None
    value = str(parsed[field]).strip()
    return value or None


def _resolve(
    name: str,
    *,
    infisical_cli: InfisicalFn | None = None,
    aws: AwsFn | None = None,
) -> tuple[str, str | None]:
    if name in REFUSED_NAMES:
        return SOURCE_REFUSED, None
    if name not in allowed_names():
        return SOURCE_UNBOUND, None
    present = (os.environ.get(name) or "").strip()
    if present:
        return SOURCE_ENV, present
    cli = infisical_cli or _from_infisical_cli
    value = cli(name)
    if value:
        return SOURCE_INFISICAL, value
    aws_fn = aws or _from_aws
    value = aws_fn(name)
    if value:
        return SOURCE_AWS, value
    return SOURCE_UNBOUND, None


def bind(
    name: str,
    *,
    infisical_cli: InfisicalFn | None = None,
    aws: AwsFn | None = None,
) -> str | None:
    """Return the bound value, or None. Never prints. Never writes ``os.environ``."""
    if name in _VALUES:
        return _VALUES[name]
    source, value = _resolve(name, infisical_cli=infisical_cli, aws=aws)
    _SOURCES[name] = source
    if value:
        _VALUES[name] = value
        return value
    return None


def bind_first(
    *names: str,
    infisical_cli: InfisicalFn | None = None,
    aws: AwsFn | None = None,
) -> str | None:
    """Bind the first name that resolves. Used by fetchers with alias env tuples."""
    for name in names:
        value = bind(name, infisical_cli=infisical_cli, aws=aws)
        if value:
            return value
    return None


def bind_status(name: str) -> dict[str, str | bool]:
    """Availability only. The value is never included."""
    bind(name)
    source = _SOURCES.get(name, SOURCE_UNBOUND)
    bound = source in {SOURCE_ENV, SOURCE_INFISICAL, SOURCE_AWS}
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
