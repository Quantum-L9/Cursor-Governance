from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "stack_pr.py"


class StackPrTests(unittest.TestCase):
    def test_base_from_stack_never_main(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            stack = Path(raw) / "STACK.json"
            stack.write_text(
                json.dumps(
                    {
                        "schema": "l9.program-execution.pr-stack.v1",
                        "stack": [
                            {
                                "task_id": "TASK-001",
                                "branch": "pec/w0/task-001",
                                "pr_base": "campaign/demo-activate-v1",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "base", "--stack", str(stack)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "campaign/demo-activate-v1")
            self.assertNotIn("main", result.stdout)

    def test_missing_stack_refuses_default_branch(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "base"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("STACK.json required", result.stderr)


if __name__ == "__main__":
    unittest.main()
