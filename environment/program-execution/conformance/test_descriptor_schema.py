from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


class DescriptorSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        schema_path = self.root / "conformance/schemas/execution-adapter-spec.schema.json"
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)

    def test_positive_fixture_passes(self) -> None:
        path = self.root / "conformance/fixtures/positive/valid-adapter.yaml"
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(list(self.validator.iter_errors(value)), [])

    def test_authority_widening_fixture_fails(self) -> None:
        path = self.root / "conformance/fixtures/negative/authority-widening.yaml"
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
        messages = [error.message for error in self.validator.iter_errors(value)]
        self.assertTrue(messages)
        self.assertIn("False was expected", " ".join(messages))


if __name__ == "__main__":
    unittest.main()
