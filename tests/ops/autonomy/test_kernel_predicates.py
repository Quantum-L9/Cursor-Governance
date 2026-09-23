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
from typing import Any

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
    note: Added input validation to prevent null pointer on empty collections
  - path: validated.py
    kernel: validate_repair
    note: Updated test assertions to cover edge case discovered during RA
---

## Recursive Alignment

Inspected touched.py and identified missing null guard. Added validation.

## Validate & Repair

Ran pytest on the touched module. All 5 assertions passed. Added edge case coverage.
"""


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "touched.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "validated.py").write_text("y = 2\n", encoding="utf-8")
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
        {
            "path": "touched.py",
            "kernel": "recursive_alignment",
            "note": "Added input validation to prevent null pointer on empty collections",
        },
        {
            "path": "validated.py",
            "kernel": "validate_repair",
            "note": "Updated test assertions to cover edge case discovered during RA",
        },
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


# -----------------------------------------------------------------------------
# Phase 1 hardening predicates
# -----------------------------------------------------------------------------


def test_delta_path_directory_is_rejected(workspace: Path) -> None:
    """A delta cannot be a directory — only regular files are valid."""
    preds = _preds()
    (workspace / "some_dir").mkdir()
    deltas = [{"path": "some_dir", "kernel": "recursive_alignment", "note": "applied RA"}]
    errors = preds.delta_paths_exist(workspace, deltas)
    assert any("directory, not a file" in err for err in errors)


def test_delta_path_symlink_is_rejected(workspace: Path) -> None:
    """A delta cannot be a dangling symlink."""
    preds = _preds()
    link = workspace / "broken_link"
    link.symlink_to(workspace / "nonexistent_target")
    deltas = [{"path": "broken_link", "kernel": "recursive_alignment", "note": "n"}]
    errors = preds.delta_paths_exist(workspace, deltas)
    assert any("symlink" in err for err in errors)


def test_deltas_cover_diff_catches_omitted_paths(workspace: Path) -> None:
    """Changed paths not in deltas are caught."""
    preds = _preds()
    deltas = [{"path": "touched.py", "kernel": "recursive_alignment", "note": "n"}]
    changed = ["touched.py", "another.py"]
    errors = preds.deltas_cover_diff(deltas, changed)
    assert any("another.py" in err and "not in deltas" in err for err in errors)


def test_deltas_cover_diff_catches_invented_paths(workspace: Path) -> None:
    """Paths in deltas that are not in the changed set are flagged as invented."""
    preds = _preds()
    deltas = [
        {"path": "touched.py", "kernel": "recursive_alignment", "note": "n"},
        {"path": "invented.py", "kernel": "validate_repair", "note": "n"},
    ]
    changed = ["touched.py"]
    errors = preds.deltas_cover_diff(deltas, changed)
    assert any("invented.py" in err and "invented" in err for err in errors)


def test_deltas_cover_diff_exempts_corpus_paths(workspace: Path) -> None:
    """Corpus paths (WIP/, docs/plans/) are exempt from coverage check."""
    preds = _preds()
    deltas = [{"path": "touched.py", "kernel": "recursive_alignment", "note": "n"}]
    changed = ["touched.py", "WIP/notes.md", "docs/plans/my.plan.md"]
    errors = preds.deltas_cover_diff(deltas, changed)
    # WIP and docs/plans should not trigger errors
    assert not any("WIP/" in err for err in errors)
    assert not any("docs/plans/" in err for err in errors)


def test_deltas_cover_diff_exempts_generated_paths(workspace: Path) -> None:
    """Generated paths are exempt from coverage check."""
    preds = _preds()
    deltas = [{"path": "touched.py", "kernel": "recursive_alignment", "note": "n"}]
    changed = ["touched.py", "ops/generated/skill-registry.json"]
    errors = preds.deltas_cover_diff(deltas, changed)
    assert not any("skill-registry" in err for err in errors)


def test_both_kernels_need_deltas(workspace: Path) -> None:
    """Each kernel must have at least one delta."""
    preds = _preds()
    # Only recursive_alignment deltas
    deltas = [
        {"path": "a.py", "kernel": "recursive_alignment", "note": "n"},
        {"path": "b.py", "kernel": "recursive_alignment", "note": "n"},
    ]
    errors = preds.both_kernels_have_deltas(deltas)
    assert any("validate_repair" in err for err in errors)
    assert not any("recursive_alignment" in err for err in errors)


def test_notes_not_template_rejects_boilerplate(workspace: Path) -> None:
    """Template placeholder notes are rejected."""
    preds = _preds()
    deltas = [
        {
            "path": "a.py",
            "kernel": "recursive_alignment",
            "note": "what the kernel changed and why",
        },
    ]
    errors = preds.notes_not_template(deltas)
    assert any("template boilerplate" in err for err in errors)


def test_notes_not_template_accepts_real_notes(workspace: Path) -> None:
    """Real, specific notes pass the check."""
    preds = _preds()
    deltas = [
        {
            "path": "a.py",
            "kernel": "recursive_alignment",
            "note": "Fixed null check in parse_input",
        },
    ]
    errors = preds.notes_not_template(deltas)
    assert errors == []


def test_headings_are_atx_rejects_non_heading_substring(workspace: Path) -> None:
    """A substring match without ATX format is rejected."""
    preds = _preds()
    # Has the text but not as a proper ## heading
    body = "This mentions Recursive Alignment and Validate & Repair in prose."
    errors = preds.headings_are_atx(body)
    assert len(errors) == 2
    assert any("ATX heading" in err or "missing heading" in err for err in errors)


def test_headings_are_atx_accepts_proper_headings(workspace: Path) -> None:
    """Proper ATX headings pass."""
    preds = _preds()
    body = "## Recursive Alignment\n\ntext\n\n## Validate & Repair\n\nmore text"
    errors = preds.headings_are_atx(body)
    assert errors == []


def test_closed_frontmatter_rejects_extra_keys(workspace: Path) -> None:
    """Unexpected frontmatter keys are rejected."""
    preds = _preds()
    data = {
        "schema": "l9.kernel_apply.v1",
        "kernels": ["recursive_alignment", "validate_repair"],
        "extra_garbage": "should not be here",
    }
    errors = preds.closed_frontmatter(data)
    assert any("extra_garbage" in err for err in errors)


def test_closed_frontmatter_accepts_allowed_keys(workspace: Path) -> None:
    """All allowed keys pass the check."""
    preds = _preds()
    data = {
        "schema": "l9.kernel_apply.v1",
        "kernels": ["recursive_alignment", "validate_repair"],
        "convergence_status": "converged",
        "deltas": [],
        "findings": [],
        "validation": [],
        "unknowns": [],
        "passes_run": [],
        "passes_skipped": [],
        "audit_scope": "full",
        "_body": "## RA\n\n## VR\n",  # internal, always allowed
    }
    errors = preds.closed_frontmatter(data)
    assert errors == []


def test_no_duplicate_delta_paths_catches_duplicates(workspace: Path) -> None:
    """Duplicate delta paths are rejected."""
    preds = _preds()
    deltas = [
        {"path": "same.py", "kernel": "recursive_alignment", "note": "first"},
        {"path": "same.py", "kernel": "validate_repair", "note": "second"},
    ]
    errors = preds.no_duplicate_delta_paths(deltas)
    assert any("duplicate" in err and "same.py" in err for err in errors)


def test_no_duplicate_delta_paths_accepts_unique(workspace: Path) -> None:
    """Unique paths pass."""
    preds = _preds()
    deltas = [
        {"path": "one.py", "kernel": "recursive_alignment", "note": "first"},
        {"path": "two.py", "kernel": "validate_repair", "note": "second"},
    ]
    errors = preds.no_duplicate_delta_paths(deltas)
    assert errors == []


def test_run_predicates_with_diff_catches_coverage_gaps(workspace: Path) -> None:
    """run_predicates_with_diff includes diff coverage check."""
    preds = _preds()
    report = _write(workspace, VALID)
    receipt = {
        "report_rel": ".l9/autonomy/kernel-apply.md",
        "report_sha256": preds.sha256_file(report),
    }
    # Pass in a changed file that is not in the deltas
    errors = preds.run_predicates_with_diff(
        workspace, receipt, ["touched.py", "validated.py", "extra.py"]
    )
    assert any("extra.py" in err for err in errors)


# -----------------------------------------------------------------------------
# Phase 2: Finding ledger predicate tests (v2 only)
# -----------------------------------------------------------------------------

# Valid v2 report for testing
VALID_V2 = """---
schema: l9.kernel_apply.v2
kernels: [recursive_alignment, validate_repair]
convergence_status: converged
deltas:
  - path: touched.py
    kernel: recursive_alignment
    note: Added input validation to prevent null pointer on empty collections
  - path: validated.py
    kernel: validate_repair
    note: Updated test assertions to cover edge case discovered during RA
findings:
  - id: RA-001
    kernel: recursive_alignment
    path: touched.py
    severity: Medium
    confidence: Confirmed
    rule: CANONICAL_LAW.md
    evidence: Input validation was missing for empty list case
    status: Resolved
    close_validation: tests/test_touched.py
passes_run:
  - context_and_scope_lock
  - reconciliation_and_convergence
  - full_pytest_suite
passes_skipped: []
unknowns: []
audit_scope: Full recursive alignment + validate & repair on touched.py and validated.py
---

## Recursive Alignment

Inspected touched.py and identified missing null guard. Added validation.

## Validate & Repair

Ran pytest on the touched module. All 5 assertions passed. Added edge case coverage.
"""


@pytest.fixture
def workspace_v2(tmp_path: Path) -> Path:
    (tmp_path / "touched.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "validated.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_touched.py").write_text("def test(): pass\n", encoding="utf-8")
    (tmp_path / ".l9" / "autonomy").mkdir(parents=True)
    return tmp_path


def test_v2_report_validates_successfully(workspace_v2: Path) -> None:
    """A complete v2 report should pass all predicates."""
    preds = _preds()
    report = _write(workspace_v2, VALID_V2)
    assert preds.report_structure(workspace_v2, report) == []


def test_v2_missing_findings_key_is_rejected(workspace_v2: Path) -> None:
    """v2 reports require the findings key."""
    preds = _preds()
    text = VALID_V2.replace("findings:", "_hidden_findings:")
    _write(workspace_v2, text)  # Write but don't use; we test the predicate directly
    data = {"schema": "l9.kernel_apply.v2"}
    errors = preds.findings_nonempty_or_explicit_clean(data)
    assert any("findings" in err for err in errors)


def test_v2_empty_findings_without_audit_scope_is_rejected(workspace_v2: Path) -> None:
    """Empty findings requires audit_scope."""
    preds = _preds()
    data = {
        "schema": "l9.kernel_apply.v2",
        "findings": [],
        "passes_run": ["context_and_scope_lock", "reconciliation_and_convergence"],
    }
    errors = preds.findings_nonempty_or_explicit_clean(data)
    assert any("audit_scope" in err for err in errors)


def test_v2_empty_findings_without_passes_run_is_rejected(workspace_v2: Path) -> None:
    """Empty findings requires passes_run."""
    preds = _preds()
    data = {
        "schema": "l9.kernel_apply.v2",
        "findings": [],
        "audit_scope": "Full audit",
    }
    errors = preds.findings_nonempty_or_explicit_clean(data)
    assert any("passes_run" in err for err in errors)


def test_v2_empty_findings_with_audit_scope_and_passes_is_ok(workspace_v2: Path) -> None:
    """Empty findings with proper explanation passes."""
    preds = _preds()
    data = {
        "schema": "l9.kernel_apply.v2",
        "findings": [],
        "audit_scope": "Full audit of all changed files",
        "passes_run": ["context_and_scope_lock", "reconciliation_and_convergence"],
    }
    errors = preds.findings_nonempty_or_explicit_clean(data)
    assert errors == []


def test_v2_finding_paths_must_exist(workspace_v2: Path) -> None:
    """Finding paths must point to existing files."""
    preds = _preds()
    findings = [{"path": "nonexistent/file.py"}]
    errors = preds.finding_paths_exist(workspace_v2, findings)
    assert any("does not exist" in err for err in errors)


def test_v2_finding_rules_must_exist(workspace_v2: Path) -> None:
    """Finding rules must be valid references."""
    preds = _preds()
    findings = [{"rule": "rules/99-fake-rule.mdc"}]
    errors = preds.finding_rules_exist(workspace_v2, findings)
    assert any("does not exist" in err for err in errors)


def test_v2_finding_rules_accept_governance_docs(workspace_v2: Path) -> None:
    """Well-known governance docs are valid rule references."""
    preds = _preds()
    findings = [
        {"rule": "CANONICAL_LAW.md"},
        {"rule": "AGENTS.md"},
        {"rule": "ORG_INVARIANTS.yaml"},
    ]
    errors = preds.finding_rules_exist(workspace_v2, findings)
    assert errors == []


def test_v2_finding_rules_accept_l9_rule_ids(workspace_v2: Path) -> None:
    """L9-* and INV-* rule IDs are valid."""
    preds = _preds()
    findings = [
        {"rule": "L9-ORG-001"},
        {"rule": "INV-03"},
    ]
    errors = preds.finding_rules_exist(workspace_v2, findings)
    assert errors == []


def test_v2_resolved_requires_close_validation(workspace_v2: Path) -> None:
    """Resolved findings must have close_validation."""
    preds = _preds()
    findings = [{"id": "RA-001", "status": "Resolved", "close_validation": ""}]
    errors = preds.resolved_has_close_validation(findings)
    assert any("close_validation" in err and "RA-001" in err for err in errors)


def test_v2_resolved_with_close_validation_passes(workspace_v2: Path) -> None:
    """Resolved findings with close_validation pass."""
    preds = _preds()
    findings = [{"id": "RA-001", "status": "Resolved", "close_validation": "tests/test_foo.py"}]
    errors = preds.resolved_has_close_validation(findings)
    assert errors == []


def test_v2_convergence_blocks_on_open_critical(workspace_v2: Path) -> None:
    """Cannot claim converged with Open Critical/High findings."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v2", "convergence_status": "converged"}
    findings = [{"id": "RA-001", "status": "Open", "severity": "Critical"}]
    errors = preds.convergence_derived(data, findings)
    assert any("converged" in err and "Open" in err for err in errors)


def test_v2_convergence_allows_open_low_medium(workspace_v2: Path) -> None:
    """Converged is allowed with Open Low/Medium findings."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v2", "convergence_status": "converged"}
    findings = [
        {"id": "RA-001", "status": "Open", "severity": "Low"},
        {"id": "RA-002", "status": "Open", "severity": "Medium"},
    ]
    errors = preds.convergence_derived(data, findings)
    assert errors == []


def test_v2_convergence_allows_resolved_critical(workspace_v2: Path) -> None:
    """Converged is allowed when Critical findings are Resolved."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v2", "convergence_status": "converged"}
    findings = [{"id": "RA-001", "status": "Resolved", "severity": "Critical"}]
    errors = preds.convergence_derived(data, findings)
    assert errors == []


def test_v2_passes_run_minimum_required(workspace_v2: Path) -> None:
    """Required passes must be run."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v2", "passes_run": ["some_other_pass"]}
    errors = preds.passes_run_minimum(data)
    assert any("context_and_scope_lock" in err for err in errors)
    assert any("reconciliation_and_convergence" in err for err in errors)


def test_v2_passes_run_minimum_satisfied(workspace_v2: Path) -> None:
    """When required passes are run, check passes."""
    preds = _preds()
    data = {
        "schema": "l9.kernel_apply.v2",
        "passes_run": [
            "context_and_scope_lock",
            "reconciliation_and_convergence",
            "extra_pass",
        ],
    }
    errors = preds.passes_run_minimum(data)
    assert errors == []


def test_v2_unknowns_key_required(workspace_v2: Path) -> None:
    """v2 reports require unknowns key."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v2"}
    errors = preds.unknowns_key_required(data)
    assert any("unknowns" in err for err in errors)


def test_v2_unknowns_empty_list_is_ok(workspace_v2: Path) -> None:
    """Empty unknowns list is acceptable."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v2", "unknowns": []}
    errors = preds.unknowns_key_required(data)
    assert errors == []


def test_v1_skips_v2_predicates(workspace: Path) -> None:
    """v1 reports skip all v2 predicates."""
    preds = _preds()
    data = {"schema": "l9.kernel_apply.v1"}
    # All v2 predicates should return empty for v1
    assert preds.findings_nonempty_or_explicit_clean(data) == []
    assert preds.convergence_derived(data, []) == []
    assert preds.passes_run_minimum(data) == []
    assert preds.unknowns_key_required(data) == []


# -----------------------------------------------------------------------------
# Phase 3: Seed findings predicate tests
# -----------------------------------------------------------------------------


def test_seed_findings_generates_coverage_seeds() -> None:
    """seed_findings generates seeds for Python files without tests."""
    preds = _preds()
    changed = ["ops/autonomy/new_module.py"]
    seeds = preds.seed_findings(changed)
    assert len(seeds) == 1
    assert seeds[0]["id"] == "SEED-VR-coverage-new_module"
    assert seeds[0]["kernel"] == "validate_repair"
    assert seeds[0]["status"] == "Open"


def test_seed_findings_skips_when_test_present() -> None:
    """seed_findings skips paths that have matching test changes."""
    preds = _preds()
    changed = [
        "ops/autonomy/some_module.py",
        "tests/ops/autonomy/test_some_module.py",
    ]
    seeds = preds.seed_findings(changed)
    # Should have no seeds since test file is present
    assert len(seeds) == 0


def test_seed_findings_skips_test_files() -> None:
    """seed_findings skips test files themselves."""
    preds = _preds()
    changed = ["tests/ops/autonomy/test_something.py"]
    seeds = preds.seed_findings(changed)
    assert len(seeds) == 0


def test_seed_findings_skips_exempt_paths() -> None:
    """seed_findings skips corpus and generated paths."""
    preds = _preds()
    changed = [
        "WIP/notes.py",
        "docs/plans/my.plan.md",
        "ops/generated/skill-registry.json",
    ]
    seeds = preds.seed_findings(changed)
    assert len(seeds) == 0


def test_seed_findings_skips_non_python() -> None:
    """seed_findings only generates seeds for Python files."""
    preds = _preds()
    changed = ["ops/autonomy/README.md"]
    seeds = preds.seed_findings(changed)
    assert len(seeds) == 0


def test_seed_findings_present_catches_missing_seeds() -> None:
    """seed_findings_present catches when seeds are deleted."""
    preds = _preds()
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": "original"}]
    findings: list[dict[str, Any]] = []  # No findings - seed was deleted
    errors = preds.seed_findings_present(findings, seeds)
    assert any("missing" in err and "deleted" in err for err in errors)


def test_seed_findings_present_catches_wrong_status() -> None:
    """seed_findings_present catches seeds with wrong disposition status."""
    preds = _preds()
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": "original"}]
    findings = [{"id": "SEED-VR-coverage-test", "status": "Open"}]
    errors = preds.seed_findings_present(findings, seeds)
    assert any("must be disposed" in err for err in errors)


def test_seed_findings_present_resolved_needs_close_validation() -> None:
    """Resolved seeds need close_validation."""
    preds = _preds()
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": "original"}]
    findings = [{"id": "SEED-VR-coverage-test", "status": "Resolved", "close_validation": ""}]
    errors = preds.seed_findings_present(findings, seeds)
    assert any("close_validation" in err for err in errors)


def test_seed_findings_present_resolved_with_validation_passes() -> None:
    """Resolved seeds with close_validation pass."""
    preds = _preds()
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": "original"}]
    findings = [
        {
            "id": "SEED-VR-coverage-test",
            "status": "Resolved",
            "close_validation": "tests/test_foo.py",
        }
    ]
    errors = preds.seed_findings_present(findings, seeds)
    assert errors == []


def test_seed_findings_present_false_positive_needs_new_evidence() -> None:
    """FalsePositive seeds need updated evidence."""
    preds = _preds()
    original_evidence = "Changed file without test"
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": original_evidence}]
    findings = [
        {
            "id": "SEED-VR-coverage-test",
            "status": "FalsePositive",
            "evidence": original_evidence,  # Same as seed - not updated
        }
    ]
    errors = preds.seed_findings_present(findings, seeds)
    assert any("evidence" in err for err in errors)


def test_seed_findings_present_false_positive_with_new_evidence_passes() -> None:
    """FalsePositive seeds with new evidence pass."""
    preds = _preds()
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": "original"}]
    findings = [
        {
            "id": "SEED-VR-coverage-test",
            "status": "FalsePositive",
            "evidence": "This is a config file, not code that needs tests",
        }
    ]
    errors = preds.seed_findings_present(findings, seeds)
    assert errors == []


def test_seed_findings_present_out_of_scope_with_evidence_passes() -> None:
    """OutOfScope seeds with evidence pass."""
    preds = _preds()
    seeds = [{"id": "SEED-VR-coverage-test", "evidence": "original"}]
    findings = [
        {
            "id": "SEED-VR-coverage-test",
            "status": "OutOfScope",
            "evidence": "This module is tested in integration tests, not unit tests",
        }
    ]
    errors = preds.seed_findings_present(findings, seeds)
    assert errors == []


def test_seed_findings_present_empty_seeds_passes() -> None:
    """Empty seed list passes."""
    preds = _preds()
    seeds: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    errors = preds.seed_findings_present(findings, seeds)
    assert errors == []


# --- Leading-dot paths (./ prefix removal, not character stripping) ----------
#
# `str.lstrip("./")` strips any run of "." and "/" characters, so
# `.l9/autonomy/kernel-apply.md` became `l9/autonomy/kernel-apply.md` and
# `.github/...` became `github/...`. The report-as-delta allowance never
# matched and dot-directory finding paths could never exist.


def test_relative_path_removes_only_a_dot_slash_prefix() -> None:
    preds = _preds()
    assert preds.relative_path("./a.py") == "a.py"
    assert preds.relative_path("././a.py") == "a.py"
    assert preds.relative_path("  .github/workflows/ci.yml ") == ".github/workflows/ci.yml"
    assert preds.relative_path(".l9/autonomy/kernel-apply.md") == ".l9/autonomy/kernel-apply.md"
    assert preds.relative_path("../escape.py") == "../escape.py"


def test_deltas_cover_diff_allows_the_apply_report_as_a_delta() -> None:
    preds = _preds()
    deltas = [
        {"path": "tests/test_x.py", "kernel": "validate_repair", "note": "n"},
        {"path": ".l9/autonomy/kernel-apply.md", "kernel": "recursive_alignment", "note": "n"},
    ]
    assert preds.deltas_cover_diff(deltas, ["tests/test_x.py"]) == []


def test_deltas_cover_diff_matches_dot_directory_paths() -> None:
    preds = _preds()
    deltas = [{"path": ".github/workflows/ci.yml", "kernel": "validate_repair", "note": "n"}]
    assert preds.deltas_cover_diff(deltas, ["./.github/workflows/ci.yml"]) == []
    errors = preds.deltas_cover_diff(deltas, ["github/workflows/ci.yml"])
    assert "changed path not in deltas: github/workflows/ci.yml" in errors


def test_duplicate_delta_paths_keep_the_leading_dot() -> None:
    preds = _preds()
    deltas = [
        {"path": ".github/a.yml", "kernel": "validate_repair", "note": "n"},
        {"path": "github/a.yml", "kernel": "recursive_alignment", "note": "n"},
    ]
    assert preds.no_duplicate_delta_paths(deltas) == []


def test_finding_paths_exist_resolves_dot_directory_paths(tmp_path: Path) -> None:
    preds = _preds()
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "ci.yml").write_text("on: push\n", encoding="utf-8")
    assert preds.finding_paths_exist(tmp_path, [{"path": ".github/ci.yml"}]) == []
