#!/usr/bin/env python3
"""CI-parity feedback at the two cheapest moments: after an edit, after a commit.

Registered `--class observer` on PostToolUse (Edit|Write|MultiEdit|NotebookEdit|Bash).

* Edit / Write: runs the fast lanes (shellcheck, actionlint, zizmor, yamllint,
  biome, ruff) on the edited file and returns findings on the lines just
  changed as `additionalContext`, so they are fixed before anything is pushed.
* Bash: when HEAD moved since the last call (a commit, amend, merge — however
  it was spelled), starts the heavy lanes (CodeQL, Semgrep, osv-scanner) for
  the new commit in the background. The push gate and make pr reuse those
  receipts. A `git push` also refreshes the SonarCloud PR read in the background.

Never blocks, never writes inside the worktree. Silent on non-Claude surfaces
and when L9_CI_PARITY=0. See ops/ci_parity/README.md.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

GOV = Path(__file__).resolve().parents[5]
RUNNER = GOV / "ops" / "ci_parity" / "run.py"
SONAR = GOV / "ops" / "ci_parity" / "sonar_status.py"
for _path in (GOV / "ops" / "autonomy", GOV / "ops" / "ci_parity"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

EDIT_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
FILE_TIMEOUT = 12
_PUSH = re.compile(r"(?:^|[;&|(]\s*)git(?:\s+-C\s+\S+|\s+-c\s+\S+)*\s+push\b")


def claude_surface() -> bool:
    try:
        import surface_detect  # noqa: PLC0415
    except ImportError:
        return False
    return bool(surface_detect.is_claude_gate_surface())


def disabled() -> bool:
    return (os.environ.get("L9_CI_PARITY") or "1").strip() == "0"


def _emit(text: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}
        )
    )


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _detach(argv: list[str], log: Path) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as handle:
        subprocess.Popen(
            argv, stdout=handle, stderr=handle, stdin=subprocess.DEVNULL, start_new_session=True
        )


def on_edit(tool_input: dict[str, Any]) -> None:
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path or not Path(str(path)).is_file():
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), "--file", str(path)],
            capture_output=True,
            text=True,
            timeout=FILE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return
    if proc.stdout.strip():
        _emit(proc.stdout.strip())


def on_bash(event: dict[str, Any]) -> None:
    cwd = Path(str(event.get("cwd") or os.getcwd()))
    top = _git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return
    head = _git(Path(top), "rev-parse", "HEAD")
    if not head:
        return
    import manifest  # noqa: PLC0415

    loaded = manifest.load()
    slug_dir = loaded.cache_root / _slug(Path(top)).replace("/", "__")
    marker = slug_dir / "last-head"
    try:
        seen = marker.read_text(encoding="utf-8").strip()
    except OSError:
        seen = ""
    if head != seen:
        slug_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(head + "\n", encoding="utf-8")
        if seen:  # first sight of a repo is a baseline, not a commit
            _detach(
                [sys.executable, str(RUNNER), "--commit", head, "--background", "--workspace", top],
                slug_dir / "commit.log",
            )
    command = str((event.get("tool_input") or {}).get("command") or "")
    if _PUSH.search(command) and SONAR.is_file():
        _detach([sys.executable, str(SONAR), "--auto", "--workspace", top], slug_dir / "sonar.log")


def _slug(repo: Path) -> str:
    url = _git(repo, "remote", "get-url", "origin").rstrip("/").removesuffix(".git")
    parts = url.replace(":", "/").split("/")
    return f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 and parts[-1] else f"local/{repo.name}"


def main() -> int:
    if disabled() or not claude_surface() or not RUNNER.is_file():
        return 0
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    tool = str(event.get("tool_name") or "")
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    try:
        if tool in EDIT_TOOLS:
            on_edit(tool_input)
        elif tool == "Bash":
            on_bash(event)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0  # an observer never turns a scanner fault into a tool failure
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
