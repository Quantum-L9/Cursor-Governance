#!/usr/bin/env python3
"""Structural acceptance dry-run for Autonomy Surface Parity (no remote PR).

Proves: Profile → SessionStart → reconcile apply/check → merge_gate deny/allow.
Does not open a real GitHub PR (network/product side-effect); that remains an
operator verification after install.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def step(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        raise SystemExit(1)


def main() -> int:
    sys.path.insert(0, str(ROOT / "ops" / "autonomy"))
    from profile_loader import session_start_block  # noqa: E402

    block = session_start_block(ROOT)
    step("profile doctrine", "Autonomy Velocity Doctrine" in block and "l9-pr-remediation" in block)

    script = ROOT / "environment" / "claude-code" / "hooks" / "session_start_claude_governance.sh"
    with tempfile.TemporaryDirectory(prefix="l9-autonomy-dry-") as td:
        home = Path(td) / "home"
        home.mkdir()
        (home / ".cursor-governance").symlink_to(ROOT)
        workspace = Path(td) / "workspace"
        workspace.mkdir()
        proc = subprocess.run(
            ["bash", str(script)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(home), "CLAUDE_PROJECT_DIR": str(workspace)},
            check=False,
        )
        step("session_start exit 0", proc.returncode == 0)
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
        ctx = payload["hookSpecificOutput"]["additionalContext"]
        step("session_start injects profile", "Autonomy Velocity Doctrine" in ctx)

        apply = subprocess.run(
            [
                sys.executable,
                str(ROOT / "ops" / "scripts" / "reconcile_claude_settings.py"),
                "--root",
                str(ROOT),
                "--workspace",
                str(workspace),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        step("reconcile apply", apply.returncode == 0, apply.stdout.strip() or apply.stderr.strip())

        check = subprocess.run(
            [
                sys.executable,
                str(ROOT / "ops" / "scripts" / "reconcile_claude_settings.py"),
                "--root",
                str(ROOT),
                "--workspace",
                str(workspace),
                "--check",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        step(
            "reconcile --check",
            check.returncode == 0,
            check.stdout.strip() or check.stderr.strip(),
        )

    gate = ROOT / "ops" / "autonomy" / "merge_gate.py"
    deny = subprocess.run(
        [sys.executable, str(gate)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "gh pr merge 1"}}),
        text=True,
        capture_output=True,
        check=False,
    )
    step("merge_gate denies gh pr merge", "deny" in deny.stdout)
    allow = subprocess.run(
        [sys.executable, str(gate)],
        input=json.dumps(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git commit -m x && git push origin HEAD"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    step("merge_gate allows commit/push", allow.stdout.strip() == "")

    ovr = ROOT / "environment" / "generated" / "llm-rules" / "zz-autonomy-surface-override.md"
    step(
        "llm-rules override",
        ovr.is_file() and "99-no-auto-commit" in ovr.read_text(encoding="utf-8"),
    )

    print("RESULT: PASS — structural autonomy surface dry-run")
    print("NOTE: live Claude session PR remediation still requires operator smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
