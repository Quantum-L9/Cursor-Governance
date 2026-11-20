"""`projection_context` survives the Controller from task card to rendered contract.

The runner hands a worker the bound projection only when the rendered contract
says `projection_context: true`. A flag the Controller dropped would silently
starve an opted-in worker, and one it invented would hand semantics to every
worker, so both directions are proven here.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, cleanup_worktree, run_cli


def _rendered(task_overrides: dict) -> tuple[dict, dict]:
    with TemporaryDirectory() as raw:
        temp = Path(raw)
        _, repo, workspace = bootstrap_repo(temp, task_overrides=task_overrides)
        draft_path = temp / "TASK-001.draft.json"
        run_cli(
            "draft-contract", "TASK-001", "--workspace", str(workspace), "--output", str(draft_path)
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        run_cli(
            "register-contract",
            "TASK-001",
            "--workspace",
            str(workspace),
            "--file",
            str(draft_path),
            "--actor",
            "operator",
        )
        try:
            run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
        finally:
            cleanup_worktree(repo, workspace)
    return draft, contract


class ProjectionContextLineageTests(unittest.TestCase):
    def test_an_opted_in_task_renders_projection_context_true(self) -> None:
        draft, contract = _rendered({"projection_context": True})
        self.assertIs(draft["projection_context"], True)
        self.assertIs(contract["projection_context"], True)

    def test_a_task_without_the_flag_renders_none(self) -> None:
        draft, contract = _rendered({})
        self.assertNotIn("projection_context", draft)
        self.assertNotIn("projection_context", contract)


if __name__ == "__main__":
    unittest.main()
