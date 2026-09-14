from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PE_ROOT.parents[1]
CAMPAIGNS_ROOT = PE_ROOT / "campaigns"
ARCHIVE_ROOT = PE_ROOT / "archive/campaign-input-v1"
CANONICAL_SCHEMA = "l9.program-execution.campaign-source.v2"
LEGACY_SCHEMAS = {
    "l9.quantum/campaign-source/v1",
    "l9.quantum/campaign-pack/v1",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CampaignSourceV2OnlyTests(unittest.TestCase):
    def test_all_live_campaign_sources_declare_the_canonical_v2_schema(self) -> None:
        sources = sorted(CAMPAIGNS_ROOT.rglob("CAMPAIGN_SOURCE.yaml"))
        self.assertGreaterEqual(len(sources), 1)
        for path in sources:
            with self.subTest(path=path.relative_to(PE_ROOT).as_posix()):
                source = yaml.safe_load(path.read_text(encoding="utf-8"))
                self.assertEqual(source.get("schema"), CANONICAL_SCHEMA)
                self.assertEqual(source.get("schema_version"), "2.0.0")
                self.assertNotIn(source.get("schema"), LEGACY_SCHEMAS)

    def test_retired_v1_inputs_exist_only_in_the_immutable_archive(self) -> None:
        self.assertFalse(
            (REPO_ROOT / "environment/program-execution-campaigns").exists(),
            "the former live-adjacent v1 pack root must not be restored",
        )
        expected = {
            "CG-PES-RUN2-HARDENING": {
                "CAMPAIGN_AUTHORIZATION.yaml",
                "CAMPAIGN_CHARTER.yaml",
                "CAMPAIGN_EXECUTION.yaml",
            },
            "session-runtime-hydration-convergence-v1": {
                "CAMPAIGN_SOURCE.yaml",
                "source-integrity-receipt.json",
            },
        }
        for archive_id, expected_files in expected.items():
            with self.subTest(archive_id=archive_id):
                root = ARCHIVE_ROOT / archive_id
                record_path = root / "ARCHIVE_RECORD.yaml"
                self.assertTrue(record_path.is_file())
                record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
                self.assertEqual(record["schema"], "l9.program-execution.campaign-input-archive.v2")
                self.assertFalse(record["live_ingress"])
                self.assertFalse(record["may_be_compiled"])
                self.assertFalse(record["may_be_executed"])
                indexed = {item["path"]: item for item in record["files"]}
                self.assertEqual(set(indexed), expected_files)
                for name in expected_files:
                    path = root / name
                    self.assertTrue(path.is_file())
                    self.assertEqual(indexed[name]["sha256"], _sha256(path))
                    self.assertEqual(indexed[name]["bytes"], path.stat().st_size)

    def test_active_campaign_directory_has_no_compile_allowlist(self) -> None:
        self.assertFalse((CAMPAIGNS_ROOT / "COMPILE_ALLOWLIST.yaml").exists())


if __name__ == "__main__":
    unittest.main()
