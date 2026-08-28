"""pr-train-v1 is a LANGGRAPH_RUNTIME: open train, remediator, then /ff at open_pr=0."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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
    group_slices,
    resolve_ff_clone,
    run_pr_train,
)

DAG_SOURCE = REPO_ROOT / "workflows" / "dags" / "pr_train_dag.py"
COMMAND = REPO_ROOT / "commands" / "pr-train.md"


def test_graph_kind_is_langgraph_not_session():
    result = classify(DAG_SOURCE)
    assert result["status"] == "PASS"
    assert result["graph_kind"] == "LANGGRAPH_RUNTIME"


def test_langgraph_source_validator_passes():
    result = validate_langgraph(DAG_SOURCE)
    assert result["status"] == "PASS", result


def test_not_registered_as_session_dag():
    import workflows.dags  # noqa: F401
    from workflows.session.registry import get_session_dag

    assert get_session_dag("pr-train-v1") is None


def test_command_is_thin_trigger():
    result = validate_command(COMMAND, GRAPH_ID)
    assert result["status"] == "PASS", result
    text = COMMAND.read_text(encoding="utf-8")
    assert "l9-pr-remediation" in text
    assert "/ff" in text
    assert "open_pr" in text
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
    monkeypatch.setattr(mod, "authorize_merge", lambda *_a, **_k: None)

    def remediate(_state):
        return {"open_pr_count": 2}

    def ff(_clone):
        raise AssertionError("/ff must not run while open_pr!=0")

    state = run_pr_train(
        tmp_path,
        execute=True,
        fetch=False,
        remediate_fn=remediate,
        ff_fn=ff,
    )
    assert state.ff_ran is False
    assert state.ff_skipped == "open_pr=2"
    assert state.open_pr_count == 2


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


def test_discovery_boundary_exports_pr_train():
    import workflows.dags

    assert workflows.dags.PR_TRAIN_DAG is not None
    assert hasattr(workflows.dags.pr_train_dag, "ff_node")
    assert not hasattr(workflows.dags.pr_train_dag, "compliance_node")
