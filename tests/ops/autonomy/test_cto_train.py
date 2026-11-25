"""cto_train.py: a merge train that defers instead of guessing, and merges only via the executor."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ops" / "autonomy"))

import cto_train  # noqa: E402
from cto_train import (  # noqa: E402
    TrainError,
    TrainRunner,
    classify_file,
    validate_train,
    verify_head,
)

SLUG = "cryptoxdog/IB-Odoo_19"
BASE = "Staging"


def _sha(ch: str) -> str:
    return ch * 40


def _train(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema": "l9.cto-train/v1",
        "campaign": "odoo-pre-go-live",
        "repo": SLUG,
        "base": BASE,
        "prs": [
            {"number": 1, "lane": "A", "proven_head": _sha("a")},
            {"number": 2, "lane": "B", "proven_head": _sha("b")},
            {"number": 3, "lane": "C", "proven_head": _sha("c")},
        ],
        "order": [1, 2, 3],
        "pairs": [],
        "integration_receipt": None,
        "runtime": None,
        "static": [],
        "suite": [],
    }
    data.update(overrides)
    return validate_train(data)


def _view(n: int, sha: str, *, base: str = BASE, ref: str = "", state: str = "open") -> dict:
    return {
        "number": n,
        "state": state,
        "merged": False,
        "mergeable_state": "clean",
        "head": {"sha": sha, "ref": ref or f"feat/{n}"},
        "base": {"ref": base},
    }


class FakeGitHub:
    def __init__(
        self,
        pulls: dict[int, dict],
        *,
        compares: dict[tuple[str, str], str] | None = None,
        boards: dict[int, dict] | None = None,
        refuse: dict[int, str] | None = None,
        unknown_polls: dict[int, int] | None = None,
    ) -> None:
        self.pulls = pulls
        self.compares = compares or {}
        self.boards = boards or {}
        self.refuse = refuse or {}
        self.unknown_polls = dict(unknown_polls or {})
        self.calls: list[tuple] = []

    def pull(self, pr: int) -> dict[str, Any]:
        self.calls.append(("pull", pr))
        view = copy.deepcopy(self.pulls[pr])
        if self.unknown_polls.get(pr, 0) > 0 and view["state"] == "open":
            self.unknown_polls[pr] -= 1
            view["mergeable_state"] = "unknown"
        return view

    def compare(self, base: str, head: str) -> str:
        self.calls.append(("compare", base, head))
        return self.compares.get((base, head), "diverged")

    def open_pulls(self) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(v)
            for v in self.pulls.values()
            if v["state"] == "open" and not v["merged"]
        ]

    def retarget(self, pr: int, base: str) -> None:
        self.calls.append(("retarget", pr, base))
        self.pulls[pr]["base"]["ref"] = base

    def board(self, pr: int) -> dict[str, Any]:
        self.calls.append(("board", pr))
        return self.boards.get(pr, {"board": "merge", "reason": "required checks green"})

    def merge(self, pr: int, head_sha: str, long_lived_bases: tuple[str, ...]) -> dict[str, Any]:
        self.calls.append(("merge", pr, head_sha, long_lived_bases))
        if pr in self.refuse:
            return {
                "rc": 3,
                "record": {"status": "MERGE_PENDING", "reason": self.refuse[pr]},
                "stderr": "",
            }
        view = self.pulls[pr]
        view.update(merged=True, state="closed", merge_commit_sha=_sha("f"))
        return {
            "rc": 0,
            "record": {"status": "MERGED", "method": "merge", "merge_commit_sha": _sha("f")},
            "stderr": "",
        }

    def merges(self) -> list[int]:
        return [c[1] for c in self.calls if c[0] == "merge"]


def _runner(train, gh, tmp_path: Path, **kw: Any) -> TrainRunner:
    kw.setdefault("sleep", lambda s: None)
    return TrainRunner(train, gh, workspace=tmp_path, **kw)


def _three(**view_overrides: dict) -> dict[int, dict]:
    pulls = {1: _view(1, _sha("a")), 2: _view(2, _sha("b")), 3: _view(3, _sha("c"))}
    for n, extra in view_overrides.items():
        pulls[int(n.lstrip("p"))].update(extra)
    return pulls


# --- manifest ------------------------------------------------------------------


def test_plan_reports_order_pairs_and_no_permission() -> None:
    train = _train(pairs=[[3, 2]])
    plan = cto_train.plan(train)
    assert plan["grants_permission"] is False
    assert [o["pr"] for o in plan["order"]] == [1, 2, 3]
    assert plan["pairs"] == [[2, 3]]  # reported in merge order
    assert plan["order"][1]["group"] == [2, 3]


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"order": [1, 2]}, "exactly once"),
        ({"order": [1, 2, 2, 3]}, "appears twice"),
        ({"pairs": [[1, 9]]}, "#9 is not in prs"),
        ({"pairs": [[1, 2], [2, 3]]}, "more than one group"),
        ({"schema": "l9.cto-train/v2"}, "schema"),
        ({"accepted": [{"pr": 9, "head_prefix": "abcdef1", "reason": "x"}]}, "accepted"),
    ],
)
def test_invalid_manifests_are_refused(overrides: dict, fragment: str) -> None:
    with pytest.raises(TrainError, match=fragment):
        _train(**overrides)


def test_bad_proven_head_is_a_schema_violation() -> None:
    with pytest.raises(TrainError, match="proven_head"):
        _train(prs=[{"number": 1, "lane": "A", "proven_head": "not-a-sha"}], order=[1])


def test_cli_plan_and_invalid_exit(tmp_path: Path, capsys) -> None:
    path = tmp_path / ".l9" / "cto-mode" / "train.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(_train()), encoding="utf-8")
    assert cto_train.main(["--workspace", str(tmp_path), "plan"]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == "l9.cto-train-plan/v1"
    path.write_text(json.dumps({**_train(), "order": [1]}), encoding="utf-8")
    assert cto_train.main(["--workspace", str(tmp_path), "plan"]) == cto_train.EXIT_USAGE


# --- run: the happy path and the executor boundary -------------------------------


def test_run_merges_in_order_through_the_executor_bound_to_the_proven_head(tmp_path) -> None:
    gh = FakeGitHub(_three())
    summary = _runner(_train(), gh, tmp_path).run()
    assert [m["pr"] for m in summary["merged"]] == [1, 2, 3]
    assert summary["deferred"] == []
    assert summary["grants_permission"] is False
    merge_calls = [c for c in gh.calls if c[0] == "merge"]
    assert merge_calls[0] == ("merge", 1, _sha("a"), (BASE,))
    assert {m["head_basis"] for m in summary["merged"]} == {"proven"}


def test_already_merged_is_skipped(tmp_path) -> None:
    pulls = _three()
    pulls[1].update(merged=True, state="closed")
    gh = FakeGitHub(pulls)
    summary = _runner(_train(), gh, tmp_path).run()
    assert summary["already_merged"] == [1]
    assert gh.merges() == [2, 3]


def test_executor_refusal_is_deferred_and_the_run_continues(tmp_path) -> None:
    gh = FakeGitHub(_three(), refuse={2: "no human GitHub merge authorization"})
    summary = _runner(_train(), gh, tmp_path).run()
    assert [m["pr"] for m in summary["merged"]] == [1, 3]
    assert summary["deferred"][0]["pr"] == 2
    assert "MERGE_PENDING" in summary["deferred"][0]["reason"]


def test_board_not_merge_defers_and_continues(tmp_path) -> None:
    gh = FakeGitHub(_three(), boards={1: {"board": "fix", "reason": "required check red"}})
    summary = _runner(_train(), gh, tmp_path).run()
    assert summary["deferred"] == [{"pr": 1, "reason": "board is fix: required check red"}]
    assert gh.merges() == [2, 3]


def test_only_limits_the_run(tmp_path) -> None:
    gh = FakeGitHub(_three())
    summary = _runner(_train(), gh, tmp_path).run({2})
    assert gh.merges() == [2]
    assert [m["pr"] for m in summary["merged"]] == [2]


def test_dry_run_changes_nothing(tmp_path) -> None:
    pulls = _three()
    pulls[2]["base"]["ref"] = "feat/1"
    gh = FakeGitHub(pulls, compares={(BASE, "feat/1"): "behind"})
    summary = _runner(_train(), gh, tmp_path, dry_run=True).run()
    assert gh.merges() == []
    assert not any(c[0] == "retarget" for c in gh.calls)
    assert [w["pr"] for w in summary["would_merge"]] == [1, 2, 3]
    assert summary["retargeted"] == [
        {"pr": 2, "from": "feat/1", "to": BASE, "base_compare": "behind", "dry_run": True}
    ]


# --- dead base -------------------------------------------------------------------


def test_dead_base_is_retargeted_before_merging(tmp_path) -> None:
    pulls = _three()
    pulls[2]["base"]["ref"] = "fix/l8-8-normalization-retry"
    gh = FakeGitHub(pulls, compares={(BASE, "fix/l8-8-normalization-retry"): "behind"})
    summary = _runner(_train(), gh, tmp_path).run()
    retarget = gh.calls.index(("retarget", 2, BASE))
    merge = next(i for i, c in enumerate(gh.calls) if c[:2] == ("merge", 2))
    assert retarget < merge
    assert summary["retargeted"][0]["from"] == "fix/l8-8-normalization-retry"


def test_live_foreign_base_is_deferred(tmp_path) -> None:
    pulls = _three()
    pulls[2]["base"]["ref"] = "feat/unmerged-parent"
    gh = FakeGitHub(pulls, compares={(BASE, "feat/unmerged-parent"): "ahead"})
    summary = _runner(_train(), gh, tmp_path).run()
    assert gh.merges() == [1, 3]
    assert "merge its parent first" in summary["deferred"][0]["reason"]


# --- containment -----------------------------------------------------------------


def test_containing_pr_waits_for_the_contained_one(tmp_path) -> None:
    """#3 contains #1; #1 is not ready, so #3 is deferred too, and #2 still lands."""
    gh = FakeGitHub(
        _three(),
        compares={(_sha("a"), _sha("c")): "ahead"},
        boards={1: {"board": "wait", "reason": "checks pending"}},
    )
    summary = _runner(_train(), gh, tmp_path).run()
    assert gh.merges() == [2]
    reasons = {d["pr"]: d["reason"] for d in summary["deferred"]}
    assert "contains open PR(s) #1 which must merge first" in reasons[3]


def test_containing_pr_merges_once_the_contained_one_has(tmp_path) -> None:
    gh = FakeGitHub(_three(), compares={(_sha("a"), _sha("c")): "ahead"})
    summary = _runner(_train(), gh, tmp_path).run()
    assert gh.merges() == [1, 2, 3]
    assert summary["deferred"] == []


# --- pairs -----------------------------------------------------------------------


def test_pair_merges_nothing_until_every_member_is_ready(tmp_path) -> None:
    gh = FakeGitHub(_three(), boards={3: {"board": "fix", "reason": "conflict"}})
    summary = _runner(_train(pairs=[[2, 3]]), gh, tmp_path).run()
    assert gh.merges() == [1]
    reasons = {d["pr"]: d["reason"] for d in summary["deferred"]}
    assert reasons[3] == "board is fix: conflict"
    assert "#3 is not ready" in reasons[2]


def test_ready_pair_lands_back_to_back(tmp_path) -> None:
    gh = FakeGitHub(_three(), boards={1: {"board": "wait", "reason": "pending"}})
    summary = _runner(_train(order=[2, 1, 3], pairs=[[2, 3]]), gh, tmp_path).run()
    assert gh.merges() == [2, 3]
    assert [d["pr"] for d in summary["deferred"]] == [1]


def test_stacked_pair_member_is_retargeted_after_its_parent_lands(tmp_path) -> None:
    """#3 is based on #2's branch; once #2 lands that base is dead and is retargeted."""
    pulls = _three()
    pulls[3]["base"]["ref"] = "feat/2"
    gh = FakeGitHub(pulls, compares={(_sha("b"), _sha("c")): "ahead"})
    original = gh.compare

    def compare(base: str, head: str) -> str:
        if (base, head) == (BASE, "feat/2"):
            return "behind" if pulls[2]["merged"] else "diverged"
        return original(base, head)

    gh.compare = compare  # type: ignore[method-assign]
    summary = _runner(_train(pairs=[[2, 3]]), gh, tmp_path).run()
    assert gh.merges() == [1, 2, 3]
    assert ("retarget", 3, BASE) in gh.calls
    assert summary["deferred"] == []


# --- head equivalence and reviewed acceptance -------------------------------------


def test_moved_head_equivalent_to_the_proven_one_merges(tmp_path) -> None:
    pulls = _three()
    pulls[2]["head"]["sha"] = _sha("d")
    seen: list[tuple] = []

    def verify(pr: int, proven: str, head: str) -> dict:
        seen.append((pr, proven, head))
        return {"verdict": "equivalent"}

    gh = FakeGitHub(pulls)
    summary = _runner(_train(), gh, tmp_path, verify=verify).run()
    assert seen == [(2, _sha("b"), _sha("d"))]
    merged = {m["pr"]: m for m in summary["merged"]}
    assert merged[2]["head_basis"] == "equivalent"
    assert ("merge", 2, _sha("d"), (BASE,)) in gh.calls


def test_moved_head_not_equivalent_is_deferred(tmp_path) -> None:
    pulls = _three()
    pulls[2]["head"]["sha"] = _sha("d")
    gh = FakeGitHub(pulls)
    verify = lambda pr, proven, head: {  # noqa: E731
        "verdict": "not_equivalent",
        "reason": "non-mechanical change in models/x.py",
    }
    summary = _runner(_train(), gh, tmp_path, verify=verify).run()
    assert gh.merges() == [1, 3]
    assert "models/x.py" in summary["deferred"][0]["reason"]


def test_unknown_equivalence_is_never_accepted(tmp_path) -> None:
    pulls = _three()
    pulls[2]["head"]["sha"] = _sha("d")
    gh = FakeGitHub(pulls)
    summary = _runner(
        _train(), gh, tmp_path, verify=lambda *a: {"verdict": "unknown", "reason": "conflict"}
    ).run()
    assert [d["pr"] for d in summary["deferred"]] == [2]


def test_reviewed_acceptance_covers_a_moved_head(tmp_path) -> None:
    pulls = _three()
    pulls[2]["head"]["sha"] = _sha("d")
    gh = FakeGitHub(pulls)
    train = _train(accepted=[{"pr": 2, "head_prefix": "ddddddd", "reason": "reviewed rebase"}])
    summary = _runner(train, gh, tmp_path).run()
    assert {m["pr"]: m["head_basis"] for m in summary["merged"]}[2] == "accepted"


def test_no_proven_head_and_no_acceptance_is_deferred(tmp_path) -> None:
    train = _train(prs=[{"number": 1, "lane": "A", "proven_head": None}], order=[1])
    gh = FakeGitHub({1: _view(1, _sha("a"))})
    summary = _runner(train, gh, tmp_path).run()
    assert gh.merges() == []
    assert "no proven head" in summary["deferred"][0]["reason"]


# --- integration receipt ----------------------------------------------------------


def _receipt(tmp_path: Path, **overrides: Any) -> str:
    data = {
        "schema": "l9.cto-integration-receipt/v1",
        "campaign": "odoo-pre-go-live",
        "repo": SLUG,
        "base_ref": BASE,
        "base_sha": _sha("0"),
        "candidate": "cand-1",
        "heads": {"1": _sha("a"), "2": _sha("b"), "3": _sha("c")},
        "tree_sha": _sha("9"),
        "resolutions": [],
        "results": {},
        "verdict": "pass",
        "created_at": "2026-11-23T00:00:00Z",
    }
    data.update(overrides)
    path = tmp_path / ".l9" / "cto-mode" / "integration" / "cand-1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return ".l9/cto-mode/integration/cand-1.json"


def test_passing_receipt_covering_the_heads_allows_merging(tmp_path) -> None:
    gh = FakeGitHub(_three())
    summary = _runner(_train(integration_receipt=_receipt(tmp_path)), gh, tmp_path).run()
    assert gh.merges() == [1, 2, 3] and summary["deferred"] == []


def test_missing_receipt_defers_every_pr(tmp_path) -> None:
    gh = FakeGitHub(_three())
    summary = _runner(
        _train(integration_receipt=".l9/cto-mode/integration/absent.json"), gh, tmp_path
    ).run()
    assert gh.merges() == []
    assert all("does not exist" in d["reason"] for d in summary["deferred"])


def test_failing_receipt_defers(tmp_path) -> None:
    gh = FakeGitHub(_three())
    train = _train(integration_receipt=_receipt(tmp_path, verdict="fail"))
    summary = _runner(train, gh, tmp_path).run()
    assert gh.merges() == []
    assert "not 'pass'" in summary["deferred"][0]["reason"]


def test_receipt_not_covering_a_proven_head_defers_that_pr(tmp_path) -> None:
    gh = FakeGitHub(_three())
    heads = {"1": _sha("a"), "2": _sha("e"), "3": _sha("c")}
    summary = _runner(
        _train(integration_receipt=_receipt(tmp_path, heads=heads)), gh, tmp_path
    ).run()
    assert gh.merges() == [1, 3]
    assert "does not cover #2" in summary["deferred"][0]["reason"]


# --- mergeable_state --------------------------------------------------------------


def test_unknown_mergeable_state_is_waited_out(tmp_path) -> None:
    sleeps: list[float] = []
    gh = FakeGitHub(_three(), unknown_polls={1: 2})
    summary = _runner(_train(), gh, tmp_path, sleep=sleeps.append, poll=1.0).run()
    assert gh.merges() == [1, 2, 3]
    assert len(sleeps) >= 1 and summary["deferred"] == []


def test_mergeable_state_that_stays_unknown_is_deferred(tmp_path) -> None:
    ticks = iter(range(0, 10_000, 50))
    gh = FakeGitHub(_three(), unknown_polls={1: 10_000})
    summary = _runner(
        _train(), gh, tmp_path, clock=lambda: float(next(ticks)), mergeable_timeout=120
    ).run()
    assert gh.merges() == [2, 3]
    assert "still unknown" in summary["deferred"][0]["reason"]


# --- the live layer merges only through stack_safe_merge.py --run -------------------


def test_live_merge_invokes_the_executor_never_the_merge_api(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake_run(argv, **kw):
        seen.append(list(argv))
        out = json.dumps({"status": "MERGED", "merge_commit_sha": _sha("f"), "method": "merge"})
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")

    monkeypatch.setattr(cto_train.subprocess, "run", fake_run)
    result = cto_train.LiveGitHub(SLUG).merge(7, _sha("a"), (BASE,))
    argv = seen[0]
    assert argv[1].endswith("ops/autonomy/stack_safe_merge.py")
    assert argv[argv.index("--head-sha") + 1] == _sha("a")
    assert "--run" in argv and argv[argv.index("--long-lived-base") + 1] == BASE
    assert not any(a in ("merge", "--admin") for a in argv[2:] if a != "--run")
    assert result["record"]["status"] == "MERGED"


# --- verify-head against real git --------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return proc.stdout.strip()


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


MANIFEST = '{{\n    "name": "ib_x",\n    "version": "{v}",\n    "depends": ["base"],\n}}\n'
README = "---\nmodule_version: {v}\n---\n# ib_x\n"


@pytest.fixture
def odoo_repo(tmp_path: Path) -> dict[str, Any]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", BASE)
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    _commit(
        repo,
        {
            "ib_x/__manifest__.py": MANIFEST.format(v="19.0.1.0.1"),
            "ib_x/README.md": README.format(v="19.0.1.0.1"),
            "ib_x/tests/__init__.py": "from . import test_a\n",
            "ib_x/models/x.py": "X = 1\n",
        },
        "base",
    )
    _git(repo, "checkout", "-q", "-b", "proven")
    proven = _commit(
        repo,
        {
            "ib_x/__manifest__.py": MANIFEST.format(v="19.0.1.0.2"),
            "ib_x/README.md": README.format(v="19.0.1.0.2"),
            "ib_x/tests/__init__.py": "from . import test_a\nfrom . import test_b\n",
            "ib_x/models/x.py": "X = 2\n",
        },
        "proven",
    )
    # A sibling lands on the base meanwhile and bumps the same module.
    _git(repo, "checkout", "-q", BASE)
    _commit(repo, {"ib_x/other.py": "Y = 1\n"}, "sibling")
    # The moved head: same change, re-versioned and with the imports reordered.
    _git(repo, "checkout", "-q", "proven")
    mechanical = _commit(
        repo,
        {
            "ib_x/__manifest__.py": MANIFEST.format(v="19.0.1.0.3"),
            "ib_x/README.md": README.format(v="19.0.1.0.3"),
            "ib_x/tests/__init__.py": "from . import test_b\nfrom . import test_a\n",
        },
        "rebump",
    )
    content = _commit(repo, {"ib_x/models/x.py": "X = 3\n"}, "real change")
    return {"repo": repo, "proven": proven, "mechanical": mechanical, "content": content}


def test_verify_head_accepts_versions_and_reordering(odoo_repo) -> None:
    record = verify_head(
        odoo_repo["repo"],
        pr=9,
        base_ref=BASE,
        proven=odoo_repo["proven"],
        head=odoo_repo["mechanical"],
    )
    assert record["verdict"] == "equivalent", record
    kinds = {d["path"]: d["kind"] for d in record["differences"]}
    assert kinds == {
        "ib_x/__manifest__.py": "version",
        "ib_x/README.md": "readme_version",
        "ib_x/tests/__init__.py": "reordered",
    }
    assert record["grants_permission"] is False


def test_verify_head_rejects_a_content_change(odoo_repo) -> None:
    record = verify_head(
        odoo_repo["repo"],
        pr=9,
        base_ref=BASE,
        proven=odoo_repo["proven"],
        head=odoo_repo["content"],
    )
    assert record["verdict"] == "not_equivalent"
    assert "ib_x/models/x.py" in record["reason"]


def test_verify_head_identical_and_unknown(odoo_repo) -> None:
    same = verify_head(
        odoo_repo["repo"], pr=9, base_ref=BASE, proven=odoo_repo["proven"], head=odoo_repo["proven"]
    )
    assert same["verdict"] == "identical"
    missing = verify_head(
        odoo_repo["repo"], pr=9, base_ref=BASE, proven=odoo_repo["proven"], head=_sha("9")
    )
    assert missing["verdict"] == "unknown"


def test_verify_head_added_file_is_not_equivalent(odoo_repo) -> None:
    repo = odoo_repo["repo"]
    _git(repo, "checkout", "-q", odoo_repo["mechanical"])
    added = _commit(repo, {"ib_x/new.py": "Z = 1\n"}, "added")
    record = verify_head(repo, pr=9, base_ref=BASE, proven=odoo_repo["proven"], head=added)
    assert record["verdict"] == "not_equivalent"
    assert {"path": "ib_x/new.py", "kind": "added"} in record["differences"]


def test_cli_verify_head_exit_codes(odoo_repo, capsys) -> None:
    base = ["--workspace", str(odoo_repo["repo"]), "verify-head", "--pr", "9", "--no-fetch"]
    common = ["--proven", odoo_repo["proven"], "--base-ref", BASE]
    assert cto_train.main([*base, *common, "--head", odoo_repo["mechanical"]]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "equivalent"
    assert cto_train.main([*base, *common, "--head", odoo_repo["content"]]) == 1
    capsys.readouterr()
    assert cto_train.main([*base, *common, "--head", _sha("9")]) == cto_train.EXIT_PENDING


def test_classify_file_version_line_only_in_a_manifest() -> None:
    before = ['    "version": "1.0.1",', "X = 1"]
    after = ['    "version": "1.0.2",', "X = 1"]
    assert classify_file("mod/__manifest__.py", before, after) == "version"
    assert classify_file("mod/setup.py", before, after) == "content"
    assert classify_file("mod/README.rst", ["module_version: 1"], ["module_version: 2"]) == (
        "readme_version"
    )
    assert classify_file("a.py", ["a", "b"], ["b", "a"]) == "reordered"
    assert classify_file("a.py", ["a", "b"], ["a", "a"]) == "content"
