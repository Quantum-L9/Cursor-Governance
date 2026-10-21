#!/usr/bin/env python3
"""PreToolUse coding-agent binding gate (file mutations).

Thin adapter: when a Claude runtime is present (never Cursor), forward the hook
event to ``ops/autonomy/coding_agent_binding_gate.py``, the one brain that
decides whether an active ``l9-coding-agent`` run may mutate files. Named
``*_wrap`` like the other adapters so the brain's module name is never shadowed
by this file when it imports it. The brain
denies only while a run is active (``.l9/coding-agent/run.json``) and its
canonical binding is neither BOUND/CURRENT nor explicitly reauthorized by the
user. Exit 0 always: a denial is the JSON decision on stdout; a brain that
cannot be resolved is a denial (a gate that cannot evaluate has not passed).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

for _autonomy in (
    Path(__file__).resolve().parents[5] / "ops" / "autonomy",
    Path.home() / ".cursor-governance" / "ops" / "autonomy",
):
    if _autonomy.is_dir() and str(_autonomy) not in sys.path:
        sys.path.insert(0, str(_autonomy))


def _deny(reason: str) -> int:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


def main() -> int:
    try:
        from surface_detect import claude_runtime_present, cursor_host_present
    except ImportError:
        return 0
    if cursor_host_present() or not claude_runtime_present():
        return 0
    try:
        import coding_agent_binding_gate as brain
    except ImportError as exc:
        return _deny(
            f"coding-agent binding gate: brain unresolved ({exc}); failing closed. "
            "Operator override: L9_CODING_BINDING_AUTHORIZED=<reason>."
        )
    return brain.main()


if __name__ == "__main__":
    raise SystemExit(main())
