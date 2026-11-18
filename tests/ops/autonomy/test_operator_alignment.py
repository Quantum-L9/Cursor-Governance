"""Fail-closed operator-alignment consumer: no schema, no projector.

The producer contract is not frozen. These tests pin the refusals that are
lawful without it: missing receipt, digest mismatch, forged view, a Coding
Agent confidentiality PASS while a .github tree is readable, and Meta Planner
with no admissible consumer.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

import operator_alignment  # noqa: E402


def _readable_github(tmp_path: Path) -> Path:
    root = tmp_path / "dot-github"
    strategy = root / "strategy"
    strategy.mkdir(parents=True)
    (strategy / "doctrine.md").write_text("operator doctrine\n", encoding="utf-8")
    (root / "README.md").write_text("full checkout\n", encoding="utf-8")
    return root


def test_admitted_producer_receipts_are_the_emitted_bytes() -> None:
    receipt = REPO / "governance" / "operator-alignment" / "operator-doctrine.receipt.json"
    assert operator_alignment.ADMITTED_PRODUCER_RECEIPTS == frozenset({receipt.read_bytes()})


def test_consumer_does_not_parse_a_receipt_or_select_a_source() -> None:
    source = (REPO / "ops" / "autonomy" / "operator_alignment.py").read_text(encoding="utf-8")
    assert "json.loads" not in source
    assert "yaml" not in source
    assert "select_source" not in source
    assert "def project" not in source


def test_missing_receipt_is_refused(tmp_path: Path) -> None:
    view = b"view-bytes"
    digest = operator_alignment.view_digest(view)
    assert (
        operator_alignment.reject_unverified_view(receipt=None, view=view, claimed_digest=digest)
        == operator_alignment.MISSING_RECEIPT
    )
    assert (
        operator_alignment.reject_unverified_view(
            receipt=tmp_path / "no-such-receipt", view=view, claimed_digest=digest
        )
        == operator_alignment.MISSING_RECEIPT
    )


def test_digest_mismatch_is_refused(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt"
    receipt.write_bytes(b"hand-written")
    view = b'{"view":"hand-written"}'
    claimed = "sha256:" + ("0" * 64)
    assert claimed != operator_alignment.view_digest(view)
    assert (
        operator_alignment.reject_unverified_view(
            receipt=receipt, view=view, claimed_digest=claimed
        )
        == operator_alignment.DIGEST_MISMATCH
    )


def test_forged_view_with_matching_digest_is_refused(tmp_path: Path) -> None:
    view = b'{"composed":"hand-written"}'
    digest = operator_alignment.view_digest(view)
    receipt = tmp_path / "receipt"
    receipt.write_text(digest + "\n", encoding="utf-8")
    assert (
        operator_alignment.reject_unverified_view(receipt=receipt, view=view, claimed_digest=digest)
        == operator_alignment.FORGED_VIEW
    )


def test_admitted_receipt_is_accepted(tmp_path: Path) -> None:
    view = b"operator-doctrine-view"
    digest = operator_alignment.view_digest(view)
    receipt = tmp_path / "receipt"
    receipt.write_bytes(next(iter(operator_alignment.ADMITTED_PRODUCER_RECEIPTS)))
    assert (
        operator_alignment.reject_unverified_view(receipt=receipt, view=view, claimed_digest=digest)
        == operator_alignment.ADMITTED
    )


def test_pass_shaped_receipt_bytes_are_still_forged(tmp_path: Path) -> None:
    view = b"projected-view"
    digest = operator_alignment.view_digest(view)
    receipt = tmp_path / "receipt"
    receipt.write_bytes(b'{"result":"pass"}\n')
    assert (
        operator_alignment.reject_unverified_view(receipt=receipt, view=view, claimed_digest=digest)
        == operator_alignment.FORGED_VIEW
    )


def test_confidentiality_pass_rejected_when_github_is_readable(tmp_path: Path) -> None:
    root = _readable_github(tmp_path)
    assert operator_alignment.full_github_read_possible(root) is True
    result = operator_alignment.coding_agent_confidentiality(root, claimed="PASS")
    assert result == operator_alignment.BLOCKED_PRIVACY
    assert result != "PASS"


def test_unreadable_github_is_not_a_confidentiality_pass(tmp_path: Path) -> None:
    missing = tmp_path / "absent-github"
    assert operator_alignment.full_github_read_possible(missing) is False
    result = operator_alignment.coding_agent_confidentiality(missing, claimed="PASS")
    assert result == operator_alignment.BLOCKED_PRIVACY
    assert result != "PASS"


def test_meta_planner_without_consumer_is_blocked() -> None:
    assert operator_alignment.meta_planner_status(consumer_path=None) == (
        operator_alignment.BLOCKED_NO_CONSUMER
    )


def test_view_stub_is_not_a_meta_planner_consumer(tmp_path: Path) -> None:
    stub = tmp_path / "view.yaml"
    stub.write_text("result: pass\n", encoding="utf-8")
    result = operator_alignment.meta_planner_status(consumer_path=stub)
    assert result == operator_alignment.BLOCKED_NO_CONSUMER
    assert result != "ACTIVE"
