#!/usr/bin/env python3
"""Deny mid-execution PR create until L4 release is authorized.

Also enforces shared-worktree isolation (scoop/revert/switch/reset of foreign
dirty files) via ``worktree_isolation_gate``.

``git`` and ``gh`` shell commands are EXEMPT from the *workflow* denials below
— publish-path, L4 phase, worktree isolation — see ``git_execution_exemption``.
The classifiers still report a raw publish, so a policy engine can say "you
bypassed `make pr`" after the fact; this gate no longer turns that report into
a blocked command.

That exemption is about workflow preference, not about destroying work, and it
is NOT a blanket allow of git: every shell command is first evaluated by
``git_guardrails`` (contract ``l9-context-sensitive-git-guardrails``), which
decides from the command's actual effect, target sensitivity, and provable
recoverability. Read-only git stays allowed unconditionally, a destructive
primitive over disposable state stays allowed, and only an unrecoverable
sensitive mutation is denied — to a human, not to a workflow phase.

Governed non-git commands and the MCP GitHub write tools are unaffected.

Claude Code PreToolUse adapter:
  environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py

Cursor beforeShellExecution adapter:
  ops/hooks/l4-local-execution-gate-shell.sh

Both adapters resolve this file through ``ops/autonomy/resolve_execution_gate.py``.
Do not add a third path lookup. A missing gate or a crashed evaluation is a
deny, never an implicit allow.

Brain lives under ops/ per CANONICAL_LAW §2.1.

Escape hatches (human / ops only):
  L9_GIT_DESTRUCTIVE_AUTHORIZED=<reason>
  L9_LOCAL_PUSH_AUTHORIZED=<reason>
  L9_L4_LOCAL_AUTONOMY=0
  L9_GIT_REVERT_AUTHORIZED=<reason>
  L9_GIT_BROAD_ADD_AUTHORIZED=<reason>
  L9_GIT_SWITCH_AUTHORIZED=<reason>
  L9_GIT_RESET_AUTHORIZED=<reason>
  L9_WORKTREE_ISOLATION=0
"""

from __future__ import annotations

import json
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
    extract_named_roots,
    segment_head,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)
from git_execution_exemption import (  # noqa: E402
    SHELL_TOOL_NAMES,
    event_is_git_or_gh,
    payload_is_git_or_gh,
)
from git_guardrails import command_requires_human  # noqa: E402
from l4_local import release_allows_remote, workspace_from_event  # noqa: E402
from worktree_isolation_gate import command_violates_worktree_isolation  # noqa: E402

#: git/gh forms that reach GitHub. `make` is NOT matched by regex here: see
#: MAKE_REMOTE_GOALS, because `\bmake\s+pr\b` also matches `make pr-check`.
REMOTE_BASH_PATTERNS = (
    re.compile(r"\bgit\s+push\b", re.I),
    re.compile(r"\bgh\s+pr\s+create\b", re.I),
    re.compile(r"\bgh\s+pr\s+edit\b", re.I),
)

#: Makefile goals that perform remote mutation, matched as exact goal tokens.
MAKE_REMOTE_GOALS = frozenset({"pr", "push"})

DENY_MCP_TOOLS = {
    "mcp__github__create_pull_request",
    "mcp__github__push_files",
    "create_pull_request",
    "push_files",
}

# ---------------------------------------------------------------------------
# Publish-path classification vs enforcement (CANONICAL_LAW §6.2.4).
#
# Campaign first publish still prefers `PR_REMEDIATE=0 make pr` (checkers, then
# open). Remediator publish of an already-open PR is `make precommit-repo`
# then `git push` (rule 48 / skill l9-pr-remediation). Classifiers still *name*
# a raw git/gh publish so a policy engine can report it afterwards.
#
# Enforcement does not deny git/gh forms — including when they share a shell
# with `make precommit-repo`, `cd`, or a pipe. The all-git exemption cannot
# see those compounds, and treating them as a publish-path deny is what
# blocked remediator velocity (F-14). Effect stays with git_guardrails
# (force-push, hard-reset, protected-branch rewrite).
#
# Still workflow-denied at every phase: `make push`, MCP create_pull_request /
# push_files. Breakglass for those: L9_PUBLISH_PATH_OVERRIDE=<reason>.
# ---------------------------------------------------------------------------
RAW_PUBLISH_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgit\s+push\b", re.I), "git push"),
    (re.compile(r"\bgh\s+pr\s+create\b", re.I), "gh pr create"),
    (re.compile(r"\bgh\s+pr\s+edit\b", re.I), "gh pr edit"),
)

#: Labels ``command_bypasses_publish_path`` returns for git/gh executables.
#: Workflow enforcement must not deny these (bare or compounded).
GIT_GH_PUBLISH_FORMS = frozenset({"git push", "gh pr create", "gh pr edit"})

#: Makefile goals that reach GitHub outside the sanctioned `pr` goal, matched
#: as exact goal tokens for the same reason as MAKE_REMOTE_GOALS.
MAKE_BYPASS_GOALS = frozenset({"push"})

# A leading `VAR=value` shell assignment. Anchored and non-nested: linear time.
ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# `make` options that consume a following argument, so that argument is never
# mistaken for the goal (`make -C /path pr`).
_MAKE_OPTS_WITH_ARG = frozenset(
    {"-C", "-f", "-j", "-l", "-o", "-W", "--directory", "--file", "--makefile", "--jobs"}
)


def make_goals(segment: str) -> tuple[str, ...]:
    """Every goal a `make` segment invokes, or () when it is not a make call.

    Deliberately a token scan, not a regex. Matching the real forms
    (``PR_REMEDIATE=0 make pr``, ``make -C /path pr``, ``make pr WS=…``) needs
    alternation under repetition, which is precisely the shape that backtracks
    exponentially (CodeQL py/redos, flagged on PR #168). This gate runs on every
    shell command an agent issues, so a hostile or merely long argument list must
    not be able to stall it: this scan is linear in the token count.

    Goals are exact tokens, which is the whole point: a regex for ``make pr``
    also matches ``make pr-check``, because ``\\b`` closes on the hyphen.

    All goals are returned, not just the first — ``make pr-check pr`` runs both,
    so a caller asking "does this publish?" must see the ``pr``.
    """
    tokens = segment.split()
    index = 0
    while index < len(tokens) and ENV_ASSIGN_RE.match(tokens[index]):
        index += 1
    if index >= len(tokens) or PurePosixPath(tokens[index]).name != "make":
        return ()
    index += 1
    goals: list[str] = []
    while index < len(tokens):
        token = tokens[index]
        if token in _MAKE_OPTS_WITH_ARG:
            index += 2
            continue
        if token.startswith("-") or ENV_ASSIGN_RE.match(token):
            index += 1
            continue
        goals.append(token)
        index += 1
    return tuple(goals)


def is_make_pr(segment: str) -> bool:
    """True when this segment invokes the `pr` goal — the sanctioned publish path.

    ``make pr-check`` is not a publish. It runs the local quality gate and never
    reaches GitHub (rule 48: "pr-check is PUBLIC quality; GitHub mutation stays
    make pr only"), so it is not this path and must not be gated as one.
    """
    return "pr" in make_goals(segment)


PUBLISH_PATH_OVERRIDE_ENV = "L9_PUBLISH_PATH_OVERRIDE"


def _publish_path_override() -> str:
    return os.environ.get(PUBLISH_PATH_OVERRIDE_ENV, "").strip()


def _publish_deny_reason(what: str) -> str:
    return (
        f"Publish path: `{what}` is not a sanctioned way to reach GitHub. "
        "Use `PR_REMEDIATE=0 make pr`, which runs the Makefile checkers and then "
        "pushes and opens the PR via ops/scripts/open_pr_after_gate.sh. "
        "Being L4 release_authorized does not permit a raw push — L4 governs WHEN, "
        f"this governs HOW. Human/ops override: {PUBLISH_PATH_OVERRIDE_ENV}=<reason>."
    )


def command_bypasses_publish_path(command: str) -> str | None:
    """Return the offending command form when it reaches GitHub outside `make pr`.

    Command-position scoped exactly like ``command_is_remote_mutation``: heredoc
    bodies are stripped and only segments whose head is the named tool count, so
    ``echo 'git push'`` is data, not a push. A segment containing `make pr` is
    the sanctioned path and is never reported.
    """
    segments: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        segments.append(segment)
        segments.extend(wrapper_subcommands(segment))
    for segment in segments:
        if is_make_pr(segment):
            continue
        head = segment_head(segment)
        if head is None:
            continue
        name = PurePosixPath(head).name
        if name == "make":
            bypass = MAKE_BYPASS_GOALS.intersection(make_goals(segment))
            if bypass:
                return f"make {sorted(bypass)[0]}"
            continue
        if name not in {"git", "gh"}:
            continue
        for pattern, label in RAW_PUBLISH_PATTERNS:
            if pattern.search(segment):
                return label
    return None


def command_has_make_remote(command: str) -> bool:
    """True when any segment invokes a Makefile remote goal (`pr` or `push`)."""
    segments: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        segments.append(segment)
        segments.extend(wrapper_subcommands(segment))
    return any(bool(MAKE_REMOTE_GOALS.intersection(make_goals(segment))) for segment in segments)


def publish_path_workflow_deny(command: str) -> str | None:
    """Workflow-plane publish deny, or None.

    git/gh forms stay reported by ``command_bypasses_publish_path`` and are
    not denied here — remediator ``make precommit-repo && git push`` and
    ``git push | tail`` must match bare ``git push``. Only non-git bypasses
    (`make push`) are denied. Override hands those to the L4 check.
    """
    if _publish_path_override():
        return None
    bypass = command_bypasses_publish_path(command)
    if bypass is None or bypass in GIT_GH_PUBLISH_FORMS:
        return None
    return _publish_deny_reason(bypass)


def command_is_remote_mutation(command: str) -> bool:
    """Detect remote mutation in command text only (heredoc data is excluded).

    Matching is command-position scoped: a segment only counts when its head
    is the tool the pattern names (git/gh/make). Quoted spans are preserved,
    so ``bash -c 'git push …'`` still matches via the wrapper descent.
    ``echo 'git push'`` and other data segments never match. Residual accepted:
    ``ssh host 'git push'`` / ``sudo git push`` heads are not pattern targets.

    A `make` segment is classified by its goals, not by a regex over the text.
    ``\\bmake\\s+pr\\b`` matches ``make pr-check`` — the word boundary closes on
    the hyphen — which denied the local quality gate as if it were a publish.
    """
    segments: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        segments.append(segment)
        segments.extend(wrapper_subcommands(segment))
    for segment in segments:
        head = segment_head(segment)
        if head is None:
            continue
        name = PurePosixPath(head).name
        if name == "make":
            if MAKE_REMOTE_GOALS.intersection(make_goals(segment)):
                return True
            continue
        if name not in {"git", "gh"}:
            continue
        if any(pattern.search(segment) for pattern in REMOTE_BASH_PATTERNS):
            return True
    return False


def _repo_root_from_path(path: str) -> Path | None:
    """Resolve a named path to its git repo root (symlinks resolved).

    Fails closed: only an existing directory inside a git work tree qualifies.
    """
    try:
        candidate = Path(path).resolve()
    except OSError:
        return None
    if not candidate.is_dir():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    top = Path(proc.stdout.strip())
    return top if top.is_dir() else None


def evaluate(tool_name: str, tool_input: dict[str, Any], *, root: Path) -> str | None:
    """Return deny reason or None if allowed.

    Workspace resolution: when the command explicitly names repo paths
    (``git -C <path>`` / ``cd <path>``), EVERY named root must hold a valid L4
    release receipt — otherwise the session-root check applies unchanged.
    Dynamic path tokens never widen the gate (extract_named_roots ignores
    them), so unknown targets stay fail-closed.

    Order matters. The context-sensitive guardrail plane runs FIRST on every
    shell command: it is the one denial a git command can still earn, and it
    earns it from the effect it would actually have, never from its name. Only
    then does the git/gh exemption short-circuit the workflow plane, so no
    state lookup, phase check, or authorization lookup can deny a git command
    that destroys nothing.
    """
    if tool_name in SHELL_TOOL_NAMES:
        guardrail = command_requires_human(
            str(tool_input.get("command") or tool_input.get("cmd") or ""), root=root
        )
        if guardrail:
            return guardrail

    if event_is_git_or_gh(tool_name, tool_input):
        return None

    if tool_name in DENY_MCP_TOOLS or tool_name.endswith("create_pull_request"):
        # An MCP push/PR call can never be the sanctioned publish path — it does
        # not run the Makefile checkers — so it is denied regardless of L4 phase.
        if not _publish_path_override():
            return _publish_deny_reason(tool_name)
        allowed, reason = release_allows_remote(root)
        return None if allowed else reason

    if tool_name in SHELL_TOOL_NAMES:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        iso = command_violates_worktree_isolation(command, root=root)
        if iso:
            return iso
        deny = publish_path_workflow_deny(command)
        if deny:
            return deny
        if not command_is_remote_mutation(command):
            return None
        if not command_has_make_remote(command):
            return None
        named_roots = extract_named_roots(command)
        if named_roots:
            resolved = [_repo_root_from_path(path) for path in named_roots]
            if any(item is None for item in resolved):
                return (
                    "L4 named root could not be resolved to a git repository; "
                    "fail-closed on unresolved remote-mutation targets"
                )
            if all(release_allows_remote(item)[0] for item in resolved):  # type: ignore[union-attr]
                return None
            denied = next(
                item for item in resolved if item is not None and not release_allows_remote(item)[0]
            )
            _, reason = release_allows_remote(denied)
            return reason
        allowed, reason = release_allows_remote(root)
        return None if allowed else reason
    return None


def _guardrail_from_payload(raw: str) -> str | None:
    """Guardrail verdict for a raw hook payload. Never raises.

    The git/gh exemption answers before the event is parsed, so the guardrail
    has to answer there too — otherwise a destructive git command would be
    waved through by the exemption before any policy ran.
    """
    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if not isinstance(event, dict):
        return None
    tool_name = str(event.get("tool_name") or event.get("toolName") or "")
    if tool_name and tool_name not in SHELL_TOOL_NAMES:
        return None
    command = str(event.get("command") or event.get("full_command") or "")
    if not command:
        tool_input = event.get("tool_input") or event.get("toolInput") or {}
        if isinstance(tool_input, dict):
            command = str(tool_input.get("command") or tool_input.get("cmd") or "")
    if not command.strip():
        return None
    try:
        root = workspace_from_event(event)
    except Exception:  # noqa: BLE001 - an unresolvable workspace is not a verdict
        root = None
    return command_requires_human(command, root=root)


def _deny_claude(reason: str) -> int:
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


def _emit_cursor(permission: str, message: str | None = None) -> int:
    payload: dict[str, Any] = {"permission": permission}
    if message:
        payload["user_message"] = message
    print(json.dumps(payload))
    return 0


#: Denial reason used when the gate cannot complete a policy evaluation.
#: A caller sees a denial; stderr keeps the detail needed to diagnose it.
INTERNAL_EVALUATION_ERROR = (
    "INTERNAL_EVALUATION_ERROR: the execution gate could not complete a policy "
    "evaluation for this command, so it denied it. This is a gate fault, not a "
    "policy decision about the command. See the hook's stderr for the failure."
)


def _fail_closed_note(exc: BaseException) -> None:
    """Record why evaluation failed. Never the gate's decision channel."""
    print(
        f"local_execution_gate: evaluation failed ({type(exc).__name__}: {exc}); failing closed",
        file=sys.stderr,
    )


def main_claude() -> int:
    raw = sys.stdin.read()
    # The destructive-risk plane answers first, even for git: the exemption
    # below removes workflow denials, not the guardrail.
    guardrail = _guardrail_from_payload(raw)
    if guardrail:
        return _deny_claude(guardrail)
    # Answered before parsing, and outside the fail-closed handler below: for a
    # git/gh command, execution permission must not depend on this gate being
    # able to evaluate anything at all.
    if payload_is_git_or_gh(raw):
        return 0
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        # Deliberate and unchanged: an unparseable event is a malformed
        # invocation, not a failed evaluation, and a hook must not brick a
        # session over one. Everything past this point is security evaluation
        # and fails closed instead.
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        tool_name = str(event.get("tool_name", ""))
        tool_input = event.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        # Same resolution main_cursor_shell() performs. Without it this surface
        # judged a `cd <worktree> && make pr` against the reported project root,
        # so the worktree's L4 receipt was never the one consulted and no
        # worktree could publish from Claude Code at all.
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        root = workspace_from_event(event)
        if command:
            root = effective_root(command, root)
        reason = evaluate(tool_name, tool_input, root=root)
    except Exception as exc:  # noqa: BLE001 - security boundary: deny on any fault
        # Workspace resolution, policy loading and command evaluation all land
        # here. Previously an exception propagated as a traceback and a non-zero
        # exit, which PreToolUse treats as non-blocking — a crash in a gate whose
        # whole purpose is to fail closed became an accidental permit (F-11).
        _fail_closed_note(exc)
        return _deny_claude(INTERNAL_EVALUATION_ERROR)
    if reason:
        return _deny_claude(reason)
    return 0


_LEADING_CD = re.compile(r"^\s*cd\s+(?P<path>\"[^\"]+\"|'[^']+'|[^\s;&|]+)")


def _git_out(cwd: Path, *args: str) -> str:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _common_dir(cwd: Path) -> Path | None:
    """Shared .git directory, identical across every worktree of one repository.

    `--git-common-dir` is reported relative to git's own cwd, which `-C` pins to
    `cwd`, so a relative answer must be resolved against `cwd` and not the
    interpreter's working directory.
    """
    out = _git_out(cwd, "rev-parse", "--git-common-dir")
    if not out:
        return None
    path = Path(out)
    if not path.is_absolute():
        path = cwd / path
    try:
        return path.resolve()
    except OSError:
        return None


def effective_root(command: str, root: Path) -> Path:
    """The checkout the command will actually run in.

    Cursor's beforeShellExecution reports the *project root*, not the shell's
    cwd. Rule 49 tells every agent to work in a linked worktree, so a command
    that begins by cd-ing into one would otherwise be judged against the wrong
    checkout -- wrong branch, wrong L4 receipt -- and no worktree could ever
    publish.

    Only a worktree of the *same* repository is accepted, verified by comparing
    `git rev-parse --git-common-dir`. A cd into an unrelated repository leaves
    the root untouched, so this cannot be used to escape the gate.

    A cloud session reports something different again: a *container root* that
    holds many clones side by side and is itself no repository (`/home/user`).
    `_common_dir` is None there, so the same-repository test could never
    succeed and every worktree resolved back to a path that cannot hold an L4
    receipt -- reproducing, for a whole surface, the impossibility described
    above. With no repository at the root there is nothing to be steered away
    from, so a cd into a real work tree is the only signal available and is
    accepted. Authorization is unchanged: the receipt must still exist at the
    resolved root and bind the head SHA. When the root *is* a repository the
    same-repository rule still applies, so this is not a way to reach an
    unrelated checkout from a real one.
    """
    match = _LEADING_CD.match(command)
    if not match:
        return root
    raw = match.group("path").strip("\"'")
    try:
        candidate = Path(os.path.expandvars(raw)).expanduser()
    except (OSError, ValueError):
        return root
    if not candidate.is_absolute() or not candidate.is_dir():
        return root

    root_common = _common_dir(root)
    if root_common is None:
        # Container root: accept any real work tree, reject a plain directory.
        if _common_dir(candidate) is None:
            return root
    elif root_common != _common_dir(candidate):
        return root

    toplevel = _git_out(candidate, "rev-parse", "--show-toplevel")
    return Path(toplevel) if toplevel else root


def main_cursor_shell() -> int:
    raw = sys.stdin.read()
    guardrail = _guardrail_from_payload(raw)
    if guardrail:
        return _emit_cursor("deny", guardrail)
    if payload_is_git_or_gh(raw):
        return _emit_cursor("allow")
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        return _emit_cursor("allow")
    if not isinstance(event, dict):
        return _emit_cursor("allow")
    try:
        command = str(event.get("command") or event.get("full_command") or "")
        root = effective_root(command, workspace_from_event(event))
        guardrail = command_requires_human(command, root=root)
        if guardrail:
            return _emit_cursor("deny", guardrail)
        iso = command_violates_worktree_isolation(command, root=root)
        if iso:
            return _emit_cursor("deny", iso)
        deny = publish_path_workflow_deny(command)
        if deny:
            return _emit_cursor("deny", deny)
        if not command_is_remote_mutation(command):
            return _emit_cursor("allow")
        if not command_has_make_remote(command):
            return _emit_cursor("allow")
        allowed, reason = release_allows_remote(root)
    except Exception as exc:  # noqa: BLE001 - security boundary: deny on any fault
        _fail_closed_note(exc)
        return _emit_cursor("deny", INTERNAL_EVALUATION_ERROR)
    if allowed:
        return _emit_cursor("allow")
    return _emit_cursor("deny", reason)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "claude"
    if mode in {"cursor-shell", "shell"}:
        raise SystemExit(main_cursor_shell())
    raise SystemExit(main_claude())
