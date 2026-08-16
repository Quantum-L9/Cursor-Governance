"""Runtime admission: a mutating Controller command needs a READY receipt.

``preflight`` already reports runtime state, but reporting is not admission — an
agent that never runs preflight could still drive ``claim``/``start``/
``record-attempt`` from a runtime whose governance revision, generated
environment or session identity was never established. That is the failure this
module closes: every command that mutates Controller state resolves the same
``l9.agents.runtime-readiness.v1`` receipt the bootstrap writes, and refuses
unless it says READY.

DEGRADED is refused as well as NOT_READY. A degraded runtime is one whose
checkers, generated environment or capability plane are known-incomplete; it is
fine to *inspect* from, and never fine to record governed evidence from.

Read-only commands are deliberately exempt. An operator whose runtime is broken
must still be able to run ``status``, ``next``, ``preflight`` and ``validate``
to find out why — a gate that blinds the diagnostic path is a gate that cannot
be cleared.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SCHEMA = "program-execution-controller.admission-refusal.v1"
UNKNOWN = "UNKNOWN"
READY = "READY"

# Commands that only READ Controller/runtime state. Everything not listed here is
# treated as mutating — the safe default when a new subcommand is added.
#
# Membership is by observed write behavior, not by how diagnostic a command
# sounds. `export-handoff` writes runtime/campaign-status.json and an output
# file, and `draft-contract` writes a draft and opens the runtime; both mutate
# and are therefore absent. The four below neither write nor open the runtime for
# write, and `replan-list` / `plan-revision` only project stored revisions.
READ_ONLY_COMMANDS = frozenset(
    {
        "status",
        "next",
        "preflight",
        "validate",
        "plan-revision",
        "replan-list",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def is_mutating(command: str) -> bool:
    return command not in READ_ONLY_COMMANDS


def resolve_surface() -> str:
    """Surface id this session runs under, as the bootstrap recorded it."""
    return (os.environ.get("L9_GOVERNANCE_SURFACE") or "").strip() or "cursor"


def resolve_receipt_workspace() -> Path:
    """Workspace the readiness receipt is keyed on.

    Must resolve identically to the ``--workspace`` the shared bootstrap passed
    to ``write_runtime_readiness_receipt.py``; the harness-injected project dir
    is that same path, so prefer it over cwd, which moves with ``cd``.
    """
    for key in ("L9_PE_RECEIPT_WORKSPACE", "CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"):
        value = (os.environ.get(key) or "").strip()
        if value:
            return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def load_receipt(surface: str, workspace: Path) -> tuple[Path | None, dict[str, Any] | None]:
    """Resolve the receipt through its own writer — never re-derive its path."""
    scripts = _repo_root() / "ops" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        from write_runtime_readiness_receipt import receipt_path
    except ImportError:
        return None, None
    path = receipt_path(surface=surface, workspace=workspace)
    if not path.is_file():
        return path, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return path, None
    return path, data if isinstance(data, dict) else None


def _write_receipt_action(surface: str, workspace: Path) -> dict[str, Any]:
    return {
        "command": "python3",
        "args": [
            str(_repo_root() / "ops" / "scripts" / "write_runtime_readiness_receipt.py"),
            "--surface",
            surface,
            "--workspace",
            str(workspace),
        ],
    }


def check_admission(command: str, *, surface: str, workspace: Path) -> dict[str, Any] | None:
    """Return a structured refusal, or ``None`` when the command may proceed."""
    if not is_mutating(command):
        return None

    path, receipt = load_receipt(surface, workspace)
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "BLOCKED",
        "command": command,
        "surface": surface,
        "receipt_workspace": str(workspace),
        "receipt_path": str(path) if path else UNKNOWN,
        "next_action": _write_receipt_action(surface, workspace),
    }

    if receipt is None:
        return {
            **base,
            "error_code": "RUNTIME_RECEIPT_MISSING",
            "overall_status": UNKNOWN,
            "error": (
                f"no runtime readiness receipt for surface {surface!r} at {workspace}; "
                "run the shared bootstrap (or the writer below) before mutating execution"
            ),
            "unresolved_required": [],
        }

    status = str(receipt.get("overall_status") or UNKNOWN)
    if status == READY:
        return None

    unresolved_required = list(receipt.get("unresolved_required") or [])
    degraded = [
        str(item.get("id"))
        for item in (receipt.get("components") or [])
        if isinstance(item, dict) and item.get("status") != "PRESENT"
    ]
    return {
        **base,
        "error_code": str(receipt.get("failure_code") or "") or "RUNTIME_NOT_READY",
        "overall_status": status,
        "error": (
            f"runtime readiness is {status}, not READY; {command!r} mutates governed "
            "state and is refused until the runtime is repaired"
        ),
        "unresolved_required": unresolved_required,
        "degraded_components": degraded,
        "governance_revision": receipt.get("governance_revision", UNKNOWN),
        "runtime_script_revision": receipt.get("runtime_script_revision", UNKNOWN),
        "session_id": receipt.get("session_id", UNKNOWN),
    }
