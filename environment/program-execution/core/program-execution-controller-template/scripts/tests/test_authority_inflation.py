from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, run_cli, source_contract, write_json


class AuthorityInflationTest(unittest.TestCase):
    def test_source_contract_cannot_widen_blueprint_authority(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            path = write_json(
                temp / "inflated.json", source_contract(actions=["inspect", "local_write", "push"])
            )
            result = run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(path),
                "--actor",
                "operator",
                expect=2,
            )
            self.assertIn("widens Blueprint authorization ceiling", result["error"])


if __name__ == "__main__":
    unittest.main()
