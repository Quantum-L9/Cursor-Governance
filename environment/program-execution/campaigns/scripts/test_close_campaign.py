from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from close_campaign import close_campaign, next_campaign


class CloseCampaignTest(unittest.TestCase):
    def _root(self, temp: Path) -> Path:
        root = temp / "campaigns"
        root.mkdir()
        (root / "CAMPAIGN_EXECUTION_POLICY.yaml").write_text(
            "campaigns:\n"
            "  - id: alpha\n    execute_order: 1\n"
            "  - id: beta\n    execute_order: 2\n",
            encoding="utf-8",
        )
        return root

    def test_close_then_next_skips_complete(self) -> None:
        with TemporaryDirectory() as raw:
            root = self._root(Path(raw))
            self.assertEqual(next_campaign(root)["id"], "alpha")
            closed = close_campaign(
                root,
                "alpha",
                "CONVERGED",
                {"pull_request": "https://example.test/1"},
                "AUTH-001",
            )
            self.assertEqual(closed["lifecycle"], "complete")
            self.assertTrue((root / "alpha" / "handoff" / "CLOSEOUT.yaml").is_file())
            self.assertEqual(next_campaign(root)["id"], "beta")


if __name__ == "__main__":
    unittest.main()
