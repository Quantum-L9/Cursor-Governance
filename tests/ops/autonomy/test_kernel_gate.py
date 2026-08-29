"""Kernel hook owns tree/plan kernels; L4 authorize does not."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _gate():
    import sys

    autonomy = str(ROOT / "ops" / "autonomy")
    if autonomy not in sys.path:
        sys.path.insert(0, autonomy)
    import kernel_gate

    return kernel_gate


def test_precommit_fails_before_receipt(stacked_repo: Path) -> None:
    gate = _gate()
    rc = gate.precommit(stacked_repo, ROOT, None)
    assert rc == 2


def test_record_then_precommit_passes_without_plans(stacked_repo: Path) -> None:
    gate = _gate()
    receipt = gate.record(stacked_repo, gov=ROOT)
    assert receipt["schema"] == gate.SCHEMA
    assert receipt["kernel_shas"] == gate.kernel_shas(ROOT)
    assert gate.precommit(stacked_repo, ROOT, None) == 0


def test_head_move_does_not_require_second_apply(stacked_repo: Path) -> None:
    gate = _gate()
    gate.record(stacked_repo, gov=ROOT)
    extra = stacked_repo / "b.txt"
    extra.write_text("b\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "-C", str(stacked_repo), "add", "b.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(stacked_repo), "commit", "-m", "rewrite"],
        check=True,
        capture_output=True,
    )
    assert gate.verify_tree(stacked_repo, ROOT) is None


def test_changed_plan_template_is_skipped(stacked_repo: Path, tmp_path: Path) -> None:
    gate = _gate()
    gate.record(stacked_repo, gov=ROOT)
    rel = "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
    template = stacked_repo / rel
    template.parent.mkdir(parents=True)
    template.write_text("---\nname: template\n---\n\n# not a live plan\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text(rel + "\n", encoding="utf-8")
    assert gate.precommit(stacked_repo, ROOT, changed) == 0


def test_changed_plan_without_receipt_is_skipped(stacked_repo: Path, tmp_path: Path) -> None:
    gate = _gate()
    gate.record(stacked_repo, gov=ROOT)
    plan = stacked_repo / "docs" / "plans" / "hook_test_00000000.plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("---\nname: hook test\n---\n\n# bare\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("docs/plans/hook_test_00000000.plan.md\n", encoding="utf-8")
    assert gate.precommit(stacked_repo, ROOT, changed) == 0


def test_corpus_only_skips_tree_latch(stacked_repo: Path, tmp_path: Path) -> None:
    gate = _gate()
    wip = stacked_repo / "WIP" / "note.md"
    wip.parent.mkdir(parents=True)
    wip.write_text("leftover\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("WIP/note.md\n")
    assert gate.precommit(stacked_repo, ROOT, changed) == 0


def test_code_change_without_receipt_still_fails(stacked_repo: Path, tmp_path: Path) -> None:
    gate = _gate()
    code = stacked_repo / "ops" / "foo.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("ops/foo.py\n")
    assert gate.precommit(stacked_repo, ROOT, changed) == 2


def test_authorize_release_without_record_kernels(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    autonomy = str(ROOT / "ops" / "autonomy")
    if autonomy not in sys.path:
        sys.path.insert(0, autonomy)
    from l4_local import authorize_release, begin, release_allows_remote

    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="no-kernels")
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed
    assert "release_authorized" in reason
