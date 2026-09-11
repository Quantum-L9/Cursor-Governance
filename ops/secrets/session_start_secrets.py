#!/usr/bin/env python3
"""SessionStart secrets plane — one owner, fail loud.

SessionStart binds Infisical. AWS CLI must be installed and authorized so the
one login secret can seed the machine profile. If that preflight fails, the
downstream secrets plane cannot start.

This is not a Makefile ceremony. Values are never printed or exported.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SECRETS = Path(__file__).resolve().parent
if str(_SECRETS) not in sys.path:
    sys.path.insert(0, str(_SECRETS))

import aws_cli_preflight as aws_preflight  # noqa: E402
import capability_bind as cb  # noqa: E402
import infisical_cli_login as login  # noqa: E402

BIND_NAMES = ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "GITHUB_TOKEN")


def run_plane() -> dict[str, Any]:
    aws = aws_preflight.probe()
    login_state = "skipped"
    if aws.get("ok"):
        login_state = login.ensure_machine_profile()
    binds: list[dict[str, Any]] = []
    for name in BIND_NAMES:
        status = cb.bind_status(name)
        binds.append(
            {
                "name": str(status.get("name") or name),
                "bound": bool(status.get("bound")),
                "source": str(status.get("source") or "unbound"),
            }
        )
    return {
        "aws": {
            "ok": bool(aws.get("ok")),
            "code": str(aws.get("code") or ""),
            "summary": str(aws.get("summary") or ""),
        },
        "login": login_state,
        "binds": binds,
        "plane_ok": bool(aws.get("ok")) and login_state != "failed",
    }


def receipt_payload(result: dict[str, Any]) -> dict[str, Any]:
    aws = result.get("aws") if isinstance(result.get("aws"), dict) else {}
    binds = result.get("binds") if isinstance(result.get("binds"), list) else []
    return {
        "ok": bool(result.get("plane_ok")),
        "login": result.get("login"),
        "aws": {
            "ok": bool(aws.get("ok")),
            "code": str(aws.get("code") or ""),
            "summary": str(aws.get("summary") or ""),
        },
        "binds": binds,
    }


def write_receipt(path: Path, result: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt_payload(result), sort_keys=True) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--receipt-out",
        default="",
        help="Write the receipt JSON to this path. Omit to write no file.",
    )
    args = parser.parse_args(argv)
    result = run_plane()
    payload = receipt_payload(result)
    if args.receipt_out:
        write_receipt(Path(args.receipt_out), result)
    if args.json:
        print(json.dumps(payload))
    if not result["plane_ok"]:
        if not result["aws"]["ok"]:
            print(
                "FAILED: AWS CLI is missing or not authorized. "
                "Infisical bind cannot start. Repair: install AWS CLI v2 && "
                "aws sts get-caller-identity",
                file=sys.stderr,
            )
        else:
            print(
                f"FAILED: Infisical machine profile {result['login']}. "
                "SessionStart cannot bind inventoried secrets.",
                file=sys.stderr,
            )
        return 1
    print(
        f"session_start_secrets: ok login={result['login']} "
        + " ".join(f"{b['name']}={b['source']}" for b in result["binds"]),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
