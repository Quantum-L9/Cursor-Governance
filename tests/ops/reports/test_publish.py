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


def _local(clone: Path, kind: str) -> Path:
    return clone / ".git" / "l9-reports" / "end-session" / kind


def test_session_handoff_is_a_pr_comment_and_never_committed(clone: Path, github) -> None:  # noqa: ANN001
    (clone / "unrelated.txt").write_text("staged by someone else\n", encoding="utf-8")
    _git(clone, "add", "--", "unrelated.txt")
    head, remote = _git(clone, "rev-parse", "HEAD"), _git(clone, "rev-parse", f"origin/{BRANCH}")

    path, result = rp.publish_session_handoff(
        clone,
        _pub(),
        ["publication: 7", "objective: ship it", "completed:", "  - tests green"],
        session_id="s1",
        agent_id="claude-code",
        transport=github,
    )

    assert result.status == "delivered" and result.ok, result
    assert path.parent == _local(clone, "session-handoff")
    assert path.name.endswith("-pr7-abcdef012345.md")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Session handoff — Org/work#7\n")
    assert "**objective:** ship it" in text and "## Completed" in text
    assert "- tests green" in text and text.endswith("\n") and not text.endswith("\n\n")
    # The PR head and the work tree are untouched: no commit, no push, no file.
    assert _git(clone, "rev-parse", "HEAD") == head
    assert _git(clone, "ls-remote", "origin", BRANCH).split()[0] == remote
    assert not (clone / "reports").exists()
    assert _git(clone, "status", "--porcelain") == "A  unrelated.txt"
    # Delivered as the PR's one handoff comment.
    [comment] = github.thread("Org/work", 7)
    assert comment["body"].startswith("<!-- l9-handoff:session-handoff:org/work#7 -->\n")
    assert "**objective:** ship it" in comment["body"]
    assert result.urls == (comment["html_url"],)


def test_republishing_the_same_pr_edits_its_comment(clone: Path, github) -> None:  # noqa: ANN001
    rp.publish_session_handoff(clone, _pub(), ["status: first"], transport=github)
    rp.publish_session_handoff(clone, _pub(), ["status: second"], transport=github)
    [comment] = github.thread("Org/work", 7)
    assert "second" in comment["body"] and "first" not in comment["body"]


def test_governance_handoff_goes_to_the_friction_intake_not_the_pr(
    clone: Path,
    github,  # noqa: ANN001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("L9_FRICTION_INTAKE_REPO", "Org/governance")
    head = _git(clone, "rev-parse", "HEAD")
    friction = [{"id": "proxy-403", "section": "environment friction", "detail": "403"}]

    path, result = rp.publish_governance_handoff(
        clone,
        _pub(),
        ["environment friction:", "  - proxy-403 — detail: 403"],
        session_id="s1",
        friction=friction,
        transport=github,
    )

    assert result.status == "delivered", result
    assert path.parent == _local(clone, "governance-handoff")
    [issue] = github.issues["Org/governance"]
    assert issue["title"] == "[session-friction] proxy-403"
    assert result.urls == (issue["html_url"],)
    assert github.thread("Org/work", 7) == []  # nothing on the consumer PR
    assert _git(clone, "rev-parse", "HEAD") == head


def test_handoff_never_moves_the_pr_head_with_unpublished_work_ahead(
    clone: Path,
    github,  # noqa: ANN001
) -> None:
    (clone / "feature.py").write_text("x = 1\n", encoding="utf-8")
    _git(clone, "add", "--", "feature.py")
    _git(clone, "commit", "-q", "-m", "unpublished work")
    head = _git(clone, "rev-parse", "HEAD")
    _, result = rp.publish_session_handoff(clone, _pub(), ["status: done"], transport=github)
    assert result.status == "delivered"
    assert _git(clone, "rev-parse", "HEAD") == head
    assert _git(clone, "rev-parse", f"origin/{BRANCH}") == _git(clone, "rev-parse", "main")


def test_unreachable_github_is_reported_not_raised(clone: Path, github) -> None:  # noqa: ANN001
    github.refuse.add("Org/work")
    path, result = rp.publish_session_handoff(clone, _pub(), ["x: y"], transport=github)
    assert result.status == "failed" and not result.ok
    assert "PR comment failed" in result.detail
    assert path.is_file()  # the local copy is kept


@pytest.mark.parametrize(("mode", "status"), [("write", "written"), ("commit", "committed")])
def test_gmp_publish_mode_env(
    clone: Path, monkeypatch: pytest.MonkeyPatch, mode: str, status: str
) -> None:
    monkeypatch.setenv(rp.PUBLISH_ENV, mode)
    report = rp.write_report(clone, rp.ReportKind.GMP, "GMP-Report-001-Mode.md", "# GMP\n")
    result = rp.publish(clone, [report], message="gmp", expected_branch=BRANCH)
    assert result.status == status
    assert _git(clone, "rev-parse", f"origin/{BRANCH}") == _git(clone, "rev-parse", "main")


def test_outside_a_git_tree_the_local_copy_lands_under_dot_l9(tmp_path: Path, github) -> None:  # noqa: ANN001
    path, result = rp.publish_session_handoff(tmp_path, _pub(), ["x: y"], transport=github)
    assert result.status == "delivered"
    assert path.parent == tmp_path / ".l9" / "reports" / "end-session" / "session-handoff"


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


def test_hook_glue_delivers_and_announces(
    clone: Path,
    github,  # noqa: ANN001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ops.reports import handoff_delivery

    monkeypatch.setattr(handoff_delivery, "GhApi", lambda: github)
    pp = _load_file("l9_test_post_publish", CLAUDE_MEM / "post_publish.py")
    line = pp.publish_report("publish_session_handoff", clone, _pub(), ["status: done"])
    assert line.startswith("• report delivered: ")
    assert ".git/l9-reports/end-session/session-handoff/" in line
    assert github.thread("Org/work", 7)[0]["html_url"] in line


def test_hook_glue_turns_a_governance_brief_into_intake_items(
    clone: Path,
    github,  # noqa: ANN001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ops.reports import handoff_delivery

    monkeypatch.setattr(handoff_delivery, "GhApi", lambda: github)
    monkeypatch.setenv("L9_FRICTION_INTAKE_REPO", "Org/governance")
    pp = _load_file("l9_test_post_publish", CLAUDE_MEM / "post_publish.py")
    brief = {
        "environment_friction": [{"item": "Proxy 403", "detail": "blocked"}],
        "workarounds": [{"item": "proxy-403", "workaround": "used REST"}],
    }
    line = pp.publish_report(
        "publish_governance_handoff", clone, _pub(), ["x: y"], session_id="s9", brief=brief
    )
    assert line.startswith("• report delivered: "), line
    [issue] = github.issues["Org/governance"]
    [occurrence] = github.thread("Org/governance", issue["number"])
    assert "Workaround: used REST" in occurrence["body"] and "Session: s9" in occurrence["body"]


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
    assert path == tmp_path / "reports" / "gmp" / "GMP-Report-130-Route-reports-into-folders.md"
    assert path.read_text(encoding="utf-8").startswith("# GMP-130\n")
    # The next id sees reports/gmp/.
    assert gmp._next_gmp_id() == "GMP-131"


# --- Repository-declared GMP report folder ----------------------------------------

ODOO_ORIGIN = "https://github.com/cryptoxdog/IB-Odoo_19.git"
ODOO_GMP_DIR = Path("docs") / "reports" / "gmp-reports"


@pytest.fixture()
def odoo_clone(tmp_path: Path) -> Path:
    """A clone whose origin the real publish-authority registry gives a gmp_report_dir."""
    work = tmp_path / "IB-Odoo_19"
    subprocess.run(["git", "init", "-q", "-b", "feat/x", str(work)], check=True)
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "config", "user.name", "t")
    _git(work, "config", "commit.gpgsign", "false")
    _git(work, "remote", "add", "origin", ODOO_ORIGIN)
    (work / "README.md").write_text("x\n", encoding="utf-8")
    _git(work, "add", "--", "README.md")
    _git(work, "commit", "-q", "-m", "init")
    return work


def test_declared_gmp_report_dir_is_used(odoo_clone: Path) -> None:
    from ops.reports import gmp

    assert gmp.report_rel(odoo_clone) == ODOO_GMP_DIR
    assert rp.report_dir(odoo_clone, rp.ReportKind.GMP) == odoo_clone / ODOO_GMP_DIR
    # Handoff folders keep the shared layout.
    assert rp.report_dir(odoo_clone, rp.ReportKind.SESSION_HANDOFF) == (
        odoo_clone / "reports" / "end-session" / "session-handoff"
    )


def test_undeclared_repository_keeps_reports_gmp(clone: Path) -> None:
    from ops.reports import gmp

    assert gmp.report_rel(clone) == Path("reports") / "gmp"


def test_next_gmp_id_scans_the_declared_dir(odoo_clone: Path) -> None:
    from ops.reports import gmp

    _report(odoo_clone / ODOO_GMP_DIR, "GMP-Report-358-Earlier-work.md")
    assert gmp.next_gmp_number(odoo_clone, floor=129) == 359


def test_gmp_executor_writes_and_commits_into_the_declared_dir(
    odoo_clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GMP_DRY_RUN", raising=False)
    executor = _load_file(
        "l9_test_gmp_executor_declared", REPO_ROOT / "workflows" / "gmp_executor.py"
    )
    (odoo_clone / "a.py").write_text("x = 1\n", encoding="utf-8")
    runner = executor.GMPExecutor(odoo_clone)
    runner.authorized = True
    runner.commit_when_done = True
    runner.state = executor.GMPState(
        gmp_id=runner._next_gmp_id(),
        tier="RUNTIME",
        task="Declared folder",
        started_at="2026-11-11T00:00:00",
        current_step=executor.STEP_ORDER[0],
        todo_plan=[{"id": "T1", "file": "a.py", "action": "Insert", "description": "x"}],
    )
    assert runner._step_generate_report().success
    rel = (ODOO_GMP_DIR / "GMP-Report-129-Declared-folder.md").as_posix()
    assert runner.state.report_path == rel
    assert runner._step_commit_gate().output == "Committed"
    committed = _git(odoo_clone, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert sorted(committed) == sorted(["a.py", rel])
    assert not (odoo_clone / "reports").exists()


# --- Agent-authored GMP reports ---------------------------------------------------


VALID_GMP = (
    "**ID:** GMP-001 | **Task:** GAR projection binding | **Tier:** RUNTIME_TIER | "
    "**Date:** 2026-11-02 | **Status:** ✅ COMPLETE\n\n"
    + "".join(
        f"## {s}\n\nx\n\n"
        for s in (
            "TODO PLAN",
            "PHASES",
            "CHANGES",
            "TODO → CHANGE MAP",
            "VALIDATION",
            "VERIFICATION",
            "DECLARATION",
        )
    )
)


def _report(where: Path, name: str = "GMP-Report-001-GAR-Projection-Binding.md") -> Path:
    where.mkdir(parents=True, exist_ok=True)
    path = where / name
    path.write_text(VALID_GMP, encoding="utf-8")
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


def test_misnamed_gmp_report_is_refused_and_left_in_place(clone: Path, tmp_path: Path) -> None:
    bad = tmp_path / "GMP_report_two.md"
    bad.write_text("any content is fine\n", encoding="utf-8")
    assert rp.main(["gmp", "--workspace", str(clone), str(bad)]) == 2
    assert not (clone / "reports" / "gmp" / bad.name).exists()


def test_content_is_free_only_the_name_is_checked(clone: Path, tmp_path: Path) -> None:
    from ops.reports import gmp

    free = tmp_path / gmp.report_name(3, "Free form notes!")
    assert free.name == "GMP-Report-003-Free-form-notes.md"
    free.write_text("no header, no sections\n", encoding="utf-8")
    assert gmp.name_error(free) == ""
    assert rp.main(["gmp", "--workspace", str(clone), str(free)]) == 0
    assert (clone / "reports" / "gmp" / free.name).is_file()


def test_next_gmp_id_is_shared_by_rule_and_executor(tmp_path: Path, capsys) -> None:  # noqa: ANN001
    from ops.reports import gmp

    assert gmp.next_gmp_number(tmp_path) == 1
    _report(tmp_path / "reports" / "gmp")  # GMP-Report-001
    (tmp_path / "reports" / "GMP-140-legacy.md").write_text("x\n", encoding="utf-8")
    assert rp.main(["next-gmp-id", "--workspace", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "GMP-141"
    assert gmp.next_gmp_number(tmp_path, floor=129) == 141


@pytest.mark.parametrize("bad", ["README.md", "reports", "reports/../README.md", "/etc/hostname"])
def test_publish_refuses_anything_but_a_report_file(clone: Path, bad: str) -> None:
    (clone / "reports").mkdir(exist_ok=True)
    head = _git(clone, "rev-parse", "HEAD")
    result = rp.publish(clone, [Path(bad)], message="x", expected_branch=BRANCH)
    assert result.status == "failed" and "not a report file under reports/" in result.detail
    assert _git(clone, "rev-parse", "HEAD") == head
    assert _git(clone, "diff", "--cached", "--name-only") == ""


# --- L9_META: reports adopt the consumer's header convention (contract C-18) ---

_CONSUMER_HEADER = (
    "<!-- L9_META\n"
    "l9_schema: 1\n"
    "origin: engine-specific\n"
    "engine: graph\n"
    "layer: [reports]\n"
    "tags: [gap-analysis]\n"
    "owner: engine-team\n"
    "status: active\n"
    "/L9_META -->\n"
)


def _expected_header(tag: str) -> str:
    return (
        "<!-- L9_META\nl9_schema: 1\norigin: engine-specific\nengine: graph\n"
        f"layer: [reports]\ntags: [{tag}]\nowner: engine-team\nstatus: active\n/L9_META -->\n\n"
    )


def test_tracked_reports_copy_the_sibling_reports_l9_meta_header(clone: Path) -> None:
    sibling = clone / "reports" / "GAP-ANALYSIS.md"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    sibling.write_text(_CONSUMER_HEADER + "\n# Gap analysis\n", encoding="utf-8")

    gmp = rp.write_report(clone, rp.ReportKind.GMP, "GMP-Report-001-x.md", "# GMP report — x\n")
    session = rp.write_report(clone, rp.ReportKind.SESSION_HANDOFF, "x.md", "# Session handoff\n")

    # The consumer's injector form: header, one blank line, then the report.
    assert gmp.read_text(encoding="utf-8").startswith(
        _expected_header("gmp-report") + "# GMP report — x\n"
    )
    assert session.read_text(encoding="utf-8").startswith(
        _expected_header("session-handoff") + "# Session handoff\n"
    )


def test_delivered_handoff_copy_is_untracked_so_gets_no_l9_meta(clone: Path, github) -> None:  # noqa: ANN001
    sibling = clone / "reports" / "GAP-ANALYSIS.md"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    sibling.write_text(_CONSUMER_HEADER + "\n# Gap analysis\n", encoding="utf-8")
    path, _ = rp.publish_session_handoff(clone, _pub(), ["status: done"], transport=github)
    assert path.read_text(encoding="utf-8").startswith("# Session handoff — Org/work#7\n")


def test_header_convention_falls_back_to_tracked_markdown(clone: Path) -> None:
    (clone / "docs").mkdir()
    (clone / "docs" / "GUIDE.md").write_text(_CONSUMER_HEADER + "\n# Guide\n", encoding="utf-8")
    _git(clone, "add", "--", "docs/GUIDE.md")
    _git(clone, "commit", "-q", "-m", "docs")

    path = rp.write_report(clone, rp.ReportKind.SESSION_HANDOFF, "x.md", "# Session handoff\n")

    assert path.read_text(encoding="utf-8").startswith(_expected_header("session-handoff"))


def test_repository_without_l9_meta_gets_no_header(clone: Path) -> None:
    # README.md exists but carries no header: nothing is invented.
    path = rp.write_report(clone, rp.ReportKind.SESSION_HANDOFF, "x.md", "# Session handoff\n")

    text = path.read_text(encoding="utf-8")
    assert "L9_META" not in text and text.startswith("# Session handoff")


@pytest.mark.parametrize(
    "bad",
    [
        _CONSUMER_HEADER.replace("engine: graph\n", ""),  # a field missing
        _CONSUMER_HEADER.replace("origin", "source"),  # a field renamed
        "\n" + _CONSUMER_HEADER,  # not at the top of the file
    ],
)
def test_malformed_sibling_header_is_not_copied(tmp_path: Path, bad: str) -> None:
    sibling = tmp_path / "reports" / "OLD.md"
    sibling.parent.mkdir(parents=True)
    sibling.write_text(bad + "\n# Old\n", encoding="utf-8")

    path = rp.write_report(tmp_path, rp.ReportKind.SESSION_HANDOFF, "x.md", "# Report\n")

    assert path.read_text(encoding="utf-8") == "# Report\n"


def test_report_that_already_has_a_header_is_not_given_a_second(tmp_path: Path) -> None:
    sibling = tmp_path / "reports" / "OLD.md"
    sibling.parent.mkdir(parents=True)
    sibling.write_text(_CONSUMER_HEADER + "\n# Old\n", encoding="utf-8")
    own = _CONSUMER_HEADER.replace("gap-analysis", "authored") + "\n# Mine\n"

    path = rp.write_report(tmp_path, rp.ReportKind.GMP, "GMP-Report-001-x.md", own)

    assert path.read_text(encoding="utf-8") == own
    assert path.read_text(encoding="utf-8").count("<!-- L9_META") == 1


def test_rewriting_a_report_keeps_the_convention_not_its_own_header(tmp_path: Path) -> None:
    # The file being written is excluded from discovery, so a rewrite never
    # copies a stale header from the previous version of itself.
    first = rp.write_report(tmp_path, rp.ReportKind.SESSION_HANDOFF, "x.md", "# One\n")
    assert first.read_text(encoding="utf-8") == "# One\n"
    first.write_text(_CONSUMER_HEADER + "\n# One\n", encoding="utf-8")

    again = rp.write_report(tmp_path, rp.ReportKind.SESSION_HANDOFF, "x.md", "# Two\n")

    assert again.read_text(encoding="utf-8") == "# Two\n"
