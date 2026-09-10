#!/usr/bin/env python3
"""AWS CLI present and authorized — library of the SessionStart secrets owner.

Infisical login seeds from one AWS Secrets Manager object. If this probe
fails, the secrets plane cannot start. Never prints secret values. Never
prints account ids or ARNs. Not a Makefile target.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any

TIMEOUT_SECONDS = 8
OK = "OK"
AWS_CLI_NOT_FOUND = "AWS_CLI_NOT_FOUND"
AWS_NOT_AUTHORIZED = "AWS_NOT_AUTHORIZED"
TIMEOUT = "TIMEOUT"

REPAIR = "install AWS CLI v2 and authorize this machine; `aws sts get-caller-identity` must exit 0"


def _fail(code: str) -> dict[str, Any]:
    return {
        "ok": False,
        "code": code,
        "summary": f"{code} — secrets plane cannot start. Repair: {REPAIR}",
    }


def probe(*, runner: Any = subprocess.run) -> dict[str, Any]:
    if shutil.which("aws") is None:
        return _fail(AWS_CLI_NOT_FOUND)
    try:
        proc = runner(
            ["aws", "sts", "get-caller-identity", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _fail(TIMEOUT)
    except FileNotFoundError:
        return _fail(AWS_CLI_NOT_FOUND)
    if proc.returncode != 0:
        return _fail(AWS_NOT_AUTHORIZED)
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return _fail(AWS_NOT_AUTHORIZED)
    if not isinstance(payload, dict) or not payload.get("Account"):
        return _fail(AWS_NOT_AUTHORIZED)
    return {
        "ok": True,
        "code": OK,
        "summary": "authorized — Infisical login seed available",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = probe()
    if args.json:
        print(json.dumps({"ok": result["ok"], "code": result["code"]}))
    else:
        status = "OK" if result["ok"] else "FAILED"
        print(f"aws_cli_preflight: {status} {result['code']}")
        if not result["ok"]:
            print(
                "FAILED: secrets plane cannot start. "
                "Infisical bind depends on AWS CLI being installed and authorized. "
                f"Repair: {REPAIR}",
                file=sys.stderr,
            )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
