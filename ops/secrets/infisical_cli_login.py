#!/usr/bin/env python3
"""The Infisical machine identity this surface binds secrets with.

Infisical project ``cursor-governance`` is the only agent secret plane. How a
surface obtains its machine identity DIVERGES BY PEER, by design:

* Claude Code (hosted, model-controlled): ONE bootstrap secret in the
  environment — no AWS anywhere on its path.
* Cursor / operator machines: unchanged — the existing
  ``~/.infisical/l9-machine.json``, seeded once from the AWS Secrets Manager
  login seed when absent. The AWS code is imported only at that moment.

Where the identity comes from, in order:

1. The environment: ``L9_INFISICAL_CLIENT_ID`` (not a secret) and
   ``L9_INFISICAL_CLIENT_SECRET`` (the one bootstrap secret). Project,
   environment and host default to ``infisical-cursor-governance.yaml`` and may
   be overridden by ``L9_INFISICAL_PROJECT_ID`` / ``L9_INFISICAL_ENV`` /
   ``L9_INFISICAL_HOST``. This is how a hosted Claude Code session is provisioned
   (the variable is set once in the environment settings).
2. ``~/.infisical/l9-machine.json`` (mode 0600) on a Cursor / operator
   machine. Nothing writes it from the environment: a secret already in the
   process environment is not copied to disk.
3. Cursor / operator only (``allow_aws_seed``): the AWS login seed, which
   writes that profile — exactly as before this module learned (1). Never
   attempted on a model-controlled surface.

Never prints secret values. Never writes ``os.environ``.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
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


def _write_profile(payload: dict[str, str]) -> None:
    dest = profile_path()
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    tmp.replace(dest)
    os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)


def _seed_from_aws() -> dict[str, str] | None:
    """Cursor / operator: the AWS Secrets Manager login seed (unchanged behaviour).

    Imported lazily so no model-controlled surface ever loads AWS code.
    """
    import login_registry  # noqa: PLC0415
    import resolve_secret as aws_secret  # noqa: PLC0415

    raw, error = aws_secret.fetch_secret_string(login_registry.AWS_SM_LOGIN_SECRET, "us-east-1")
    if error or not raw:
        _status(f"aws seed failed code={error or 'empty'}")
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        _status("aws seed failed code=NOT_JSON")
        return None
    if not isinstance(parsed, dict):
        _status("aws seed failed code=NOT_OBJECT")
        return None
    missing = [key for key in REQUIRED if not str(parsed.get(key) or "").strip()]
    if missing:
        _status("aws seed failed code=FIELD_MISSING fields=" + ",".join(missing))
        return None
    host = str(parsed.get("host") or DEFAULT_HOST).strip() or DEFAULT_HOST
    return {
        "schema": "1",
        "host": host,
        "project_id": str(parsed["project_id"]).strip(),
        "environment": str(parsed.get("env") or DEFAULT_ENV).strip() or DEFAULT_ENV,
        "client_id": str(parsed["client_id"]).strip(),
        "client_secret": str(parsed["client_secret"]).strip(),
    }


def ensure_machine_profile(
    env: Mapping[str, str] | None = None, *, allow_aws_seed: bool = False
) -> str:
    """The identity's state. Never prints values.

    ``env`` — the environment identity logged in (Claude); ``present`` — the
    profile file exists (Cursor / operator, unchanged: not re-verified here);
    ``seeded`` — the AWS seed wrote the profile and it logged in (Cursor /
    operator, only with ``allow_aws_seed``); ``absent`` — no identity and no
    seed attempted; ``failed`` — an identity Infisical refused, or a seed that
    failed.
    """
    source, identity = machine_identity(env)
    if source == SOURCE_PROFILE:
        return "present"
    if identity is not None:
        token = universal_auth_login(
            identity["host"], identity["client_id"], identity["client_secret"]
        )
        return "env" if token else "failed"
    if not allow_aws_seed:
        return "absent"
    seeded = _seed_from_aws()
    if seeded is None:
        return "failed"
    if not universal_auth_login(seeded["host"], seeded["client_id"], seeded["client_secret"]):
        return "failed"
    _write_profile(seeded)
    return "seeded"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="identity present? names only")
    args = parser.parse_args(argv)
    if args.check:
        source, identity = machine_identity()
        if identity is not None:
            # Literals only: nothing derived from the identity is printed.
            _status(
                "identity present source=env"
                if source == SOURCE_ENV
                else "identity present source=profile"
            )
            return 0
        _status(f"identity absent — set {ENV_CLIENT_ID} and {ENV_CLIENT_SECRET}")
        return 1
    state = ensure_machine_profile(allow_aws_seed=True)
    if state == "seeded":
        _status("login ok project=cursor-governance source=aws-chicken-egg")
        return 0
    if state == "env":
        _status("login ok project=cursor-governance source=env")
        return 0
    if state == "present":
        _status("login ok project=cursor-governance source=profile")
        return 0
    if state == "absent":
        _status(f"identity absent — set {ENV_CLIENT_ID} and {ENV_CLIENT_SECRET}")
    else:
        _status("login failed (identity refused or Infisical unreachable)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
