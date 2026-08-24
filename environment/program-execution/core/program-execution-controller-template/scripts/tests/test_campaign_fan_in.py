"""Campaign integration lineage and verified fan-in (PHASE-6 parts B and C).

Local execution lineage comes from the campaign integration branch
(`campaign/<campaign_id>`), never from STACK.json publication topology, and a
repo_local task is not COMPLETED until its verified candidate commits are
integrated back into that branch.
"""

from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import bootstrap_repo, prepare_attempt, register_contract, run_cli, write_json

CAMPAIGN_BRANCH = "campaign/test-program"


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def _make_campaign_branch(repo: Path) -> str:
    _git(repo, "branch", CAMPAIGN_BRANCH, "HEAD")
    return _git(repo, "rev-parse", CAMPAIGN_BRANCH)


def _commit_worktree(worktree: Path, message: str) -> str:
    subprocess.run(
        ["git", "-C", str(worktree), "add", "-A"], check=True, capture_output=True, timeout=30
    )
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "-m", message],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return _git(worktree, "rev-parse", "HEAD")


def _complete(
    temp: Path, workspace: Path, *, task_id: str = "TASK-001", output: str = "docs/result.txt"
) -> dict:
    contract, prepared = prepare_attempt(temp, workspace, task_id=task_id, output=output)
    _commit_worktree(Path(prepared["worktree"]), f"{task_id} verified work")
    verification = run_cli("verify", task_id, "--workspace", str(workspace))
    assert verification["verdict"] == "PASSED_LOCAL", verification
    evidence_id = verification["evidence_id"]
    run_cli(
        "evaluate-gate",
        "GATE-001",
        "PASS",
        "--workspace",
        str(workspace),
        "--evidence-id",
        evidence_id,
        "--method",
        "independent verification",
        "--actor",
        "controller",
    )
    return run_cli(
        "complete",
        task_id,
        "--workspace",
        str(workspace),
        "--actor",
        "operator",
        "--evidence-id",
        evidence_id,
    )


class CampaignLineageTests(unittest.TestCase):
    def test_stack_pr_base_has_zero_effect_on_local_lease_base(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            tip = _make_campaign_branch(repo)
            register_contract(temp, workspace)
            # A poisoned publication topology must not decide (or block) the
            # local execution base: the old implementation raised on an
            # unresolvable pr_base ref; the new one never reads it.
            write_json(
                workspace / "runtime" / "STACK.json",
                {
                    "schema": "l9.program-execution.pr-stack.v1",
                    "campaign_id": "test-program",
                    "stack": [
                        {
                            "task_id": "TASK-001",
                            "branch": "pec/w0/task-001",
                            "pr_base": "refs/heads/does-not-exist-anywhere",
                        }
                    ],
                },
            )
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            self.assertEqual(lease["base_sha"], tip)

    def test_lease_base_is_campaign_branch_head(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            tip = _make_campaign_branch(repo)
            register_contract(temp, workspace)
            lease = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            self.assertEqual(lease["base_sha"], tip)


class CampaignFanInTests(unittest.TestCase):
    def test_complete_integrates_candidate_into_campaign_branch(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            before = _make_campaign_branch(repo)
            register_contract(temp, workspace)
            result = _complete(temp, workspace)
            integration = result["integration"]
            self.assertEqual(integration["integration_branch"], CAMPAIGN_BRANCH)
            after = _git(repo, "rev-parse", CAMPAIGN_BRANCH)
            self.assertNotEqual(before, after)
            self.assertEqual(integration["campaign_sha"], after)
            self.assertEqual(len(integration["integrated_commits"]), 1)
            receipt_path = workspace / "receipts" / "integration" / "TASK-001.json"
            self.assertTrue(receipt_path.is_file())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["candidate_sha"], integration["candidate_sha"])
            self.assertEqual(receipt["campaign_sha"], after)
            # The integrated content is on the campaign branch.
            shown = _git(repo, "show", f"{CAMPAIGN_BRANCH}:docs/result.txt")
            self.assertIn("ok", shown)

    def test_dependent_task_bases_on_post_fan_in_campaign_head(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp, two_tasks=True)
            _make_campaign_branch(repo)
            register_contract(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
            first = _complete(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            integrated_head = first["integration"]["campaign_sha"]
            lease = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker"
            )
            self.assertEqual(lease["base_sha"], integrated_head)

    def test_integration_conflict_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _make_campaign_branch(repo)
            register_contract(temp, workspace)
            contract, prepared = prepare_attempt(temp, workspace)
            _commit_worktree(Path(prepared["worktree"]), "TASK-001 verified work")
            # Move the campaign branch after claim with conflicting content at
            # the same path, without touching the primary checkout.
            _git(repo, "worktree", "add", str(temp / "conflict-wt"), CAMPAIGN_BRANCH)
            conflict_file = temp / "conflict-wt" / "docs" / "result.txt"
            conflict_file.parent.mkdir(parents=True, exist_ok=True)
            conflict_file.write_text("conflicting content\n", encoding="utf-8")
            _commit_worktree(temp / "conflict-wt", "conflicting campaign change")
            _git(repo, "worktree", "remove", "--force", str(temp / "conflict-wt"))
            moved_tip = _git(repo, "rev-parse", CAMPAIGN_BRANCH)

            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "PASSED_LOCAL")
            evidence_id = verification["evidence_id"]
            run_cli(
                "evaluate-gate",
                "GATE-001",
                "PASS",
                "--workspace",
                str(workspace),
                "--evidence-id",
                evidence_id,
                "--method",
                "independent verification",
                "--actor",
                "controller",
            )
            result = run_cli(
                "complete",
                "TASK-001",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--evidence-id",
                evidence_id,
                expect=2,
            )
            self.assertIn("integration conflict", result["error"])
            status = run_cli("status", "--workspace", str(workspace))
            task = next(t for t in status["tasks"] if t["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "PASSED_LOCAL")
            # The aborted cherry-pick left the campaign branch untouched and
            # the candidate branch/worktree preserved.
            self.assertEqual(_git(repo, "rev-parse", CAMPAIGN_BRANCH), moved_tip)
            self.assertTrue(Path(prepared["worktree"]).is_dir())
            self.assertFalse((workspace / "receipts" / "integration" / "TASK-001.json").is_file())

    def test_already_integrated_candidate_replays_safely(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            _make_campaign_branch(repo)
            register_contract(temp, workspace)
            result = _complete(temp, workspace)
            integration = result["integration"]
            after_first = _git(repo, "rev-parse", CAMPAIGN_BRANCH)
            # Replaying integration for the same candidate must not duplicate
            # commits: the receipt short-circuits the cherry-pick.
            import sys

            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from pec.controller import _integrate_candidate, open_runtime

            db, ledger = open_runtime(workspace)
            try:
                task = db.task("TASK-001")
                replay = _integrate_candidate(db, ledger, workspace, task)
            finally:
                db.close()
            self.assertEqual(replay["candidate_sha"], integration["candidate_sha"])
            self.assertEqual(_git(repo, "rev-parse", CAMPAIGN_BRANCH), after_first)

    def test_run_git_ignores_host_git_dir(self) -> None:
        """``git -C`` must win when the host exported GIT_DIR (GHA/CI)."""
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from pec.common import run_git

        with TemporaryDirectory() as raw:
            decoy = Path(raw) / "decoy"
            target = Path(raw) / "target"
            identity = (
                "-c",
                "user.email=test@example.com",
                "-c",
                "user.name=Test",
            )
            for path in (decoy, target):
                path.mkdir()
                subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
                (path / "README.md").write_text(f"{path.name}\n", encoding="utf-8")
                subprocess.run(
                    ["git", "add", "README.md"], cwd=path, check=True, capture_output=True
                )
                subprocess.run(
                    ["git", *identity, "commit", "-m", "init"],
                    cwd=path,
                    check=True,
                    capture_output=True,
                )
            previous = os.environ.get("GIT_DIR")
            os.environ["GIT_DIR"] = str((decoy / ".git").resolve())
            try:
                shown = run_git(target, "rev-parse", "--show-toplevel").stdout.strip()
            finally:
                if previous is None:
                    os.environ.pop("GIT_DIR", None)
                else:
                    os.environ["GIT_DIR"] = previous
            self.assertEqual(Path(shown).resolve(), target.resolve())


if __name__ == "__main__":
    unittest.main()
