"""Golden semantic vectors and blocking parity gate conformance (TASK-005)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from peer_execution.golden_vectors import (
    ALLOWED_DELTA_CLASSES,
    FORBIDDEN_DELTA_CLASSES,
    GOLDEN_VECTORS,
    evaluate_vector,
    run_parity_gate,
)
from peer_execution.replan_projection import build_semantic_revision, project_to_peers

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent.parent
CONTRACT = ROOT / "core/shared/REPLAN_CONTRACT.yaml"
SCHEMA = ROOT / "core/shared/schemas/replan-revision.schema.json"


class GoldenVectorTests(unittest.TestCase):
    def test_all_required_vectors_are_present(self) -> None:
        ids = {vector["vector_id"] for vector in GOLDEN_VECTORS}
        self.assertSetEqual(
            ids,
            {
                "valid_bounded_replan",
                "permission_widening",
                "architecture_boundary",
                "missing_authority",
                "scoped_unknown",
                "structural_vs_runtime_evidence",
                "replan_outside_program_lock",
                "unsupported_peer",
                "peer_local_override",
            },
        )

    def test_every_vector_matches_its_golden_expectation(self) -> None:
        for vector in GOLDEN_VECTORS:
            result = evaluate_vector(vector)
            self.assertEqual(
                result["authority_result"],
                vector["expected"]["authority_result"],
                vector["vector_id"],
            )
            self.assertEqual(result["blocker"], vector["expected"]["blocker"], vector["vector_id"])
            self.assertEqual(
                result["escalation"], vector["expected"]["escalation"], vector["vector_id"]
            )

    def test_delta_classes_pinned_to_canonical_contract(self) -> None:
        import yaml

        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            FORBIDDEN_DELTA_CLASSES,
            set(contract["forbidden_authority_delta_classes"]),
        )
        self.assertEqual(
            ALLOWED_DELTA_CLASSES,
            set(contract["allowed_delta_classes"]),
        )

    def test_unknown_delta_class_is_rejected(self) -> None:
        vector = {
            "vector_id": "unknown_class",
            "scenario": "A delta class outside the contract is rejected.",
            "input": {
                "delta_classes": ["silent_objective_edit"],
                "trigger_evidence_ids": ["EVID-001"],
                "program_lock_matches": True,
                "previous_plan_revision_matches": True,
            },
        }
        result = evaluate_vector(vector)
        self.assertEqual(result["authority_result"], "REJECTED")
        self.assertEqual(result["blocker"], "unknown_delta_class")

    def test_parity_gate_passes_for_current_registry(self) -> None:
        semantic = build_semantic_revision(
            CONTRACT,
            SCHEMA,
            replan_revision_id="rev-1",
            plan_revision="plan-rev-0+rev-1",
            activated_at="2026-08-14T22:00:00+00:00",
            actor="controller",
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            project_to_peers(REPO_ROOT, workspace, semantic_revision=semantic, actor="controller")
            report = run_parity_gate(REPO_ROOT, workspace)
            self.assertEqual(report["status"], "PASS", report["failures"])
            self.assertTrue(report["per_peer_digests"])
            peer_digests = {
                entry["normalized_vector_digest"] for entry in report["per_peer_digests"]
            }
            self.assertEqual(len(peer_digests), 1)

    def test_parity_gate_blocks_when_a_peer_diverges(self) -> None:
        semantic = build_semantic_revision(
            CONTRACT,
            SCHEMA,
            replan_revision_id="rev-1",
            plan_revision="plan-rev-0+rev-1",
            activated_at="2026-08-14T22:00:00+00:00",
            actor="controller",
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            project_to_peers(REPO_ROOT, workspace, semantic_revision=semantic, actor="controller")
            accounting_path = workspace / "runtime/projection/peer-accounting.json"
            accounting = json.loads(accounting_path.read_text(encoding="utf-8"))
            # Simulate one peer left on a superseded semantic revision.
            accounting["records"][0]["semantic_revision_digest"] = "sha256:" + "0" * 64
            accounting_path.write_text(
                json.dumps(accounting, sort_keys=True) + "\n", encoding="utf-8"
            )
            report = run_parity_gate(REPO_ROOT, workspace)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("cross_peer_normalized_divergence", report["failures"])

    def test_parity_gate_cli_exits_nonzero_when_blocked(self) -> None:
        script = ROOT / "scripts/run_parity_gate.py"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            proc = subprocess.run(
                [sys.executable, str(script), str(REPO_ROOT), "--workspace", str(workspace)],
                capture_output=True,
                text=True,
                cwd=ROOT,
            )
            self.assertEqual(proc.returncode, 1)
            report = json.loads(proc.stdout)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertIn("peer_accounting_missing", report["failures"])


if __name__ == "__main__":
    unittest.main()
