#!/usr/bin/env python3
"""Resolve openclaw-igorbot AWS Secrets Manager refs.

ID format:
  secret_id#json_field  → JSON field from SecretString
  secret_id             → whole SecretString (plain or JSON text)

Never writes a resolved secret value to stderr or logs.
  --check   verify resolution; print OK/FAIL + ref only; exit 0/1
  --ref     single ref to resolve (required)
  default   print value to stdout only (for programmatic capture)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

AWS_REGION_DEFAULT = "us-east-1"
AWS_CALL_TIMEOUT_SECONDS = 6
HERE = Path(__file__).resolve().parent
DEFAULT_REGISTRY = HERE / "openclaw-igorbot.registry.yaml"


def _err(msg: str) -> None:
    print(f"resolve_secret: {msg}", file=sys.stderr)


def _safe_path(path: Path | str) -> Path:
    """Resolve a CLI/file path; require it stay under cwd or system temp (S8707)."""
    resolved = Path(path).expanduser().resolve()
    allowed = (Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve())
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    _err(f"path escapes allowed roots: {path}")
    raise SystemExit(2)


def split_id(ref_id: str) -> tuple[str, str | None]:
    if "#" in ref_id:
        secret_id, field = ref_id.split("#", 1)
        return secret_id, field or None
    return ref_id, None


def load_registry(path: Path) -> dict[str, Any]:
    if yaml is None:
        _err("PyYAML required")
        raise SystemExit(2)
    path = _safe_path(path)
    if not path.is_file():
        _err(f"registry not found: {path}")
        raise SystemExit(2)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict) or "secrets" not in data:
        _err(f"invalid registry: {path}")
        raise SystemExit(2)
    return data


def ref_registered(registry: dict[str, Any], ref_id: str) -> bool:
    secret_id, field = split_id(ref_id)
    for entry in registry.get("secrets") or []:
        if entry.get("secret_id") != secret_id:
            continue
        if not entry.get("enabled", False):
            return False
        if field is None:
            return True
        keys = {k.get("json_key") for k in (entry.get("keys") or [])}
        return field in keys
    return False


def entry_for(registry: dict[str, Any], secret_id: str) -> dict[str, Any] | None:
    for entry in registry.get("secrets") or []:
        if entry.get("secret_id") == secret_id:
            return entry
    return None


def fetch_secret_string(
    secret_id: str,
    region: str,
    *,
    runner: Any = subprocess.run,
) -> tuple[str | None, str | None]:
    """Returns (raw_secret_string, error_code). Never raises. Never logs values."""
    try:
        proc = runner(
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                secret_id,
                "--region",
                region,
                "--query",
                "SecretString",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=AWS_CALL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except FileNotFoundError:
        return None, "AWS_CLI_NOT_FOUND"

    if proc.returncode != 0:
        stderr = proc.stderr or ""
        if "ResourceNotFoundException" in stderr:
            return None, "NOT_FOUND"
        return None, "RESOLUTION_ERROR"

    value = (proc.stdout or "").strip()
    if not value or value == "None":
        return None, "NOT_FOUND"
    return value, None


def resolve_ref(
    ref_id: str,
    region: str,
    *,
    runner: Any = subprocess.run,
) -> tuple[str | None, str | None]:
    secret_id, field = split_id(ref_id)
    raw_value, fetch_error = fetch_secret_string(secret_id, region, runner=runner)
    if fetch_error is not None:
        return None, fetch_error
    assert raw_value is not None
    if field is None:
        return raw_value, None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return None, "NOT_JSON"
    if not isinstance(parsed, dict) or field not in parsed:
        return None, "FIELD_NOT_FOUND"
    return str(parsed[field]), None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="secret_id or secret_id#json_key")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify resolve without printing the secret value",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to openclaw-igorbot.registry.yaml",
    )
    parser.add_argument(
        "--allow-unregistered",
        action="store_true",
        help="Skip registry membership gate (default: fail-closed)",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region override (default: registry entry / AWS_REGION / us-east-1)",
    )
    args = parser.parse_args(argv)

    ref_id = args.ref.strip()
    if not ref_id:
        _err("empty --ref")
        return 2

    registry = load_registry(args.registry)
    if not args.allow_unregistered and not ref_registered(registry, ref_id):
        _err(f"FAIL ref={ref_id} code=UNREGISTERED")
        if args.check:
            print(f"FAIL ref={ref_id} code=UNREGISTERED")
        return 1

    secret_id, _field = split_id(ref_id)
    entry = entry_for(registry, secret_id)
    if entry is not None and entry.get("provisioned") is False:
        _err(f"FAIL ref={ref_id} code=NOT_PROVISIONED")
        if args.check:
            print(f"FAIL ref={ref_id} code=NOT_PROVISIONED")
        return 1

    region = (
        args.region
        or (entry or {}).get("region")
        or os.environ.get("AWS_REGION")
        or registry.get("region_default")
        or AWS_REGION_DEFAULT
    )

    value, error = resolve_ref(ref_id, region)
    if error is not None:
        _err(f"FAIL ref={ref_id} code={error}")
        if args.check:
            print(f"FAIL ref={ref_id} code={error}")
        return 1

    if args.check:
        # Value resolved successfully — never echo it.
        print(f"OK ref={ref_id}")
        return 0

    # Programmatic path: value on stdout only.
    sys.stdout.write(value or "")
    if value and not value.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
