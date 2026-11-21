#!/usr/bin/env python3
"""Deny shared-worktree git ops that scoop or destroy foreign dirty work.

Incident (2026-08-12): parallel agent on the same Cursor-Governance working
tree ran unscoped ``git add`` of dirty files (including another chat's
``commands/plan.md`` v2.0.0), committed them as a "style" commit, then
``git revert`` — restoring plan.md to v1.2.0 and erasing in-flight work.

Same day: parallel agents kept ``git checkout`` / ``git reset`` thrashing the
primary clone, wiping untracked fix files mid-session.

Destructive-effect classification (which forced clean is safe, which is not)
belongs to ``git_guardrails`` — this module keeps the incident-specific rules
(foreign-work scoops, never-lose scratch holds) and delegates the rest.

Brain lives under ops/ per CANONICAL_LAW §2.1. Invoked from
``local_execution_gate.py`` (Cursor beforeShellExecution + Claude PreToolUse).

Escape hatches (human / ops only):
  L9_GIT_REVERT_AUTHORIZED=<reason>
  L9_GIT_BROAD_ADD_AUTHORIZED=<reason>
  L9_GIT_SWITCH_AUTHORIZED=<reason>
  L9_GIT_RESET_AUTHORIZED=<reason>
  L9_WORKTREE_ISOLATION=0
  L9_GIT_CLEAN_AUTHORIZED=<reason>
  L9_WORKTREE_ADD_AUTHORIZED=<reason>
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    git_toplevel,
    segment_head,
    segment_words,
    segments_with_directories,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)
from git_guardrails import command_requires_human  # noqa: E402

# Broad add forms that scoop the whole dirty tree.
_BROAD_ADD_SHORT = re.compile(
    # A combined short flag (-uv, -vA) stages everything just as -u / -A does.
    r"\bgit\s+add\s+(?:(?:-[A-Za-z]+|--[a-z-]+)\s+)*-[A-Za-z]*[Au][A-Za-z]*\b",
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

#: Pathspecs that name the whole tree; they never narrow a broad add.
_WIDE_PATHSPECS = frozenset({".", "./", ":", ":/", ":/.", "*", "**", "/"})
#: git global options that consume the following word.
_GIT_OPTIONS_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})
_STAGE_ALL_LONG = frozenset({"--all", "--update", "--no-ignore-removal"})


def _git_add_args(segment: str) -> list[str] | None:
    """Arguments after ``git [global options] add`` in *segment*, else ``None``."""
    words = segment_words(segment)
    if "git" not in words:
        return None
    index = words.index("git") + 1
    while index < len(words) and words[index].startswith("-"):
        index += 2 if words[index] in _GIT_OPTIONS_WITH_VALUE else 1
    if index >= len(words) or words[index] != "add":
        return None
    return words[index + 1 :]


def _add_segment_is_broad(args: list[str]) -> bool:
    """True when this ``git add`` stages beyond explicitly named paths."""
    stage_all = False
    paths: list[str] = []
    after_separator = False
    for arg in args:
        if after_separator:
            paths.append(arg)
        elif arg == "--":
            after_separator = True
        elif arg.startswith("--"):
            stage_all = stage_all or arg in _STAGE_ALL_LONG
        elif arg.startswith("-") and arg != "-":
            stage_all = stage_all or "A" in arg[1:] or "u" in arg[1:]
        else:
            paths.append(arg)
    if any(path in _WIDE_PATHSPECS for path in paths):
        return True
    return stage_all and not paths


def _broad_add_is_pathspec_scoped(command: str) -> bool:
    """A broad-add flag is harmless when every add names only explicit paths.

    ``git add -u -- a.py b.py`` stages modifications to exactly those tracked
    paths, which is what the denial message itself asks for. Fail closed: when
    a broad pattern matched but no plain ``git add`` segment can be parsed
    (a ``bash -c`` wrapper, say), the command is not treated as scoped.
    """
    scoped = False
    for segment in split_segments(strip_heredoc_bodies(command)):
        args = _git_add_args(segment)
        if args is None:
            continue
        if _add_segment_is_broad(args):
            return False
        scoped = True
    if not scoped:
        return False
    # Every broad-pattern hit must sit inside a parsed, scoped add segment.
    return not any(
        pattern.search(segment) and _git_add_args(segment) is None
        for segment in split_segments(strip_heredoc_bodies(command))
        for pattern in (_BROAD_ADD_SHORT, _BROAD_ADD_LONG, _BROAD_ADD_DOT)
    )


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


# Never-lose scratch: forced cleans answer the guardrail; public-temp holds are denied.
_TMP_PUBLIC = bytes((0x2F, 0x74, 0x6D, 0x70, 0x2F)).decode("ascii")
_GIT_CLEAN_FORCE = re.compile(r"\bgit\s+clean\b(?:\s+-\S+)*\s+-(?:f|fd|fdx|df|dfx)\b", re.I)
_TMP_HOLD_CREATE = re.compile(
    r"(?:\bmkdir\b|\bmktemp\b)\s+\S*(?:cg-\S*hold|untracked-hold)|"
    + re.escape(_TMP_PUBLIC)
    + r"(?:cg-\S*hold|\S*untracked-hold)",
    re.I,
)


def _is_wired_worktree_wrapper(command: str) -> bool:
    return "worktree_add_wired.sh" in command


def _is_raw_worktree_add(command: str) -> bool:
    """True for ``git worktree add`` including ``git -C <path> worktree add``."""
    words = segment_words(command)
    if not words:
        return False
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    if index >= len(words) or words[index] != "git":
        return False
    index += 1
    while index < len(words):
        word = words[index]
        if word in {"-C", "--git-dir", "--work-tree"}:
            index += 2
            continue
        if word.startswith("--git-dir=") or word.startswith("--work-tree="):
            index += 1
            continue
        if word.startswith("-") and word not in {"worktree"}:
            index += 1
            continue
        break
    return index + 1 < len(words) and words[index] == "worktree" and words[index + 1] == "add"


def _deny_raw_worktree_add(command: str) -> str | None:
    if _authorized("L9_WORKTREE_ADD_AUTHORIZED") or _is_wired_worktree_wrapper(command):
        return None
    if _is_raw_worktree_add(command):
        return (
            "shared-worktree isolation: raw git worktree add denied — "
            "the new folder has no .cursor links. Use "
            "ops/scripts/worktree_add_wired.sh or set "
            "L9_WORKTREE_ADD_AUTHORIZED=<reason>."
        )
    return None


#: git options that precede the subcommand and take a separate value.
_GIT_GLOBAL_WITH_ARG = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})


def _without_git_globals(segment: str) -> str:
    """``git -C <dir> -c k=v checkout x`` as ``git checkout x``.

    Every matcher below expects the subcommand right after ``git``, so before
    this a ``git -C <repo> checkout|reset|revert|add -A`` slipped past the whole
    gate (found while fixing #971). Global options never change which
    subcommand runs; the repository they name is resolved separately.
    """
    import shlex

    words = segment_words(segment)
    head = 0
    while head < len(words) and "=" in words[head] and not words[head].startswith("-"):
        head += 1
    if head >= len(words) or PurePosixPath(words[head]).name != "git":
        return segment
    index = head + 1
    while index < len(words) and words[index].startswith("-"):
        word = words[index]
        index += 2 if word in _GIT_GLOBAL_WITH_ARG else 1
    if index == head + 1:
        return segment
    return shlex.join([*words[: head + 1], *words[index:]])


def _deny_shared_git(command: str, *, dirty: bool) -> str | None:
    # Subcommand-position checks: only argv[1] can trigger revert/reset, so a
    # commit message like `git commit -m "mention git revert"` never matches.
    command = _without_git_globals(command)
    words = segment_words(command)
    subcommand = words[1] if len(words) > 1 else None
    if subcommand == "revert" and not _authorized("L9_GIT_REVERT_AUTHORIZED"):
        return (
            "shared-worktree isolation: git "
            "revert denied (destroyed in-flight commands/plan.md on 2026-08-12). "
            "Set L9_GIT_REVERT_AUTHORIZED=<reason> only after confirming the "
            "target commit has no foreign/out-of-scope paths, or use a "
            "dedicated git worktree per parallel agent."
        )
    if dirty and subcommand == "reset" and not _authorized("L9_GIT_RESET_AUTHORIZED"):
        return (
            "shared-worktree isolation: git reset denied while the worktree is "
            "dirty (wipes parallel agents dirty/untracked work). Use a git "
            "worktree, or set L9_GIT_RESET_AUTHORIZED=<reason>."
        )
    if dirty and _is_branch_switch(command) and not _authorized("L9_GIT_SWITCH_AUTHORIZED"):
        return (
            "shared-worktree isolation: branch checkout/switch denied while the "
            "worktree is dirty (2026-08-12 thrash wiped in-flight files). "
            "Use a dedicated worktree for parallel branches, or set "
            "L9_GIT_SWITCH_AUTHORIZED=<reason>."
        )
    if _is_diff_name_pipe_add(command) and not _authorized("L9_GIT_BROAD_ADD_AUTHORIZED"):
        return (
            "shared-worktree isolation: piping name-only diff into staging "
            "denied — that scoops parallel agents dirty files. Stage an explicit "
            "allowlist of paths you authored, or set L9_GIT_BROAD_ADD_AUTHORIZED=<reason>."
        )
    if (
        (
            _BROAD_ADD_SHORT.search(command)
            or _BROAD_ADD_LONG.search(command)
            or _BROAD_ADD_DOT.search(command)
        )
        and not _authorized("L9_GIT_BROAD_ADD_AUTHORIZED")
        and not _broad_add_is_pathspec_scoped(command)
    ):
        return (
            "shared-worktree isolation: broad staging (-A/--all/./-u without "
            "pathspecs) denied — scoops foreign dirty work on shared clones. "
            "Stage explicit paths, use a dedicated worktree, or set "
            "L9_GIT_BROAD_ADD_AUTHORIZED=<reason>."
        )
    return None


def _deny_never_lose_scratch(command: str, *, root: Path | None = None) -> str | None:
    if _GIT_CLEAN_FORCE.search(command) and not _authorized("L9_GIT_CLEAN_AUTHORIZED"):
        # Rule 49 used to deny every forced clean by flag alone. Under the
        # context-sensitive guardrail contract the target set decides: a clean
        # whose `git clean -nd` preflight lists only build output and caches
        # destroys nothing, while one that would take an untracked file nobody
        # can prove disposable still fails closed. git_guardrails runs that
        # preflight and returns the deny reason.
        return command_requires_human(command, root=root)
    if _TMP_HOLD_CREATE.search(command):
        return (
            "never-lose scratch: creating public-temp cg-*-hold* or *untracked-hold* "
            "denied. Park scratch via ops/scripts/scratch_hold.py "
            "(.l9/scratch-hold/)."
        )
    return None


def _git_command_segments(command: str) -> list[str]:
    """Segments that ARE git commands, including wrapper-nested ones.

    Heredoc bodies are stripped first (they are data, not commands); quoted
    spans are preserved, so a real ``bash -c 'git revert …'`` still surfaces
    via the wrapper descent.
    """
    segments: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        if segment_head(segment) == "git":
            segments.append(segment)
        for nested in wrapper_subcommands(segment):
            if segment_head(nested) == "git":
                segments.append(nested)
    return segments


def command_violates_worktree_isolation(command: str, *, root: Path | None = None) -> str | None:
    """Return deny reason if command is a known foreign-work destroyer."""
    if isolation_disabled() or not command.strip():
        return None
    sanitized = strip_heredoc_bodies(command)
    # #971/#961: a segment's dirt is the dirt of the repository it runs in. A
    # `cd <scratch clone> && git checkout --detach <sha>` was judged by the
    # session checkout's dirt and refused. Unknown targets keep the session root.
    targets: dict[str, list[Path | None]] = {}
    for segment, directory in segments_with_directories(command, root):
        if segment_head(segment) == "git":
            targets.setdefault(segment, []).append(directory)
    dirt: dict[Path | None, bool] = {}

    def dirty_for(segment: str) -> bool:
        # The same text can run in several repositories; any dirty one counts.
        verdict = False
        for directory in targets.get(segment) or [root]:
            repo = root
            if directory is not None and directory != root:
                repo = git_toplevel(directory) or root
            if repo not in dirt:
                dirt[repo] = _working_tree_dirty(repo)
            verdict = verdict or dirt[repo]
        return verdict

    # Never-lose scratch patterns (forced clean, public-temp hold creation) span
    # whole pipelines and match the sanitized full text; git-subcommand patterns
    # match per git segment so message text in unrelated segments can never trip
    # them. The diff-pipe scoop loop is inherently cross-segment and keeps the
    # full-text check.
    for segment in _git_command_segments(command):
        reason = _deny_shared_git(segment, dirty=dirty_for(segment))
        if reason:
            return reason
        reason = _deny_raw_worktree_add(segment)
        if reason:
            return reason
    reason = _deny_raw_worktree_add(sanitized)
    if reason:
        return reason
    if _is_diff_name_pipe_add(sanitized) and not _authorized("L9_GIT_BROAD_ADD_AUTHORIZED"):
        return (
            "shared-worktree isolation: piping name-only diff into staging "
            "denied — that scoops parallel agents dirty files. Stage an explicit "
            "allowlist of paths you authored, or set L9_GIT_BROAD_ADD_AUTHORIZED=<reason>."
        )
    return _deny_never_lose_scratch(sanitized, root=root)
