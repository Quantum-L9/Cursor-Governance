#!/usr/bin/env python3
"""CTO integration candidate builder and receipt writer (campaign cto-workflow-v1, lane C).

An integration candidate is the train's base plus every listed PR head, merged
in train order inside a disposable clone. Building one surfaces cross-PR
collisions that no per-PR CI run can see; running the train's checks on it
yields an integration receipt that the train (lane A) consults before merging.

Inputs and outputs (frozen campaign interfaces):
  train    <workspace>/.l9/cto-mode/train.json                 ("l9.cto-train/v1", lane A)
  receipt  <workspace>/.l9/cto-mode/integration/<candidate>.json
           ("l9.cto-integration-receipt/v1"; schema
           governance/cto-mode/schemas/integration-receipt.schema.json)
  driver   ops/scripts/ensure_git_merge_drivers.sh <clone> registers merge
           drivers, including lane B's "l9-versions" once it lands.

Commands:
  build  --train T [--candidate NAME] [--workdir DIR] [--resolution PR:path:file ...]
  run    --candidate NAME [--fixture NAME] [--allow-rebuild --rebuild-command CMD]
  check  --receipt R --heads pr=sha,...

Exit codes: 0 success / pass, 1 verdict fail or check mismatch, 2 usage or
invalid input, 3 build stopped on a conflict that needs a reviewed resolution.

This tool grants no permission (every JSON output carries
"grants_permission": false). It never merges a PR, pushes, or touches the
user's checkout: all git mutation happens in a clone it created and marked.
A receipt is evidence of what was observed (L9-EVIDENCE-001), not authority.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

GOV_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_SCHEMA_PATH = GOV_ROOT / "governance/cto-mode/schemas/integration-receipt.schema.json"
ENSURE_DRIVERS = GOV_ROOT / "ops/scripts/ensure_git_merge_drivers.sh"

TRAIN_SCHEMA = "l9.cto-train/v1"
RECEIPT_SCHEMA = "l9.cto-integration-receipt/v1"
BUILD_SCHEMA = "l9.cto-integration-build/v1"
RUN_SCHEMA = "l9.cto-integration-run/v1"
CHECK_SCHEMA = "l9.cto-integration-check/v1"

VERSION_DRIVER = "l9-versions"
CLONE_MARKER = "l9-cto-integrate.json"  # lives in the clone's .git dir: proof we own it
CANDIDATE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
INCOMPATIBLE_FIXTURE = "incompatible with the current inputs"
SIDE_INLINE_LIMIT = 4000
OUTPUT_TAIL = 4000

EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_STOPPED = 0, 1, 2, 3


class IntegrateError(Exception):
    """Invalid input or an environment fault; reported with exit code 2."""


# --------------------------------------------------------------------------- utils


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(doc: dict[str, Any]) -> None:
    print(json.dumps(doc, indent=2, sort_keys=True))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=_git_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise IntegrateError(
            f"git {' '.join(args)} failed in {cwd} (exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    return proc


def _rev(cwd: Path, ref: str) -> str:
    return _git(cwd, "rev-parse", "--verify", "--quiet", ref).stdout.strip()


def _workspace_root(workspace: Path) -> Path:
    proc = _git(workspace, "rev-parse", "--show-toplevel", check=False)
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else workspace.resolve()


def _integration_dir(workspace: Path) -> Path:
    return workspace / ".l9" / "cto-mode" / "integration"


def _repo_slug(repo: str) -> str:
    return repo.replace("/", "__")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


# --------------------------------------------------------------------------- train


def load_train(path: Path) -> dict[str, Any]:
    """Read the train manifest (frozen interface 1, owned by lane A) and check the
    fields this tool consumes. Unknown extra fields are left alone."""
    try:
        train = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IntegrateError(f"train manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise IntegrateError(f"train manifest is not JSON: {path}: {exc}") from exc
    if not isinstance(train, dict):
        raise IntegrateError("train manifest must be a JSON object")
    problems: list[str] = []
    if train.get("schema") != TRAIN_SCHEMA:
        problems.append(f"schema must be {TRAIN_SCHEMA!r}, got {train.get('schema')!r}")
    for key in ("campaign", "repo", "base"):
        if not isinstance(train.get(key), str) or not train.get(key):
            problems.append(f"{key} must be a non-empty string")
    if isinstance(train.get("repo"), str) and not re.fullmatch(r"[^/\s]+/[^/\s]+", train["repo"]):
        problems.append("repo must be OWNER/NAME")
    prs = train.get("prs")
    numbers: list[int] = []
    if not isinstance(prs, list) or not prs:
        problems.append("prs must be a non-empty list")
    else:
        for entry in prs:
            num = entry.get("number") if isinstance(entry, dict) else None
            if not isinstance(num, int) or isinstance(num, bool) or num < 1:
                problems.append(f"prs entry has no positive integer number: {entry!r}")
                continue
            proven = entry.get("proven_head")
            if proven is not None and not (
                isinstance(proven, str) and SHA_RE.fullmatch(proven.lower())
            ):
                problems.append(f"PR {num}: proven_head must be a full sha or null")
            numbers.append(num)
        if len(set(numbers)) != len(numbers):
            problems.append("prs lists a PR number twice")
    order = train.get("order") or []
    if not isinstance(order, list) or any(
        not isinstance(n, int) or isinstance(n, bool) for n in order
    ):
        problems.append("order must be a list of PR numbers")
    elif order and sorted(order) != sorted(numbers):
        problems.append("order must list every PR in prs exactly once")
    for key in ("static", "suite"):
        cmds = train.get(key, [])
        if not isinstance(cmds, list) or any(
            not isinstance(c, list) or not c or any(not isinstance(a, str) for a in c) for c in cmds
        ):
            problems.append(f"{key} must be a list of non-empty argv lists")
    runtime = train.get("runtime")
    if runtime is not None:
        if not isinstance(runtime, dict):
            problems.append("runtime must be an object or null")
        else:
            cmd = runtime.get("command")
            if not isinstance(cmd, list) or not cmd or any(not isinstance(a, str) for a in cmd):
                problems.append("runtime.command must be a non-empty argv list")
            env = runtime.get("env", {})
            if not isinstance(env, dict) or any(
                not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()
            ):
                problems.append("runtime.env must map strings to strings")
            timeout = runtime.get("timeout_s")
            if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
                problems.append("runtime.timeout_s must be a positive integer")
    if problems:
        raise IntegrateError(f"invalid train manifest {path}: " + "; ".join(problems))
    return train


def train_order(train: dict[str, Any]) -> list[int]:
    return list(train.get("order") or [p["number"] for p in train["prs"]])


def _base_branch(base: str) -> str:
    for prefix in ("refs/heads/", "origin/", "refs/remotes/origin/"):
        if base.startswith(prefix):
            return base[len(prefix) :]
    return base


# --------------------------------------------------------------------------- locks


@contextlib.contextmanager
def exclusive_lock(path: Path, wait_s: float) -> Iterator[bool]:
    """Hold an exclusive advisory flock on `path`; yields False if not acquired in time.

    This is a process mutex for one machine resource (a clone working tree, or a
    runtime fixture such as a Docker database template) so that two runs never
    share it at once. It is NOT a repository lock: it authorizes and serializes no
    repository write. Rule 96 (E7/E8/E10) forbids repository-write locks; git,
    the PR gates and pr_fleet overlap analysis remain that enforcement.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        deadline = time.monotonic() + max(wait_s, 0.0)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.2)
        if acquired:
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()} {_now()}\n".encode())
        yield acquired
    finally:
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


# --------------------------------------------------------------------------- clone


def prepare_clone(workdir: Path, remote: str, repo: str, workspace: Path) -> Path:
    """Create (or reuse) the disposable clone. Refuses the user's checkout and any
    existing directory this tool did not create."""
    workdir = workdir.expanduser().resolve()
    if _is_within(workdir, workspace) or _is_within(workspace, workdir):
        raise IntegrateError(
            f"--workdir {workdir} overlaps the workspace {workspace}; the candidate "
            "clone must be disposable and outside the user's checkout"
        )
    marker = workdir / ".git" / CLONE_MARKER
    if workdir.exists() and any(workdir.iterdir()) and not marker.is_file():
        raise IntegrateError(
            f"{workdir} exists and was not created by cto_integrate.py "
            f"(no .git/{CLONE_MARKER}); refusing to reuse it"
        )
    if not marker.is_file():
        workdir.mkdir(parents=True, exist_ok=True)
        _git(workdir, "init", "-q")
        _write_json(marker, {"tool": "cto_integrate.py", "repo": repo, "created_at": _now()})
    else:
        owner = json.loads(marker.read_text(encoding="utf-8")).get("repo")
        if owner != repo:
            raise IntegrateError(f"{workdir} is the candidate clone of {owner}, not {repo}")
    if _git(workdir, "remote", "get-url", "origin", check=False).returncode == 0:
        _git(workdir, "remote", "set-url", "origin", remote)
    else:
        _git(workdir, "remote", "add", "origin", remote)
    _git(workdir, "config", "user.name", "l9 cto-integrate")
    _git(workdir, "config", "user.email", "cto-integrate@l9.invalid")
    _git(workdir, "config", "commit.gpgsign", "false")
    return workdir


def _owned_clone(clone: Path) -> None:
    if not (clone / ".git" / CLONE_MARKER).is_file():
        raise IntegrateError(f"{clone} is not a cto_integrate.py clone; refusing to reset it")


def reset_to(clone: Path, branch: str, start: str | None) -> None:
    """Discard all local state in the disposable clone and check out `branch`
    (created or moved to `start` when given). Ownership is proven by the marker."""
    _owned_clone(clone)
    if (clone / ".git" / "MERGE_HEAD").exists():
        _git(clone, "merge", "--abort", check=False)
    if start is None:
        _git(clone, "checkout", "-q", "--force", branch)
    else:
        _git(clone, "checkout", "-q", "--force", "-B", branch, start)
    _git(clone, "reset", "-q", "--hard")
    _git(clone, "clean", "-ffdxq")


def fetch_refs(clone: Path, base: str, numbers: list[int]) -> None:
    specs = [f"+refs/heads/{_base_branch(base)}:refs/l9/base"]
    specs += [f"+refs/pull/{n}/head:refs/l9/pr/{n}" for n in numbers]
    _git(clone, "fetch", "-q", "--no-tags", "origin", *specs)


def register_drivers(clone: Path, registrar: Path = ENSURE_DRIVERS) -> dict[str, Any]:
    """Run the governance driver registrar; report whether lane B's version driver
    is present. Its absence is tolerated and recorded, never assumed away."""
    proc = subprocess.run(
        ["bash", str(registrar), str(clone)],
        capture_output=True,
        text=True,
        check=False,
        env=_git_env(),
    )
    if proc.returncode != 0:
        raise IntegrateError(
            f"{registrar.name} failed (exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    versions = _git(clone, "config", "--get", f"merge.{VERSION_DRIVER}.driver", check=False)
    return {
        "registrar": str(registrar),
        "registrar_output": proc.stdout.strip(),
        VERSION_DRIVER: "registered" if versions.returncode == 0 else "absent",
    }


# --------------------------------------------------------------------------- merge


def resolution_kind(path: str) -> str | None:
    """Map a path a merge driver resolved to a frozen resolution kind."""
    name = path.rsplit("/", 1)[-1]
    if name == "__manifest__.py":
        return "version"
    if name.upper().startswith("README"):
        return "readme_version"
    if path == "tests/__init__.py" or path.endswith("/tests/__init__.py"):
        return "tests_init"
    return None


def _blob(clone: Path, rev: str, path: str) -> str | None:
    proc = _git(clone, "rev-parse", "--verify", "--quiet", f"{rev}:{path}", check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _textual_conflict(clone: Path, base: str, ours: str, theirs: str) -> bool:
    """Would a plain 3-way text merge of these blobs conflict?"""
    with tempfile.TemporaryDirectory(prefix="l9-integrate-") as tmp:
        files = []
        for label, blob in (("ours", ours), ("base", base), ("theirs", theirs)):
            target = Path(tmp) / label
            target.write_bytes(
                subprocess.run(
                    ["git", "cat-file", "blob", blob],
                    cwd=clone,
                    capture_output=True,
                    check=True,
                ).stdout
            )
            files.append(str(target))
        proc = subprocess.run(
            ["git", "merge-file", "-p", "--quiet", *files],
            cwd=clone,
            capture_output=True,
            check=False,
        )
        return proc.returncode != 0


def driver_resolutions(
    clone: Path, pr: int, pre: str, head: str, exclude: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Find paths a merge driver resolved during the merge of `head` onto `pre`:
    changed differently on both sides, and conflicting under a plain text merge.
    Returns (frozen-kind resolutions, driver merges of an unclassified kind)."""
    mb = _git(clone, "merge-base", pre, head, check=False).stdout.strip()
    if not mb:
        return [], []
    ours_paths = set(_git(clone, "diff", "--name-only", mb, pre).stdout.split("\n"))
    theirs_paths = set(_git(clone, "diff", "--name-only", mb, head).stdout.split("\n"))
    resolved: list[dict[str, Any]] = []
    unclassified: list[dict[str, Any]] = []
    for path in sorted((ours_paths & theirs_paths) - exclude - {""}):
        base_b, ours_b, theirs_b = (_blob(clone, r, path) for r in (mb, pre, head))
        if base_b is None or ours_b is None or theirs_b is None or ours_b == theirs_b:
            continue
        if not _textual_conflict(clone, base_b, ours_b, theirs_b):
            continue
        attr = _git(clone, "check-attr", "merge", "--", path).stdout.strip().rsplit(": ", 1)[-1]
        result_b = _blob(clone, "HEAD", path) or "deleted"
        detail = (
            f"merge driver {attr!r}: ours {ours_b[:12]} + theirs {theirs_b[:12]} -> {result_b[:12]}"
        )
        kind = resolution_kind(path)
        entry = {"pr": pr, "path": path, "detail": detail}
        if kind is None:
            unclassified.append(entry)
        else:
            resolved.append({**entry, "kind": kind})
    return resolved, unclassified


def _side(clone: Path, stage: int, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f":{stage}:{path}"],
        cwd=clone,
        capture_output=True,
        check=False,
    )
    return proc.stdout.decode("utf-8", "replace") if proc.returncode == 0 else None


def _conflict_report(
    clone: Path, workdir_conflicts: Path, pr: int, paths: list[str]
) -> list[dict[str, Any]]:
    out = []
    for path in paths:
        entry: dict[str, Any] = {"path": path, "files": {}}
        for stage, label in ((1, "base"), (2, "ours"), (3, "theirs")):
            text = _side(clone, stage, path)
            if text is None:
                entry[label] = None
                continue
            target = workdir_conflicts / f"pr{pr}" / f"{path.replace('/', '__')}.{label}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            entry["files"][label] = str(target)
            entry[label] = (
                text
                if len(text) <= SIDE_INLINE_LIMIT
                else text[:SIDE_INLINE_LIMIT] + f"\n... [truncated; full text in {target}]"
            )
        out.append(entry)
    return out


def parse_resolutions(values: list[str]) -> dict[tuple[int, str], Path]:
    parsed: dict[tuple[int, str], Path] = {}
    for value in values:
        pr_s, _, rest = value.partition(":")
        path, _, file_s = rest.rpartition(":")
        if not pr_s.isdigit() or not path or not file_s:
            raise IntegrateError(f"--resolution must be PR:path:file, got {value!r}")
        source = Path(file_s).expanduser().resolve()
        if not source.is_file():
            raise IntegrateError(f"--resolution file not found: {source}")
        parsed[(int(pr_s), path)] = source
    return parsed


def default_candidate(campaign: str, base_sha: str, heads: dict[str, str]) -> str:
    digest = hashlib.sha256(
        json.dumps({"base": base_sha, "heads": heads}, sort_keys=True).encode()
    ).hexdigest()[:12]
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", campaign).strip("-") or "candidate"
    return f"{slug}-{digest}"


def build(args: argparse.Namespace) -> int:
    workspace = _workspace_root(Path(args.workspace))
    train_path = Path(args.train or workspace / ".l9/cto-mode/train.json").resolve()
    train = load_train(train_path)
    repo: str = train["repo"]
    order = train_order(train)
    proven = {p["number"]: (p.get("proven_head") or "").lower() or None for p in train["prs"]}
    workdir = Path(args.workdir or Path.home() / ".l9/cto-integrate" / _repo_slug(repo))
    remote = args.remote or f"https://github.com/{repo}.git"
    manual = parse_resolutions(args.resolution or [])
    if args.candidate and not CANDIDATE_RE.fullmatch(args.candidate):
        raise IntegrateError(f"--candidate must match {CANDIDATE_RE.pattern}")

    clone = prepare_clone(workdir, remote, repo, workspace)
    with exclusive_lock(clone / ".git" / "l9-cto-integrate.lock", args.lock_wait) as got:
        if not got:
            raise IntegrateError(f"clone {clone} is busy (another build or run holds it)")
        fetch_refs(clone, train["base"], order)
        drivers = register_drivers(clone, Path(args.driver_registrar).resolve())
        base_sha = _rev(clone, "refs/l9/base")
        heads = {str(n): _rev(clone, f"refs/l9/pr/{n}") for n in order}
        moved = {
            str(n): {"proven_head": proven[n], "fetched": heads[str(n)]}
            for n in order
            if proven[n] and proven[n] != heads[str(n)]
        }
        candidate = args.candidate or default_candidate(train["campaign"], base_sha, heads)
        state_path = _integration_dir(workspace) / f"{candidate}.build.json"
        state: dict[str, Any] = {
            "schema": BUILD_SCHEMA,
            "grants_permission": False,
            "campaign": train["campaign"],
            "repo": repo,
            "base_ref": train["base"],
            "base_sha": base_sha,
            "candidate": candidate,
            "heads": heads,
            "order": order,
            "clone": str(clone),
            "branch": f"l9/candidate/{candidate}",
            "train": str(train_path),
            "train_sha256": _sha256_file(train_path),
            "drivers": drivers,
            "resolutions": [],
            "unclassified_driver_merges": [],
            "created_at": _now(),
        }
        if moved:
            state.update(status="stopped", reason="head_moved", moved=moved)
            _write_json(state_path, state)
            _emit({**state, "state": str(state_path)})
            return EXIT_STOPPED

        reset_to(clone, state["branch"], base_sha)
        used: set[tuple[int, str]] = set()
        for n in order:
            pre = _rev(clone, "HEAD")
            head = heads[str(n)]
            proc = _git(
                clone,
                "merge",
                "--no-ff",
                "--no-edit",
                "-m",
                f"l9 integrate PR #{n}",
                head,
                check=False,
            )
            manual_paths: set[str] = set()
            if proc.returncode != 0:
                conflicted = [
                    p
                    for p in _git(clone, "diff", "--name-only", "--diff-filter=U").stdout.split(
                        "\n"
                    )
                    if p
                ]
                if not conflicted:
                    _git(clone, "merge", "--abort", check=False)
                    state.update(
                        status="stopped",
                        reason="merge_failed",
                        pr=n,
                        head=head,
                        error=(proc.stderr or proc.stdout).strip(),
                    )
                    _write_json(state_path, state)
                    _emit({**state, "state": str(state_path)})
                    return EXIT_STOPPED
                unresolved = [p for p in conflicted if (n, p) not in manual]
                if unresolved:
                    report = _conflict_report(
                        clone, clone.parent / f"{clone.name}.conflicts" / candidate, n, unresolved
                    )
                    _git(clone, "merge", "--abort", check=False)
                    state.update(
                        status="stopped",
                        reason="conflict",
                        pr=n,
                        head=head,
                        conflicts=report,
                        next=(
                            "review both sides, write the resolved file, and rebuild with "
                            + " ".join(f"--resolution {n}:{p}:<file>" for p in unresolved)
                        ),
                    )
                    _write_json(state_path, state)
                    _emit({**state, "state": str(state_path)})
                    return EXIT_STOPPED
                for path in conflicted:
                    source = manual[(n, path)]
                    target = clone / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
                    _git(clone, "add", "--", path)
                    used.add((n, path))
                    manual_paths.add(path)
                    state["resolutions"].append(
                        {
                            "pr": n,
                            "path": path,
                            "kind": "manual",
                            "detail": f"reviewed resolution {source} sha256 {_sha256_file(source)}",
                        }
                    )
                _git(clone, "commit", "-q", "--no-edit")
            resolved, unclassified = driver_resolutions(clone, n, pre, head, manual_paths)
            state["resolutions"].extend(resolved)
            state["unclassified_driver_merges"].extend(unclassified)

        state.update(
            status="built",
            commit_sha=_rev(clone, "HEAD"),
            tree_sha=_rev(clone, "HEAD^{tree}"),
            unused_resolutions=[f"{n}:{p}" for (n, p) in manual if (n, p) not in used],
        )
        _write_json(state_path, state)
    _emit({**state, "state": str(state_path)})
    return EXIT_OK


# --------------------------------------------------------------------------- run


def run_command(
    argv: list[str], cwd: Path, timeout_s: float, env: dict[str, str] | None = None
) -> dict[str, Any]:
    """Run one argv in its own process group; kill the whole group on timeout."""
    started = time.monotonic()
    full_env = dict(os.environ)
    full_env.update(env or {})
    try:
        proc = subprocess.Popen(
            argv,
            cwd=cwd,
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except OSError as exc:
        return {
            "argv": argv,
            "rc": 127,
            "timed_out": False,
            "output": f"cannot start: {exc}",
            "seconds": 0.0,
        }
    timed_out = False
    try:
        out, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
        out, _ = proc.communicate()
    return {
        "argv": argv,
        "rc": proc.returncode,
        "timed_out": timed_out,
        "output": out.decode("utf-8", "replace"),
        "seconds": round(time.monotonic() - started, 3),
    }


_ODOO_RE = re.compile(r"(\d+) failed, (\d+) error\(s\) of (\d+) tests")
_PYTEST_COUNT_RE = re.compile(r"(\d+) (passed|failed|skipped|errors?)\b")


def parse_counts(output: str) -> dict[str, int] | None:
    """Parse a test summary: Odoo "N failed, M error(s) of T tests" (last one wins),
    else pytest's final summary line. None when neither is present."""
    odoo = _ODOO_RE.findall(output)
    if odoo:
        failed, errors, total = (int(x) for x in odoo[-1])
        return {
            "run": total,
            "passed": max(total - failed - errors, 0),
            "failed": failed,
            "errors": errors,
            "skipped": 0,
        }
    for line in reversed(output.splitlines()):
        if "no tests ran" in line:
            return {"run": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
        found = _PYTEST_COUNT_RE.findall(line)
        if found:
            counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
            for num, word in found:
                counts["errors" if word.startswith("error") else word] += int(num)
            counts["run"] = counts["passed"] + counts["failed"] + counts["errors"]
            return counts
    return None


def _tail(text: str) -> str:
    return text if len(text) <= OUTPUT_TAIL else "..." + text[-OUTPUT_TAIL:]


def _failure_detail(res: dict[str, Any]) -> str:
    why = "timeout" if res["timed_out"] else f"exit {res['rc']}"
    return f"{shlex.join(res['argv'])}: {why}"


def run_static(cmds: list[list[str]], clone: Path, timeout_s: float) -> tuple[dict, list]:
    results = [run_command(c, clone, timeout_s) for c in cmds]
    failures = [_failure_detail(r) for r in results if r["rc"] != 0 or r["timed_out"]]
    if not cmds:
        detail = "no static commands declared"
    elif failures:
        detail = "; ".join(failures)
    else:
        detail = f"{len(cmds)} command(s) passed"
    return {"ok": not failures, "detail": detail}, results


def run_suite(cmds: list[list[str]], clone: Path, timeout_s: float) -> tuple[dict, list]:
    results = [run_command(c, clone, timeout_s) for c in cmds]
    ok = all(r["rc"] == 0 and not r["timed_out"] for r in results)
    parsed = [parse_counts(r["output"]) for r in results]
    if any(p is None for p in parsed):
        totals: dict[str, int | None] = {"passed": None, "failed": None, "skipped": None}
    else:
        totals = {
            "passed": sum(p["passed"] for p in parsed if p),
            "failed": sum(p["failed"] + p["errors"] for p in parsed if p),
            "skipped": sum(p["skipped"] for p in parsed if p),
        }
    if totals["failed"]:
        ok = False
    return {"ok": ok, **totals}, results


def default_fixture(repo: str, runtime: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(runtime["command"]).encode()).hexdigest()[:12]
    return f"{_repo_slug(repo)}-{digest}"


def run_runtime(
    runtime: dict[str, Any] | None,
    clone: Path,
    lock_path: Path,
    lock_wait: float,
    allow_rebuild: bool,
    rebuild: list[str] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if runtime is None:
        return None, {"declared": False}
    env = dict(runtime.get("env") or {})
    timeout_s = float(runtime["timeout_s"])
    info: dict[str, Any] = {"declared": True, "fixture_lock": str(lock_path), "env": sorted(env)}
    with exclusive_lock(lock_path, lock_wait) as got:
        if not got:
            info["reason"] = "fixture_busy"
            return {"ok": False, "run": None, "failed": None, "errors": None}, info
        res = run_command(runtime["command"], clone, timeout_s, env)
        if INCOMPATIBLE_FIXTURE in res["output"].lower():
            info["reason"] = "fixture_inputs_changed"
            info["rebuild_command"] = shlex.join(rebuild) if rebuild else None
            if not rebuild:
                info["rebuild_hint"] = (
                    "UNKNOWN: the train declares no rebuild command; rerun with "
                    "--rebuild-command '<cmd>' --allow-rebuild after reviewing it"
                )
            if allow_rebuild and rebuild:
                info["rebuild"] = _summary(run_command(rebuild, clone, timeout_s, env))
                if info["rebuild"]["rc"] == 0 and not info["rebuild"]["timed_out"]:
                    res = run_command(runtime["command"], clone, timeout_s, env)
                    if INCOMPATIBLE_FIXTURE not in res["output"].lower():
                        info.pop("reason")
        info["result"] = _summary(res)
    if info.get("reason") == "fixture_inputs_changed":
        return {"ok": False, "run": None, "failed": None, "errors": None}, info
    counts = parse_counts(res["output"])
    ok = res["rc"] == 0 and not res["timed_out"]
    if counts is None:
        out: dict[str, Any] = {"ok": ok, "run": None, "failed": None, "errors": None}
    else:
        ok = ok and counts["failed"] == 0 and counts["errors"] == 0
        out = {
            "ok": ok,
            "run": counts["run"],
            "failed": counts["failed"],
            "errors": counts["errors"],
        }
    if res["timed_out"]:
        info["reason"] = "timeout"
    return out, info


def _summary(res: dict[str, Any]) -> dict[str, Any]:
    return {**res, "argv": shlex.join(res["argv"]), "output": _tail(res["output"])}


def validate_receipt(doc: dict[str, Any]) -> list[str]:
    import jsonschema

    schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    return [
        f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in validator.iter_errors(doc)
    ]


def run(args: argparse.Namespace) -> int:
    workspace = _workspace_root(Path(args.workspace))
    if not CANDIDATE_RE.fullmatch(args.candidate):
        raise IntegrateError(f"--candidate must match {CANDIDATE_RE.pattern}")
    idir = _integration_dir(workspace)
    state_path = idir / f"{args.candidate}.build.json"
    if not state_path.is_file():
        raise IntegrateError(f"no build state for candidate {args.candidate}: {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") != "built":
        raise IntegrateError(
            f"candidate {args.candidate} is {state.get('status')!r} "
            f"({state.get('reason')}); build it first"
        )
    train = load_train(Path(args.train or state["train"]))
    if train["repo"] != state["repo"] or train_order(train) != state["order"]:
        raise IntegrateError("train no longer matches the built candidate (repo or PRs); rebuild")
    for p in train["prs"]:
        want = (p.get("proven_head") or "").lower()
        if want and want != state["heads"][str(p["number"])]:
            raise IntegrateError(
                f"PR {p['number']}: train proven_head {want} differs from built head "
                f"{state['heads'][str(p['number'])]}; rebuild"
            )
    clone = Path(state["clone"])
    timeout_s = float(args.timeout)
    rebuild = shlex.split(args.rebuild_command) if args.rebuild_command else None
    if args.allow_rebuild and not rebuild:
        raise IntegrateError("--allow-rebuild needs --rebuild-command")
    runtime = train.get("runtime")
    fixture = args.fixture or (default_fixture(train["repo"], runtime) if runtime else "none")
    lock_dir = Path(args.lock_dir or Path.home() / ".l9/cto-integrate/locks")

    with exclusive_lock(clone / ".git" / "l9-cto-integrate.lock", args.lock_wait) as got:
        if not got:
            raise IntegrateError(f"clone {clone} is busy (another build or run holds it)")
        reset_to(clone, state["branch"], None)
        if (
            _rev(clone, "HEAD") != state["commit_sha"]
            or _rev(clone, "HEAD^{tree}") != state["tree_sha"]
        ):
            raise IntegrateError(f"candidate branch in {clone} moved since build; rebuild")
        static, static_runs = run_static(train.get("static", []), clone, timeout_s)
        suite, suite_runs = run_suite(train.get("suite", []), clone, timeout_s)
        runtime_result, runtime_info = run_runtime(
            runtime,
            clone,
            lock_dir / f"{fixture}.lock",
            float(args.lock_wait if args.fixture_wait is None else args.fixture_wait),
            args.allow_rebuild,
            rebuild,
        )

    executed = bool(train.get("static")) or bool(train.get("suite")) or runtime is not None
    passed = (
        executed
        and static["ok"]
        and suite["ok"]
        and (runtime_result is None or runtime_result["ok"])
    )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "grants_permission": False,
        "campaign": state["campaign"],
        "repo": state["repo"],
        "base_ref": state["base_ref"],
        "base_sha": state["base_sha"],
        "candidate": state["candidate"],
        "heads": state["heads"],
        "tree_sha": state["tree_sha"],
        "resolutions": state["resolutions"],
        "results": {"static": static, "suite": suite, "runtime": runtime_result},
        "verdict": "pass" if passed else "fail",
        "created_at": _now(),
    }
    errors = validate_receipt(receipt)
    if errors:
        raise IntegrateError("receipt failed its schema: " + "; ".join(errors))
    receipt_path = idir / f"{state['candidate']}.json"
    _write_json(receipt_path, receipt)
    report = {
        "schema": RUN_SCHEMA,
        "grants_permission": False,
        "candidate": state["candidate"],
        "receipt": str(receipt_path),
        "verdict": receipt["verdict"],
        "reasons": [
            r
            for r in (
                None if executed else "no_checks_declared",
                None if static["ok"] else "static_failed",
                None if suite["ok"] else "suite_failed",
                runtime_info.get("reason")
                or (None if runtime_result is None or runtime_result["ok"] else "runtime_failed"),
            )
            if r
        ],
        "static": [_summary(r) for r in static_runs],
        "suite": [_summary(r) for r in suite_runs],
        "runtime": runtime_info,
        "fixture": fixture,
        "created_at": receipt["created_at"],
    }
    _write_json(idir / f"{state['candidate']}.run.json", report)
    _emit(report)
    return EXIT_OK if passed else EXIT_FAIL


# --------------------------------------------------------------------------- check


def parse_heads(value: str) -> dict[str, str]:
    heads: dict[str, str] = {}
    for item in filter(None, (s.strip() for s in value.split(","))):
        pr, sep, sha = item.partition("=")
        if not sep or not pr.isdigit() or not SHA_RE.fullmatch(sha.lower()):
            raise IntegrateError(f"--heads entries must be pr=<full sha>, got {item!r}")
        heads[str(int(pr))] = sha.lower()
    if not heads:
        raise IntegrateError("--heads is empty")
    return heads


def check(args: argparse.Namespace) -> int:
    path = Path(args.receipt)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrateError(f"cannot read receipt {path}: {exc}") from exc
    if not isinstance(receipt, dict):
        raise IntegrateError(f"receipt {path} is not a JSON object")
    want = parse_heads(args.heads)
    reasons: list[str] = [f"schema: {e}" for e in validate_receipt(receipt)]
    if not reasons:
        if receipt["verdict"] != "pass":
            reasons.append("verdict is fail")
        have = receipt["heads"]
        for pr in sorted(set(want) | set(have), key=int):
            if pr not in have:
                reasons.append(f"PR {pr} is not in the receipt")
            elif pr not in want:
                reasons.append(f"receipt includes PR {pr}, which was not asked for")
            elif have[pr] != want[pr]:
                reasons.append(f"PR {pr}: receipt head {have[pr]} != {want[pr]}")
    _emit(
        {
            "schema": CHECK_SCHEMA,
            "grants_permission": False,
            "receipt": str(path),
            "ok": not reasons,
            "reasons": reasons,
        }
    )
    return EXIT_OK if not reasons else EXIT_FAIL


# --------------------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cto_integrate.py", description="CTO integration candidate builder and receipt writer."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="merge base + every train PR head in a disposable clone")
    b.add_argument("--train", help="train manifest (default <workspace>/.l9/cto-mode/train.json)")
    b.add_argument("--candidate", help="candidate name (default: campaign + digest of heads)")
    b.add_argument("--workdir", help="clone dir (default $HOME/.l9/cto-integrate/<owner__name>)")
    b.add_argument("--remote", help="clone source (default https://github.com/<repo>.git)")
    b.add_argument(
        "--driver-registrar",
        default=str(ENSURE_DRIVERS),
        help="merge-driver registrar run as `bash <registrar> <clone>` "
        "(default ops/scripts/ensure_git_merge_drivers.sh)",
    )
    b.add_argument(
        "--resolution",
        action="append",
        metavar="PR:path:file",
        help="apply a reviewed resolution file for a conflicted path (repeatable)",
    )
    b.add_argument("--lock-wait", type=float, default=600.0, help="seconds to wait for the clone")
    b.add_argument("--workspace", default=os.getcwd())
    b.set_defaults(func=build)

    r = sub.add_parser("run", help="run the train's checks on a built candidate; write receipt")
    r.add_argument("--candidate", required=True)
    r.add_argument("--train", help="train manifest (default: the one the candidate was built from)")
    r.add_argument("--timeout", type=float, default=1800.0, help="per static/suite command")
    r.add_argument("--fixture", help="runtime fixture name (default: repo + digest of command)")
    r.add_argument("--lock-dir", help="fixture lock dir (default $HOME/.l9/cto-integrate/locks)")
    r.add_argument("--lock-wait", type=float, default=600.0, help="seconds to wait for the clone")
    r.add_argument(
        "--fixture-wait", type=float, help="seconds to wait for the fixture (default --lock-wait)"
    )
    r.add_argument("--rebuild-command", help="reviewed command that rebuilds the runtime fixture")
    r.add_argument(
        "--allow-rebuild",
        action="store_true",
        help="rebuild once when the fixture reports changed inputs (never automatic)",
    )
    r.add_argument("--workspace", default=os.getcwd())
    r.set_defaults(func=run)

    c = sub.add_parser("check", help="exit 0 only for a pass receipt whose heads match")
    c.add_argument("--receipt", required=True)
    c.add_argument("--heads", required=True, help="pr=sha,pr=sha,...")
    c.set_defaults(func=check)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except IntegrateError as exc:
        _emit(
            {"schema": "l9.cto-integration-error/v1", "grants_permission": False, "error": str(exc)}
        )
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
