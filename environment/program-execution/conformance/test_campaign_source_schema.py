from __future__ import annotations

import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

PE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = PE_ROOT / "core/shared/schemas/campaign-source.schema.json"
CAMPAIGNS = PE_ROOT / "campaigns"


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


if __name__ == "__main__":
    unittest.main()
