from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    establish_runtime_readiness,
    make_blueprint,
    make_repo,
    register_contract,
    run_cli,
)


class WaveDependencyTest(unittest.TestCase):
    def test_successor_wave_cannot_start_before_predecessor_completion_and_exit_gate(self):
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            establish_runtime_readiness(temp)
            bp = make_blueprint(temp / "blueprint", two_tasks=True)
            waves = yaml.safe_load((bp / "EXECUTION_WAVES.yaml").read_text())
            waves["waves"] = [
                {
                    "id": "W0",
                    "name": "first",
                    "sequence": 0,
                    "depends_on": [],
                    "workstream_ids": ["WS-01"],
                    "task_ids": ["TASK-001"],
                    "entry_gate_ids": [],
                    "exit_gate_ids": ["GATE-001"],
                    "rollback_boundary": "revert",
                    "definition_status": "active",
                },
                {
                    "id": "W1",
                    "name": "second",
                    "sequence": 1,
                    "depends_on": ["W0"],
                    "workstream_ids": ["WS-01"],
                    "task_ids": ["TASK-002"],
                    "entry_gate_ids": ["GATE-001"],
                    "exit_gate_ids": ["GATE-001"],
                    "rollback_boundary": "revert",
                    "definition_status": "active",
                },
            ]
            (bp / "EXECUTION_WAVES.yaml").write_text(yaml.safe_dump(waves, sort_keys=False))
            tasks = yaml.safe_load((bp / "TASK_CARDS.yaml").read_text())
            tasks["tasks"][1]["wave_id"] = "W1"
            (bp / "TASK_CARDS.yaml").write_text(yaml.safe_dump(tasks, sort_keys=False))
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
            result = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker", expect=2
            )
            self.assertIn("predecessor_wave_task_not_completed:W0:TASK-001", result["error"])
            self.assertIn("predecessor_wave_exit_gate_not_satisfied:W0:GATE-001", result["error"])


if __name__ == "__main__":
    unittest.main()
