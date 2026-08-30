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
#: The REST merge endpoint, reached by `gh api` or curl. `gh pr merge` is a
#: GraphQL call; where GraphQL is unavailable this path is the merge, so the
#: gate must recognise it as one. Matched against argv words, method checked
#: separately (GET on this path only reports whether the PR is merged).
REST_MERGE_PATH = re.compile(r"(?:^|/)repos/[^/\s]+/[^/\s]+/pulls/\d+/merge/?$", re.I)
#: Same endpoint, capturing owner / name / number so the stack probe and the
#: authorization receipt can resolve a REST merge's target.
#: \b, not (?:^|/): this one is searched in the whole command line, where the
#: path is preceded by a space rather than a slash or the string start.
REST_MERGE_TARGET = re.compile(r"\brepos/([\w.-]+)/([\w.-]+)/pulls/(\d+)/merge\b", re.I)
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


def _stack_unknown_reason(pr: str, repo: str, detail: str, kind: str = "unknown") -> str:
    """Fail-closed message. The DECISION never varies on `kind`; the advice does.

    Naming the obstacle matters because the old message sent operators to
    `gh pr list`, which on a GraphQL-restricted surface is refused by the same
    policy that just broke the probe -- advice that cannot be followed.
    """
    target = f"{repo}#{pr}" if repo else f"#{pr}"
    slug = repo or "<owner/name>"
    head = (
        "Stack safety: both probe transports were refused by this session "
        if kind == "transport_blocked"
        else "Stack safety: cannot determine whether "
    )
    body = f"for {target}" if kind == "transport_blocked" else f"{target} is the base of an open PR"
    verify = (
        f"`gh api 'repos/{slug}/pulls?state=open' --jq '.[]|\"#\\(.number) base=\\(.base.ref)\"'`"
    )
    return (
        f"{head}{body} ({detail}). A squash/rebase merge of a stacked head "
        "silently destroys the child PR's content, so this is fail-closed. "
        f"Verify over REST with {verify} -- no open PR may name this PR's head as "
        "its base -- then re-run with --merge, or set "
        "L9_STACK_CHECK_BYPASS=<reason> in the gate process environment."
    )


def _argv_skip_env(words: list[str]) -> list[str]:
    index = 0
    while index < len(words) and "=" in words[index] and not words[index].startswith(("-", "/")):
        index += 1
    return words[index:]


def _segment_is_cli_pr_merge(segment: str) -> bool:
    """True when this segment *invokes* ``gh pr merge``, not when it mentions it."""
    rest = _argv_skip_env(segment_words(segment))
    if len(rest) >= 3 and rest[0] == "gh" and rest[1] == "pr" and rest[2] == "merge":
        return True
    return any(_segment_is_cli_pr_merge(sub) for sub in wrapper_subcommands(segment))


def _segment_is_rest_pr_merge(segment: str) -> bool:
    """True when this segment merges a PR over REST rather than the ``pr`` verb.

    ``gh pr merge`` is a GraphQL call. Where GraphQL is unavailable — this
    Claude surface serves only a pinned set of PR-review operations and 403s
    the rest — the working transport is the REST endpoint:

        gh api -X PUT repos/<owner>/<name>/pulls/<n>/merge -f merge_method=squash

    Matching the literal words ``gh pr merge`` therefore recognised only the
    transport that does not work here, and the one that does slipped past
    every check this module performs — stack safety included, which is the
    check that keeps a squash of a stack parent from silently dropping a
    child PR's content. The verb is not the merge; the effect is.

    Transport-agnostic on purpose: ``gh api`` and ``curl`` reach the same
    endpoint, and the curl form skipped even *authorization*, since it is not
    a git/gh event and the old ``MERGE_BASH`` regex looked for the CLI verb.
    A PUT to that path is a merge whatever binary issues it. GET on the same
    path only asks whether the PR is merged, so the method is required.
    """
    rest = _argv_skip_env(segment_words(segment))
    if rest:
        method = ""
        for index, word in enumerate(rest):
            if word in ("-X", "--method", "--request") and index + 1 < len(rest):
                method = rest[index + 1].strip("'\"").upper()
            elif word.startswith(("--method=", "--request=", "-X=")):
                method = word.split("=", 1)[1].strip("'\"").upper()
        if method == "PUT" and any(REST_MERGE_PATH.search(word.strip("'\"")) for word in rest):
            return True
    return any(_segment_is_rest_pr_merge(sub) for sub in wrapper_subcommands(segment))


def _segment_is_pr_merge(segment: str) -> bool:
    """True for either transport: the ``gh pr merge`` verb or a REST merge."""
    return _segment_is_cli_pr_merge(segment) or _segment_is_rest_pr_merge(segment)


def _command_is_pr_merge(command: str) -> bool:
    """True only for an executed merge. Heredoc/commit text does not count."""
    return any(
        _segment_is_pr_merge(segment) for segment in split_segments(strip_heredoc_bodies(command))
    )


def _rest_merge_method(rest: list[str]) -> str:
    """merge_method named on a `gh api` argv via -f/-F/--field/--raw-field.

    Unspecified stays "unspecified" — ANCESTRY_BREAKING, so a REST merge that
    does not name its method is treated as unsafe for a stack parent. That is
    deliberate and needs no claim about the endpoint's server-side default:
    this module's own contract is that the method is "selected in code, not
    guessed", and naming it costs the caller one flag.
    """
    field_flags = ("-f", "-F", "--field", "--raw-field")
    for index, word in enumerate(rest):
        value = ""
        if word in field_flags and index + 1 < len(rest):
            value = rest[index + 1]
        elif any(word.startswith(f"{flag}=") for flag in field_flags):
            value = word.split("=", 1)[1]
        elif word.startswith("merge_method="):
            value = word
        if value.startswith("merge_method="):
            method = value.split("=", 1)[1].strip().strip("'\"").lower()
            if method in ("squash", "rebase", "merge"):
                return method
    return "unspecified"


def _merge_method(command: str) -> str:
    """Merge method named on the executed merge argv, not on nearby text."""
    for segment in split_segments(strip_heredoc_bodies(command)):
        if not _segment_is_pr_merge(segment):
            continue
        rest = _argv_skip_env(segment_words(segment))
        if _segment_is_rest_pr_merge(segment) and not _segment_is_cli_pr_merge(segment):
            return _rest_merge_method(rest)
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


class ProbeError(RuntimeError):
    """A stack probe that could not answer, tagged with WHY it could not.

    The deny decision never varies on the kind: an unanswerable probe is
    fail-closed regardless. The kind exists so the operator-facing message can
    name the actual obstacle. A transport that is switched off for the whole
    session and a genuinely ambiguous repository topology are different
    problems with different remedies, and reporting both as "unknown" sent
    people to verify with a command that was also switched off.
    """

    def __init__(self, detail: str, kind: str = "unknown") -> None:
        super().__init__(detail)
        self.kind = kind


def _transport_blocked(detail: str) -> bool:
    """True when the failure looks like the transport, not the repository."""
    low = detail.lower()
    return any(
        marker in low
        for marker in (
            "graphql query is not enabled",
            "not enabled for this session",
            "http 403",
            "403 forbidden",
            "gh not on path",
        )
    )


def _gh_rest_json(path: str) -> Any:
    """GET a REST path through gh. Raises ProbeError tagged by failure kind.

    REST is the surface that stays available when the session gateway serves
    only a pinned set of GraphQL operations, which is what every `gh pr`
    subcommand is built on.
    """
    try:
        return _gh_json(["api", path])
    except RuntimeError as exc:
        detail = str(exc)
        kind = "transport_blocked" if _transport_blocked(detail) else "probe_failed"
        raise ProbeError(detail, kind) from exc


def _stacked_children_rest(repo: str, pr: str) -> tuple[str, list[int]]:
    """Resolve (head, children) over REST only.

    `GET /repos/{owner}/{repo}/pulls/{n}` carries `head.ref`, and
    `GET /repos/{owner}/{repo}/pulls?state=open&base=<head>` lists exactly the
    open pull requests based on it. That is everything the stack probe needs,
    with no GraphQL.
    """
    view = _gh_rest_json(f"repos/{repo}/pulls/{pr}")
    head = str(((view or {}).get("head") or {}).get("ref") or "")
    if not head:
        raise ProbeError("REST did not report a head branch", "probe_failed")
    listing = _gh_rest_json(f"repos/{repo}/pulls?state=open&base={head}&per_page=100")
    children = [
        int(item["number"])
        for item in (listing or [])
        if isinstance(item, dict) and "number" in item
    ]
    return head, [c for c in children if str(c) != pr]


def _stacked_children_cli(repo: str, pr: str) -> tuple[str, list[int]]:
    """Resolve (head, children) through `gh pr`, which is GraphQL-backed."""
    try:
        view = _gh_json(["pr", "view", pr, "--repo", repo, "--json", "headRefName"])
        head = str((view or {}).get("headRefName") or "")
        if not head:
            raise ProbeError("gh did not report a head branch", "probe_failed")
        listing = _gh_json(
            ["pr", "list", "--repo", repo, "--state", "open", "--base", head, "--json", "number"]
        )
    except ProbeError:
        raise
    except RuntimeError as exc:
        detail = str(exc)
        kind = "transport_blocked" if _transport_blocked(detail) else "probe_failed"
        raise ProbeError(detail, kind) from exc
    children = [int(item["number"]) for item in (listing or []) if "number" in item]
    return head, [c for c in children if str(c) != pr]


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
    """Return (head branch, open PR numbers based on it). Raises ProbeError if unknown.

    Two transports, tried in order, first answer wins:

      1. REST  -- `gh api repos/{o}/{r}/pulls...`
      2. `gh pr view` / `gh pr list` -- GraphQL-backed

    REST leads because it is the transport that survives a session gateway
    serving only a pinned set of GraphQL operations; on such a surface every
    `gh pr` subcommand returns 403 and this gate denied every squash merge it
    was asked about, including of leaf pull requests that were provably safe.

    The fallback exists so a surface where the reverse holds still gets an
    answer. If BOTH transports fail the probe still raises, and the caller
    still fails closed -- this widens how the question can be answered, never
    what happens when it cannot be.
    """
    entry = _probe_file_entry(repo, pr)
    if entry is not None:
        children = [int(c) for c in entry.get("children") or []]
        return str(entry.get("head") or ""), children

    if not repo:
        raise ProbeError("no --repo on the command and no probe file", "no_repo")

    failures: list[str] = []
    kinds: list[str] = []
    for label, resolver in (("rest", _stacked_children_rest), ("gh pr", _stacked_children_cli)):
        try:
            return resolver(repo, pr)
        except ProbeError as exc:
            failures.append(f"{label}: {exc}")
            kinds.append(getattr(exc, "kind", "unknown"))

    # Only call it a transport problem when EVERY transport was refused that
    # way. One blocked transport plus one real repository error is a repository
    # error, and saying otherwise would send the operator to the wrong remedy.
    # A substantive failure therefore outranks a blocked one, whichever
    # transport happened to run last.
    detail = "; ".join(failures)
    substantive = [k for k in kinds if k != "transport_blocked"]
    if substantive:
        kind = substantive[0]
    elif kinds:
        kind = "transport_blocked"
    else:
        kind = "unknown"
    raise ProbeError(detail, kind)


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
            return _stack_unknown_reason(pr, repo, str(exc), getattr(exc, "kind", "unknown"))
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
        else:
            # A REST merge carries both identifiers in the endpoint path, and
            # nowhere else. Without parsing them the stack probe returns early
            # on an empty PR number and every REST merge reads as safe -- so
            # recognising the transport in _segment_is_rest_pr_merge only
            # matters if the target can be resolved from it too.
            rest_match = REST_MERGE_TARGET.search(command)
            if rest_match:
                repo = f"{rest_match.group(1)}/{rest_match.group(2)}"
                pr = rest_match.group(3)
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


_LAST_EFFECTIVE: dict[str, str] = {}


def effective_merge_authority() -> dict[str, str]:
    """The last L9_MERGE_AUTHORIZED presence merge_gate actually read."""
    return dict(_LAST_EFFECTIVE)


def _human_breakglass() -> bool:
    """L9_MERGE_AUTHORIZED is human-set; it accepts the stack risk explicitly."""
    raw = os.environ.get("L9_MERGE_AUTHORIZED", "").strip()
    _LAST_EFFECTIVE["L9_MERGE_AUTHORIZED"] = "set" if raw else "empty"
    return bool(raw)


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
    # Heredoc bodies are DATA being written to a file, not commands being run.
    # Searching the raw string denied a document that merely quoted these forms
    # — writing a runbook or an audit that names the merge path was refused as
    # if it were a merge. Every genuinely executed command survives the strip.
    command = strip_heredoc_bodies(command)
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
            stack = _stack_safety_reason(command, tool_name, tool_input)
            if stack:
                return (
                    f"{stack} (effective L9_MERGE_AUTHORIZED="
                    f"{_LAST_EFFECTIVE.get('L9_MERGE_AUTHORIZED', 'unread')})"
                )
            return stack
        return None

    if _never_waive_tool(tool_name, tool_input):
        return NEVER_WAIVE_REASON

    if tool_name in {"Bash", "bash", "Shell", "shell"}:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if _never_waive_command(command):
            return NEVER_WAIVE_REASON
        # _command_is_pr_merge covers the REST endpoint reached by curl, which
        # is not a git/gh event and so lands here — where authorization runs.
        # MERGE_BASH must see the SAME heredoc-stripped text: searching the raw
        # command short-circuited the parsing _command_is_pr_merge already does,
        # so a file whose contents quoted the merge command was denied as one.
        if MERGE_BASH.search(strip_heredoc_bodies(command)) or _command_is_pr_merge(command):
            if not _merge_authorized(tool_name, tool_input):
                return (
                    f"{MERGE_DENY_REASON} (effective L9_MERGE_AUTHORIZED="
                    f"{_LAST_EFFECTIVE.get('L9_MERGE_AUTHORIZED', 'unread')})"
                )
            if _human_breakglass():
                return None
            stack = _stack_safety_reason(command, tool_name, tool_input)
            if stack:
                return (
                    f"{stack} (effective L9_MERGE_AUTHORIZED="
                    f"{_LAST_EFFECTIVE.get('L9_MERGE_AUTHORIZED', 'unread')})"
                )
            return stack
        return None

    if tool_name in DENY_TOOL_NAMES:
        if not _merge_authorized(tool_name, tool_input):
            return (
                f"{MERGE_DENY_REASON} (effective L9_MERGE_AUTHORIZED="
                f"{_LAST_EFFECTIVE.get('L9_MERGE_AUTHORIZED', 'unread')})"
            )
        if _human_breakglass():
            return None
        method = str(tool_input.get("merge_method") or tool_input.get("method") or "")
        pseudo = f"gh pr merge --{method.lower()}" if method else "gh pr merge"
        stack = _stack_safety_reason(pseudo, tool_name, tool_input)
        if stack:
            return (
                f"{stack} (effective L9_MERGE_AUTHORIZED="
                f"{_LAST_EFFECTIVE.get('L9_MERGE_AUTHORIZED', 'unread')})"
            )
        return stack
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
