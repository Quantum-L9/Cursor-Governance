from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/campaign_pr_copy.py"
CAMPAIGNS = PE_ROOT / "campaigns"
BOUNDED = CAMPAIGNS / "bounded-replanning-v1/CAMPAIGN_SOURCE.yaml"
BOUNDED_DIGEST = "9528abeaf8117dd0598036216784593a62e88948800636c2eced9dc6262ae010"


def _load():
    spec = importlib.util.spec_from_file_location("campaign_pr_copy_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CampaignPrCopyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load()

    def test_all_registered_campaigns_have_unique_specific_titles(self) -> None:
        titles: list[str] = []
        for source in sorted(CAMPAIGNS.glob("*/CAMPAIGN_SOURCE.yaml")):
            campaign_id = source.parent.name
            payload = self.mod.render(
                campaign_id=campaign_id,
                pr_base=f"origin/campaign/{campaign_id}",
                branch=f"feat/{campaign_id}-w1",
            )
            meta_title = yaml.safe_load(source.read_text(encoding="utf-8"))["metadata"]["title"]
            self.assertEqual(payload["title"], f"[{campaign_id}] {meta_title}")
            self.assertIn(meta_title, payload["body"])
            self.assertIn(f"`{campaign_id}`", payload["body"])
            self.assertIn("objective:", payload["body"])
            self.assertNotEqual(
                payload["title"],
                self.mod.branch_default_title(f"campaign/{campaign_id}"),
            )
            titles.append(payload["title"])
        self.assertEqual(len(titles), len(set(titles)))
        self.assertGreaterEqual(len(titles), 4)

    def test_branch_default_title_matches_github_campaign_shape(self) -> None:
        self.assertEqual(
            self.mod.branch_default_title("campaign/bounded-replanning-v1"),
            "Campaign/bounded replanning v1",
        )

    def test_non_campaign_refs_are_rejected(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--pr-base",
                "origin/main",
                "--branch",
                "fix/pe-crack-remediation-v1",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("not a campaign PR", completed.stderr)

    def test_activate_writes_runtime_receipt_without_touching_source(self) -> None:
        before = hashlib.sha256(BOUNDED.read_bytes()).hexdigest()
        self.assertEqual(before, BOUNDED_DIGEST)
        with tempfile.TemporaryDirectory() as raw:
            runtime = Path(raw) / "programs" / "bounded-replanning-v1"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--campaign-id",
                    "bounded-replanning-v1",
                    "--pr-base",
                    "origin/campaign/bounded-replanning-v1",
                    "--activate",
                    "--runtime-root",
                    str(runtime),
                    "--actor",
                    "test",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            receipt = Path(payload["runtime_status_path"])
            self.assertTrue(receipt.is_file())
            status = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(status["runtime_status"], "active")
            self.assertEqual(status["source_status"], "operator_intake")
            self.assertEqual(status["campaign_id"], "bounded-replanning-v1")
        after = hashlib.sha256(BOUNDED.read_bytes()).hexdigest()
        self.assertEqual(after, BOUNDED_DIGEST)


if __name__ == "__main__":
    unittest.main()
