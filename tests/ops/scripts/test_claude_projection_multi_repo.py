"""Conformance: project-scope projection reaches per-repository mirrors.

Observed defect: the `claude-code-project` adapter targeted the container root,
so `.claude/skills` and `.claude/commands` mirrors inside each repository were
outside every reconciler's target set. The reconciler's obsolete-entry sweep
therefore never reached them and they kept symlinks to skills the SSOT had
removed — 16 dangling links across 4 repositories, which failed two tests in a
consumer repo whose suite copies its own tree.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "ops" / "scripts" / "lib"))

from workspace_roots import projection_roots  # noqa: E402

SKILL_ADAPTERS = REPO_ROOT / "ops" / "scripts" / "reconcile_llm_skill_adapters.py"
COMMAND_ADAPTERS = REPO_ROOT / "ops" / "scripts" / "reconcile_claude_commands.py"


def make_repo(parent: Path, name: str) -> Path:
    repo = parent / name
    (repo / ".git").mkdir(parents=True)
    return repo


def test_skill_adapter_fans_project_scope_over_mount_roots() -> None:
    body = SKILL_ADAPTERS.read_text(encoding="utf-8")
    assert 'projection_roots(workspace) if scope == "project" else [workspace]' in body
    assert "mount_root" in body, "each result must name the root it reconciled"


def test_command_adapter_fans_project_scope_over_mount_roots() -> None:
    body = COMMAND_ADAPTERS.read_text(encoding="utf-8")
    assert "projection_roots(workspace)" in body
    assert "target_override is None" in body, (
        "an explicit --target names one directory and must never be fanned out"
    )


def test_mount_roots_cover_every_repository_and_the_container(tmp_path: Path) -> None:
    repos = [make_repo(tmp_path, name) for name in ("alpha", "beta", "gamma")]
    roots = projection_roots(tmp_path)
    assert roots[0] == tmp_path
    assert set(roots[1:]) == set(repos)


def test_single_repository_workspace_is_not_fanned_out(tmp_path: Path) -> None:
    """A normal developer checkout must reconcile exactly one mirror."""
    repo = make_repo(tmp_path, "solo")
    assert projection_roots(repo) == [repo]


def test_live_container_has_no_dangling_managed_links() -> None:
    """The acceptance signal, asserted against the real container.

    Skipped where the workspace is not a multi-repo container, so the suite
    stays meaningful on a developer checkout instead of silently passing.
    """
    import pytest

    container = REPO_ROOT.parent
    roots = projection_roots(container)
    if roots == [container]:
        pytest.skip("not a multi-repository container")

    dangling = [
        str(entry)
        for root in roots
        for sub in ("skills", "commands")
        for entry in (root / ".claude" / sub).glob("*")
        if entry.is_symlink() and not entry.exists()
    ]
    assert not dangling, "dangling projection links:\n" + "\n".join(dangling)
