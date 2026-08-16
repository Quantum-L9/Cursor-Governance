from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, register_contract, run_cli

REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "ops" / "scripts"))
from write_runtime_readiness_receipt import main as write_receipt  # noqa: E402


def _ready_receipt(temp: Path, repo: Path) -> None:
    os.environ["L9_RUNTIME_ROOT"] = str(temp / "l9")
    sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    rc = write_receipt(
        [
            "--surface",
            "cursor",
            "--workspace",
            str(repo),
            "--governance-revision",
            sha,
            "--runtime-script-revision",
            sha,
            "--session-id",
            "preflight-session",
        ]
    )
    assert rc == 0


class PreflightTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("CURSOR_PROJECT_DIR", None)
        os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def test_missing_receipt_does_not_mutate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            os.environ["L9_RUNTIME_ROOT"] = str(temp / "l9")
            _, repo, workspace = bootstrap_repo(temp)
            result = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--task-id",
                "TASK-001",
                "--receipt-workspace",
                str(repo),
            )
            self.assertFalse(result["ready"])
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("runtime_receipt_missing", tokens)
            self.assertEqual(result["next_action"]["command"], "python3")
            self.assertIn("write_runtime_readiness_receipt.py", result["next_action"]["args"][0])

    def test_not_ready_receipt_refuses_mutation(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            os.environ["L9_RUNTIME_ROOT"] = str(temp / "l9")
            _, repo, workspace = bootstrap_repo(temp)
            write_receipt(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(repo),
                    "--governance-revision",
                    "aaa111",
                    "--runtime-script-revision",
                    "bbb222",
                ]
            )
            result = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--receipt-workspace",
                str(repo),
            )
            self.assertFalse(result["ready"])
            self.assertIn(
                "runtime_receipt_not_ready", [row["token"] for row in result["blockers"]]
            )
            self.assertEqual(result["blockers"][0]["error_code"], "REVISION_MISMATCH")

    def test_source_contract_incomplete_names_draft(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _ready_receipt(temp, repo)
            result = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--task-id",
                "TASK-001",
                "--receipt-workspace",
                str(repo),
            )
            self.assertFalse(result["ready"])
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("source_contract_incomplete", tokens)
            self.assertEqual(result["next_action"]["command"], "pec")
            self.assertEqual(result["next_action"]["args"][0], "draft-contract")

    def test_after_register_names_claim(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _ready_receipt(temp, repo)
            register_contract(temp, workspace)
            result = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--task-id",
                "TASK-001",
                "--receipt-workspace",
                str(repo),
            )
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("lease_missing", tokens)
            self.assertEqual(result["next_action"]["args"][0], "claim")

    def test_lock_identity_mismatch(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _ready_receipt(temp, repo)
            os.environ["CLAUDE_PROJECT_DIR"] = str(temp / "a")
            os.environ["CURSOR_PROJECT_DIR"] = str(temp / "b")
            result = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--receipt-workspace",
                str(repo),
            )
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("lock_identity_mismatch", tokens)
            self.assertEqual(result["blockers"][0]["error_code"], "LOCK_IDENTITY_MISMATCH")

    def test_dirty_repo_named(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _ready_receipt(temp, repo)
            (repo / "dirty.txt").write_text("x\n", encoding="utf-8")
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            result = run_cli(
                "preflight",
                "--workspace",
                str(workspace),
                "--receipt-workspace",
                str(repo),
            )
            tokens = [row["token"] for row in result["blockers"]]
            self.assertIn("repository_dirty", tokens)


if __name__ == "__main__":
    unittest.main()
