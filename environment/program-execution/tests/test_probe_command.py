from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ProbeCommandTests(unittest.TestCase):
    def test_probe_is_truthful_inventory_not_all_hosts_gate(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(root)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["L9_PROGRAM_HOME"] = temporary
            completed = subprocess.run(
                [sys.executable, "-B", str(root / "scripts/probe_execution_adapters.py")],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["receipts"]), 12)
            self.assertGreater(report["status_counts"].get("BLOCKED", 0), 0)


if __name__ == "__main__":
    unittest.main()
