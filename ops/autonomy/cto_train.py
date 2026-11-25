#!/usr/bin/env python3
"""Run a CTO merge train: land a campaign's PRs in a declared order, safely.

Manifest: <workspace>/.l9/cto-mode/train.json (``l9.cto-train/v1``, schema
governance/cto-mode/schemas/train.schema.json). Every output carries
``"grants_permission": false``: this tool decides *when* a PR is ready to hand
to the merge executor, never *whether* a merge is authorized. Every merge goes
through ``stack_safe_merge.py --run --head-sha`` and therefore through
merge_gate, the authorization check and the read-back there. It never calls the
merge API itself, never uses ``--admin``, never force-pushes and never resets.

    plan         validate train.json and print the order and the pair groups
    run          walk ``order``; merge each ready PR, DEFER the rest, continue
    verify-head  the head-equivalence check alone (reusable by integration)

What ``run`` requires of each PR before it is handed to the executor, in order
(a PR failing any step is DEFERRED with the reason and the run continues):

1. Open (a merged PR is skipped; a closed one is deferred).
2. Its live head is the integration-proven head, or a reviewed acceptance in
   ``accepted`` covers it, or ``verify-head`` shows it mechanically equivalent.
3. When ``integration_receipt`` is set: the receipt exists, its verdict is
   ``pass`` and it names this PR's proven head.
4. Every other open PR whose head this head contains has merged first.
5. Its base is the train base. A base the train base already contains
   (compare ``behind`` / ``identical``) is retargeted first -- merging into it
   would land the change on a branch nothing promotes.
6. GitHub reports a ``mergeable_state`` other than ``unknown``.
7. pr_board's verdict is ``merge`` (required checks green, no conflict).

A ``pairs`` group is all-or-nothing: every member must pass 1-7 before any is
merged, then the members merge back to back in ``order``.

Head equivalence (contract ``l9.cto-head-equivalence/v1``, declared here, not
inferred): with B the current train base, P the proven head and H the live head,
H is equivalent to P when ``merge-tree(B, P)`` and ``merge-tree(B, H)`` are both
clean and differ only in

* a ``__manifest__.py`` ``"version"`` line,
* a README ``module_version:`` line, or
* the order of otherwise identical lines in a file (same multiset of lines).

Any added or removed path, mode change, or other content is not equivalent.
Anything that cannot be computed (an unresolvable commit, a conflicting merge)
is ``unknown``, which is never equivalent.

Exit codes: 0 done (plan valid / everything merged / equivalent), 1 not
equivalent, 2 usage or invalid manifest, 3 deferred work or unknown equivalence.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import stack_safe_merge as ssm  # noqa: E402

ROOT = _HERE.parent.parent
TRAIN_SCHEMA = "l9.cto-train/v1"
RECEIPT_SCHEMA = "l9.cto-integration-receipt/v1"
EQUIVALENCE_SCHEMA = "l9.cto-head-equivalence/v1"
PLAN_SCHEMA = "l9.cto-train-plan/v1"
RUN_SCHEMA = "l9.cto-train-run/v1"
SCHEMA_PATH = ROOT / "governance" / "cto-mode" / "schemas" / "train.schema.json"
TRAIN_REL = Path(".l9") / "cto-mode" / "train.json"
EXECUTOR = _HERE / "stack_safe_merge.py"

EXIT_OK = 0
EXIT_NOT_EQUIVALENT = 1
EXIT_USAGE = 2
EXIT_PENDING = 3

MERGEABLE_TIMEOUT_SECONDS = 120.0
MERGEABLE_POLL_SECONDS = 5.0

_SHA = re.compile(r"^[0-9a-f]{40}$")
_MANIFEST_VERSION = re.compile(r"""^\s*["']version["']\s*:""")
_README_VERSION = re.compile(r"^\s*module_version\s*:")


class TrainError(ValueError):
    """The manifest is missing, unreadable, or violates its schema or semantics."""


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_train(data: Any) -> dict[str, Any]:
    """Return ``data`` with defaults filled, or raise TrainError naming every violation."""
    import jsonschema  # noqa: PLC0415

    validator = jsonschema.Draft202012Validator(_schema())
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        raise TrainError(
            "; ".join(
                f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
                for e in errors
            )
        )
    train: dict[str, Any] = dict(data)
    train.setdefault("pairs", [])
    train.setdefault("accepted", [])
    train.setdefault("integration_receipt", None)
    train.setdefault("runtime", None)
    train.setdefault("static", [])
    train.setdefault("suite", [])
    problems: list[str] = []
    numbers = [int(p["number"]) for p in train["prs"]]
    if len(set(numbers)) != len(numbers):
        problems.append("prs: a pull request is listed twice")
    order = [int(n) for n in train["order"]]
    if len(set(order)) != len(order):
        problems.append("order: a pull request appears twice")
    if set(order) != set(numbers):
        missing = sorted(set(numbers) - set(order))
        extra = sorted(set(order) - set(numbers))
        problems.append(
            f"order must list every PR in prs exactly once (missing {missing}, unknown {extra})"
        )
    seen: set[int] = set()
    for group in train["pairs"]:
        members = [int(n) for n in group]
        if len(set(members)) != len(members):
            problems.append(f"pairs: group {members} repeats a PR")
        for member in members:
            if member not in numbers:
                problems.append(f"pairs: #{member} is not in prs")
            if member in seen:
                problems.append(f"pairs: #{member} is in more than one group")
            seen.add(member)
    for item in train["accepted"]:
        if int(item["pr"]) not in numbers:
            problems.append(f"accepted: #{item['pr']} is not in prs")
    if problems:
        raise TrainError("; ".join(problems))
    return train


def load_train(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TrainError(f"{path}: no train manifest") from exc
    except (OSError, ValueError) as exc:
        raise TrainError(f"{path}: unreadable ({exc})") from exc
    return validate_train(data)


def _groups(train: dict[str, Any]) -> dict[int, list[int]]:
    """Each PR in a pair group mapped to the whole group, in merge order."""
    rank = {int(n): i for i, n in enumerate(train["order"])}
    groups: dict[int, list[int]] = {}
    for group in train["pairs"]:
        members = sorted((int(n) for n in group), key=lambda n: rank[n])
        for member in members:
            groups[member] = members
    return groups


def plan(train: dict[str, Any]) -> dict[str, Any]:
    groups = _groups(train)
    heads = {int(p["number"]): p for p in train["prs"]}
    return {
        "schema": PLAN_SCHEMA,
        "campaign": train["campaign"],
        "repo": train["repo"],
        "base": train["base"],
        "order": [
            {
                "pr": int(n),
                "lane": heads[int(n)]["lane"],
                "proven_head": heads[int(n)]["proven_head"],
                "group": groups.get(int(n)),
            }
            for n in train["order"]
        ],
        "pairs": [_groups(train)[int(g[0])] for g in train["pairs"]],
        "integration_receipt": train["integration_receipt"],
        "accepted": train["accepted"],
        "grants_permission": False,
    }


# ---------------------------------------------------------------------------
# head equivalence
# ---------------------------------------------------------------------------


def _git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo_dir), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _resolve(repo_dir: Path, ref: str) -> str | None:
    proc = _git(repo_dir, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    sha = proc.stdout.strip().lower()
    return sha if proc.returncode == 0 and _SHA.match(sha) else None


def _merge_tree(repo_dir: Path, base: str, head: str) -> str | None:
    """Tree of the clean merge of ``head`` into ``base``; None when it conflicts."""
    proc = _git(repo_dir, "merge-tree", "--write-tree", base, head)
    tree = (proc.stdout.splitlines() or [""])[0].strip()
    if proc.returncode == 0 and _SHA.match(tree):
        return tree
    if proc.returncode == 1:
        return None
    raise RuntimeError(proc.stderr.strip() or f"git merge-tree exited {proc.returncode}")


def _lines(repo_dir: Path, tree: str, path: str) -> list[str]:
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo_dir), "cat-file", "blob", f"{tree}:{path}"],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"cannot read {path} from {tree}")
    return proc.stdout.decode("utf-8", errors="replace").splitlines()


def _mechanical(path: str, line: str) -> str | None:
    """The kind of mechanical line ``line`` is in ``path``, or None."""
    name = PurePosixPath(path).name
    if name == "__manifest__.py" and _MANIFEST_VERSION.match(line):
        return "version"
    if name.lower().startswith("readme") and _README_VERSION.match(line):
        return "readme_version"
    return None


def classify_file(path: str, before: list[str], after: list[str]) -> str:
    """``version`` / ``readme_version`` / ``reordered`` when mechanical, else ``content``."""
    kinds = {k for line in before + after if (k := _mechanical(path, line))}
    kept_before = Counter(line for line in before if not _mechanical(path, line))
    kept_after = Counter(line for line in after if not _mechanical(path, line))
    if kept_before != kept_after:
        return "content"
    plain_before = [line for line in before if not _mechanical(path, line)]
    plain_after = [line for line in after if not _mechanical(path, line)]
    if plain_before != plain_after:
        return "reordered"
    if "version" in kinds:
        return "version"
    if "readme_version" in kinds:
        return "readme_version"
    return "reordered"


def _tree_differences(repo_dir: Path, left: str, right: str) -> list[dict[str, str]]:
    proc = _git(repo_dir, "diff", "--raw", "-z", "--no-renames", "--no-abbrev", left, right)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    fields = proc.stdout.split("\0")
    out: list[dict[str, str]] = []
    i = 0
    while i + 1 < len(fields) and fields[i].startswith(":"):
        meta, path = fields[i].split(), fields[i + 1]
        i += 2
        mode_a, mode_b, status = meta[0].lstrip(":"), meta[1], meta[4]
        if status == "A":
            out.append({"path": path, "kind": "added"})
        elif status == "D":
            out.append({"path": path, "kind": "removed"})
        elif mode_a != mode_b:
            out.append({"path": path, "kind": "mode"})
        else:
            kind = classify_file(path, _lines(repo_dir, left, path), _lines(repo_dir, right, path))
            out.append({"path": path, "kind": kind})
    return out


MECHANICAL_KINDS = frozenset({"version", "readme_version", "reordered"})


def fetch_for_verify(repo_dir: Path, base: str, pr: int, shas: Iterable[str]) -> list[str]:
    """Fetch the train base, the PR's head ref, and any named commit not present. Best effort.

    Returns the fetch failures; a commit still missing afterwards makes the
    verdict ``unknown`` rather than being guessed.
    """
    failures: list[str] = []
    for refspec in (
        f"+refs/heads/{base}:refs/remotes/origin/{base}",
        f"+refs/pull/{pr}/head:refs/remotes/origin/pr/{pr}",
    ):
        proc = _git(repo_dir, "fetch", "--quiet", "origin", refspec)
        if proc.returncode != 0:
            failures.append(f"{refspec}: {proc.stderr.strip()[:200]}")
    for sha in shas:
        if _resolve(repo_dir, sha) is None:
            proc = _git(repo_dir, "fetch", "--quiet", "origin", sha)
            if proc.returncode != 0:
                failures.append(f"{sha}: {proc.stderr.strip()[:200]}")
    return failures


def verify_head(
    repo_dir: Path,
    *,
    pr: int,
    base_ref: str,
    proven: str,
    head: str,
) -> dict[str, Any]:
    """Decide whether ``head`` is mechanically equivalent to ``proven`` on ``base_ref``."""
    record: dict[str, Any] = {
        "schema": EQUIVALENCE_SCHEMA,
        "pr": pr,
        "base_ref": base_ref,
        "proven_head": proven,
        "head": head,
        "grants_permission": False,
    }
    base_sha = _resolve(repo_dir, base_ref)
    record["base_sha"] = base_sha
    proven_sha = _resolve(repo_dir, proven)
    head_sha = _resolve(repo_dir, head)
    missing = [
        name
        for name, sha in (("base", base_sha), ("proven head", proven_sha), ("head", head_sha))
        if sha is None
    ]
    if missing or base_sha is None or proven_sha is None or head_sha is None:
        return {**record, "verdict": "unknown", "reason": f"unresolvable: {', '.join(missing)}"}
    if proven_sha == head_sha:
        return {**record, "verdict": "identical", "differences": []}
    try:
        proven_tree = _merge_tree(repo_dir, base_sha, proven_sha)
        head_tree = _merge_tree(repo_dir, base_sha, head_sha)
        if proven_tree is None or head_tree is None:
            which = "proven head" if proven_tree is None else "head"
            return {
                **record,
                "verdict": "unknown",
                "reason": f"merging the {which} into the base conflicts",
            }
        differences = (
            [] if proven_tree == head_tree else _tree_differences(repo_dir, proven_tree, head_tree)
        )
    except RuntimeError as exc:
        return {**record, "verdict": "unknown", "reason": str(exc)}
    non_mechanical = [d for d in differences if d["kind"] not in MECHANICAL_KINDS]
    return {
        **record,
        "verdict": "not_equivalent" if non_mechanical else "equivalent",
        "differences": differences,
        **(
            {"reason": "non-mechanical change in " + ", ".join(d["path"] for d in non_mechanical)}
            if non_mechanical
            else {}
        ),
    }


# ---------------------------------------------------------------------------
# GitHub layer (REST only; the merge itself is stack_safe_merge.py --run)
# ---------------------------------------------------------------------------


class GitHub(Protocol):
    def pull(self, pr: int) -> dict[str, Any]: ...
    def compare(self, base: str, head: str) -> str: ...
    def open_pulls(self) -> list[dict[str, Any]]: ...
    def retarget(self, pr: int, base: str) -> None: ...
    def board(self, pr: int) -> dict[str, Any]: ...
    def merge(
        self, pr: int, head_sha: str, long_lived_bases: tuple[str, ...]
    ) -> dict[str, Any]: ...


class LiveGitHub:
    """Reads over ``gh api`` (REST); merges only through the executor subprocess."""

    def __init__(self, repo: str) -> None:
        self.repo = repo

    def pull(self, pr: int) -> dict[str, Any]:
        return ssm._pull(self.repo, str(pr))

    def compare(self, base: str, head: str) -> str:
        return ssm.compare_status(self.repo, base, head)

    def open_pulls(self) -> list[dict[str, Any]]:
        return ssm.open_pulls(self.repo)

    def retarget(self, pr: int, base: str) -> None:
        argv = ssm.retarget_argv(self.repo, str(pr), base)
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[:300] or f"retarget exited {proc.returncode}")

    def board(self, pr: int) -> dict[str, Any]:
        import pr_board  # noqa: PLC0415

        return pr_board.board_for(self.repo, str(pr))

    def merge(self, pr: int, head_sha: str, long_lived_bases: tuple[str, ...]) -> dict[str, Any]:
        argv = [
            sys.executable,
            str(EXECUTOR),
            "--repo",
            self.repo,
            "--pr",
            str(pr),
            "--head-sha",
            head_sha,
            "--run",
        ]
        for base in long_lived_bases:
            argv += ["--long-lived-base", base]
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)  # noqa: S603
        return {
            "rc": proc.returncode,
            "record": _last_json(proc.stdout),
            "stderr": proc.stderr.strip()[-500:],
        }


def _last_json(text: str) -> dict[str, Any] | None:
    """The executor prints one indented JSON object; take the outermost one."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


class Deferred(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


Verifier = Callable[[int, str, str], dict[str, Any]]


class TrainRunner:
    def __init__(
        self,
        train: dict[str, Any],
        gh: GitHub,
        *,
        workspace: Path,
        verify: Verifier | None = None,
        dry_run: bool = False,
        mergeable_timeout: float = MERGEABLE_TIMEOUT_SECONDS,
        poll: float = MERGEABLE_POLL_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.train = train
        self.gh = gh
        self.workspace = workspace
        self.verify = verify
        self.dry_run = dry_run
        self.mergeable_timeout = mergeable_timeout
        self.poll = poll
        self.sleep = sleep
        self.clock = clock
        self.base = str(train["base"])
        self.proven = {int(p["number"]): p["proven_head"] for p in train["prs"]}
        self.groups = _groups(train)
        self.summary: dict[str, Any] = {
            "schema": RUN_SCHEMA,
            "campaign": train["campaign"],
            "repo": train["repo"],
            "base": self.base,
            "dry_run": dry_run,
            "merged": [],
            "already_merged": [],
            "deferred": [],
            "retargeted": [],
            "grants_permission": False,
        }
        if dry_run:
            self.summary["would_merge"] = []

    # -- individual requirements ------------------------------------------------

    def _head_basis(self, pr: int, head: str) -> str:
        proven = self.proven.get(pr)
        if proven and head == proven:
            return "proven"
        for item in self.train["accepted"]:
            if int(item["pr"]) == pr and head.startswith(str(item["head_prefix"]).lower()):
                return "accepted"
        if not proven:
            raise Deferred("no proven head and no reviewed acceptance covers the live head")
        if self.verify is None:
            raise Deferred(f"head {head} is not the proven head {proven}; no equivalence check")
        verdict = self.verify(pr, proven, head)
        if verdict.get("verdict") in ("identical", "equivalent"):
            return "equivalent"
        detail = verdict.get("reason") or verdict.get("verdict")
        raise Deferred(
            f"head {head} is not the proven head {proven} and not equivalent to it ({detail}); "
            "re-prove it or record a reviewed acceptance"
        )

    def _receipt(self) -> dict[str, Any] | None:
        ref = self.train.get("integration_receipt")
        if not ref:
            return None
        path = Path(ref)
        if not path.is_absolute():
            path = self.workspace / path
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise Deferred(f"integration receipt {path} does not exist") from exc
        except (OSError, ValueError) as exc:
            raise Deferred(f"integration receipt {path} is unreadable ({exc})") from exc
        if not isinstance(data, dict) or data.get("schema") != RECEIPT_SCHEMA:
            raise Deferred(f"integration receipt {path} is not {RECEIPT_SCHEMA}")
        if data.get("verdict") != "pass":
            raise Deferred(f"integration receipt verdict is {data.get('verdict')!r}, not 'pass'")
        if data.get("repo") not in (None, self.train["repo"]):
            raise Deferred(
                f"integration receipt is for {data.get('repo')}, not {self.train['repo']}"
            )
        return data

    def _covered(self, pr: int) -> None:
        receipt = self._receipt()
        if receipt is None:
            return
        proven = self.proven.get(pr)
        raw_heads = receipt.get("heads")
        heads: dict[str, Any] = raw_heads if isinstance(raw_heads, dict) else {}
        if not proven or str(heads.get(str(pr)) or "").lower() != proven:
            raise Deferred(
                f"integration receipt does not cover #{pr} at its proven head "
                f"(receipt {heads.get(str(pr))}, proven {proven})"
            )

    def _contained_first(self, pr: int, head: str, exclude: set[int]) -> None:
        try:
            pulls = self.gh.open_pulls()
            blockers = []
            for other in pulls:
                number = other.get("number")
                sha = str((other.get("head") or {}).get("sha") or "").lower()
                if not isinstance(number, int) or number == pr or number in exclude:
                    continue
                if not _SHA.match(sha):
                    raise RuntimeError(f"#{number} reports no head sha")
                if self.gh.compare(sha, head) in ssm.CONTAINS_STATUSES:
                    blockers.append(number)
        except RuntimeError as exc:
            raise Deferred(f"containment unreadable ({exc}); never merge on unknown") from exc
        if blockers:
            raise Deferred(
                "contains open PR(s) "
                + ", ".join(f"#{n}" for n in sorted(blockers))
                + " which must merge first"
            )

    def _base(self, pr: int, view: dict[str, Any], allowed: frozenset[str] = frozenset()) -> bool:
        """Ensure the PR targets the train base. True when it was (or would be) retargeted.

        ``allowed`` names the head branches of earlier members of the same pair
        group: a member stacked on one of them is checked now and retargeted
        once that member has landed.
        """
        base = str((view.get("base") or {}).get("ref") or "")
        if base == self.base or base in allowed:
            return False
        try:
            status = self.gh.compare(self.base, base)
        except RuntimeError as exc:
            raise Deferred(f"base '{base}' liveness unreadable ({exc})") from exc
        if status not in ssm.DEAD_BASE_STATUSES:
            raise Deferred(
                f"base '{base}' is not the train base '{self.base}' and is not yet contained "
                "in it; merge its parent first"
            )
        entry = {"pr": pr, "from": base, "to": self.base, "base_compare": status}
        if self.dry_run:
            self.summary["retargeted"].append({**entry, "dry_run": True})
            return True
        try:
            self.gh.retarget(pr, self.base)
        except RuntimeError as exc:
            raise Deferred(f"base '{base}' is dead and the retarget failed ({exc})") from exc
        self.summary["retargeted"].append(entry)
        return True

    def _mergeable(self, pr: int, head: str) -> dict[str, Any]:
        deadline = self.clock() + self.mergeable_timeout
        while True:
            try:
                view = self.gh.pull(pr)
            except RuntimeError as exc:
                raise Deferred(f"cannot read the pull request ({exc})") from exc
            live = str((view.get("head") or {}).get("sha") or "").lower()
            if live != head:
                raise Deferred(f"head moved from {head} to {live} while checking")
            state = str(view.get("mergeable_state") or "unknown").lower()
            if state != "unknown":
                return view
            if self.clock() >= deadline:
                raise Deferred(
                    f"mergeable_state still unknown after {self.mergeable_timeout:.0f}s; "
                    "never merge on unknown"
                )
            self.sleep(self.poll)

    def check(
        self, pr: int, exclude: set[int], allowed_bases: frozenset[str] = frozenset()
    ) -> dict[str, Any] | None:
        """None when already merged; the ready record otherwise. Raises Deferred."""
        try:
            view = self.gh.pull(pr)
        except RuntimeError as exc:
            raise Deferred(f"cannot read the pull request ({exc})") from exc
        if view.get("merged"):
            return None
        if view.get("state") != "open":
            raise Deferred(f"pull request is {view.get('state')} without merging")
        head = str((view.get("head") or {}).get("sha") or "").lower()
        if not _SHA.match(head):
            raise Deferred("GitHub reports no head sha")
        basis = self._head_basis(pr, head)
        self._covered(pr)
        self._contained_first(pr, head, exclude)
        retargeted = self._base(pr, view, allowed_bases)
        view = self._mergeable(pr, head)
        board = self.gh.board(pr)
        if board.get("board") != "merge":
            raise Deferred(f"board is {board.get('board')}: {board.get('reason')}")
        return {
            "pr": pr,
            "head": head,
            "head_ref": str((view.get("head") or {}).get("ref") or ""),
            "head_basis": basis,
            "retargeted": retargeted,
        }

    # -- merging ----------------------------------------------------------------

    def _merge(self, ready: dict[str, Any]) -> None:
        pr, head = int(ready["pr"]), str(ready["head"])
        if self.dry_run:
            self.summary["would_merge"].append(ready)
            return
        result = self.gh.merge(pr, head, (self.base,))
        record = result.get("record") or {}
        if result.get("rc") != 0 or record.get("status") != "MERGED":
            reason = record.get("reason") or result.get("stderr") or "no record"
            raise Deferred(
                f"executor did not merge (exit {result.get('rc')}, "
                f"{record.get('status') or 'no status'}): {reason}"
            )
        try:
            after = self.gh.pull(pr)
        except RuntimeError as exc:
            raise Deferred(f"merge reported but GitHub state unreadable ({exc})") from exc
        if not after.get("merged"):
            raise Deferred("executor reported MERGED but GitHub does not show it merged")
        self.summary["merged"].append(
            {
                **ready,
                "merge_commit_sha": after.get("merge_commit_sha") or record.get("merge_commit_sha"),
                "method": record.get("method"),
            }
        )

    def _defer(self, pr: int, reason: str) -> None:
        self.summary["deferred"].append({"pr": pr, "reason": reason})

    def _land(self, members: list[int]) -> None:
        ready: list[dict[str, Any]] = []
        failed: dict[int, str] = {}
        pending = set(members)
        earlier_refs: set[str] = set()
        for pr in members:
            try:
                record = self.check(pr, exclude=set(members), allowed_bases=frozenset(earlier_refs))
            except Deferred as exc:
                failed[pr] = exc.reason
                continue
            if record is None:
                self.summary["already_merged"].append(pr)
                pending.discard(pr)
            else:
                ready.append(record)
                if record["head_ref"]:
                    earlier_refs.add(str(record["head_ref"]))
        if failed:
            first = min(failed, key=members.index)
            for pr in members:
                if pr in failed:
                    self._defer(pr, failed[pr])
                elif pr in pending:
                    self._defer(
                        pr,
                        f"pair group {members}: #{first} is not ready ({failed[first]}); "
                        "no member merges until all are",
                    )
            return
        for index, record in enumerate(ready):
            pr = int(record["pr"])
            try:
                if index and not self.dry_run:
                    # An earlier member just landed: its branch may now be this
                    # member's dead base, and GitHub recomputes mergeability.
                    view = self.gh.pull(pr)
                    if self._base(pr, view):
                        self._mergeable(pr, str(record["head"]))
                self._merge(record)
            except Deferred as exc:
                landed = [int(r["pr"]) for r in ready[:index]]
                partial = f" (group partially landed: {landed})" if landed else ""
                self._defer(pr, exc.reason + partial)
                for rest in ready[index + 1 :]:
                    self._defer(
                        int(rest["pr"]),
                        f"pair group {members}: #{pr} did not merge{partial}; stopped",
                    )
                return

    def run(self, only: set[int] | None = None) -> dict[str, Any]:
        handled: set[int] = set()
        for raw in self.train["order"]:
            pr = int(raw)
            if pr in handled:
                continue
            members = self.groups.get(pr, [pr])
            if only and not (set(members) & only):
                continue
            handled.update(members)
            self._land(members)
        return self.summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _train_path(args: argparse.Namespace) -> Path:
    if args.train:
        return Path(args.train)
    return Path(args.workspace) / TRAIN_REL


def _git_verifier(repo_dir: Path, base: str, *, fetch: bool) -> Verifier:
    def _verify(pr: int, proven: str, head: str) -> dict[str, Any]:
        if fetch:
            fetch_for_verify(repo_dir, base, pr, (proven, head))
        return verify_head(repo_dir, pr=pr, base_ref=f"origin/{base}", proven=proven, head=head)

    return _verify


def _print(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--workspace", default=".", help="workspace holding .l9/cto-mode/")
    parser.add_argument(
        "--train", default="", help="train.json path (default: <workspace>/.l9/cto-mode/train.json)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="validate train.json and print order and pairs")
    run = sub.add_parser("run", help="land the train")
    run.add_argument("--only", nargs="+", type=int, default=[], metavar="N")
    run.add_argument("--dry-run", action="store_true", help="check everything, change nothing")
    run.add_argument(
        "--repo-dir", default="", help="local clone for equivalence (default: workspace)"
    )
    run.add_argument("--no-fetch", action="store_true", help="do not fetch before equivalence")
    run.add_argument("--mergeable-timeout", type=float, default=MERGEABLE_TIMEOUT_SECONDS)
    verify = sub.add_parser("verify-head", help="head-equivalence check alone")
    verify.add_argument("--pr", type=int, required=True)
    verify.add_argument("--head", required=True)
    verify.add_argument("--proven", default="", help="proven head (default: from train.json)")
    verify.add_argument("--base-ref", default="", help="base ref (default: origin/<train base>)")
    verify.add_argument("--repo-dir", default="", help="local clone (default: workspace)")
    verify.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()

    if args.command == "verify-head":
        proven = args.proven.strip().lower()
        base_ref = args.base_ref
        base = ""
        if not proven or not base_ref:
            try:
                train = load_train(_train_path(args))
            except TrainError as exc:
                print(f"FAIL: {exc} (or pass --proven and --base-ref)", file=sys.stderr)
                return EXIT_USAGE
            base = str(train["base"])
            base_ref = base_ref or f"origin/{base}"
            if not proven:
                proven = str(
                    next((p["proven_head"] for p in train["prs"] if p["number"] == args.pr), "")
                    or ""
                )
            if not proven:
                print(f"FAIL: #{args.pr} has no proven head in the train", file=sys.stderr)
                return EXIT_USAGE
        repo_dir = Path(args.repo_dir).resolve() if args.repo_dir else workspace
        head = args.head.strip().lower()
        if not args.no_fetch and base:
            fetch_for_verify(repo_dir, base, args.pr, (proven, head))
        record = verify_head(repo_dir, pr=args.pr, base_ref=base_ref, proven=proven, head=head)
        _print(record)
        verdict = record["verdict"]
        if verdict in ("identical", "equivalent"):
            return EXIT_OK
        return EXIT_NOT_EQUIVALENT if verdict == "not_equivalent" else EXIT_PENDING

    try:
        train = load_train(_train_path(args))
    except TrainError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.command == "plan":
        _print(plan(train))
        return EXIT_OK

    repo_dir = Path(args.repo_dir).resolve() if args.repo_dir else workspace
    runner = TrainRunner(
        train,
        LiveGitHub(str(train["repo"])),
        workspace=workspace,
        verify=_git_verifier(repo_dir, str(train["base"]), fetch=not args.no_fetch),
        dry_run=args.dry_run,
        mergeable_timeout=args.mergeable_timeout,
    )
    summary = runner.run(set(args.only) or None)
    _print(summary)
    return EXIT_OK if not summary["deferred"] else EXIT_PENDING


if __name__ == "__main__":
    raise SystemExit(main())
