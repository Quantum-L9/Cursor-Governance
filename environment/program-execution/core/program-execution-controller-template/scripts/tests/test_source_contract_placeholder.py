from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import (
    bootstrap_repo,
    register_contract,
    run_cli,
    source_contract,
    write_json,
)


class SourceContractPlaceholderTest(unittest.TestCase):
    def test_register_rejects_replace_with_rollback(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            payload = source_contract()
            payload["rollback"] = "REPLACE_WITH_EXACT_ROLLBACK_OR_RECOVERY"
            path = write_json(temp / "bad.source.json", payload)
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
            self.assertIn("REPLACE_WITH", result["error"])

    def test_register_accepts_concrete_rollback(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)


if __name__ == "__main__":
    unittest.main()
