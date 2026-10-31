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

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


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
