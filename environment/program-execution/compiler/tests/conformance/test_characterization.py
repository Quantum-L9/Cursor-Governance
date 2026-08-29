"""W1.1 — characterization of journeys A–J. Records route and losses; no semantic product fixes."""

from __future__ import annotations

from pathlib import Path

from compiler.tests.conformance.shadow_runner import compile_fixture

JOURNEYS = {
    "A": "01_one_sentence_intent",
    "B": "02_brain_dump",
    "C": "12_explicit_target",
    "D": "03_long_architecture_adr",
    "E": "03_long_architecture_adr",
    "F": "04_lowercase_prohibition",
    "G": "09_detailed_technical_spec",
    "H": "06_existing_feature_requested_again",
    "I": "08_vague_business_goal",
    "J": "13_authority_ambiguity",
}


def test_journeys_a_through_j_record_route_and_stages(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[5]
    records = []
    for letter, fixture_id in JOURNEYS.items():
        fixture = Path(__file__).resolve().parent / "fixtures" / fixture_id
        report = compile_fixture(fixture, repo_root=root)
        assert report.kind, f"{letter} produced no kind"
        assert report.stages, f"{letter} produced no stages"
        records.append(
            {
                "journey": letter,
                "fixture": fixture_id,
                "kind": report.kind,
                "route": report.route,
                "stages": report.stages,
                "losses": report.losses,
                "side_effects": report.side_effects,
            }
        )
    assert len(records) == 10
    assert all(not row["side_effects"] for row in records)
