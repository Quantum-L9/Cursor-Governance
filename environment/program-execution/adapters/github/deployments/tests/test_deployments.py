from __future__ import annotations

import unittest
from pathlib import Path


class DeploymentSourceTests(unittest.TestCase):
    def test_target_deployment_is_not_performed(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in Path(__file__).resolve().parents[1].glob("*.py")
        )
        self.assertNotIn("kubectl", text)
        self.assertNotIn("terraform apply", text)
        self.assertIn("create_deployment_record", text)


if __name__ == "__main__":
    unittest.main()
