#!/usr/bin/env python3
"""The Infisical machine identity this surface binds secrets with — no AWS.

Infisical project ``cursor-governance`` is the only agent secret plane. A
surface reaches it with ONE bootstrap secret: the Universal Auth client secret
of a machine identity dedicated to that surface. Nothing on this path touches
AWS (the former AWS Secrets Manager "login seed" is retired).

Where the identity comes from, in order:

1. The environment: ``L9_INFISICAL_CLIENT_ID`` (not a secret) and
   ``L9_INFISICAL_CLIENT_SECRET`` (the one bootstrap secret). Project,
   environment and host default to ``infisical-cursor-governance.yaml`` and may
   be overridden by ``L9_INFISICAL_PROJECT_ID`` / ``L9_INFISICAL_ENV`` /
   ``L9_INFISICAL_HOST``. This is how a hosted Claude Code session is provisioned
   (the variable is set once in the environment settings).
2. ``~/.infisical/l9-machine.json`` (mode 0600) on an operator workstation that
   already has one. Nothing writes it from the environment: a secret already in
   the process environment is not copied to disk.

Never prints secret values. Never writes ``os.environ``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from infisical_http import DEFAULT_HOST, universal_auth_login  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PROFILE = Path.home() / ".infisical" / "l9-machine.json"
INVENTORY = HERE / "infisical-cursor-governance.yaml"
DEFAULT_ENV = "prod"
REQUIRED = ("client_id", "client_secret", "project_id")

#: The one bootstrap secret, and its non-secret companion.
ENV_CLIENT_ID = "L9_INFISICAL_CLIENT_ID"
ENV_CLIENT_SECRET = "L9_INFISICAL_CLIENT_SECRET"
ENV_PROJECT_ID = "L9_INFISICAL_PROJECT_ID"
ENV_ENVIRONMENT = "L9_INFISICAL_ENV"
ENV_HOST = "L9_INFISICAL_HOST"

SOURCE_ENV = "env"
SOURCE_PROFILE = "profile"


def profile_path() -> Path:
    return PROFILE


def _status(msg: str) -> None:
    print(f"infisical_cli_login: {msg}")


def _inventory_project() -> dict[str, str]:
    if yaml is None:
        return {}
    try:
        raw = yaml.safe_load(INVENTORY.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}
    if not isinstance(raw, dict):
        return {}
    project = raw.get("project") if isinstance(raw.get("project"), dict) else {}
    return {
        "host": str(raw.get("host") or ""),
        "project_id": str(project.get("id") or ""),
        "environment": str(project.get("environment") or ""),
    }


def _flag(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def env_identity(env: Mapping[str, str] | None = None) -> dict[str, str] | None:
    """The machine identity carried by the environment, or None when incomplete."""
    source = os.environ if env is None else env
    client_id, client_secret = _flag(source, ENV_CLIENT_ID), _flag(source, ENV_CLIENT_SECRET)
    if not client_id or not client_secret:
        return None
    inventory = _inventory_project()
    identity = {
        "host": _flag(source, ENV_HOST) or inventory.get("host") or DEFAULT_HOST,
        "project_id": _flag(source, ENV_PROJECT_ID) or inventory.get("project_id", ""),
        "environment": _flag(source, ENV_ENVIRONMENT)
        or inventory.get("environment")
        or DEFAULT_ENV,
        "client_id": client_id,
        "client_secret": client_secret,
    }
    return identity if identity["project_id"] else None


def file_identity() -> dict[str, str] | None:
    """The operator workstation's profile file, or None."""
    path = profile_path()
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict) or not all(str(raw.get(k) or "").strip() for k in REQUIRED):
        return None
    return {
        "host": str(raw.get("host") or DEFAULT_HOST).strip() or DEFAULT_HOST,
        "project_id": str(raw["project_id"]).strip(),
        "environment": str(raw.get("environment") or DEFAULT_ENV).strip() or DEFAULT_ENV,
        "client_id": str(raw["client_id"]).strip(),
        "client_secret": str(raw["client_secret"]).strip(),
    }


def machine_identity(
    env: Mapping[str, str] | None = None,
) -> tuple[str, dict[str, str] | None]:
    """(source, identity): the environment first, then the workstation profile."""
    identity = env_identity(env)
    if identity is not None:
        return SOURCE_ENV, identity
    identity = file_identity()
    if identity is not None:
        return SOURCE_PROFILE, identity
    return "", None


def profile_present() -> bool:
    return machine_identity()[1] is not None


def ensure_machine_profile(env: Mapping[str, str] | None = None) -> str:
    """``env`` / ``present`` when the identity logs in; ``absent``; ``failed``.

    ``absent`` means no identity at all; ``failed`` means one Infisical refused
    (revoked, wrong secret) or could not be reached. Never prints values.
    """
    source, identity = machine_identity(env)
    if identity is None:
        return "absent"
    token = universal_auth_login(identity["host"], identity["client_id"], identity["client_secret"])
    if not token:
        return "failed"
    return "env" if source == SOURCE_ENV else "present"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="identity present? names only")
    args = parser.parse_args(argv)
    if args.check:
        source, identity = machine_identity()
        if identity is not None:
            _status(f"identity present source={source}")
            return 0
        _status(f"identity absent — set {ENV_CLIENT_ID} and {ENV_CLIENT_SECRET}")
        return 1
    state = ensure_machine_profile()
    if state in {"env", "present"}:
        _status(f"login ok project=cursor-governance source={state}")
        return 0
    if state == "absent":
        _status(f"identity absent — set {ENV_CLIENT_ID} and {ENV_CLIENT_SECRET}")
    else:
        _status("login failed (identity refused or Infisical unreachable)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
