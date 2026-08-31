"""GMP-133: dispatch, signals, claim projection, routing, worker_cannot_self_verify."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from helpers import bootstrap_repo, cleanup_worktree, prepare_attempt, register_contract, run_cli

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from pec.dispatch import (  # noqa: E402
    DispatchError,
    assert_worker_cannot_self_verify,
    dispatch_rendered_contract,
    map_provider_result_to_presubmission,
    pe_root,
    route_rendered,
)
from pec.signals import list_dry_run_queue  # noqa: E402


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
        result = dispatch_rendered_contract(
            rendered,
            provider=_StubProvider(),
            invoke=True,
            capability_receipts={"cursor-foreground": {"status": "PASS"}},
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
            self.assertIn(rendered["dispatch"]["dispatch"]["status"], {"ROUTED", "UNSUPPORTED"})
            cleanup_worktree(repo, workspace)

    def test_record_attempt_enqueues_distill_job(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            _, repo, workspace = bootstrap_repo(temp)
            register_contract(temp, workspace)
            prepare_attempt(temp, workspace)
            names = [path.name for path in list_dry_run_queue(workspace)]
            self.assertTrue(any("record-attempt" in name for name in names), names)
            cleanup_worktree(repo, workspace)


if __name__ == "__main__":
    unittest.main()
