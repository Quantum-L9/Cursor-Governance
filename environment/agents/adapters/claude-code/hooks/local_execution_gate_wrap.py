#!/usr/bin/env python3
"""Claude PreToolUse wrapper: forward the event to the root execution gate.

The wrapper does not authorize and does not schedule. It resolves the existing
``ops/autonomy`` execution gate, sends the byte-identical hook stdin, and
propagates that gate's exit code. A gate that cannot be resolved or invoked
is a denial.

Exit codes are Claude Code's hook contract: 0 proceed, 2 block.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


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


def _default_gate() -> Path | None:
    """Same file Cursor's beforeShellExecution loads — one resolver."""
    autonomy = _governance_root() / "ops" / "autonomy"
    resolver = autonomy / "resolve_execution_gate.py"
    fallback = autonomy / "local_execution_gate.py"
    if not resolver.is_file():
        return fallback if fallback.is_file() else None
    if str(autonomy) not in sys.path:
        sys.path.insert(0, str(autonomy))
    try:
        from resolve_execution_gate import resolve_gate  # noqa: PLC0415

        return resolve_gate(workspace=_workspace_hint(), hook_file=None)
    except FileNotFoundError:
        return fallback if fallback.is_file() else None
    except Exception:
        return None


GATE = _default_gate()


def _deny(reason: str) -> int:
    print(f"l9-autonomy: BLOCKED — {reason}", file=sys.stderr)
    return 2


def main() -> int:
    raw = sys.stdin.buffer.read()
    gate = GATE
    if gate is None or not Path(gate).is_file():
        return _deny(f"ops local execution gate is missing at {gate}")
    try:
        completed = subprocess.run(
            [sys.executable, str(gate), "claude"],
            input=raw,
            check=False,
        )
    except OSError as exc:
        return _deny(f"ops local execution gate could not be invoked: {exc}")
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
