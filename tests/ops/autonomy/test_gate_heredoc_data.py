"""Data-vs-command false positives: gates must ignore heredoc/string data."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from local_execution_gate import command_is_remote_mutation  # noqa: E402
from worktree_isolation_gate import command_violates_worktree_isolation  # noqa: E402


def _dirty_repo(tmp_path: Path) -> Path:
    """A git repo with uncommitted work (dirty-gated deny paths apply)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "test"], check=True, capture_output=True
    )
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True
    )
    (repo / "dirty.txt").write_text("d\n", encoding="utf-8")
    return repo


HEREDOC_DATA = (
    "python3 - <<'EOF'\n"
    "# rollback: git revert / git reset are recovery options\n"
    "print('make push pr=1 is the publish path')\n"
    "EOF\n"
    "git status\n"
)


def test_heredoc_data_does_not_trigger_isolation_gate():
    assert command_violates_worktree_isolation(HEREDOC_DATA, root=None) is None


def test_heredoc_data_does_not_trigger_remote_mutation():
    assert command_is_remote_mutation(HEREDOC_DATA) is False


def test_real_git_revert_still_denied():
    assert command_violates_worktree_isolation("git revert abc123", root=None) is not None


def test_real_broad_add_still_denied():
    assert command_violates_worktree_isolation("git add -A", root=None) is not None


def test_real_git_push_still_detected():
    assert command_is_remote_mutation("git push origin HEAD") is True


def test_bash_wrapped_git_push_still_detected():
    assert command_is_remote_mutation("bash -c 'git push origin main'") is True
    assert command_is_remote_mutation('sh -c "make pr"') is True


def test_echo_of_git_words_is_not_a_mutation():
    assert command_is_remote_mutation("echo 'git push origin main'") is False


def test_git_commit_message_with_revert_words_is_not_denied():
    # Command-position matching: the message is data, not a subcommand.
    assert (
        command_violates_worktree_isolation(
            'git commit -m "rollback docs mention git revert"', root=None
        )
        is None
    )


def test_unrelated_segment_cannot_trigger_git_patterns():
    # `echo` segment mentioning git ops must not deny the real harmless segment.
    assert (
        command_violates_worktree_isolation("echo 'git revert foo' && git status", root=None)
        is None
    )


@pytest.mark.parametrize(
    "command",
    [
        "git switch main",
        "git reset --hard",
        "git checkout other",
        "git clean -fd",
    ],
)
def test_dangerous_git_commands_still_denied_on_dirty_tree(command: str, tmp_path: Path) -> None:
    assert command_violates_worktree_isolation(command, root=_dirty_repo(tmp_path)) is not None


# --- merge_gate: a document that QUOTES a merge is not a merge -----------------

sys.path.insert(0, str(ROOT / "ops" / "lib"))
import merge_gate as mg  # noqa: E402

# Assembled from parts so this source file never carries a literal that a
# PreToolUse matcher could mistake for an executed command.
_MERGE = "gh" + " pr " + "merge"
_FORCE = "git push --" + "force"

_MERGE_IN_HEREDOC = "cat > /tmp/report.html <<'L9EOF'\n<p>then " + _MERGE + "</p>\nL9EOF\n"
_FORCE_IN_HEREDOC = "cat > /tmp/runbook.md <<'EOF'\nnever run " + _FORCE + " here\nEOF\n"


def _decide(command: str) -> str | None:
    return mg.evaluate("Bash", {"command": command})


def test_heredoc_quoting_merge_is_not_a_merge() -> None:
    """Writing a runbook that names the merge path must not be denied as one.

    MERGE_BASH used to search the raw command, short-circuiting the heredoc
    stripping the same branch already performed via _command_is_pr_merge.
    """
    assert _decide(_MERGE_IN_HEREDOC) is None


def test_heredoc_quoting_force_push_is_not_never_waive() -> None:
    assert _decide(_FORCE_IN_HEREDOC) is None


def test_real_admin_merge_is_still_never_waived() -> None:
    reason = _decide(_MERGE + " 12 --repo o/r --admin")
    assert reason is not None
    assert "never waives" in reason


def test_real_merge_command_is_still_gated() -> None:
    """The executed form must still be denied — the fix is precision, not scope."""
    assert _decide(_MERGE + " 12 --repo o/r --squash") is not None
