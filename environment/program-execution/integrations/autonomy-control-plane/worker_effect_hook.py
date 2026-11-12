#!/usr/bin/env python3
"""PreToolUse hook for a Program worker window: authorize one effect, or block.

Program Execution launches its own worker windows, so it carries its own
enforcement into them. The provider registers this file as a PreToolUse hook
of the window it starts; the host-wide Claude wrapper
(`environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py`)
does not reach Program Execution and is not asked to.

For each tool call, in order, fail-closed at every step:

1. the window's environment must name a complete authority lookup key;
2. that key must resolve to the grant receipt PE persisted for this exact
   task and generation, whose sidecar still carries its own digest and agrees
   with every field the environment claims;
3. `ProgramBoundEffectAuthorizer` re-reads the live Program parent and asks
   the root gateway for this capability on this resource;
4. the byte-identical event is handed to the root execution gate, which stays
   the owner of publish-path, L4 and worktree-isolation policy.

The environment is a lookup key for recorded authority, never authority
itself. Exit codes are Claude Code's hook contract: 0 proceed, 2 block.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent

#: Environment variable -> authority sidecar field. The provider exports
#: exactly these; every one is required and every one is checked against the
#: persisted receipt.
AUTHORITY_ENVIRONMENT: dict[str, str] = {
    "L9_ADAPTER_SESSION_ID": "adapter_session_id",
    "L9_LEASE_ID": "lease_id",
    "L9_AGENT_ID": "agent_id",
    "L9_AUTONOMY_DATABASE": "runtime_database",
    "L9_AUTONOMY_ROOT": "repository_root",
    "L9_PROGRAM_WORKSPACE": "workspace",
    "L9_PROGRAM_TASK_ID": "task_id",
    "L9_PROGRAM_ATTEMPT_NUMBER": "attempt_number",
    "L9_AUTONOMY_AUTHORITY_DIGEST": "authority_digest",
}

GATE_OVERRIDE_ENV = "L9_EXECUTION_GATE"
GATE_RELATIVE = Path("ops/autonomy/local_execution_gate.py")


class HookDenied(RuntimeError):
    """One refused effect; the message is the reason shown to the window."""


def _deny(reason: str) -> int:
    print(f"l9-program-authority: BLOCKED — {reason}", file=sys.stderr)
    return 2


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise HookDenied(f"AUTHORIZER_UNAVAILABLE: cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sidecar_digest(authority: Mapping[str, Any]) -> str:
    """Same digest `grant.authority_digest` computes over the sidecar."""
    payload = {key: value for key, value in authority.items() if key != "authority_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _receipt_path(workspace: str, task_id: str, attempt_number: int) -> Path:
    """Same location `grant.grant_receipt_path(..., kind="grant")` writes."""
    safe_task = re.sub(r"[^a-zA-Z0-9._-]+", "-", task_id).strip("-") or "task"
    return (
        Path(workspace).resolve()
        / "runtime"
        / "autonomy-grants"
        / f"{safe_task}.attempt-{attempt_number:03d}.grant.json"
    )


def claimed_authority(environment: Mapping[str, str]) -> dict[str, str]:
    """The lookup key the window carries; an incomplete one is refused."""
    claimed: dict[str, str] = {}
    for name, field in AUTHORITY_ENVIRONMENT.items():
        value = str(environment.get(name) or "").strip()
        if not value:
            raise HookDenied(f"ROOT_AUTHORITY_INCOMPLETE: {name} is not set in this window")
        claimed[field] = value
    return claimed


def recorded_authority(claimed: Mapping[str, str]) -> dict[str, Any]:
    """The persisted sidecar this window's environment names, verified."""
    try:
        attempt_number = int(claimed["attempt_number"])
    except ValueError as exc:
        raise HookDenied("ROOT_AUTHORITY_INCOMPLETE: attempt number is not an integer") from exc
    path = _receipt_path(claimed["workspace"], claimed["task_id"], attempt_number)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HookDenied(f"GRANT_RECEIPT_MISSING: no readable grant receipt at {path}") from exc
    authority = receipt.get("autonomy_authority") if isinstance(receipt, dict) else None
    if not isinstance(authority, dict):
        raise HookDenied("GRANT_RECEIPT_MALFORMED: receipt carries no authority sidecar")
    carried = str(authority.get("authority_digest") or "")
    if not carried or _sidecar_digest(authority) != carried:
        raise HookDenied("GRANT_RECEIPT_TAMPERED: persisted sidecar fails its own digest")
    for field, value in claimed.items():
        recorded = authority.get(field)
        if recorded is None or str(recorded) != value:
            raise HookDenied(
                f"ROOT_AUTHORITY_MISMATCH: window claims {field}={value!r}, "
                "which the persisted grant receipt does not record"
            )
    return authority


def _downstream_gate(authority: Mapping[str, Any], environment: Mapping[str, str]) -> Path:
    override = str(environment.get(GATE_OVERRIDE_ENV) or "").strip()
    candidate = (
        Path(override) if override else Path(str(authority["repository_root"])) / GATE_RELATIVE
    )
    if not candidate.is_file():
        raise HookDenied(f"ROOT_GATE_MISSING: no execution gate at {candidate}")
    return candidate


def main() -> int:
    raw = sys.stdin.buffer.read()
    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _deny("HOOK_EVENT_MALFORMED: the tool event is not JSON")
    if not isinstance(event, dict):
        return _deny("HOOK_EVENT_MALFORMED: the tool event is not an object")
    tool_name = str(event.get("tool_name") or event.get("toolName") or "").strip()
    if not tool_name:
        return _deny("TOOL_UNNAMED: an effect with no tool name cannot be authorized")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    try:
        authority = recorded_authority(claimed_authority(os.environ))
        program_authority = _load(_HERE / "program_authority.py", "pe_worker_program_authority")
        try:
            authorizer = program_authority.ProgramBoundEffectAuthorizer(authority)
            decision = authorizer.authorize(tool_name=tool_name, arguments=tool_input)
        except program_authority.ProgramAuthorityError as exc:
            raise HookDenied(str(exc)) from exc
        if not decision.allowed:
            raise HookDenied(f"{decision.code}: {decision.message}")
        gate = _downstream_gate(authority, os.environ)
    except HookDenied as exc:
        return _deny(str(exc))
    except Exception as exc:  # noqa: BLE001 - enforcement boundary: any fault denies
        return _deny(f"AUTHORIZER_UNAVAILABLE: {type(exc).__name__}: {exc}")
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [sys.executable, str(gate), "claude"],
            input=raw,
            check=False,
        )
    except OSError as exc:
        return _deny(f"ROOT_GATE_UNAVAILABLE: {exc}")
    return 0 if completed.returncode == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
