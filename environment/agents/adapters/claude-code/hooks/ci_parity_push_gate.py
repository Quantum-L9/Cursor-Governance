#!/usr/bin/env python3
"""PreToolUse observer that no longer scans a push.

Registered on PreToolUse (Bash) as `--class observer`. It used to wait up to
600 seconds on a whole-tree scan, which made Claude's `make pr` a different
ceremony from Cursor's. CI remains the CodeQL and Semgrep authority. This
file stays registered so a missing hook still fails open through the
launcher; it does not start a scan.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

_SEGMENT = re.compile(r"&&|\|\||[;|\n]")


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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
