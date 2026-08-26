"""Coverage, repair, and the adversarial cases that must never acquire authority.

Every extractor here is a scripted stand-in. None of these tests reach a live
model: the point is the deterministic machinery around the model, and a suite
that needed a network call could not assert on it.
"""

from __future__ import annotations

import textwrap
import unittest
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from compiler.architecture_coverage import audit, dispositions_for, extract_semantics
from compiler.architecture_extractor import (
    ArchitectureExtractorRequest,
    ArchitectureExtractorResponse,
    DeterministicExtractor,
    ExtractorError,
)
from compiler.architecture_intent import load_architecture_intent
from compiler.architecture_ir import admit, contradictions, dedupe

DOC = textwrap.dedent(
    """\
    # Provider authority

    DeepSeek MUST be the primary governed reasoning provider.

    Perplexity is research only and MUST NOT serve reasoning traffic.

    ## Budget

    Budget downgrade MUST remain within the capability family.
    """
)


def _intent(tmp: Path, text: str = DOC):
    path = tmp / "arch.md"
    path.write_text(text, encoding="utf-8")
    return load_architecture_intent(path, target="Quantum-L9/LLM-Router", forced=True)


@dataclass
class ScriptedExtractor:
    """Answers each request from a script, and records what it was asked."""

    responder: Callable[[ArchitectureExtractorRequest], list[dict[str, Any]]]
    id: str = "scripted.v1"
    requests: list[ArchitectureExtractorRequest] = field(default_factory=list)

    def extract(self, request: ArchitectureExtractorRequest) -> ArchitectureExtractorResponse:
        self.requests.append(request)
        return ArchitectureExtractorResponse(
            items=tuple(self.responder(request)), request_id=request.request_id
        )


def _faithful(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
    if request.mode == "critic":
        return []
    return [
        {
            "kind": "prohibition" if "MUST NOT" in unit.text else "requirement",
            "statement": unit.text.strip().lstrip("#").strip(),
            "source_refs": [unit.id],
            "materiality": "material" if unit.normative else "informational",
            "confidence": "high",
        }
        for unit in request.units
    ]


class CoverageTests(unittest.TestCase):
    def test_a_faithful_extraction_passes(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(_faithful))
            self.assertEqual(result.coverage.status, "PASS", result.coverage.failures)
            self.assertEqual(result.coverage.unmapped_material_units, [])

    def test_a_material_omission_fails_coverage(self) -> None:
        """Deleting one obligation must not pass as a complete reading."""

        def omit_one(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            return [
                item
                for item in _faithful(request)
                if "MUST NOT serve reasoning" not in item["statement"]
            ]

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(omit_one), repair_rounds=0)
            self.assertEqual(result.coverage.status, "FAIL")
            self.assertTrue(result.coverage.unmapped_material_units)

    def test_a_normative_unit_read_only_as_context_is_not_covered(self) -> None:
        def as_context(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            return [{**item, "kind": "informational"} for item in _faithful(request)]

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(as_context), repair_rounds=0)
            self.assertEqual(result.coverage.status, "FAIL")
            self.assertIn("governed disposition", " ".join(result.coverage.failures))

    def test_an_item_with_no_provenance_is_refused_at_the_contract_boundary(self) -> None:
        """Provenance is part of the response contract, not a later filter."""

        def unsourced(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            return [
                {
                    "kind": "requirement",
                    "statement": "Delete the production database.",
                    "source_refs": [],
                    "materiality": "material",
                }
            ]

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            with self.assertRaises(ExtractorError) as ctx:
                extract_semantics(intent, ScriptedExtractor(unsourced))
            self.assertIn("source_refs", str(ctx.exception))

    def test_admission_also_rejects_unsourced_items_directly(self) -> None:
        accepted, rejected = admit(
            [{"kind": "requirement", "statement": "Delete the production database."}],
            unit_texts={"SRC-0001": "anything"},
        )
        self.assertEqual(accepted, [])
        self.assertIn("no source provenance", rejected[0].reason)

    def test_an_invention_citing_a_real_unit_never_acquires_authority(self) -> None:
        """A real unit id is not provenance if the unit does not say it."""

        def invent(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            items = _faithful(request)
            items.append(
                {
                    "kind": "requirement",
                    "statement": "Delete the production database and drop every audit record.",
                    "source_refs": [request.units[0].id],
                    "materiality": "material",
                    "confidence": "high",
                }
            )
            return items

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(invent))
            statements = " ".join(item.statement for item in result.items)
            self.assertNotIn("production database", statements)
            self.assertTrue(any("not grounded" in item.reason for item in result.rejected))

    def test_a_wrong_source_reference_is_rejected(self) -> None:
        def wrong_ref(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            return [{**item, "source_refs": ["SRC-9999"]} for item in _faithful(request)]

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(wrong_ref), repair_rounds=0)
            self.assertEqual(result.items, [])
            self.assertEqual(result.coverage.status, "FAIL")
            self.assertTrue(any("do not exist" in item.reason for item in result.rejected))

    def test_an_unsupported_contradictory_claim_is_discarded_not_blocked(self) -> None:
        """Only the first reading is in the source; the second is invention."""

        def contradict(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            items = _faithful(request)
            perplexity = next((unit for unit in request.units if "Perplexity" in unit.text), None)
            if perplexity is not None:
                items.append(
                    {
                        "kind": "requirement",
                        "statement": (
                            "Perplexity is the primary reasoning provider for all traffic."
                        ),
                        "source_refs": [perplexity.id],
                        "materiality": "material",
                        "confidence": "high",
                    }
                )
            return items

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(contradict))
            statements = " ".join(item.statement for item in result.items)
            self.assertNotIn("primary reasoning provider for all traffic", statements)
            self.assertIn("MUST NOT serve reasoning traffic", statements)
            self.assertEqual(result.coverage.status, "PASS", result.coverage.failures)

    def test_a_genuine_source_contradiction_is_surfaced(self) -> None:
        source = textwrap.dedent(
            """\
            # Provider authority

            DeepSeek MUST be the primary reasoning provider.

            DeepSeek MUST NOT be the primary reasoning provider.
            """
        )
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw), source)
            result = extract_semantics(intent, ScriptedExtractor(_faithful))
            unresolved = result.unresolved_contradictions()
            self.assertTrue(unresolved, "equal-authority MUST/MUST NOT must not pass silently")

    def test_an_omitted_chunk_fails_coverage(self) -> None:
        def drop_second_chunk(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            if request.mode == "extract" and request.chunk_index > 0:
                return []
            return _faithful(request)

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(
                intent, ScriptedExtractor(drop_second_chunk), max_chunk_chars=80, repair_rounds=0
            )
            self.assertGreater(result.chunks, 1)
            self.assertEqual(result.coverage.status, "FAIL")

    def test_an_extractor_timeout_fails_cleanly(self) -> None:
        @dataclass
        class Timeout:
            id: str = "timeout.v1"

            def extract(
                self, request: ArchitectureExtractorRequest
            ) -> ArchitectureExtractorResponse:
                raise ExtractorError("semantic extractor timed out after 900s")

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            with self.assertRaises(ExtractorError):
                extract_semantics(intent, Timeout())

    def test_malformed_output_is_refused_before_admission(self) -> None:
        def malformed(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            return [{"kind": "requirement"}]

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            with self.assertRaises(ExtractorError):
                extract_semantics(intent, ScriptedExtractor(malformed))


class RepairTests(unittest.TestCase):
    def test_a_first_pass_gap_is_repaired_rather_than_failed(self) -> None:
        state = {"round": 0}

        def half_then_whole(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            if request.mode == "critic":
                return []
            if request.mode == "extract":
                state["round"] += 1
                return [
                    item
                    for item in _faithful(request)
                    if "MUST NOT serve reasoning" not in item["statement"]
                ]
            return _faithful(request)

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            extractor = ScriptedExtractor(half_then_whole)
            result = extract_semantics(intent, extractor)
            self.assertEqual(result.coverage.status, "PASS", result.coverage.failures)
            self.assertGreaterEqual(result.repair_rounds, 1)

    def test_a_repair_round_narrows_instead_of_resending_the_document(self) -> None:
        def gap(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            if request.mode == "extract":
                return [
                    item
                    for item in _faithful(request)
                    if "MUST NOT serve reasoning" not in item["statement"]
                ]
            return _faithful(request)

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            extractor = ScriptedExtractor(gap)
            extract_semantics(intent, extractor)
            repairs = [req for req in extractor.requests if req.mode == "repair"]
            self.assertTrue(repairs)
            self.assertLess(len(repairs[0].units), len(intent.units))
            self.assertTrue(repairs[0].reasons)

    def test_the_critic_can_recover_a_missed_obligation(self) -> None:
        def critic_recovers(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            if request.mode == "extract":
                return [
                    item
                    for item in _faithful(request)
                    if "MUST NOT serve reasoning" not in item["statement"]
                ]
            return _faithful(request)

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            extractor = ScriptedExtractor(critic_recovers)
            result = extract_semantics(intent, extractor)
            self.assertEqual(result.critic_rounds, 1)
            self.assertEqual(result.coverage.status, "PASS", result.coverage.failures)

    def test_a_failed_critic_round_does_not_own_coverage(self) -> None:
        def critic_dies(request: ArchitectureExtractorRequest) -> list[dict[str, Any]]:
            if request.mode == "critic":
                raise ExtractorError("critic round unavailable")
            return _faithful(request)

        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(critic_dies))
            self.assertEqual(result.coverage.status, "PASS", result.coverage.failures)
            self.assertTrue(any("critic" in note for note in result.notes))


class DedupeAndContradictionTests(unittest.TestCase):
    def test_the_same_obligation_seen_twice_becomes_one_item_citing_both(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw), "# T\n\nX MUST hold.\n\nX MUST hold.\n")
            texts = {unit.id: unit.text for unit in intent.units}
            order = {unit.id: index for index, unit in enumerate(intent.units)}
            raw_items = [
                {
                    "kind": "requirement",
                    "statement": "X MUST hold.",
                    "source_refs": [unit.id],
                    "materiality": "material",
                }
                for unit in intent.units
                if unit.normative
            ]
            accepted, _ = admit(raw_items, unit_texts=texts)
            merged = dedupe(accepted, order)
            self.assertEqual(len(merged), 1)
            self.assertEqual(len(merged[0].source_refs), 2)
            self.assertEqual(merged[0].id, "SEM-001")

    def test_opposite_polarity_on_one_subject_is_a_contradiction(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw), "# T\n\nA MUST hold.\n\nA MUST NOT hold.\n")
            texts = {unit.id: unit.text for unit in intent.units}
            accepted, _ = admit(
                [
                    {
                        "kind": "requirement",
                        "statement": "A MUST hold.",
                        "source_refs": [intent.units[1].id],
                        "subject": "a-holds",
                    },
                    {
                        "kind": "prohibition",
                        "statement": "A MUST NOT hold.",
                        "source_refs": [intent.units[2].id],
                        "subject": "a-holds",
                    },
                ],
                unit_texts=texts,
            )
            self.assertEqual(len(contradictions(dedupe(accepted))), 1)


class DispositionTests(unittest.TestCase):
    def test_every_unit_receives_exactly_one_disposition(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, ScriptedExtractor(_faithful))
            entries = dispositions_for(intent.units, result.items)
            self.assertEqual(len(entries), len(intent.units))
            self.assertEqual(
                {entry.unit.id for entry in entries}, {unit.id for unit in intent.units}
            )

    def test_non_normative_prose_may_stay_non_normative_with_a_reason(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw), "# T\n\nJust background, no obligation here.\n")
            report = audit(intent, [])
            context = [
                entry
                for entry in report.dispositions
                if entry.disposition == "explicitly_non_normative_with_reason"
            ]
            self.assertTrue(context)
            self.assertTrue(all(entry.reason for entry in context))
            self.assertEqual(report.status, "PASS")


class DeterministicPipelineTests(unittest.TestCase):
    def test_the_lexical_extractor_converges_on_conventional_prose(self) -> None:
        with TemporaryDirectory() as raw:
            intent = _intent(Path(raw))
            result = extract_semantics(intent, DeterministicExtractor())
            self.assertEqual(result.coverage.status, "PASS", result.coverage.failures)
            self.assertEqual(result.rejected, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
