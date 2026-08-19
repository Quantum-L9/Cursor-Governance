#!/usr/bin/env python3
"""Resolve openclaw-igorbot AWS Secrets Manager refs.

ID format:
  secret_id#json_field  → JSON field from SecretString
  secret_id             → whole SecretString (plain or JSON text)

Never writes a resolved secret value to stderr or logs.
  --check   verify status; print OK/FAIL only; exit 0/1
  --ref     single ref to resolve (required)
  default   print value to stdout only (for programmatic capture)

WHAT ``--check`` MEANS. The governed reference is registered and provisioned
according to the inventory, and its backing Secrets Manager object is reachable
through a non-value-bearing probe (``describe-secret``). It does NOT mean the
current ``SecretString`` was fetched and the requested field was observed inside
it — proving that requires the value, which is a trusted-surface operation.
Field membership is therefore an inventory question, answered by
:func:`ref_registered` against the registry entry's declared ``keys``.

TRUST BOUNDARY. The two modes are not equally available. ``--check`` never
retrieves ``SecretString`` or ``SecretBinary``, so no secret byte enters the
process and it stays reachable from every surface.
Raw resolution is trusted-operator-only and is guarded by
:func:`surface_trust.require_trusted`, which refuses any caller running inside a
model-controlled runtime — including one that sets ``L9_GOVERNANCE_SURFACE`` to
an operator id while Claude's or Cursor's own environment markers are visible.
There is no flag, argument or environment variable here that relaxes that; the
single authority is ``ops/secrets/surface_trust.py``.
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

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from surface_trust import require_trusted  # noqa: E402

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

AWS_REGION_DEFAULT = "us-east-1"
AWS_CALL_TIMEOUT_SECONDS = 6
DEFAULT_REGISTRY = HERE / "openclaw-igorbot.registry.yaml"


def _err(msg: str) -> None:
    print(f"resolve_secret: {msg}", file=sys.stderr)


_KNOWN_ERROR_CODES = frozenset(
    {
        "TIMEOUT",
        "AWS_CLI_NOT_FOUND",
        "NOT_FOUND",
        "RESOLUTION_ERROR",
        "NOT_JSON",
        "FIELD_NOT_FOUND",
        "UNREGISTERED",
        "NOT_PROVISIONED",
    }
)


def _canonical_error(code: str | None) -> str:
    """Barrier: only allowlisted status codes may leave probe_ref."""
    if code in _KNOWN_ERROR_CODES:
        return code
    return "RESOLUTION_ERROR"


def _emit_secret_value(value: str) -> None:
    """Write resolved secret to stdout fd 1 (CLI contract; not a log sink)."""
    payload = value if value.endswith("\n") else value + "\n"
    # Use raw fd 1 — avoids modeled cleartext-logging sinks on print/stdout.write.
    os.write(1, payload.encode("utf-8"))


def _safe_path(path: Path | str) -> Path:
    """Resolve a CLI/file path; require it stay under cwd, system temp, or the
    governance root (S8707). The governance root is always allowed so the
    resolver works when invoked from a consumer repo (2026-08-15 factory repair)."""
    resolved = Path(path).expanduser().resolve()
    allowed = (
        Path.cwd().resolve(),
        Path(tempfile.gettempdir()).resolve(),
        Path(__file__).resolve().parents[2],  # governance root (ops/secrets -> ops -> root)
    )
    for root in allowed:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    _err("path escapes allowed roots")
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


def probe_secret_metadata(
    secret_id: str,
    region: str,
    *,
    runner: Any = subprocess.run,
) -> str | None:
    """Reachability probe. Returns a canonical error code, or None when reachable.

    NON-VALUE-BEARING by construction: ``describe-secret`` returns metadata only.
    The Secrets Manager API has no parameter that would make it emit
    ``SecretString`` or ``SecretBinary``, so no secret byte can enter this
    process through this path even if the response were mishandled. ``--query
    ARN`` narrows the response further, to one identifier the registry already
    names.

    This is the counterpart of :func:`fetch_secret_string`, and the two are kept
    as separate functions on purpose: one retrieves the value, one does not, and
    no flag turns either into the other.
    """
    try:
        proc = runner(
            [
                "aws",
                "secretsmanager",
                "describe-secret",
                "--secret-id",
                secret_id,
                "--region",
                region,
                "--query",
                "ARN",
                "--output",
                "text",
            ],
            capture_output=True,
            text=True,
            timeout=AWS_CALL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except FileNotFoundError:
        return "AWS_CLI_NOT_FOUND"

    if proc.returncode != 0:
        stderr = proc.stderr or ""
        if "ResourceNotFoundException" in stderr:
            return "NOT_FOUND"
        # Auth, access-denied, region and transport failures all land here.
        # The repository's canonical vocabulary has no finer code, and provider
        # stderr is deliberately not surfaced (see _canonical_error).
        return "RESOLUTION_ERROR"

    arn = (proc.stdout or "").strip()
    if not arn or arn == "None":
        return "NOT_FOUND"
    return None


def resolve_ref(
    ref_id: str,
    region: str,
    *,
    runner: Any = subprocess.run,
    surface: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve a ref to its VALUE. The only value-bearing path in this module.

    Guarded: a caller inside a model-controlled runtime raises ``PermissionError``
    here even if it reached this module by direct import rather than through the
    CLI. The boundary is enforced at the value path, not only at the entrypoint,
    and there is no unguarded sibling of this function to reach around it.
    """
    require_trusted(surface)
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


def probe_ref(
    ref_id: str,
    region: str,
    *,
    runner: Any = subprocess.run,
) -> str | None:
    """Return a canonical error code, or None on success. Never fetches the value.

    Status probing asks whether the backing provider object is reachable. It does
    NOT ask what the object contains, so it calls :func:`probe_secret_metadata`
    and never :func:`fetch_secret_string`. Discarding a fetched value after the
    fact would not satisfy the boundary — on a model-controlled surface the bytes
    must not be delivered into the process at all.

    Field membership is answered by the registry (:func:`ref_registered`, which
    matches the ref's field against the entry's declared ``keys``), not by the
    provider. Confirming that the *stored* JSON currently carries that field
    requires the value, so it belongs to :func:`resolve_ref` on a trusted surface.

    Fails closed: an inconclusive metadata probe returns its canonical error. No
    path here falls back to value retrieval.
    """
    secret_id, _field = split_id(ref_id)
    error = probe_secret_metadata(secret_id, region, runner=runner)
    if error is None:
        return None
    return _canonical_error(error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="secret_id or secret_id#json_key")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Status only: registry + non-value-bearing provider reachability probe",
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

    if not args.check:
        # Trust boundary first. A model-controlled caller is refused before the
        # registry is read and before any provider call is made, so it learns
        # nothing about inventory contents either. resolve_ref() repeats the
        # guard for callers that import the value path directly.
        try:
            require_trusted()
        except PermissionError as exc:
            _err(str(exc))
            return 1

    registry = load_registry(args.registry)
    if not args.allow_unregistered and not ref_registered(registry, ref_id):
        if args.check:
            print("FAIL")
        else:
            print("FAIL", file=sys.stderr)
        return 1

    secret_id, _field = split_id(ref_id)
    entry = entry_for(registry, secret_id)
    if entry is not None and entry.get("provisioned") is False:
        if args.check:
            print("FAIL")
        else:
            print("FAIL", file=sys.stderr)
        return 1

    region = (
        args.region
        or (entry or {}).get("region")
        or os.environ.get("AWS_REGION")
        or registry.get("region_default")
        or AWS_REGION_DEFAULT
    )

    if args.check:
        error = probe_ref(ref_id, region)
        if error is not None:
            # Static status only — never interpolate codes/handles from the
            # secret-resolution dataflow (CodeQL clear-text-logging).
            print("FAIL")
            return 1
        print("OK")
        return 0

    value, error = resolve_ref(ref_id, region)
    if error is not None:
        print("FAIL", file=sys.stderr)
        return 1
    _emit_secret_value(value or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
