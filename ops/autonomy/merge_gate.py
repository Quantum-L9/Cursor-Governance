#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/agents/adapters/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Ordinary `gh pr merge` is allowed when either of these is true:

  L9_MERGE_AUTHORIZED=<nonempty reason string>          # human session breakglass
  ~/.l9/autonomy/merge-authorization.json               # scoped, expiring receipt
    {"authorizations": [{"repo": "org/repo", "pr": "*" | 53,
                          "source": "l9-pr-remediation",
                          "expires_at": <unix-seconds>, "reason": "...",
                          "head_sha": "<40-hex>"      # optional revision binding
                          }]}
    Overridable for tests via L9_MERGE_AUTHORIZATION_FILE. An entry authorizes
    only when: repo matches; pr is "*" (all open PRs in that repo) or the exact
    PR number; expires_at is a positive number in the future (a receipt with no
    valid expiry never authorizes — expiry is required); and, when the entry
    carries a head_sha, the merge names that same head revision (a receipt bound
    to a revision is rejected once HEAD moves, or when the caller does not name
    the head at all).

A standing environment boolean is NOT a merge authority. An env var set once in
the Claude account/session configuration must never grant unattended merge, so
the retired L9_AUTONOMY_AUTONOMOUS_MERGE flag authorizes nothing here: merge
requires the human per-session breakglass or a scoped, expiring receipt bound to
the repo (and PR). Setting the flag has no effect on this gate.

Invoking /l9-pr-remediation writes that receipt via
ops/autonomy/authorize_merge.py. Campaigns and make pr do not merge.
An L4 release receipt does NOT authorize merge. Agents still merge only
after green + mergeable + review threads resolved (oldest first).

Shell ``git``/``gh`` commands are exempt from *authorization* — see
``git_execution_exemption``. Stack safety is not exempt: ``gh pr merge
--squash|--rebase`` (or an unspecified method) of a stack parent is denied
on Shell and MCP alike. Agents must use ``stack_safe_merge.py`` so the
method is selected in code, not guessed. The never-waive set still applies
to the MCP merge tool.

Stack safety
------------
Squash and rebase merges replace the head branch's commits with a new commit
that shares no ancestry with them. Any open PR based on that head therefore
loses its merge base: it rewinds to the pre-merge tip, where files the merged
PR deleted still exist. Git then reads "child preserved the file" and "child
never touched the file" as the same snapshot and resolves delete-wins with no
conflict, silently dropping the child's content.

So an authorized merge is additionally denied when the head branch is the base
of an open PR and the method is squash/rebase (or unspecified). Merge with
--merge, or land the children bottom-up first. Probe order:

  L9_STACK_CHECK_BYPASS=<reason>   # skip the probe (human breakglass)
  L9_STACK_PROBE_FILE              # JSON {"owner/name#12": {"children": [13]}}
  gh pr view / gh pr list          # live probe, fail-closed on error

L9_MERGE_AUTHORIZED (session env, human-set per merge) also skips the probe. A
receipt written by an agent does not -- unattended merging is exactly when an
orphaned child PR would go unnoticed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from command_parse import (  # noqa: E402
    segment_words,
    split_segments,
    strip_heredoc_bodies,
    wrapper_subcommands,
)
from git_execution_exemption import event_is_git_or_gh  # noqa: E402
from l4_local import workspace_from_event  # noqa: E402

DENY_TOOL_NAMES = {
    "mcp__github__merge_pull_request",
    "MergePullRequest",
}

MERGE_BASH = re.compile(r"\bgh\s+pr\s+merge\b", re.I)
ADMIN_MERGE_BASH = re.compile(r"\bgh\s+pr\s+merge\b.*--admin\b", re.I)
FORCE_PUSH_BASH = re.compile(r"\bgit\s+push\s+.*(--force|-f)\b", re.I)
HARD_RESET_BASH = re.compile(r"\bgit\s+reset\s+--hard\b", re.I)
CLEAN_FD_BASH = re.compile(r"\bgit\s+clean\s+-fd\b", re.I)
REPO_SCOPE = {"*", "all", "ALL"}

SQUASH_FLAG = re.compile(r"--squash\b", re.I)
REBASE_FLAG = re.compile(r"--rebase\b", re.I)
MERGE_COMMIT_FLAG = re.compile(r"--merge\b", re.I)

# Methods that rewrite the head's commits and orphan any PR based on it.
ANCESTRY_BREAKING = {"squash", "rebase", "unspecified"}

GH_TIMEOUT_SECONDS = 20

NEVER_WAIVE_REASON = (
    "Autonomy Surface Profile never waives force-push, hard-reset, "
    "destructive clean, or admin-merge."
)

MERGE_DENY_REASON = (
    "Autonomy Surface Profile forbids merge until /l9-pr-remediation writes a "
    "scoped, expiring authorization receipt, or a human sets "
    "L9_MERGE_AUTHORIZED=<reason> for this session. A standing environment "
    "boolean is not an authority. Campaigns and make pr end at green + "
    "merge-ready. Then ops/autonomy/stack_safe_merge.py --repo <owner/name> "
    "--pr <n> --run (no --admin) for each green mergeable PR, oldest first."
)


def _stack_deny_reason(pr: str, head: str, children: list[int], method: str) -> str:
    kids = ", ".join(f"#{c}" for c in children)
    shown = method if method != "unspecified" else "the default method (unspecified)"
    return (
        f"Stack safety: PR #{pr} head '{head}' is the base of open PR(s) {kids}, and "
        f"{shown} rewrites that head's commits. The child would lose its merge base and "
        "silently drop any file this PR deletes (delete-wins, no conflict). "
        f"Either merge {kids} first (bottom-up), retarget them to the base branch, or "
        "merge this PR with --merge to preserve ancestry. "
        "Human breakglass: L9_STACK_CHECK_BYPASS=<reason>."
    )


def _stack_unknown_reason(pr: str, repo: str, detail: str) -> str:
    target = f"{repo}#{pr}" if repo else f"#{pr}"
    return (
        f"Stack safety: cannot determine whether {target} is the base of an open PR "
        f"({detail}). A squash/rebase merge of a stacked head silently destroys the "
        "child PR's content, so this is fail-closed. Verify with "
        f"`gh pr list --repo <owner/name> --state open --base <head-branch>`, then "
        "re-run with --merge, or set L9_STACK_CHECK_BYPASS=<reason>."
    )


def _argv_skip_env(words: list[str]) -> list[str]:
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    return words[index:]


def _segment_is_pr_merge(segment: str) -> bool:
    """True when this segment *invokes* ``gh pr merge``, not when it mentions it."""
    rest = _argv_skip_env(segment_words(segment))
    if len(rest) >= 3 and rest[0] == "gh" and rest[1] == "pr" and rest[2] == "merge":
        return True
    return any(_segment_is_pr_merge(sub) for sub in wrapper_subcommands(segment))


def _command_is_pr_merge(command: str) -> bool:
    """True only for an executed ``gh pr merge``. Heredoc/commit text does not count."""
    return any(
        _segment_is_pr_merge(segment) for segment in split_segments(strip_heredoc_bodies(command))
    )


def _merge_method(command: str) -> str:
    """Merge method named on the executed `gh pr merge` argv, not on nearby text."""
    for segment in split_segments(strip_heredoc_bodies(command)):
        if not _segment_is_pr_merge(segment):
            continue
        rest = _argv_skip_env(segment_words(segment))
        if "--squash" in rest:
            return "squash"
        if "--rebase" in rest:
            return "rebase"
        if "--merge" in rest:
            return "merge"
        return "unspecified"
    if SQUASH_FLAG.search(command):
        return "squash"
    if REBASE_FLAG.search(command):
        return "rebase"
    if MERGE_COMMIT_FLAG.search(command):
        return "merge"
    return "unspecified"


def _gh_json(args: list[str]) -> Any:
    """Run a gh command returning JSON. Raises RuntimeError with a short detail."""
    if not shutil.which("gh"):
        raise RuntimeError("gh not on PATH")
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["gh", *args],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"gh failed: {exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "gh returned non-zero").strip().splitlines()[-1][:200])
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"gh emitted non-JSON: {exc}") from exc


def _probe_file_entry(repo: str, pr: str) -> dict[str, Any] | None:
    """Injected probe result, so the gate is deterministic offline and in tests."""
    override = os.environ.get("L9_STACK_PROBE_FILE", "").strip()
    if not override:
        return None
    try:
        payload = json.loads(Path(override).expanduser().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RuntimeError(f"unreadable L9_STACK_PROBE_FILE ({exc})") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("L9_STACK_PROBE_FILE is not a JSON object")
    entry = payload.get(f"{repo}#{pr}") if repo else None
    if entry is None:
        entry = payload.get(f"#{pr}", payload.get("default"))
    if entry is None:
        return {"head": "", "children": []}
    if not isinstance(entry, dict):
        raise RuntimeError("L9_STACK_PROBE_FILE entry is not a JSON object")
    return entry


def _stacked_children(repo: str, pr: str) -> tuple[str, list[int]]:
    """Return (head branch, open PR numbers based on it). Raises RuntimeError if unknown."""
    entry = _probe_file_entry(repo, pr)
    if entry is not None:
        children = [int(c) for c in entry.get("children") or []]
        return str(entry.get("head") or ""), children

    if not repo:
        raise RuntimeError("no --repo on the command and no probe file")
    view = _gh_json(["pr", "view", pr, "--repo", repo, "--json", "headRefName"])
    head = str((view or {}).get("headRefName") or "")
    if not head:
        raise RuntimeError("gh did not report a head branch")
    listing = _gh_json(
        ["pr", "list", "--repo", repo, "--state", "open", "--base", head, "--json", "number"]
    )
    children = [int(item["number"]) for item in (listing or []) if "number" in item]
    return head, [c for c in children if str(c) != pr]


def _stack_safety_reason(command: str, tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Deny reason when this merge would orphan an open child PR, else None."""
    if os.environ.get("L9_STACK_CHECK_BYPASS", "").strip():
        return None
    repo, pr = _target_from_input(tool_name, tool_input)
    if not pr:
        return None
    method = _merge_method(command)
    try:
        head, children = _stacked_children(repo, pr)
    except RuntimeError as exc:
        if method in ANCESTRY_BREAKING:
            return _stack_unknown_reason(pr, repo, str(exc))
        return None
    if not children:
        return None
    if method in ANCESTRY_BREAKING:
        return _stack_deny_reason(pr, head or "<unknown>", children, method)
    return None


def _auth_file_path() -> Path:
    override = os.environ.get("L9_MERGE_AUTHORIZATION_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".l9" / "autonomy" / "merge-authorization.json"


def _target_from_input(tool_name: str, tool_input: dict[str, Any]) -> tuple[str, str]:
    """Return (repo, pr) parsed conservatively from the tool input; ('', '') when unknown.

    Two MCP argument shapes reach this gate. Some servers pass a single
    ``repo="owner/name"`` with ``pull_number``; the GitHub MCP server splits the
    identity across ``owner`` + ``repo`` and spells the number ``pullNumber``.
    Parsing only the first shape yielded ``("name", "")`` for the second, which
    no receipt can match (``authorize_merge.py`` refuses a repo without an
    owner) and which silently disabled the stack-safety probe, since that probe
    returns early on an empty PR number.
    """
    repo = str(tool_input.get("repo") or tool_input.get("repository") or "")
    owner = str(tool_input.get("owner") or "")
    # Only join when the repo is a bare name: never rewrite an explicit owner/name.
    if owner and repo and "/" not in repo:
        repo = f"{owner}/{repo}"
    pr = str(
        tool_input.get("pull_number")
        or tool_input.get("pullNumber")
        or tool_input.get("pr")
        or tool_input.get("number")
        or ""
    )
    if not (repo and pr) and tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        match = re.search(r"\bgh\s+pr\s+merge\s+(\d+)", command, re.I)
        if match:
            pr = match.group(1)
            repo_match = re.search(r"--repo\s+([\w.-]+/[\w.-]+)", command, re.I)
            repo = repo_match.group(1) if repo_match else ""
    return repo, pr


def _file_authorizes(repo: str, pr: str, head_sha: str = "") -> bool:
    """True when a fresh, in-scope, unexpired authorization matches.

    Expiry is required: a receipt with no positive future ``expires_at`` never
    authorizes. When a receipt carries ``head_sha`` it is bound to that immutable
    revision -- the merge must name the same head (``head_sha`` argument),
    otherwise a moved HEAD (or a caller that does not name the head) is rejected.
    Receipts without ``head_sha`` stay repo/PR-scoped as before.
    """
    path = _auth_file_path()
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("authorizations", []) if isinstance(payload, dict) else []
    except (json.JSONDecodeError, OSError):
        return False
    now = time.time()
    live_sha = head_sha.strip().lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        # Require expiry: missing / non-numeric / already-past never authorizes.
        expires = entry.get("expires_at")
        if not isinstance(expires, (int, float)) or isinstance(expires, bool) or expires <= now:
            continue
        entry_repo = str(entry.get("repo") or "")
        if not entry_repo or not repo or entry_repo != repo:
            continue
        entry_pr = str(entry.get("pr") or entry.get("number") or "")
        if entry_pr not in REPO_SCOPE and not (pr and entry_pr == pr):
            continue
        # Optional immutable-revision binding.
        entry_sha = str(entry.get("head_sha") or "").strip().lower()
        if entry_sha and (not live_sha or live_sha != entry_sha):
            continue
        return True
    return False


def _human_breakglass() -> bool:
    """L9_MERGE_AUTHORIZED is human-set; it accepts the stack risk explicitly."""
    return bool(os.environ.get("L9_MERGE_AUTHORIZED", "").strip())


_SHA_INPUT_KEYS = ("sha", "head_sha", "expected_head_sha", "expected_head_oid", "match_head_commit")
_MATCH_HEAD_BASH = re.compile(r"--match-head-commit[= ]+([0-9a-fA-F]{7,40})")


def _head_sha_from_input(tool_name: str, tool_input: dict[str, Any]) -> str:
    """The head revision the caller names for this merge, or '' when unnamed."""
    for key in _SHA_INPUT_KEYS:
        value = tool_input.get(key)
        if value:
            return str(value)
    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        match = _MATCH_HEAD_BASH.search(command)
        if match:
            return match.group(1)
    return ""


def _merge_authorized(tool_name: str, tool_input: dict[str, Any]) -> bool:
    # Authority only; stack safety is evaluated separately in evaluate(). Merge
    # authority is the human per-session breakglass or a scoped, expiring receipt
    # bound to the repo (and PR, and optionally the head revision). A standing
    # environment boolean is deliberately not consulted: an env var set once in
    # the account/session configuration must never grant unattended merge.
    if _human_breakglass():
        return True
    repo, pr = _target_from_input(tool_name, tool_input)
    head_sha = _head_sha_from_input(tool_name, tool_input)
    return _file_authorizes(repo, pr, head_sha)


def _never_waive_command(command: str) -> bool:
    return bool(
        FORCE_PUSH_BASH.search(command)
        or HARD_RESET_BASH.search(command)
        or CLEAN_FD_BASH.search(command)
        or ADMIN_MERGE_BASH.search(command)
    )


def _never_waive_tool(tool_name: str, tool_input: dict[str, Any]) -> bool:
    if tool_name in DENY_TOOL_NAMES and bool(
        tool_input.get("admin") or tool_input.get("admin_override")
    ):
        return True
    return False


def _deny(reason: str) -> int:
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


def evaluate(
    tool_name: str,
    tool_input: dict[str, Any],
    *,
    root: Path | None = None,
) -> str | None:
    """Return deny reason or None if allowed to proceed (no decision).

    Shell git/gh commands skip *authorization* (``git_execution_exemption``).
    Stack safety still runs: squash/rebase of a parent orphans children.
    The MCP merge tool stays fully governed.
    """
    del root  # signature kept for hook callers

    if event_is_git_or_gh(tool_name, tool_input):
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if _command_is_pr_merge(command):
            rest = []
            for segment in split_segments(strip_heredoc_bodies(command)):
                if _segment_is_pr_merge(segment):
                    rest = _argv_skip_env(segment_words(segment))
                    break
            if "--admin" in rest:
                return NEVER_WAIVE_REASON
            if _human_breakglass():
                return None
            return _stack_safety_reason(command, tool_name, tool_input)
        return None

    if _never_waive_tool(tool_name, tool_input):
        return NEVER_WAIVE_REASON

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if _never_waive_command(command):
            return NEVER_WAIVE_REASON
        if MERGE_BASH.search(command):
            if not _merge_authorized(tool_name, tool_input):
                return MERGE_DENY_REASON
            if _human_breakglass():
                return None
            return _stack_safety_reason(command, tool_name, tool_input)
        return None

    if tool_name in DENY_TOOL_NAMES:
        if not _merge_authorized(tool_name, tool_input):
            return MERGE_DENY_REASON
        if _human_breakglass():
            return None
        method = str(tool_input.get("merge_method") or tool_input.get("method") or "")
        pseudo = f"gh pr merge --{method.lower()}" if method else "gh pr merge"
        return _stack_safety_reason(pseudo, tool_name, tool_input)
    return None


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_name = str(event.get("tool_name", ""))
    tool_input = event.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    root = workspace_from_event(event)
    reason = evaluate(tool_name, tool_input, root=root)
    if reason:
        return _deny(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
