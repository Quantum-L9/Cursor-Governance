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


def write_apply_report(
    repo: Path, *, delta_path: str = "a.txt", delta_path_2: str = "b.txt", body: str = ""
) -> Path:
    """Write a valid apply report naming files that exist in `repo`.

    Tests used to call `record()` bare, which is exactly the honor-system stamp
    this latch removed. Producing the artifact is now part of setup.

    Phase 1 hardening requires both kernels to have at least one delta each,
    and notes cannot be template boilerplate.
    """
    target = repo / delta_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("touched\n", encoding="utf-8")
    target2 = repo / delta_path_2
    target2.parent.mkdir(parents=True, exist_ok=True)
    target2.write_text("validated\n", encoding="utf-8")
    report = repo / ".l9" / "autonomy" / "kernel-apply.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "---\n"
        "schema: l9.kernel_apply.v1\n"
        "kernels: [recursive_alignment, validate_repair]\n"
        "convergence_status: converged\n"
        "deltas:\n"
        f"  - path: {delta_path}\n"
        "    kernel: recursive_alignment\n"
        "    note: Added input validation for empty collections\n"
        f"  - path: {delta_path_2}\n"
        "    kernel: validate_repair\n"
        "    note: Updated test assertions to cover edge case\n"
        "---\n"
        "\n## Recursive Alignment\n\nInspected and found missing null guard. Fixed.\n"
        f"\n## Validate & Repair\n\nRan pytest suite. All assertions passed.{body}\n",
        encoding="utf-8",
    )
    return report


def record_with_evidence(
    gate, repo: Path, *, delta_path: str = "a.txt", delta_path_2: str = "b.txt"
) -> dict:
    write_apply_report(repo, delta_path=delta_path, delta_path_2=delta_path_2)
    return gate.record(repo, gov=ROOT)


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


def test_record_with_evidence_then_precommit_passes_without_plans(stacked_repo: Path) -> None:
    gate = _gate()
    receipt = record_with_evidence(gate, stacked_repo)
    assert receipt["schema"] == gate.SCHEMA
    assert receipt["kernel_shas"] == gate.kernel_shas(ROOT)
    # The claim is bound to an artifact, not to ambient state.
    assert receipt["report_rel"] == ".l9/autonomy/kernel-apply.md"
    assert len(receipt["report_sha256"]) == 64
    assert receipt["deltas"] == [
        {
            "path": "a.txt",
            "kernel": "recursive_alignment",
            "note": "Added input validation for empty collections",
        },
        {
            "path": "b.txt",
            "kernel": "validate_repair",
            "note": "Updated test assertions to cover edge case",
        },
    ]
    assert gate.precommit(stacked_repo, ROOT, None) == 0


def test_bare_record_without_a_report_writes_no_receipt(stacked_repo: Path) -> None:
    """The honor-system stamp, asserted gone.

    `record()` with no apply report is what produced INC-2026-09-14-001. It must
    raise AND leave no receipt: a caller that swallows the exception must not
    end up with something a gate accepts.
    """
    gate = _gate()
    with pytest.raises(gate.ReportError):
        gate.record(stacked_repo, gov=ROOT)
    assert not gate.receipt_path(stacked_repo).is_file()
    assert gate.precommit(stacked_repo, ROOT, None) == 2


def test_v1_receipt_is_rejected_by_name(stacked_repo: Path) -> None:
    gate = _gate()
    gate.write_receipt(
        stacked_repo,
        {
            "schema": gate.SCHEMA_V1,
            "head": "deadbeef",
            "kernel_shas": gate.kernel_shas(ROOT),
            "phase": "recorded",
        },
    )
    failure = gate.verify_tree(stacked_repo, ROOT)
    assert failure is not None
    assert gate.SCHEMA_V1 in failure
    assert gate.precommit(stacked_repo, ROOT, None) == 2


def test_load_receipt_none_only_when_the_file_is_absent(stacked_repo: Path) -> None:
    """None means no claim. An existing unreadable file must not be None."""
    gate = _gate()
    assert gate.load_receipt(stacked_repo) is None
    path = gate.receipt_path(stacked_repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(gate.ReceiptLoadError, match="not valid JSON"):
        gate.load_receipt(stacked_repo)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(gate.ReceiptLoadError, match="not a JSON object"):
        gate.load_receipt(stacked_repo)
    failure = gate.verify_tree(stacked_repo, ROOT)
    assert failure is not None
    assert "not a JSON object" in failure


def test_editing_the_report_after_recording_fails_verify(stacked_repo: Path) -> None:
    """Verify re-derives. A receipt is not a durable permission slip."""
    gate = _gate()
    report = write_apply_report(stacked_repo)
    gate.record(stacked_repo, gov=ROOT)
    assert gate.verify_tree(stacked_repo, ROOT) is None
    report.write_text(report.read_text(encoding="utf-8") + "\nadded later\n", encoding="utf-8")
    failure = gate.verify_tree(stacked_repo, ROOT)
    assert failure is not None
    assert "no longer satisfies" in failure


def test_deleting_the_report_after_recording_fails_verify(stacked_repo: Path) -> None:
    gate = _gate()
    report = write_apply_report(stacked_repo)
    gate.record(stacked_repo, gov=ROOT)
    report.unlink()
    assert gate.verify_tree(stacked_repo, ROOT) is not None


def test_delta_naming_a_nonexistent_path_is_refused(stacked_repo: Path) -> None:
    gate = _gate()
    report = stacked_repo / ".l9" / "autonomy" / "kernel-apply.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "---\n"
        "schema: l9.kernel_apply.v1\n"
        "kernels: [recursive_alignment, validate_repair]\n"
        "convergence_status: converged\n"
        "deltas:\n"
        "  - path: never/existed.py\n"
        "    kernel: validate_repair\n"
        "    note: invented\n"
        "---\n\n## Recursive Alignment\n\nx\n\n## Validate & Repair\n\ny\n",
        encoding="utf-8",
    )
    with pytest.raises(gate.ReportError):
        gate.record(stacked_repo, gov=ROOT)
    assert not gate.receipt_path(stacked_repo).is_file()


def test_report_outside_the_autonomy_dir_is_refused(stacked_repo: Path) -> None:
    gate = _gate()
    with pytest.raises(gate.ReportError):
        gate.record(stacked_repo, gov=ROOT, report=Path("../escape.md"))
    assert not gate.receipt_path(stacked_repo).is_file()


def test_template_cannot_be_recorded_as_written(stacked_repo: Path) -> None:
    """The scaffold must not be stampable: its deltas are placeholders."""
    gate = _gate()
    report = stacked_repo / ".l9" / "autonomy" / "kernel-apply.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(gate.apply_report_template(), encoding="utf-8")
    with pytest.raises(gate.ReportError):
        gate.record(stacked_repo, gov=ROOT)


def test_head_move_does_not_require_second_apply(stacked_repo: Path) -> None:
    gate = _gate()
    record_with_evidence(gate, stacked_repo)
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
    record_with_evidence(gate, stacked_repo)
    rel = "environment/contracts/execution/templates/canonical.template.executable_plan.v1.plan.md"
    template = stacked_repo / rel
    template.parent.mkdir(parents=True)
    template.write_text("---\nname: template\n---\n\n# not a live plan\n", encoding="utf-8")
    changed = tmp_path / "changed.txt"
    changed.write_text(rel + "\n", encoding="utf-8")
    assert gate.precommit(stacked_repo, ROOT, changed) == 0


def test_changed_plan_without_receipt_is_skipped(stacked_repo: Path, tmp_path: Path) -> None:
    gate = _gate()
    record_with_evidence(gate, stacked_repo)
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
    record_with_evidence(gate, stacked_repo, delta_path="ops/foo.py")
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
    command = gate.record_command(consumer, ROOT)
    assert "--changed-file" in command
    # And the interpreter is the locked governance one when present.
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


def test_record_and_verify_cover_live_diff_without_changed_file(stacked_repo: Path) -> None:
    """Omitting --changed-file must still run deltas_cover_diff on the live git set."""
    gate = _gate()
    receipt = record_with_evidence(gate, stacked_repo)
    assert receipt["changed_paths_count"]
    assert "a.txt" in gate.discover_changed_paths(stacked_repo)
    assert gate.verify_tree(stacked_repo, ROOT) is None
