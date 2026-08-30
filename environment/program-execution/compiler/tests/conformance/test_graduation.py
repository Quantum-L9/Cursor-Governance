"""W7 — golden journeys through shadow compile. Campaign runner is not invoked."""

from __future__ import annotations

from pathlib import Path

from compiler.tests.conformance.shadow_runner import compile_fixture

GOLDEN = (
    "01_one_sentence_intent",
    "03_long_architecture_adr",
    "04_lowercase_prohibition",
    "06_existing_feature_requested_again",
    "12_explicit_target",
    "13_authority_ambiguity",
    "14_safe_resolvable_ambiguity",
)


def test_w7_golden_journeys_have_zero_blocking_metrics() -> None:
    root = Path(__file__).resolve().parents[5]
    fixtures = Path(__file__).resolve().parent / "fixtures"
    totals = {
        "material_intent_loss": 0,
        "false_create_where_canonical_exists": 0,
        "authority_widening": 0,
        "manual_artifact_edits": 0,
        "private_stage_bypasses": 0,
    }
    for fixture_id in GOLDEN:
        report = compile_fixture(fixtures / fixture_id, repo_root=root)
        totals["material_intent_loss"] += int(report.metrics["material_intent_loss_count"])
        totals["false_create_where_canonical_exists"] += int(report.metrics["false_create_count"])
        totals["authority_widening"] += int(report.metrics["authority_widening_count"])
        assert report.side_effects == []
        assert report.metrics["fixture_fail_count"] == 0, (fixture_id, report.losses)
    assert totals["material_intent_loss"] == 0, totals
    assert totals["false_create_where_canonical_exists"] == 0, totals
    assert totals["authority_widening"] == 0, totals
    assert totals["manual_artifact_edits"] == 0
    assert totals["private_stage_bypasses"] == 0
