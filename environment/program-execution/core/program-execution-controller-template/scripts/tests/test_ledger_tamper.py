from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, run_cli


class LedgerTamperTest(unittest.TestCase):
    def test_ledger_tamper_detected(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, _, workspace = bootstrap_repo(temp)
            ledger = workspace / "ledger/events.jsonl"
            ledger.write_text(ledger.read_text() + '{"tampered":true}\n')
            result = run_cli("validate", "--workspace", str(workspace), expect=1)
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
