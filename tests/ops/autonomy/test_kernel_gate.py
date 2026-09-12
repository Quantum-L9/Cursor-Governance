"""Kernel hook stamps/verifies tree kernels; L4 authorize requires the receipt."""

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


@pytest.fixture(autouse=True)
def adapter_kernel_surface(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing latch tests prove Claude Code / adapter behavior."""
    monkeypatch.setenv("L9_GOVERNANCE_SURFACE", "claude-code")
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("CLAUDECODE", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_REMOTE", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_ENTRYPOINT", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)


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


def test_cursor_surface_requires_tree_latch(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_GOVERNANCE_SURFACE", "cursor")
    monkeypatch.setenv("CURSOR_AGENT", "1")
    gate = _gate()
    assert gate.precommit(stacked_repo, ROOT, None) == 2


def test_ci_unknown_skips_tree_latch(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_GOVERNANCE_SURFACE", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    gate = _gate()
    assert gate.precommit(stacked_repo, ROOT, None) == 0


def test_bare_local_surface_requires_tree_latch(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GOVERNANCE_SURFACE", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    gate = _gate()
    assert gate.precommit(stacked_repo, ROOT, None) == 2


def test_authorize_release_without_record_kernels(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import sys

    autonomy = str(ROOT / "ops" / "autonomy")
    if autonomy not in sys.path:
        sys.path.insert(0, autonomy)
    from l4_local import authorize_release, begin, release_allows_remote

    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setenv("CURSOR_AGENT", "1")
    begin(stacked_repo, contract_id="no-kernels")
    # CANONICAL_LAW KERNEL_PRECOMMIT_HOOK_V1: post-finish kernels are not an
    # L4 phase and authorize-release does not require a kernel stamp. The one
    # mechanical latch is kernel_gate.precommit, asserted by the surface tests
    # above. A stamp requirement here would be a second, unauthorized gate.
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed
    assert "release_authorized" in reason


def test_cursor_surface_requires_receipt_on_code_change(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_GOVERNANCE_SURFACE", "cursor")
    gate = _gate()
    code = stacked_repo / "ops" / "foo.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("ops/foo.py\n")
    assert gate.precommit(stacked_repo, ROOT, changed) == 2


def test_ci_unknown_skips_tree_latch_without_receipt(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_GOVERNANCE_SURFACE", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    gate = _gate()
    code = stacked_repo / "ops" / "foo.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("ops/foo.py\n")
    assert gate.precommit(stacked_repo, ROOT, changed) == 0
    assert gate.adapter_tree_kernels_required({"GITHUB_ACTIONS": "true"}) is False
    assert gate.adapter_tree_kernels_required({}) is True
    assert gate.adapter_tree_kernels_required({"L9_GOVERNANCE_SURFACE": "claude-code"}) is True


def test_cursor_requires_tree_receipt_before_pass(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CURSOR_AGENT", "1")
    monkeypatch.delenv("L9_GOVERNANCE_SURFACE", raising=False)
    gate = _gate()
    code = stacked_repo / "ops" / "foo.py"
    code.parent.mkdir(parents=True)
    code.write_text("x = 1\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text("ops/foo.py\n")
    assert gate.precommit(stacked_repo, ROOT, changed) == 2
    gate.record(stacked_repo, gov=ROOT)
    assert gate.precommit(stacked_repo, ROOT, changed) == 0


def test_authorize_release_is_not_gated_by_the_kernel_receipt(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The canonical boundary, asserted from the other direction.

    A precommit latch that is failing on this very tree must still not block
    L4 authorization: they are different gates with different owners
    (CANONICAL_LAW KERNEL_PRECOMMIT_HOOK_V1).
    """
    import sys

    autonomy = str(ROOT / "ops" / "autonomy")
    if autonomy not in sys.path:
        sys.path.insert(0, autonomy)
    from l4_local import authorize_release, begin

    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")

    gate = _gate()
    # Precommit is red on this tree: no receipt at all.
    assert gate.precommit(stacked_repo, ROOT, None) == 2
    # L4 authorization is nonetheless available.
    begin(stacked_repo, contract_id="boundary")
    assert authorize_release(stacked_repo)["phase"] == "release_authorized"


def test_corpus_only_change_needs_no_kernel_receipt(stacked_repo: Path, tmp_path: Path) -> None:
    """The /ff corpus lifecycle must not require a tree receipt.

    WIP/, docs/plans/ and PE campaigns are owned by /ff (Improve then RA then
    Validate & Repair). Requiring a stamp here would break the documented
    corpus publish flow.
    """
    gate = _gate()
    changed = tmp_path / "corpus.txt"
    changed.write_text("docs/plans/some.plan.md\nWIP/notes.md\n", encoding="utf-8")
    assert gate.precommit(stacked_repo, ROOT, changed) == 0


def test_record_command_is_runnable_from_a_consumer_workspace(tmp_path: Path) -> None:
    """Remediation guidance must not assume the consumer has governance's ops/.

    The documented delegated form leaves the reader in the consumer tree,
    where `ops/autonomy/kernel_gate.py` does not exist.
    """
    gate = _gate()
    consumer = tmp_path / "consumer"
    (consumer / "src").mkdir(parents=True)
    text = gate._agent_required_tree(consumer, ROOT)

    line = next(ln for ln in text.splitlines() if "kernel_gate.py record" in ln)
    # The script is named in the GOVERNANCE checkout, not relative to cwd.
    assert str(ROOT / "ops" / "autonomy" / "kernel_gate.py") in line
    assert "  4. python3 ops/autonomy/kernel_gate.py record" not in text
    # The target workspace is explicit, so it works from anywhere.
    assert f'--workspace "{consumer}"' in line
    # And the interpreter is the locked governance one when present.
    command = gate.record_command(consumer, ROOT)
    locked = ROOT / ".venv" / "bin" / "python"
    if locked.is_file():
        assert command.startswith(str(locked))
    assert command in line
    # No consumer-relative path is offered anywhere in the guidance.
    assert str(consumer / "ops" / "autonomy") not in text


def test_guidance_does_not_claim_kernels_gate_l4() -> None:
    """Nothing printed by this hook may teach the superseded L4 coupling."""
    gate = _gate()
    text = gate._agent_required_tree(Path("/ws"), ROOT)
    assert "Kernels are not an L4 phase." in text
    assert "authorize-release" not in text
