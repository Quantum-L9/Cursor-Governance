#!/usr/bin/env python3
"""Deny a `git push` whose commit adds a CI-blocking finding on a changed line.

Registered `--class gate` on PreToolUse (Bash). It runs `ops/ci_parity/run.py
--gate HEAD` for the repository being pushed. Usually a receipt from the
commit-time background run already exists and this returns at once; otherwise
it waits on the in-flight run or scans (bounded by L9_CI_PARITY_WAIT).

Blocks only what CI would turn red: a NEW finding on a line this change touched,
at a severity its lane lists as blocking (tools.yaml). Pre-existing debt, absent
tools and unbound paid-tier tokens are reported as skips and never block — this
is checker semantics, not a workflow deny of the remediator's push path.

Exit 0 without output on non-Claude surfaces (Cursor loads .claude/settings.json
too), when L9_CI_PARITY=0, for `--dry-run` pushes, and for commands that are
not a push. Exit 2 with the findings on stderr to block.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

GOV = Path(__file__).resolve().parents[5]
RUNNER = GOV / "ops" / "ci_parity" / "run.py"
AUTONOMY = GOV / "ops" / "autonomy"
if str(AUTONOMY) not in sys.path:
    sys.path.insert(0, str(AUTONOMY))

_SEGMENT = re.compile(r"&&|\|\||[;|\n]")
DEFAULT_WAIT = 600


def claude_surface() -> bool:
    try:
        import surface_detect  # noqa: PLC0415
    except ImportError:
        return False
    return bool(surface_detect.is_claude_gate_surface())


def push_target(command: str, cwd: Path) -> Path | None:
    """The repository a `git ... push` in `command` operates on, else None."""
    for segment in _SEGMENT.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            continue
        while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
            tokens.pop(0)  # VAR=value prefixes
        if not tokens or Path(tokens[0]).name != "git":
            continue
        repo, i = cwd, 1
        while i < len(tokens) and tokens[i].startswith("-"):
            if tokens[i] == "-C" and i + 1 < len(tokens):
                repo = (cwd / tokens[i + 1]).resolve()
                i += 2
            elif tokens[i] == "-c" and i + 1 < len(tokens):
                i += 2
            else:
                i += 1
        if i < len(tokens) and tokens[i] == "push":
            rest = tokens[i + 1 :]
            if "--dry-run" in rest or "-n" in rest or "--delete" in rest or "-d" in rest:
                return None
            return repo
    return None


def main() -> int:
    if (os.environ.get("L9_CI_PARITY") or "1").strip() == "0" or not claude_surface():
        return 0
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash" or not RUNNER.is_file():
        return 0
    command = str((event.get("tool_input") or {}).get("command") or "")
    repo = push_target(command, Path(str(event.get("cwd") or os.getcwd())))
    if repo is None:
        return 0
    wait = float(os.environ.get("L9_CI_PARITY_WAIT") or DEFAULT_WAIT)
    try:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--gate", "HEAD", "--workspace", str(repo)],
            capture_output=True,
            text=True,
            timeout=wait + 120,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print(
            "ci-parity: push gate timed out — allowing; CI remains authoritative", file=sys.stderr
        )
        return 0
    if proc.returncode == 2:
        print(proc.stdout.strip(), file=sys.stderr)
        print(
            "ci-parity: push blocked — fix the BLOCK findings above (CI would fail on them). "
            "Kill switch for a false positive: L9_CI_PARITY=0.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
