#!/usr/bin/env python3
"""First tests for the apply-report predicates.

`ops/autonomy/kernel_predicates.py` shipped as a complete 196-line module with
zero importers and zero tests — it arrived as parked session-end dirt rather
than from the reverted #545 design. Its correctness was inferred. These tests
measure it, because `kernel_gate.record` now refuses to write a receipt on its
verdict and `verify_tree` re-runs it on every local `make pr`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _preds():
    import sys

    autonomy = str(ROOT / "ops" / "autonomy")
    if autonomy not in sys.path:
        sys.path.insert(0, autonomy)
    import kernel_predicates

    return kernel_predicates


VALID = """---
schema: l9.kernel_apply.v1
kernels: [recursive_alignment, validate_repair]
convergence_status: converged
deltas:
  - path: touched.py
    kernel: recursive_alignment
    note: narrowed the guard
---

## Recursive Alignment

surfaced and applied

## Validate & Repair

ran the checks
"""


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "touched.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / ".l9" / "autonomy").mkdir(parents=True)
    return tmp_path


def _write(workspace: Path, text: str) -> Path:
    report = workspace / ".l9" / "autonomy" / "kernel-apply.md"
    report.write_text(text, encoding="utf-8")
    return report


def test_valid_report_has_no_structural_errors(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, VALID)
    assert preds.report_structure(workspace, report) == []
    assert preds.load_validated_deltas(workspace, report) == [
        {"path": "touched.py", "kernel": "recursive_alignment", "note": "narrowed the guard"}
    ]


@pytest.mark.parametrize(
    ("label", "escape"),
    [
        ("parent traversal", "../kernel-apply.md"),
        ("deep traversal", "../../../../etc/passwd"),
        ("absolute path", "/tmp/kernel-apply.md"),
        ("sibling dir", ".l9/other/kernel-apply.md"),
    ],
)
def test_path_escape_is_refused(workspace: Path, label: str, escape: str) -> None:
    """The report must live in workspace/.l9/autonomy/ or the digest is meaningless."""
    preds = _preds()
    with pytest.raises(preds.ReportError):
        preds.confine_report_path(workspace, Path(escape))


def test_confinement_accepts_the_canonical_location(workspace: Path) -> None:
    preds = _preds()
    resolved = preds.confine_report_path(workspace, Path(".l9/autonomy/kernel-apply.md"))
    assert resolved == (workspace / ".l9" / "autonomy" / "kernel-apply.md").resolve()


def test_empty_deltas_is_refused(workspace: Path) -> None:
    """An apply with no deltas is a claim that nothing changed — not evidence."""
    preds = _preds()
    report = _write(workspace, VALID.replace("deltas:", "deltas: []\n_unused:"))
    errors = preds.report_structure(workspace, report)
    assert any("deltas must be a non-empty list" in err for err in errors)


def test_missing_deltas_key_is_refused(workspace: Path) -> None:
    preds = _preds()
    text = VALID.split("deltas:")[0] + "---\n\n## Recursive Alignment\n\n## Validate & Repair\n"
    report = _write(workspace, text)
    errors = preds.report_structure(workspace, report)
    assert any("deltas" in err for err in errors)


def test_wrong_schema_is_refused(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, VALID.replace("l9.kernel_apply.v1", "l9.kernel_apply.v99"))
    assert any("schema must be" in err for err in preds.report_structure(workspace, report))


def test_one_kernel_only_is_refused(workspace: Path) -> None:
    preds = _preds()
    report = _write(
        workspace, VALID.replace("[recursive_alignment, validate_repair]", "[recursive_alignment]")
    )
    errors = preds.report_structure(workspace, report)
    assert any("must include recursive_alignment and validate_repair" in err for err in errors)


def test_bad_convergence_status_is_refused(workspace: Path) -> None:
    preds = _preds()
    report = _write(
        workspace, VALID.replace("convergence_status: converged", "convergence_status: fine")
    )
    errors = preds.report_structure(workspace, report)
    assert any("convergence_status" in err for err in errors)


def test_missing_body_headings_are_refused(workspace: Path) -> None:
    preds = _preds()
    text = VALID.split("## Recursive Alignment")[0] + "nothing here\n"
    report = _write(workspace, text)
    errors = preds.report_structure(workspace, report)
    assert any("Recursive Alignment" in err for err in errors)
    assert any("Validate & Repair" in err for err in errors)


def test_missing_frontmatter_is_refused(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, "# just prose\n\nno frontmatter at all\n")
    assert any("frontmatter" in err for err in preds.report_structure(workspace, report))


def test_delta_path_must_exist(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, VALID.replace("touched.py", "never/existed.py"))
    with pytest.raises(preds.ReportError):
        preds.load_validated_deltas(workspace, report)


def test_delta_path_may_not_traverse_out(workspace: Path) -> None:
    preds = _preds()
    deltas = [{"path": "../outside.py", "kernel": "validate_repair", "note": "n"}]
    errors = preds.delta_paths_exist(workspace, deltas)
    assert any("not workspace-relative" in err for err in errors)


def test_delta_path_may_not_be_absolute(workspace: Path) -> None:
    preds = _preds()
    deltas = [{"path": "/etc/passwd", "kernel": "validate_repair", "note": "n"}]
    errors = preds.delta_paths_exist(workspace, deltas)
    assert any("not workspace-relative" in err for err in errors)


def test_report_sha_detects_edit(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, VALID)
    digest = preds.sha256_file(report)
    assert preds.report_sha(report, digest) == []
    report.write_text(VALID + "\nlater\n", encoding="utf-8")
    assert preds.report_sha(report, digest) != []


def test_report_sha_refuses_an_unset_claim(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, VALID)
    assert any("unset" in err for err in preds.report_sha(report, ""))


def test_run_predicates_needs_report_rel(workspace: Path) -> None:
    preds = _preds()
    _write(workspace, VALID)
    assert any("report_rel is unset" in err for err in preds.run_predicates(workspace, {}))


def test_run_predicates_round_trip(workspace: Path) -> None:
    preds = _preds()
    report = _write(workspace, VALID)
    receipt = {
        "report_rel": ".l9/autonomy/kernel-apply.md",
        "report_sha256": preds.sha256_file(report),
    }
    assert preds.run_predicates(workspace, receipt) == []


def test_run_predicates_rejects_a_receipt_pointing_outside(workspace: Path) -> None:
    preds = _preds()
    _write(workspace, VALID)
    receipt = {"report_rel": "../../elsewhere.md", "report_sha256": "0" * 64}
    assert preds.run_predicates(workspace, receipt) != []
