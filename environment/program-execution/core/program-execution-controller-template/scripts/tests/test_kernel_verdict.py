from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from helpers import (
    cleanup_worktree,
    make_blueprint,
    make_repo,
    prepare_attempt,
    register_contract,
    run_cli,
    source_contract,
    write_json,
)


def _inspection_blueprint(root: Path) -> Path:
    bp = make_blueprint(root)
    cards = yaml.safe_load((bp / "TASK_CARDS.yaml").read_text(encoding="utf-8"))
    for task in cards.get("tasks") or []:
        for item in task.get("validation") or []:
            item["method"] = "inspection"
    (bp / "TASK_CARDS.yaml").write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")
    return bp


class KernelVerdictTest(unittest.TestCase):
    def test_missing_command_is_incomplete(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = _inspection_blueprint(temp / "blueprint")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            drafted = run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(temp / "TASK-001.source.json"),
            )
            self.assertEqual(
                json.loads(Path(drafted["path"]).read_text(encoding="utf-8"))["validation_commands"],
                [],
            )
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(temp / "TASK-001.source.json"),
                "--actor",
                "operator",
            )
            prepare_attempt(temp, workspace)
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["kernel_verdict"], "INCOMPLETE")
            self.assertEqual(verification["verdict"], "FAILED")
            self.assertEqual(verification["gates"]["validation"], "INCOMPLETE")
            cleanup_worktree(repo, workspace)

    def test_command_pass_is_kernel_pass(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = make_blueprint(temp / "blueprint")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            rendered = json.loads(
                (workspace / "contracts" / "rendered" / "TASK-001.json").read_text(encoding="utf-8")
            )
            self.assertIn(rendered.get("kernel_profile", "BUILD"), {"BUILD", "CHANGE", "AUDIT"})
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["kernel_verdict"], "PASS", verification.get("gates"))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL")
            self.assertEqual(verification["dod_gates"]["validation_honest"], "PASS")
            cleanup_worktree(repo, workspace)

    def test_complete_requires_dod(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            bp = _inspection_blueprint(temp / "blueprint")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(bp))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            run_cli(
                "draft-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--output",
                str(temp / "TASK-001.source.json"),
            )
            run_cli(
                "register-contract",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--file",
                str(temp / "TASK-001.source.json"),
                "--actor",
                "operator",
            )
            prepare_attempt(temp, workspace)
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "FAILED")
            with self.assertRaises(Exception):
                run_cli(
                    "complete",
                    "TASK-001",
                    "--workspace",
                    str(workspace),
                    "--actor",
                    "operator",
                    "--evidence-id",
                    verification["evidence_id"],
                )
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
