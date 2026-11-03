#!/usr/bin/env python3
"""Fail closed on abandoned work: unpushed commits and unclosed findings.

Three operator rules, one mechanism (rules/42-no-abandoned-work.mdc):

  1. If you commit, you must push.
  2. If a bug exists, you must fix it.
  3. A pre-existing error is in scope the moment it is identified.

Doctrine alone did not hold these. An agent can read a rule saying "do not leave
work uncommitted" and still end a session with five local commits and a blocker
narrated in chat, because narrating a blocker *feels* like discharging it. So
each rule is reduced here to a machine-checkable debt item, and the Stop hook
runs this as a `--class gate`: exit 2 blocks the turn from ending and hands the
reason back to the model. Work cannot be abandoned quietly; it can only be
finished or explicitly, durably deferred with a reason a human can read later.

Two debt kinds:

  publish   Detected, never declared. A non-default branch with commits its
            upstream does not have -- or with no upstream at all -- is rule 1
            violated, and no amount of explanation closes it. Only a push does.

  finding   Declared by whoever observed it. A failing validator, a bug found
            while reading code, a pre-existing error inherited from main: rule 2
            and rule 3 make all three the same object. "Not mine" and
            "pre-existing" stop being exits; they are at most a `defer` with a
            stated reason, which stays in the ledger and stays visible.

Deferral is deliberately weaker than closing. `close` asserts the thing is
fixed; `defer` records that it is not, and both keep the item in the ledger so
the next session inherits it rather than rediscovering it.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

LEDGER_NAME = "session-debt.json"
SCHEMA = "l9.session-debt.v1"

#: Branches this repository never publishes from, so commits on them are not
#: publish debt. A detached HEAD is likewise not a branch to push.
UNPUBLISHABLE_BRANCHES = frozenset({"main", "master", "HEAD"})

#: States that keep an item in the LIVE view. A deferral must stay visible --
#: rule 42's whole point is that it "stays open and visible rather than
#: dissolving into chat", so the next session inherits it.
OPEN_STATES = frozenset({"open", "deferred"})

#: States that BLOCK a turn from ending. Visibility and blocking are different
#: questions, and conflating them made the gate unclearable: with everything
#: else discharged, a turn carrying only deferrals still exited 2, and no action
#: available to an agent could change that. Rule 42 calls `defer` "the correct
#: discharge" when finishing requires authority the session does not have, and
#: its Satisfiability section names an unclearable gate as worse than none,
#: because it teaches bypassing. So a deferral discharges the TURN while the
#: ITEM stays on the ledger until a human closes it.
#:
#: `open` is deliberately the only member. Widening this set would let a plain
#: `record` clear a turn, which is the abandonment the gate exists to stop.
BLOCKING_STATES = frozenset({"open"})


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return proc.returncode, proc.stdout.strip()


def git_root(candidate: Path) -> Path | None:
    code, out = _git(candidate, "rev-parse", "--show-toplevel")
    return Path(out) if code == 0 and out else None


def _ledger_path(root: Path) -> Path:
    return root / ".l9" / "autonomy" / LEDGER_NAME


def load_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.is_file():
        return {"schema": SCHEMA, "findings": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # An unreadable ledger is not an empty one. Failing closed here keeps a
        # corrupt file from silently discharging every finding it held.
        return {"schema": SCHEMA, "findings": [], "unreadable": True}
    if not isinstance(payload, dict):
        return {"schema": SCHEMA, "findings": [], "unreadable": True}
    payload.setdefault("findings", [])
    return payload


def save_ledger(root: Path, payload: dict[str, Any]) -> Path:
    path = _ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _was_published(root: Path, branch: str) -> bool:
    """True when this branch was pushed at some point, even if it is gone now.

    `git push -u` writes branch.<name>.remote; a branch that was never pushed
    carries none. That is the only offline evidence separating "merged and
    deleted upstream" from "never published", because a squash merge leaves the
    branch's commits unreachable from main and the deleted ref leaves nothing to
    compare against.

    Residual, stated rather than hidden: a branch whose upstream was set by hand
    without ever pushing reads as published here. That requires a deliberate
    `--set-upstream-to`, and the alternative — treating every deleted branch as
    unpushed work — misfires on every merged branch in every session.
    """
    code, remote = _git(root, "config", "--get", f"branch.{branch}.remote")
    return code == 0 and bool(remote.strip())


def publish_debt(root: Path) -> dict[str, Any] | None:
    """Commits on a publishable branch that the remote does not have.

    Local remote-tracking refs are checked first because they are free, but they
    cannot be trusted to *clear* the check. A cloud clone is created with a
    single-branch refspec (`+refs/heads/main:refs/remotes/origin/main`), so no
    `refs/remotes/origin/<feature>` ever exists no matter how many times the
    branch is pushed. Trusting those refs alone reports an already-published
    branch as unpushed, and pushing again does not clear it: an unsatisfiable
    gate, which is worse than no gate because it teaches people to bypass gates.

    So when local refs cannot prove publication, the remote is asked directly.
    A remote that cannot be reached leaves the debt standing but marked
    unverified -- fail closed on the decision, honest about the evidence.
    """
    code, branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or not branch or branch in UNPUBLISHABLE_BRANCHES:
        return None

    code, head = _git(root, "rev-parse", "HEAD")
    if code != 0 or not head:
        return None

    # Cheap local proof: some remote-tracking ref already contains HEAD.
    code, contains = _git(root, "branch", "--remotes", "--contains", head)
    if code == 0 and contains.strip():
        return None

    code, out = _git(root, "ls-remote", "--heads", "origin", branch)
    if code != 0:
        return {
            "kind": "publish",
            "workspace": str(root),
            "branch": branch,
            "verified": False,
            "detail": (
                f"cannot reach origin to prove {branch!r} is published "
                "(local refs do not contain HEAD)"
            ),
        }

    remote_sha = out.split("\t", 1)[0].strip() if out.strip() else ""
    if remote_sha == head:
        return None
    if not remote_sha and _was_published(root, branch):
        # Merged and deleted upstream. A squash merge gives the branch's commits
        # no ancestry to main by design, so no reachability test can find them,
        # and the branch itself is gone -- absence upstream looks identical to
        # never having been pushed. The distinguisher is that pushing writes
        # upstream config and a branch that was never pushed has none.
        #
        # Not a soft call: the remedy attached to publish debt is "push it", and
        # pushing here recreates a branch the merge deleted. An instruction that
        # is wrong to follow is worse than silence -- the same satisfiability
        # rule that governs the two cases above.
        return None
    if remote_sha:
        # HEAD reachable from the remote tip means the work is published and
        # this checkout is merely behind -- a second worktree left on an older
        # commit, say. Debt is unpushed *work*, not a stale checkout, and
        # reporting it here would be unclearable: pushing does nothing when the
        # remote is already ahead. Exit 0 is the only proof accepted; a missing
        # object exits 128 and correctly leaves the debt standing.
        code, _ = _git(root, "merge-base", "--is-ancestor", head, remote_sha)
        if code == 0:
            return None
    return {
        "kind": "publish",
        "workspace": str(root),
        "branch": branch,
        "verified": True,
        "remote_sha": remote_sha or None,
        "detail": (
            f"HEAD {head[:8]} of {branch!r} is not on origin"
            + (f" (origin has {remote_sha[:8]})" if remote_sha else " (origin has no such branch)")
        ),
    }


def candidate_roots(explicit: list[str] | None = None) -> list[Path]:
    """Repositories this session could have committed in.

    When the caller names roots -- ``explicit`` arguments or
    ``L9_SESSION_DEBT_ROOTS`` -- those are the session's own repositories and
    the scan is confined to them: a Stop hook that knows its project dir must
    not be blocked by debt another session left in a sibling worktree under
    ``~/.l9/gov-worktrees``. Only when nothing is named does discovery widen
    (the Stop hook carries no workspace, and a cloud session's cwd is a
    container root holding many clones).
    """
    seen: list[Path] = []

    def add(path: Path | None) -> None:
        if path is None:
            return
        resolved = path.resolve()
        if resolved not in seen and (resolved / ".git").exists():
            seen.append(resolved)

    for raw in explicit or []:
        add(git_root(Path(raw)))

    env = os.environ.get("L9_SESSION_DEBT_ROOTS", "")
    for raw in filter(None, (part.strip() for part in env.split(os.pathsep))):
        add(git_root(Path(raw)))

    if seen:
        return seen

    add(git_root(Path.cwd()))

    worktrees = Path.home() / ".l9" / "gov-worktrees"
    if worktrees.is_dir():
        for child in sorted(worktrees.iterdir()):
            if child.is_dir():
                add(child)

    cwd = Path.cwd()
    if cwd.is_dir():
        for child in sorted(cwd.iterdir()):
            if child.is_dir():
                add(child)

    add(Path.home() / ".cursor-governance")
    return seen


def collect(roots: list[Path]) -> dict[str, Any]:
    publish: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    unreadable: list[str] = []
    for root in roots:
        debt = publish_debt(root)
        if debt:
            publish.append(debt)
        ledger = load_ledger(root)
        if ledger.get("unreadable"):
            unreadable.append(str(root))
        for item in ledger.get("findings", []):
            if isinstance(item, dict) and item.get("state") in OPEN_STATES:
                findings.append({**item, "workspace": str(root)})
    blocking = [f for f in findings if f.get("state") in BLOCKING_STATES]
    return {
        "schema": SCHEMA,
        "publish_debt": publish,
        "open_findings": findings,
        "blocking_findings": blocking,
        "unreadable_ledgers": unreadable,
        # An unreadable ledger blocks: it cannot prove debt is discharged.
        "clean": not publish and not blocking and not unreadable,
    }


#: The repository whose workspaces a handoff covers. Environment friction is
#: governance's to fix, and its to-dos are the ones this ledger owns.
GOVERNANCE_REPOSITORY = "quantum-l9/cursor-governance"


def is_governance_workspace(root: Path) -> bool:
    """True when ``root``'s origin is Quantum-L9/Cursor-Governance (any URL form)."""
    code, url = _git(root, "config", "--get", "remote.origin.url")
    if code != 0:
        return False
    path = url.strip().lower().rstrip("/").removesuffix(".git")
    return path.endswith("/" + GOVERNANCE_REPOSITORY) or path.endswith(":" + GOVERNANCE_REPOSITORY)


def governance_root(explicit: str | None = None) -> Path | None:
    """Where friction is recorded: the named or current Cursor-Governance
    workspace, else the governance SSOT clone. Never another repository's."""
    for candidate in filter(None, (explicit, str(Path.cwd()))):
        root = git_root(Path(candidate))
        if root is not None and is_governance_workspace(root):
            return root
    ssot = git_root(Path.home() / ".cursor-governance")
    return ssot if ssot is not None and is_governance_workspace(ssot) else None


def _contracts() -> tuple[Any, Any]:
    """The two post-publish handoff contracts the Stop hook already enforces."""
    repo = str(Path(__file__).resolve().parents[2])
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from ops.memory import governance_handoff, session_handoff

    return session_handoff, governance_handoff


def build_handoffs(
    roots: list[Path],
    *,
    pr_number: int,
    objective: str,
    status: str,
    next_steps: list[str],
    friction_root: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Both post-publish handoffs, generated instead of hand-written.

    Only Cursor-Governance workspaces are read, and only what is still to be
    done (repository handoff) and environment friction (governance handoff) is
    carried: what is finished, pushed or merely uncommitted is not a to-do.
    Each document passes its own contract's ``normalize``, so the Stop hook
    accepts exactly what this produces.
    """
    session_handoff, governance_handoff = _contracts()
    governed = [root for root in roots if is_governance_workspace(root)]
    report = collect(governed)
    deferred = [f for f in report["open_findings"] if f.get("state") == "deferred"]

    repo_brief = {
        "schema": session_handoff.HANDOFF_SCHEMA,
        "pr_number": pr_number,
        "objective": objective,
        "status": status,
        "not_completed": [
            {"item": f"push {d['branch']} ({d['workspace']})", "reason": d["detail"]}
            for d in report["publish_debt"]
        ]
        + [
            {"item": f"{f.get('id')}: {f.get('detail', '')}", "reason": "open finding"}
            for f in report["blocking_findings"]
        ]
        + [
            {"item": f"repair ledger {path}", "reason": "unreadable; debt unprovable"}
            for path in report["unreadable_ledgers"]
        ],
        "blocked": [
            {
                "item": f"{f.get('id')}: {f.get('detail', '')}",
                "blocker": f.get("reason") or "deferred",
                "unblock": "a human decision, then session_debt.py close",
            }
            for f in deferred
        ],
        "human_actions": [
            {"action": f"decide {f.get('id')}: {f.get('detail', '')}", "why": f.get("reason", "")}
            for f in deferred
        ],
        "next_actions": [step for step in next_steps if step.strip()],
    }

    friction: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in [*governed, *([friction_root] if friction_root else [])]:
        for item in load_ledger(root).get("friction", []):
            if isinstance(item, dict) and item.get("state") == "open":
                if item.get("id") not in seen:
                    seen.add(str(item.get("id")))
                    friction.append(item)
    governance_brief = {
        "schema": governance_handoff.GOVERNANCE_SCHEMA,
        "pr_number": pr_number,
        "environment_friction": [
            {"item": str(f.get("id")), "detail": f.get("detail", "")} for f in friction
        ],
        "workarounds": [
            {"item": str(f.get("id")), "workaround": f["workaround"]}
            for f in friction
            if f.get("workaround")
        ],
    }
    return (
        session_handoff.normalize(repo_brief, pr_number=pr_number),
        governance_handoff.normalize(governance_brief, pr_number=pr_number),
    )


def render_handoffs(repo_brief: dict[str, Any], governance_brief: dict[str, Any]) -> str:
    """Both briefs as one Markdown page, through the contracts' own renderers."""
    session_handoff, governance_handoff = _contracts()
    gov_lines = governance_handoff.render_sections(governance_brief)
    return "\n".join(
        [
            f"# Session handoff — PR #{repo_brief['pr_number']}",
            "",
            "## Still to do",
            "",
            "```text",
            session_handoff.render(repo_brief),
            "```",
            "",
            "## Environment friction (Cursor-Governance)",
            "",
            "```text",
            "\n".join(gov_lines) if gov_lines else "none",
            "```",
            "",
        ]
    )


def _render_findings(findings: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in findings:
        state = str(item.get("state", "open")).upper()
        lines.append(
            f"  {state:9} {item.get('id', '?')} — {item.get('detail', '')}\n"
            f"            {item['workspace']}\n"
            f"            rules 2/3: a known bug is work, whoever wrote it. Fix it, "
            f"or `session_debt.py defer <id> --reason` with a reason that survives you."
        )
    return "\n".join(lines)


def _render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in report["publish_debt"]:
        lines.append(
            f"  UNPUSHED  {item['branch']} — {item['detail']}\n"
            f"            {item['workspace']}\n"
            f"            rule 1: if you commit, you must push. Publish with "
            f"`PR_REMEDIATE=0 l9 pr` from that workspace."
        )
    lines.extend(_render_findings(report["open_findings"]).splitlines() or [])
    for path in report["unreadable_ledgers"]:
        lines.append(f"  CORRUPT   ledger unreadable at {path} — cannot prove debt is discharged")
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    report = collect(candidate_roots(args.root))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    deferred = [f for f in report["open_findings"] if f.get("state") == "deferred"]
    if report["clean"]:
        print("PASS: no abandoned work (nothing unpushed, no blocking findings)")
        if deferred:
            # `clean` means the TURN is dischargeable, never that the ledger is
            # empty. Hiding deferrals behind it would undo the visibility the
            # deferral exists to preserve.
            print(f"\n{len(deferred)} deferred item(s) awaiting a human:")
            print(_render_findings(deferred))
        return 0
    print("Open debt:")
    print(_render(report))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Gate entry point. Exit 2 blocks; the reason goes to stderr for the model."""
    report = collect(candidate_roots(args.root))
    if report["clean"]:
        # Deferrals do not block, but they are never silent: a turn that ends
        # carrying them says so, or the reason a human needs to act on stops
        # reaching anyone.
        deferred = [f for f in report["open_findings"] if f.get("state") == "deferred"]
        if deferred:
            print(
                f"l9-debt: turn clear; {len(deferred)} deferred item(s) still on the "
                "ledger for a human to close:\n" + _render_findings(deferred),
                file=sys.stderr,
            )
        return 0
    print(
        "l9-debt: this turn leaves work abandoned (rules/42-no-abandoned-work).\n"
        + _render(report)
        + "\n\nFinish it or record a durable deferral. Narrating a blocker in chat "
        "does not discharge it.",
        file=sys.stderr,
    )
    return 2


def cmd_handoff(args: argparse.Namespace) -> int:
    """Write both post-publish handoffs the Stop hook asks for, from the ledger."""
    workspace = git_root(Path(args.workspace or Path.cwd()))
    if workspace is None:
        print(f"ERROR: not a git work tree: {args.workspace or Path.cwd()}", file=sys.stderr)
        return 1
    session_handoff, governance_handoff = _contracts()
    try:
        repo_brief, governance_brief = build_handoffs(
            candidate_roots(args.root),
            pr_number=args.pr,
            objective=args.objective,
            status=args.status,
            next_steps=args.next or [],
            friction_root=governance_root(str(workspace)),
        )
    except session_handoff.HandoffError as exc:
        print(f"ERROR: handoff not accepted by its contract: {exc}", file=sys.stderr)
        return 1
    for rel, brief in (
        (session_handoff.HANDOFF_REL, repo_brief),
        (governance_handoff.GOVERNANCE_REL, governance_brief),
    ):
        path = workspace / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_handoffs(repo_brief, governance_brief), encoding="utf-8")
        print(f"wrote {out}")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    root = git_root(Path(args.workspace or Path.cwd()))
    if root is None:
        print(f"ERROR: not a git work tree: {args.workspace or Path.cwd()}", file=sys.stderr)
        return 1
    ledger = load_ledger(root)
    findings = [f for f in ledger["findings"] if f.get("id") != args.id]
    findings.append(
        {
            "id": args.id,
            "state": "open",
            "detail": args.detail,
            "source": args.source,
            "recorded_at": int(time.time()),
        }
    )
    ledger["findings"] = findings
    path = save_ledger(root, ledger)
    print(f"recorded {args.id} (open) → {path}")
    return 0


def _transition(args: argparse.Namespace, state: str, extra: dict[str, Any]) -> int:
    root = git_root(Path(args.workspace or Path.cwd()))
    if root is None:
        print(f"ERROR: not a git work tree: {args.workspace or Path.cwd()}", file=sys.stderr)
        return 1
    ledger = load_ledger(root)
    for finding in [*ledger["findings"], *ledger.get("friction", [])]:
        if finding.get("id") == args.id:
            finding["state"] = state
            finding.update(extra)
            save_ledger(root, ledger)
            print(f"{args.id} → {state}")
            return 0
    print(f"ERROR: no finding {args.id!r} in {_ledger_path(root)}", file=sys.stderr)
    return 1


def cmd_friction(args: argparse.Namespace) -> int:
    """Record something in the environment that got in the way.

    Friction is governance's to fix, so it lands in a Cursor-Governance
    workspace's ledger whatever repository the session was working in. It is
    never a gate item: an agent cannot clear the environment by its own action.
    """
    root = governance_root(args.workspace)
    if root is None:
        print("ERROR: no Cursor-Governance workspace to record friction in", file=sys.stderr)
        return 1
    ledger = load_ledger(root)
    items = [f for f in ledger.get("friction", []) if f.get("id") != args.id]
    items.append(
        {
            "id": args.id,
            "state": "open",
            "detail": args.detail,
            "workaround": args.workaround,
            "recorded_at": int(time.time()),
        }
    )
    ledger["friction"] = items
    path = save_ledger(root, ledger)
    print(f"recorded friction {args.id} → {path}")
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    return _transition(args, "closed", {"closed_at": int(time.time()), "evidence": args.evidence})


def cmd_defer(args: argparse.Namespace) -> int:
    """Deferral is not closure: the item stays open so it is inherited, not lost."""
    return _transition(args, "deferred", {"deferred_at": int(time.time()), "reason": args.reason})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", help="extra repository to inspect")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="report open debt (always exit 0)")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    check = sub.add_parser("check", help="exit 2 when any debt is open (gate)")
    check.set_defaults(func=cmd_check)

    handoff = sub.add_parser(
        "handoff",
        help="write both post-publish handoffs (to-dos + environment friction) from the ledger",
    )
    handoff.add_argument("--pr", type=int, required=True, help="the publication's PR number")
    handoff.add_argument("--objective", required=True)
    handoff.add_argument("--status", required=True, help="where things stand, one or two sentences")
    handoff.add_argument("--next", action="append", help="a next step (repeatable)")
    handoff.add_argument("--workspace", help="the published workspace (default: cwd)")
    handoff.add_argument("--out", help="also write both briefs as one Markdown page here")
    handoff.set_defaults(func=cmd_handoff)

    friction = sub.add_parser(
        "friction", help="record environment friction for Cursor-Governance to fix"
    )
    friction.add_argument("id")
    friction.add_argument("--detail", required=True)
    friction.add_argument("--workaround", help="what the session did instead")
    friction.add_argument("--workspace", help="a Cursor-Governance workspace")
    friction.set_defaults(func=cmd_friction)

    record = sub.add_parser("record", help="record an observed defect as debt")
    record.add_argument("id")
    record.add_argument("--detail", required=True)
    record.add_argument("--source", default="observed")
    record.add_argument("--workspace")
    record.set_defaults(func=cmd_record)

    close = sub.add_parser("close", help="mark a finding fixed, with evidence")
    close.add_argument("id")
    close.add_argument("--evidence", required=True)
    close.add_argument("--workspace")
    close.set_defaults(func=cmd_close)

    defer = sub.add_parser("defer", help="record that a finding is knowingly not fixed")
    defer.add_argument("id")
    defer.add_argument("--reason", required=True)
    defer.add_argument("--workspace")
    defer.set_defaults(func=cmd_defer)

    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
