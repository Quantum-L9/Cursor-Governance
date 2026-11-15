"""``make release`` front door: pin, Core resolution, engine invocation, dispatch.

Core is a local repository served at its GitHub URL through ``url.insteadOf``
in an isolated global git config; its ``tools.l9_release`` is a stand-in that
records the argv, cwd and environment it was run with, so these tests prove the
front door's contract without copying or re-testing Core's engine. ``gh`` is
stubbed at the transport boundary for dispatch.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))

import l9_release  # noqa: E402

CORE_SLUG = "Quantum-L9/l9-ci-core"
FACTORY_SLUG = "Quantum-L9/l9-repo-template"
CONSUMER_URL = "https://github.com/acme/widget"

FAKE_ENGINE = textwrap.dedent(
    """\
    import json, os, sys
    from pathlib import Path
    record = Path(os.environ["FAKE_ENGINE_LOG"])
    with record.open("a") as stream:
        stream.write(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd(),
                                 "env": dict(os.environ)}) + "\\n")
    stage = next(a for a in sys.argv[1:] if a in ("plan", "build", "publish", "verify"))
    sys.exit(int(os.environ.get(f"FAKE_ENGINE_EXIT_{stage.upper()}", "0")))
    """
)

FAKE_GH = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys
    from pathlib import Path
    state = Path(os.environ["FAKE_GH_STATE"])
    args = sys.argv[1:]
    with (state / "calls.log").open("a") as stream:
        stream.write(json.dumps(args) + "\\n")
    if os.environ.get("FAKE_GH_DENY"):
        print("HTTP 403: Resource not accessible", file=sys.stderr)
        sys.exit(1)
    if "POST" in args and args[3].endswith("/dispatches"):
        sys.exit(0)
    if "GET" in args and args[3].endswith("/runs"):
        print(json.dumps({{"workflow_runs": [
            {{"html_url": "https://github.com/x/old", "created_at": "2020-01-01T00:00:00Z",
              "head_branch": "main"}},
            {{"html_url": "https://github.com/{core}/actions/runs/42",
              "created_at": os.environ["FAKE_GH_NOW"], "head_branch": "main"}},
        ]}}))
        sys.exit(0)
    sys.exit(2)
    """
)


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    core = tmp_path / "core"
    (core / "tools" / "l9_release").mkdir(parents=True)
    (core / "tools" / "l9_release" / "__init__.py").write_text("")
    (core / "tools" / "l9_release" / "__main__.py").write_text(FAKE_ENGINE)
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text(
        "[user]\n\tname = T\n\temail = t@example.invalid\n"
        f'[url "{core}"]\n\tinsteadOf = https://github.com/{CORE_SLUG}\n'
        "[init]\n\tdefaultBranch = main\n[commit]\n\tgpgSign = false\n"
        "[uploadpack]\n\tallowAnySHA1InWant = true\n"
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _git(core, "init", "-q")
    _git(core, "add", "-A")
    _git(core, "commit", "-q", "-m", "core")
    revision = _git(core, "rev-parse", "HEAD")

    pin = tmp_path / "release-core.json"
    pin.write_text(
        json.dumps(
            {
                "schema": "l9.release-core-pin/v1",
                "repository": CORE_SLUG,
                "revision": revision,
                "engine_module": "tools.l9_release",
                "runner_repository": FACTORY_SLUG,
                "runner_workflow": "release-schedule.yml",
                "runner_ref": "main",
                "runner_input": "repo",
            }
        )
    )
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _git(workspace, "init", "-q")
    _git(workspace, "remote", "add", "origin", CONSUMER_URL)
    (workspace / "README.md").write_text("x\n")
    _git(workspace, "add", "-A")
    _git(workspace, "commit", "-q", "-m", "init")

    state = tmp_path / "gh-state"
    state.mkdir()
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "gh").write_text(FAKE_GH.format(python=sys.executable, core=FACTORY_SLUG))
    (bindir / "gh").chmod(0o755)
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_GH_STATE", str(state))
    monkeypatch.setenv("FAKE_GH_NOW", datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    monkeypatch.setenv("FAKE_ENGINE_LOG", str(tmp_path / "engine.log"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    return {
        "core": core,
        "pin": pin,
        "workspace": workspace,
        "state": state,
        "log": tmp_path / "engine.log",
        "cache": tmp_path / "cache",
        "revision": Path(revision),
    }


def _engine_calls(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def _run(env: dict[str, Path], *flags: str) -> int:
    return l9_release.main(["--workspace", str(env["workspace"]), "--pin", str(env["pin"]), *flags])


# ---------------------------------------------------------------------------
# Pin
# ---------------------------------------------------------------------------
def test_shipped_pin_names_a_core_commit() -> None:
    pin = l9_release.load_pin()
    assert pin["repository"] == CORE_SLUG
    assert len(pin["revision"]) == 40
    assert pin["engine_module"] == "tools.l9_release"
    # DISPATCH=1 goes to the factory caller, never to Core (workflow_call only).
    assert pin["runner_repository"] == FACTORY_SLUG
    assert pin["runner_workflow"] == "release-schedule.yml"
    assert pin["runner_input"] == "repo"
    assert pin["runner_ref"] == "main"


def test_pin_without_a_runner_repository_is_refused(tmp_path: Path) -> None:
    pin = json.loads(l9_release.PIN_PATH.read_text(encoding="utf-8"))
    del pin["runner_repository"]
    bad = tmp_path / "pin.json"
    bad.write_text(json.dumps(pin))
    with pytest.raises(l9_release.Refused, match="runner_repository"):
        l9_release.load_pin(bad)


def test_malformed_pin_is_refused(tmp_path: Path) -> None:
    bad = tmp_path / "pin.json"
    bad.write_text(json.dumps({"schema": "l9.release-core-pin/v1", "revision": "main"}))
    with pytest.raises(l9_release.Refused, match="40-hex"):
        l9_release.load_pin(bad)


# ---------------------------------------------------------------------------
# Engine invocation
# ---------------------------------------------------------------------------
def test_default_runs_only_the_read_only_plan(env: dict[str, Path]) -> None:
    assert _run(env) == 0
    calls = _engine_calls(env["log"])
    assert len(calls) == 1
    argv = calls[0]["argv"]
    assert argv[-1] == "plan"
    assert argv[argv.index("--repository") + 1] == "acme/widget"
    assert argv[argv.index("--workspace") + 1] == str(env["workspace"])


def test_dry_run_plans_then_builds_from_the_pinned_core(
    env: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    for leaked in ("MAKEFLAGS", "PYTHON", "UV_PROJECT", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH"):
        monkeypatch.setenv(leaked, "/governance")
    assert _run(env, "--dry-run") == 0
    plan, build = _engine_calls(env["log"])
    assert plan["argv"][-1] == "plan"
    stage = build["argv"][build["argv"].index("build") :]
    assert stage[stage.index("--phases") + 1] == "run"
    assert Path(stage[stage.index("--out") + 1]).parent.parent.parent == (
        env["cache"] / "l9-release" / "build"
    )
    core = env["cache"] / "l9-release" / "core" / str(env["revision"])
    assert Path(build["cwd"]) == core
    assert _git(core, "rev-parse", "HEAD") == str(env["revision"])
    for leaked in ("MAKEFLAGS", "PYTHON", "UV_PROJECT", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH"):
        assert leaked not in build["env"], leaked


def test_failed_plan_stops_before_build(env: dict[str, Path], monkeypatch) -> None:
    monkeypatch.setenv("FAKE_ENGINE_EXIT_PLAN", "1")
    assert _run(env, "--dry-run") == 1
    assert [c["argv"][-1] for c in _engine_calls(env["log"])] == ["plan"]


def test_engine_exit_code_is_propagated(env: dict[str, Path], monkeypatch) -> None:
    monkeypatch.setenv("FAKE_ENGINE_EXIT_BUILD", "2")
    assert _run(env, "--dry-run") == 2


def test_the_front_door_never_publishes(env: dict[str, Path]) -> None:
    _run(env, "--dry-run")
    stages = {c["argv"][c["argv"].index("--repository") + 2] for c in _engine_calls(env["log"])}
    assert stages == {"plan", "build"}
    source = (ROOT / "ops" / "scripts" / "l9_release.py").read_text()
    assert '"publish"' not in source and '"tag"' not in source


def test_core_cache_is_reused(env: dict[str, Path]) -> None:
    assert _run(env) == 0
    marker = env["cache"] / "l9-release" / "core" / str(env["revision"]) / "marker"
    marker.write_text("kept")
    assert _run(env) == 0
    assert marker.read_text() == "kept"


def test_core_revision_without_the_engine_is_refused(env: dict[str, Path]) -> None:
    core = env["core"]
    _git(core, "rm", "-q", "-r", "tools")
    _git(core, "commit", "-q", "-m", "drop engine")
    pin = json.loads(env["pin"].read_text())
    pin["revision"] = _git(core, "rev-parse", "HEAD")
    env["pin"].write_text(json.dumps(pin))
    assert _run(env) == l9_release.EXIT_REFUSED
    assert not _engine_calls(env["log"])


def test_unfetchable_core_is_a_transport_failure(env: dict[str, Path]) -> None:
    pin = json.loads(env["pin"].read_text())
    pin["revision"] = "0" * 40
    env["pin"].write_text(json.dumps(pin))
    assert _run(env) == l9_release.EXIT_TRANSPORT


def test_non_github_origin_is_refused(env: dict[str, Path]) -> None:
    _git(env["workspace"], "remote", "set-url", "origin", "/srv/repo.git")
    assert _run(env) == l9_release.EXIT_REFUSED


def test_dry_run_and_dispatch_are_exclusive(env: dict[str, Path]) -> None:
    assert _run(env, "--dry-run", "--dispatch") == l9_release.EXIT_REFUSED
    assert not _engine_calls(env["log"])


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def test_dispatch_triggers_the_factory_release_schedule(env: dict[str, Path], capsys) -> None:
    assert _run(env, "--dispatch") == 0
    calls = [json.loads(line) for line in (env["state"] / "calls.log").read_text().splitlines()]
    post = calls[0]
    assert post[:4] == [
        "api",
        "--method",
        "POST",
        f"repos/{FACTORY_SLUG}/actions/workflows/release-schedule.yml/dispatches",
    ]
    assert "ref=main" in post and "inputs[repo]=acme/widget" in post
    assert not any(CORE_SLUG in arg for call in calls for arg in call), "never Core directly"
    assert f"https://github.com/{FACTORY_SLUG}/actions/runs/42" in capsys.readouterr().out
    assert not _engine_calls(env["log"]), "dispatch runs no local engine stage"


def test_dispatch_refusal_is_reported(env: dict[str, Path], monkeypatch) -> None:
    monkeypatch.setenv("FAKE_GH_DENY", "1")
    assert _run(env, "--dispatch") == l9_release.EXIT_TRANSPORT


# ---------------------------------------------------------------------------
# Make wiring
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("args", "flags"),
    [((), []), (("DRY_RUN=1",), ["--dry-run"]), (("DISPATCH=1",), ["--dispatch"])],
)
def test_make_target_routes_to_the_front_door(args: tuple[str, ...], flags: list[str]) -> None:
    dry = subprocess.run(
        ["make", "--no-print-directory", "-n", "release", "WS=/r", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    line = " ".join(dry.replace("\\\n", " ").split())
    assert 'ops/scripts/l9_release.py --workspace "/r"' in line
    for flag in ("--dry-run", "--dispatch"):
        assert (flag in line) == (flag in flags)


def test_release_is_consumer_safe() -> None:
    safe = subprocess.run(
        ["make", "--no-print-directory", "l9-consumer-safe-list"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert "release" in safe
