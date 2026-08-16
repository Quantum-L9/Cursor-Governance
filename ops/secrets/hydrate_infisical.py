#!/usr/bin/env python3
"""Infisical read side — provider layer plus a TRUSTED-OPERATOR CLI.

Companion to ``port_aws_to_infisical.py``, which owns the AWS -> Infisical write
direction. There is one Infisical client in this repository and this is its read
half.

RESPONSIBILITY SPLIT (contract R3). This file used to be three things at once;
they are now separated, and only two of them live here:

    provider layer          resolves secrets INSIDE a trusted boundary
                            (:func:`fetch_names`, :func:`fetch_values`)
    operator CLI            optional manual resolution for a human
                            (``--surface operator --export ...``)
    agent capability layer  NOT HERE — ops/secrets/capability_client.py, which
                            has no value-returning path at all

The agent-facing layer is a different module on purpose. LLM-facing code cannot
import a value path from here by accident, because every value path is behind
:func:`surface_trust.require_trusted`, which refuses any caller running inside a
model-controlled runtime — including one that passes ``--surface operator``
while Claude's own environment markers are visible.

The AWS bootstrap is gone (contract S1). It is not a fallback, not a legacy
branch, and not reachable by flag: an agent surface must never be able to obtain
Universal Auth credentials from an instance profile. Operators who need raw
values authenticate with their own Infisical credentials in their own shell.

Secret VALUES are never logged, never printed by ``--check``, and never written
to a receipt. ``--check`` asks Infisical for names only (``viewSecretValue=false``),
so a check run cannot leak a value even in a trace.

Usage:
  hydrate_infisical.py --check                      # names/availability only
  hydrate_infisical.py --surface operator --export SONAR_TOKEN   # humans only

Exit 0 when every required name is available, 1 otherwise.
"""

# L9-TRUSTED-OPERATOR-ONLY — raw-secret paths in this file are reachable only
# beyond the model boundary and are guarded by surface_trust.require_trusted /
# the broker's boundary self-check. The marker declares that status for review;
# it is not a bypass, and it does not disable those runtime guards.

from __future__ import annotations

import argparse
import shlex
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
from surface_trust import classify, require_trusted  # noqa: E402

DEFAULT_HOST = "https://app.infisical.com"
DEFAULT_SECRET_PATH = "/"


def _err(msg: str) -> None:
    print(f"hydrate_infisical: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Provider layer — trusted boundary only
# ---------------------------------------------------------------------------


def bootstrap_config(env: dict[str, str] | None = None) -> dict[str, str] | None:
    """Resolve Infisical connection settings. Never returns secret payloads.

    Environment-supplied Universal Auth only, and only for a trusted operator.
    There is deliberately no AWS branch: see the module docstring.
    """
    import os

    source = os.environ if env is None else env
    client_id = (source.get("INFISICAL_CLIENT_ID") or "").strip()
    client_secret = (source.get("INFISICAL_CLIENT_SECRET") or "").strip()
    if not (client_id and client_secret):
        return None
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "host": ((source.get("INFISICAL_SITE_URL") or "").strip() or DEFAULT_HOST).rstrip("/"),
        "project_id": (source.get("INFISICAL_PROJECT_ID") or "").strip() or DEFAULT_PROJECT_ID,
        "environment": (source.get("INFISICAL_ENV") or "").strip() or DEFAULT_ENV,
        "secret_path": (source.get("INFISICAL_SECRET_PATH") or "").strip() or DEFAULT_SECRET_PATH,
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


def fetch_names(cfg: dict[str, str]) -> dict[str, str]:
    """Availability only. Values are not requested from the provider at all."""
    return _fetch(cfg, with_values=False)


def fetch_values(cfg: dict[str, str], *, surface: str | None = None) -> dict[str, str]:
    """Resolve VALUES. Guarded — the guard is the point of this function existing.

    Callers inside a model-controlled runtime raise ``PermissionError`` here
    even if they reached this module by direct import rather than through the
    CLI. The boundary is enforced at the value path, not at the entrypoint.
    """
    require_trusted(surface)
    return _fetch(cfg, with_values=True)


def _split(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _provider_unavailable(required: list[str]) -> int:
    _err(
        "no Infisical operator credentials in this shell "
        "(INFISICAL_CLIENT_ID / INFISICAL_CLIENT_SECRET). Agent surfaces do not use "
        "this path at all — they request named capabilities; see capability_client.py"
    )
    for name in required:
        print(f"{name}: PROVIDER_UNAVAILABLE")
    return 1


# ---------------------------------------------------------------------------
# Operator CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Infisical read side (operator CLI).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report availability; never values")
    mode.add_argument("--export", dest="export", help="comma-separated names to emit as exports")
    parser.add_argument("--require", help="comma-separated names that must be available")
    parser.add_argument("--surface", help="calling surface id (default: L9_GOVERNANCE_SURFACE)")
    args = parser.parse_args(argv)

    trust = classify(args.surface)
    required = _split(args.require) or _split(args.export)

    if args.export and not trust.raw_secret_allowed:
        # The same refusal the shell emits, enforced independently so that
        # calling this module directly is not a way around it.
        _err("DENIED: raw secret export is prohibited on model-controlled surfaces")
        _err(f"  {trust.reason}")
        _err("  request a named capability instead (ops/secrets/capabilities.yaml)")
        return 3

    cfg = bootstrap_config()
    if cfg is None:
        return _provider_unavailable(required)

    try:
        available = fetch_values(cfg, surface=args.surface) if args.export else fetch_names(cfg)
    except PermissionError as exc:
        _err(str(exc))
        return 3
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
        # Values reach stdout only, for `eval`, in a trusted operator shell.
        print(f"export {name}={shlex.quote(available[name])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
