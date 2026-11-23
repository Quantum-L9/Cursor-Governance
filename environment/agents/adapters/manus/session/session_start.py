"""Manus session start: refresh authority, compute the binding, emit a receipt.

Manus fires no session hook. This module is the substitute that does not depend
on remembering: it is (a) a ``make manus-session-start`` target, (b) a unit
precondition on the governance service, and (c) the ``governance_session_start``
MCP tool a session calls first.

It is idempotent. Running it twice issues a second receipt with a later
timestamp and the same binding facts; it never mutates the checkout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RECEIPT_SCHEMA = "l9.manus.session-receipt.v1"
TOOL_NAME = "governance_session_start"


def _iso_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _authority_root() -> Path:
    configured = os.environ.get("L9_AUTHORITY_ROOT")
    return Path(configured) if configured else Path.home() / ".github"


def collect(
    context: Any,
    *,
    workspace: str | None = None,
    refresh: bool = True,
) -> dict[str, Any]:
    """Produce a session receipt. Never raises for a degraded binding."""

    steps: list[dict[str, Any]] = []
    root = context.governance_root

    if refresh:
        script = root / "ops/scripts/ensure_authority_checkout.sh"
        if script.is_file():
            refreshed = context.run(["bash", script], timeout=90)
            steps.append(
                {
                    "step": "authority_refresh",
                    "status": refreshed.get("status"),
                    "exit_code": refreshed.get("exit_code"),
                }
            )
        else:
            steps.append(
                {"step": "authority_refresh", "status": "skipped", "reason": "script absent"}
            )
    else:
        steps.append(
            {"step": "authority_refresh", "status": "skipped", "reason": "refresh disabled"}
        )

    from tools.binding import collect_binding  # local import: tools imports session

    binding = collect_binding(context)
    steps.append(
        {
            "step": "projection_binding",
            "status": binding.get("status"),
            "reason": (binding.get("default_projection") or {}).get("reason"),
        }
    )

    authority = _authority_root()
    authority_sha = None
    if authority.is_dir():
        head = context.run(
            ["git", "-C", str(authority), "rev-parse", "--short", "HEAD"], timeout=30
        )
        if head.get("status") == "completed" and head.get("exit_code") == 0:
            authority_sha = (head.get("stdout") or "").strip() or None

    status = binding.get("status") or "UNKNOWN"
    return {
        "schema": RECEIPT_SCHEMA,
        "host": "manus",
        "issued_at": _iso_now(),
        "workspace": workspace or str(root),
        "binding_status": status,
        "bound": status == "BOUND",
        "authority_root": str(authority),
        "authority_sha": authority_sha,
        "canonical_binding_ref": binding.get("canonical_binding_ref"),
        "steps": steps,
        "idempotent": True,
        "note": (
            "Manus fires no session hook; this receipt is the session's binding evidence. "
            "Cite operating-plane semantics only when bound is true."
        ),
    }


def handle(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    workspace = arguments.get("workspace")
    if workspace is not None and not isinstance(workspace, str):
        raise ValueError("workspace must be a string")
    refresh = arguments.get("refresh", True)
    if not isinstance(refresh, bool):
        raise ValueError("refresh must be a boolean")
    return collect(context, workspace=workspace, refresh=refresh)


def build_spec():
    from tools.base import ToolSpec

    return ToolSpec(
        name=TOOL_NAME,
        description=(
            "Establish the Manus session binding: refresh the authority checkout, compute the "
            "projection binding, and return a timestamped receipt with the authority commit. "
            "Read-only and idempotent. Call this before citing operating-plane semantics."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "workspace": {
                    "type": "string",
                    "description": (
                        "Workspace the session is bound to. Defaults to the governance root."
                    ),
                },
                "refresh": {
                    "type": "boolean",
                    "description": (
                        "Refresh the authority checkout before binding. Defaults to true."
                    ),
                },
            },
            "additionalProperties": False,
        },
        handler=handle,
    )


def main(argv: list[str] | None = None) -> int:
    from tools.base import RuntimeContext

    parser = argparse.ArgumentParser(description="Manus session start: bind and emit a receipt.")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--format", choices=("json", "line"), default="line")
    parser.add_argument("--no-refresh", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 1 unless the binding is BOUND.")
    parser.add_argument("--governance-root", type=Path, default=None)
    args = parser.parse_args(argv)

    root = args.governance_root or Path(__file__).resolve().parents[4]
    context = RuntimeContext(root)
    receipt = collect(context, workspace=args.workspace, refresh=not args.no_refresh)

    if args.format == "json":
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        print(
            f"manus session start: {receipt['binding_status']} "
            f"(authority {receipt['authority_sha'] or 'unknown'}) "
            f"workspace {receipt['workspace']} at {receipt['issued_at']}"
        )
    if args.strict and not receipt["bound"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
