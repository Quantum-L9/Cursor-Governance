"""W5 — disposition IR on repo_truth.discover, not a replacement."""

from __future__ import annotations

from pathlib import Path

from compiler.repo_truth import DISPOSITIONS, classify_dispositions, discover


def test_existing_path_is_keep_not_create() -> None:
    root = Path(__file__).resolve().parents[4]
    truth = discover(root)
    rows = classify_dispositions(
        ["Reuse the existing environment/program-execution/compiler/intent.py parser."],
        truth,
    )
    assert rows[0].disposition == "KEEP"
    assert rows[0].path == "environment/program-execution/compiler/intent.py"
    assert "CREATE" not in {row.disposition for row in rows}


def test_unknown_requirement_stays_unknown() -> None:
    root = Path(__file__).resolve().parents[4]
    rows = classify_dispositions(
        ["Invent a seam nobody named."],
        discover(root),
    )
    assert rows[0].disposition == "UNKNOWN"
    assert rows[0].path is None


def test_disposition_vocabulary_is_complete() -> None:
    assert "UNKNOWN" in DISPOSITIONS
    assert "CREATE" in DISPOSITIONS
    assert "KEEP" in DISPOSITIONS
