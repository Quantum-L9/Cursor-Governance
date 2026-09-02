"""GMP-133: dispatch, signals, claim projection, routing, worker_cannot_self_verify."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from pec import controller  # noqa: E402
from pec.dispatch import (  # noqa: E402
    DispatchError,
    assert_worker_cannot_self_verify,
    dispatch_rendered_contract,
    map_provider_result_to_presubmission,
    pe_root,
    route_rendered,
)
from pec.signals import (  # noqa: E402
    list_dry_run_queue,
    publish_controller_event,
)
from peer_execution.models import CapabilityReceipt  # noqa: E402


class _StubProvider:
    def probe(self, context: object) -> SimpleNamespace:
        return SimpleNamespace(status="PASS", observed_capabilities=("inspect", "local_write"))

    def invoke(self, request: object) -> SimpleNamespace:
        return SimpleNamespace(
            status="PASS",
            result=SimpleNamespace(
                status="PASS",
                structured_payload={
                    "candidate_sha": None,
                    "changed_files": [],
                    "validation_results": [],
                    "residual_unknowns": [],
                },
            ),
        )


class UnifiedLoopSeamTests(unittest.TestCase):
    def test_codex_row_and_dormant_route_is_unsupported(self) -> None:
        policy = (pe_root() / "registry" / "EXECUTION_ROUTING_POLICY.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("tightly_scoped_mechanical:", policy)
        self.assertIn("codex-cloud", policy)
        self.assertIn("worker_cannot_self_verify", policy)
        self.assertIn("no_match_returns_CAPABILITY_UNSUPPORTED", policy)
        routed = route_rendered(
            {
                "action_class": "tightly_scoped_mechanical",
                "requested_actions": ["local_write"],
                "target_kind": "git_repository",
            }
        )
        self.assertEqual(routed["status"], "UNSUPPORTED")
        self.assertEqual(routed["error_code"], "CAPABILITY_UNSUPPORTED")
        self.assertEqual(routed["fallback"], "manual_worker_brief")

    def test_unknown_action_class_is_unsupported(self) -> None:
        routed = route_rendered({"action_class": "not-a-real-class", "requested_actions": []})
        self.assertEqual(routed["status"], "UNSUPPORTED")
        self.assertEqual(routed["error_code"], "CAPABILITY_UNSUPPORTED")

    def test_worker_cannot_self_verify(self) -> None:
        with self.assertRaises(DispatchError):
            assert_worker_cannot_self_verify({"independent_verification": True})
        with self.assertRaises(DispatchError):
            map_provider_result_to_presubmission(
                {
                    "task_id": "TASK-001",
                    "contract_digest": "x",
                    "program_digest": "y",
                    "base_sha": "z",
                },
                status="PASS",
                structured_payload={"independent_verification": True},
            )

    def test_dispatch_probe_invoke_maps_presubmission(self) -> None:
        rendered = {
            "task_id": "TASK-001",
            "contract_digest": "sha256:" + "a" * 64,
            "program_digest": "sha256:" + "b" * 64,
            "base_sha": "c" * 40,
            "attempt_number": 1,
            "worktree": "/tmp",
            "requested_actions": ["inspect"],
            "action_class": "read_only_architecture_or_artifact_work",
            "target_kind": "git_repository",
            "independent_verification": False,
        }
        lock = str(rendered["program_digest"])
        receipt = CapabilityReceipt.create(
            adapter_id="cursor-foreground",
            adapter_version="1.0.0",
            status="PASS",
            capabilities=["inspect"],
            program_lock_digest=lock,
        ).to_dict()
        result = dispatch_rendered_contract(
            rendered,
            provider=_StubProvider(),
            invoke=True,
            capability_receipts={"cursor-foreground": receipt},
        )
        self.assertEqual(result["dispatch"]["status"], "ROUTED")
        self.assertEqual(result["probe"]["status"], "PASS")
        receipt = result["attempt_receipt_presubmission"]
        self.assertTrue(receipt["presubmission"])
        self.assertFalse(receipt["independent_verification"])
        self.assertEqual(receipt["task_id"], "TASK-001")

    def test_claim_projection_render_dispatch_and_record_signal(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            claim = run_cli(
                "claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker"
            )
            self.assertIn("autonomy_action_id", claim)
            self.assertIn("autonomy_packet_skeleton", claim)
            run_cli("prepare", "TASK-001", "--workspace", str(workspace))
            rendered = run_cli("render-contract", "TASK-001", "--workspace", str(workspace))
            self.assertIn("dispatch", rendered)
            plan = rendered["dispatch"]["dispatch"]
            # Naming the expected status is the point: accepting either of the
            # only two values route_rendered can return asserts nothing. The
            # standard fixture contract declares no action_class, so the honest
            # expectation is a fail-closed plan with the manual fallback.
            self.assertEqual(plan["status"], "UNSUPPORTED", plan)
            self.assertEqual(plan["error_code"], "CAPABILITY_UNSUPPORTED", plan)
            self.assertEqual(plan["fallback"], "manual_worker_brief", plan)
            cleanup_worktree(repo, workspace)

    def test_record_attempt_enqueues_distill_job(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            jobs = list_dry_run_queue(workspace)
            names = [path.name for path in jobs]
            self.assertTrue(any("record-attempt" in name for name in names), names)
            cleanup_worktree(repo, workspace)

    def test_distill_job_carries_a_usable_subject(self) -> None:
        """A job of key *names* cannot be distilled. Regression for the empty payload."""

        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            jobs = [p for p in list_dry_run_queue(workspace) if "record-attempt" in p.name]
            self.assertTrue(jobs, "no record-attempt job enqueued")
            job = json.loads(jobs[0].read_text(encoding="utf-8"))
            self.assertEqual(job["subject"]["task_id"], "TASK-001")
            self.assertRegex(job["receipt_digest"], r"^[0-9a-f]{64}$")
            cleanup_worktree(repo, workspace)

    def test_two_signals_in_one_second_do_not_overwrite(self) -> None:
        with TemporaryDirectory() as raw:
            workspace = Path(raw)
            for _ in range(2):
                publish_controller_event(
                    workspace, event="verify", receipt={"task_id": "TASK-001", "status": "OK"}
                )
            self.assertEqual(len(list_dry_run_queue(workspace)), 2)

    def test_signal_failure_never_fails_the_operation(self) -> None:
        """Observability is not authority: a dead queue must not fail a committed op."""

        with TemporaryDirectory() as raw:
            workspace = Path(raw)
            # A file where the queue directory must go: mkdir raises NotADirectoryError.
            (workspace / "runtime").mkdir()
            (workspace / "runtime" / "distill_queue").write_text("not a dir", encoding="utf-8")
            out = publish_controller_event(
                workspace, event="verify", receipt={"task_id": "TASK-001"}
            )
            self.assertEqual(out["distill"]["status"], "failed")
            self.assertFalse(out["distill"]["accepted"])

    def test_claim_survives_a_projection_that_raises(self) -> None:
        """The projection runs after TASK_LEASED is durable. It must never raise out.

        Without the guard the task is left in_progress under a lease the caller
        never received: unclaimable by anyone, recoverable only by hand.
        """

        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)

            # Raise from contract_mapper itself -- patching
            # _claim_autonomy_projection would replace the guard under test.
            mapper_dir = str(pe_root() / "integrations" / "autonomy-control-plane")
            if mapper_dir not in sys.path:
                sys.path.insert(0, mapper_dir)
            import contract_mapper

            def _raise(*args: object, **kwargs: object) -> None:
                # The real shape: require_coherent_actions raises
                # ContractActionError(ValueError) on an incoherent action set.
                raise contract_mapper.ContractActionError(
                    "contract requests 'commit' without 'local_write'."
                )

            original = contract_mapper.map_program_contract
            contract_mapper.map_program_contract = _raise
            try:
                lease = controller.claim_task(workspace, "TASK-001", holder="worker")
            finally:
                contract_mapper.map_program_contract = original
            self.assertTrue(lease.get("lease_id"), lease)
            self.assertNotIn("autonomy_action_id", lease)
            self.assertIn("ContractActionError", lease["autonomy_projection_error"])
            # The task stays claimed by THIS caller, holding the lease it got.
            in_progress = controller.next_tasks(workspace)["in_progress"]
            self.assertEqual([t["id"] for t in in_progress], ["TASK-001"])
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
