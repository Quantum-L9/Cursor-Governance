#!/usr/bin/env python3
"""Claude PreToolUse wrapper: Program-bound root authorization → ops gate (§2.1).

Two decisions run here, in this order, for every tool call:

1. **Root authorization.** Inside a Program Execution worker window
   (``L9_AUTONOMY_REQUIRED=1``) the effect is authorized through the root
   capability gateway, bound to the live Program parent, *before* the tool
   runs. Missing authority, an unavailable authorizer, or a denial is a
   denial — a worker window that cannot prove its authority has none.
2. **The existing ops gate.** ``ops/autonomy/local_execution_gate.py`` remains
   the downstream owner of publish-path, L4 and worktree-isolation policy. It
   is invoked unchanged, with the *byte-identical* hook stdin this process
   read, so its verdict is computed on exactly the event Claude sent.

Outside a worker window nothing changes: no authority is required and the ops
gate decides alone. This is not a second hook framework — it is the one
wrapper that already existed, now composing an authorization step in front of
the gate it always called.

Exit codes are Claude Code's hook contract: 0 proceed, 2 block.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def _governance_root() -> Path:
    """The clone this hook was launched from, never one the environment names.

    `l9_hook_exec.sh` execs this file out of the governance tree it validated,
    so the tree above this file is the authoritative one. Resolving it from an
    environment variable instead would let a caller point a gate at its own
    policy.
    """
    here = Path(__file__).resolve()
    candidate = here.parents[5]
    if (candidate / "CANONICAL_LAW.md").is_file():
        return candidate
    return Path.home() / ".cursor-governance"


def _workspace_hint() -> Path | None:
    for key in ("CLAUDE_PROJECT_DIR", "CURSOR_PROJECT", "L9_L4_WORKSPACE"):
        raw = os.environ.get(key, "").strip()
        if raw:
            return Path(raw)
    return None


def _default_gate() -> Path:
    """Same file Cursor's beforeShellExecution loads — one resolver."""
    autonomy = _governance_root() / "ops" / "autonomy"
    resolver = autonomy / "resolve_execution_gate.py"
    fallback = autonomy / "local_execution_gate.py"
    if not resolver.is_file():
        return fallback
    if str(autonomy) not in sys.path:
        sys.path.insert(0, str(autonomy))
    from resolve_execution_gate import resolve_gate  # noqa: PLC0415

    try:
        return resolve_gate(workspace=_workspace_hint(), hook_file=None)
    except FileNotFoundError:
        return fallback


GOV = _governance_root()
GATE = _default_gate()
AUTHORITY_MODULE = (
    GOV
    / "environment"
    / "program-execution"
    / "integrations"
    / "autonomy-control-plane"
    / "program_authority.py"
)

#: Environment the Program Execution Claude provider exports into a worker
#: window. `L9_AUTONOMY_LEASE_ID` / `L9_AUTONOMY_AGENT_ID` are the historical
#: aliases root autonomy already accepts.
_AUTHORITY_ENV = (
    ("adapter_session_id", ("L9_ADAPTER_SESSION_ID",)),
    ("lease_id", ("L9_LEASE_ID", "L9_AUTONOMY_LEASE_ID")),
    ("agent_id", ("L9_AGENT_ID", "L9_AUTONOMY_AGENT_ID")),
    ("runtime_database", ("L9_AUTONOMY_DATABASE",)),
    ("repository_root", ("L9_AUTONOMY_ROOT",)),
    ("workspace", ("L9_PROGRAM_WORKSPACE",)),
    ("task_id", ("L9_PROGRAM_TASK_ID",)),
    ("attempt_number", ("L9_PROGRAM_ATTEMPT_NUMBER",)),
    ("authority_digest", ("L9_AUTONOMY_AUTHORITY_DIGEST",)),
)

#: Fields the environment must agree on with the persisted grant receipt. The
#: environment is a lookup key for authority PE recorded, never authority
#: itself: a worker window that edits its own environment changes which
#: receipt it points at, and a receipt it does not match denies.
_RECEIPT_BOUND_FIELDS = (
    "adapter_session_id",
    "lease_id",
    "agent_id",
    "runtime_database",
    "repository_root",
    "workspace",
    "task_id",
    "attempt_number",
)


def autonomy_required() -> bool:
    return os.environ.get("L9_AUTONOMY_REQUIRED", "").strip() == "1"


def authority_from_environment() -> dict[str, Any] | None:
    """The worker window's root authority, or None when it is incomplete."""
    authority: dict[str, Any] = {}
    for field, names in _AUTHORITY_ENV:
        value = next((os.environ[name] for name in names if os.environ.get(name)), None)
        if not value:
            return None
        authority[field] = value
    parent = {
        "workspace": authority["workspace"],
        "task_id": authority["task_id"],
        "lease_id": os.environ.get("L9_PROGRAM_LEASE_ID") or None,
        "worktree": os.environ.get("L9_PROGRAM_WORKTREE") or None,
    }
    authority["program_parent"] = {key: value for key, value in parent.items() if value}
    return authority


def _authority_digest(sidecar: dict[str, Any]) -> str:
    """Same canonical digest `grant.authority_digest` records on the sidecar."""
    payload = {key: value for key, value in sidecar.items() if key != "authority_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _grant_receipt_path(authority: dict[str, Any]) -> Path:
    """Task/attempt-scoped grant receipt, the same location `grant.py` writes."""
    task = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(authority["task_id"])).strip("-") or "task"
    attempt = int(str(authority["attempt_number"]))
    return (
        Path(str(authority["workspace"])).resolve()
        / "runtime"
        / "autonomy-grants"
        / f"{task}.attempt-{attempt:03d}.grant.json"
    )


def persisted_authority(environment_authority: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Resolve the window's environment to the grant receipt PE persisted.

    Returns ``(sidecar, "")`` when the environment names exactly the authority
    the receipt records, else ``(None, reason)``. The receipt's own sidecar is
    what the authorizer then runs on: it carries the Program parent binding
    (base SHA, contract digest, lease) that the environment deliberately does
    not export, so parent-drift checks are live rather than inert.
    """
    try:
        path = _grant_receipt_path(environment_authority)
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"authority environment does not name a grant receipt: {exc}"
    if not path.is_file():
        return None, f"no persisted grant receipt at {path}"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, f"grant receipt is unreadable: {path}: {exc}"
    sidecar = receipt.get("autonomy_authority") if isinstance(receipt, dict) else None
    if not isinstance(sidecar, dict):
        return None, f"grant receipt carries no authority sidecar: {path}"
    recorded = str(sidecar.get("authority_digest") or "")
    claimed = str(environment_authority.get("authority_digest") or "")
    if not recorded or recorded != claimed:
        return None, "authority digest does not match the persisted grant receipt"
    if _authority_digest(sidecar) != recorded:
        return None, "persisted grant receipt fails its own digest"
    for field in _RECEIPT_BOUND_FIELDS:
        if str(sidecar.get(field)) != str(environment_authority.get(field)):
            return None, f"authority {field!r} does not match the persisted grant receipt"
    return dict(sidecar), ""


def _load_authority_module() -> Any:
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location(
        "l9_program_authority_hook", str(AUTHORITY_MODULE)
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load program authority module: {AUTHORITY_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["l9_program_authority_hook"] = module
    try:
        spec.loader.exec_module(module)
    # BaseException, not Exception: a partially executed module must be
    # unregistered even when the load is interrupted, or the next import
    # silently gets the broken half. The block re-raises.
    except BaseException:
        sys.modules.pop("l9_program_authority_hook", None)
        raise
    return module


def _event(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _deny(reason: str) -> int:
    print(f"l9-autonomy: BLOCKED — {reason}", file=sys.stderr)
    return 2


def authorize(raw: bytes) -> int:
    """0 when this effect may proceed to the ops gate, 2 when it may not."""
    if not autonomy_required():
        return 0
    claimed = authority_from_environment()
    if claimed is None:
        return _deny(
            "L9_AUTONOMY_REQUIRED=1 but this window carries no root autonomy authority "
            "(adapter session, lease, agent, runtime database, workspace, task, attempt, digest)"
        )
    authority, reason = persisted_authority(claimed)
    if authority is None:
        return _deny(f"root authority is not the one PE recorded: {reason}")
    if not AUTHORITY_MODULE.is_file():
        return _deny(f"root authorizer is missing at {AUTHORITY_MODULE}")
    event = _event(raw)
    tool_name = str(event.get("tool_name") or "")
    if not tool_name:
        return _deny("hook event carries no tool_name; a nameless effect cannot be authorized")
    tool_input = event.get("tool_input")
    arguments = dict(tool_input) if isinstance(tool_input, dict) else {}
    try:
        module = _load_authority_module()
        authorizer = module.ProgramBoundEffectAuthorizer(authority)
        decision = authorizer.authorize(tool_name=tool_name, arguments=arguments)
    except Exception as exc:  # noqa: BLE001 - security boundary: deny on any fault
        return _deny(f"root authorization could not be evaluated: {type(exc).__name__}: {exc}")
    if not decision.allowed:
        return _deny(f"{decision.code}: {decision.message}")
    return 0


def main() -> int:
    raw = sys.stdin.buffer.read()
    verdict = authorize(raw)
    if verdict != 0:
        return verdict
    if not GATE.is_file():
        return _deny(f"ops local execution gate is missing at {GATE}")
    completed = subprocess.run(
        [sys.executable, str(GATE), "claude"],
        input=raw,
        check=False,
    )
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
