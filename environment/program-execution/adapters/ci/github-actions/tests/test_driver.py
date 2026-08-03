from __future__ import annotations

import unittest
from pathlib import Path


class GitHubActionsSourceTests(unittest.TestCase):
    def test_does_not_install_workflows(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in Path(__file__).resolve().parents[1].glob("*.py")
        )
        self.assertNotIn(".github/workflows", text)
        self.assertIn("workflow", text)


if __name__ == "__main__":
    unittest.main()
