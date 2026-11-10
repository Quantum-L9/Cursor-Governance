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

from workspace_roots import adopted_projection_roots, projection_roots  # noqa: E402

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


def test_a_container_mirror_is_adopted_from_a_repository_workspace(tmp_path: Path) -> None:
    """The half of the defect `projection_roots` alone cannot reach.

    The boot-time reconcile ran with the container as its workspace and wrote
    `<container>/.claude/skills`. Every later session ran with the repository as
    its workspace, where `projection_roots` correctly answers `[repository]`, so
    that mirror left every target set and its obsolete-entry sweep stopped
    running. It kept a symlink to a skill the SSOT had removed.
    """
    repo = make_repo(tmp_path, "solo")
    mirror = tmp_path / ".claude" / "skills"
    mirror.mkdir(parents=True)
    (mirror / ".l9-managed-skills.json").write_text("{}", encoding="utf-8")

    assert projection_roots(repo) == [repo], "discovery must stay unchanged"
    assert adopted_projection_roots(
        repo, Path(".claude") / "skills", ".l9-managed-skills.json"
    ) == [tmp_path]


def test_adoption_requires_our_own_state_file(tmp_path: Path) -> None:
    """Ownership is proven, never assumed: an ancestor holding a same-named
    directory we never wrote is somebody else's and stays untouched."""
    repo = make_repo(tmp_path, "solo")
    (tmp_path / ".claude" / "skills").mkdir(parents=True)

    assert (
        adopted_projection_roots(repo, Path(".claude") / "skills", ".l9-managed-skills.json") == []
    )


def test_the_user_scope_target_is_never_adopted_as_a_project_mount(tmp_path: Path) -> None:
    """A checkout under `$HOME` makes the user projection answer the scan.

    `$HOME/.claude/skills` carries the same relative path and the same state
    filename as a container mirror, and the state file records a governance
    root rather than a scope, so nothing in it separates the two. Adopting it
    would hand the user's own projection to a project-scope reconcile.
    """
    home = tmp_path / "home" / "dev"
    repo = make_repo(home, "checkout")
    user_target = home / ".claude" / "skills"
    user_target.mkdir(parents=True)
    (user_target / ".l9-managed-skills.json").write_text("{}", encoding="utf-8")

    relative = Path(".claude") / "skills"
    assert adopted_projection_roots(repo, relative, ".l9-managed-skills.json") == [home], (
        "without the exclusion the user projection is adopted — that is the hazard"
    )
    assert (
        adopted_projection_roots(
            repo, relative, ".l9-managed-skills.json", exclude_targets=[user_target]
        )
        == []
    )


def test_a_traversing_target_is_never_adopted(tmp_path: Path) -> None:
    """`..` is relative, so an absolute-only check would let it climb out of the
    ancestor it was joined to and adopt a directory outside the lineage."""
    outside = tmp_path / "outside" / ".claude" / "skills"
    outside.mkdir(parents=True)
    (outside / ".l9-managed-skills.json").write_text("{}", encoding="utf-8")
    repo = make_repo(tmp_path / "nest", "solo")

    escaping = Path("..") / "outside" / ".claude" / "skills"
    assert adopted_projection_roots(repo, escaping, ".l9-managed-skills.json") == []


def test_an_absolute_target_is_never_adopted(tmp_path: Path) -> None:
    """A user-scope target is the same directory for every ancestor, so it
    proves nothing about which root owns it."""
    repo = make_repo(tmp_path, "solo")

    assert adopted_projection_roots(repo, Path("/etc"), "passwd") == []


def _mirror(parent: Path, governance_root: str | None) -> None:
    import json

    mirror = parent / ".claude" / "skills"
    mirror.mkdir(parents=True)
    payload = {} if governance_root is None else {"governance_root": governance_root}
    (mirror / ".l9-managed-skills.json").write_text(json.dumps(payload), encoding="utf-8")


def test_a_second_checkout_never_adopts_the_ssot_mirror(tmp_path: Path) -> None:
    """Observed: a governance checkout nested in the container re-pointed the
    container mirror the SSOT bootstrap wrote, every time it ran its generator."""
    ssot, checkout = tmp_path / "ssot", make_repo(tmp_path, "Cursor-Governance")
    _mirror(tmp_path, str(ssot))
    relative = Path(".claude") / "skills"

    assert (
        adopted_projection_roots(checkout, relative, ".l9-managed-skills.json", owner_root=checkout)
        == []
    )
    assert adopted_projection_roots(
        checkout, relative, ".l9-managed-skills.json", owner_root=ssot
    ) == [tmp_path]


def test_an_ownerless_state_file_is_not_adopted_when_an_owner_is_required(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path, "solo")
    _mirror(tmp_path, None)
    assert (
        adopted_projection_roots(
            repo, Path(".claude") / "skills", ".l9-managed-skills.json", owner_root=tmp_path
        )
        == []
    )


def test_both_adapters_adopt_only_their_own_mirror() -> None:
    for script in (SKILL_ADAPTERS, COMMAND_ADAPTERS):
        body = script.read_text(encoding="utf-8")
        assert "owner_root=root" in body, (
            f"{script.name} must adopt only a mirror its own governance root wrote"
        )


def test_both_adapters_adopt_an_ancestor_mirror() -> None:
    for script in (SKILL_ADAPTERS, COMMAND_ADAPTERS):
        body = script.read_text(encoding="utf-8")
        assert "adopted_projection_roots" in body, (
            f"{script.name} must reconcile container mirrors it already owns"
        )


def test_live_container_has_no_dangling_managed_links() -> None:
    """The acceptance signal, asserted against the real container.

    Skipped where the workspace is not a multi-repo container, so the suite
    stays meaningful on a developer checkout instead of silently passing.

    A link its repository COMMITTED is that repository's content, not a
    projection link: reconcile_scope never creates, repoints or removes it, and
    claude_projection reports it as consumer_owned. Counting one here failed this
    suite on content no governance change can or should alter (IB-Odoo_19's
    committed links to retired skills). Every link the projection could have
    written is still checked.
    """
    import subprocess

    import pytest

    container = REPO_ROOT.parent
    roots = projection_roots(container)
    if roots == [container]:
        pytest.skip("not a multi-repository container")

    def committed(entry: Path) -> bool:
        probe = subprocess.run(
            ["git", "-C", str(entry.parent), "ls-files", "--error-unmatch", entry.name],
            capture_output=True,
            check=False,
        )
        return probe.returncode == 0

    dangling = [
        str(entry)
        for root in roots
        for sub in ("skills", "commands")
        for entry in (root / ".claude" / sub).glob("*")
        if entry.is_symlink() and not entry.exists() and not committed(entry)
    ]
    assert not dangling, "dangling projection links:\n" + "\n".join(dangling)
