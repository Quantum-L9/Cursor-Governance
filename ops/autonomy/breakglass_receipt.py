#!/usr/bin/env python3
"""Scoped, expiring publish-path breakglass receipt.

A standing ``L9_PUBLISH_PATH_OVERRIDE=<reason>`` environment string is inert.
Only a receipt with issuer, scope, reason, issued_at, and expires_at can
restore prior override behaviour, and only while it is unexpired.

Usage:
  python3 ops/autonomy/breakglass_receipt.py --status
  python3 ops/autonomy/breakglass_receipt.py --write --issuer ops --reason incident-1234 --hours 2
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SCHEMA = "l9.publish-path-breakglass.v1"
SCOPE_PUBLISH_PATH = "publish_path"
OVERRIDE_ENV = "L9_PUBLISH_PATH_OVERRIDE"
RECEIPT_ENV = "L9_PUBLISH_PATH_RECEIPT"
DEFAULT_HOURS = 4


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _parse_ts(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def default_receipt_path() -> Path:
    override = (os.environ.get(RECEIPT_ENV) or "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".l9" / "autonomy" / "publish-path-override.json"


def load_receipt(path: Path | None = None) -> dict[str, Any] | None:
    target = path or default_receipt_path()
    if not target.is_file():
        return None
    try:
        parsed = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def evaluate(
    receipt: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Classify a receipt. Never raises."""
    moment = now or _utc_now()
    standing = (os.environ.get(OVERRIDE_ENV) or "").strip()
    base = {
        "in_force": False,
        "reason": "",
        "issuer": "",
        "scope": "",
        "age_seconds": 0,
        "expires_at": "",
        "standing_env_inert": bool(standing),
    }
    if receipt is None:
        if standing:
            base["status"] = "inert_env"
            base["detail"] = (
                f"{OVERRIDE_ENV} is set but inert without a valid breakglass receipt"
            )
        else:
            base["status"] = "none"
            base["detail"] = "no publish-path breakglass in force"
        return base

    if str(receipt.get("schema") or "") != SCHEMA:
        base["status"] = "invalid"
        base["detail"] = "receipt schema is not a publish-path breakglass"
        return base
    if str(receipt.get("scope") or "") != SCOPE_PUBLISH_PATH:
        base["status"] = "invalid"
        base["detail"] = f"receipt scope {receipt.get('scope')!r} is not {SCOPE_PUBLISH_PATH}"
        return base
    issuer = str(receipt.get("issuer") or "").strip()
    reason = str(receipt.get("reason") or "").strip()
    if issuer not in {"human", "ops"} or not reason:
        base["status"] = "invalid"
        base["detail"] = "receipt needs issuer=human|ops and a non-empty reason"
        return base

    issued = _parse_ts(str(receipt.get("issued_at") or ""))
    expires = _parse_ts(str(receipt.get("expires_at") or ""))
    if issued is None or expires is None:
        base["status"] = "invalid"
        base["detail"] = "receipt issued_at/expires_at are not parseable UTC timestamps"
        return base
    age = max(0, int((moment - issued).total_seconds()))
    base.update(
        {
            "issuer": issuer,
            "scope": SCOPE_PUBLISH_PATH,
            "reason": reason,
            "age_seconds": age,
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    if moment >= expires:
        base["status"] = "expired"
        base["detail"] = f"publish-path breakglass expired ({age}s after issue)"
        return base
    base["in_force"] = True
    base["status"] = "in_force"
    base["detail"] = (
        f"publish-path grant in force issuer={issuer} age={age}s expires={base['expires_at']}"
    )
    return base


def active_publish_path_reason(*, now: datetime | None = None) -> str:
    """Return the grant reason only when a valid unexpired receipt is in force."""
    verdict = evaluate(load_receipt(), now=now)
    return verdict["reason"] if verdict.get("in_force") else ""


def write_receipt(
    *,
    issuer: str,
    reason: str,
    hours: int = DEFAULT_HOURS,
    path: Path | None = None,
    now: datetime | None = None,
) -> Path:
    moment = now or _utc_now()
    expires = moment + timedelta(hours=max(1, hours))
    payload = {
        "schema": SCHEMA,
        "issuer": issuer,
        "scope": SCOPE_PUBLISH_PATH,
        "reason": reason,
        "issued_at": moment.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    target = path or default_receipt_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def status_line(*, now: datetime | None = None) -> str:
    verdict = evaluate(load_receipt(), now=now)
    return f"publish-path grant: {verdict['detail']}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--issuer", choices=("human", "ops"), default="ops")
    parser.add_argument("--reason", default="")
    parser.add_argument("--hours", type=int, default=DEFAULT_HOURS)
    parser.add_argument("--path", default="")
    args = parser.parse_args(argv)

    path = Path(args.path) if args.path else None
    if args.write:
        if not args.reason.strip():
            print("FAIL: --write requires --reason", file=sys.stderr)
            return 2
        written = write_receipt(
            issuer=args.issuer, reason=args.reason.strip(), hours=args.hours, path=path
        )
        print(f"wrote {written}")
        return 0

    verdict = evaluate(load_receipt(path))
    if args.json:
        print(json.dumps(verdict, indent=2, sort_keys=True))
    else:
        print(status_line())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
