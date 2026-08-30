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
import re
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


def run(workspace: Path, home: Path, *, remote: str = "true", budget: str = "20"):
    env = {
        **os.environ,
        "HOME": str(home),
        "CLAUDE_CODE_REMOTE": remote,
        "L9_SESSION_DEPS_BUDGET": budget,
    }
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


def test_never_installs_a_git_commit_hook() -> None:
    """A raw hook runs the catalog without the surface-aware SKIP list.

    The assertion is over INVOCATIONS, not over the file text: the phrase
    `pre-commit install` legitimately appears in a comment forbidding it and in
    a warning message about a failed package install, and matching those would
    make this test fail on correct code.
    """
    body = HELPER.read_text(encoding="utf-8")
    assert "pre-commit install-hooks" in body

    invocation = re.compile(r"(?<![\w-])pre-commit\s+install(?!-hooks)")
    quoted = re.compile(r"\"[^\"]*\"|'[^']*'")
    offenders = []
    for number, line in enumerate(body.splitlines(), start=1):
        # Strip comments AND quoted strings: a message that merely mentions the
        # command is prose, not an invocation.
        code = quoted.sub("", line.split("#", 1)[0])
        if invocation.search(code):
            offenders.append(f"{number}: {line.strip()}")
    assert not offenders, "raw `pre-commit install` invocation:\n" + "\n".join(offenders)


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
    """
    workspace = tmp_path / "container"
    workspace.mkdir()
    repo = make_repo(workspace, "webapp")
    (repo / "package.json").write_text('{"name":"webapp","private":true}\n', encoding="utf-8")
    home = tmp_path / "home"
    result = run(workspace, home, budget="1")
    assert result.returncode == 0
    combined = result.stdout + result.stderr
    assert "UNPROVEN" in combined or "continues in background" in combined
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
    assert "import json,sys,yaml" in body


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
    assert "UNPROVEN" in combined or "continues in background" in combined
    stamps = list((home / ".l9" / "claude").glob("deps-*.stamp"))
    assert stamps == [], "a stamp must never be written for an unproven pip toolchain"
