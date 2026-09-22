"""Tests for L4 local autonomy phase machine + remote gate."""

from __future__ import annotations

import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import open_pr_probe  # noqa: E402
from l4_local import (  # noqa: E402
    authorize_release,
    begin,
    breakglass_path,
    current_head,
    extend_release,
    kernel_evidence,
    receipt_path,
    record_kernels,
    release_allows_remote,
    resolve_pr_template,
    state_path,
    status_dict,
    workspace_from_event,
    workspace_identity,
)
from local_execution_gate import evaluate  # noqa: E402


def test_denies_remote_without_release(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    allowed, reason = release_allows_remote(stacked_repo)
    assert not allowed
    assert "mid-execution" in reason or "L4" in reason


def test_push_breakglass_leaves_a_trail_bound_to_head(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setenv("L9_LOCAL_PUSH_AUTHORIZED", "ops: hotfix for #1")
    assert not breakglass_path(stacked_repo).exists()
    allowed, reason = release_allows_remote(stacked_repo, record=True)
    assert allowed
    assert "breakglass" in reason
    trail = json.loads(breakglass_path(stacked_repo).read_text(encoding="utf-8"))
    assert trail["schema"] == "l9.l4_breakglass.v1"
    assert trail["variable"] == "L9_LOCAL_PUSH_AUTHORIZED"
    assert trail["reason"] == "ops: hotfix for #1"
    assert trail["head"] == current_head(stacked_repo)
    assert len(trail["tree_digest"]) == 64
    assert trail["branch"]
    assert trail["used_at"].endswith("Z") or "+" in trail["used_at"]


def test_l4_switch_off_also_leaves_a_trail(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "0")
    assert release_allows_remote(stacked_repo, record=True)[0]
    trail = json.loads(breakglass_path(stacked_repo).read_text(encoding="utf-8"))
    assert trail["variable"] == "L9_L4_LOCAL_AUTONOMY"
    assert trail["reason"] == "0"


def test_status_probe_does_not_record_breakglass(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_LOCAL_PUSH_AUTHORIZED", "ops: status only")
    assert status_dict(stacked_repo)["remote_allowed"] is True
    assert not breakglass_path(stacked_repo).exists()


def test_receipt_path_leaves_no_breakglass_trail(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="c1")
    authorize_release(stacked_repo)
    assert release_allows_remote(stacked_repo)[0]
    assert not breakglass_path(stacked_repo).exists()


def test_begin_kernels_authorize_allows_push(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="c1")
    assert release_allows_remote(stacked_repo)[0] is False
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    assert release_allows_remote(stacked_repo)[0] is False
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed
    assert "release_authorized" in reason


def test_gate_denies_mid_execution_remote_mutation(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L4 gates `make pr`; a raw push is judged by the publication plane instead.

    L4 state never decides a git command (git_execution_exemption). A raw push
    of this branch — which has no open PR and no GitHub remote — is a first
    publication and is denied by `first_publication_gate`, not by L4; the same
    push with an open PR is remediation and passes regardless of L4 phase.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate("Bash", {"command": "make pr"}, root=stacked_repo)
    assert reason is not None
    assert "L4" in reason

    monkeypatch.setattr(
        open_pr_probe, "open_pr_for_branch", lambda root, branch, remote="origin": False
    )
    push = evaluate("Bash", {"command": "git push -u origin HEAD"}, root=stacked_repo)
    assert push is not None and "FIRST publication" in push and "L4" not in push.split(".")[0]

    monkeypatch.setattr(
        open_pr_probe, "open_pr_for_branch", lambda root, branch, remote="origin": True
    )
    assert evaluate("Bash", {"command": "git push -u origin HEAD"}, root=stacked_repo) is None


# ---------------------------------------------------------------------------
# Audit R2: release_authorized is bound to the attested HEAD sha
# ---------------------------------------------------------------------------


_MOVE_HEAD_SEQ = itertools.count()


def _move_head(repo: Path, message: str = "move head") -> None:
    """Commit new content, which is what "a commit after authorize-release" means.

    This helper used to commit `--allow-empty`. That moved HEAD without
    changing a byte, which was indistinguishable from real work only because
    the receipt bound HEAD — a proxy for the tree it claimed to attest. The
    receipt now binds worktree content, so an empty commit deliberately does
    *not* void it (see `test_a_no_op_commit_does_not_void_the_release`), and
    a helper that made one would be asserting the proxy rather than the
    subject.
    """
    marker = repo / f"moved_{next(_MOVE_HEAD_SEQ)}.txt"
    marker.write_text(f"{message}\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo), "add", marker.name],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", message],
        check=True,
        capture_output=True,
    )


def test_release_does_not_survive_head_movement(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A commit after authorize-release voids the release unless a PR is open."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="r2")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is True
    _move_head(stacked_repo)
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is False
    assert "stale" in reason
    # The phase file still says release_authorized; that word alone is not an attestation.
    assert json.loads(state_path(stacked_repo).read_text())["phase"] == "release_authorized"


def test_a_no_op_commit_does_not_void_the_release(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The proxy-binding defect, pinned closed.

    An empty commit, an amend, a rebase that replays identical content — each
    moves HEAD while the attested tree is untouched. Under `head_sha` binding
    every one of them voided a receipt that was still true, and a gate that
    expires for reasons unrelated to its subject is what teaches agents to
    re-stamp on a schedule rather than to do the work.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="p6-noop")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    subprocess.run(
        ["git", "-C", str(stacked_repo), "commit", "--allow-empty", "-m", "no-op"],
        check=True,
        capture_output=True,
    )
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is True, reason
    assert "content" in reason


def test_a_content_change_still_voids_the_release(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The half that must not be traded away for the convenience above.

    An uncommitted edit is enough: the binding is worktree content, not the
    committed tree, so work done after attestation is never carried by it.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="p6-content")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    (stacked_repo / "unattested.py").write_text("print('new work')\n", encoding="utf-8")
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is False
    assert "stale" in reason


def test_authorize_release_still_works_with_no_kernel_receipt(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The corpus exemption `eace25ed` protected, kept protected.

    `authorize_release` has no changed-path context, so it cannot tell a
    corpus-only `/ff` changeset from a code one. Absence of a kernel receipt
    therefore authorizes. Requiring one is what broke the `/ff` publish flow,
    and CANONICAL_LAW §6.2.9 item 6 still forbids it.
    """
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="p6-corpus")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    assert not (stacked_repo / ".l9" / "autonomy" / "kernel-receipt.json").exists()
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    assert receipt["tree_digest"]


def _record_kernel_evidence(repo: Path, *, delta_path: str = "evidenced.txt") -> dict:
    """Produce a real v2 kernel receipt in `repo` through the sole writer."""
    import kernel_gate

    target = repo / delta_path
    target.write_text("touched\n", encoding="utf-8")
    validated = repo / "validated.txt"
    validated.write_text("validated\n", encoding="utf-8")
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
        "    note: narrowed a guard\n"
        "  - path: validated.txt\n"
        "    kernel: validate_repair\n"
        "    note: validated the recorded kernel evidence\n"
        "---\n"
        "\n## Recursive Alignment\n\napplied\n"
        "\n## Validate & Repair\n\nran the checks\n",
        encoding="utf-8",
    )
    return kernel_gate.record(repo, gov=ROOT)


def test_authorize_release_annotates_kernels_from_the_kernel_receipt(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real apply must read as one: evidence overwrites the self-report."""
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setenv("GOV_ROOT", str(ROOT))
    begin(stacked_repo, contract_id="r2-evidenced")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    kernel_receipt = _record_kernel_evidence(stacked_repo)
    receipt = authorize_release(stacked_repo)
    assert receipt["kernel_evidence"] == "evidenced"
    for label in ("recursive_alignment", "validate_repair"):
        entry = receipt["kernels"][label]
        assert entry["status"] == "evidenced"
        assert entry["self_reported"] == "passed"
        assert entry["evidence"] == "evidenced"
        assert entry["report_rel"] == kernel_receipt["report_rel"]
        assert entry["report_sha256"] == kernel_receipt["report_sha256"]
        assert entry["applied_at"] == kernel_receipt["applied_at"]
        assert entry["delta_count"] == 2
    assert status_dict(stacked_repo)["kernel_evidence"] == "evidenced"


def test_authorize_release_marks_kernels_absent_when_no_receipt(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No receipt: still authorizes, and says so instead of looking applied."""
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="r2-absent")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    receipt = authorize_release(stacked_repo)
    assert receipt["phase"] == "release_authorized"
    assert receipt["kernel_evidence"] == "absent"
    for label in ("recursive_alignment", "validate_repair"):
        entry = receipt["kernels"][label]
        assert entry["status"] == "passed", "the self-report stands, labelled"
        assert entry["evidence"] == "absent"
        assert entry["note"] == "kernel_gate.precommit decides exemption"
    assert status_dict(stacked_repo)["kernel_evidence"] == "absent"


def test_status_dict_reports_stale_kernel_evidence_live(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Editing the apply report after release flips the live status to stale."""
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setenv("GOV_ROOT", str(ROOT))
    begin(stacked_repo, contract_id="r2-stale")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    _record_kernel_evidence(stacked_repo)
    receipt = authorize_release(stacked_repo)
    assert receipt["kernel_evidence"] == "evidenced"
    report = stacked_repo / ".l9" / "autonomy" / "kernel-apply.md"
    report.write_text(report.read_text(encoding="utf-8") + "\nedited after the fact\n")
    assert status_dict(stacked_repo)["kernel_evidence"] == "stale"
    # And a fresh authorize refuses the stale receipt rather than re-annotating it.
    with pytest.raises(RuntimeError, match="no longer re-derives"):
        authorize_release(stacked_repo)


def test_authorize_release_refuses_a_kernel_receipt_that_no_longer_derives(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A present receipt must re-derive. Present-and-false is not absent."""
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="p6-kernel-false")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    kernel_receipt = stacked_repo / ".l9" / "autonomy" / "kernel-receipt.json"
    kernel_receipt.parent.mkdir(parents=True, exist_ok=True)
    # A v1 receipt: the unbound form, rejected by name (CANONICAL_LAW §6.2.9 item 5).
    kernel_receipt.write_text(
        json.dumps({"schema": "l9.kernel_receipt.v1", "phase": "recorded"}),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="no longer re-derives"):
        authorize_release(stacked_repo)


def test_authorize_release_refuses_a_malformed_existing_kernel_receipt(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing file that is not JSON is a claim, not absence.

    load_receipt used to return None for both a missing file and a
    broken one, so authorize-release took the corpus exemption. The
    exemption is only for genuine absence (CANONICAL_LAW §6.2.9 item 6).
    """
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="p6-kernel-malformed")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    kernel_receipt = stacked_repo / ".l9" / "autonomy" / "kernel-receipt.json"
    kernel_receipt.parent.mkdir(parents=True, exist_ok=True)
    kernel_receipt.write_text("{not-json", encoding="utf-8")
    assert kernel_evidence(stacked_repo)["status"] == "stale"
    with pytest.raises(RuntimeError, match="no longer re-derives"):
        authorize_release(stacked_repo)


def test_authorize_release_refuses_a_non_object_existing_kernel_receipt(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A JSON array (or other non-object) is present-and-false, not absent."""
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="p6-kernel-array")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    kernel_receipt = stacked_repo / ".l9" / "autonomy" / "kernel-receipt.json"
    kernel_receipt.parent.mkdir(parents=True, exist_ok=True)
    kernel_receipt.write_text("[]", encoding="utf-8")
    assert kernel_evidence(stacked_repo)["status"] == "stale"
    with pytest.raises(RuntimeError, match="no longer re-derives"):
        authorize_release(stacked_repo)


def test_remediation_of_an_open_pr_still_allows_after_head_moves(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: True)
    begin(stacked_repo, contract_id="r2-open")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    _move_head(stacked_repo)
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is True
    assert "remediation" in reason


def test_phase_file_alone_never_authorizes(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A release_authorized phase without its sha-bound receipt denies."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="r2-phase")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    receipt_path(stacked_repo).unlink()
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is False
    assert "receipt" in reason


def test_receipt_that_binds_nothing_is_refused(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receipt with no binding at all authorizes no tree."""
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="r2-nosha")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    doc = json.loads(receipt_path(stacked_repo).read_text())
    doc.pop("head_sha")
    doc.pop("tree_digest")
    receipt_path(stacked_repo).write_text(json.dumps(doc))
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is False
    assert "binds neither" in reason


def test_receipt_without_head_sha_still_authorizes_its_tree(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`head_sha` is recorded metadata as of v2, not the binding.

    Dropping it leaves a receipt that still says exactly which content it
    attested, and the verifier can still re-derive that. Refusing here would
    be refusing on the absence of a field nothing depends on.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="r2-nohead-v2")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    doc = json.loads(receipt_path(stacked_repo).read_text())
    doc.pop("head_sha")
    receipt_path(stacked_repo).write_text(json.dumps(doc))
    assert release_allows_remote(stacked_repo)[0] is True


def test_v1_receipt_is_still_honored_on_its_head_sha(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The L4 v1 receipt is a weaker proxy, not a falsehood.

    Unlike the v1 *kernel* receipt — which attested nothing and is rejected by
    name — a v1 release receipt names the exact commit it authorized. It is
    honored so the schema bump does not strand an operator mid-publish.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="r2-v1")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    doc = json.loads(receipt_path(stacked_repo).read_text())
    doc["schema"] = "l9.l4_local_release_receipt/v1"
    doc.pop("tree_digest")
    receipt_path(stacked_repo).write_text(json.dumps(doc))
    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is True
    assert "v1 receipt" in reason


# ---------------------------------------------------------------------------
# Audit R3: extend-release is the only re-bind, and it is narrow
# ---------------------------------------------------------------------------


def test_extend_release_rebinds_only_a_fast_forward_of_the_attested_head(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.setattr("l4_local.pr_open_for_branch", lambda root, branch=None: False)
    begin(stacked_repo, contract_id="r3")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    attested = authorize_release(stacked_repo)["head_sha"]
    _move_head(stacked_repo, "merge origin/main (push recovery)")
    assert release_allows_remote(stacked_repo)[0] is False

    # The claimed prior head must be the one the receipt attests.
    with pytest.raises(RuntimeError, match="not the claimed prior head"):
        extend_release(stacked_repo, from_head="0" * 40, reason="push-recovery")

    extended = extend_release(stacked_repo, from_head=attested, reason="push-recovery")
    assert extended["extended_from"] == attested
    assert extended["head_sha"] == current_head(stacked_repo)
    assert extended["extension_reason"] == "push-recovery"
    assert release_allows_remote(stacked_repo)[0] is True

    # A second extension needs the NEW attested sha, never the original one.
    _move_head(stacked_repo, "another commit")
    with pytest.raises(RuntimeError, match="not the claimed prior head"):
        extend_release(stacked_repo, from_head=attested, reason="push-recovery")


def test_extend_release_refuses_a_rewritten_history(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    begin(stacked_repo, contract_id="r3-rewrite")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    attested = authorize_release(stacked_repo)["head_sha"]
    subprocess.run(
        ["git", "-C", str(stacked_repo), "commit", "--amend", "--allow-empty", "-m", "rewritten"],
        check=True,
        capture_output=True,
    )
    with pytest.raises(RuntimeError, match="not an ancestor"):
        extend_release(stacked_repo, from_head=attested, reason="push-recovery")


def test_extend_release_requires_a_release_receipt(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="r3-none")
    with pytest.raises(RuntimeError, match="release_authorized receipt"):
        extend_release(stacked_repo, from_head="0" * 40, reason="push-recovery")


def test_gate_allows_local_commit(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    reason = evaluate(
        "Bash",
        {"command": "git commit -m 'local only'"},
        root=stacked_repo,
    )
    assert reason is None


def test_breakglass_allows(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("L9_LOCAL_PUSH_AUTHORIZED", "human override")
    allowed, _ = release_allows_remote(stacked_repo)
    assert allowed


def test_workspace_from_event_uses_workspace_roots_when_cwd_empty(
    stacked_repo: Path,
) -> None:
    """Cursor beforeShellExecution often sends cwd="" and the checkout in workspace_roots."""
    event = {
        "cwd": "",
        "workspace_roots": [str(stacked_repo)],
        "transcript_path": "unused",
    }
    assert workspace_from_event(event) == stacked_repo.resolve()


def test_cli_check_remote_exit_codes(stacked_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    cli = ROOT / "ops" / "autonomy" / "l4_local.py"
    denied = subprocess.run(
        [sys.executable, str(cli), "--workspace", str(stacked_repo), "check-remote"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert denied.returncode == 2
    begin(stacked_repo)
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    ok = subprocess.run(
        [sys.executable, str(cli), "--workspace", str(stacked_repo), "check-remote"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert ok.returncode == 0
    assert json.loads(ok.stdout)["allowed"] is True


# -- CI-016 / IMP-14: pr_template resolves against the RELEASED repo ----------
# The field was the literal "PULL_REQUEST_TEMPLATE.md" in every receipt, so a
# receipt written in a repository with no template named the governance clone's
# default as if it were that repo's own.


def test_pr_template_is_none_when_the_released_repo_has_none(tmp_path: Path) -> None:
    assert resolve_pr_template(tmp_path) is None


@pytest.mark.parametrize(
    "rel",
    [
        ".github/pull_request_template.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "docs/PULL_REQUEST_TEMPLATE.md",
    ],
)
def test_pr_template_found_at_each_standard_location(tmp_path: Path, rel: str) -> None:
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("## Summary\n", encoding="utf-8")
    assert resolve_pr_template(tmp_path) == rel


def test_pr_template_prefers_github_default(tmp_path: Path) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "pull_request_template.md").write_text("gh", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "PULL_REQUEST_TEMPLATE.md").write_text("docs", encoding="utf-8")
    assert resolve_pr_template(tmp_path) == ".github/pull_request_template.md"


def test_pr_template_never_reports_the_governance_default_for_a_bare_repo(
    stacked_repo: Path,
) -> None:
    """The done_when: a receipt in a repo without a template says null."""
    for rel in (
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/pull_request_template.md",
        "docs/PULL_REQUEST_TEMPLATE.md",
    ):
        assert not (stacked_repo / rel).exists(), f"fixture unexpectedly ships {rel}"
    begin(stacked_repo, contract_id="ci-016")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    receipt = authorize_release(stacked_repo)
    assert receipt["pr_template"] is None
    assert status_dict(stacked_repo)["pr_template"] is None


def test_status_dict_exposes_stale_when_content_changes(stacked_repo: Path) -> None:
    """`make l4-status` reports staleness against what the receipt binds.

    It used to report it against HEAD, so an empty commit made the status line
    say "stale" about an attestation that was still true.
    """
    begin(stacked_repo, contract_id="ci-016-stale")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    status = status_dict(stacked_repo)
    assert status["stale"] is False
    assert status["tree_digest"]
    subprocess.run(
        ["git", "-C", str(stacked_repo), "commit", "--allow-empty", "-m", "move head"],
        check=True,
        capture_output=True,
    )
    assert status_dict(stacked_repo)["stale"] is False
    _move_head(stacked_repo, "real work")
    moved = status_dict(stacked_repo)
    assert moved["stale"] is True
    assert moved["head"] != (moved["receipt"] or {}).get("head_sha")


def test_pr_template_names_the_released_repos_own_template(stacked_repo: Path) -> None:
    (stacked_repo / ".github").mkdir(exist_ok=True)
    (stacked_repo / ".github" / "pull_request_template.md").write_text("x", encoding="utf-8")
    begin(stacked_repo, contract_id="ci-016b")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    receipt = authorize_release(stacked_repo)
    assert receipt["pr_template"] == ".github/pull_request_template.md"


# ---------------------------------------------------------------------------
# Workspace-scoped state: one repo's release never authorizes another's push
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    """Local git helper.

    Deliberately not imported from tests/ops/autonomy/conftest.py: under a
    full-suite run pytest's rootdir puts the REPO-ROOT conftest on sys.path, so
    `from conftest import git_in` resolves to the wrong module and the whole
    file fails to collect. A three-line helper beats a fragile import.
    """
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _sibling_repo(tmp_path: Path, name: str, branch: str) -> Path:
    """A second checkout carrying the SAME branch name as `stacked_repo`."""
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")
    _git(repo, "branch", "-M", "main")
    _git(repo, "checkout", "-b", branch)
    return repo


def test_release_in_one_workspace_does_not_authorize_another(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reported hole: a shared state dir + a shared branch name.

    Every repository in the fleet carries the same branch name, so matching on
    `stacked_branch` alone let an authorize-release in one checkout satisfy the
    gate in every other checkout that shared the machine-wide state directory.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    shared = tmp_path / "shared-state"
    monkeypatch.setenv("L9_AUTONOMY_STATE_DIR", str(shared))

    begin(stacked_repo, contract_id="ci-scope")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is True

    other = _sibling_repo(tmp_path, "other", "feat/l4-stack")
    allowed, reason = release_allows_remote(other)
    assert allowed is False, reason
    assert "mid-execution" in reason or "workspace" in reason


def test_relocated_state_dir_is_namespaced_per_workspace(
    stacked_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shared = tmp_path / "shared-state"
    monkeypatch.setenv("L9_AUTONOMY_STATE_DIR", str(shared))
    other = _sibling_repo(tmp_path, "other-ns", "feat/l4-stack")

    mine = receipt_path(stacked_repo)
    theirs = receipt_path(other)
    assert mine != theirs, "two workspaces must not share one receipt file"
    assert shared in mine.parents and shared in theirs.parents


def test_unstamped_legacy_receipt_is_refused(
    stacked_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receipt from before workspace stamping cannot prove it belongs here.

    It was written when one directory served every repository, so it is exactly
    the file that must not be trusted. Failing closed costs a re-authorize.
    """
    monkeypatch.delenv("L9_LOCAL_PUSH_AUTHORIZED", raising=False)
    monkeypatch.setenv("L9_L4_LOCAL_AUTONOMY", "1")
    monkeypatch.delenv("L9_AUTONOMY_STATE_DIR", raising=False)

    begin(stacked_repo, contract_id="ci-legacy")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    authorize_release(stacked_repo)
    assert release_allows_remote(stacked_repo)[0] is True

    for path in (receipt_path(stacked_repo), state_path(stacked_repo)):
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.pop("workspace", None)
        path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    allowed, reason = release_allows_remote(stacked_repo)
    assert allowed is False
    assert "no workspace stamp" in reason


def test_receipt_and_phase_carry_the_workspace_they_authorize(stacked_repo: Path) -> None:
    begin(stacked_repo, contract_id="ci-stamp")
    record_kernels(stacked_repo, recursive_alignment="passed", validate_repair="passed")
    receipt = authorize_release(stacked_repo)
    identity = workspace_identity(stacked_repo)
    assert receipt["workspace"] == identity
    assert json.loads(state_path(stacked_repo).read_text(encoding="utf-8"))["workspace"] == identity
