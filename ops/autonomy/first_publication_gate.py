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
import subprocess
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

#: `git push` options that consume the following token when written without
#: `=`. Anything else that starts with `-` is a bare flag.
_PUSH_OPTS_WITH_ARG = frozenset(
    {"-o", "--push-option", "--receive-pack", "--exec", "--recurse-submodules", "--signed"}
)

#: `gh` options that consume the following token. `-R/--repo` is the one that
#: matters for publication: `gh -R owner/name pr create` is the repository's
#: own documented spelling (test_pe_local_commit_only), and a filter that only
#: dropped dash-tokens left `owner/name` in front of `pr create` and missed it
#: (audit F1).
_GH_OPTS_WITH_ARG = frozenset({"-R", "--repo", "--hostname"})


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


#: Fallback builtin list, used only when `git --list-cmds=builtins` cannot be
#: read. Any word not in the live/fallback set is treated as a possible alias
#: and resolved through git config, never assumed harmless.
_BUILTIN_FALLBACK = frozenset(
    """add am annotate apply archive bisect blame branch bundle cat-file checkout
    cherry cherry-pick clean clone commit config describe diff difftool fetch
    format-patch fsck gc grep help init log ls-files ls-remote ls-tree merge
    merge-base mv notes pull push range-diff rebase reflog remote repack replace
    reset restore rev-list rev-parse revert rm send-pack shortlog show
    show-branch show-ref sparse-checkout stash status submodule switch
    symbolic-ref tag update-ref var verify-commit verify-tag version whatchanged
    worktree write-tree""".split()
)

_builtins_cache: frozenset[str] | None = None


def _git_builtins() -> frozenset[str]:
    """The names git itself owns; everything else is an alias or an external git-*."""
    global _builtins_cache  # noqa: PLW0603 - process-wide cache of an immutable fact
    if _builtins_cache is not None:
        return _builtins_cache
    names: set[str] = set(_BUILTIN_FALLBACK)
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "--list-cmds=builtins"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if proc.returncode == 0:
            names.update(word for word in proc.stdout.split() if word)
    except (OSError, subprocess.SubprocessError):
        # Live builtin list is unavailable; keep the static fallback.
    _builtins_cache = frozenset(names)
    return _builtins_cache


def _git_invocation(words: list[str]) -> tuple[list[str], dict[str, Any]]:
    """(argv after git's global options, invocation context) for a `git …` word list.

    The context is what decides WHICH repository the command acts on and HOW
    its subcommand resolves — the two things the re-audit (F2) showed a
    syntax-only parser losing:

    * ``named_root`` (-C), ``git_dir`` (--git-dir / GIT_DIR) and ``work_tree``
      (--work-tree / GIT_WORK_TREE): repository selectors. A push under any of
      them acts on THAT repository, so the open-PR probe must ask that
      repository, not the ambient one.
    * ``aliases``: ``-c alias.NAME=VALUE`` definitions on the command line,
      which make ``git p …`` a push.
    """
    context: dict[str, Any] = {
        "named_root": None,
        "git_dir": None,
        "work_tree": None,
        "aliases": {},
    }
    index = 0
    # Leading environment assignments (`GIT_DIR=… git push`) select a
    # repository exactly like the global options do.
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        key, _, value = words[index].partition("=")
        if key == "GIT_DIR":
            context["git_dir"] = value
        elif key == "GIT_WORK_TREE":
            context["work_tree"] = value
        index += 1
    index += 1  # the `git` executable itself
    while index < len(words):
        word = words[index]
        base, has_value, value = word.partition("=")
        if base in _GIT_GLOBAL_WITH_ARG:
            if not has_value:
                value = words[index + 1] if index + 1 < len(words) else ""
                index += 2
            else:
                index += 1
            if base == "-C":
                previous = context["named_root"]
                if previous is None or os.path.isabs(value):
                    context["named_root"] = value
                else:
                    context["named_root"] = os.path.join(previous, value)
            elif base == "--git-dir":
                context["git_dir"] = value
            elif base == "--work-tree":
                context["work_tree"] = value
            elif base == "-c":
                key, _, setting = value.partition("=")
                if key.lower().startswith("alias."):
                    context["aliases"][key[len("alias.") :]] = setting
            continue
        if word.startswith("-"):
            index += 1
            continue
        break
    return words[index:], context


def _config_alias(root: Path | None, name: str) -> tuple[str, str | None]:
    """(state, expansion) for a git-config alias: 'alias', 'none' or 'unreadable'."""
    argv = ["git"]
    if root is not None:
        argv += ["-C", str(root)]
    argv += ["config", "--get", f"alias.{name}"]
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "unreadable", None
    if proc.returncode == 0:
        return "alias", proc.stdout.strip()
    if proc.returncode == 1:
        return "none", None
    return "unreadable", None


def _resolve_subcommand(
    argv: list[str], context: dict[str, Any], root: Path | None
) -> tuple[str | None, list[str], str | None]:
    """(effective subcommand, its args, undeterminable-reason).

    A word that is not a git builtin is resolved as an alias — first from the
    command line (``-c alias.p=push``), then from git config in the targeted
    repository — up to a small depth. An alias whose expansion is a shell
    command (``!…``) can do anything, including push, and its effect cannot be
    read from here: that is undeterminable and the caller fails closed. A word
    that is neither builtin nor alias is an external ``git-<word>`` helper and
    publishes no ref of this repository.
    """
    if not argv:
        return None, [], None
    name, args = argv[0], argv[1:]
    builtins = _git_builtins()
    for _ in range(4):
        if name in builtins:
            return name, args, None
        expansion = context["aliases"].get(name)
        if expansion is None:
            state, expansion = _config_alias(root, name)
            if state == "unreadable":
                return None, [], f"git alias {name!r} could not be resolved (git config unreadable)"
            if state == "none":
                return name, args, None
        expansion = str(expansion or "").strip()
        if expansion.startswith("!"):
            return None, [], f"git alias {name!r} expands to a shell command"
        expanded = _split_words(expansion)
        if not expanded:
            return name, args, None
        name, args = expanded[0], expanded[1:] + args
    return None, [], f"git alias {argv[0]!r} did not resolve within the expansion limit"


def _refspec_branch(refspec: str) -> str | None:
    """The remote branch a push refspec publishes, or None when it publishes none.

    ``src``, ``src:dst``, ``+src:dst`` and ``HEAD:refs/heads/x`` all name a
    destination; ``:dst`` deletes it. The remote-side name is what a PR is
    open for, so ``dst`` wins over ``src`` and ``refs/heads/`` is stripped.
    """
    text = refspec[1:] if refspec.startswith("+") else refspec
    if not text or text.startswith(":"):
        return None
    dst = text.split(":", 1)[1] if ":" in text else text
    if not dst:
        return None
    if dst.startswith("refs/heads/"):
        dst = dst[len("refs/heads/") :]
    return dst


def _classify_push(args: list[str]) -> list[dict[str, Any]]:
    """Every publication a `git push …` argument list performs.

    One entry per refspec: ``git push origin open-pr-branch new-branch`` is two
    publications, and the verdict must see both — a parser that kept only the
    first refspec let the second branch reach GitHub behind a remediation
    push (audit F1). No refspec means the current branch (git's default
    ``push.default`` behaviours all publish the checked-out branch or nothing).
    A dry run, a delete, and a bare `git push` with `--delete` publish nothing.
    """
    positional: list[str] = []
    delete = False
    index = 0
    while index < len(args):
        arg = args[index]
        base = arg.split("=", 1)[0]
        if base in {"-n", "--dry-run"}:
            return []
        if base in _PUSH_WHOLE_REPO_FLAGS:
            return [{"remote": None, "branch": None, "whole_repo": base}]
        if base in {"--delete", "-d"}:
            delete = True
            index += 1
            continue
        if arg == "--":
            positional.extend(args[index + 1 :])
            break
        if arg.startswith("-"):
            if base in _PUSH_OPTS_WITH_ARG and "=" not in arg:
                index += 2
            else:
                index += 1
            continue
        positional.append(arg)
        index += 1
    if delete:
        return []
    remote = positional[0] if positional else "origin"
    refspecs = positional[1:]
    if not refspecs:
        return [{"remote": remote, "branch": None, "whole_repo": None}]
    forms: list[dict[str, Any]] = []
    for refspec in refspecs:
        branch = _refspec_branch(refspec)
        if branch is None:
            continue
        forms.append({"remote": remote, "branch": branch, "whole_repo": None})
    return forms


def _gh_creates_pr(words: list[str]) -> bool:
    """True when a `gh …` word list runs `pr create`, wherever its options sit.

    Option-aware: a value-taking option (`-R owner/name`, `--repo owner/name`)
    consumes its value, and a `--opt=value` spelling is one token. The
    subcommand pair is then the first two positional words, or — for an
    option this list does not know — any two consecutive positional words:
    denying a `gh` command that carries `pr create` among its positionals is
    the safe direction.
    """
    positional: list[str] = []
    index = 1
    while index < len(words):
        word = words[index]
        if word.startswith("-"):
            base = word.split("=", 1)[0]
            if base in _GH_OPTS_WITH_ARG and "=" not in word:
                index += 2
            else:
                index += 1
            continue
        positional.append(word)
        index += 1
    return any(
        positional[position : position + 2] == ["pr", "create"]
        for position in range(len(positional) - 1)
    )


def publication_forms(command: str, root: Path | None = None) -> list[dict[str, Any]]:
    """Every publication a command would perform, in order.

    Each entry is ``{"form": "git push" | "git send-pack" | "gh pr create",
    ...}``; a push also carries ``remote``, ``branch`` (None = the current
    branch), the repository selectors ``named_root`` (``-C``), ``git_dir``
    (``--git-dir`` / ``GIT_DIR``) and ``work_tree`` (``--work-tree`` /
    ``GIT_WORK_TREE``), and ``whole_repo`` (a flag that publishes everything).
    A multi-refspec push yields one entry per refspec, so the verdict judges
    every branch the command would publish, not only the first. An alias whose
    effect cannot be read yields ``{"form": "git push", "undeterminable": …}``.

    Parsing is local, with one exception: a git word that is not a builtin is
    resolved as an alias through ``git config`` in the repository the command
    targets (``root`` when no selector overrides it), because
    ``git -c alias.p=push p …`` and a configured alias are pushes that a
    syntax-only parser cannot see (audit F2).
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
            if _gh_creates_pr(words):
                found.append({"form": "gh pr create"})
            continue
        argv, context = _git_invocation(words)
        selectors = {key: context[key] for key in ("named_root", "git_dir", "work_tree")}
        subcommand, args, undeterminable = _resolve_subcommand(
            argv, context, _bind_root(selectors, root)[0]
        )
        if undeterminable:
            found.append({"form": "git push", "undeterminable": undeterminable, **selectors})
            continue
        if subcommand == "send-pack":
            found.append({"form": "git send-pack", "whole_repo": "send-pack", **selectors})
            continue
        if subcommand != "push":
            continue
        for push in _classify_push(args):
            push["form"] = "git push"
            push.update(selectors)
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


_DYNAMIC_PATH_CHARS = "$`()*?[]{}"


def _static_dir(raw: str, base: Path | None) -> Path | None:
    """A repository selector as an existing directory, or None when it cannot be pinned.

    Dynamic tokens (`$VAR`, globs, substitutions) are never widened into a
    path: the gate cannot know what they expand to, so they are unresolvable.
    """
    if any(ch in raw for ch in _DYNAMIC_PATH_CHARS):
        return None
    try:
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            candidate = (base if base is not None else Path.cwd()) / candidate
        candidate = candidate.resolve()
    except (OSError, ValueError, RuntimeError):
        return None
    return candidate if candidate.is_dir() else None


def _bind_root(selectors: dict[str, Any], ambient: Path | None) -> tuple[Path | None, bool]:
    """(repository the command acts on, whether a selector named it).

    ``--work-tree`` names the work tree outright; ``--git-dir`` names the
    repository (its parent when it is a ``.git`` directory, itself when bare);
    ``-C`` changes the directory git starts in. Any selector that is present
    but does not resolve leaves the repository unknown — the caller must fail
    closed rather than fall back to the ambient checkout, which is exactly the
    wrong-repository authorization the re-audit (F2) described.
    """
    base = ambient
    named = selectors.get("named_root")
    if named:
        base = _static_dir(str(named), ambient)
        if base is None:
            return None, True
    work_tree = selectors.get("work_tree")
    if work_tree:
        return _static_dir(str(work_tree), base), True
    git_dir = selectors.get("git_dir")
    if git_dir:
        resolved = _static_dir(str(git_dir), base)
        if resolved is None:
            return None, True
        return (resolved.parent if resolved.name == ".git" else resolved), True
    if named:
        return base, True
    return ambient, False


def _resolve_push_root(push: dict[str, Any], root: Path | None) -> Path | None:
    return _bind_root(push, root)[0]


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
        forms = publication_forms(command, root=root)
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
        if form.get("undeterminable"):
            return _deny("git <alias>", f"its effect is undeterminable: {form['undeterminable']}")
        if form.get("whole_repo"):
            what = form["form"] if form["form"] != "git push" else f"git push {form['whole_repo']}"
            return _deny(what, "it publishes every ref at once")
        push_root, selected = _bind_root(form, root)
        if selected and push_root is None:
            return _deny(
                "git push",
                "the repository named by --git-dir/--work-tree/-C/GIT_DIR could not be resolved",
            )
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
