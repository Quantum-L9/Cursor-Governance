"""pr-train-v1 is a LANGGRAPH_RUNTIME: open train, remediator, then /ff at open_pr=0."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "skills" / "l9-dag-authoring" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from classify_graph_kind import classify  # noqa: E402
from validate_command_trigger import validate as validate_command  # noqa: E402
from validate_langgraph_source import validate as validate_langgraph  # noqa: E402

from workflows.dags.pr_train_dag import (  # noqa: E402
    GRAPH_ID,
    NovelCommit,
    campaign_halt,
    collect_remainder_slice,
    commits_must_colocate,
    default_extract,
    filter_slices_against_tip,
    github_repo_slug,
    group_slices,
    is_empty_cherry_pick,
    order_slice,
    parse_merge_tree_name_only,
    probe_cherry_conflicts,
    probe_sha_conflicts,
    resolve_ff_clone,
    run_pr_train,
    shares_generated_clobber,
)

DAG_SOURCE = REPO_ROOT / "workflows" / "dags" / "pr_train_dag.py"
COMMAND = REPO_ROOT / "commands" / "pr-train.md"


def _git_c(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
    )


def _init_git(repo: Path) -> None:
    subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
    _git_c(repo, "config", "user.email", "pr-train@test")
    _git_c(repo, "config", "user.name", "pr-train")


def _rev_parse(repo: Path) -> str:
    return _git_c(repo, "rev-parse", "HEAD").stdout.strip()


def _commit_file(repo: Path, rel: str, content: str, message: str) -> str:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git_c(repo, "add", rel)
    _git_c(repo, "commit", "-m", message)
    return _rev_parse(repo)


def _commit_on_branch(repo: Path, branch: str, rel: str, content: str, message: str) -> str:
    _git_c(repo, "checkout", "-b", branch)
    return _commit_file(repo, rel, content, message)


def _colocate(repo: Path):
    def must(left: NovelCommit, right: NovelCommit) -> bool:
        return commits_must_colocate(repo, left, right)

    return must


def test_graph_kind_is_langgraph_not_session():
    result = classify(DAG_SOURCE)
    assert result["status"] == "PASS"
    assert result["graph_kind"] == "LANGGRAPH_RUNTIME"


def test_langgraph_source_validator_passes():
    result = validate_langgraph(DAG_SOURCE)
    assert result["status"] == "PASS", result


def test_not_registered_as_session_dag():
    from workflows import dags  # noqa: F401
    from workflows.session.registry import get_session_dag

    assert get_session_dag("pr-train-v1") is None


def test_command_is_thin_trigger():
    result = validate_command(COMMAND, GRAPH_ID)
    assert result["status"] == "PASS", result
    text = COMMAND.read_text(encoding="utf-8")
    assert "l9-pr-remediation" in text
    assert "/ff" in text
    assert "open_pr" in text
    assert "awaiting" in text
    assert "--ff-only" in text
    assert "--all-refs" in text
    assert ".cursor-commands/workflows/dags" not in text


def test_overlapping_paths_stay_one_slice():
    commits = [
        NovelCommit("aaa", ("ops/a.py",), "feat/x"),
        NovelCommit("bbb", ("ops/a.py", "ops/b.py"), "feat/x"),
        NovelCommit("ccc", ("ops/b.py",), "feat/x"),
    ]
    slices = group_slices(commits)
    assert len(slices) == 1
    assert [c.sha for c in slices[0]] == ["aaa", "bbb", "ccc"]


def test_disjoint_paths_are_separate_slices():
    commits = [
        NovelCommit("aaa", ("ops/a.py",), "feat/x"),
        NovelCommit("bbb", ("docs/b.md",), "feat/x"),
    ]
    slices = group_slices(commits)
    assert len(slices) == 2


def test_generated_prefix_colocates_distinct_filenames():
    left = NovelCommit("aaa", ("environment/generated/llm-rules/02-slash-commands.md",), "feat/x")
    right = NovelCommit("bbb", ("environment/generated/llm-rules/99-no-auto-commit.md",), "feat/x")
    assert shares_generated_clobber(left, right)
    slices = group_slices([left, right], must_colocate=shares_generated_clobber)
    assert len(slices) == 1


def test_generated_prefix_does_not_union_unrelated_corpora():
    left = NovelCommit("aaa", ("commands/COMMANDS_MANIFEST.yaml",), "feat/x")
    right = NovelCommit("bbb", ("skills/AUTONOMY_MANIFEST.yaml",), "feat/x")
    assert not shares_generated_clobber(left, right)
    slices = group_slices([left, right], must_colocate=shares_generated_clobber)
    assert len(slices) == 2


def test_merge_tree_callback_unions_disjoint_paths():
    commits = [
        NovelCommit("aaa", ("ops/a.py",), "feat/x"),
        NovelCommit("bbb", ("ops/renamed.py",), "feat/x"),
    ]
    slices = group_slices(commits, must_colocate=lambda *_a: True)
    assert len(slices) == 1


def test_parse_merge_tree_unknown_is_none():
    assert parse_merge_tree_name_only("", 0) == []
    assert parse_merge_tree_name_only("ops/a.py\n", 1) == ["ops/a.py"]
    assert parse_merge_tree_name_only("fatal: ...", 128) is None


def test_unknown_probe_fail_closes_into_one_slice(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    a = _commit_file(repo, "ops/a.py", "a\n", "a")
    b = _commit_file(repo, "docs/b.md", "b\n", "b")
    monkeypatch.setattr(mod, "probe_sha_conflicts", lambda *_a, **_k: None)
    left = NovelCommit(a, ("ops/a.py",), "feat/x")
    right = NovelCommit(b, ("docs/b.md",), "feat/x")
    assert commits_must_colocate(repo, left, right) is True
    slices = group_slices([left, right], must_colocate=_colocate(repo))
    assert len(slices) == 1


def test_clean_disjoint_commits_stay_two_slices(tmp_path):
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    branch_a = _commit_on_branch(repo, "side-a", "ops/a.py", "a\n", "a")
    _git_c(repo, "checkout", "main")
    branch_b = _commit_on_branch(repo, "side-b", "docs/b.md", "b\n", "b")
    left = NovelCommit(branch_a, ("ops/a.py",), "side-a")
    right = NovelCommit(branch_b, ("docs/b.md",), "side-b")
    assert commits_must_colocate(repo, left, right) is False
    slices = group_slices([left, right], must_colocate=_colocate(repo))
    assert len(slices) == 2


def test_file_vs_directory_merge_tree_unions_one_slice(tmp_path):
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "dira")
    nested = repo / "clash" / "x.py"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("a\n", encoding="utf-8")
    _git_c(repo, "add", "clash/x.py")
    _git_c(repo, "commit", "-m", "dir")
    dir_sha = _rev_parse(repo)
    _git_c(repo, "checkout", "main")
    _git_c(repo, "checkout", "-b", "fileb")
    (repo / "clash").write_text("b\n", encoding="utf-8")
    _git_c(repo, "add", "clash")
    _git_c(repo, "commit", "-m", "file")
    file_sha = _rev_parse(repo)
    left = NovelCommit(dir_sha, ("clash/x.py",), "dira")
    right = NovelCommit(file_sha, ("clash",), "fileb")
    assert set(left.paths) & set(right.paths) == set()
    assert commits_must_colocate(repo, left, right) is True
    slices = group_slices([left, right], must_colocate=_colocate(repo))
    assert len(slices) == 1


def test_campaign_branch_halts_without_override():
    assert campaign_halt("campaign/foo", False)
    assert campaign_halt("campaign/foo", True) is None
    assert campaign_halt("feat/x", False) is None


def test_ff_clone_uses_ssot_off_main(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    ssot = tmp_path / ".cursor-governance"
    ssot.mkdir()
    repo = tmp_path / "wt"
    repo.mkdir()
    assert resolve_ff_clone(repo, "feat/x") == ssot
    assert resolve_ff_clone(repo, "main") == repo


def _inventory(branch: str, refs: list[str]):
    return {
        "branch": branch,
        "head": "deadbeef",
        "unpushed_or_diverged": [{"name": name} for name in refs],
    }


def test_plan_mode_does_not_ff_or_publish(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x"]),
    )
    monkeypatch.setattr(
        mod,
        "load_diagnosis",
        lambda *_a, **_k: {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": ["aaa"],
            "cherry_dup_commits": ["bbb"],
        },
    )
    monkeypatch.setattr(mod, "load_commit_paths", lambda *_a, **_k: ("ops/a.py",))
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )

    def boom(*_a, **_k):
        raise AssertionError("must not publish or ff in plan mode")

    monkeypatch.setattr(mod, "default_publish", boom)
    monkeypatch.setattr(mod, "run_ff", boom)
    monkeypatch.setattr(mod, "authorize_merge", boom)

    state = run_pr_train(tmp_path, execute=False, fetch=False)
    assert state.status == "complete"
    assert state.slices
    assert state.skipped_dup == ["bbb"]
    assert state.skill_dispatch == "l9-pr-remediation"
    assert state.ff_ran is False
    assert "plan only" in state.report


def test_execute_open_then_remediate_then_ff_when_open_pr_zero(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x"]),
    )
    monkeypatch.setattr(
        mod,
        "load_diagnosis",
        lambda *_a, **_k: {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": ["aaa", "ccc"],
            "cherry_dup_commits": [],
        },
    )
    monkeypatch.setattr(
        mod,
        "load_commit_paths",
        lambda _repo, sha: ("ops/a.py",) if sha == "aaa" else ("docs/b.md",),
    )
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )
    monkeypatch.setattr(mod, "authorize_merge", lambda *_a, **_k: None)

    extracted: list[str] = []
    published: list[str] = []
    ff_called: list[Path] = []

    def extract(_repo, commits, _tip, index):
        extracted.append(commits[0]["sha"])
        return str(tmp_path / f"wt-{index}"), f"feat/pr-train-{index}"

    def publish(worktree: str):
        published.append(worktree)
        return {"worktree": worktree, "ok": True}

    def remediate(_state):
        return {"open_pr_count": 0}

    def ff(clone: Path):
        ff_called.append(clone)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    state = run_pr_train(
        tmp_path,
        execute=True,
        fetch=False,
        extract_fn=extract,
        publish_fn=publish,
        remediate_fn=remediate,
        ff_fn=ff,
    )
    assert state.status == "complete"
    assert len(state.slices) == 2
    assert extracted == ["aaa", "ccc"]
    assert len(published) == 2
    assert state.skill_dispatch == "l9-pr-remediation"
    assert state.open_pr_count == 0
    assert state.ff_ran is True
    assert ff_called


def test_ff_skipped_while_open_prs_remain(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(mod, "count_open_prs", lambda *_a, **_k: 2)

    def ff(_clone):
        raise AssertionError("/ff must not run while open_pr!=0")

    state = run_pr_train(tmp_path, ff_only=True, ff_fn=ff)
    assert state.ff_ran is False
    assert state.ff_skipped == "open_pr=2"
    assert state.open_pr_count == 2


def test_execute_without_remediator_halts_and_does_not_authorize(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x"]),
    )
    monkeypatch.setattr(
        mod,
        "load_diagnosis",
        lambda *_a, **_k: {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": ["aaa"],
            "cherry_dup_commits": [],
        },
    )
    monkeypatch.setattr(mod, "load_commit_paths", lambda *_a, **_k: ("ops/a.py",))
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )

    def boom(*_a, **_k):
        raise AssertionError("graph must not authorize merge")

    monkeypatch.setattr(mod, "authorize_merge", boom)
    monkeypatch.setattr(mod, "run_ff", boom)

    def extract(_repo, _commits, _tip, index):
        return str(tmp_path / f"wt-{index}"), f"feat/pr-train-{index}"

    def publish(worktree: str):
        return {"worktree": worktree, "ok": True}

    state = run_pr_train(
        tmp_path,
        execute=True,
        fetch=False,
        extract_fn=extract,
        publish_fn=publish,
    )
    assert state.status == "blocked"
    assert "awaiting l9-pr-remediation" in state.halt_reason
    assert state.merge_authorized is False
    assert state.ff_ran is False
    assert state.opened_prs


def test_execute_empty_train_does_not_authorize_or_remediate(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x"]),
    )
    monkeypatch.setattr(
        mod,
        "load_diagnosis",
        lambda *_a, **_k: {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": [],
            "cherry_dup_commits": ["already"],
        },
    )
    monkeypatch.setattr(mod, "load_commit_paths", lambda *_a, **_k: ())
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )

    def boom(*_a, **_k):
        raise AssertionError("empty train must not authorize merge")

    monkeypatch.setattr(mod, "authorize_merge", boom)

    def remediate(_state):
        raise AssertionError("empty train must not enter remediator")

    state = run_pr_train(
        tmp_path,
        execute=True,
        fetch=False,
        remediate_fn=remediate,
    )
    assert state.status == "complete"
    assert state.slices == []
    assert state.merge_authorized is False
    assert state.skill_dispatch == ""


def test_default_inventory_is_current_branch_only(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    seen: list[str] = []

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x", "feat/foreign"]),
    )

    def diagnose(_repo, ref, *_a, **_k):
        seen.append(ref)
        return {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": [],
            "cherry_dup_commits": [],
        }

    monkeypatch.setattr(mod, "load_diagnosis", diagnose)
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )
    state = run_pr_train(tmp_path, execute=False, fetch=False)
    assert seen == ["feat/x"]
    assert state.unpushed_refs == ["feat/x"]


def test_all_refs_includes_foreign_unpushed(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    seen: list[str] = []
    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x", "feat/foreign"]),
    )

    def diagnose(_repo, ref, *_a, **_k):
        seen.append(ref)
        return {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": [],
            "cherry_dup_commits": [],
        }

    monkeypatch.setattr(mod, "load_diagnosis", diagnose)
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )
    state = run_pr_train(tmp_path, execute=False, fetch=False, all_refs=True)
    assert seen == ["feat/x", "feat/foreign"]
    assert state.unpushed_refs == ["feat/x", "feat/foreign"]


def test_github_slug_refuses_non_github(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    def fake_git(_repo, *args):
        if args[:2] == ("remote", "get-url"):
            return SimpleNamespace(returncode=0, stdout="git@example.com:org/repo\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="no")

    monkeypatch.setattr(mod, "_git", fake_git)
    try:
        github_repo_slug(tmp_path)
    except RuntimeError as exc:
        assert "not GitHub" in str(exc)
    else:
        raise AssertionError("expected refuse")


def test_campaign_halt_skips_remediator_and_ff(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("campaign/x", ["campaign/x"]),
    )

    def remediate(_state):
        raise AssertionError("campaign halt must not dispatch remediator")

    state = run_pr_train(
        tmp_path,
        execute=True,
        fetch=False,
        remediate_fn=remediate,
    )
    assert state.status == "blocked"
    assert "campaign" in state.halt_reason
    assert state.skill_dispatch == ""
    assert state.ff_ran is False


def test_tip_preflight_uses_cherry_pick_not_tree_merge(tmp_path):
    """A unique-file commit on an old base must not skip after the tip squash.

    Tree-merge(tip, sha) conflicts on every file the squash already landed
    because ``sha``'s tree still carries the pre-tip bytes. Cherry-pick only
    applies parent..sha.
    """
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "feature")
    _commit_file(repo, "keep.txt", "feature-edit\n", "ancestral edit")
    unique = _commit_file(repo, "ops/unique.py", "x\n", "unique")
    _git_c(repo, "checkout", "main")
    tip = _commit_file(repo, "keep.txt", "squashed\n", "squash")
    tree = probe_sha_conflicts(repo, tip, unique)
    cherry = probe_cherry_conflicts(repo, tip, unique)
    assert tree, "tree-merge must still see the ancestral keep.txt clash"
    assert cherry == []
    kept, skipped, _skipped_items = filter_slices_against_tip(
        repo, [[{"sha": unique, "paths": ["ops/unique.py"]}]], tip
    )
    assert skipped == []
    assert kept[0][0]["sha"] == unique


def test_tip_preflight_keeps_child_when_parent_stays(tmp_path):
    """A follow-up commit on a kept parent must not probe against the original tip."""
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "dag.py", "v0\n", "base")
    _git_c(repo, "checkout", "-b", "feature")
    parent = _commit_file(repo, "dag.py", "v1\n", "parent")
    child = _commit_file(repo, "dag.py", "v2\n", "child")
    _git_c(repo, "checkout", "main")
    tip = _commit_file(repo, "other.txt", "x\n", "unrelated tip")
    assert probe_cherry_conflicts(repo, tip, child)
    kept, skipped, _skipped_items = filter_slices_against_tip(
        repo,
        [[{"sha": child, "paths": ["dag.py"]}, {"sha": parent, "paths": ["dag.py"]}]],
        tip,
    )
    assert skipped == []
    assert [item["sha"] for item in kept[0]] == [parent, child]


def test_tip_preflight_still_probes_child_on_new_paths(tmp_path):
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "feature")
    parent = _commit_file(repo, "ops/unique.py", "x\n", "parent unique")
    child = _commit_file(repo, "keep.txt", "feature\n", "child clashes tip")
    _git_c(repo, "checkout", "main")
    tip = _commit_file(repo, "keep.txt", "squash\n", "tip squash")
    kept, skipped, _skipped_items = filter_slices_against_tip(
        repo,
        [[{"sha": parent, "paths": ["ops/unique.py"]}, {"sha": child, "paths": ["keep.txt"]}]],
        tip,
    )
    assert skipped == [child]
    assert [item["sha"] for item in kept[0]] == [parent]


def test_remainder_slice_keeps_unique_path_from_tip_conflict(tmp_path):
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "feature")
    (repo / "keep.txt").write_text("feature\n", encoding="utf-8")
    (repo / "ops").mkdir()
    (repo / "ops" / "unique.py").write_text("x\n", encoding="utf-8")
    _git_c(repo, "add", "keep.txt", "ops/unique.py")
    _git_c(repo, "commit", "-m", "mixed")
    mixed = _rev_parse(repo)
    _git_c(repo, "checkout", "main")
    tip = _commit_file(repo, "keep.txt", "squash\n", "tip squash")
    remainder = collect_remainder_slice(
        repo,
        [{"sha": mixed, "paths": ("keep.txt", "ops/unique.py")}],
        tip,
    )
    assert remainder
    assert remainder[0]["mode"] == "remainder"
    assert "ops/unique.py" in remainder[0]["paths"]
    assert "keep.txt" not in remainder[0]["paths"]


def test_extract_remainder_checkouts_unique_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "feature")
    (repo / "keep.txt").write_text("feature\n", encoding="utf-8")
    (repo / "ops").mkdir()
    (repo / "ops" / "unique.py").write_text("x\n", encoding="utf-8")
    _git_c(repo, "add", "keep.txt", "ops/unique.py")
    _git_c(repo, "commit", "-m", "mixed")
    mixed = _rev_parse(repo)
    _git_c(repo, "checkout", "main")
    _commit_file(repo, "keep.txt", "squash\n", "tip squash")
    worktree, _branch = default_extract(
        repo,
        [{"sha": mixed, "paths": ("ops/unique.py",), "mode": "remainder"}],
        "main",
        0,
    )
    assert (Path(worktree) / "ops" / "unique.py").read_text(encoding="utf-8") == "x\n"
    assert (Path(worktree) / "keep.txt").read_text(encoding="utf-8") == "squash\n"
    _git_c(repo, "worktree", "remove", "--force", worktree)


def test_tip_conflict_commit_dropped_clean_stays(tmp_path):
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "clash")
    clash = _commit_file(repo, "docs/plans/x.plan.json", '{"a":1}\n', "clash")
    _git_c(repo, "checkout", "main")
    tip = _commit_file(repo, "docs/plans/x.plan.json", '{"a":2}\n', "tip")
    _git_c(repo, "checkout", "-b", "clean")
    clean = _commit_file(repo, "ops/a.py", "a\n", "clean")
    slices = [
        [{"sha": clash, "paths": ["docs/plans/x.plan.json"]}],
        [{"sha": clean, "paths": ["ops/a.py"]}],
    ]
    kept, skipped, _skipped_items = filter_slices_against_tip(repo, slices, tip)
    assert skipped == [clash]
    assert len(kept) == 1
    assert kept[0][0]["sha"] == clean


def test_stack_base_filters_pending_slices_only(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod
    from workflows.dags.pr_train_dag import PrTrainState, stack_base_node

    seen: list[list[str]] = []

    def fake_filter(_repo, slices, _tip):
        seen.append([item["sha"] for group in slices for item in group])
        return slices, [], []

    monkeypatch.setattr(mod, "filter_slices_against_tip", fake_filter)
    monkeypatch.setattr(
        mod, "load_stack_tip", lambda *_a, **_k: ("origin/main", "1" * 40, "no_open_prs")
    )
    state = PrTrainState(
        repo=str(tmp_path),
        execute=True,
        current_slice=1,
        slices=[[{"sha": "done"}], [{"sha": "pending"}]],
    )
    out = stack_base_node(state)
    assert seen == [["pending"]]
    assert [group[0]["sha"] for group in out["slices"]] == ["done", "pending"]


def test_default_publish_is_git_push_not_make_pr(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        if argv[:2] == ["gh", "pr"]:
            return SimpleNamespace(returncode=0, stdout="358\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    out = mod.default_publish(str(tmp_path / "wt"))
    assert out["ok"] is True
    assert any(argv[:4] == ["git", "-C", str(tmp_path / "wt"), "push"] for argv in calls)
    assert not any(argv[:1] == ["make"] or "record-kernels" in argv for argv in calls)


def test_is_empty_cherry_pick_detects_git_empty_message():
    empty_msg = "The previous cherry-pick is now empty, possibly due to conflict resolution."
    assert is_empty_cherry_pick("", empty_msg)
    assert not is_empty_cherry_pick("", "CONFLICT (content): Merge conflict in AGENTS.md")


def test_extract_skips_empty_cherry_pick_then_keeps_unique(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "readme.md", "v1\n", "base")
    _git_c(repo, "checkout", "-b", "feature")
    empty = _commit_file(repo, "readme.md", "v2\n", "already on tip")
    unique = _commit_file(repo, "ops/unique.py", "x\n", "unique")
    _git_c(repo, "checkout", "main")
    _commit_file(repo, "readme.md", "v2\n", "tip already has v2")
    worktree, branch = default_extract(
        repo,
        [{"sha": empty}, {"sha": unique}],
        "main",
        0,
    )
    assert branch.startswith("feat/pr-train-0-")
    assert Path(worktree).is_dir()
    assert (Path(worktree) / "ops" / "unique.py").read_text(encoding="utf-8") == "x\n"
    _git_c(repo, "worktree", "remove", "--force", worktree)


def test_extract_removes_worktree_on_cherry_pick_abort(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    _commit_file(repo, "keep.txt", "base\n", "base")
    _git_c(repo, "checkout", "-b", "clash")
    clash = _commit_file(repo, "docs/plans/x.plan.json", '{"a":1}\n', "clash")
    _git_c(repo, "checkout", "main")
    _commit_file(repo, "docs/plans/x.plan.json", '{"a":2}\n', "tip")
    with pytest.raises(RuntimeError, match="cherry-pick conflict"):
        default_extract(repo, [{"sha": clash}], "main", 0)
    leftover = list((tmp_path / ".l9" / "gov-worktrees").glob("pr-train-0-*"))
    assert leftover == []
    listed = _git_c(repo, "worktree", "list", "--porcelain").stdout
    assert str(tmp_path / ".l9") not in listed


def test_incomplete_novelty_receipt_halts(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(mod, "load_inventory", lambda *_a, **_k: _inventory("feat/x", ["feat/x"]))
    monkeypatch.setattr(
        mod,
        "load_diagnosis",
        lambda *_a, **_k: {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel": 51,
            "cherry_novel_commits": ["aaa"],
            "merge_commits_unexamined": 0,
            "cherry_dup_commits": [],
        },
    )

    def boom(*_a, **_k):
        raise AssertionError("incomplete receipt must not extract")

    monkeypatch.setattr(mod, "default_extract", boom)
    state = run_pr_train(tmp_path, execute=True, fetch=False)
    assert state.status == "blocked"
    assert "incomplete" in state.halt_reason


def test_order_slice_preserves_ancestry(tmp_path):
    repo = tmp_path / "git"
    repo.mkdir()
    _init_git(repo)
    parent = _commit_file(repo, "a.txt", "1\n", "parent")
    child = _commit_file(repo, "a.txt", "2\n", "child")
    commits = [
        NovelCommit(sha=child, paths=("a.txt",), ref="feat"),
        NovelCommit(sha=parent, paths=("a.txt",), ref="feat"),
    ]
    ordered = order_slice(repo, commits)
    assert [item.sha for item in ordered] == [parent, child]


def test_sibling_stack_halts_to_remediator_without_extract(monkeypatch, tmp_path):
    from workflows.dags import pr_train_dag as mod

    monkeypatch.setattr(
        mod,
        "load_inventory",
        lambda *_a, **_k: _inventory("feat/x", ["feat/x"]),
    )
    monkeypatch.setattr(
        mod,
        "load_diagnosis",
        lambda *_a, **_k: {
            "cherry_available": True,
            "baseline_resolved": True,
            "cherry_novel_commits": ["aaa"],
            "cherry_dup_commits": [],
        },
    )
    monkeypatch.setattr(mod, "load_commit_paths", lambda *_a, **_k: ("ops/a.py",))

    def boom_tip(*_a, **_k):
        raise RuntimeError("sibling open-PR chains target main: #355,#356,#357")

    monkeypatch.setattr(mod, "load_stack_tip", boom_tip)

    def boom(*_a, **_k):
        raise AssertionError("sibling halt must not extract or authorize")

    monkeypatch.setattr(mod, "default_extract", boom)
    monkeypatch.setattr(mod, "authorize_merge", boom)

    state = run_pr_train(tmp_path, execute=True, fetch=False)
    assert state.status == "blocked"
    assert "sibling open-PR" in state.halt_reason
    assert state.skill_dispatch == "l9-pr-remediation"
    assert state.opened_prs == []
    assert state.ff_ran is False


def test_discovery_boundary_exports_pr_train():
    from workflows import dags

    assert dags.PR_TRAIN_DAG is not None
    assert hasattr(dags.pr_train_dag, "ff_node")
    assert not hasattr(dags.pr_train_dag, "compliance_node")
