"""#861: pr-intent.json survives commits the publish machinery adds after it.

GMP finalize, the gate's writer-rewrite commit and the generated-heal commit all
land between the author writing pr-intent.json and the composer reading it, so a
strict head match dropped the intent and titled the PR from the oldest commit.
An intent whose head is an ancestor of HEAD is honoured only when every commit in
between is machine-authored; an unrelated or author-advanced head is still
refused.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from compose_pr_body import INTENT_SCHEMA, load_intent  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, name: str, message: str) -> str:
    (repo / name).write_text(message + "\n", encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "ws"
    path.mkdir()
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "t@example.com")
    _git(path, "config", "user.name", "t")
    _commit(path, "a.txt", "feat: the author's change")
    return path


def _intent(tmp_path: Path, head: str) -> Path:
    path = tmp_path / "pr-intent.json"
    path.write_text(
        json.dumps({"schema": INTENT_SCHEMA, "head": head, "title": "Author title"}),
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    "machine_subject",
    [
        "style: commit gate writer rewrites so make pr finishes once",
        "chore(generated): commit generated heal before publish",
        "chore(generated): heal artifacts after push-recovery merge",
        "docs(reports): GMP report GMP-Report-131-Build.md",
        "GMP-131: Build docs plans",
    ],
)
def test_intent_survives_machine_commits(repo: Path, tmp_path: Path, machine_subject: str) -> None:
    written = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "m.txt", machine_subject)
    intent = load_intent(_intent(tmp_path, written[:12]), head, workspace=repo)
    assert intent is not None and intent.title == "Author title"


def test_intent_refused_after_an_author_commit(repo: Path, tmp_path: Path) -> None:
    written = _git(repo, "rev-parse", "HEAD")
    _commit(repo, "m.txt", "style: commit gate writer rewrites so make pr finishes once")
    head = _commit(repo, "b.txt", "feat: more author work the intent never described")
    assert load_intent(_intent(tmp_path, written), head, workspace=repo) is None


def test_intent_for_an_unrelated_head_is_refused(repo: Path, tmp_path: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "other")
    unrelated = _commit(repo, "x.txt", "feat: elsewhere")
    _git(repo, "checkout", "-q", "-")
    head = _commit(repo, "m.txt", "chore(generated): commit generated heal before publish")
    assert load_intent(_intent(tmp_path, unrelated), head, workspace=repo) is None


def test_without_a_workspace_the_strict_match_stands(repo: Path, tmp_path: Path) -> None:
    written = _git(repo, "rev-parse", "HEAD")
    head = _commit(repo, "m.txt", "chore(generated): commit generated heal before publish")
    assert load_intent(_intent(tmp_path, written), head) is None
    assert load_intent(_intent(tmp_path, head[:9]), head) is not None
