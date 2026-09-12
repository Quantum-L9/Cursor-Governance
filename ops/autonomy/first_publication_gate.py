#!/usr/bin/env python3
"""Publication plane: a *first* publication happens only through ``make pr``.

CANONICAL_LAW §6.2.4 removed name-based gating of ``git``/``gh``: a command is
judged by its effect, never by its spelling. This plane is the effect-based
answer to audit finding R1, and §6.2.8 is its doctrine. It asks one question of
a ``git push`` or ``gh pr create``:

    does this command publish a branch that has no open pull request?

* **Yes → denied.** That is a first publication, and the only route that runs
  the checkers, the overlap gate, the main-bound gate and the L4 receipt check
  before it reaches GitHub is ``PR_REMEDIATE=0 make pr``
  (``ops/scripts/open_pr_after_gate.sh``). A raw push there skips all of it.
* **No (an open PR exists) → allowed.** Advancing an already-open PR is the
  remediator path (rule 48: ``make precommit-repo`` then ``git push``), and it
  stays a plain git command.
* **Cannot tell → denied.** No ``gh``, no network, no GitHub remote, unreadable
  branch: the collision and review state of the push is undeterminable, so it
  fails closed — the same rule the overlap gate applies (E6). ``make pr`` is
  always available as the sanctioned alternative.

Everything else git does is untouched: read-only git, commits, fetches,
deletes, dry runs, and pushes that are not publications never reach the probe
and never earn a denial here. Destructive effect stays with ``git_guardrails``.

Human/ops breakglass: ``L9_LOCAL_PUSH_AUTHORIZED=<reason>`` or a scoped
expiring publish-path receipt (``ops/autonomy/breakglass_receipt.py``).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    segment_head,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)

PUSH_BREAKGLASS_ENV = "L9_LOCAL_PUSH_AUTHORIZED"

#: Last-resort detector, used only when structural parsing itself fails. A
#: parse fault on a command that names a publication must deny, never allow.
_PUBLISH_TEXT_RE = re.compile(r"\bgit\s+push\b|\bgh\s+pr\s+create\b", re.I)

#: `git` global options that consume the following token.
_GIT_GLOBAL_WITH_ARG = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})

#: Push forms that publish every branch (or tag) at once. There is no single
#: branch whose PR could make them remediation, so they are first publications.
_PUSH_WHOLE_REPO_FLAGS = frozenset({"--all", "--mirror", "--tags", "--follow-tags"})


def _publish_path_override() -> str:
    try:
        from breakglass_receipt import active_publish_path_reason
    except ImportError:  # pragma: no cover - package import
        from ops.autonomy.breakglass_receipt import active_publish_path_reason
    return active_publish_path_reason()


def breakglass_reason() -> str | None:
    """Human/ops authorization that waives this plane, or None."""
    env = os.environ.get(PUSH_BREAKGLASS_ENV, "").strip()
    if env:
        return f"{PUSH_BREAKGLASS_ENV} breakglass"
    receipt = _publish_path_override()
    if receipt:
        return f"publish-path receipt: {receipt}"
    return None


def _split_words(segment: str) -> list[str]:
    import shlex

    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _git_argv(words: list[str]) -> tuple[list[str], str | None]:
    """(subcommand + its args, -C path) for a `git ...` word list."""
    index = 1
    named_root: str | None = None
    while index < len(words):
        word = words[index]
        if word in _GIT_GLOBAL_WITH_ARG:
            if word == "-C" and index + 1 < len(words):
                named_root = words[index + 1]
            index += 2
            continue
        if word.startswith("-"):
            index += 1
            continue
        break
    return words[index:], named_root


def _classify_push(args: list[str]) -> dict[str, Any] | None:
    """What a `git push …` argument list publishes, or None when it is no publication."""
    try:
        from git_guardrails import _parse_push
    except ImportError:  # pragma: no cover - package import
        from ops.autonomy.git_guardrails import _parse_push

    for arg in args:
        base = arg.split("=", 1)[0]
        if base in {"-n", "--dry-run"}:
            return None
        if base in _PUSH_WHOLE_REPO_FLAGS:
            return {"remote": None, "branch": None, "whole_repo": base}
    spec = _parse_push(args)
    if spec.delete:
        return None
    return {"remote": spec.remote, "branch": spec.branch, "whole_repo": None}


def publication_forms(command: str) -> list[dict[str, Any]]:
    """Every publication a command would perform, in order. Pure parsing, no I/O.

    Each entry is ``{"form": "git push" | "gh pr create", ...}``; a push also
    carries ``remote``, ``branch`` (None = the current branch), ``named_root``
    (a ``git -C`` path) and ``whole_repo`` (a flag that publishes everything).
    """
    found: list[dict[str, Any]] = []
    segments: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        segments.append(segment)
        segments.extend(wrapper_subcommands(segment))
    for segment in segments:
        head = segment_head(segment)
        if head is None:
            continue
        name = PurePosixPath(head).name
        if name not in {"git", "gh"}:
            continue
        words = _split_words(segment)
        if not words:
            continue
        if name == "gh":
            rest = [word for word in words[1:] if not word.startswith("-")]
            if rest[:2] == ["pr", "create"]:
                found.append({"form": "gh pr create"})
            continue
        argv, named_root = _git_argv(words)
        if not argv or argv[0] != "push":
            continue
        push = _classify_push(argv[1:])
        if push is None:
            continue
        push["form"] = "git push"
        push["named_root"] = named_root
        found.append(push)
    return found


def _deny(what: str, detail: str) -> str:
    return (
        f"Publication plane: `{what}` would be a FIRST publication ({detail}). "
        "First publication goes through `PR_REMEDIATE=0 make pr`, which runs the "
        "checkers, the overlap and main-bound gates and the L4 release check before "
        "it pushes and opens the PR (ops/scripts/open_pr_after_gate.sh). A push that "
        "advances a branch with an OPEN pull request stays allowed (remediation). "
        f"Human/ops breakglass: {PUSH_BREAKGLASS_ENV}=<reason> or a scoped receipt via "
        "ops/autonomy/breakglass_receipt.py (CANONICAL_LAW §6.2.8)."
    )


def _resolve_push_root(push: dict[str, Any], root: Path | None) -> Path | None:
    named = push.get("named_root")
    if named:
        try:
            candidate = Path(os.path.expandvars(str(named))).expanduser()
            if not candidate.is_absolute() and root is not None:
                candidate = root / candidate
            candidate = candidate.resolve()
        except (OSError, ValueError):
            return None
        return candidate if candidate.is_dir() else None
    return root


def _open_pr(root: Path | None, branch: str | None, remote: str | None) -> bool | None:
    try:
        from l4_local import current_branch
        from open_pr_probe import open_pr_for_branch
    except ImportError:  # pragma: no cover - package import
        from ops.autonomy.l4_local import current_branch
        from ops.autonomy.open_pr_probe import open_pr_for_branch
    if root is None:
        return None
    # `git push origin HEAD` names the checked-out branch; a detached HEAD has
    # no branch and therefore no PR to advance.
    target = branch if branch and branch != "HEAD" else current_branch(root)
    if not target or target == "HEAD":
        return None
    return open_pr_for_branch(root, target, remote=remote or "origin")


def first_publication_verdict(command: str, *, root: Path | None) -> str | None:
    """Deny reason when ``command`` performs a first publication, else None.

    Pure parsing decides whether the command publishes at all; only a command
    that does reaches the GitHub probe, so a read-only or local git command can
    never be delayed or denied by this plane. A probe that cannot answer denies.
    """
    if not command or not command.strip():
        return None
    try:
        forms = publication_forms(command)
    except Exception:  # noqa: BLE001 - a parse fault must not become an allow
        if _PUBLISH_TEXT_RE.search(command):
            return _deny("git push / gh pr create", "the command could not be parsed")
        return None
    if not forms:
        return None
    if breakglass_reason():
        return None
    for form in forms:
        if form["form"] == "gh pr create":
            return _deny("gh pr create", "it opens a pull request outside make pr")
        if form.get("whole_repo"):
            return _deny(f"git push {form['whole_repo']}", "it publishes every ref at once")
        push_root = _resolve_push_root(form, root)
        try:
            answer = _open_pr(push_root, form.get("branch"), form.get("remote"))
        except Exception as exc:  # noqa: BLE001 - probe fault is undeterminable state
            answer = None
            detail = f"open-PR state undeterminable: {type(exc).__name__}: {exc}"
        else:
            detail = "open-PR state undeterminable (gh/network/remote unavailable)"
        if answer is True:
            continue
        branch = form.get("branch") or "the current branch"
        if answer is False:
            detail = f"no open pull request for {branch!r}"
        return _deny("git push", detail)
    return None


__all__ = [
    "PUSH_BREAKGLASS_ENV",
    "breakglass_reason",
    "first_publication_verdict",
    "publication_forms",
]
