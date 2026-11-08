"""worktree_add_wired.sh never writes into a consumer's tracked AGENTS.md / CLAUDE.md.

Worktree creation used to run the full workspace reconciler, which reaches
install_ide_profile.sh -> adapters/agentdocs.sh and appends the generated
formatter-ownership block to the consumer's tracked governance documents. Every
new consumer worktree therefore started dirty in T4 files (EIE PR #259
governance handoff). Worktree creation now wires links only, like every other
programmatic worktree creator; the formatter block still reaches consumers
through sessionStart and `make ide-profile`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops/scripts/worktree_add_wired.sh"
_STUB_VENV = "venv:\n\ttouch .venv-marker\n"

pytestmark = [
    pytest.mark.skipif(shutil.which("git") is None, reason="git not installed"),
    pytest.mark.skipif(shutil.which("make") is None, reason="make not installed"),
]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def test_new_consumer_worktree_leaves_tracked_agent_docs_untouched(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cursor-governance").symlink_to(ROOT)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _git(consumer, "init", "-q", "-b", "main")
    (consumer / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    (consumer / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
    _git(consumer, "add", "AGENTS.md", "CLAUDE.md")
    _git(consumer, "commit", "-qm", "init")

    worktree = tmp_path / "wt"
    env = {**os.environ, "HOME": str(home)}
    env.pop("L9_WIRE_LINKS_ONLY", None)
    proc = subprocess.run(
        ["bash", str(SCRIPT), "-b", "feat/x", str(worktree), "main"],
        cwd=consumer,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr

    changed = _git(worktree, "status", "--porcelain", "--", "AGENTS.md", "CLAUDE.md")
    assert changed == "", changed
    assert (worktree / ".cursor-commands").is_symlink(), proc.stdout
    assert not (worktree / ".vscode").exists(), "worktree setup ran the IDE reconciler"
    assert "--- venv (make venv) ---" not in proc.stdout


def _init_consumer(tmp_path: Path, files: dict[str, str]) -> tuple[Path, Path, Path]:
    home = tmp_path / "home"
    home.mkdir()
    (home / ".cursor-governance").symlink_to(ROOT)
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _git(consumer, "init", "-q", "-b", "main")
    for name, text in files.items():
        dest = consumer / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        _git(consumer, "add", "--", name)
    _git(consumer, "commit", "-qm", "init")
    return consumer, tmp_path / "wt", home


def _run_wired(consumer: Path, worktree: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HOME": str(home)}
    env.pop("L9_WIRE_LINKS_ONLY", None)
    return subprocess.run(
        ["bash", str(SCRIPT), "-b", "feat/x", str(worktree), "main"],
        cwd=consumer,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=600,
    )


def _assert_stub_venv(proc: subprocess.CompletedProcess[str], worktree: Path) -> None:
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "--- venv (make venv) ---" in proc.stdout
    assert (worktree / ".venv-marker").is_file()
    assert not (worktree / ".venv").is_symlink()


def test_worktree_runs_root_venv_target(tmp_path: Path) -> None:
    consumer, worktree, home = _init_consumer(tmp_path, {"Makefile": _STUB_VENV})
    proc = _run_wired(consumer, worktree, home)
    _assert_stub_venv(proc, worktree)


def test_worktree_runs_venv_target_from_included_fragment(tmp_path: Path) -> None:
    consumer, worktree, home = _init_consumer(
        tmp_path,
        {"Makefile": "include fragment.mk\n", "fragment.mk": _STUB_VENV},
    )
    proc = _run_wired(consumer, worktree, home)
    _assert_stub_venv(proc, worktree)


def test_uv_lock_without_venv_target_does_not_build(tmp_path: Path) -> None:
    consumer, worktree, home = _init_consumer(
        tmp_path,
        {"pyproject.toml": "[project]\nname = 'x'\n", "uv.lock": "version = 1\n"},
    )
    proc = _run_wired(consumer, worktree, home)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "locked venv" not in proc.stdout
    assert not (worktree / ".venv").exists()
