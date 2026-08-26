from __future__ import annotations

import copy
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

PE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = PE_ROOT / "core/shared/schemas/campaign-source.schema.json"
CAMPAIGNS = PE_ROOT / "campaigns"
INTENT_PROVENANCE_SCHEMA = "l9.program-execution.intent-provenance.v1"

MINIMAL_PROVENANCE = {
    "schema": INTENT_PROVENANCE_SCHEMA,
    "campaign_id": "demo-v1",
    "target": "Quantum-L9/LLM-Router",
    "source": {"sha256": "a" * 64, "media_type": "text/markdown", "path": "arch.md"},
    "source_units": [
        {
            "id": "SRC-0001",
            "kind": "paragraph",
            "line_start": 1,
            "line_end": 2,
            "sha256": "b" * 64,
            "signals": ["MUST"],
            "disposition": "mapped_requirement",
        }
    ],
    "semantic_items": [
        {
            "id": "SEM-001",
            "kind": "requirement",
            "statement": "X MUST hold.",
            "source_refs": ["SRC-0001"],
            "materiality": "material",
            "campaign_mappings": [{"kind": "task", "task_id": "TASK-001"}],
        }
    ],
    "coverage": {
        "total_units": 1,
        "material_units": 1,
        "mapped_material_units": 1,
        "unmapped_material_units": 0,
        "status": "PASS",
    },
}


def _campaign_files() -> list[Path]:
    return sorted(CAMPAIGNS.glob("*/CAMPAIGN_SOURCE.yaml"))


class CampaignSourceSchemaTests(unittest.TestCase):
    def test_schema_exists(self) -> None:
        self.assertTrue(SCHEMA.is_file())

    def test_all_registered_campaign_sources_validate(self) -> None:
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        files = _campaign_files()
        self.assertGreaterEqual(len(files), 4)
        for path in files:
            with self.subTest(path=path.relative_to(PE_ROOT).as_posix()):
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                errors = sorted(
                    validator.iter_errors(data),
                    key=lambda item: list(item.path),
                )
                messages = [
                    f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
                    for err in errors
                ]
                self.assertEqual(messages, [], msg="\n".join(messages))


class IntentProvenanceSchemaTests(unittest.TestCase):
    """`intent_provenance` is a declared contract, not loose additionalProperties.

    A lineage record that nothing validates is a lineage record anyone can
    forge; the campaign compiler re-derives it, and this test proves the shape
    it re-derives against is actually declared here.
    """

    def setUp(self) -> None:
        self.validator = Draft202012Validator(yaml.safe_load(SCHEMA.read_text(encoding="utf-8")))
        self.base = {
            "schema": "l9.program-execution.campaign-source.v2",
            "schema_version": "2.0.0",
            "metadata": {"campaign_id": "demo-v1", "title": "Demo"},
            "program": {"id": "demo-v1", "name": "Demo", "definition_status": "ready"},
        }

    def _errors(self, provenance: object) -> list[str]:
        document = {**self.base, "intent_provenance": provenance}
        return [
            f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
            for err in self.validator.iter_errors(document)
        ]

    def test_the_property_is_declared_not_merely_permitted(self) -> None:
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        declared = schema["properties"]["intent_provenance"]
        self.assertEqual(declared["properties"]["schema"]["const"], INTENT_PROVENANCE_SCHEMA)
        self.assertIn("source_units", declared["required"])
        self.assertIn("semantic_items", declared["required"])
        self.assertIn("coverage", declared["required"])

    def test_a_well_formed_record_validates(self) -> None:
        self.assertEqual(self._errors(copy.deepcopy(MINIMAL_PROVENANCE)), [])

    def test_a_semantic_item_without_provenance_is_invalid(self) -> None:
        broken = copy.deepcopy(MINIMAL_PROVENANCE)
        broken["semantic_items"][0]["source_refs"] = []
        self.assertTrue(self._errors(broken))

    def test_a_source_unit_without_a_disposition_is_invalid(self) -> None:
        broken = copy.deepcopy(MINIMAL_PROVENANCE)
        del broken["source_units"][0]["disposition"]
        self.assertTrue(self._errors(broken))

    def test_coverage_status_is_constrained(self) -> None:
        broken = copy.deepcopy(MINIMAL_PROVENANCE)
        broken["coverage"]["status"] = "PROBABLY"
        self.assertTrue(self._errors(broken))

    def test_a_campaign_source_without_provenance_is_still_valid(self) -> None:
        self.assertEqual(list(self.validator.iter_errors(self.base)), [])


if __name__ == "__main__":
    unittest.main()
