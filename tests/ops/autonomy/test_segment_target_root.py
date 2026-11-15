"""Gates judge a git segment by the repository it runs in, not the session root (#971).

``git -C <repo> ...`` and ``cd <repo> && git ...`` act on <repo>. Both directions
matter: a clean target is not denied because the session root is dirty or is no
repository at all (#971, #961, #902), and a dirty target is not allowed because
the session root happens to be clean.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ops" / "autonomy"))

from command_parse import segments_with_directories  # noqa: E402
from git_guardrails import command_requires_human  # noqa: E402
from worktree_isolation_gate import command_violates_worktree_isolation  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _repo(path: Path, *, dirty: bool = False) -> Path:
    path.mkdir(parents=True)
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@example.invalid")
    _git(path, "config", "user.name", "t")
    (path / "a.txt").write_text("a\n", encoding="utf-8")
    _git(path, "add", "a.txt")
    _git(path, "commit", "-qm", "a")
    _git(path, "branch", "other")
    if dirty:
        (path / "a.txt").write_text("foreign edit\n", encoding="utf-8")
        (path / "foreign-notes.md").write_text("another chat's work\n", encoding="utf-8")
    return path.resolve()


@pytest.fixture(autouse=True)
def _no_breakglass(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "L9_GIT_DESTRUCTIVE_AUTHORIZED",
        "L9_GIT_SWITCH_AUTHORIZED",
        "L9_GIT_RESET_AUTHORIZED",
        "L9_GIT_CLEAN_AUTHORIZED",
        "L9_WORKTREE_ISOLATION",
    ):
        monkeypatch.delenv(name, raising=False)


def test_directories_follow_cd_and_dash_c() -> None:
    root = Path("/session")
    got = segments_with_directories(
        "cd /srv/r && git status && git -C sub reset --hard && git -C $X reset", root
    )
    assert [str(d) for _s, d in got] == ["/srv/r", "/srv/r", "/srv/r/sub", "None"]


def test_guardrail_probes_the_dash_c_repo_from_a_non_repo_cwd(tmp_path: Path) -> None:
    """#971: cwd /home/user (no repo) made every `git -C <repo>` mutation fault (I017)."""
    session = tmp_path / "home"
    session.mkdir()
    clean = _repo(tmp_path / "clean")
    assert command_requires_human(f"git -C {clean} branch -D other", root=session) is None


def test_guardrail_judges_a_dirty_target_not_the_clean_session(tmp_path: Path) -> None:
    session = _repo(tmp_path / "session")
    dirty = _repo(tmp_path / "dirty", dirty=True)
    reason = command_requires_human(f"git -C {dirty} clean -fd", root=session)
    assert reason and "foreign-notes.md" in reason, reason
    assert command_requires_human("git clean -fd", root=session) is None


def test_isolation_allows_a_checkout_in_a_clean_scratch_clone(tmp_path: Path) -> None:
    """#961 / #902: the scratch clone's checkout was judged by the dirty session."""
    session = _repo(tmp_path / "session", dirty=True)
    scratch = _repo(tmp_path / "scratch")
    command = f"cd {scratch} && git checkout other"
    assert command_violates_worktree_isolation(command, root=session) is None
    assert command_violates_worktree_isolation("git checkout other", root=session)


def test_isolation_denies_a_checkout_in_a_dirty_target_from_a_clean_session(
    tmp_path: Path,
) -> None:
    session = _repo(tmp_path / "session")
    dirty = _repo(tmp_path / "dirty", dirty=True)
    reason = command_violates_worktree_isolation(f"git -C {dirty} checkout other", root=session)
    assert reason and "worktree is dirty" in reason
    same_text_twice = f"cd {dirty} && git checkout other && cd {session} && git checkout other"
    assert command_violates_worktree_isolation(same_text_twice, root=session)


@pytest.mark.parametrize(
    "template",
    [
        "git -C {repo} revert HEAD",
        "git -C {repo} reset HEAD~0",
        "git -C {repo} -c core.pager=cat checkout other",
        "git -C {repo} add -A",
        "git --git-dir {repo}/.git --work-tree {repo} add --all",
    ],
)
def test_global_options_do_not_hide_the_subcommand(tmp_path: Path, template: str) -> None:
    """`git -C <repo> <sub>` used to slip past every isolation matcher."""
    dirty = _repo(tmp_path / "dirty", dirty=True)
    command = template.format(repo=dirty)
    assert command_violates_worktree_isolation(command, root=dirty), command
