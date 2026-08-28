"""The advisory must fire on the case that cost a cycle, and stay quiet otherwise.

2026-08-28: one rewritten line in `pyproject.toml` was discovered by `make pr` an
hour after the edit. The rule was not missing — AGENTS.md §14 states it exactly —
it just never reached the model's context. An advisory nobody reads is the same
failure again, so the bar here is: silent unless there is something to act on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

from root_file_advisory import advisory  # noqa: E402


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo shaped like this one: a protection config and an additive_only file."""
    work = tmp_path / "repo"
    (work / "ops" / "config").mkdir(parents=True)
    (work / "ops" / "config" / "root-file-protection.json").write_text(
        json.dumps(
            {
                "protected_files": [
                    {"path": "pyproject.toml", "rule": "additive_only"},
                    {"path": "CLAUDE.md", "rule": "managed"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (work / "pyproject.toml").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (work / "CLAUDE.md").write_text("pointer\n", encoding="utf-8")
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "base")
    _git(work, "branch", "-f", "origin/main")  # stand-in for the remote ref
    return work


def _as_origin_main(repo: Path) -> None:
    """Point refs/remotes/origin/main at the base commit the gate compares against."""
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "main"], capture_output=True, text=True, check=True
    ).stdout.strip()
    (repo / ".git" / "refs" / "remotes" / "origin").mkdir(parents=True, exist_ok=True)
    (repo / ".git" / "refs" / "remotes" / "origin" / "main").write_text(head + "\n")


def test_silent_when_nothing_changed(repo: Path) -> None:
    _as_origin_main(repo)
    assert advisory(repo) is None


def test_silent_on_a_purely_additive_change(repo: Path) -> None:
    _as_origin_main(repo)
    (repo / "pyproject.toml").write_text("alpha\nbeta\ngamma\ndelta\n", encoding="utf-8")
    assert advisory(repo) is None, "appending to an additive_only file is the sanctioned edit"


def test_fires_on_an_uncommitted_overwrite(repo: Path) -> None:
    """The cheapest moment to act: the marker can still go in the commit."""
    _as_origin_main(repo)
    (repo / "pyproject.toml").write_text("ALPHA\nbeta\ngamma\n", encoding="utf-8")
    message = advisory(repo)
    assert message and "pyproject.toml" in message
    assert "ALLOW-ROOT-DELETION" in message


def test_fires_on_a_committed_overwrite(repo: Path) -> None:
    _as_origin_main(repo)
    (repo / "pyproject.toml").write_text("ALPHA\nbeta\ngamma\n", encoding="utf-8")
    _git(repo, "add", "pyproject.toml")
    _git(repo, "commit", "-q", "-m", "rewrite a line")
    message = advisory(repo)
    assert message and "pyproject.toml" in message


def test_clears_itself_once_the_marker_exists(repo: Path) -> None:
    """The advisory is a reminder, not a nag: satisfying it silences it."""
    _as_origin_main(repo)
    (repo / "pyproject.toml").write_text("ALPHA\nbeta\ngamma\n", encoding="utf-8")
    _git(repo, "add", "pyproject.toml")
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        "rewrite a line\n\nALLOW-ROOT-DELETION: pyproject.toml — the pinned value moved upstream",
    )
    assert advisory(repo) is None


def test_managed_files_are_not_flagged(repo: Path) -> None:
    """`managed` is review-only; flagging it would train the reader to ignore this."""
    _as_origin_main(repo)
    (repo / "CLAUDE.md").write_text("rewritten pointer\n", encoding="utf-8")
    assert advisory(repo) is None


def test_missing_config_is_silent_not_noisy(tmp_path: Path) -> None:
    """Observer class: a broken advisory must never cost a turn."""
    bare = tmp_path / "bare"
    bare.mkdir()
    _git(bare, "init", "-q", "-b", "main")
    assert advisory(bare) is None


def test_hook_emits_useable_userpromptsubmit_json(repo: Path) -> None:
    _as_origin_main(repo)
    (repo / "pyproject.toml").write_text("ALPHA\nbeta\ngamma\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "ops" / "autonomy" / "root_file_advisory.py")],
        input=json.dumps({"cwd": str(repo)}),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)["hookSpecificOutput"]
    assert payload["hookEventName"] == "UserPromptSubmit"
    assert "pyproject.toml" in payload["additionalContext"]


def test_wired_into_the_settings_template() -> None:
    """An unwired advisory is a file, not a mechanism."""
    template = json.loads(
        (
            ROOT / "environment" / "agents" / "adapters" / "claude-code" / "settings.template.json"
        ).read_text(encoding="utf-8")
    )
    commands = [
        hook["command"]
        for group in template["hooks"]["UserPromptSubmit"]
        for hook in group["hooks"]
    ]
    assert any("root_file_advisory_wrap.py" in command for command in commands)
    assert all("--class observer" in c for c in commands if "root_file_advisory" in c)
