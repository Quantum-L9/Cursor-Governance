from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

PE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = PE_ROOT / "core/shared/schemas/campaign-source.schema.json"
PROVENANCE_SCHEMA = PE_ROOT / "core/shared/schemas/intent-provenance.schema.json"
CAMPAIGNS = PE_ROOT / "campaigns"
GOLDEN_FIXTURE = PE_ROOT / "scripts/tests/fixtures/architecture-intent-llm-router.md"

if str(PE_ROOT) not in sys.path:
    sys.path.insert(0, str(PE_ROOT))


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

    def test_generated_architecture_source_conforms(self) -> None:
        """The architecture compiler emits schema-clean campaign-source.v2 whose
        intent_provenance validates against its own canonical contract."""
        from compiler.architecture_extractor import DeterministicExtractor  # noqa: PLC0415
        from scripts.compile_architecture_intent import compile_architecture  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as raw:
            result = compile_architecture(
                GOLDEN_FIXTURE,
                target="Quantum-L9/LLM-Router",
                primed_dir=Path(raw),
                extractor=DeterministicExtractor(),
            )
        source = result["campaign_source"]
        schema = yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))
        errors = [
            f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
            for err in Draft202012Validator(schema).iter_errors(source)
        ]
        self.assertEqual(errors, [], msg="\n".join(errors))
        provenance_schema = json.loads(PROVENANCE_SCHEMA.read_text(encoding="utf-8"))
        errors = [
            f"{'.'.join(str(part) for part in err.path) or '<root>'}: {err.message}"
            for err in Draft202012Validator(provenance_schema).iter_errors(
                source["intent_provenance"]
            )
        ]
        self.assertEqual(errors, [], msg="\n".join(errors))


if __name__ == "__main__":
    unittest.main()
