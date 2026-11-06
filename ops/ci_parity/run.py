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
import io
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
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


#: Languages the SDK's packaged Semgrep rulesets cover, by changed-file suffix.
SDK_LANGUAGES = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
}
#: What a proxied host needs to reach the Semgrep registry. The SDK hands
#: semgrep only PATH/HOME/TMP*, so behind a proxy semgrep exits 2 and writes no
#: report; a shim first on PATH restores these for that one process.
PROXY_ENV = (
    "HTTPS_PROXY",
    "https_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "NO_PROXY",
    "no_proxy",
    "SSL_CERT_FILE",
    "REQUESTS_CA_BUNDLE",
)
GATE_EXIT = {0: "pass", 1: "fail", 6: "incomplete"}


def sdk_languages(files: Sequence[str]) -> list[str]:
    return sorted({SDK_LANGUAGES[s] for f in files if (s := Path(f).suffix) in SDK_LANGUAGES})


def provider_path(directory: Path, semgrep: Path, env: dict[str, str]) -> str:
    """PATH for the SDK: a proxy shim when needed, then the pinned semgrep's directory."""
    entries = [str(semgrep.parent)]
    exported = {k: env[k] for k in PROXY_ENV if env.get(k)}
    if exported:
        shim_dir = directory / "semgrep-shim"
        shim_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        shim = shim_dir / "semgrep"
        lines = ["#!/bin/sh"]
        lines += [f"export {k}={shlex.quote(v)}" for k, v in sorted(exported.items())]
        lines.append(f'exec {shlex.quote(str(semgrep))} "$@"')
        shim.write_text("\n".join(lines) + "\n", encoding="utf-8")
        shim.chmod(0o700)
        entries.insert(0, str(shim_dir))
    return os.pathsep.join([*entries, env.get("PATH", "")])


def sdk_blocking_findings(gate: dict[str, Any], bundle: dict[str, Any]) -> list[fnd.Finding]:
    """Core's blocking findings, located through the SDK's own finding bundle."""
    by_id = {f.get("finding_id"): f for f in bundle.get("findings") or []}
    out: list[fnd.Finding] = []
    for finding_id in gate.get("blocking_finding_ids") or []:
        found = by_id.get(finding_id) or {}
        where = (found.get("locations") or [{}])[0]
        out.append(
            fnd.Finding(
                "semgrep-l9",
                str(found.get("provider_rule_id") or finding_id),
                "error",
                str(where.get("normalized_path") or "?"),
                int(where.get("start_line") or 0),
                str(found.get("message") or "blocking finding"),
            )
        )
    return out


def _provider_failure(bundle_path: Path) -> str:
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "no finding bundle"
    failures = bundle.get("provider_failures") or []
    return "; ".join(str(f.get("message") or f.get("failure_type")) for f in failures) or "unknown"


#: Where org-ci provisions the SDK and stages Core's governance, relative to the
#: checkout. Semgrep names a rule after its config file's path from the working
#: directory, so Core's policy keys read `l9.runtime.sdk.source.l9_ci...`: the
#: SDK source has to sit at this same relative path for those keys to match.
SDK_SOURCE = Path(".l9/runtime/sdk/source")
ORG_GOVERNANCE = Path(".l9/runtime/org-governance")
GOVERNANCE_ROOT = ".github/actions/resolve-governance"
#: Runs the SDK's CLI from SDK_SOURCE inside the pinned tool's environment (the
#: role Core's `.pth` edge plays), so the packaged rulesets resolve under the
#: checkout instead of the tool's site-packages.
SDK_BOOTSTRAP = (
    "import sys; sys.path.insert(0, sys.argv.pop(1)); "
    "from l9_ci.__main__ import main; raise SystemExit(main())"
)


@dataclass(frozen=True)
class CoreGovernance:
    """What resolve-governance emits for one Core profile."""

    core_sha: str
    strict: bool
    required: bool
    policy: Path  # staged, relative to the checkout
    identity_maps: Path  # staged directory, relative to the checkout


def _core_reader() -> Any:
    scripts = HERE.parent / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import docker_sandbox  # noqa: PLC0415  (the one reader of Core's files)

    return docker_sandbox


def _profile_value(text: str, profile: str, key: str) -> Any:
    import yaml  # noqa: PLC0415

    data = yaml.safe_load(text) or {}
    entry = (data.get("profiles") or {}).get(profile)
    if not isinstance(entry, dict) or key not in entry:
        raise ValueError(f"Core governance has no {key!r} for profile {profile!r}")
    return entry[key]


def stage_core_governance(
    ctx: Context, profile: str, languages: Sequence[str], core_ref: str = "main"
) -> CoreGovernance:
    """Read Core's bundled governance at `core_ref` and stage it like resolve-governance.

    Core never uses a consumer's own governance files for this gate; it ships
    the execution profile, policy and identity maps with its action.
    """
    reader = _core_reader()
    sha = reader.core_commit(core_ref)
    cached = ctx.loaded.cache_root / "core" / sha
    files = {
        "profiles": f"{GOVERNANCE_ROOT}/defaults/execution-profiles.yaml",
        "required": f"{GOVERNANCE_ROOT}/defaults/provider-requiredness.yaml",
        "thresholds": f"{GOVERNANCE_ROOT}/defaults/quality-thresholds.yaml",
    }

    def read(rel: str) -> str:
        path = cached / rel
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(reader.core_file(sha, rel), encoding="utf-8")
        return path.read_text(encoding="utf-8")

    strict = bool(_profile_value(read(files["profiles"]), profile, "strict"))
    required = bool(_profile_value(read(files["required"]), profile, "semgrep"))
    policy_name = Path(str(_profile_value(read(files["thresholds"]), profile, "sdk_policy"))).name
    staged = ctx.scan_dir / ORG_GOVERNANCE
    (staged / "semgrep-identity-maps").mkdir(parents=True, exist_ok=True)
    (staged / policy_name).write_text(read(f"{GOVERNANCE_ROOT}/{policy_name}"), encoding="utf-8")
    for language in languages:
        text = read(f"{GOVERNANCE_ROOT}/identity-maps/{language}.yaml")
        (staged / "semgrep-identity-maps" / f"{language}.yaml").write_text(text, encoding="utf-8")
    return CoreGovernance(
        core_sha=sha,
        strict=strict,
        required=required,
        policy=ORG_GOVERNANCE / policy_name,
        identity_maps=ORG_GOVERNANCE / "semgrep-identity-maps",
    )


def stage_sdk_source(ctx: Context, tool: manifest.Tool) -> Path:
    """The SDK at its pinned commit, extracted at SDK_SOURCE in the snapshot."""
    url = tool.package.removeprefix("git+")
    mirror = ctx.loaded.cache_root / "l9-ci-sdk.git"
    if not (mirror / "HEAD").is_file():
        mirror.mkdir(parents=True, exist_ok=True)
        _git(mirror, "init", "-q", "--bare")
    probe = subprocess.run(
        ["git", "-C", str(mirror), "cat-file", "-e", f"{tool.version}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        _git(mirror, "fetch", "-q", "--depth=1", url, tool.version)
    target = ctx.scan_dir / SDK_SOURCE
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    archive = subprocess.run(
        ["git", "-C", str(mirror), "archive", "--format=tar", tool.version],
        capture_output=True,
        check=True,
    )
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
        tar.extractall(target, filter="data")
    return target


def sdk_python(binary: Path) -> str:
    """The interpreter of the pinned l9-ci tool environment (its entry point's shebang)."""
    first = binary.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    if first and first[0].startswith("#!") and Path(first[0][2:].strip()).is_file():
        return first[0][2:].strip()
    sibling = binary.parent / "python"
    if sibling.is_file():
        return str(sibling)
    raise OSError(f"cannot find the Python behind {binary}")


def _lane_semgrep_l9(
    ctx: Context, lane: manifest.Lane, binary: Path, files: list[str]
) -> list[fnd.Finding]:
    """Core's SDK Semgrep gate on the whole snapshot, as org-ci runs it.

    Same SDK commit, semgrep version, rule composition, staged Core governance
    (profile strictness, requiredness, policy, identity map) and gate. The
    verdict is `gate evaluate`'s exit (0 pass, 1 fail, 6 incomplete); `semgrep
    run` exits 0 even when semgrep wrote no report, so it never stands for a pass.
    """
    provider = str(lane.extra.get("provider") or "semgrep")
    semgrep = ctx.loaded.resolve(provider)
    if semgrep is None:
        version = ctx.loaded.tools[provider].version
        ctx.notices.append(f"semgrep-l9: SKIP — {provider} {version} not installed")
        return []
    languages = sdk_languages(files)
    profile = str(lane.extra.get("core_profile") or "pr_fast")
    core_ref = str(lane.extra.get("core_ref") or "main")
    try:
        gov = stage_core_governance(ctx, profile, languages, core_ref)
        source = stage_sdk_source(ctx, ctx.loaded.tools[lane.tool])
        python = sdk_python(binary)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        ctx.notices.append(f"semgrep-l9: cannot stage Core's gate — {exc}")
        return []
    work = ctx.cache / "semgrep-l9"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    env = dict(os.environ)
    env["PATH"] = provider_path(work, semgrep, env)
    cli = [python, "-c", SDK_BOOTSTRAP, str(source)]
    try:
        return _sdk_gate(ctx, cli, languages, gov, work, env)
    finally:
        shutil.rmtree(work / "semgrep-shim", ignore_errors=True)  # proxy values off disk


def _sdk_gate(
    ctx: Context,
    cli: list[str],
    languages: Sequence[str],
    gov: CoreGovernance,
    work: Path,
    env: dict[str, str],
) -> list[fnd.Finding]:
    out: list[fnd.Finding] = []
    for language in languages:
        bundle = work / f"{language}.finding-bundle.json"
        gate_out = work / f"{language}.gate-result.json"
        run_argv = [*cli, "semgrep", "run", "--language", language, "--root", "."]
        run_argv += ["--output", str(bundle), "--snapshot-id", ctx.sha, "--revision", ctx.sha]
        run_argv += ["--policy", str(gov.policy)]
        run_argv += ["--identity-map", str(gov.identity_maps / f"{language}.yaml")]
        run_argv += ["--strict"] if gov.strict else []
        run_argv += ["--required"] if gov.required else []
        proc = _run(run_argv, ctx.scan_dir, ctx, env=env)
        if not bundle.is_file():
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or ["no output"]
            reason = tail[0][:240]
            ctx.notices.append(f"semgrep-l9 ({language}): the SDK wrote no bundle — {reason}")
            continue
        gate_argv = [*cli, "gate", "evaluate", "--bundle", str(bundle), "--output", str(gate_out)]
        gate_argv.append("--strict-unresolved" if gov.strict else "--no-strict-unresolved")
        verdict = GATE_EXIT.get(_run(gate_argv, ctx.scan_dir, ctx, env=env).returncode)
        if verdict == "pass":
            continue
        if verdict == "fail" and gate_out.is_file():
            gate = json.loads(gate_out.read_text(encoding="utf-8"))
            out.extend(sdk_blocking_findings(gate, json.loads(bundle.read_text(encoding="utf-8"))))
            continue
        reason = _provider_failure(bundle)
        ctx.notices.append(f"semgrep-l9 ({language}): gate {verdict or 'error'} — {reason}")
    return out


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


def lane_digest(
    lane: manifest.Lane, tool: manifest.Tool, provider: manifest.Tool | None = None
) -> str:
    """Receipt key: runner code, lane config, and every tool version the lane runs."""
    payload = json.dumps(
        {
            "runner": _runner_digest(),
            "lane": lane.__dict__,
            "tool": tool.version,
            "provider": provider.version if provider else None,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _lane_digest(loaded: manifest.Manifest, lane: manifest.Lane) -> str:
    provider = loaded.tools.get(str(lane.extra.get("provider") or ""))
    return lane_digest(lane, loaded.tools[lane.tool], provider)


def run_lane(ctx: Context, lane: manifest.Lane, sem: WeightedSemaphore) -> dict[str, Any]:
    tool = ctx.loaded.tools[lane.tool]
    files = [f for f in ctx.changed if lane.matches(f)]
    record: dict[str, Any] = {
        "lane": lane.name,
        "tool": lane.tool,
        "version": tool.version,
        "digest": _lane_digest(ctx.loaded, lane),
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
    # Lanes whose CI check judges a whole file or the whole tree keep every
    # finding; the rest keep only those on a line the change touched.
    scope = lane.extra.get("scope")
    if lane.name == "osv-scanner" or scope == "whole-tree":
        fresh = found
    elif scope == "changed-files":
        fresh = [f for f in found if f.path in files]
    else:
        fresh = fnd.new_findings(found, ctx.ranges)
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


def applicable(
    ctx: Context, tiers: Sequence[str], only: Sequence[str] | None = None
) -> list[manifest.Lane]:
    return [
        lane
        for lane in ctx.loaded.lanes.values()
        if lane.tier in tiers
        and (only is None or lane.name in only)
        and any(lane.matches(f) for f in ctx.changed)
    ]


def run_lanes(ctx: Context, lanes: Sequence[manifest.Lane]) -> list[dict[str, Any]]:
    if not lanes:
        return []
    sem = WeightedSemaphore(os.cpu_count() or 2)
    with ThreadPoolExecutor(max_workers=len(lanes)) as pool:
        return list(pool.map(lambda lane: run_lane(ctx, lane, sem), lanes))


# --- snapshot clone, receipts, in-flight ------------------------------------


def _has_commit(clone: Path, sha: str) -> bool:
    probe = subprocess.run(
        ["git", "-C", str(clone), "cat-file", "-e", f"{sha}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


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
    if not _has_commit(clone, sha):
        # A shallow workspace cannot be shared: git ignores --shared/--local for
        # a shallow source, so the clone is a copy frozen at creation, with no
        # alternates. Every later commit was then "not a tree" (checkout exit
        # 128) on every run — hosted checkouts are shallow. Fetch it in, from
        # the workspace being scanned: the clone is cached per repository, so
        # its `origin` is whichever workspace created it, and another worktree
        # or clone's commits are not there.
        _git(clone, "fetch", "-q", "--no-tags", str(workspace), sha)
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
        if data.get("digest") == _lane_digest(ctx.loaded, lane) and data.get("status") != "error":
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


def scan_commit(
    ctx: Context, wait: float, only: Sequence[str] | None = None
) -> list[dict[str, Any]]:
    """Run every applicable lane (or only the named ones) not already receipted."""
    lanes = applicable(ctx, ("fast", "heavy"), only)
    with clone_lock(ctx.cache, wait):
        have = read_receipts(ctx.cache, ctx)
        missing = [lane for lane in lanes if lane.name not in have]
        if missing:
            ensure_snapshot(ctx.workspace, ctx.cache, ctx.sha)
            records = run_lanes(ctx, missing)
            write_receipts(ctx.cache, ctx, records)
            have.update({r["lane"]: r for r in records})
    return [have[lane.name] for lane in lanes if lane.name in have]


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


def mode_gate(
    loaded: manifest.Manifest,
    workspace: Path,
    sha_ref: str,
    base: str | None,
    only: Sequence[str] | None = None,
) -> int:
    ctx = build_context(loaded, workspace, sha_ref, base, nice=True)
    if ctx is None:
        print(
            f"ci-parity gate {sha_ref}: cannot-evaluate — merge-base unresolved "
            "(shallow history or missing base; no parent-commit fallback)"
        )
        return 0
    if not applicable(ctx, ("fast", "heavy"), only):
        print(f"ci-parity gate {ctx.sha[:8]}: no lane applies to this change")
        return 0
    wait = float(os.environ.get("L9_CI_PARITY_WAIT") or DEFAULT_WAIT)
    try:
        records = scan_commit(ctx, wait=wait, only=only)
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
    parser.add_argument(
        "--lanes",
        help="--gate only: comma-separated lane names to run (default: every applicable lane)",
    )
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
    only = None
    if args.lanes:
        only = [name.strip() for name in args.lanes.split(",") if name.strip()]
        unknown = sorted(set(only) - set(loaded.lanes))
        if unknown:
            parser.error(f"--lanes: unknown lane(s) {', '.join(unknown)}")
    return mode_gate(loaded, workspace, args.gate, args.base, only)


if __name__ == "__main__":
    raise SystemExit(main())
