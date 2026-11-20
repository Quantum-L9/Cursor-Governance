"""SessionStart hydrates exactly the repositories bootstrap reports in scope.

``memory_prefetch._hydration_selection`` and the bootstrap readiness report
(``namespace_context.resolve_workspace_namespaces``) share one selection. A
second checkout of one repository (a linked worktree beside its clone) must not
take a hydration slot under the cap: if it did, a distinct repository would be
dropped from hydration while bootstrap still reported it in scope.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

CLAUDE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = CLAUDE_DIR.parents[3]
for _p in (str(CLAUDE_DIR / "memory"), str(CLAUDE_DIR / "hooks"), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ops.memory import namespace_context as nc  # noqa: E402


def _prefetch():
    spec = importlib.util.spec_from_file_location(
        "memory_prefetch_under_test", CLAUDE_DIR / "hooks" / "memory_prefetch.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _git(*args: str, cwd: Path | None = None) -> None:
    env = {**os.environ, "L9_WORKTREE_ADD_AUTHORIZED": "test fixture"}
    subprocess.run(["git", *args], cwd=cwd, check=True, env=env, capture_output=True)


def _repo(path: Path, remote: str) -> Path:
    path.mkdir(parents=True)
    _git("init", "-q", str(path))
    _git("-C", str(path), "remote", "add", "origin", remote)
    return path


@pytest.fixture
def container(tmp_path: Path) -> Path:
    """A clone, its linked worktree (sorted right after it), then a distinct repo."""
    clone = _repo(tmp_path / "Cursor-Governance", "https://github.com/Quantum-L9/Cursor-Governance")
    _git(
        "-C", str(clone), "-c", "user.email=t@t", "-c", "user.name=t",
        "commit", "-q", "--allow-empty", "-m", "seed",
    )  # fmt: skip
    _git(
        "-C",
        str(clone),
        "worktree",
        "add",
        "-q",
        "--detach",
        str(tmp_path / "Cursor-Governance-wt"),
    )
    _repo(tmp_path / "l9-ci-core", "https://github.com/Quantum-L9/l9-ci-core")
    return tmp_path


def test_a_duplicate_checkout_never_takes_a_hydration_slot(
    container: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefetch = _prefetch()
    monkeypatch.setattr(prefetch, "_MAX_HYDRATION_ROOTS", 2)
    hydrated = [root.name for root in prefetch._hydration_selection(container).selected]
    assert hydrated == ["Cursor-Governance", "l9-ci-core"]
    dropped = {root.name: why for root, why in prefetch._hydration_selection(container).dropped}
    assert dropped == {"Cursor-Governance-wt": nc.DROPPED_DUPLICATE_NAMESPACE}
    note = prefetch._dropped_summary(prefetch._hydration_selection(container).dropped)
    assert "Cursor-Governance-wt" in note
    assert "already in scope" in note


def test_bootstrap_reports_exactly_the_hydrated_roots(
    container: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefetch = _prefetch()
    monkeypatch.setattr(prefetch, "_MAX_HYDRATION_ROOTS", 2)
    hydrated = [str(root) for root in prefetch._hydration_selection(container).selected]
    reported = nc.resolve_workspace_namespaces(container, cap=2)
    assert [root for root, _ in reported.namespaces] == hydrated
    assert [ns for _, ns in reported.namespaces] == ["cursor-governance", "l9-ci-core"]
