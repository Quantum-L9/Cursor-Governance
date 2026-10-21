"""CG-01 ownership guard for the Claude skill reconciler.

A consumer that tracks `.claude/skills/l9-*` links (relative, e.g. into its own
`.cursor-commands`) and the `.l9-managed-skills.json` manifest owns those git
objects. SessionStart rewrote them into machine-absolute SSOT links and rewrote
the manifest, so a clean checkout went dirty without an agent edit (observed on
a consumer with ~45 tracked links). The reconciler must refuse to mutate a
tracked entry or manifest and report it; untracked entries keep today's repair.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import reconcile_claude_l9_skills as rs  # noqa: E402


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout


def _fake_ssot(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    gov = tmp_path / "gov"
    for name in ("l9-alpha", "l9-beta"):
        skill = gov / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    registry = {
        "skills": [
            {"name": "l9-alpha", "path": "skills/l9-alpha"},
            {"name": "l9-beta", "path": "skills/l9-beta"},
        ]
    }
    return gov, registry


def _consumer(tmp_path: Path, *, track: bool) -> Path:
    """A consumer whose `.claude/skills` holds relative links into its own tree."""
    ws = tmp_path / "consumer"
    skills = ws / ".claude" / "skills"
    skills.mkdir(parents=True)
    for name in ("l9-alpha", "l9-beta"):
        own = ws / ".cursor-commands" / "skills" / name
        own.mkdir(parents=True)
        (own / "SKILL.md").write_text(f"# consumer {name}\n", encoding="utf-8")
        (skills / name).symlink_to(Path("../../.cursor-commands/skills") / name)
    (skills / rs.STATE_NAME).write_text(
        json.dumps({"schema_version": 1, "skills": ["l9-alpha", "l9-beta"]}) + "\n",
        encoding="utf-8",
    )
    _git("init", "-q", cwd=ws)
    _git("config", "user.email", "t@t", cwd=ws)
    _git("config", "user.name", "t", cwd=ws)
    if track:
        _git("add", ".claude", ".cursor-commands", cwd=ws)
        _git("commit", "-qm", "consumer owns its skill links", cwd=ws)
    return ws


def _tree_fingerprint(ws: Path) -> tuple[str, str]:
    return (
        _git("status", "--porcelain", cwd=ws),
        _git("ls-files", "-s", ".claude", cwd=ws),
    )


def test_tracked_links_and_manifest_survive_two_reconciles(tmp_path: Path) -> None:
    gov, registry = _fake_ssot(tmp_path)
    ws = _consumer(tmp_path, track=True)
    before = _tree_fingerprint(ws)
    link_targets = {
        name: (ws / ".claude" / "skills" / name).readlink() for name in ("l9-alpha", "l9-beta")
    }

    for _ in range(2):
        result = rs.reconcile_scope(gov, registry, "project", ws, "symlink", False)
        assert "tracked-owned:l9-alpha" in result.conflicts, result.as_dict()
        assert "tracked-owned:l9-beta" in result.conflicts, result.as_dict()
        assert f"tracked-manifest:{rs.STATE_NAME}" in result.drift, result.as_dict()
        assert result.created == [] and result.removed == []

    assert _tree_fingerprint(ws) == before
    for name, target in link_targets.items():
        assert (ws / ".claude" / "skills" / name).readlink() == target


def test_untracked_wrong_target_link_is_still_repaired(tmp_path: Path) -> None:
    """Positive control: an entry git does not own is governance-managed."""
    gov, registry = _fake_ssot(tmp_path)
    ws = _consumer(tmp_path, track=False)

    result = rs.reconcile_scope(gov, registry, "project", ws, "symlink", False)

    assert not [c for c in result.conflicts if c.startswith("tracked-owned:")], result.as_dict()
    for name in ("l9-alpha", "l9-beta"):
        link = ws / ".claude" / "skills" / name
        assert link.resolve() == (gov / "skills" / name).resolve()
    state = json.loads((ws / ".claude" / "skills" / rs.STATE_NAME).read_text(encoding="utf-8"))
    assert state["skills"] == ["l9-alpha", "l9-beta"]


def test_a_tracked_real_directory_copy_is_never_deleted(tmp_path: Path) -> None:
    """The duplicate branch `rmtree`s a real directory: a tracked one is the
    consumer's content, not a forbidden copy to replace."""
    gov, registry = _fake_ssot(tmp_path)
    ws = tmp_path / "consumer"
    copy = ws / ".claude" / "skills" / "l9-alpha"
    copy.mkdir(parents=True)
    (copy / "SKILL.md").write_text("# consumer-owned copy\n", encoding="utf-8")
    _git("init", "-q", cwd=ws)
    _git("config", "user.email", "t@t", cwd=ws)
    _git("config", "user.name", "t", cwd=ws)
    _git("add", ".claude", cwd=ws)
    _git("commit", "-qm", "own copy", cwd=ws)

    result = rs.reconcile_scope(gov, registry, "project", ws, "symlink", False)

    assert "tracked-owned:l9-alpha" in result.conflicts, result.as_dict()
    assert copy.is_dir() and not copy.is_symlink()
    assert (copy / "SKILL.md").read_text(encoding="utf-8") == "# consumer-owned copy\n"


def test_tracked_probe_failure_is_non_destructive(tmp_path: Path, monkeypatch) -> None:
    """An unanswerable ownership question must take the branch that destroys
    nothing, exactly as `_path_is_git_tracked` treats a git timeout."""
    monkeypatch.setitem(sys.modules, "reconcile_claude_settings", None)
    assert rs.path_is_tracked(tmp_path / "anything") is True
