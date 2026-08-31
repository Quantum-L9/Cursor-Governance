#!/usr/bin/env python3
"""Decide what happens to a pull request: merge | fix | wait | leftover.

This exists because a remediator kept reporting blockers it had never verified.
It read `statusCheckRollup`, which lists *every* check, and treated any red one
as a merge blocker -- so an optional scanner failing on an empty API key was
indistinguishable from a required gate. On the next run the same PRs merged on
the first attempt. The missing datum was never severity or ownership; it was
*which checks are required*.

Two axes, and only one of them belongs in prose:

  edit  -- may I patch this file? (CODEBASE / CI_PIPELINE / ENVIRONMENT /
           HUMAN / FALSE_POSITIVE) stays a judgement in the skill pack.
  board -- what happens to this PR? is computed here, from required-check
           identity and conflicted paths, and never inferred from
           `mergeStateStatus` alone, from a check conclusion without the
           required set, or from an issue body asserting "do not merge".

Required checks are the union of two sources, because a repository can be
protected entirely by a ruleset and carry no branch-protection object at all:

  GET /repos/{owner}/{repo}/branches/{branch}/protection   (contexts)
  GET /repos/{owner}/{repo}/rules/branches/{branch}        (required_status_checks)

Reading only the first is the bug that matters: it reports zero required checks
on a ruleset-protected repository, and zero required checks reads as "nothing
is blocking, merge it".

`leftover` is never inferred. It is an *input*: the caller declares a named
HUMAN decision (--human-decision) or a required check it cannot fix without
editing CI (--unfixable-check), both of which are evidence the caller already
holds. Everything else resolves to work (`fix`), waiting (`wait`), or merge.

This helper is read-only advice. It never merges. `stack_safe_merge.py --run`
remains the only sanctioned merge executor, and it alone chooses the method.

Probe: L9_PR_BOARD_PROBE_FILE (tests / offline) or live `gh`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
for _path in (str(_HERE), str(_ROOT / "ops" / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from merge_gate import _gh_json  # noqa: E402
from sync_generated_artifacts import is_generated_path  # noqa: E402

MERGE = "merge"
FIX = "fix"
WAIT = "wait"
LEFTOVER = "leftover"
BOARD_VALUES = (MERGE, FIX, WAIT, LEFTOVER)

# A required check in one of these states is failing, not pending.
FAILING_STATES = frozenset(
    {
        "FAILURE",
        "ERROR",
        "CANCELLED",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
        "STALE",
    }
)
# EXPECTED means the branch requires a context that has not reported at all.
PENDING_STATES = frozenset({"PENDING", "QUEUED", "IN_PROGRESS", "WAITING", "EXPECTED", "REQUESTED"})

PR_VIEW_FIELDS = (
    "number,headRefName,baseRefName,mergeable,mergeStateStatus,reviewDecision,"
    "statusCheckRollup,headRefOid,isDraft"
)

# A state outside this set is never a merge. CLEAN is green; UNSTABLE is green
# required checks with a red optional one; HAS_HOOKS is CLEAN with hooks.
MERGE_READY_STATES = frozenset({"CLEAN", "UNSTABLE", "HAS_HOOKS"})

# reviewThreads is GraphQL-only -- it is not a `gh pr view --json` field, and
# naming it there fails the whole call, which is how every live verdict came
# back as "telemetry unavailable" the first time this ran.
THREADS_QUERY = """
query($owner:String!, $name:String!, $pr:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$pr) {
      reviewThreads(first:100) { nodes { isResolved } }
    }
  }
}
"""


class BoardError(RuntimeError):
    """Telemetry could not be resolved. Callers degrade to WAIT, never MERGE."""


def _probe_entry(repo: str, pr: str) -> dict[str, Any] | None:
    """Injected telemetry, so the verdict is deterministic offline and in tests."""
    override = os.environ.get("L9_PR_BOARD_PROBE_FILE", "").strip()
    if not override:
        return None
    try:
        payload = json.loads(Path(override).expanduser().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise BoardError(f"unreadable L9_PR_BOARD_PROBE_FILE ({exc})") from exc
    if not isinstance(payload, dict):
        raise BoardError("L9_PR_BOARD_PROBE_FILE is not a JSON object")
    entry = payload.get(f"{repo}#{pr}", payload.get(f"#{pr}", payload.get("default")))
    if entry is None:
        raise BoardError(f"L9_PR_BOARD_PROBE_FILE has no entry for {repo}#{pr}")
    if not isinstance(entry, dict):
        raise BoardError("L9_PR_BOARD_PROBE_FILE entry is not a JSON object")
    return entry


def _pr_view(repo: str, pr: str) -> dict[str, Any]:
    try:
        view = _gh_json(["pr", "view", pr, "--repo", repo, "--json", PR_VIEW_FIELDS])
    except RuntimeError as exc:
        raise BoardError(f"gh pr view failed: {exc}") from exc
    if not isinstance(view, dict):
        raise BoardError("gh pr view emitted no object")
    return view


def ruleset_required(repo: str, branch: str) -> tuple[list[str], bool]:
    """Required contexts and the strict flag from repository rulesets.

    A missing or unreadable ruleset is not zero required checks -- it is
    unknown, and the branch-protection source still gets a turn. Only an empty
    successful answer means "this source requires nothing".
    """
    try:
        rules = _gh_json(["api", f"repos/{repo}/rules/branches/{branch}"])
    except RuntimeError as exc:
        raise BoardError(f"ruleset probe failed: {exc}") from exc
    contexts: list[str] = []
    strict = False
    for rule in rules or []:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        params = rule.get("parameters") or {}
        strict = strict or bool(params.get("strict_required_status_checks_policy"))
        for check in params.get("required_status_checks") or []:
            context = str((check or {}).get("context") or "").strip()
            if context:
                contexts.append(context)
    return contexts, strict


def _required_app_ids(rules: list[Any]) -> dict[str, str]:
    """Context -> integration/app id when a ruleset or protection pins a producer."""
    pinned: dict[str, str] = {}
    for rule in rules or []:
        if not isinstance(rule, dict) or rule.get("type") != "required_status_checks":
            continue
        for check in (rule.get("parameters") or {}).get("required_status_checks") or []:
            context = str((check or {}).get("context") or "").strip()
            app_id = (check or {}).get("integration_id")
            if context and app_id is not None:
                pinned[context] = str(app_id)
    return pinned


def protection_required(repo: str, branch: str) -> tuple[list[str], bool]:
    """Required contexts and the strict flag from classic branch protection.

    404 is the normal answer on a ruleset-only repository and means this source
    requires nothing -- not that the probe broke.
    """
    try:
        payload = _gh_json(["api", f"repos/{repo}/branches/{branch}/protection"])
    except RuntimeError as exc:
        if "404" in str(exc) or "Not Found" in str(exc) or "Branch not protected" in str(exc):
            return [], False
        raise BoardError(f"branch protection probe failed: {exc}") from exc
    checks = (payload or {}).get("required_status_checks") or {}
    contexts = [str(c).strip() for c in (checks.get("contexts") or []) if str(c).strip()]
    for check in checks.get("checks") or []:
        context = str((check or {}).get("context") or "").strip()
        if context and context not in contexts:
            contexts.append(context)
    return contexts, bool(checks.get("strict"))


def required_checks(repo: str, branch: str) -> tuple[list[str], bool]:
    """Union both protection sources. Strict if either source is strict."""
    ruleset_contexts, ruleset_strict = ruleset_required(repo, branch)
    protection_contexts, protection_strict = protection_required(repo, branch)
    merged = list(dict.fromkeys([*ruleset_contexts, *protection_contexts]))
    return merged, ruleset_strict or protection_strict


def _rollup_app_id(node: dict[str, Any]) -> str:
    app = node.get("app") or node.get("checkSuite") or {}
    if isinstance(app, dict):
        nested = app.get("app") if isinstance(app.get("app"), dict) else app
        for key in ("databaseId", "id", "integration_id", "slug"):
            value = nested.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    for key in ("integration_id", "app_id"):
        value = node.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _rollup_states(
    view: dict[str, Any], required_apps: dict[str, str] | None = None
) -> dict[str, str]:
    """Map check name -> state, over both check runs and legacy statuses.

    When a required context is pinned to an integration, prefer the rollup
    node whose app identity matches. Name-only fallback stays for telemetry
    that does not carry an app id.
    """
    pinned = required_apps or {}
    states: dict[str, str] = {}
    pinned_hit: set[str] = set()
    for node in view.get("statusCheckRollup") or []:
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or node.get("context") or "").strip()
        if not name:
            continue
        state = str(node.get("conclusion") or node.get("state") or node.get("status") or "").upper()
        # A check run that is still running reports an empty conclusion.
        if not state:
            state = "PENDING"
        app_id = _rollup_app_id(node)
        want = pinned.get(name)
        if want:
            if app_id and app_id != want:
                continue
            if app_id and app_id == want:
                states[name] = state
                pinned_hit.add(name)
                continue
        if name not in pinned_hit:
            states[name] = state
    return states


def conflicted_paths(base: str, head: str) -> list[str]:
    """Conflicted paths for the merge, or [] when git cannot answer.

    Path-level truth matters: a PR whose only conflict is a regenerated
    manifest is work, not a wall, and `mergeStateStatus: CONFLICTING` cannot
    tell those apart.
    """
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "merge-tree", "--write-tree", "--name-only", base, head],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode == 0:
        return []
    lines = [line.strip() for line in (proc.stdout or "").splitlines()]
    # Output is the tree oid, a blank line, then the conflicted paths.
    if lines and lines[0] and " " not in lines[0]:
        lines = lines[1:]
    return [line for line in lines if line]


def _unresolved_threads(view: dict[str, Any]) -> int:
    threads = view.get("reviewThreads")
    nodes = threads.get("nodes") if isinstance(threads, dict) else threads
    if not isinstance(nodes, list):
        return 0
    return sum(1 for node in nodes if isinstance(node, dict) and node.get("isResolved") is False)


def fetch_review_threads(repo: str, pr: str) -> dict[str, Any] | None:
    """Unresolved-thread nodes over GraphQL, or None when unavailable.

    "A conversation must be resolved" is a real merge blocker (this repo's own
    ruleset sets required_review_thread_resolution), so the board needs it. A
    failure here is not fatal: mergeStateStatus still refuses to be CLEAN, and
    the ladder never reads a non-ready state as a merge.
    """
    owner, _, name = repo.partition("/")
    if not owner or not name:
        return None
    try:
        payload = _gh_json(
            [
                "api",
                "graphql",
                "-f",
                f"query={THREADS_QUERY}",
                "-F",
                f"owner={owner}",
                "-F",
                f"name={name}",
                "-F",
                f"pr={int(pr)}",
            ]
        )
    except (RuntimeError, ValueError):
        return None
    pull = (((payload or {}).get("data") or {}).get("repository") or {}).get("pullRequest") or {}
    threads = pull.get("reviewThreads")
    return threads if isinstance(threads, dict) else None


def collect(repo: str, pr: str) -> dict[str, Any]:
    """Gather every input the verdict needs. Raises BoardError when unknown."""
    injected = _probe_entry(repo, pr)
    if injected is not None:
        view = injected.get("pr") or {}
        if not isinstance(view, dict):
            raise BoardError("probe 'pr' is not a JSON object")
        contexts = [str(c) for c in injected.get("required_checks") or []]
        strict = bool(injected.get("strict"))
        conflicts = [str(p) for p in injected.get("conflicted_paths") or []]
        apps = {str(k): str(v) for k, v in (injected.get("required_apps") or {}).items()}
        return {
            "view": view,
            "required": contexts,
            "strict": strict,
            "conflicted_paths": conflicts,
            "required_apps": apps,
        }

    view = _pr_view(repo, pr)
    base = str(view.get("baseRefName") or "")
    if not base:
        raise BoardError("gh pr view reported no base branch")
    threads = fetch_review_threads(repo, pr)
    if threads is not None:
        view["reviewThreads"] = threads
    contexts, strict = required_checks(repo, base)
    apps: dict[str, str] = {}
    try:
        rules = _gh_json(["api", f"repos/{repo}/rules/branches/{base}"])
        if isinstance(rules, list):
            apps.update(_required_app_ids(rules))
    except RuntimeError:
        apps = {}
    conflicts: list[str] = []
    if str(view.get("mergeable") or "").upper() == "CONFLICTING":
        conflicts = conflicted_paths(f"origin/{base}", str(view.get("headRefOid") or ""))
    return {
        "view": view,
        "required": contexts,
        "strict": strict,
        "conflicted_paths": conflicts,
        "required_apps": apps,
    }


def decide(
    facts: dict[str, Any],
    *,
    human_decision: str = "",
    unfixable_checks: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Compute the board verdict. Declared leftovers win; nothing else is inferred."""
    view = facts["view"]
    required = list(facts["required"])
    strict = bool(facts["strict"])
    conflicts = list(facts["conflicted_paths"])
    states = _rollup_states(view, facts.get("required_apps") or {})
    merge_state = str(view.get("mergeStateStatus") or "").upper()
    mergeable = str(view.get("mergeable") or "").upper()
    review_decision = str(view.get("reviewDecision") or "").upper()

    failing = [name for name in required if states.get(name, "EXPECTED") in FAILING_STATES]
    pending = [name for name in required if states.get(name, "EXPECTED") in PENDING_STATES]
    unresolved = _unresolved_threads(view)
    declared_unfixable = [name for name in unfixable_checks if name in failing]
    fixable_failing = [name for name in failing if name not in unfixable_checks]

    verdict = {
        "board": WAIT,
        "reason": "",
        "required_checks": required,
        "failing_required": failing,
        "pending_required": pending,
        "conflicted_paths": conflicts,
        "strict_required_status_checks_policy": strict,
        "merge_state_status": merge_state,
        "mergeable": mergeable,
        "unresolved_threads": unresolved,
    }

    if conflicts:
        generated_only = all(is_generated_path(path) for path in conflicts)
        verdict["board"] = FIX
        verdict["reason"] = (
            "conflicted paths are all generated; regenerate and commit, then merge"
            if generated_only
            else "conflicted paths need resolution: " + ", ".join(conflicts[:5])
        )
        verdict["generated_only_conflict"] = generated_only
        return verdict

    if mergeable == "CONFLICTING":
        verdict["board"] = FIX
        verdict["reason"] = "GitHub reports a conflict; resolve against the base"
        return verdict

    if merge_state == "BEHIND":
        verdict["board"] = FIX
        verdict["reason"] = (
            "strict required-status-checks policy: head is behind the base; catch up "
            "(merge from base for a sibling, rebase --onto after a parent squash)"
            if strict
            else "head is behind the base; catch up before merge"
        )
        return verdict

    if fixable_failing:
        verdict["board"] = FIX
        verdict["reason"] = "required check(s) failing: " + ", ".join(fixable_failing)
        return verdict

    if unresolved:
        verdict["board"] = FIX
        verdict["reason"] = (
            f"{unresolved} unresolved review thread(s) block merge; reply and resolve"
        )
        return verdict

    if review_decision == "CHANGES_REQUESTED":
        verdict["board"] = FIX
        verdict["reason"] = "review decision is CHANGES_REQUESTED"
        return verdict

    if pending:
        verdict["board"] = WAIT
        verdict["reason"] = "required check(s) still running: " + ", ".join(pending)
        return verdict

    if view.get("isDraft"):
        verdict["board"] = FIX
        verdict["reason"] = "pull request is a draft; mark it ready for review"
        return verdict

    if human_decision:
        verdict["board"] = LEFTOVER
        verdict["reason"] = f"named HUMAN decision outstanding: {human_decision}"
        return verdict

    if declared_unfixable:
        verdict["board"] = LEFTOVER
        verdict["reason"] = (
            "required check(s) "
            + ", ".join(declared_unfixable)
            + " declared unfixable without editing CI"
        )
        return verdict

    if review_decision == "REVIEW_REQUIRED":
        verdict["board"] = LEFTOVER
        verdict["reason"] = (
            "required approval is missing; wait for review — no source edit can supply it"
        )
        return verdict

    # Everything this helper can name is green, and GitHub still will not merge.
    # Whatever is left (an approval, a thread, a protection rule this probe did
    # not see) is unnamed -- so say that, rather than calling it a merge.
    if merge_state and merge_state not in MERGE_READY_STATES:
        verdict["board"] = FIX if merge_state == "BLOCKED" else WAIT
        verdict["reason"] = (
            f"every required check this probe can name is green but GitHub reports "
            f"{merge_state}"
            + (
                "; expect an unresolved conversation or a missing approval"
                if merge_state == "BLOCKED"
                else "; GitHub has not finished computing mergeability"
            )
        )
        return verdict

    # An empty required set here is an *answer*, not a gap: a failed protection
    # probe raises BoardError upstream and degrades to WAIT. A stacked PR based
    # on an unprotected agent branch really does require nothing, and calling
    # that "wait" would invent the very blocker this module exists to delete.
    if not merge_state and not required:
        verdict["board"] = WAIT
        verdict["reason"] = (
            "no required context and no merge state; there is no evidence this PR "
            "is mergeable — never merge on unknown"
        )
        return verdict

    verdict["board"] = MERGE
    verdict["reason"] = (
        (
            "no required check on this base and GitHub reports it mergeable"
            if not required
            else "every required check passed"
        )
        + (f" (non-required checks red: {merge_state})" if merge_state == "UNSTABLE" else "")
        + "; attempt via stack_safe_merge.py --run"
    )
    return verdict


def board_for(
    repo: str,
    pr: str,
    *,
    human_decision: str = "",
    unfixable_checks: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Full verdict for one PR. Unknown telemetry degrades to WAIT."""
    try:
        facts = collect(repo, pr)
    except BoardError as exc:
        return {
            "repo": repo,
            "pr": int(pr) if str(pr).isdigit() else pr,
            "board": WAIT,
            "reason": f"telemetry unavailable ({exc}); never merge on unknown",
            "required_checks": [],
            "failing_required": [],
            "pending_required": [],
            "conflicted_paths": [],
        }
    verdict = decide(facts, human_decision=human_decision, unfixable_checks=unfixable_checks)
    verdict["repo"] = repo
    verdict["pr"] = int(pr) if str(pr).isdigit() else pr
    verdict["head"] = str(facts["view"].get("headRefName") or "")
    verdict["base"] = str(facts["view"].get("baseRefName") or "")
    return verdict


def write_receipt(verdict: dict[str, Any], root: Path | None = None) -> Path:
    """Persist the verdict so a status quotes machine output, not prose."""
    base = root or Path.cwd()
    path = base / ".l9" / "pr" / f"board-{verdict['pr']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--pr", required=True, help="pull request number")
    parser.add_argument(
        "--human-decision",
        default="",
        help="name the outstanding human decision; makes this PR leftover",
    )
    parser.add_argument(
        "--unfixable-check",
        action="append",
        default=[],
        metavar="NAME",
        help="required check that cannot be fixed without editing CI (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="print the verdict as JSON")
    parser.add_argument(
        "--no-receipt", action="store_true", help="do not write .l9/pr/board-<pr>.json"
    )
    args = parser.parse_args(argv)

    verdict = board_for(
        args.repo,
        args.pr,
        human_decision=args.human_decision,
        unfixable_checks=tuple(args.unfixable_check),
    )
    if not args.no_receipt:
        verdict["receipt"] = str(write_receipt(verdict))

    if args.json:
        print(json.dumps(verdict, indent=2, sort_keys=True))
    else:
        print(f"board={verdict['board']} pr={verdict['pr']} reason={verdict['reason']}")
        if verdict.get("required_checks"):
            print("required=" + ", ".join(verdict["required_checks"]))
        if verdict.get("conflicted_paths"):
            print("conflicted=" + ", ".join(verdict["conflicted_paths"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
