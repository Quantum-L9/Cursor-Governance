"""Governance must not leave the wiring it injects as dirt in a consumer.

The Claude adapter's reconcilers materialize real files inside every workspace
they touch: `.claude/settings.json` and the two `CONSUMER_HOOK_FILES` hooks.
The installer's exclude list deliberately omitted them as "committable consumer
wiring" — right for a repo that commits them, wrong for the repo that does not,
where they sit as `??` after every session and land in any inventory that
enumerates the working tree.

Tracked-ness is the ownership signal, exactly as
`reconcile_claude_settings.settings_is_git_tracked` already defines it: a
tracked file is repo content and is left alone; an untracked one was injected
here and is governance's to contain. So the exclusion is conditional — an
unconditional one would force `git add -f` on a consumer that legitimately
commits its wiring.

These tests run the real installer against throwaway repositories and assert
the observable effect (`git status`), not the text of the glob list.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
INSTALL = ROOT / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"
RECONCILER = ROOT / "ops" / "scripts" / "reconcile_claude_settings.py"
GOV_PY = ROOT / ".venv" / "bin" / "python3"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )


def _workspace(tmp_path: Path, *, commit_wiring: bool) -> Path:
    repo = tmp_path / ("tracked" if commit_wiring else "untracked")
    (repo / ".claude" / "hooks").mkdir(parents=True)
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    (repo / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    for name in ("session_start_claude_governance.sh", "merge_gate_wrap.py"):
        (repo / ".claude" / "hooks" / name).write_text("#!/bin/sh\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    if commit_wiring:
        _git(repo, "add", "-f", ".claude/settings.json", ".claude/hooks")
    _git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return repo


def _install(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(INSTALL), "--governance", str(ROOT), "--workspace", str(repo)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_reconciler_publishes_the_files_it_writes() -> None:
    """The installer reads this list instead of restating it in shell."""
    out = subprocess.run(
        [str(GOV_PY), str(RECONCILER), "--print-workspace-artifacts"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert ".claude/settings.json" in out
    assert any(item.startswith(".claude/hooks/") for item in out)


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; installer cannot run")
def test_injected_wiring_leaves_no_dirt(tmp_path: Path) -> None:
    """A consumer that never committed the wiring ends the session clean."""
    repo = _workspace(tmp_path, commit_wiring=False)
    assert _git(repo, "status", "--porcelain").stdout.strip(), "fixture should start dirty"

    _install(repo)

    assert _git(repo, "status", "--porcelain").stdout.strip() == ""


@pytest.mark.skipif(not GOV_PY.exists(), reason="locked interpreter absent; installer cannot run")
def test_committed_wiring_is_left_alone(tmp_path: Path) -> None:
    """Repo content stays visible: no exclusion, so edits still show up."""
    repo = _workspace(tmp_path, commit_wiring=True)

    _install(repo)

    exclude = repo / ".git" / "info" / "exclude"
    body = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    assert ".claude/settings.json" not in body.splitlines()

    (repo / ".claude" / "settings.json").write_text('{"edited": true}\n', encoding="utf-8")
    assert ".claude/settings.json" in _git(repo, "status", "--porcelain").stdout
