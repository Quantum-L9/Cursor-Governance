#!/usr/bin/env python3
"""Run CI-parity scanners at the right moment, off the working tree.

Modes (see README.md for the timing table):

    run.py --file PATH...      edit time: fast lanes on the edited files, in the
                               workspace, findings on lines changed vs HEAD only
    run.py --commit SHA [--background]
                               commit time: every applicable lane on the commit,
                               in a snapshot clone, receipts written; background
                               detaches and cancels an older commit's run
    run.py --gate SHA          pre-push: reuse receipts for SHA (waiting on an
                               in-flight run), run missing lanes, exit 2 when a
                               NEW finding on a changed line blocks
    run.py --status            receipts and in-flight state for this repository

Scans never touch the working tree: commit and gate runs check SHA out into a
`git clone --shared` under ~/.cache/l9-ci-parity/<repo>/clone, serialized by
an flock, and every receipt lives beside it. Lanes run concurrently under a
weighted CPU budget of nproc slots at nice 10, so pytest in make pr keeps
priority. L9_CI_PARITY=0 disables everything.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
for _path in (HERE, HERE.parent / "secrets"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import findings as fnd  # noqa: E402
import manifest  # noqa: E402

RUNNER_VERSION = "1"
YAMLLINT_CONFIG = HERE / "lanes" / "yamllint.yaml"
FILE_MODE_TIMEOUT = 8
LANE_TIMEOUT = 1800
KEEP_RECEIPTS = 5
DEFAULT_WAIT = 600


# --- repository context ------------------------------------------------------


def _git(repo: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=check
    )
    return proc.stdout.strip()


def toplevel(path: Path) -> Path:
    start = path if path.is_dir() else path.parent
    return Path(_git(start, "rev-parse", "--show-toplevel"))


def repo_slug(repo: Path) -> str:
    url = _git(repo, "remote", "get-url", "origin", check=False)
    tail = url.rstrip("/").removesuffix(".git")
    parts = tail.replace(":", "/").split("/")
    if len(parts) >= 2 and parts[-1] and parts[-2]:
        return f"{parts[-2]}/{parts[-1]}"
    return f"local/{repo.name}"


def open_pr_base(repo: Path, slug: str) -> str | None:
    """origin/<base> of the open PR for this branch (REST GET), when resolvable.

    A stacked branch's PR is judged by CI against its parent branch, not main;
    diffing against main would attribute the parent's lines to this change.
    """
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    gh = shutil.which("gh")
    if not branch or branch == "HEAD" or gh is None or slug.startswith("local/"):
        return None
    owner = slug.split("/", 1)[0]
    try:
        proc = subprocess.run(
            [
                gh,
                "api",
                "--method",
                "GET",
                f"repos/{slug}/pulls",
                "-f",
                f"head={owner}:{branch}",
                "-f",
                "state=open",
                "--jq",
                ".[0].base.ref // empty",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    ref = proc.stdout.strip()
    if proc.returncode != 0 or not ref:
        return None
    candidate = f"origin/{ref}"
    return candidate if _git(repo, "rev-parse", "--verify", "-q", candidate, check=False) else None


def resolve_base(repo: Path, sha: str, base: str | None) -> str | None:
    """Merge-base of the requested ref and sha, or None when it cannot be evaluated.

    A missing base or a shallow history that cannot see the base is cannot-evaluate.
    Never substitutes ``sha^`` or ``sha``: that would hide earlier commits of a
    multi-commit change.
    """
    ref = (
        base
        or os.environ.get("L9_CI_PARITY_BASE")
        or os.environ.get("PR_BASE")
        or open_pr_base(repo, repo_slug(repo))
        or "origin/main"
    )
    return _git(repo, "merge-base", ref, sha, check=False) or None


@dataclass
class Context:
    loaded: manifest.Manifest
    workspace: Path
    slug: str
    cache: Path
    scan_dir: Path
    sha: str
    base: str
    changed: list[str]
    ranges: dict[str, list[tuple[int, int]]]
    nice: bool
    timeout: int
    notices: list[str] = field(default_factory=list)


def cache_dir(loaded: manifest.Manifest, slug: str) -> Path:
    path = loaded.cache_root / slug.replace("/", "__")
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- process helpers ---------------------------------------------------------


def _run(
    argv: Sequence[str], cwd: Path, ctx: Context, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    child_env = dict(os.environ if env is None else env)
    child_env.pop("SEMGREP_APP_TOKEN", None)  # only capability_exec may place it
    return subprocess.run(
        list(argv),
        cwd=cwd,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=ctx.timeout,
        preexec_fn=(lambda: os.nice(10)) if ctx.nice else None,
        check=False,
    )


class WeightedSemaphore:
    """nproc slots shared by concurrently running lanes."""

    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self.used = 0
        self._cond = threading.Condition()

    def acquire(self, weight: int) -> int:
        weight = min(max(1, weight), self.capacity)
        with self._cond:
            while self.used + weight > self.capacity:
                self._cond.wait()
            self.used += weight
        return weight

    def release(self, weight: int) -> None:
        with self._cond:
            self.used -= weight
            self._cond.notify_all()


# --- lanes -------------------------------------------------------------------

LaneFn = Callable[[Context, manifest.Lane, Path, list[str]], list[fnd.Finding]]


def _lane_ruff(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    proc = _run(
        [str(binary), "check", "--output-format=json", "--no-fix", *files], ctx.scan_dir, ctx
    )
    return fnd.parse_ruff(proc.stdout, ctx.scan_dir, files)


def _lane_shellcheck(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    proc = _run([str(binary), "--format=json1", "-x", *files], ctx.scan_dir, ctx)
    return fnd.parse_shellcheck(proc.stdout or "{}", ctx.scan_dir, files)


def _lane_actionlint(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    proc = _run([str(binary), "-format", "{{json .}}", *files], ctx.scan_dir, ctx)
    return fnd.parse_actionlint(proc.stdout or "[]", ctx.scan_dir, files)


def _lane_zizmor(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    proc = _run([str(binary), "--offline", "--format", "sarif", *files], ctx.scan_dir, ctx)
    return fnd.parse_sarif(json.loads(proc.stdout or "{}"), "zizmor", ctx.scan_dir, files)


def _lane_yamllint(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    proc = _run(
        [str(binary), "-f", "parsable", "-c", str(YAMLLINT_CONFIG), *files], ctx.scan_dir, ctx
    )
    return fnd.parse_yamllint(proc.stdout, ctx.scan_dir, files)


def _lane_biome(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    proc = _run([str(binary), "ci", "--reporter=sarif", "--colors=off", *files], ctx.scan_dir, ctx)
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return []
    return fnd.parse_sarif(data, "biome", ctx.scan_dir, files)


def _lane_codeql(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    threads = str(max(1, lane.weight))
    db = ctx.cache / "codeql-db"
    sarif = ctx.cache / "codeql.sarif"
    config = ctx.scan_dir / str(lane.extra.get("config") or "")
    languages = ",".join(lane.extra.get("languages") or ["python"])
    create = [
        str(binary),
        "database",
        "create",
        str(db),
        f"--language={languages}",
        "--build-mode=none",
        f"--source-root={ctx.scan_dir}",
        f"--threads={threads}",
        "--overwrite",
    ]
    if config.is_file():
        create.append(f"--codescanning-config={config}")
    proc = _run(create, ctx.scan_dir, ctx)
    if proc.returncode != 0:
        ctx.notices.append("codeql: database create failed")
        return []
    analyze = [
        str(binary),
        "database",
        "analyze",
        str(db),
        "--format=sarif-latest",
        f"--output={sarif}",
        f"--threads={threads}",
    ]
    proc = _run(analyze, ctx.scan_dir, ctx)
    if proc.returncode != 0 or not sarif.is_file():
        ctx.notices.append("codeql: analyze failed")
        return []
    return fnd.parse_sarif(
        json.loads(sarif.read_text(encoding="utf-8")), "codeql", ctx.scan_dir, files
    )


def _lane_semgrep_l9(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    sarif = ctx.cache / "semgrep-l9.sarif"
    argv = [
        str(binary),
        "scan",
        "--sarif",
        f"--output={sarif}",
        "--metrics=off",
        "--disable-version-check",
        "--quiet",
    ]
    for config in lane.extra.get("configs") or []:
        argv.append(f"--config={config}")
    argv += [f"--baseline-commit={ctx.base}", "."]
    _run(argv, ctx.scan_dir, ctx)
    if not sarif.is_file():
        ctx.notices.append("semgrep-l9: no SARIF produced")
        return []
    return fnd.parse_sarif(
        json.loads(sarif.read_text(encoding="utf-8")), "semgrep-l9", ctx.scan_dir, files
    )


def _lane_semgrep_pro(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    import capability_exec as cx  # noqa: PLC0415

    sarif = ctx.cache / "semgrep-pro.sarif"
    sarif.unlink(missing_ok=True)
    plan = cx.plan(
        str(lane.extra.get("capability") or "semgrep-pro"),
        {"output": str(sarif), "baseline": ctx.base, "repo": ctx.slug},
        str(ctx.scan_dir),
        cx.load_registry(),
    )
    result = cx.execute(plan)
    if result.status == "unbound":
        ctx.notices.append(
            "semgrep-pro: SKIP — SEMGREP_APP_TOKEN not bound (set the Infisical identity)"
        )
        return []
    if result.status != "ok" or not sarif.is_file():
        ctx.notices.append(f"semgrep-pro: {result.status}")
        return []
    return fnd.parse_sarif(
        json.loads(sarif.read_text(encoding="utf-8") or "{}"), "semgrep-pro", ctx.scan_dir, files
    )


def _lane_osv(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    out: list[fnd.Finding] = []
    for rel in files:
        head = _osv_scan(ctx, binary, ctx.scan_dir / rel)
        with tempfile.TemporaryDirectory() as tmp:
            base_file = Path(tmp) / Path(rel).name
            shown = subprocess.run(
                ["git", "-C", str(ctx.scan_dir), "show", f"{ctx.base}:{rel}"],
                capture_output=True,
                check=False,
            )
            base = set()
            if shown.returncode == 0:
                base_file.write_bytes(shown.stdout)
                base = _osv_scan(ctx, binary, base_file)
        for _, package, vuln in sorted(head - base):
            out.append(
                fnd.Finding(
                    "osv-scanner", vuln, "error", rel, 1, f"{package} is affected by {vuln}"
                )
            )
    return out


def _osv_scan(ctx: Context, binary: Path, path: Path) -> set[tuple[str, str, str]]:
    proc = _run(
        [str(binary), "scan", "source", "-L", str(path), "--format", "json"], ctx.scan_dir, ctx
    )
    try:
        return fnd.osv_vulnerabilities(json.loads(proc.stdout or "{}"))
    except json.JSONDecodeError:
        ctx.notices.append(f"osv-scanner: unreadable output for {path.name}")
        return set()


LANES: dict[str, LaneFn] = {
    "ruff": _lane_ruff,
    "shellcheck": _lane_shellcheck,
    "actionlint": _lane_actionlint,
    "zizmor": _lane_zizmor,
    "yamllint": _lane_yamllint,
    "biome": _lane_biome,
    "codeql": _lane_codeql,
    "semgrep-l9": _lane_semgrep_l9,
    "semgrep-pro": _lane_semgrep_pro,
    "osv-scanner": _lane_osv,
}
#: Lanes whose result already depends on the whole tree, not just matched files.
WHOLE_TREE = frozenset({"codeql", "semgrep-l9", "semgrep-pro"})


def _mapped_rules(ctx: Context, lane: manifest.Lane) -> frozenset[str]:
    rel = lane.extra.get("identity_map")
    if not rel:
        return frozenset()
    import yaml  # noqa: PLC0415

    try:
        data = yaml.safe_load((ctx.scan_dir / str(rel)).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return frozenset()
    return frozenset((data.get("rules") or {}).keys())


def _runner_digest() -> str:
    """The runner's own code: a change to how findings are judged voids receipts."""
    digest = hashlib.sha256(RUNNER_VERSION.encode())
    for path in (
        Path(__file__).resolve(),
        HERE / "findings.py",
        HERE / "manifest.py",
        YAMLLINT_CONFIG,
    ):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def lane_digest(lane: manifest.Lane, tool: manifest.Tool) -> str:
    payload = json.dumps(
        {"runner": _runner_digest(), "lane": lane.__dict__, "tool": tool.version},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def run_lane(ctx: Context, lane: manifest.Lane, sem: WeightedSemaphore) -> dict[str, Any]:
    tool = ctx.loaded.tools[lane.tool]
    files = [f for f in ctx.changed if lane.matches(f)]
    record: dict[str, Any] = {
        "lane": lane.name,
        "tool": lane.tool,
        "version": tool.version,
        "digest": lane_digest(lane, tool),
        "sha": ctx.sha,
        "base": ctx.base,
        "status": "pass",
        "blocking": [],
        "advisory": [],
        "notice": "",
    }
    binary = ctx.loaded.resolve(lane.tool)
    if binary is None:
        record.update(
            status="skip",
            notice=f"{lane.tool} {tool.version} not installed (ops/ci_parity/install.py)",
        )
        return record
    ctx = replace(ctx, notices=[])  # per lane: lanes run concurrently
    weight = sem.acquire(lane.weight)
    started = time.monotonic()
    try:
        found = LANES[lane.name](ctx, lane, binary, files)
    except subprocess.TimeoutExpired:
        found = []
        ctx.notices.append(f"{lane.name}: timed out")
    except (OSError, ValueError) as exc:
        found = []
        ctx.notices.append(f"{lane.name}: {type(exc).__name__}")
    finally:
        sem.release(weight)
    record["elapsed_ms"] = int((time.monotonic() - started) * 1000)
    fresh = found if lane.name == "osv-scanner" else fnd.new_findings(found, ctx.ranges)
    mapped = _mapped_rules(ctx, lane)
    for finding in fresh:
        bucket = "blocking" if fnd.blocks(finding, lane.block, mapped) else "advisory"
        record[bucket].append(finding.as_dict())
    lane_notices = ctx.notices
    if lane_notices:
        record["notice"] = "; ".join(lane_notices)
        if any("SKIP" in n for n in lane_notices):
            record["status"] = "skip"
        elif not fresh:
            record["status"] = "error"
    if record["blocking"]:
        record["status"] = "fail"
    return record


def applicable(ctx: Context, tiers: Sequence[str]) -> list[manifest.Lane]:
    return [
        lane
        for lane in ctx.loaded.lanes.values()
        if lane.tier in tiers and any(lane.matches(f) for f in ctx.changed)
    ]


def run_lanes(ctx: Context, lanes: Sequence[manifest.Lane]) -> list[dict[str, Any]]:
    if not lanes:
        return []
    sem = WeightedSemaphore(os.cpu_count() or 2)
    with ThreadPoolExecutor(max_workers=len(lanes)) as pool:
        return list(pool.map(lambda lane: run_lane(ctx, lane, sem), lanes))


# --- snapshot clone, receipts, in-flight ------------------------------------


def ensure_snapshot(workspace: Path, cache: Path, sha: str) -> Path:
    clone = cache / "clone"
    if not (clone / ".git").exists():
        if clone.exists():
            shutil.rmtree(clone)
        subprocess.run(
            ["git", "clone", "-q", "--shared", "--no-checkout", str(workspace), str(clone)],
            check=True,
            capture_output=True,
        )
    _git(clone, "-c", "advice.detachedHead=false", "checkout", "-q", "--detach", "--force", sha)
    _git(clone, "clean", "-q", "-f", "-d", "-x")
    return clone


def receipt_dir(cache: Path, sha: str, base: str) -> Path:
    return cache / "receipts" / f"{sha[:12]}__{base[:12]}"


def read_receipts(cache: Path, ctx: Context) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    directory = receipt_dir(cache, ctx.sha, ctx.base)
    for lane in ctx.loaded.lanes.values():
        path = directory / f"{lane.name}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        tool = ctx.loaded.tools[lane.tool]
        if data.get("digest") == lane_digest(lane, tool) and data.get("status") != "error":
            found[lane.name] = data
    return found


def write_receipts(cache: Path, ctx: Context, records: Sequence[dict[str, Any]]) -> None:
    directory = receipt_dir(cache, ctx.sha, ctx.base)
    directory.mkdir(parents=True, exist_ok=True)
    for record in records:
        tmp = directory / f".{record['lane']}.tmp"
        tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        tmp.replace(directory / f"{record['lane']}.json")
    receipts = sorted((cache / "receipts").iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in receipts[KEEP_RECEIPTS:]:
        if stale.is_dir() and stale.parent == cache / "receipts":
            shutil.rmtree(stale, ignore_errors=True)


def _inflight_path(cache: Path) -> Path:
    return cache / "inflight.json"


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def read_inflight(cache: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(_inflight_path(cache).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and _alive(int(data.get("pid") or 0)) else None


def cancel_older(cache: Path, sha: str) -> None:
    """Latest-wins: a newer commit's run cancels an older commit's run."""
    current = read_inflight(cache)
    if current and current.get("sha") != sha:
        try:
            os.killpg(int(current["pgid"]), signal.SIGTERM)
        except (OSError, ValueError, KeyError):
            # Already exited, or a malformed record: nothing left to cancel. The
            # clone lock still serializes us behind anything that survives.
            return


class clone_lock:
    """flock on the snapshot clone; waits up to `wait` seconds."""

    def __init__(self, cache: Path, wait: float) -> None:
        self.path = cache / "clone.lock"
        self.wait = wait
        self.handle: Any = None

    def __enter__(self) -> clone_lock:
        self.handle = self.path.open("w")
        deadline = time.monotonic() + self.wait
        while True:
            try:
                fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self.handle.close()
                    raise TimeoutError("ci-parity: snapshot clone busy") from None
                time.sleep(0.5)

    def __exit__(self, *_exc: object) -> None:
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()


# --- modes -------------------------------------------------------------------


def build_context(
    loaded: manifest.Manifest, workspace: Path, sha_ref: str, base: str | None, *, nice: bool
) -> Context | None:
    sha = _git(workspace, "rev-parse", sha_ref)
    merge_base = resolve_base(workspace, sha, base)
    if merge_base is None:
        return None
    changed = [
        line
        for line in _git(
            workspace, "diff", "--name-only", "--diff-filter=ACMR", merge_base, sha
        ).splitlines()
        if line
    ]
    slug = repo_slug(workspace)
    cache = cache_dir(loaded, slug)
    return Context(
        loaded=loaded,
        workspace=workspace,
        slug=slug,
        cache=cache,
        scan_dir=cache / "clone",
        sha=sha,
        base=merge_base,
        changed=changed,
        ranges=fnd.changed_ranges(workspace, merge_base, sha),
        nice=nice,
        timeout=LANE_TIMEOUT,
    )


def scan_commit(ctx: Context, wait: float) -> list[dict[str, Any]]:
    """Run every applicable lane not already receipted for this commit."""
    with clone_lock(ctx.cache, wait):
        have = read_receipts(ctx.cache, ctx)
        missing = [lane for lane in applicable(ctx, ("fast", "heavy")) if lane.name not in have]
        if missing:
            ensure_snapshot(ctx.workspace, ctx.cache, ctx.sha)
            records = run_lanes(ctx, missing)
            write_receipts(ctx.cache, ctx, records)
            have.update({r["lane"]: r for r in records})
    return [have[lane.name] for lane in applicable(ctx, ("fast", "heavy")) if lane.name in have]


def summarize(ctx: Context, records: Sequence[dict[str, Any]], *, label: str) -> tuple[str, int]:
    blocking = [f for r in records for f in r.get("blocking", [])]
    advisory = [f for r in records for f in r.get("advisory", [])]
    skipped = [r for r in records if r.get("status") in ("skip", "error")]
    lines = [
        f"ci-parity {label} {ctx.sha[:8]} base {ctx.base[:8]}: lanes={len(records)} "
        f"blocking={len(blocking)} advisory={len(advisory)} skipped={len(skipped)}"
    ]
    for item in blocking[:40]:
        lines.append("  BLOCK " + fnd.Finding.from_dict(item).render())
    for item in advisory[:15]:
        lines.append("  note  " + fnd.Finding.from_dict(item).render())
    for record in skipped:
        lines.append(
            f"  skip  {record.get('notice') or record['lane'] + ': ' + str(record.get('status'))}"
        )
    return "\n".join(lines), len(blocking)


def mode_file(loaded: manifest.Manifest, paths: Sequence[str]) -> int:
    by_repo: dict[Path, list[str]] = {}
    for raw in paths:
        path = Path(raw).resolve()
        if not path.is_file():
            continue
        try:
            repo = toplevel(path)
        except subprocess.CalledProcessError:
            continue
        by_repo.setdefault(repo, []).append(path.relative_to(repo).as_posix())
    output: list[str] = []
    for repo, rels in by_repo.items():
        ranges = (
            fnd.changed_ranges(repo, "HEAD", None)
            if _git(repo, "rev-parse", "--verify", "-q", "HEAD", check=False)
            else {r: [fnd.WHOLE_FILE] for r in rels}
        )
        ctx = Context(
            loaded=loaded,
            workspace=repo,
            slug=repo_slug(repo),
            cache=cache_dir(loaded, repo_slug(repo)),
            scan_dir=repo,
            sha="worktree",
            base="HEAD",
            changed=rels,
            ranges={r: ranges.get(r, []) for r in rels},
            nice=False,
            timeout=FILE_MODE_TIMEOUT,
        )
        records = run_lanes(ctx, applicable(ctx, ("fast",)))
        findings = [f for r in records for f in r.get("blocking", []) + r.get("advisory", [])]
        for item in findings[:20]:
            output.append(fnd.Finding.from_dict(item).render())
    if output:
        print("ci-parity (edited lines):\n  " + "\n  ".join(output))
    return 0


def mode_commit(
    loaded: manifest.Manifest, workspace: Path, sha_ref: str, base: str | None, background: bool
) -> int:
    if background:
        log = cache_dir(loaded, repo_slug(workspace)) / "commit.log"
        argv = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--commit",
            sha_ref,
            "--workspace",
            str(workspace),
        ]
        if base:
            argv += ["--base", base]
        with log.open("ab") as handle:
            subprocess.Popen(
                argv, stdout=handle, stderr=handle, stdin=subprocess.DEVNULL, start_new_session=True
            )
        return 0
    ctx = build_context(loaded, workspace, sha_ref, base, nice=True)
    if ctx is None:
        print(
            f"ci-parity commit {sha_ref}: cannot-evaluate — merge-base unresolved "
            "(shallow history or missing base; no parent-commit fallback)"
        )
        return 0
    if not applicable(ctx, ("fast", "heavy")):
        return 0
    cancel_older(ctx.cache, ctx.sha)
    _inflight_path(ctx.cache).write_text(
        json.dumps(
            {"sha": ctx.sha, "pid": os.getpid(), "pgid": os.getpgid(0), "started": time.time()}
        ),
        encoding="utf-8",
    )
    try:
        records = scan_commit(ctx, wait=LANE_TIMEOUT)
    finally:
        current = read_inflight(ctx.cache)
        if current and current.get("pid") == os.getpid():
            _inflight_path(ctx.cache).unlink(missing_ok=True)
    text, _ = summarize(ctx, records, label="commit")
    print(text)
    return 0


def mode_gate(loaded: manifest.Manifest, workspace: Path, sha_ref: str, base: str | None) -> int:
    ctx = build_context(loaded, workspace, sha_ref, base, nice=True)
    if ctx is None:
        print(
            f"ci-parity gate {sha_ref}: cannot-evaluate — merge-base unresolved "
            "(shallow history or missing base; no parent-commit fallback)"
        )
        return 0
    if not applicable(ctx, ("fast", "heavy")):
        print(f"ci-parity gate {ctx.sha[:8]}: no lane applies to this change")
        return 0
    wait = float(os.environ.get("L9_CI_PARITY_WAIT") or DEFAULT_WAIT)
    try:
        records = scan_commit(ctx, wait=wait)
    except TimeoutError:
        print(
            f"ci-parity gate {ctx.sha[:8]}: SKIP — scan still running after "
            f"{int(wait)}s (L9_CI_PARITY_WAIT)"
        )
        return 0
    text, blocking = summarize(ctx, records, label="gate")
    print(text)
    return 2 if blocking else 0


def mode_status(loaded: manifest.Manifest, workspace: Path) -> int:
    cache = cache_dir(loaded, repo_slug(workspace))
    inflight = read_inflight(cache)
    running = str(inflight.get("sha", ""))[:8] if inflight else "none"
    print(f"ci-parity: repo={repo_slug(workspace)} inflight={running}")
    for directory in sorted(
        (cache / "receipts").glob("*"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        verdicts = []
        for path in sorted(directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            verdicts.append(f"{data['lane']}={data['status']}")
        print(f"  {directory.name}: {' '.join(verdicts)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--file", nargs="+")
    mode.add_argument("--commit")
    mode.add_argument("--gate")
    mode.add_argument("--status", action="store_true")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--base")
    parser.add_argument("--background", action="store_true")
    args = parser.parse_args(argv)
    if manifest.disabled():
        print("ci-parity: disabled (L9_CI_PARITY=0)")
        return 0
    loaded = manifest.load()
    if args.file:
        return mode_file(loaded, args.file)
    workspace = toplevel((args.workspace or Path.cwd()).resolve())
    if args.status:
        return mode_status(loaded, workspace)
    if args.commit:
        return mode_commit(loaded, workspace, args.commit, args.base, args.background)
    return mode_gate(loaded, workspace, args.gate, args.base)


if __name__ == "__main__":
    raise SystemExit(main())
