from __future__ import annotations

import unittest
from pathlib import Path


class ChecksSourceTests(unittest.TestCase):
    def test_write_requires_approval(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "provider.py").read_text()
        self.assertIn('action == "publish_check"', text)
        approvals = (
            Path(__file__).resolve().parents[4] / "peer_execution/approvals.py"
        ).read_text()
        self.assertIn("require_exact_approval", approvals)


if __name__ == "__main__":
    unittest.main()
