#!/usr/bin/env python3
"""Resolve registered secrets from the Infisical project (read side).

Companion to ``port_aws_to_infisical.py``, which owns the AWS -> Infisical write
direction. This module adds the read direction that consumers need, and reuses
that script's HTTP client and Universal Auth login rather than reimplementing
them — there is one Infisical client in this repository.

Surface-agnostic on purpose: any consumer (Cursor, Claude Code cloud, CI, a
laptop) hydrates the same way. Do not add a surface-specific copy of this.

Bootstrap credentials, in precedence order:

1. ``INFISICAL_CLIENT_ID`` / ``INFISICAL_CLIENT_SECRET`` from the environment —
   the path used where AWS credentials are unavailable, e.g. the Claude Code
   cloud sandbox. Names come from ``infisical-cursor-governance.yaml``.
2. The AWS bootstrap ref ``openclaw-igorbot/infisical-cursor-governance`` when
   the AWS CLI is configured (the chicken-egg path documented in README.md).

Secret VALUES are never logged, never printed by ``--check``, and never written
to a receipt. ``--check`` asks Infisical for names only
(``viewSecretValue=false``), so a check run cannot leak a value even in a trace.

Usage:
  hydrate_infisical.py --check
  hydrate_infisical.py --check --require SONAR_TOKEN,SEMGREP_APP_TOKEN
  eval "$(hydrate_infisical.py --export SONAR_TOKEN,SEMGREP_APP_TOKEN)"

Exit 0 when every required name is available, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess  # noqa: S404 - fixed argv, no shell
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Single Infisical client for the repository — imported, never copied.
from port_aws_to_infisical import (  # noqa: E402
    DEFAULT_ENV,
    DEFAULT_PROJECT_ID,
    infisical_req,
    login,
)

BOOTSTRAP_AWS_REF = "openclaw-igorbot/infisical-cursor-governance"
DEFAULT_HOST = "https://app.infisical.com"
DEFAULT_SECRET_PATH = "/"


def _err(msg: str) -> None:
    print(f"hydrate_infisical: {msg}", file=sys.stderr)


def _aws_bootstrap() -> dict[str, str] | None:
    """Fetch Universal Auth credentials from AWS when the CLI is configured."""
    try:
        proc = subprocess.run(  # noqa: S603
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                BOOTSTRAP_AWS_REF,
                "--query",
                "SecretString",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        payload = json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def bootstrap_config() -> dict[str, str] | None:
    """Resolve Infisical connection settings. Never returns secret payloads."""
    client_id = os.environ.get("INFISICAL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("INFISICAL_CLIENT_SECRET", "").strip()
    host = os.environ.get("INFISICAL_SITE_URL", "").strip() or DEFAULT_HOST
    project = os.environ.get("INFISICAL_PROJECT_ID", "").strip() or DEFAULT_PROJECT_ID
    environment = os.environ.get("INFISICAL_ENV", "").strip() or DEFAULT_ENV
    secret_path = os.environ.get("INFISICAL_SECRET_PATH", "").strip() or DEFAULT_SECRET_PATH

    if not (client_id and client_secret):
        aws = _aws_bootstrap()
        if not aws:
            return None
        client_id = str(aws.get("client_id", ""))
        client_secret = str(aws.get("client_secret", ""))
        host = str(aws.get("host", host)).rstrip("/")
        project = str(aws.get("project_id", project))
        if not (client_id and client_secret):
            return None

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "host": host.rstrip("/"),
        "project_id": project,
        "environment": environment,
        "secret_path": secret_path,
    }


def _fetch(cfg: dict[str, str], *, with_values: bool) -> dict[str, str]:
    token = login(cfg["host"], cfg["client_id"], cfg["client_secret"])
    query = urllib.parse.urlencode(
        {
            "workspaceId": cfg["project_id"],
            "environment": cfg["environment"],
            "secretPath": cfg["secret_path"],
            "viewSecretValue": "true" if with_values else "false",
            "include_imports": "false",
            "recursive": "false",
        }
    )
    status, payload = infisical_req(cfg["host"], "GET", f"/api/v3/secrets/raw?{query}", token)
    if status != 200:
        raise RuntimeError(f"Infisical read failed (HTTP {status})")
    out: dict[str, str] = {}
    for secret in payload.get("secrets") or []:
        key = secret.get("secretKey") or ""
        if key:
            out[key] = secret.get("secretValue") or "" if with_values else ""
    return out


def _split(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _provider_unavailable(required: list[str]) -> int:
    _err(
        "no Infisical bootstrap credentials "
        "(set INFISICAL_CLIENT_ID / INFISICAL_CLIENT_SECRET, or configure the AWS CLI)"
    )
    for name in required:
        print(f"{name}: PROVIDER_UNAVAILABLE")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve secrets from Infisical (read side).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report availability; never values")
    mode.add_argument("--export", dest="export", help="comma-separated names to emit as exports")
    parser.add_argument("--require", help="comma-separated names that must be available")
    args = parser.parse_args(argv)

    required = _split(args.require) or _split(args.export)
    cfg = bootstrap_config()
    if cfg is None:
        return _provider_unavailable(required)

    try:
        available = _fetch(cfg, with_values=bool(args.export))
    except (RuntimeError, OSError, SystemExit) as exc:
        _err(f"provider error: {exc}")
        for name in required:
            print(f"{name}: PROVIDER_ERROR")
        return 1

    if args.check:
        # Names only. `available` was fetched with viewSecretValue=false.
        names = sorted(available)
        print(f"provider: infisical {cfg['host']} env={cfg['environment']} keys={len(names)}")
        if not required:
            for name in names:
                print(f"{name}: available")
            return 0
        missing = [name for name in required if name not in available]
        for name in required:
            print(f"{name}: {'available' if name in available else 'MISSING'}")
        return 1 if missing else 0

    missing = [name for name in required if not available.get(name)]
    if missing:
        _err(f"missing from provider: {', '.join(missing)}")
        return 1
    for name in required:
        # Values reach stdout only, for `eval`. Never logged.
        print(f"export {name}={shlex.quote(available[name])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
