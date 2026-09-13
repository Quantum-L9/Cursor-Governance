from __future__ import annotations

import unittest
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parents[1]
SKILL = PACK / "SKILL.md"
CANONICAL_REFERENCE = PACK / "references/canonical-template.md"
SOURCE_CONTRACT = PACK / "references/source-contract.md"
FILE_SET = PACK / "references/file-set.md"
CANONICAL_SOURCE = (
    REPO / "environment/program-execution/templates/campaign-source-v2/CAMPAIGN_SOURCE.yaml"
)
CANONICAL_GUIDE = REPO / "environment/program-execution/templates/campaign-source-v2/README.md"


class CampaignSkillContractTests(unittest.TestCase):
    def test_skill_routes_complete_source_to_canonical_template(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("campaign-source-v2/CAMPAIGN_SOURCE.yaml", text)
        self.assertIn('make -C "$repo_root" campaign-check-input', text)
        self.assertIn('make -C "$repo_root" campaign INTENT=path/to/CAMPAIGN_SOURCE.yaml', text)
        self.assertIn("PEC consumes the validated Blueprint", text)

    def test_references_point_to_existing_canonical_assets(self) -> None:
        self.assertTrue(CANONICAL_REFERENCE.is_file())
        self.assertTrue(CANONICAL_SOURCE.is_file())
        self.assertTrue(CANONICAL_GUIDE.is_file())
        reference = CANONICAL_REFERENCE.read_text(encoding="utf-8")
        self.assertIn("source-of-truth", reference)
        self.assertIn("Do not create a compile", reference)
        self.assertIn("archive/campaign-input-v1", reference)

    def test_contract_and_file_set_reject_retired_preregistration(self) -> None:
        source_contract = SOURCE_CONTRACT.read_text(encoding="utf-8")
        file_set = FILE_SET.read_text(encoding="utf-8")
        self.assertIn("not preregistered", source_contract)
        self.assertIn("There is no compile allowlist", file_set)
        self.assertNotIn("append `<id>`", file_set)

    def test_canonical_source_contract_is_direct_route_compatible(self) -> None:
        source = CANONICAL_SOURCE.read_text(encoding="utf-8")
        guide = CANONICAL_GUIDE.read_text(encoding="utf-8")
        self.assertIn("schema: l9.program-execution.campaign-source.v2", source)
        self.assertIn("source_is_immutable: true", source)
        self.assertIn("PEC itself bootstraps from a validated Blueprint", guide)
        self.assertIn("source-integrity-receipt.json", guide)


if __name__ == "__main__":
    unittest.main()
