#!/usr/bin/env python3
"""Deny merge / force / admin-destructive git operations (Autonomy Surface Profile).

Claude Code PreToolUse adapter: environment/agents/adapters/claude-code/hooks/merge_gate_wrap.py
calls this module. Brain lives under ops/ per CANONICAL_LAW §2.1.

Merge authority is a human act, never an invocation (CANONICAL_LAW §6.2.12,
§6.2.13). A merge — `gh pr merge`, the REST merge endpoint (gh api or curl),
an MCP merge tool, or `stack_safe_merge.py --run` — is allowed only when one
of these holds:

  a human GitHub authorization on the named head          # ordinary path (§6.2.13)
  L9_MERGE_AUTHORIZED=<nonempty reason string>            # human session breakglass
  ~/.l9/autonomy/merge-authorization.json                 # optional legacy grant
    {"authorizations": [{"repo": "org/repo", "pr": 53,
                          "head_sha": "<40-hex>", "issuer": "human",
                          "issued_at": <unix-seconds>,
                          "expires_at": <unix-seconds>, "reason": "..."}]}
    Overridable for tests via L9_MERGE_AUTHORIZATION_FILE (this hook's own
    environment, which a tool call cannot set). A grant authorizes only when:
    repo and PR number match exactly (a repository-wide "*" never matches);
    issuer is "human"; expires_at is in the future and no further out than
    MAX_GRANT_TTL_SECONDS; and the merge names the grant's exact head SHA
    (`--match-head-commit`, `-f sha=`, an MCP `sha`, or `--head-sha`). A moved
    head, an unnamed head, or a stale grant is MERGE_PENDING.

The ordinary records are a human GitHub approval or the exact line
``authorize merge <owner>/<repo>#<pr>@<sha>`` on that pull request
(``github_merge_authorization.py``), and an explicit merge instruction the
operator typed, recorded by the host's prompt hook
(``operator_merge_instruction.py``) and transcribed into the grant file by
``authorize_merge.py --operator-instruction``. A terminal transcription is not
required. An agent tool call may run ``authorize_merge.py`` only in that mode
and only when a live, uncancelled recorded instruction covers the named
repository and PR and the receipt is bound to the live session: the PreToolUse
event's ``session_id`` and ``transcript_path`` match the receipt's hook
provenance and a human turn of that transcript carries the instruction. Any
other run of it, an agent run of the instruction recorder (other than ``show``)
or of its host prompt adapters, a direct write of the grant file, the
instruction receipt or a host transcript, an approving review, or a posted
authorization line is denied (self-issuance). An operator cancellation ("do not
merge #n") recorded after a grant or alongside a GitHub record withdraws it:
the merge is MERGE_PENDING until the operator authorizes again.
Invoking /l9-pr-remediation, Converge, green CI, an L4 release receipt, make pr,
or an agent-written receipt is NOT authorization. A standing environment
boolean is not an authority either: the retired L9_AUTONOMY_AUTONOMOUS_MERGE
flag has no effect.

Shell ``git``/``gh`` commands are exempt from the *workflow* plane
(``git_execution_exemption``), but a merge is an effect, so merge authority
applies to them. Auto-merge enablement (`gh pr merge --auto`, MCP
`enable_pr_auto_merge`, REST `ccr/auto_merge`) merges at a future head no grant
can bind, and is denied without the human breakglass. Stack safety is applied
after authority: ``gh pr merge --squash|--rebase`` (or an unspecified method)
of a stack parent is denied on Shell and MCP alike. Agents must use
``stack_safe_merge.py`` so the method is selected in code, not guessed. The
never-waive set still applies to the MCP merge tool.

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
human grant does not -- the grant authorizes the merge, the probe still decides
whether the chosen method would orphan a child PR.
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
from github_merge_authorization import verdict_for_hook  # noqa: E402
from l4_local import workspace_from_event  # noqa: E402
from operator_merge_instruction import (  # noqa: E402
    INSTRUCTION_FILE_NAME,
    find_instruction,
    receipt_verdict,
    revocation_for,
    revocation_reason,
)

DENY_TOOL_NAMES = {
    "mcp__github__merge_pull_request",
    "MergePullRequest",
}
#: Any MCP server's merge tool (plugin-namespaced GitHub servers included).
MERGE_TOOL_SUFFIX = "__merge_pull_request"
AUTO_MERGE_TOOL_SUFFIX = "__enable_pr_auto_merge"

#: Human merge grants (authorize_merge.py writes these).
GRANT_ISSUER = "human"
MAX_GRANT_TTL_SECONDS = 4 * 60 * 60
GRANT_FILE_NAME = "merge-authorization.json"
#: Files only a human act may produce: the grant, and the host-recorded
#: operator instruction the grant may be transcribed from. An agent tool call
#: that writes either one is self-issuance.
PROTECTED_RECORD_FILES = frozenset({GRANT_FILE_NAME, INSTRUCTION_FILE_NAME})
OPERATOR_FLAG = "--operator-instruction"
#: The recorder and the host adapters that feed it. Only the host's own prompt
#: hook may run them; an agent tool call that does is manufacturing a receipt.
#: ``show`` is the recorder's read-only subcommand and stays allowed.
RECORDER_SCRIPT = "operator_merge_instruction.py"
_RECORDER_MODULE = RECORDER_SCRIPT.removesuffix(".py")
_RECORDER_TARGETS = frozenset(
    {RECORDER_SCRIPT, _RECORDER_MODULE, f"ops.autonomy.{_RECORDER_MODULE}"}
)
_RECORDER_ADAPTERS = frozenset(
    {
        "operator_merge_instruction_wrap.py",
        "before_submit_merge_instruction.py",
        "before-submit-merge-instruction.py",
    }
)
_HOOK_LAUNCHERS = frozenset({"l9_hook_exec.sh"})
#: Text that names the recorder's implementation inside inline interpreter code
#: (``python -c``, ``python - <<EOF``), where no script argv can be resolved.
_RECORDER_TOKENS = (
    _RECORDER_MODULE,
    "before_submit_merge_instruction",
    "before-submit-merge-instruction",
    "record_instructions(",
)
#: The host-written session transcript the gate corroborates a receipt against.
#: Appending to it would forge the corroboration, so a shell or file-tool write
#: to one is denied; reading it is not.
_HOST_TRANSCRIPT = re.compile(r"\.claude/projects/[^\s'\"<>|;&]*\.jsonl\b")
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
FILE_TOOL_NAMES = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOL_NAMES = {"Bash", "bash", "Shell", "shell"}
#: Heads that only read a file, so naming the grant file with them is not a write.
_READ_ONLY_HEADS = frozenset(
    "cat less more head tail jq ls stat wc test [ grep rg diff file git".split()
)
REST_AUTO_MERGE_PATH = re.compile(r"(?:^|/)repos/[^/\s]+/[^/\s]+/pulls/\d+/ccr/auto_merge/?$", re.I)

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

#: Copy-ready command prefixes for every grant / merge instruction this package
#: emits. They must run from any directory -- the human, or a remediation lane,
#: may be in a consumer repository where a relative ``ops/autonomy/...`` path does
#: not exist -- and AGENTS.md requires the locked governance interpreter.
GOV_PYTHON = '"$HOME/.cursor-governance/.venv/bin/python"'
GRANT_COMMAND = f'{GOV_PYTHON} "$HOME/.cursor-governance/ops/autonomy/authorize_merge.py"'
MERGE_COMMAND = f'{GOV_PYTHON} "$HOME/.cursor-governance/ops/autonomy/stack_safe_merge.py"'

MERGE_DENY_REASON = (
    "MERGE_PENDING: merging requires human authorization bound to this "
    "repository, PR and exact head SHA (CANONICAL_LAW §6.2.13). That is either an "
    "APPROVED review on that head, or a pull-request comment whose body contains the "
    "exact line `authorize merge <owner>/<repo>#<n>@<40-hex>`, from a human with write "
    "access; or an explicit merge instruction the operator typed in their own prompt, "
    f"recorded by the host prompt hook and transcribed with {GRANT_COMMAND} "
    "--operator-instruction --repo <owner/name> --pr <n> --head-sha <live sha>. "
    "L9-ORG-007 paths reject the PR author and accept no operator-prompt grant. "
    "Invoking /l9-pr-remediation, green CI, an L4 release, make pr, a local receipt, "
    "or a terminal transcription is not merge permission, and a standing environment "
    "boolean is not an authority. Report MERGE_PENDING and continue independent work. "
    f"With that authorization: {MERGE_COMMAND} --repo <owner/name> --pr <n> "
    "--head-sha <sha> --run (no --admin), oldest first."
)

SELF_ISSUE_REASON = (
    "Merge authorization is a human act, never by an agent "
    "(CANONICAL_LAW §6.2.13): an agent tool call may not run authorize_merge.py "
    "except as `--operator-instruction` backed by a host-recorded operator prompt "
    "that names this repository and PR, belongs to this live session, is "
    "corroborated by a human turn in the session's host transcript, and has not "
    f"been cancelled; may not run {RECORDER_SCRIPT} (other than `show`) or its host "
    f"prompt adapters; may not write {GRANT_FILE_NAME}, {INSTRUCTION_FILE_NAME} or a "
    "host transcript; and may not submit an approving review or post an "
    "`authorize merge` line. Report MERGE_PENDING: the operator authorizes in their "
    "own prompt, or on the pull request."
)

AUTO_MERGE_DENY_REASON = (
    "MERGE_PENDING: auto-merge (gh pr merge --auto, enable_pr_auto_merge, REST "
    "ccr/auto_merge) merges at a future head that no human grant can bind "
    "(CANONICAL_LAW §6.2.12). Only the human session breakglass "
    "L9_MERGE_AUTHORIZED=<reason> enables it."
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


def _argv_is_cli_merge(rest: list[str]) -> bool:
    return len(rest) >= 3 and rest[0] == "gh" and rest[1] == "pr" and rest[2] == "merge"


def _argv_is_rest_merge(rest: list[str]) -> bool:
    method = ""
    for index, word in enumerate(rest):
        if word in ("-X", "--method", "--request") and index + 1 < len(rest):
            method = rest[index + 1].strip("'\"").upper()
        elif word.startswith(("--method=", "--request=", "-X=")):
            method = word.split("=", 1)[1].strip("'\"").upper()
    return method == "PUT" and any(REST_MERGE_PATH.search(word.strip("'\"")) for word in rest)


def _segment_is_cli_pr_merge(segment: str) -> bool:
    """True when this segment *invokes* ``gh pr merge``, not when it mentions it."""
    if _argv_is_cli_merge(_argv_skip_env(segment_words(segment))):
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
    if _argv_is_rest_merge(_argv_skip_env(segment_words(segment))):
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


def _merge_segments(command: str, depth: int = 0) -> list[str]:
    """Every executed merge segment (innermost text), descending wrappers.

    Authority and stack safety are judged per segment, so a grant, a head SHA
    or a PR number elsewhere in the command line can never vouch for a merge
    that does not itself carry them, and a second merge in the same command is
    judged on its own.
    """
    found: list[str] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        rest = _argv_skip_env(segment_words(segment))
        if _argv_is_cli_merge(rest) or _argv_is_rest_merge(rest):
            found.append(segment)
        elif depth < 3:
            for sub in wrapper_subcommands(segment):
                found.extend(_merge_segments(sub, depth + 1))
    return found


#: `gh pr merge` flags that take a value, so the value is not the PR argument.
_CLI_VALUE_FLAGS = frozenset(
    "-R --repo -b --body -F --body-file -t --subject --match-head-commit -A --author-email".split()
)
_FIELD_FLAGS = ("-f", "-F", "--field", "--raw-field", "-d", "--data", "--data-raw")
_JSON_SHA = re.compile(r'"sha"\s*:\s*"([0-9a-fA-F]{7,40})"')


def _segment_merge_target(segment: str) -> tuple[str, str, str]:
    """(repo, pr, head_sha) named by THIS merge segment's own argv; '' when absent.

    The CLI PR must be a number (a branch or URL argument cannot be matched to
    a grant, so it reads as unknown and denies). The head is the segment's own
    ``--match-head-commit`` or REST ``sha`` field — the binding GitHub enforces.
    """
    rest = _argv_skip_env(segment_words(segment))
    if _argv_is_cli_merge(rest):
        args, pr, index = rest[3:], "", 0
        while index < len(args):
            word = args[index]
            if word in _CLI_VALUE_FLAGS:
                index += 2
                continue
            if not word.startswith("-"):
                pr = word.strip("'\"")
                break
            index += 1
        repo = _argv_value(rest, "--repo") or _argv_value(rest, "-R")
        return repo, pr if pr.isdigit() else "", _argv_value(rest, "--match-head-commit")
    repo = pr = sha = ""
    for index, word in enumerate(rest):
        match = REST_MERGE_TARGET.search(word.strip("'\""))
        if match and not pr:
            repo, pr = f"{match.group(1)}/{match.group(2)}", match.group(3)
        value = ""
        if word in _FIELD_FLAGS and index + 1 < len(rest):
            value = rest[index + 1].strip("'\"")
        elif word.startswith(tuple(f"{flag}=" for flag in _FIELD_FLAGS)):
            value = word.split("=", 1)[1].strip("'\"")
        if value.startswith("sha="):
            sha = value[4:]
        elif json_sha := _JSON_SHA.search(value):
            sha = json_sha.group(1)
    return repo, pr, sha


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


def _stack_safety_reason(
    command: str,
    tool_name: str,
    tool_input: dict[str, Any],
    target: tuple[str, str] | None = None,
) -> str | None:
    """Deny reason when this merge would orphan an open child PR, else None."""
    if os.environ.get("L9_STACK_CHECK_BYPASS", "").strip():
        return None
    repo, pr = target or _target_from_input(tool_name, tool_input)
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


def _instruction_file_path() -> Path:
    """The host-recorded operator instructions. Hook-environment override for tests only."""
    override = os.environ.get("L9_OPERATOR_INSTRUCTION_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".l9" / "autonomy" / INSTRUCTION_FILE_NAME


def _session_binding(event: dict[str, Any] | None) -> tuple[str, str]:
    """(session_id, transcript_path) the host put on the PreToolUse event."""
    if not isinstance(event, dict):
        return "", ""
    session = event.get("session_id")
    transcript = event.get("transcript_path")
    return (
        session.strip() if isinstance(session, str) else "",
        transcript.strip() if isinstance(transcript, str) else "",
    )


def _operator_grant_run_allowed(argv: list[str], event: dict[str, Any] | None = None) -> bool:
    """True when this ``authorize_merge.py`` argv transcribes a recorded operator instruction.

    The run must ask for ``--operator-instruction`` and name a repository and PR
    that a live, unrevoked receipt covers (a cohort receipt covers the pull
    requests in its recorded snapshot). The receipt must then be bound to the
    live session: the PreToolUse event names the session and its host-written
    transcript, the receipt must carry the same session and transcript in its
    hook provenance, and a human turn of that transcript must carry the
    instruction. The script also rechecks the live head and L9-ORG-007, so this
    check gates the attempt, not the grant. A host whose receipts cannot be
    bound this way (Cursor) is BLOCKED_HOST_ORIGIN for this channel.
    """
    if OPERATOR_FLAG not in argv:
        return False
    repo = _argv_value(argv, "--repo")
    pr = _argv_value(argv, "--pr")
    if not repo or not pr.isdigit():
        return False
    entry = find_instruction(repo, pr, path=_instruction_file_path())
    if entry is None:
        return False
    session, transcript = _session_binding(event)
    if not session or not transcript:
        return False
    return bool(receipt_verdict(entry, session_id=session, transcript_path=transcript).get("ok"))


def _is_interpreter(head: str) -> bool:
    name = Path(head.strip("'\"")).name
    return name.startswith("python") or head.startswith("$")


def _agent_runs_recorder(command: str) -> bool:
    """A shell segment that executes the instruction recorder or a host adapter.

    Resolved from argv like the grant-writer check, so ``cat``, ``grep``,
    ``git diff``, a linter or pytest naming the file only reads it, and the
    recorder's own read-only ``show`` stays allowed. Inline interpreter code
    (``python -c``, ``python - <<EOF``) that names the implementation is denied
    by text: no argv can be resolved for it, and the gap §6.2.12 names is
    exactly an agent reaching the Python API around the command filter.
    """
    inline_interpreter = False
    for words in _executed_segments(command):
        if not words:
            continue
        if Path(words[0].strip("'\"")).name in _HOOK_LAUNCHERS and any(
            Path(word.strip("'\"")).name in _RECORDER_ADAPTERS for word in words[1:]
        ):
            return True
        target = _invoked_target(words)
        if target is None:
            inline_interpreter = inline_interpreter or _is_interpreter(words[0])
            continue
        name, argv = target
        if name in _RECORDER_TARGETS:
            if argv and argv[0].strip("'\"") == "show":
                continue
            return True
        if name in _RECORDER_ADAPTERS:
            return True
        if name in _HOOK_LAUNCHERS and any(
            Path(word.strip("'\"")).name in _RECORDER_ADAPTERS for word in argv
        ):
            return True
    if inline_interpreter and any(token in command for token in _RECORDER_TOKENS):
        return True
    return False


def _shell_writes_host_transcript(command: str) -> bool:
    """A shell segment that writes a host session transcript (``.claude/projects/*.jsonl``)."""
    if not _HOST_TRANSCRIPT.search(command):
        return False
    for segment in split_segments(command):
        if not _HOST_TRANSCRIPT.search(segment):
            continue
        words = _argv_skip_env(segment_words(segment))
        head = Path(words[0].strip("'\"")).name if words else ""
        if head not in _READ_ONLY_HEADS or ">" in segment:
            return True
    for words in _executed_segments(command):
        if words and _invoked_target(words) is None and _is_interpreter(words[0]):
            return True
    return False


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


def grant_matches(
    entry: Any, repo: str, pr: str, head_sha: str, *, now: float | None = None
) -> bool:
    """True when ``entry`` is a live human grant for exactly repo#pr@head_sha.

    Every binding is required. A repository-wide "*" scope, a missing or
    unparseable head, a non-human issuer, a missing or past expiry, and an
    expiry further out than MAX_GRANT_TTL_SECONDS all fail: authorize_merge.py
    never writes such an entry, so one on disk is legacy or forged.
    """
    if not isinstance(entry, dict):
        return False
    stamp = time.time() if now is None else now
    expires = entry.get("expires_at")
    if not isinstance(expires, (int, float)) or isinstance(expires, bool):
        return False
    if expires <= stamp or expires > stamp + MAX_GRANT_TTL_SECONDS:
        return False
    if entry.get("issuer") != GRANT_ISSUER:
        return False
    entry_repo = str(entry.get("repo") or "")
    if not entry_repo or not repo or entry_repo != repo:
        return False
    entry_pr = str(entry.get("pr") or entry.get("number") or "").strip()
    if entry_pr in REPO_SCOPE or not entry_pr.isdigit() or not pr or entry_pr != str(pr).strip():
        return False
    entry_sha = str(entry.get("head_sha") or "").strip().lower()
    named_sha = head_sha.strip().lower()
    return bool(_FULL_SHA.match(entry_sha)) and named_sha == entry_sha


def find_grant(
    repo: str,
    pr: str,
    head_sha: str,
    *,
    path: Path | None = None,
    now: float | None = None,
) -> dict[str, Any] | None:
    """The first live human grant for repo#pr@head_sha in ``path``, else None."""
    source = path or _auth_file_path()
    if not source.is_file():
        return None
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        entries = payload.get("authorizations", []) if isinstance(payload, dict) else []
    except (json.JSONDecodeError, OSError):
        return None
    for entry in entries if isinstance(entries, list) else []:
        if grant_matches(entry, repo, pr, head_sha, now=now):
            return dict(entry)
    return None


def _revocation(repo: str, pr: str, *, since: float | None = None) -> dict[str, Any] | None:
    """The operator's live cancellation covering ``repo#pr``, issued at or after ``since``.

    "Do not merge #735", "cancel the merge of #735" and the repository-wide
    forms are recorded by the same host prompt hook as the instruction they
    withdraw. The latest instruction wins: a cancellation withdraws every
    authority issued before it (a grant's ``issued_at`` is ``since``) until the
    operator authorizes again. A GitHub record carries no comparable issue time
    here, so a live cancellation withdraws it until a newer prompt instruction
    re-authorizes the pull request.
    """
    if not repo or not str(pr).strip().isdigit():
        return None
    return revocation_for(repo, str(pr).strip(), path=_instruction_file_path(), since=since)


def _file_authorizes(repo: str, pr: str, head_sha: str = "") -> bool:
    """True when a live, unrevoked human grant binds this exact repo, PR and named head."""
    grant = find_grant(repo, pr, head_sha)
    if grant is None:
        return False
    issued = grant.get("issued_at")
    since = (
        float(issued) if isinstance(issued, (int, float)) and not isinstance(issued, bool) else None
    )
    return _revocation(repo, pr, since=since) is None


def _github_verdict(repo: str, pr: str, head_sha: str) -> dict[str, Any]:
    """GitHub authorization verdict. A short or missing SHA fails closed."""
    if not repo or not str(pr).strip().isdigit() or not _FULL_SHA.match(head_sha.strip().lower()):
        return {
            "authorized": False,
            "reason": "the merge did not name the repository, PR and full head SHA",
        }
    return verdict_for_hook(repo, str(pr).strip(), head_sha.strip().lower())


def _github_authorizes(repo: str, pr: str, head_sha: str) -> bool:
    """True when a human GitHub record covers this head and no operator cancellation stands."""
    if not _github_verdict(repo, pr, head_sha).get("authorized"):
        return False
    return _revocation(repo, pr) is None


def _missing_detail(repo: str, pr: str, head_sha: str) -> str:
    """Why no authority covers the merge: an operator cancellation first, else GitHub's reason."""
    revoked = _revocation(repo, pr)
    if revoked is not None:
        return revocation_reason(revoked)
    return str(_github_verdict(repo, pr, head_sha).get("reason") or "")


_AUTH_LINE_IN_COMMAND = re.compile(r"(?i)authorize merge [\w.-]+/[\w.-]+#[1-9]\d*@[0-9a-fA-F]{40}")
_APPROVE_EVENT = re.compile(r'(?i)\bevent"?\s*[=:]\s*"?APPROVE\b')
#: MCP tools that create the review or comment the gate trusts (same act as
#: ``gh pr review`` / ``gh pr comment``): denied when they carry the record.
_GITHUB_RECORD_TOOL_SUFFIXES = (
    "__pull_request_review_write",
    "__add_comment_to_pending_review",
    "__add_issue_comment",
    "__update_issue_comment",
    "__add_reply_to_pull_request_comment",
)
_PAYLOAD_VALUE_FLAGS = {
    "-f",
    "--raw-field",
    "-F",
    "--field",
    "--body",
    "-b",
    "-d",
    "--data",
    "--data-binary",
    "--data-raw",
}
_MAX_PAYLOAD_BYTES = 1_000_000


def _payload_text(path_text: str) -> str | None:
    """File body, or None when the path is missing, huge, or not a file."""
    raw = path_text.strip().strip("'\"")
    if not raw or raw == "-":
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        if not path.is_file() or path.stat().st_size > _MAX_PAYLOAD_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _referenced_payloads(words: list[str]) -> tuple[str, bool]:
    """Text of inline and file payloads. The flag is true when a file cannot be read.

    ``gh pr review`` and ``gh pr comment`` use ``-F`` as a body file. ``gh api``
    uses ``-F`` as a field, and ``@path`` as that field's file.
    """
    pr_body = _gh_record_subcommand(words) is not None
    file_flags = {"--body-file", "--input"}
    value_flags = set(_PAYLOAD_VALUE_FLAGS)
    if pr_body:
        file_flags.add("-F")
        value_flags.discard("-F")
    chunks: list[str] = []
    hidden = False
    index = 0
    while index < len(words):
        word = words[index]
        value = ""
        consumed = 1
        if word in value_flags and index + 1 < len(words):
            value = words[index + 1].strip("'\"")
            consumed = 2
        else:
            for flag in value_flags:
                if word.startswith(f"{flag}="):
                    value = word.split("=", 1)[1].strip("'\"")
                    break
        index += consumed
        if not value:
            continue
        if value.startswith("@"):
            body = _payload_text(value[1:])
            if body is None:
                hidden = True
            else:
                chunks.append(body)
        else:
            chunks.append(value)
    for flag in file_flags:
        named = _argv_value(words, flag)
        if not named:
            continue
        body = _payload_text(named)
        if body is None:
            hidden = True
        else:
            chunks.append(body)
    return "\n".join(chunks), hidden


def _url_is_github_api_record(token: str) -> bool:
    """True when this argv token is a URL whose host is exactly api.github.com."""
    from urllib.parse import urlparse

    parsed = urlparse(token.strip("'\""))
    if (parsed.hostname or "").lower() != "api.github.com":
        return False
    path = parsed.path or ""
    return "/reviews" in path or "/comments" in path


def _gh_record_subcommand(words: list[str]) -> str | None:
    """``review`` or ``comment`` when argv is ``gh pr review|comment`` or ``gh issue comment``.

    ``gh`` is matched by basename: ``/usr/bin/gh`` creates the same record.
    """
    if len(words) < 3 or Path(words[0]).name != "gh":
        return None
    if words[1] == "pr" and words[2] in {"review", "comment"}:
        return words[2]
    if words[1] == "issue" and words[2] == "comment":
        return "comment"
    return None


def _is_authorization_write(words: list[str]) -> bool:
    """True when this argv can create the GitHub review or comment the gate trusts."""
    if not words:
        return False
    head = Path(words[0]).name
    joined = " ".join(words)
    subcommand = _gh_record_subcommand(words)
    review = subcommand == "review"
    comment = subcommand == "comment"
    api = (
        head == "gh"
        and len(words) >= 2
        and words[1] == "api"
        and any(
            token in joined
            for token in (
                "/reviews",
                "/comments",
                "addPullRequestReview",
                "submitPullRequestReview",
                "addComment",
            )
        )
    )
    curl = head == "curl" and any(_url_is_github_api_record(word) for word in words)
    if not (review or comment or api or curl):
        return False
    if api or curl:
        method = (
            _argv_value(words, "-X")
            or _argv_value(words, "--method")
            or _argv_value(words, "--request")
        ).upper()
        writes = method in {"POST", "PATCH", "PUT"} or any(
            token in words for token in ("-d", "--data", "--data-binary", "--data-raw", "--input")
        )
        if api and "graphql" in words:
            writes = True
        if not writes:
            return False
    return True


def _segment_posts_github_authorization(words: list[str]) -> bool:
    """True when this argv would create, or could hide, the GitHub record the gate trusts."""
    if not _is_authorization_write(words):
        return False
    joined = " ".join(words)
    if any(token in joined for token in ("$(", "`", "<<")) or " <" in f" {joined}":
        return True
    if "--editor" in words or "--web" in words or "--approve" in words:
        return True
    if _gh_record_subcommand(words) == "review" and "-a" in words:
        return True  # gh pr review -a is --approve
    visible, hidden = _referenced_payloads(words)
    if hidden:
        return True
    blob = f"{joined}\n{visible}"
    return _AUTH_LINE_IN_COMMAND.search(blob) is not None or _APPROVE_EVENT.search(blob) is not None


def _mcp_posts_github_authorization(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """True when an MCP review/comment tool would submit APPROVE or post the line."""
    if not tool_name.endswith(_GITHUB_RECORD_TOOL_SUFFIXES):
        return False
    if str(tool_input.get("event") or "").strip().upper() == "APPROVE":
        return True
    return _AUTH_LINE_IN_COMMAND.search(json.dumps(tool_input, default=str)) is not None


def _shell_posts_github_authorization(command: str) -> bool:
    if ("<<" in command or "$(" in command or "`" in command) and any(
        _is_authorization_write(words) for words in _executed_segments(command)
    ):
        return True
    return any(_segment_posts_github_authorization(words) for words in _executed_segments(command))


def live_head_sha(repo: str, pr: str) -> str:
    """The PR's current head SHA from GitHub, lowercased. Raises ProbeError.

    L9_STACK_PROBE_FILE entries may carry ``sha`` so tests stay offline; an
    entry without one reports the head as unknown rather than guessing.
    """
    entry = _probe_file_entry(repo, pr)
    if entry is not None:
        sha = str(entry.get("sha") or "").strip().lower()
        if not _FULL_SHA.match(sha):
            raise ProbeError("probe file names no head sha", "probe_failed")
        return sha
    if not repo:
        raise ProbeError("no repository to recheck the head against", "no_repo")
    view = _gh_rest_json(f"repos/{repo}/pulls/{pr}")
    sha = str(((view or {}).get("head") or {}).get("sha") or "").strip().lower()
    if not _FULL_SHA.match(sha):
        raise ProbeError("REST did not report a head sha", "probe_failed")
    return sha


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
    return _file_authorizes(repo, pr, head_sha) or _github_authorizes(repo, pr, head_sha)


def _executed_segments(command: str, depth: int = 0) -> list[list[str]]:
    """argv of every executed segment, descending ``bash -c``-style wrappers."""
    found: list[list[str]] = []
    for segment in split_segments(strip_heredoc_bodies(command)):
        found.append(_argv_skip_env(segment_words(segment)))
        if depth < 3:
            for sub in wrapper_subcommands(segment):
                found.extend(_executed_segments(sub, depth + 1))
    return found


_PASSTHROUGH_HEADS = {"env", "exec", "nohup", "nice", "command"}


def _invoked_target(words: list[str], depth: int = 0) -> tuple[str, list[str]] | None:
    """(script-or-module, argv after it) that ``words`` executes, else None.

    The target of an interpreter is its first non-option argument or its ``-m``
    module — so ``python3 x/authorize_merge.py`` runs the script while ``python
    -m ruff check x/authorize_merge.py`` runs ruff. A head that is an unexpanded
    variable (``"$GOV_PY"``) is read as an interpreter, because that is how the
    governed skills spell the locked venv. Launchers (``env``, ``uv run``,
    ``timeout``) are looked through.
    """
    if not words or depth > 4:
        return None
    head = words[0].strip("'\"")
    name = Path(head).name
    rest = words[1:]
    if name in _PASSTHROUGH_HEADS:
        while rest and ("=" in rest[0] or rest[0].startswith("-")):
            rest = rest[1:]
        return _invoked_target(rest, depth + 1)
    if name == "timeout":
        while rest and rest[0].startswith("-"):
            rest = rest[1:]
        return _invoked_target(rest[1:], depth + 1)
    if name == "uv":
        if rest[:1] != ["run"]:
            return None
        rest = rest[1:]
        valued = {"--with", "--python", "--project", "--directory"}
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in valued else rest[1:]
        return _invoked_target(rest, depth + 1)
    if name.startswith("python") or head.startswith("$"):
        index = 0
        while index < len(rest):
            word = rest[index]
            if word == "-m" and index + 1 < len(rest):
                return rest[index + 1], rest[index + 2 :]
            if word in {"-c", "-"}:
                return None
            if word.startswith("-"):
                index += 1
                continue
            return Path(word).name, rest[index + 1 :]
        return None
    return name, rest


def _script_argvs(command: str, script: str) -> list[list[str]]:
    """argv after ``script`` for every segment of the command that executes it.

    ``cat``, ``git diff``, ``grep`` or a linter naming the file only reads it.
    """
    module = script.removesuffix(".py")
    found: list[list[str]] = []
    for words in _executed_segments(command):
        target = _invoked_target(words)
        if target and target[0] in {script, module, f"ops.autonomy.{module}"}:
            found.append(target[1])
    return found


def _argv_value(argv: list[str], flag: str) -> str:
    for index, word in enumerate(argv):
        if word == flag and index + 1 < len(argv):
            return argv[index + 1].strip("'\"")
        if word.startswith(f"{flag}="):
            return word.split("=", 1)[1].strip("'\"")
    return ""


def _shell_writes_grant_file(command: str) -> bool:
    """A shell segment that names the grant or instruction file with anything but a reader.

    Name-based on purpose and therefore a speed bump, not a proof: it stops the
    ordinary agent path (``cat > …``, ``tee``, ``python - <<…``, ``cp``) while
    deliberate obfuscation remains the host-enforcement gap of §6.2.12.
    """
    if not any(name in command for name in PROTECTED_RECORD_FILES):
        return False
    for segment in split_segments(command):
        if not any(name in segment for name in PROTECTED_RECORD_FILES):
            continue
        words = _argv_skip_env(segment_words(segment))
        head = Path(words[0]).name if words else ""
        if head not in _READ_ONLY_HEADS or ">" in segment:
            return True
    return False


def _file_tool_writes_grant_file(tool_input: dict[str, Any]) -> bool:
    for key in ("file_path", "notebook_path", "path"):
        value = str(tool_input.get(key) or "")
        if value and Path(value).name in PROTECTED_RECORD_FILES:
            return True
        if value and _HOST_TRANSCRIPT.search(value):
            return True
    return False


def _command_enables_auto_merge(command: str) -> bool:
    """`gh pr merge --auto` or a PUT to the REST auto-merge route."""
    for words in _executed_segments(command):
        if len(words) >= 3 and words[:3] == ["gh", "pr", "merge"] and "--auto" in words:
            return True
        method = _argv_value(words, "-X") or _argv_value(words, "--method")
        if method.upper() == "PUT" and any(
            REST_AUTO_MERGE_PATH.search(word.strip("'\"")) for word in words
        ):
            return True
    return False


def _is_merge_tool(tool_name: str) -> bool:
    return tool_name in DENY_TOOL_NAMES or tool_name.endswith(MERGE_TOOL_SUFFIX)


def _stack_safe_run_reason(argv: list[str]) -> str | None:
    """Deny a ``stack_safe_merge.py --run`` that no human grant covers.

    The helper's own entrypoint re-verifies the grant against the live head; this
    check exists because its inner ``gh`` calls are subprocesses no hook sees.
    """
    if "--run" not in argv:
        return None
    if _human_breakglass():
        return None
    repo = _argv_value(argv, "--repo")
    pr = _argv_value(argv, "--pr")
    head_sha = _argv_value(argv, "--head-sha")
    if _file_authorizes(repo, pr, head_sha) or _github_authorizes(repo, pr, head_sha):
        return None
    detail = _missing_detail(repo, pr, head_sha)
    return (
        f"{MERGE_DENY_REASON} Missing prerequisite: {detail}. "
        f"(target {repo or '<repo?>'}#{pr or '<pr?>'}"
        f"@{head_sha or '<head-sha not named>'}; effective L9_MERGE_AUTHORIZED="
        f"{_LAST_EFFECTIVE.get('L9_MERGE_AUTHORIZED', 'unread')})"
    )


def _authorized_merge_reason(
    command: str,
    tool_name: str,
    tool_input: dict[str, Any],
    target: tuple[str, str, str] | None = None,
) -> str | None:
    """Authority first, then stack safety. None when the merge may proceed.

    ``target`` is (repo, pr, head_sha) read from the merge segment itself; MCP
    calls leave it None and are read from their structured input.
    """
    effective = lambda: _LAST_EFFECTIVE.get("L9_MERGE_AUTHORIZED", "unread")  # noqa: E731
    if target is None:
        authorized = _merge_authorized(tool_name, tool_input)
        stack_target = None
    else:
        authorized = _human_breakglass() or _file_authorizes(*target) or _github_authorizes(*target)
        stack_target = (target[0], target[1])
    if not authorized:
        if target is None:
            named_repo, named_pr = _target_from_input(tool_name, tool_input)
            named_sha = _head_sha_from_input(tool_name, tool_input)
        else:
            named_repo, named_pr, named_sha = target
        detail = _missing_detail(named_repo, named_pr, named_sha)
        missing = f" Missing prerequisite: {detail}." if detail else ""
        return f"{MERGE_DENY_REASON}{missing} (effective L9_MERGE_AUTHORIZED={effective()})"
    if _human_breakglass():
        return None
    stack = _stack_safety_reason(command, tool_name, tool_input, stack_target)
    if stack:
        return f"{stack} (effective L9_MERGE_AUTHORIZED={effective()})"
    return None


def _shell_merge_reason(command: str, tool_name: str) -> str | None:
    """Judge every executed merge segment on its own argv; deny the first failure.

    A command that names a merge only in a form no segment parse can resolve
    (``eval``, an unusual wrapper) cannot be bound to a grant, so it is denied
    unless the human breakglass is set.
    """
    segments = _merge_segments(command)
    if not segments:
        if _human_breakglass():
            return None
        return (
            f"{MERGE_DENY_REASON} (no executed merge segment could be resolved to a "
            "repository, PR and head; run the merge as its own command)"
        )
    for segment in segments:
        if "--admin" in _argv_skip_env(segment_words(segment)):
            return NEVER_WAIVE_REASON
        reason = _authorized_merge_reason(
            segment, tool_name, {"command": segment}, _segment_merge_target(segment)
        )
        if reason:
            return reason
    return None


def _never_waive_command(command: str) -> bool:
    return bool(
        FORCE_PUSH_BASH.search(command)
        or HARD_RESET_BASH.search(command)
        or CLEAN_FD_BASH.search(command)
        or ADMIN_MERGE_BASH.search(command)
    )


def _never_waive_tool(tool_name: str, tool_input: dict[str, Any]) -> bool:
    if _is_merge_tool(tool_name) and bool(
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
    event: dict[str, Any] | None = None,
) -> str | None:
    """Return deny reason or None if allowed to proceed (no decision).

    Shell git/gh commands are exempt from the workflow plane, not from merge
    authority: a merge is an effect (§6.2.12). Every merge transport needs a
    human grant (or the human breakglass); stack safety runs after authority.
    ``event`` is the host's PreToolUse payload; its ``session_id`` and
    ``transcript_path`` bind an operator receipt to the live session.
    """
    del root  # signature kept for hook callers

    if tool_name in FILE_TOOL_NAMES:
        return SELF_ISSUE_REASON if _file_tool_writes_grant_file(tool_input) else None

    if _mcp_posts_github_authorization(tool_name, tool_input):
        return SELF_ISSUE_REASON

    if tool_name in SHELL_TOOL_NAMES:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        for grant_argv in _script_argvs(command, "authorize_merge.py"):
            if not _operator_grant_run_allowed(grant_argv, event):
                return SELF_ISSUE_REASON
        if _agent_runs_recorder(command):
            return SELF_ISSUE_REASON
        if _shell_writes_grant_file(command) or _shell_writes_host_transcript(command):
            return SELF_ISSUE_REASON
        if _shell_posts_github_authorization(command):
            return SELF_ISSUE_REASON
        for run_argv in _script_argvs(command, "stack_safe_merge.py"):
            reason = _stack_safe_run_reason(run_argv)
            if reason:
                return reason
        if _command_enables_auto_merge(command) and not _human_breakglass():
            return AUTO_MERGE_DENY_REASON

    if event_is_git_or_gh(tool_name, tool_input):
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if _command_is_pr_merge(command):
            return _shell_merge_reason(command, tool_name)
        return None

    if _never_waive_tool(tool_name, tool_input):
        return NEVER_WAIVE_REASON

    if tool_name in SHELL_TOOL_NAMES:
        command = str(tool_input.get("command") or tool_input.get("cmd") or "")
        if _never_waive_command(command):
            return NEVER_WAIVE_REASON
        # _command_is_pr_merge covers the REST endpoint reached by curl, which
        # is not a git/gh event and so lands here.
        if MERGE_BASH.search(command) or _command_is_pr_merge(command):
            return _shell_merge_reason(command, tool_name)
        return None

    if tool_name.endswith(AUTO_MERGE_TOOL_SUFFIX):
        return None if _human_breakglass() else AUTO_MERGE_DENY_REASON

    if _is_merge_tool(tool_name):
        method = str(tool_input.get("merge_method") or tool_input.get("method") or "")
        pseudo = f"gh pr merge --{method.lower()}" if method else "gh pr merge"
        return _authorized_merge_reason(pseudo, tool_name, tool_input)
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
    reason = evaluate(tool_name, tool_input, root=root, event=event)
    if reason:
        return _deny(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
