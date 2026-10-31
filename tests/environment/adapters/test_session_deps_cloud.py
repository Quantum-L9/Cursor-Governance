"""Conformance: dependency provisioning is per-repository and proof-gated.

Two observed defects, one cause. `--workspace` received the multi-repository
container root, so:

  * the fingerprint degenerated to tool versions (no manifest was ever seen),
  * `toolchain_present()` tested `<container>/.venv/bin/python`, which cannot
    exist, so the cache branch was unreachable,
  * the install pass found nothing to install and still reported readiness,
  * and repository environments never received a lock refreshed that session.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HELPER = (
    REPO_ROOT
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "session_deps_cloud.sh"
)


def run(
    workspace: Path,
    home: Path,
    *,
    remote: str = "true",
    budget: str = "20",
    path_prefix: Path | None = None,
    extra_env: dict[str, str] | None = None,
):
    env = {
        **os.environ,
        "HOME": str(home),
        "CLAUDE_CODE_REMOTE": remote,
        "L9_SESSION_DEPS_BUDGET": budget,
        # Not under test here. Left on, every case launched a detached install
        # of the whole CI-parity toolchain (codeql, semgrep, biome, …; ~1.9 GB
        # with its uv cache) into its temporary HOME whenever the caller's
        # environment named a governance checkout — as `make pr` does — and
        # a pytest run filled the session disk (ENOSPC in unrelated tests).
        "L9_CI_PARITY": "0",
    }
    if path_prefix is not None:
        env["PATH"] = f"{path_prefix}{os.pathsep}{env.get('PATH', '')}"
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(HELPER), "--workspace", str(workspace)],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
    )


def make_repo(parent: Path, name: str) -> Path:
    repo = parent / name
    (repo / ".git").mkdir(parents=True)
    return repo


def test_helper_exists_and_parses() -> None:
    assert HELPER.is_file()
    assert subprocess.run(["bash", "-n", str(HELPER)]).returncode == 0


def _hook_checker():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "l9_validate_claude_env_hooks",
        REPO_ROOT / "environment/agents/adapters/claude-code/validate_claude_env.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DRIVEN_HOOK_PREAMBLE = """
types = entry.get("required_git_hook_types") or []
case "$hook_type" in
  pre-push|commit-msg) ;;
esac
"""


def test_validator_accepts_declared_hook_type_and_rejects_bare_install() -> None:
    """The declared form is `pre-commit install --hook-type` for pre-push or commit-msg.

    A bare install and `--hook-type pre-commit` write the commit-stage hook.
    A hook-type install that does not read required_git_hook_types is the same
    blanket install the ban exists to stop.
    """
    checker = _hook_checker()
    declared = _DRIVEN_HOOK_PREAMBLE + 'pre-commit install --hook-type "$hook_type"\n'
    assert checker.git_hook_install_offenders(declared) == []
    assert checker.git_hook_install_offenders(HELPER.read_text(encoding="utf-8")) == []
    for snippet in (
        _DRIVEN_HOOK_PREAMBLE + "pre-commit install\n",
        _DRIVEN_HOOK_PREAMBLE + "pre-commit install --hook-type pre-commit\n",
        'pre-commit install --hook-type "$hook_type"\n',
        _DRIVEN_HOOK_PREAMBLE + "pre-commit install --hook-type post-commit\n",
    ):
        assert checker.git_hook_install_offenders(snippet), snippet


def test_never_installs_a_git_commit_hook() -> None:
    """A raw commit-stage hook runs the catalog without the surface-aware SKIP list.

    The live helper may install a consumer-declared pre-push or commit-msg hook.
    It must not bare-install, and `pre-commit install-hooks` stays the warm-up.
    """
    body = HELPER.read_text(encoding="utf-8")
    assert "pre-commit install-hooks" in body
    assert "required_git_hook_types" in body
    assert _hook_checker().git_hook_install_offenders(body) == []


def test_local_session_is_a_no_op(tmp_path: Path) -> None:
    result = run(tmp_path, tmp_path / "home", remote="false")
    assert result.returncode == 0
    assert "not a cloud session" in result.stdout


def test_absent_workspace_does_not_fail_the_session(tmp_path: Path) -> None:
    result = run(tmp_path / "missing", tmp_path / "home", remote="true")
    assert result.returncode == 0
    assert "does not exist" in result.stdout


def test_container_reports_every_repository_not_one_workspace(tmp_path: Path) -> None:
    """The regression: a container with no manifest at its root reported a single
    'toolchain ready' while four repositories went untouched."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    for name in ("alpha", "beta", "gamma"):
        make_repo(workspace, name)
    result = run(workspace, tmp_path / "home")
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    for name in ("alpha", "beta", "gamma"):
        assert name in combined, combined
    assert "3" in result.stdout


def test_manifestless_repositories_are_vacuously_proven(tmp_path: Path) -> None:
    """Nothing to apply is proven, not degraded — otherwise every docs-only repo
    would make the banner shout forever."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    make_repo(workspace, "docs-only")
    result = run(workspace, tmp_path / "home")
    assert "proven" in result.stdout
    assert "UNPROVEN" not in result.stdout


def test_unapplied_node_lock_is_not_reported_ready(tmp_path: Path) -> None:
    """A package.json with no node_modules must never be claimed as ready.

    This is the shape of the original false positive: readiness asserted from
    the fact that a pass ran rather than from applied state.

    The install must FAIL for that shape to exist, and this test used to get
    that by accident — it assumed npm could not succeed. Where npm is on PATH
    (any container with node installed), `npm install --ignore-scripts` on a
    dependency-free package.json succeeds in milliseconds and creates
    node_modules, so the repository really was applied and "proven" was the
    correct answer. The test failed for a reason that said nothing about the
    contract.

    A failing shim makes the premise real instead of assumed: the install is
    attempted and fails, node_modules stays absent, and readiness must not be
    claimed. That is the original false positive exactly, and it no longer
    depends on what the runner happens to have installed.
    """
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = make_repo(workspace, "webapp")
    (repo / "package.json").write_text('{"name":"webapp","private":true}\n', encoding="utf-8")

    shims = tmp_path / "failing-bin"
    shims.mkdir()
    for tool in ("npm", "pnpm"):
        shim = shims / tool
        shim.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
        shim.chmod(0o755)

    home = tmp_path / "home"
    result = run(workspace, home, budget="1", path_prefix=shims)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert (
        "UNPROVEN" in combined or "continues in background" in combined or "INCOMPLETE" in combined
    )
    stamps = list((home / ".l9" / "claude").glob("deps-*.stamp"))
    assert stamps == [], "a stamp must never be written for an unproven toolchain"


def test_single_repository_workspace_keeps_its_own_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "solo")
    result = run(repo, tmp_path / "home")
    assert result.returncode == 0
    assert "1" in result.stdout


@pytest.mark.parametrize("budget", ["1", "20"])
def test_always_exits_zero_and_never_blocks(tmp_path: Path, budget: str) -> None:
    workspace = tmp_path / "container"
    workspace.mkdir()
    make_repo(workspace, "alpha")
    assert run(workspace, tmp_path / "home", budget=budget).returncode == 0


def test_stamp_writer_records_exit_and_interpreter() -> None:
    body = HELPER.read_text(encoding="utf-8")
    assert "write_deps_stamp()" in body
    assert "import_smoke()" in body
    assert 'echo "exit=$rc"' in body
    assert "import json,sys" in body
    assert "import json,sys,yaml" not in body


def test_proof_does_not_collapse_outdated_into_the_plain_resolution() -> None:
    """`uv sync --check` exit 1 (outdated) must never fall through to a narrower
    resolution that could pass. Only exit 2 (extra undefined) may fall through."""
    body = HELPER.read_text(encoding="utf-8")
    assert 'rc" -eq 2' in body
    assert 'rc" -ne 0' in body


def test_unapplied_pip_manifest_is_not_reported_ready(tmp_path: Path) -> None:
    """pyproject.toml / requirements.txt without uv.lock must not stamp ready
    when .venv is absent — pip install in install_repo is best-effort."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = make_repo(workspace, "pip-only")
    (repo / "pyproject.toml").write_text("[project]\nname='pip-only'\n", encoding="utf-8")
    home = tmp_path / "home"
    result = run(workspace, home, budget="1")
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert (
        "UNPROVEN" in combined or "continues in background" in combined or "INCOMPLETE" in combined
    )
    stamps = list((home / ".l9" / "claude").glob("deps-*.stamp"))
    assert stamps == [], "a stamp must never be written for an unproven pip toolchain"


def test_a_governance_checkout_syncs_through_its_locked_writer(tmp_path: Path) -> None:
    """A raw `uv sync` bypassed the environment lock readers wait on.

    A governance checkout's .venv has one writer, ensure_uv_environment.sh,
    which holds .l9/uv-environment.lock for the whole install; a second writer
    replacing packages beside it is how a memory runtime imported a
    half-installed package (2026-09-24).
    """
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = make_repo(workspace, "governance")
    (repo / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname="g"\n', encoding="utf-8")
    calls = tmp_path / "calls.log"
    ensure = repo / "ops" / "scripts" / "ensure_uv_environment.sh"
    ensure.parent.mkdir(parents=True)
    ensure.write_text(f'#!/usr/bin/env bash\necho "ensure $*" >> "{calls}"\n', encoding="utf-8")
    shims = tmp_path / "bin"
    shims.mkdir()
    (shims / "uv").write_text(
        f'#!/usr/bin/env bash\necho "uv $*" >> "{calls}"\n'
        '[ "${1:-}" = "--version" ] && echo "uv 9.9.9"\nexit 0\n',
        encoding="utf-8",
    )
    (shims / "uv").chmod(0o755)
    result = run(workspace, tmp_path / "home", budget="20", path_prefix=shims)
    assert result.returncode == 0
    lines = calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []
    assert f"ensure {repo} apply" in lines, lines
    assert not [line for line in lines if line.startswith("uv sync --locked --extra dev")], lines


def _governance_checkout(workspace: Path, calls: Path, check_rc: int) -> Path:
    """A governance-shaped repo whose venv owner answers `check` with check_rc."""
    repo = make_repo(workspace, "governance")
    (repo / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname="g"\n', encoding="utf-8")
    venv_bin = repo / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").symlink_to(Path(os.environ.get("PYTHON", "/usr/bin/python3")))
    ensure = repo / "ops" / "scripts" / "ensure_uv_environment.sh"
    ensure.parent.mkdir(parents=True)
    ensure.write_text(
        f'#!/usr/bin/env bash\necho "ensure $*" >> "{calls}"\n'
        f'[ "${{2:-}}" = "check" ] && exit {check_rc}\nexit 0\n',
        encoding="utf-8",
    )
    return repo


def _uv_shim_reporting_outdated(shims: Path, calls: Path) -> None:
    """`uv sync --check` exits 1, as it does for a sealed governance venv."""
    shims.mkdir()
    (shims / "uv").write_text(
        f'#!/usr/bin/env bash\necho "uv $*" >> "{calls}"\n'
        '[ "${1:-}" = "--version" ] && { echo "uv 9.9.9"; exit 0; }\n'
        'case " $* " in *" --check "*) exit 1 ;; esac\nexit 0\n',
        encoding="utf-8",
    )
    (shims / "uv").chmod(0o755)


def test_a_governance_checkout_is_proven_by_its_venv_owner(tmp_path: Path) -> None:
    """The memory seal makes a raw `uv sync --check` report a governance venv
    outdated forever. Proof must come from ensure_uv_environment.sh `check`,
    the same owner install_repo applies through, or no stamp is ever written."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    calls = tmp_path / "calls.log"
    repo = _governance_checkout(workspace, calls, check_rc=0)
    shims = tmp_path / "bin"
    _uv_shim_reporting_outdated(shims, calls)
    home = tmp_path / "home"
    result = run(workspace, home, budget="20", path_prefix=shims)
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "UNPROVEN" not in combined, combined
    lines = calls.read_text(encoding="utf-8").splitlines()
    assert f"ensure {repo} check" in lines, lines
    assert not [line for line in lines if line.startswith("uv sync --locked --extra dev --check")]
    assert list((home / ".l9" / "claude").glob("deps-*.stamp")), "proven checkout must stamp"


def test_a_governance_checkout_its_owner_rejects_is_never_stamped(tmp_path: Path) -> None:
    """Negative control: when the owner says the venv is not applied, the
    checkout stays unproven and no stamp is written."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    calls = tmp_path / "calls.log"
    _governance_checkout(workspace, calls, check_rc=1)
    shims = tmp_path / "bin"
    _uv_shim_reporting_outdated(shims, calls)
    home = tmp_path / "home"
    result = run(workspace, home, budget="20", path_prefix=shims)
    assert result.returncode == 0
    assert "UNPROVEN" in result.stdout + result.stderr
    assert list((home / ".l9" / "claude").glob("deps-*.stamp")) == []


needs_uv = pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="uv is the pip-repo provisioner; this case needs it installed",
)


def _pip_repo(workspace: Path, requirements: str) -> Path:
    repo = make_repo(workspace, "pip-only")
    (repo / "requirements.txt").write_text(requirements, encoding="utf-8")
    (repo / "requirements-dev.txt").write_text("# dev pins\n", encoding="utf-8")
    return repo


def _stamps(home: Path) -> set[str]:
    return {p.name for p in (home / ".l9" / "claude").glob("deps-*.stamp")}


@needs_uv
def test_a_pip_repository_gets_its_own_venv_and_a_stamp(tmp_path: Path) -> None:
    """CG-04: pip installed into the system interpreter while the proof demanded
    <repo>/.venv, so a pip repository could never be proven. It now gets an
    isolated .venv, and the stamp follows a complete install."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "# no third-party pins\n")
    home = tmp_path / "home"
    result = run(workspace, home, budget="120", extra_env={"UV_OFFLINE": "1"})
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "UNPROVEN" not in combined, combined
    assert (repo / ".venv" / "bin" / "python").exists()
    assert (repo / ".venv" / ".l9-pip-applied").is_file()
    assert _stamps(home)


@needs_uv
def test_a_changed_dev_pin_set_invalidates_the_stamp(tmp_path: Path) -> None:
    """requirements-dev.txt was not fingerprinted, so a dev pin bump kept a
    stale stamp. A changed split pin set must re-provision."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "# no third-party pins\n")
    home = tmp_path / "home"
    run(workspace, home, budget="120", extra_env={"UV_OFFLINE": "1"})
    first = _stamps(home)
    assert first
    cached = run(workspace, home, budget="120", extra_env={"UV_OFFLINE": "1"})
    assert "cached and proven" in cached.stdout, cached.stdout + cached.stderr
    (repo / "requirements-dev.txt").write_text("# dev pins, bumped\n", encoding="utf-8")
    again = run(workspace, home, budget="120", extra_env={"UV_OFFLINE": "1"})
    assert "cached and proven" not in again.stdout, again.stdout
    assert _stamps(home) - first, "a changed pin set must produce a new fingerprint"


@needs_uv
def test_a_failed_pip_install_is_never_stamped(tmp_path: Path) -> None:
    """A venv created and then left half-installed must not read as proven."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "no-such-package-l9-test==1.0\n")
    home = tmp_path / "home"
    result = run(workspace, home, budget="120", extra_env={"UV_OFFLINE": "1"})
    assert "UNPROVEN" in result.stdout + result.stderr
    assert not (repo / ".venv" / ".l9-pip-applied").exists()
    assert _stamps(home) == set()


def _uv_provision_shim(shims: Path, calls: Path, *, fail_dev_extra: bool) -> None:
    """A uv that records its cwd and arguments, builds a usable .venv, and
    optionally refuses the `.[dev]` extra the way a failed resolve would."""
    shims.mkdir()
    fail = 'case "$*" in *".[dev]"*) exit 1 ;; esac\n' if fail_dev_extra else ""
    (shims / "uv").write_text(
        f'#!/usr/bin/env bash\necho "uv cwd=$PWD $*" >> "{calls}"\n'
        '[ "${1:-}" = "--version" ] && { echo "uv 9.9.9"; exit 0; }\n'
        'if [ "${1:-}" = "venv" ]; then mkdir -p "$2/bin" && '
        'ln -sf "$(command -v python3)" "$2/bin/python"; exit 0; fi\n'
        f"{fail}exit 0\n",
        encoding="utf-8",
    )
    (shims / "uv").chmod(0o755)


def test_pip_provisioning_runs_from_the_repository_not_the_caller(tmp_path: Path) -> None:
    """uv discovers project and uv.toml settings from its cwd. Run from the
    caller's directory, a sibling's configuration decided this install."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "# no third-party pins\n")
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=False)
    result = run(workspace, tmp_path / "home", budget="60", path_prefix=tmp_path / "bin")
    assert result.returncode == 0, result.stdout + result.stderr
    provisioning = [
        line for line in calls.read_text(encoding="utf-8").splitlines() if " venv " in line
    ]
    assert provisioning, calls.read_text(encoding="utf-8")
    assert all(line.startswith(f"uv cwd={repo} ") for line in provisioning), provisioning


def test_a_failed_declared_dev_extra_is_not_downgraded_to_ready(tmp_path: Path) -> None:
    """Retrying without a declared `dev` extra once succeeded with the test and
    lint pins absent and stamped the repository proven."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = make_repo(workspace, "pip-only")
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "p"\nversion = "0"\n[project.optional-dependencies]\ndev = ["pytest"]\n',
        encoding="utf-8",
    )
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=True)
    home = tmp_path / "home"
    result = run(workspace, home, budget="60", path_prefix=tmp_path / "bin")
    assert "UNPROVEN" in result.stdout + result.stderr
    assert _stamps(home) == set()
    log = calls.read_text(encoding="utf-8")
    assert ".[dev]" in log
    assert not [line for line in log.splitlines() if line.endswith(" -e .")], log


def test_a_project_without_a_dev_extra_installs_itself(tmp_path: Path) -> None:
    """Positive control: no declared extra means a plain editable install."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = make_repo(workspace, "pip-only")
    (repo / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "0"\n', encoding="utf-8")
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=True)
    home = tmp_path / "home"
    result = run(workspace, home, budget="60", path_prefix=tmp_path / "bin")
    assert "UNPROVEN" not in result.stdout + result.stderr, result.stdout + result.stderr
    assert [
        line for line in calls.read_text(encoding="utf-8").splitlines() if line.endswith(" -e .")
    ]
    assert _stamps(home)


# --- A venv this helper did not build is the owner's -------------------------
#
# The helper reused any existing .venv and installed every requirements*.txt on
# top of it. An agent-built worktree venv (`pip install -e .[dev]`) received a
# requirements-ci.txt overlay with stale type stubs, and installs only add, so
# the stubs outlived their removal from the pin set (EIE PR #259 governance
# handoff). Its own header says it must never mutate a developer checkout's
# toolchain as a session side effect.


def _foreign_venv(repo: Path) -> None:
    bin_dir = repo / ".venv" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "python").symlink_to(shutil.which("python3") or "/usr/bin/python3")


def _installs(calls: Path) -> list[str]:
    if not calls.exists():
        return []
    return [line for line in calls.read_text(encoding="utf-8").splitlines() if " install " in line]


def test_an_existing_venv_the_helper_did_not_build_is_left_alone(tmp_path: Path) -> None:
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "types-redis==4.6.0.20241004\n")
    _foreign_venv(repo)
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=False)
    result = run(workspace, tmp_path / "home", budget="60", path_prefix=tmp_path / "bin")
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert _installs(calls) == [], calls.read_text(encoding="utf-8")
    assert not (repo / ".venv" / ".l9-pip-applied").exists()
    assert not (repo / ".venv" / ".l9-pip-owner").exists()
    assert "UNPROVEN" not in combined, combined


def test_an_owner_managed_venv_is_not_reprovisioned_next_session(tmp_path: Path) -> None:
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "# no third-party pins\n")
    _foreign_venv(repo)
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=False)
    home = tmp_path / "home"
    run(workspace, home, budget="60", path_prefix=tmp_path / "bin")
    again = run(workspace, home, budget="60", path_prefix=tmp_path / "bin")
    assert "cached and proven" in again.stdout, again.stdout + again.stderr
    assert _installs(calls) == []


def test_a_venv_the_helper_builds_is_marked_as_its_own(tmp_path: Path) -> None:
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "# no third-party pins\n")
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=False)
    result = run(workspace, tmp_path / "home", budget="60", path_prefix=tmp_path / "bin")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".venv" / ".l9-pip-owner").is_file()
    assert _installs(calls), "a venv the helper built is still provisioned"


def test_a_venv_an_earlier_helper_run_provisioned_is_still_maintained(tmp_path: Path) -> None:
    """Adoption: venvs built before the owner marker existed carry the applied marker."""
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = _pip_repo(workspace, "# no third-party pins\n")
    _foreign_venv(repo)
    (repo / ".venv" / ".l9-pip-applied").write_text("stale-fingerprint\n", encoding="utf-8")
    calls = tmp_path / "calls.log"
    _uv_provision_shim(tmp_path / "bin", calls, fail_dev_extra=False)
    result = run(workspace, tmp_path / "home", budget="60", path_prefix=tmp_path / "bin")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _installs(calls), calls.read_text(encoding="utf-8") if calls.exists() else "no calls"
    assert (repo / ".venv" / ".l9-pip-owner").is_file()


# The exact lines IB-Odoo_19 scripts/git_push_with_pr.sh require_pre_push_enforcement greps for.
_PRE_PUSH_HOOK_LINES = (
    "# File generated by pre-commit: https://pre-commit.com",
    "ARGS=(hook-impl --config=.pre-commit-config.yaml --hook-type=pre-push)",
)
_ODOO_ORIGIN = "https://github.com/cryptoxdog/IB-Odoo_19.git"
_GIT_ISOLATION = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}

_VENV_PRE_COMMIT = REPO_ROOT / ".venv" / "bin" / "pre-commit"
needs_pre_commit = pytest.mark.skipif(
    not _VENV_PRE_COMMIT.is_file(),
    reason="the fixture must run the locked pre-commit hook installer",
)


def _precommit_path(parent: Path) -> Path:
    """The isolated HOME hides user-site pre-commit. The venv binary does not."""
    bindir = parent / "pre-commit-bin"
    bindir.mkdir()
    (bindir / "pre-commit").symlink_to(_VENV_PRE_COMMIT)
    return bindir


def _hook_repo(parent: Path, name: str, origin: str) -> Path:
    repo = parent / name
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(repo)],
        check=True,
        env={**os.environ, **_GIT_ISOLATION},
    )
    subprocess.run(
        ["git", "-C", str(repo), "remote", "add", "origin", origin],
        check=True,
        env={**os.environ, **_GIT_ISOLATION},
    )
    (repo / ".pre-commit-config.yaml").write_text(
        "repos:\n"
        "- repo: local\n"
        "  hooks:\n"
        "  - id: noop\n"
        "    name: noop\n"
        "    entry: 'true'\n"
        "    language: system\n"
        "    pass_filenames: false\n",
        encoding="utf-8",
    )
    return repo


@needs_pre_commit
def test_declared_repo_gets_executable_pre_push_hook_and_no_commit_hook(tmp_path: Path) -> None:
    """A fresh clone has no hooks. The bootstrap installs the declared pre-push hook only."""
    repo = _hook_repo(tmp_path, "IB-Odoo_19", _ODOO_ORIGIN)
    result = run(
        repo,
        tmp_path / "home",
        budget="60",
        path_prefix=_precommit_path(tmp_path),
        extra_env=_GIT_ISOLATION,
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    hook = repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file(), combined
    assert os.access(hook, os.X_OK)
    lines = hook.read_text(encoding="utf-8").splitlines()
    for expected in _PRE_PUSH_HOOK_LINES:
        assert expected in lines, lines
    assert not (repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (repo / ".git" / "hooks" / "commit-msg").exists()


@needs_pre_commit
def test_undeclared_repo_gets_no_git_hook(tmp_path: Path) -> None:
    repo = _hook_repo(tmp_path, "other", "https://github.com/example/not-declared.git")
    result = run(
        repo,
        tmp_path / "home",
        budget="60",
        path_prefix=_precommit_path(tmp_path),
        extra_env=_GIT_ISOLATION,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    hooks = repo / ".git" / "hooks"
    assert not (hooks / "pre-push").exists()
    assert not (hooks / "pre-commit").exists()


def test_failed_install_hooks_does_not_install_a_hook(tmp_path: Path) -> None:
    """The declared install runs only after install-hooks succeeds."""
    repo = _hook_repo(tmp_path, "IB-Odoo_19", _ODOO_ORIGIN)
    calls = tmp_path / "calls.log"
    shims = tmp_path / "bin"
    shims.mkdir()
    shim = shims / "pre-commit"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$*" >> "{calls}"\n'
        '[ "${1:-}" = "install-hooks" ] && exit 1\n'
        "mkdir -p .git/hooks\n"
        "printf broken > .git/hooks/pre-push\n"
        "exit 0\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    result = run(repo, tmp_path / "home", budget="60", path_prefix=shims, extra_env=_GIT_ISOLATION)
    assert result.returncode == 0, result.stdout + result.stderr
    log = calls.read_text(encoding="utf-8") if calls.exists() else ""
    assert "install-hooks" in log, log
    assert "install --hook-type" not in log, log
    assert not (repo / ".git" / "hooks" / "pre-push").exists()


@needs_pre_commit
def test_cached_dependency_stamp_still_installs_missing_declared_hook(tmp_path: Path) -> None:
    """A proven dependency stamp must not skip a missing declared pre-push hook.

    The stamp is written even when hook install failed, and stamps from before
    required_git_hook_types existed never enter install_repo again. The next
    cached SessionStart reconciles the hook without a toolchain reinstall.
    """
    repo = _hook_repo(tmp_path, "IB-Odoo_19", _ODOO_ORIGIN)
    home = tmp_path / "home"
    precommit_bin = _precommit_path(tmp_path)
    first = run(
        repo,
        home,
        budget="60",
        path_prefix=precommit_bin,
        extra_env=_GIT_ISOLATION,
    )
    assert first.returncode == 0, first.stdout + first.stderr
    hook = repo / ".git" / "hooks" / "pre-push"
    assert hook.is_file(), first.stdout + first.stderr
    assert _stamps(home)
    hook.unlink()
    second = run(
        repo,
        home,
        budget="60",
        path_prefix=precommit_bin,
        extra_env=_GIT_ISOLATION,
    )
    combined = second.stdout + second.stderr
    assert second.returncode == 0, combined
    assert "cached and proven" in second.stdout, combined
    assert "installing toolchain" not in combined, combined
    assert "reconciling" in second.stderr, combined
    assert hook.is_file(), combined
    assert os.access(hook, os.X_OK)
    lines = hook.read_text(encoding="utf-8").splitlines()
    for expected in _PRE_PUSH_HOOK_LINES:
        assert expected in lines, lines
    assert not (repo / ".git" / "hooks" / "pre-commit").exists()
    assert not (repo / ".git" / "hooks" / "commit-msg").exists()
