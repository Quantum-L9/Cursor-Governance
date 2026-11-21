"""Python entry to the ONE session git-exclude list in ``session_git_excludes.sh``.

A writer that materializes a governance mirror, a managed-commands manifest or
a memory record inside a clone must exclude that output in the SAME clone
before it writes. SessionStart applies the excludes to a single workspace — and
to none when that workspace is a multi-repository container, which is not a
git checkout — while the command, skill and memory writers fan out to every
repository in the container, including one attached after SessionStart ran.
Binding the exclude to the writer is what closes that gap.

This module carries no list of its own: it sources the shell library and calls
``apply_session_git_excludes``, so the shell file stays the single owner of
which paths are excluded. Same Option B contract as the library: entries go to
``$GIT_COMMON_DIR/info/exclude`` (local, uncommitted, shared by linked
worktrees); a tracked ``.gitignore`` is never touched (Option A, forbidden by
Cursor-Governance#281) and a blanket ``.claude/`` is refused by the library.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

#: The shell library this module delegates to; it owns the list.
LIBRARY = Path(__file__).resolve().with_suffix(".sh")


def apply_session_git_excludes(workspace: Path | str) -> bool:
    """Apply the session excludes to ``workspace``'s clone, idempotently.

    True when the excludes are in place or ``workspace`` is not a git checkout
    (nothing to exclude). False when the exclude file could not be written; the
    reason is printed to stderr. Callers keep writing either way — a missing
    exclude makes ``git status`` noisy, it must not cost the session its
    mirrors or memory latches — but the failure is never silent.
    """
    try:
        proc = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1" && apply_session_git_excludes "$2"',
                "_",
                str(LIBRARY),
                str(workspace),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(
            f"session_git_excludes: could not exclude session paths in {workspace}: {exc}",
            file=sys.stderr,
        )
        return False
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        print(
            f"session_git_excludes: could not exclude session paths in {workspace} "
            f"(rc={proc.returncode}) {detail}",
            file=sys.stderr,
        )
        return False
    return True
