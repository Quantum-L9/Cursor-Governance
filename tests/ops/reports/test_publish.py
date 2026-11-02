"""ops/reports/publish.py — report layout and publication onto the open PR.

Real git, no mocks: a work clone with a bare ``origin``, on a PR branch, with
``reports/`` gitignored the way most governed repositories ignore it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ops.reports import publish as rp

BRANCH = "agent/claude-code/report-publish"


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture()
def clone(tmp_path: Path) -> Path:
    remote = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _git(work, "config", "commit.gpgsign", "false")
    (work / ".gitignore").write_text("reports/*\n", encoding="utf-8")
    (work / "README.md").write_text("x\n", encoding="utf-8")
    _git(work, "add", "--", ".gitignore", "README.md")
    _git(work, "commit", "-q", "-m", "init")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-q", "origin", "main")
    _git(work, "checkout", "-q", "-b", BRANCH)
    _git(work, "push", "-q", "origin", BRANCH)
    return work


def _pub(number: int = 7, head: str = BRANCH) -> dict[str, object]:
    return {
        "repo": "Org/work",
        "number": number,
        "url": f"https://github.com/Org/work/pull/{number}",
        "label": f"Org/work#{number}",
        "head": head,
        "head_sha": "abcdef0123456789",
    }


def test_layout_is_created_when_absent(tmp_path: Path) -> None:
    made = rp.ensure_layout(tmp_path)
    rels = {str(p.relative_to(tmp_path)) for p in made}
    assert rels == {
        "reports/gmp",
        "reports/end-session/session-handoff",
        "reports/end-session/governance-handoff",
    }
    assert all(p.is_dir() for p in made)
    # idempotent
    assert rp.ensure_layout(tmp_path) == made


def test_session_handoff_is_written_committed_alone_and_pushed(clone: Path) -> None:
    (clone / "unrelated.txt").write_text("staged by someone else\n", encoding="utf-8")
    _git(clone, "add", "--", "unrelated.txt")

    path, result = rp.publish_session_handoff(
        clone,
        _pub(),
        ["publication: 7", "objective: ship it", "completed:", "  - tests green"],
        session_id="s1",
        agent_id="claude-code",
    )

    assert result.status == "pushed", result
    assert path.parent == clone / "reports" / "end-session" / "session-handoff"
    assert path.name.endswith("-pr7-abcdef012345.md")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Session handoff — Org/work#7\n")
    assert "**objective:** ship it" in text and "## Completed" in text
    assert "- tests green" in text and text.endswith("\n") and not text.endswith("\n\n")

    rel = str(path.relative_to(clone))
    assert _git(clone, "show", "--name-only", "--format=", "HEAD") == rel
    assert _git(clone, "rev-parse", f"origin/{BRANCH}") == _git(clone, "rev-parse", "HEAD")
    # The foreign staged file was not scooped into the report commit.
    assert _git(clone, "diff", "--cached", "--name-only") == "unrelated.txt"


def test_governance_handoff_lands_in_its_own_folder(clone: Path) -> None:
    path, result = rp.publish_governance_handoff(
        clone, _pub(), ["environment friction:", "  - proxy 403"]
    )
    assert result.ok, result
    assert path.parent == clone / "reports" / "end-session" / "governance-handoff"


def test_republishing_identical_report_is_unchanged(clone: Path) -> None:
    rp.publish_session_handoff(clone, _pub(), ["status: done"])
    head = _git(clone, "rev-parse", "HEAD")
    # Same content (timestamp aside) on the same day overwrites the same file.
    path = next((clone / "reports" / "end-session" / "session-handoff").iterdir())
    result = rp.publish(clone, [path], message="noop", expected_branch=BRANCH)
    assert result.status == "unchanged"
    assert _git(clone, "rev-parse", "HEAD") == head


def test_refuses_branch_other_than_pr_head(clone: Path) -> None:
    path, result = rp.publish_session_handoff(clone, _pub(head="someone/else"), ["x: y"])
    assert result.status == "skipped"
    assert "PR head is someone/else" in result.detail
    assert path.is_file()  # written, not committed
    assert _git(clone, "log", "-1", "--format=%s") == "init"


def test_refuses_default_branch(clone: Path) -> None:
    _git(clone, "checkout", "-q", "main")
    _, result = rp.publish_session_handoff(clone, _pub(head=""), ["x: y"])
    assert result.status == "skipped" and "default branch main" in result.detail


def test_rejected_push_keeps_commit_and_never_forces(clone: Path, tmp_path: Path) -> None:
    other = tmp_path / "other"
    subprocess.run(
        ["git", "clone", "-q", "-b", BRANCH, str(tmp_path / "origin.git"), str(other)], check=True
    )
    _git(other, "config", "user.email", "o@example.com")
    _git(other, "config", "user.name", "o")
    (other / "moved.txt").write_text("remote moved\n", encoding="utf-8")
    _git(other, "add", "--", "moved.txt")
    _git(other, "commit", "-q", "-m", "remote moved")
    _git(other, "push", "-q", "origin", BRANCH)
    remote_tip = _git(other, "rev-parse", "HEAD")

    _, result = rp.publish_session_handoff(clone, _pub(), ["x: y"])
    assert result.status == "committed"
    assert "never force" in result.detail
    assert _git(other, "ls-remote", "origin", BRANCH).split()[0] == remote_tip


@pytest.mark.parametrize(("mode", "status"), [("write", "written"), ("commit", "committed")])
def test_publish_mode_env(
    clone: Path, monkeypatch: pytest.MonkeyPatch, mode: str, status: str
) -> None:
    monkeypatch.setenv(rp.PUBLISH_ENV, mode)
    _, result = rp.publish_governance_handoff(clone, _pub(), ["x: y"])
    assert result.status == status
    assert _git(clone, "rev-parse", f"origin/{BRANCH}") == _git(clone, "rev-parse", "main")


def test_not_a_git_tree_is_skipped_but_written(tmp_path: Path) -> None:
    path, result = rp.publish_session_handoff(tmp_path, _pub(), ["x: y"])
    assert result.status == "skipped" and path.is_file()


def test_filename_must_be_bare_markdown(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        rp.write_report(tmp_path, rp.ReportKind.GMP, "../escape.md", "x")


def test_cli_dirs(tmp_path: Path) -> None:
    assert rp.main(["dirs", "--workspace", str(tmp_path)]) == 0
    assert (tmp_path / "reports" / "gmp").is_dir()


# --- Callers -------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_MEM = REPO_ROOT / "environment" / "agents" / "adapters" / "claude-code" / "memory"


def _load_file(name: str, path: Path):  # noqa: ANN202 - test helper
    import importlib.util
    import sys

    if str(CLAUDE_MEM) not in sys.path:
        sys.path.insert(0, str(CLAUDE_MEM))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses resolve annotations through it
    spec.loader.exec_module(module)
    return module


def test_hook_glue_publishes_and_announces(clone: Path) -> None:
    pp = _load_file("l9_test_post_publish", CLAUDE_MEM / "post_publish.py")
    line = pp.publish_report("publish_session_handoff", clone, _pub(), ["status: done"])
    assert line.startswith("• report pushed @ ")
    assert "reports/end-session/session-handoff/" in line


def test_hook_glue_is_fail_open_and_loud(tmp_path: Path) -> None:
    pp = _load_file("l9_test_post_publish", CLAUDE_MEM / "post_publish.py")
    line = pp.publish_report("no_such_publisher", tmp_path, _pub(), ["x: y"])
    assert line.startswith("• report NOT published (AttributeError")


def test_gmp_executor_writes_into_reports_gmp(tmp_path: Path) -> None:
    executor = _load_file("l9_test_gmp_executor", REPO_ROOT / "workflows" / "gmp_executor.py")
    gmp = executor.GMPExecutor(tmp_path)
    gmp.state = executor.GMPState(
        gmp_id="GMP-130",
        tier="RUNTIME",
        task="Route reports into folders",
        started_at="2026-11-02T00:00:00",
        current_step=executor.STEP_ORDER[0],
        todo_plan=[{"id": "T1", "file": "a.py", "action": "Replace", "description": "x"}],
    )
    path = gmp._write_local_report()
    assert path == tmp_path / "reports" / "gmp" / "GMP-130-route-reports-into-folders.md"
    assert path.read_text(encoding="utf-8").startswith("# GMP-130\n")
    # The next id sees reports/gmp/.
    assert gmp._next_gmp_id() == "GMP-131"


# --- Agent-authored GMP reports ---------------------------------------------------


def _report(where: Path, name: str = "GMP-Report-001-GAR-Projection-Binding.md") -> Path:
    where.mkdir(parents=True, exist_ok=True)
    path = where / name
    path.write_text("**ID:** GMP-001 | **Task:** x\n\n## TODO PLAN\n", encoding="utf-8")
    return path


def test_scratch_gmp_report_is_placed_and_committed_without_open_pr(
    clone: Path, tmp_path: Path
) -> None:
    scratch = _report(tmp_path / "scratchpad")
    assert rp.main(["gmp", "--workspace", str(clone), str(scratch)]) == 0
    dest = clone / "reports" / "gmp" / scratch.name
    assert dest.is_file() and scratch.is_file()  # scratch outside the clone is left alone
    rel = f"reports/gmp/{scratch.name}"
    assert _git(clone, "show", "--name-only", "--format=", "HEAD") == rel
    # No open PR for this branch: committed, never a first-publication push.
    assert _git(clone, "rev-parse", f"origin/{BRANCH}") == _git(clone, "rev-parse", "main")


def test_gmp_report_is_pushed_when_branch_has_open_pr(clone: Path) -> None:
    summary = clone / ".l9" / "pr" / "pr-summary.json"
    summary.parent.mkdir(parents=True)
    summary.write_text(json.dumps({"number": 9, "repo": "Org/work", "head": BRANCH}), "utf-8")
    legacy = _report(clone / "reports")  # legacy root location inside the clone
    paths, result = rp.publish_gmp_report(clone, [legacy])
    assert result.status == "pushed", result
    assert paths == [clone / "reports" / "gmp" / legacy.name]
    assert not legacy.exists()  # no second, untracked copy left in the clone
    assert _git(clone, "rev-parse", f"origin/{BRANCH}") == _git(clone, "rev-parse", "HEAD")


def test_gmp_cli_refuses_non_gmp_markdown(clone: Path, tmp_path: Path) -> None:
    other = tmp_path / "notes.md"
    other.write_text("x\n", encoding="utf-8")
    assert rp.main(["gmp", "--workspace", str(clone), str(other)]) == 2
