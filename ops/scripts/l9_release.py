#!/usr/bin/env python3
"""``make release`` — the Cursor-Governance front door to Core's release engine.

The release engine (``tools.l9_release``: plan / build / publish / verify, schema
``l9.release/v1``) and the release runner live in Quantum-L9/l9-ci-core. This
front door holds no engine code. It resolves Core at the revision pinned in
``ops/config/release-core.json`` and either runs the engine's read-only stages
locally or asks Core's release runner to release this repository::

    l9 release                    # plan (read-only): what would be released
    l9 release DRY_RUN=1          # plan + reproducible build, locally; publishes nothing
    l9 release DISPATCH=1         # workflow_dispatch Core's release runner for this repo
    make -C "$GOV" release WS="$PWD" [DRY_RUN=1] [DISPATCH=1]

It never tags, pushes a tag, or creates a Release: publication is Core's runner.

Exit codes: 0 done; 1 refused (engine precondition, or this front door's own
input checks); 2 engine tool/transport/contract failure; 3 transport failure of
this front door (Core fetch, dispatch).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PIN_PATH = ROOT / "ops" / "config" / "release-core.json"
PIN_SCHEMA = "l9.release-core-pin/v1"

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_TRANSPORT = 3

_SHA = re.compile(r"^[0-9a-f]{40}$")
_SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_GITHUB_URL = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)

#: Governance invocation state that must not reach the engine or the released
#: repository's own Make/build: command-line overrides travel in MAKEFLAGS,
#: Repo.mk exports PYTHON as the governance interpreter, and the governance
#: toolchain exports UV_PROJECT / UV_PROJECT_ENVIRONMENT, which would point the
#: released repository's `uv` at Cursor-Governance.
_ENGINE_ENV_DROP = frozenset(
    {
        "MAKEFLAGS",
        "MFLAGS",
        "MAKELEVEL",
        "MAKEOVERRIDES",
        "MAKE_TERMOUT",
        "MAKE_TERMERR",
        "PYTHON",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "UV_PROJECT",
        "UV_PROJECT_ENVIRONMENT",
        "UV_WORKING_DIRECTORY",
        "UV_PYTHON",
        "WS",
        "DRY_RUN",
        "DISPATCH",
        "GOV_ROOT",
    }
)


class Refused(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def load_pin(path: Path = PIN_PATH) -> dict[str, str]:
    try:
        pin = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(EXIT_REFUSED, f"{path}: unreadable Core pin: {exc}") from exc
    problems = []
    if pin.get("schema") != PIN_SCHEMA:
        problems.append(f"schema is not {PIN_SCHEMA}")
    if not _SLUG.match(str(pin.get("repository", ""))):
        problems.append("repository is not owner/name")
    if not _SHA.match(str(pin.get("revision", ""))):
        problems.append("revision is not a 40-hex commit")
    for key in ("engine_module", "runner_workflow", "runner_ref"):
        if not str(pin.get(key, "")).strip():
            problems.append(f"{key} is empty")
    if problems:
        raise Refused(EXIT_REFUSED, f"{path}: " + "; ".join(problems))
    return {key: str(value) for key, value in pin.items()}


def engine_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _ENGINE_ENV_DROP}


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv only
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )


def origin_slug(workspace: Path) -> str:
    url = _git(workspace, "config", "--get", "remote.origin.url").stdout.strip()
    match = _GITHUB_URL.match(url)
    if match is None:
        raise Refused(EXIT_REFUSED, f"origin {url!r} of {workspace} is not a GitHub repository")
    return match.group("slug")


def cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "l9-release"


def materialize_core(pin: dict[str, str]) -> Path:
    """Return a checkout of Core at exactly the pinned revision (cached, verified)."""
    revision = pin["revision"]
    target = cache_root() / "core" / revision
    module = Path(*pin["engine_module"].split("."))
    if (target / module / "__main__.py").is_file() and _git(
        target, "rev-parse", "HEAD"
    ).stdout.strip() == revision:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f"{revision[:12]}-", dir=target.parent))
    url = f"https://github.com/{pin['repository']}"
    steps = (
        ("init", "--quiet"),
        ("fetch", "--quiet", "--depth", "1", url, revision),
        ("checkout", "--quiet", "--detach", "FETCH_HEAD"),
    )
    for step in steps:
        proc = _git(staging, *step)
        if proc.returncode != 0:
            shutil.rmtree(staging, ignore_errors=True)
            raise Refused(
                EXIT_TRANSPORT,
                f"cannot fetch {pin['repository']}@{revision}: {proc.stderr.strip()}",
            )
    head = _git(staging, "rev-parse", "HEAD").stdout.strip()
    if head != revision or not (staging / module / "__main__.py").is_file():
        shutil.rmtree(staging, ignore_errors=True)
        raise Refused(
            EXIT_REFUSED,
            f"{pin['repository']}@{revision} does not carry {pin['engine_module']}",
        )
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    return target


def run_engine(core: Path, pin: dict[str, str], workspace: Path, slug: str, *stage: str) -> int:
    argv = [
        sys.executable,
        "-m",
        pin["engine_module"],
        "--workspace",
        str(workspace),
        "--repository",
        slug,
        *stage,
    ]
    print(f"l9 release: {pin['repository']}@{pin['revision'][:12]} {' '.join(stage)}", flush=True)
    # cwd=Core puts the engine package on sys.path without exporting PYTHONPATH
    # into the released repository's own phases.
    return subprocess.run(argv, cwd=core, env=engine_env(), check=False).returncode  # noqa: S603


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["gh", *args], text=True, capture_output=True, check=False)  # noqa: S603


def dispatch(pin: dict[str, str], slug: str, *, attempts: int = 10, wait: float = 3.0) -> str:
    """workflow_dispatch Core's release runner for ``slug``; return the run URL."""
    core, workflow, ref = pin["repository"], pin["runner_workflow"], pin["runner_ref"]
    started = datetime.now(UTC) - timedelta(seconds=30)
    proc = _gh(
        "api",
        "--method",
        "POST",
        f"repos/{core}/actions/workflows/{workflow}/dispatches",
        "-f",
        f"ref={ref}",
        "-f",
        f"inputs[repository]={slug}",
    )
    if proc.returncode != 0:
        raise Refused(
            EXIT_TRANSPORT,
            f"dispatch of {core} {workflow} refused: {(proc.stderr or proc.stdout).strip()}",
        )
    listing = f"https://github.com/{core}/actions/workflows/{workflow}"
    for attempt in range(attempts):
        runs = _gh(
            "api",
            "--method",
            "GET",
            f"repos/{core}/actions/workflows/{workflow}/runs",
            "-f",
            "event=workflow_dispatch",
            "-f",
            "per_page=10",
        )
        if runs.returncode == 0:
            for run in _runs(runs.stdout):
                created = _timestamp(str(run.get("created_at", "")))
                if created is not None and created >= started and run.get("head_branch") == ref:
                    return str(run.get("html_url"))
        if attempt + 1 < attempts:
            time.sleep(wait)
    print(f"l9 release: dispatched; the run is not listed yet: {listing}", file=sys.stderr)
    return listing


def _runs(text: str) -> list[dict[str, Any]]:
    try:
        document = json.loads(text or "{}")
    except ValueError:
        return []
    runs = document.get("workflow_runs", []) if isinstance(document, dict) else []
    return [run for run in runs if isinstance(run, dict)]


def _timestamp(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def execute(
    workspace: Path, *, dry_run: bool, dispatch_run: bool, pin_path: Path = PIN_PATH
) -> int:
    if dry_run and dispatch_run:
        raise Refused(EXIT_REFUSED, "DRY_RUN=1 and DISPATCH=1 are exclusive; choose one")
    pin = load_pin(pin_path)
    slug = origin_slug(workspace)
    if dispatch_run:
        url = dispatch(pin, slug)
        print(f"l9 release: dispatched {pin['runner_workflow']} for {slug}: {url}")
        return EXIT_OK
    core = materialize_core(pin)
    code = run_engine(core, pin, workspace, slug, "plan")
    if code != EXIT_OK or not dry_run:
        return code
    commit = _git(workspace, "rev-parse", "HEAD").stdout.strip()
    stage_root = cache_root() / "build" / slug.replace("/", "__") / commit
    if stage_root.exists():
        shutil.rmtree(stage_root)
    out, scratch = stage_root / "dist", stage_root / "scratch"
    scratch.mkdir(parents=True)
    code = run_engine(
        core,
        pin,
        workspace,
        slug,
        "build",
        "--out",
        str(out),
        "--scratch",
        str(scratch),
        "--phases",
        "run",
    )
    if code == EXIT_OK:
        print(f"l9 release: DRY_RUN artifacts in {out} (nothing tagged or published)")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Front door to Core's release engine.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dispatch", action="store_true")
    parser.add_argument("--pin", type=Path, default=PIN_PATH, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        return execute(
            Path(args.workspace).resolve(),
            dry_run=args.dry_run,
            dispatch_run=args.dispatch,
            pin_path=args.pin,
        )
    except Refused as exc:
        print(f"l9 release: {exc}", file=sys.stderr)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
