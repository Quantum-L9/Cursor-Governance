"""v3 hardening repairs, proven at the Controller boundary.

Each case here pins a defect the v2 Controller carried in live code:

* gate PASS and task completion accepted any valid evidence, so planning
  evidence closed execution gates and completed tasks (evidence not bound to
  the claim);
* the integrated candidate was never compared with the verified state, so
  bytes written after the verdict landed on the campaign branch;
* a dependency was satisfied by PASSED_LOCAL before fan-in, so a successor
  could base on a lineage that lacked the change it depended on;
* a replan `reorder` could delete a locked dependency edge under a benign
  class label;
* retries had no bound at the Controller;
* `pec close` accepted a success verdict over a halt or a tampered ledger,
  and `export-handoff` terminalized the runtime on its own recommendation;
* transitions appended on top of a tampered ledger.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml
from helpers import (
    bootstrap_repo,
    cleanup_worktree,
    make_blueprint,
    make_repo,
    prepare_attempt,
    register_contract,
    run_cli,
    write_json,
)

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


def _commit_all(worktree: Path, message: str) -> str:
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


def _gate_pass(workspace: Path, *evidence_ids: str, expect: int = 0) -> dict[str, Any]:
    argv: list[str] = []
    for evidence_id in evidence_ids:
        argv.extend(["--evidence-id", evidence_id])
    return run_cli(
        "evaluate-gate",
        "GATE-001",
        "PASS",
        "--workspace",
        str(workspace),
        *argv,
        "--method",
        "independent verification",
        "--actor",
        "controller",
        expect=expect,
    )


def _complete(workspace: Path, task_id: str, *evidence_ids: str, expect: int = 0) -> dict[str, Any]:
    argv: list[str] = []
    for evidence_id in evidence_ids:
        argv.extend(["--evidence-id", evidence_id])
    return run_cli(
        "complete",
        task_id,
        "--workspace",
        str(workspace),
        "--actor",
        "operator",
        *argv,
        expect=expect,
    )


def _state(workspace: Path, task_id: str) -> str:
    status = run_cli("status", "--workspace", str(workspace))
    return next(item["runtime_state"] for item in status["tasks"] if item["id"] == task_id)


def _ledger_events(workspace: Path) -> list[dict[str, Any]]:
    ledger = workspace / "ledger" / "events.jsonl"
    return [
        json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _verified(temp: Path, workspace: Path, **kwargs: Any) -> tuple[dict[str, Any], Path]:
    _contract, prepared = prepare_attempt(temp, workspace, **kwargs)
    task_id = kwargs.get("task_id", "TASK-001")
    verification = run_cli("verify", task_id, "--workspace", str(workspace))
    assert verification["verdict"] == "PASSED_LOCAL", verification
    return verification, Path(prepared["worktree"])


class EvidenceBindingTests(unittest.TestCase):
    def test_execution_gate_refuses_planning_evidence(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            verification, _ = _verified(temp, workspace)
            refused = _gate_pass(workspace, "EVID-PLAN", expect=2)
            self.assertIn("Controller verification evidence", refused["error"])
            passed = _gate_pass(workspace, verification["evidence_id"])
            self.assertEqual(passed["result"], "PASS")
            cleanup_worktree(repo, workspace)

    def test_gate_pass_requires_its_declared_evidence(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = make_blueprint(temp / "blueprint")
            gates_path = blueprint / "CONVERGENCE_GATES.yaml"
            gates = yaml.safe_load(gates_path.read_text(encoding="utf-8"))
            gates["gates"][0]["required_evidence_ids"] = ["EVID-PLAN"]
            gates_path.write_text(yaml.safe_dump(gates, sort_keys=False), encoding="utf-8")
            repo = make_repo(temp / "repo")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(blueprint))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace)
            verification, _ = _verified(temp, workspace)
            refused = _gate_pass(workspace, verification["evidence_id"], expect=2)
            self.assertIn("EVID-PLAN", refused["error"])
            passed = _gate_pass(workspace, verification["evidence_id"], "EVID-PLAN")
            self.assertEqual(passed["result"], "PASS")
            cleanup_worktree(repo, workspace)

    def test_completion_requires_this_attempts_verification_evidence(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            verification, _ = _verified(temp, workspace)
            _gate_pass(workspace, verification["evidence_id"])
            refused = _complete(workspace, "TASK-001", "EVID-PLAN", expect=2)
            self.assertIn("verification evidence", refused["error"])
            self.assertEqual(_state(workspace, "TASK-001"), "PASSED_LOCAL")
            done = _complete(workspace, "TASK-001", verification["evidence_id"])
            self.assertEqual(done["status"], "COMPLETED")
            cleanup_worktree(repo, workspace)


class CandidateIdentityTests(unittest.TestCase):
    """Under a campaign branch, the integrated candidate is the verified state."""

    def _campaign(self, temp: Path) -> tuple[Path, Path]:
        _, repo, workspace = bootstrap_repo(temp)
        _git(repo, "branch", CAMPAIGN_BRANCH, "HEAD")
        register_contract(temp, workspace)
        return repo, workspace

    def test_the_exact_verified_state_integrates(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            repo, workspace = self._campaign(temp)
            verification, worktree = _verified(temp, workspace)
            self.assertEqual(sorted(verification["observed_file_digests"]), ["docs/result.txt"])
            _commit_all(worktree, "verified work")
            _gate_pass(workspace, verification["evidence_id"])
            done = _complete(workspace, "TASK-001", verification["evidence_id"])
            self.assertEqual(done["status"], "COMPLETED")
            self.assertEqual(done["integration"]["task_id"], "TASK-001")
            cleanup_worktree(repo, workspace)

    def test_bytes_the_verdict_never_saw_do_not_integrate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            repo, workspace = self._campaign(temp)
            verification, worktree = _verified(temp, workspace)
            (worktree / "docs" / "extra.txt").write_text("unverified\n", encoding="utf-8")
            _commit_all(worktree, "verified work plus an unverified file")
            _gate_pass(workspace, verification["evidence_id"])
            refused = _complete(workspace, "TASK-001", verification["evidence_id"], expect=2)
            self.assertIn("does not match the verified changes", refused["error"])
            self.assertEqual(_state(workspace, "TASK-001"), "PASSED_LOCAL")
            self.assertEqual(
                _git(repo, "rev-parse", CAMPAIGN_BRANCH), _git(repo, "rev-parse", "HEAD")
            )
            cleanup_worktree(repo, workspace)

    def test_altered_verified_bytes_do_not_integrate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            repo, workspace = self._campaign(temp)
            verification, worktree = _verified(temp, workspace)
            (worktree / "docs" / "result.txt").write_text("ok\nand then some\n", encoding="utf-8")
            _commit_all(worktree, "the verified path, rewritten after the verdict")
            _gate_pass(workspace, verification["evidence_id"])
            refused = _complete(workspace, "TASK-001", verification["evidence_id"], expect=2)
            self.assertIn("verified as", refused["error"])
            self.assertEqual(_state(workspace, "TASK-001"), "PASSED_LOCAL")
            cleanup_worktree(repo, workspace)

    def test_uncommitted_verified_changes_do_not_integrate(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            repo, workspace = self._campaign(temp)
            verification, _worktree = _verified(temp, workspace)
            _gate_pass(workspace, verification["evidence_id"])
            refused = _complete(workspace, "TASK-001", verification["evidence_id"], expect=2)
            self.assertIn("does not match the verified changes", refused["error"])
            self.assertEqual(_state(workspace, "TASK-001"), "PASSED_LOCAL")
            cleanup_worktree(repo, workspace)


class DependencyFanInTests(unittest.TestCase):
    def test_dependency_is_satisfied_only_by_fan_in_under_a_campaign_branch(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = make_blueprint(temp / "blueprint", two_tasks=True)
            graph_path = blueprint / "DEPENDENCY_GRAPH.yaml"
            graph = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
            graph["edges"] = [
                {
                    "id": "EDGE-001",
                    "from": "TASK-001",
                    "to": "TASK-002",
                    "relation": "requires",
                    "blocking": True,
                    "proof_gate_ids": [],
                }
            ]
            graph_path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
            repo = make_repo(temp / "repo")
            _git(repo, "branch", CAMPAIGN_BRANCH, "HEAD")
            workspace = temp / "runtime"
            run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(blueprint))
            run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
            register_contract(temp, workspace, task_id="TASK-001", output="docs/result.txt")
            register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
            verification, worktree = _verified(temp, workspace)
            self.assertEqual(_state(workspace, "TASK-001"), "PASSED_LOCAL")
            refused = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker", expect=2
            )
            self.assertIn("dependency_not_complete:TASK-001", refused["error"])
            _commit_all(worktree, "verified work")
            _gate_pass(workspace, verification["evidence_id"])
            done = _complete(workspace, "TASK-001", verification["evidence_id"])
            self.assertEqual(done["status"], "COMPLETED")
            lease = run_cli(
                "claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker"
            )
            # The successor bases on the post-fan-in campaign head.
            self.assertEqual(lease["base_sha"], _git(repo, "rev-parse", CAMPAIGN_BRANCH))
            cleanup_worktree(repo, workspace, "TASK-001")
            cleanup_worktree(repo, workspace, "TASK-002")


class ReplanContainmentTests(unittest.TestCase):
    def _propose(self, temp: Path, workspace: Path, delta: dict[str, Any], *, expect: int = 0):
        delta_path = write_json(temp / "delta.json", delta)
        return run_cli(
            "replan-propose",
            "rev-1",
            "--workspace",
            str(workspace),
            "--program-id",
            "test-program",
            "--trigger-evidence-id",
            "EVID-PLAN",
            "--affected-future-task-id",
            "TASK-002",
            "--delta-file",
            str(delta_path),
            "--expected-validation-effect",
            "none",
            "--proposer-actor",
            "planner",
            expect=expect,
        )

    def _locked_dependency_workspace(self, temp: Path) -> Path:
        blueprint = make_blueprint(temp / "blueprint", two_tasks=True)
        graph_path = blueprint / "DEPENDENCY_GRAPH.yaml"
        graph = yaml.safe_load(graph_path.read_text(encoding="utf-8"))
        graph["edges"] = [
            {
                "id": "EDGE-001",
                "from": "TASK-001",
                "to": "TASK-002",
                "relation": "requires",
                "blocking": True,
                "proof_gate_ids": [],
            }
        ]
        graph_path.write_text(yaml.safe_dump(graph, sort_keys=False), encoding="utf-8")
        repo = make_repo(temp / "repo")
        workspace = temp / "runtime"
        run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(blueprint))
        run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
        return workspace

    def test_reorder_cannot_remove_a_locked_dependency(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            workspace = self._locked_dependency_workspace(temp)
            refused = self._propose(
                temp,
                workspace,
                {
                    "classes": ["add_diagnostics"],
                    "operations": [
                        {
                            "op": "reorder",
                            "target_task_id": "TASK-002",
                            "remove_dependencies": ["TASK-001"],
                        }
                    ],
                },
                expect=2,
            )
            self.assertIn("removes locked dependencies", refused["error"])

    def test_reorder_may_add_ordering_the_lock_permits(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            workspace = self._locked_dependency_workspace(temp)
            proposed = self._propose(
                temp,
                workspace,
                {
                    "classes": ["reorder_where_deps_permit"],
                    "operations": [
                        {
                            "op": "reorder",
                            "target_task_id": "TASK-001",
                            "add_dependencies": ["TASK-002"],
                        }
                    ],
                },
            )
            self.assertEqual(proposed["status"], "proposed")
            self.assertEqual(proposed["authority_containment"]["result"], "PASS")


class RetryBudgetTests(unittest.TestCase):
    def test_retries_are_finite_and_exhaustion_cancels(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            # T2 allows three recorded attempts. Each one fails verification
            # because the receipt declares no changed files. A verification
            # FAILED keeps the writer lease, so a retry re-enters at `start`.
            contract, prepared = prepare_attempt(temp, workspace, declared_changed=[])
            verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
            self.assertEqual(verification["verdict"], "FAILED")
            receipt = {
                "schema": "program-execution-controller.attempt-receipt.v2",
                "task_id": "TASK-001",
                "contract_digest": contract["contract_digest"],
                "program_digest": contract["program_digest"],
                "base_sha": contract["base_sha"],
                "candidate_sha": None,
                "changed_files": [],
                "validation_results": [
                    {"command": command, "status": "PASS", "exit_code": 0, "evidence": "x"}
                    for command in contract["validation_commands"]
                ],
                "produced_evidence": [],
                "residual_unknowns": [],
                "claimed_status": "completed",
            }
            receipt_path = write_json(temp / "retry.attempt.json", receipt)
            for attempt in (2, 3):
                run_cli("start", "TASK-001", "--workspace", str(workspace), "--actor", "worker")
                run_cli(
                    "record-attempt",
                    "TASK-001",
                    "--workspace",
                    str(workspace),
                    "--receipt",
                    str(receipt_path),
                )
                verification = run_cli("verify", "TASK-001", "--workspace", str(workspace))
                self.assertEqual(verification["verdict"], "FAILED", attempt)
            refused = run_cli(
                "start", "TASK-001", "--workspace", str(workspace), "--actor", "worker", expect=2
            )
            self.assertIn("retry budget exhausted", refused["error"])
            self.assertEqual(_state(workspace, "TASK-001"), "CANCELLED")
            status = run_cli("status", "--workspace", str(workspace))
            self.assertFalse(status.get("active_leases"))
            events = [e for e in _ledger_events(workspace) if e.get("type") == "TASK_CANCELLED"]
            self.assertTrue(events)
            cleanup_worktree(repo, workspace)


class TruthfulCloseTests(unittest.TestCase):
    def _completed_program(self, temp: Path) -> tuple[Path, Path]:
        _, repo, workspace = bootstrap_repo(temp)
        register_contract(temp, workspace)
        verification, _ = _verified(temp, workspace)
        _gate_pass(workspace, verification["evidence_id"])
        _complete(workspace, "TASK-001", verification["evidence_id"])
        return repo, workspace

    def test_close_refuses_a_success_verdict_over_a_halt(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            repo, workspace = self._completed_program(temp)
            run_cli(
                "halt", "--workspace", str(workspace), "--reason", "operator stop", "--actor", "op"
            )
            refused = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--verdict",
                "CONVERGED",
                expect=2,
            )
            self.assertIn("exceeds the Controller recommendation", refused["error"])
            status = json.loads((workspace / "runtime" / "campaign-status.json").read_text())
            self.assertEqual(status["runtime_status"], "active")
            cleanup_worktree(repo, workspace)

    def test_close_refuses_a_success_verdict_over_a_tampered_ledger(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            repo, workspace = self._completed_program(temp)
            ledger = workspace / "ledger" / "events.jsonl"
            ledger.write_text(ledger.read_text() + '{"tampered":true}\n', encoding="utf-8")
            refused = run_cli(
                "close",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--verdict",
                "CONVERGED",
                expect=2,
            )
            self.assertIn("recommendation", refused["error"])
            cleanup_worktree(repo, workspace)


class LedgerIntegrityTests(unittest.TestCase):
    def test_transitions_refuse_to_land_on_a_tampered_ledger(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            verification, _ = _verified(temp, workspace)
            ledger = workspace / "ledger" / "events.jsonl"
            ledger.write_text(ledger.read_text() + '{"tampered":true}\n', encoding="utf-8")
            refused = _gate_pass(workspace, verification["evidence_id"], expect=2)
            self.assertIn("ledger integrity failure", refused["error"])
            refused = _complete(workspace, "TASK-001", verification["evidence_id"], expect=2)
            self.assertIn("ledger integrity failure", refused["error"])
            cleanup_worktree(repo, workspace)


class BootstrapVisibilityTests(unittest.TestCase):
    def test_skipped_blueprint_validation_is_recorded_never_silent(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = make_blueprint(temp / "blueprint")
            workspace = temp / "runtime"
            result = run_cli(
                "bootstrap", "--workspace", str(workspace), "--blueprint", str(blueprint)
            )
            self.assertEqual(result["blueprint_validation"], "skipped")
            events = [
                event
                for event in _ledger_events(workspace)
                if event.get("type") == "BLUEPRINT_VALIDATION_SKIPPED"
            ]
            self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
