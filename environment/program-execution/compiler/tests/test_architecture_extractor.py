"""Extractor boundary tests: chunking, provenance, repair, failure modes.

Every extractor here is deterministic — no network, no model call.
"""

from __future__ import annotations

import unittest
from typing import Any

from compiler.architecture_extractor import (
    ArchitectureExtractorRequest,
    ArchitectureExtractorResponse,
    DeterministicExtractor,
    ExtractionFailed,
    ExtractorError,
    SourceContradiction,
    build_extraction_requests,
    run_extraction,
)
from compiler.architecture_intent import segment_source

DOC = """# Sample

The service MUST expose a health endpoint.

Perplexity is research-only and MUST NOT serve reasoning requests.

Ordinary narrative paragraph describing history and motivation for readers.
"""


class ScriptedExtractor:
    """Plays back scripted responses per (role) and records requests."""

    identity = "scripted.v1"

    def __init__(self, script: dict[str, list[Any]]) -> None:
        self.script = {role: list(responses) for role, responses in script.items()}
        self.requests: list[ArchitectureExtractorRequest] = []
        self.fallback = DeterministicExtractor()

    def extract(self, request: ArchitectureExtractorRequest) -> ArchitectureExtractorResponse:
        self.requests.append(request)
        queued = self.script.get(request.role)
        if queued:
            action = queued.pop(0)
            if isinstance(action, Exception):
                raise action
            if callable(action):
                return action(request)
            return action
        if request.role == "critic":
            return ArchitectureExtractorResponse(items=())
        return self.fallback.extract(request)


def _items_response(items: list[dict[str, Any]]) -> ArchitectureExtractorResponse:
    return ArchitectureExtractorResponse(items=tuple(items))


class ChunkingTests(unittest.TestCase):
    def test_every_unit_appears_in_exactly_whole_unit_chunks(self) -> None:
        document = segment_source(DOC)
        requests = build_extraction_requests(document, chunk_budget_chars=120)
        self.assertGreater(len(requests), 1, "budget must force the chunking path")
        covered: list[str] = []
        for request in requests:
            for unit in request.units:
                covered.append(unit.id)
                self.assertEqual(document.unit_by_id()[unit.id].sha256, unit.sha256)
        self.assertEqual(sorted(covered), sorted(document.unit_ids()))

    def test_long_source_chunks_and_still_converges(self) -> None:
        document = segment_source(DOC)
        outcome = run_extraction(DeterministicExtractor(), document, chunk_budget_chars=120)
        self.assertGreater(outcome.chunk_count, 1)
        self.assertTrue(outcome.coverage.passed, outcome.coverage.problems)


class ProvenanceTests(unittest.TestCase):
    def test_invented_requirement_without_provenance_is_rejected(self) -> None:
        document = segment_source(DOC)
        extractor = ScriptedExtractor(
            {
                "extract": [
                    lambda request: _items_response(
                        list(DeterministicExtractor().extract(request).to_dict()["items"])
                        + [
                            {
                                "id": "EVIL-1",
                                "kind": "requirement",
                                "statement": "Delete the production database.",
                                "source_refs": [],
                                "materiality": "material",
                            }
                        ]
                    )
                ]
            }
        )
        outcome = run_extraction(extractor, document, run_critic=False)
        statements = [item.statement for item in outcome.items]
        self.assertNotIn("Delete the production database.", statements)
        reasons = {entry["reason"] for entry in outcome.rejected}
        self.assertIn("no_source_provenance", reasons)

    def test_wrong_source_reference_is_rejected_and_fails_coverage_if_uncovered(self) -> None:
        document = segment_source(DOC)
        extractor = ScriptedExtractor(
            {
                "extract": [
                    lambda request: _items_response(
                        list(DeterministicExtractor().extract(request).to_dict()["items"])
                        + [
                            {
                                "id": "BAD-REF",
                                "kind": "requirement",
                                "statement": "Rotate every credential in the vault.",
                                "source_refs": ["SRC-9999"],
                                "materiality": "material",
                            }
                        ]
                    )
                ]
            }
        )
        outcome = run_extraction(extractor, document, run_critic=False)
        self.assertNotIn(
            "Rotate every credential in the vault.",
            [item.statement for item in outcome.items],
        )
        self.assertIn("unknown_source_refs", {entry["reason"] for entry in outcome.rejected})

    def test_contradictory_unsupported_candidate_is_discarded(self) -> None:
        """The extractor asserts both research-only and primary-reasoning for
        Perplexity, but only the first is supported by the cited source: the
        unsupported candidate loses candidacy — no BLOCKED runtime campaign."""
        document = segment_source(DOC)
        research_unit = next(unit.id for unit in document.units if "research-only" in unit.text)
        extractor = ScriptedExtractor(
            {
                "extract": [
                    lambda request: _items_response(
                        list(DeterministicExtractor().extract(request).to_dict()["items"])
                        + [
                            {
                                "id": "FLIP-1",
                                "kind": "requirement",
                                "statement": (
                                    "Perplexity becomes the primary governed provider "
                                    "for dispatch traffic."
                                ),
                                "source_refs": [research_unit],
                                "materiality": "material",
                            }
                        ]
                    )
                ]
            }
        )
        outcome = run_extraction(extractor, document, run_critic=False)
        self.assertTrue(outcome.coverage.passed, outcome.coverage.problems)
        flipped = [item for item in outcome.items if "primary governed provider" in item.statement]
        self.assertEqual(flipped, [])
        self.assertIn(
            "unsupported_by_cited_source", {entry["reason"] for entry in outcome.rejected}
        )

    def test_genuine_source_contradiction_fails_compilation(self) -> None:
        contradictory = (
            "# Contradiction\n\n"
            "The exporter MUST persist raw telemetry payloads to disk.\n\n"
            "The exporter MUST NOT persist raw telemetry payloads to disk.\n"
        )
        document = segment_source(contradictory)
        unit_a, unit_b = document.units[1].id, document.units[2].id

        def flagged(request: ArchitectureExtractorRequest) -> ArchitectureExtractorResponse:
            return _items_response(
                [
                    {
                        "id": "A",
                        "kind": "requirement",
                        "statement": "The exporter MUST persist raw telemetry payloads to disk.",
                        "source_refs": [unit_a],
                        "conflicts_with": ["B"],
                    },
                    {
                        "id": "B",
                        "kind": "prohibition",
                        "statement": (
                            "The exporter MUST NOT persist raw telemetry payloads to disk."
                        ),
                        "source_refs": [unit_b],
                        "conflicts_with": ["A"],
                    },
                    {
                        "id": "C",
                        "kind": "informational",
                        "statement": "heading: contradiction sample",
                        "source_refs": [document.units[0].id],
                        "materiality": "informational",
                    },
                ]
            )

        extractor = ScriptedExtractor({"extract": [flagged, flagged, flagged, flagged]})
        with self.assertRaises(SourceContradiction):
            run_extraction(extractor, document, run_critic=False, max_repair_rounds=1)


class FailureModeTests(unittest.TestCase):
    def test_timeout_retries_once_then_fails_cleanly(self) -> None:
        document = segment_source(DOC)
        extractor = ScriptedExtractor(
            {
                "extract": [
                    ExtractorError("timed out after 300s"),
                    ExtractorError("timed out after 300s"),
                ]
            }
        )
        with self.assertRaises(ExtractionFailed) as ctx:
            run_extraction(extractor, document, run_critic=False)
        self.assertIn("timed out", str(ctx.exception))

    def test_malformed_output_retries_then_succeeds(self) -> None:
        document = segment_source(DOC)
        extractor = ScriptedExtractor({"extract": [{"schema": "wrong", "items": "not-a-list"}]})
        outcome = run_extraction(extractor, document, run_critic=False)
        self.assertTrue(outcome.coverage.passed, outcome.coverage.problems)

    def test_persistently_malformed_output_fails_cleanly(self) -> None:
        document = segment_source(DOC)
        bad = {"schema": "wrong", "items": "still-not-a-list"}
        extractor = ScriptedExtractor({"extract": [dict(bad), dict(bad)]})
        with self.assertRaises(ExtractionFailed):
            run_extraction(extractor, document, run_critic=False)

    def test_chunk_omission_fails_coverage(self) -> None:
        """An extractor that silently returns nothing for a chunk cannot PASS."""
        document = segment_source(DOC)
        empty = ArchitectureExtractorResponse(items=())
        extractor = ScriptedExtractor({"extract": [empty] * 10, "repair": [empty] * 10})
        outcome = run_extraction(extractor, document, run_critic=False, max_repair_rounds=1)
        self.assertFalse(outcome.coverage.passed)
        self.assertIn(
            "unit_unclassified",
            {problem["code"] for problem in outcome.coverage.problems},
        )


class CriticAndRepairTests(unittest.TestCase):
    def test_critic_findings_enter_reconciliation_with_provenance(self) -> None:
        document = segment_source(DOC)
        health_unit = next(unit.id for unit in document.units if "health endpoint" in unit.text)

        def weak_extract(request: ArchitectureExtractorRequest) -> ArchitectureExtractorResponse:
            # Misses the health requirement; classifies everything informational.
            return _items_response(
                [
                    {
                        "id": f"I-{unit.id}",
                        "kind": "informational",
                        "statement": f"narrative context for {unit.id}",
                        "source_refs": [unit.id],
                        "materiality": "informational",
                    }
                    for unit in request.units
                    if unit.kind != "frontmatter"
                ]
            )

        def critic(request: ArchitectureExtractorRequest) -> ArchitectureExtractorResponse:
            return _items_response(
                [
                    {
                        "id": "CRIT-1",
                        "kind": "requirement",
                        "statement": "The service MUST expose a health endpoint.",
                        "source_refs": [health_unit],
                        "materiality": "material",
                    },
                    {
                        "id": "CRIT-2",
                        "kind": "prohibition",
                        "statement": (
                            "Perplexity is research-only and MUST NOT serve reasoning requests."
                        ),
                        "source_refs": [
                            next(unit.id for unit in document.units if "research-only" in unit.text)
                        ],
                        "materiality": "material",
                    },
                ]
            )

        extractor = ScriptedExtractor({"extract": [weak_extract], "critic": [critic, critic]})
        outcome = run_extraction(extractor, document)
        self.assertTrue(outcome.critic_ran)
        kinds = {item.kind for item in outcome.items}
        self.assertIn("requirement", kinds)
        self.assertIn("prohibition", kinds)
        self.assertTrue(outcome.coverage.passed, outcome.coverage.problems)

    def test_repair_round_targets_only_uncovered_units(self) -> None:
        document = segment_source(DOC)
        skip_unit = next(unit.id for unit in document.units if "health endpoint" in unit.text)

        def partial(request: ArchitectureExtractorRequest) -> ArchitectureExtractorResponse:
            full = DeterministicExtractor().extract(request).to_dict()["items"]
            return _items_response([item for item in full if skip_unit not in item["source_refs"]])

        extractor = ScriptedExtractor({"extract": [partial]})
        outcome = run_extraction(extractor, document, run_critic=False)
        self.assertEqual(outcome.repair_rounds, 1)
        repair_requests = [request for request in extractor.requests if request.role == "repair"]
        self.assertTrue(repair_requests)
        self.assertEqual(
            {unit.id for request in repair_requests for unit in request.units},
            {skip_unit},
        )
        self.assertTrue(outcome.coverage.passed, outcome.coverage.problems)


if __name__ == "__main__":
    unittest.main()
