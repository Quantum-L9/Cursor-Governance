#!/usr/bin/env python3
"""Deny shared-worktree git ops that scoop or destroy foreign dirty work.

Incident (2026-08-12): parallel agent on the same Cursor-Governance working
tree ran unscoped ``git add`` of dirty files (including another chat's
``commands/plan.md`` v2.0.0), committed them as a "style" commit, then
``git revert`` — restoring plan.md to v1.2.0 and erasing in-flight work.

Same day: parallel agents kept ``git checkout`` / ``git reset`` thrashing the
primary clone, wiping untracked fix files mid-session.

Brain lives under ops/ per CANONICAL_LAW §2.1. Invoked from
``local_execution_gate.py`` (Cursor beforeShellExecution + Claude PreToolUse).

Escape hatches (human / ops only):
  L9_GIT_REVERT_AUTHORIZED=<reason>
  L9_GIT_BROAD_ADD_AUTHORIZED=<reason>
  L9_GIT_SWITCH_AUTHORIZED=<reason>
  L9_GIT_RESET_AUTHORIZED=<reason>
  L9_WORKTREE_ISOLATION=0
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Broad add forms that scoop the whole dirty tree.
_BROAD_ADD_SHORT = re.compile(
    r"\bgit\s+add\s+(?:(?:-[A-Za-z]+|--[a-z-]+)\s+)*-(?:A|u)\b",
    re.I,
)
_BROAD_ADD_LONG = re.compile(
    r"\bgit\s+add\s+(?:(?:-[A-Za-z]+|--[a-z-]+)\s+)*(?:--all|--update)\b",
    re.I,
)
_BROAD_ADD_DOT = re.compile(
    r"\bgit\s+add\s+(?:(?:-[A-Za-z]+|--[a-z-]+)\s+)*\.(?:\s|$)",
    re.I,
)

_REVERT = re.compile(r"\bgit\s+revert\b", re.I)
_RESET = re.compile(r"\bgit\s+reset\b", re.I)

# Branch moves (not path checkout `git checkout -- file`, not create -b).
_SWITCH = re.compile(r"\bgit\s+switch\b", re.I)
_CHECKOUT_BRANCH = re.compile(
    r"""
    \bgit\s+checkout\s+
    (?!
        (?:--\s+)                  # git checkout -- <paths>
      | (?:-[bB]\b)                # create branch
      | (?:--orphan\b)
      | (?:--\w[\w-]*\s+)*-[bB]\b
    )
    """,
    re.I | re.VERBOSE,
)

_DIFF_NAME = re.compile(r"\bgit\s+diff\b", re.I)
_ADD = re.compile(r"\bgit\s+add\b", re.I)


def isolation_disabled() -> bool:
    return os.environ.get("L9_WORKTREE_ISOLATION", "1").strip() in {"0", "false", "no"}


def _authorized(env_key: str) -> bool:
    return bool(os.environ.get(env_key, "").strip())


def _is_diff_name_pipe_add(command: str) -> bool:
    """True for ``git diff --name-only | while read; do git add`` scoop loops."""
    if "|" not in command:
        return False
    if not _DIFF_NAME.search(command) or not _ADD.search(command):
        return False
    return ("--name-only" in command) or ("--name-status" in command)


def _is_branch_switch(command: str) -> bool:
    if _SWITCH.search(command):
        # allow git switch -c / --create
        if re.search(r"\bgit\s+switch\s+(?:-[cC]\b|--create\b)", command, re.I):
            return False
        return True
    # Path restore from tree-ish: git checkout <ref> -- <paths>
    if re.search(r"\bgit\s+checkout\b[\s\S]*?\s--\s+\S", command, re.I):
        return False
    return bool(_CHECKOUT_BRANCH.search(command))


def _working_tree_dirty(root: Path | None) -> bool:
    """True when the git worktree has staged/unstaged/untracked changes."""
    if root is None or not (root / ".git").exists():
        return False
    proc = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    return bool(proc.stdout.strip())


def command_violates_worktree_isolation(
    command: str, *, root: Path | None = None
) -> str | None:
    """Return deny reason if command is a known foreign-work destroyer."""
    if isolation_disabled() or not command.strip():
        return None

    if _REVERT.search(command) and not _authorized("L9_GIT_REVERT_AUTHORIZED"):
        return (
            "shared-worktree isolation: git revert denied (destroyed in-flight "
            "commands/plan.md on 2026-08-12). Set L9_GIT_REVERT_AUTHORIZED=<reason> "
            "only after confirming the target commit has no foreign/out-of-scope "
            "paths, or use a dedicated git worktree per parallel agent."
        )

    dirty = _working_tree_dirty(root)

    if (
        dirty
        and _RESET.search(command)
        and not _authorized("L9_GIT_RESET_AUTHORIZED")
    ):
        return (
            "shared-worktree isolation: git reset denied while the worktree is "
            "dirty (wipes parallel agents' dirty/untracked work). Use a git "
            "worktree, or set L9_GIT_RESET_AUTHORIZED=<reason>."
        )

    if (
        dirty
        and _is_branch_switch(command)
        and not _authorized("L9_GIT_SWITCH_AUTHORIZED")
    ):
        return (
            "shared-worktree isolation: git checkout/switch denied while the "
            "worktree is dirty (2026-08-12 thrash wiped in-flight files). "
            "Use `git worktree add` for parallel branches, or set "
            "L9_GIT_SWITCH_AUTHORIZED=<reason>."
        )

    if _is_diff_name_pipe_add(command) and not _authorized("L9_GIT_BROAD_ADD_AUTHORIZED"):
        return (
            "shared-worktree isolation: piping git diff --name-only into git add "
            "denied — that scoops parallel agents' dirty files. Stage an explicit "
            "allowlist of paths you authored, or set L9_GIT_BROAD_ADD_AUTHORIZED=<reason>."
        )

    if (
        _BROAD_ADD_SHORT.search(command)
        or _BROAD_ADD_LONG.search(command)
        or _BROAD_ADD_DOT.search(command)
    ) and not _authorized("L9_GIT_BROAD_ADD_AUTHORIZED"):
        return (
            "shared-worktree isolation: broad git add (-A/--all/./-u without "
            "pathspecs) denied — scoops foreign dirty work on shared clones. "
            "Stage explicit paths, use a git worktree, or set "
            "L9_GIT_BROAD_ADD_AUTHORIZED=<reason>."
        )

    return None
