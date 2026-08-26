"""Coverage-audit semantics: PASS requirements and every adversarial FAIL."""

from __future__ import annotations

import unittest

from compiler.architecture_coverage import audit_coverage, requires_campaign_mapping
from compiler.architecture_intent import segment_source
from compiler.architecture_ir import parse_semantic_item

DOC = """# Coverage sample

The gateway MUST validate every inbound token.

Perplexity is research-only and MUST NOT serve reasoning requests.

Plain narrative background paragraph without obligations.
"""


def _document():
    return segment_source(DOC)


def _items(document):
    unit_req = document.units[1].id
    unit_prob = document.units[2].id
    unit_info = document.units[3].id
    return [
        parse_semantic_item(
            {
                "id": "SEM-000",
                "kind": "informational",
                "statement": "document title heading",
                "source_refs": [document.units[0].id],
                "materiality": "informational",
            }
        ),
        parse_semantic_item(
            {
                "id": "SEM-001",
                "kind": "requirement",
                "statement": "The gateway MUST validate every inbound token.",
                "source_refs": [unit_req],
            }
        ),
        parse_semantic_item(
            {
                "id": "SEM-002",
                "kind": "prohibition",
                "statement": "Perplexity is research-only and MUST NOT serve reasoning requests.",
                "source_refs": [unit_prob],
            }
        ),
        parse_semantic_item(
            {
                "id": "SEM-003",
                "kind": "informational",
                "statement": "narrative background for readers",
                "source_refs": [unit_info],
                "materiality": "informational",
            }
        ),
    ]


def _mappings():
    return {
        "SEM-001": [{"kind": "task", "id": "TASK-001", "task_id": "TASK-001"}],
        "SEM-002": [{"kind": "prohibited_path", "id": "DNB-001"}],
    }


class CoveragePassTests(unittest.TestCase):
    def test_full_coverage_passes(self) -> None:
        document = _document()
        result = audit_coverage(
            document,
            _items(document),
            mappings=_mappings(),
            requested_unit_ids=document.unit_ids(),
        )
        self.assertTrue(result.passed, result.problems)
        self.assertEqual(result.total_units, len(document.units))
        self.assertEqual(result.classified_units, result.total_units)
        self.assertEqual(result.unmapped_material_units, 0)
        self.assertEqual(result.material_units, result.mapped_material_units)

    def test_informational_prose_needs_no_task(self) -> None:
        document = _document()
        result = audit_coverage(
            document,
            _items(document),
            mappings=_mappings(),
            requested_unit_ids=document.unit_ids(),
        )
        info_unit = document.units[3].id
        self.assertEqual(result.unit_dispositions[info_unit], "informational")


class CoverageFailTests(unittest.TestCase):
    def test_material_mapping_omission_fails(self) -> None:
        """§ adversarial: delete one material semantic mapping → not PASS."""
        document = _document()
        broken = _mappings()
        del broken["SEM-002"]
        result = audit_coverage(
            document,
            _items(document),
            mappings=broken,
            requested_unit_ids=document.unit_ids(),
        )
        self.assertFalse(result.passed)
        codes = {problem["code"] for problem in result.problems}
        self.assertIn("material_item_unmapped", codes)
        self.assertGreater(result.unmapped_material_units, 0)

    def test_omitted_chunk_fails(self) -> None:
        document = _document()
        requested = document.unit_ids() - {document.units[1].id}
        result = audit_coverage(
            document, _items(document), mappings=_mappings(), requested_unit_ids=requested
        )
        self.assertFalse(result.passed)
        self.assertIn("source_chunk_omitted", {problem["code"] for problem in result.problems})

    def test_signal_unit_cannot_disappear_silently(self) -> None:
        document = _document()
        items = [item for item in _items(document) if item.id != "SEM-002"]
        result = audit_coverage(document, items, requested_unit_ids=document.unit_ids())
        self.assertFalse(result.passed)
        self.assertIn("unit_unclassified", {problem["code"] for problem in result.problems})

    def test_signal_unit_accepts_explicit_non_normative_reason(self) -> None:
        document = _document()
        items = _items(document)
        items[2] = parse_semantic_item(
            {
                "id": "SEM-002",
                "kind": "informational",
                "statement": ("table of historical provider names; obligations restated elsewhere"),
                "source_refs": [document.units[2].id],
                "materiality": "informational",
            }
        )
        mappings = {"SEM-001": _mappings()["SEM-001"]}
        result = audit_coverage(
            document, items, mappings=mappings, requested_unit_ids=document.unit_ids()
        )
        self.assertTrue(result.passed, result.problems)
        self.assertEqual(
            result.unit_dispositions[document.units[2].id],
            "explicitly_non_normative_with_reason",
        )

    def test_unreconciled_contradiction_fails(self) -> None:
        document = _document()
        items = _items(document)
        items[1] = parse_semantic_item(
            {
                "id": "SEM-001",
                "kind": "requirement",
                "statement": "The gateway MUST validate every inbound token.",
                "source_refs": [document.units[1].id],
                "conflicts_with": ["SEM-002"],
            }
        )
        result = audit_coverage(
            document, items, mappings=_mappings(), requested_unit_ids=document.unit_ids()
        )
        self.assertFalse(result.passed)
        self.assertIn(
            "unreconciled_contradiction",
            {problem["code"] for problem in result.problems},
        )


class MappingObligationTests(unittest.TestCase):
    def test_supporting_seams_need_no_standalone_mapping(self) -> None:
        seam = parse_semantic_item(
            {
                "id": "SEM-009",
                "kind": "file_seam",
                "statement": "dispatch lives in src/router/dispatch.ts",
                "source_refs": ["SRC-0001"],
            }
        )
        self.assertFalse(requires_campaign_mapping(seam))
        requirement = parse_semantic_item(
            {
                "id": "SEM-010",
                "kind": "requirement",
                "statement": "the gateway MUST validate tokens",
                "source_refs": ["SRC-0001"],
            }
        )
        self.assertTrue(requires_campaign_mapping(requirement))


if __name__ == "__main__":
    unittest.main()
