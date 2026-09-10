#!/usr/bin/env python3
"""One-time chicken-egg login: AWS UA → local Infisical machine profile.

Universal Auth ``infisical login --method=universal-auth`` does not persist a
keyring session. This script writes ``~/.infisical/l9-machine.json`` (mode 0600)
from the one allowed AWS login secret so ``capability_bind`` can use Infisical
without putting UA in the model environment.

Never prints secret values. Never writes ``os.environ``. Library of the
SessionStart secrets owner — not a Makefile target.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import login_registry  # noqa: E402
import resolve_secret as aws_secret  # noqa: E402
from port_aws_to_infisical import infisical_req  # noqa: E402

AWS_ID = login_registry.AWS_SM_LOGIN_SECRET
PROFILE = Path.home() / ".infisical" / "l9-machine.json"
DEFAULT_HOST = "https://app.infisical.com"
DEFAULT_ENV = "prod"
REQUIRED = ("client_id", "client_secret", "project_id")


def profile_path() -> Path:
    return PROFILE


def _status(msg: str) -> None:
    print(f"infisical_cli_login: {msg}")


def profile_present() -> bool:
    path = profile_path()
    if not path.is_file():
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(raw, dict):
        return False
    return all(str(raw.get(key) or "").strip() for key in REQUIRED)


def _write_profile(payload: dict[str, str]) -> None:
    dest = profile_path()
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    tmp.replace(dest)
    os.chmod(dest, stat.S_IRUSR | stat.S_IWUSR)


def _seed_from_aws() -> dict[str, str] | None:
    raw, error = aws_secret.fetch_secret_string(AWS_ID, "us-east-1")
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


def _verify_login(profile: dict[str, str]) -> bool:
    status, payload = infisical_req(
        profile["host"],
        "POST",
        "/api/v1/auth/universal-auth/login",
        body={"clientId": profile["client_id"], "clientSecret": profile["client_secret"]},
    )
    token = str((payload or {}).get("accessToken") or "").strip()
    if status != 200 or not token:
        _status(f"infisical login failed status={status}")
        return False
    return True


def ensure_machine_profile() -> str:
    """Return ``present``, ``seeded``, or ``failed``. Never prints values."""
    if profile_present():
        return "present"
    profile = _seed_from_aws()
    if profile is None:
        return "failed"
    if not _verify_login(profile):
        return "failed"
    _write_profile(profile)
    return "seeded"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="profile present? names only")
    args = parser.parse_args(argv)
    if args.check:
        if profile_present():
            _status("profile present")
            return 0
        _status("profile absent")
        return 1
    state = ensure_machine_profile()
    if state == "present":
        _status("profile present")
        return 0
    if state == "seeded":
        _status("login ok project=cursor-governance env=prod source=aws-chicken-egg")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
