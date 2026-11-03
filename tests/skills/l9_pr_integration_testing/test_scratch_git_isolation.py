"""Scratch repositories carry no hooks, without a verification-bypass flag.

integrate.py used to disable hooks on every git call with a hook-path override,
which the commit-verification contract rejects as an emitted bypass. The
guarantee it stood for is kept by construction instead: the object store and
every case clone are created with an empty template, so no hooks directory
exists, and git_env() drops global and system config, so no inherited setting
can redirect hooks. These tests hold that guarantee against a hostile
GIT_TEMPLATE_DIR; ops/scripts/validate_commit_verification_contract.py keeps the
override itself out.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/l9-pr-integration-testing/scripts"
sys.path.insert(0, str(SCRIPTS))

import integrate  # noqa: E402


@pytest.fixture
def hostile_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A template whose hook would run on any ref update if it were installed."""
    template = tmp_path / "template"
    hook = template / "hooks" / "reference-transaction"
    hook.parent.mkdir(parents=True)
    marker = tmp_path / "hook-ran"
    hook.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    hook.chmod(0o755)
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(template))
    return marker


def test_scratch_store_has_no_hooks_directory(tmp_path: Path, hostile_template: Path) -> None:
    store = tmp_path / "objects.git"
    integrate.scratch_init(store)
    assert store.is_dir()
    assert not (store / "hooks").exists()


def test_scratch_clone_has_no_hooks_and_runs_none(tmp_path: Path, hostile_template: Path) -> None:
    store = tmp_path / "objects.git"
    integrate.scratch_init(store)
    clone = tmp_path / "case"
    integrate.scratch_clone(store, clone)
    assert not (clone / ".git" / "hooks").exists()
    # A commit updates a ref, which fires reference-transaction when that hook
    # is installed. The commit must succeed, or the assertion below proves nothing.
    integrate.git(
        [
            "-C",
            str(clone),
            "-c",
            "user.name=L9 Test",
            "-c",
            "user.email=integration@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "probe",
        ]
    )
    assert not hostile_template.exists(), "a hook from GIT_TEMPLATE_DIR ran in a scratch repo"


def test_git_env_drops_inherited_git_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_CONFIG_PARAMETERS", "'user.name'='inherited'")
    env = integrate.git_env()
    assert "GIT_CONFIG_PARAMETERS" not in env
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_CONFIG_GLOBAL"] == integrate.os.devnull
