"""``governance_binding`` — report the Manus projection binding.

Wraps ``ops/autonomy/host_binding.py --host manus``. This is the same report
``make manus-start`` prints, exposed as a tool so a session can establish
whether operating-plane semantics may be cited *before* it cites them.

Read-only: the binding report verifies and prints, and binds nothing by itself.
"""

from __future__ import annotations

import json
from typing import Any

from .base import RuntimeContext, ToolInputError, ToolSpec

NAME = "governance_binding"
DESCRIPTION = (
    "Report the Manus projection binding (BOUND / NOT_BOUND / DEGRADED) and the "
    "authority commit it resolved against. Read-only: it verifies and prints, and "
    "binds nothing by itself."
)
INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "format": {
            "type": "string",
            "enum": ["json", "line"],
            "description": "Structured report (default) or the human binding line.",
        }
    },
    "additionalProperties": False,
}

_BINDING_SCRIPT = "ops/autonomy/host_binding.py"


def collect_binding(context: RuntimeContext, *, timeout: int = 90) -> dict[str, Any]:
    """Run the binding report and normalise its outcome."""

    script = context.governance_root / _BINDING_SCRIPT
    if not script.is_file():
        raise ToolInputError(f"binding control absent at {_BINDING_SCRIPT}")

    result = context.run(
        [context_python(context), script, "--host", "manus", "--format", "json"],
        timeout=timeout,
    )
    if result.get("status") != "completed":
        return {
            "status": "UNKNOWN",
            "reason": result.get("status"),
            "detail": result.get("error") or result.get("timeout_seconds"),
            "raw": result,
        }

    raw = (result.get("stdout") or "").strip()
    try:
        report = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "status": "UNKNOWN",
            "reason": "binding report was not JSON",
            "exit_code": result.get("exit_code"),
            "stderr": (result.get("stderr") or "").strip()[:2000],
        }

    default = report.get("default") or {}
    return {
        "status": report.get("status") or default.get("status") or "UNKNOWN",
        "host": report.get("host"),
        "authority_root": report.get("authority_root"),
        "canonical_binding_ref": report.get("canonical_binding_ref"),
        "default_projection": default,
        "activations": report.get("activations"),
        "blockers": report.get("blockers"),
        "domains": report.get("domains"),
        "fail_open": report.get("fail_open"),
        "exit_code": result.get("exit_code"),
    }


def context_python(context: RuntimeContext) -> str:
    """Prefer the repository's locked interpreter when it exists."""

    candidate = context.governance_root / ".venv/bin/python"
    return str(candidate) if candidate.is_file() else "python3"


def handle(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
    requested = arguments.get("format", "json")
    if requested not in {"json", "line"}:
        raise ToolInputError("format must be json or line")

    report = collect_binding(context)
    if requested == "line":
        default = report.get("default_projection") or {}
        if report["status"] == "BOUND":
            sha = (default.get("authority_main") or "")[:12]
            line = (
                "default projection binding (manus): BOUND — every default projection "
                f"verified (authority {sha or 'unknown'})"
            )
        else:
            line = (
                f"default projection binding (manus): {report['status']} — "
                f"{default.get('reason') or 'no reason reported'}"
            )
        return {"status": report["status"], "line": line, "report": report}
    return report


def build_spec() -> ToolSpec:
    return ToolSpec(
        name=NAME,
        description=DESCRIPTION,
        input_schema=INPUT_SCHEMA,
        handler=handle,
    )
