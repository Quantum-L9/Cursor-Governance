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

OPEN_STATES = frozenset({"open", "deferred"})


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

    The Stop hook carries no workspace, and a cloud session's cwd is a container
    root holding many clones, so the roots are discovered rather than passed.
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
    return {
        "schema": SCHEMA,
        "publish_debt": publish,
        "open_findings": findings,
        "unreadable_ledgers": unreadable,
        "clean": not publish and not findings and not unreadable,
    }


def _render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in report["publish_debt"]:
        lines.append(
            f"  UNPUSHED  {item['branch']} — {item['detail']}\n"
            f"            {item['workspace']}\n"
            f"            rule 1: if you commit, you must push. Publish with "
            f"`PR_REMEDIATE=0 l9 pr` from that workspace."
        )
    for item in report["open_findings"]:
        state = str(item.get("state", "open")).upper()
        lines.append(
            f"  {state:9} {item.get('id', '?')} — {item.get('detail', '')}\n"
            f"            {item['workspace']}\n"
            f"            rules 2/3: a known bug is work, whoever wrote it. Fix it, "
            f"or `session_debt.py defer <id> --reason` with a reason that survives you."
        )
    for path in report["unreadable_ledgers"]:
        lines.append(f"  CORRUPT   ledger unreadable at {path} — cannot prove debt is discharged")
    return "\n".join(lines)


def cmd_status(args: argparse.Namespace) -> int:
    report = collect(candidate_roots(args.root))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    if report["clean"]:
        print("PASS: no abandoned work (nothing unpushed, no open findings)")
        return 0
    print("Open debt:")
    print(_render(report))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    """Gate entry point. Exit 2 blocks; the reason goes to stderr for the model."""
    report = collect(candidate_roots(args.root))
    if report["clean"]:
        return 0
    print(
        "l9-debt: this turn leaves work abandoned (rules/42-no-abandoned-work).\n"
        + _render(report)
        + "\n\nFinish it or record a durable deferral. Narrating a blocker in chat "
        "does not discharge it.",
        file=sys.stderr,
    )
    return 2


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
    for finding in ledger["findings"]:
        if finding.get("id") == args.id:
            finding["state"] = state
            finding.update(extra)
            save_ledger(root, ledger)
            print(f"{args.id} → {state}")
            return 0
    print(f"ERROR: no finding {args.id!r} in {_ledger_path(root)}", file=sys.stderr)
    return 1


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
