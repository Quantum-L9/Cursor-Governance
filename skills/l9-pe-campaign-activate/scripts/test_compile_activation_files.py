#!/usr/bin/env python3
"""Tests for the PE campaign activation compiler.

Metadata:
  parent: l9-pe-campaign-activate
  layer: script
  role: test
  version: 1.0.0
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import authorize_campaign_merge  # noqa: E402
from compile_activation_files import (  # noqa: E402
    ALLOWED_CAMPAIGN_FILES,
    FORBIDDEN_CAMPAIGN_FILES,
    CompileError,
    compile_activation,
    dump_yaml,
)

HOST_POLICY = """schema: l9.program-execution.campaign-execution-policy.v1
campaigns:
  - id: bounded-replanning-v1
    integration_branch: campaign/bounded-replanning-v1
    pr_base: campaign/bounded-replanning-v1
    execute_order: 1
    lane: pe_host

owner:
  authority_id: AUTH-001
"""

HOST_PROFILE = """campaign_execution:
  merge: forbidden
  campaigns:
    bounded-replanning-v1:
      integration_branch: campaign/bounded-replanning-v1

authority_order:
  - CANONICAL_LAW.campaign_execution_pr_no_merge
"""

HOST_STATUS = """schema: l9.program-execution.campaign-status-ledger.v1
updated: "2026-08-15T00:00:00Z"
campaigns:
  - id: bounded-replanning-v1
    lifecycle: complete
"""

STUB_INTENT = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "tasks": [
        {"title": "Lock current state", "objective": "Record baseline."},
        {"title": "Implement change", "objective": "Edit declared paths only."},
    ],
}

INTENT = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "plan_status": "Ready",
    "tasks": [
        {
            "title": "Lock current state",
            "objective": "Record baseline SHA and refuse dirty overlap.",
            "actions": ["record_baseline_sha"],
            "acceptance": [
                {
                    "id": "AC-001",
                    "statement": "Baseline SHA is recorded and matches HEAD.",
                    "required_evidence_types": ["inspection"],
                }
            ],
            "nugget_id": "NUG-001",
            "kernel_profile": "AUDIT",
            "consumers": ["controller"],
            "entrypoints": ["compile_activation"],
            "validation": [{"id": "VAL-001", "command": "git rev-parse HEAD"}],
        },
        {
            "title": "Implement change",
            "objective": "Edit declared paths only.",
            "actions": ["edit_only_declared_paths"],
            "acceptance": [
                {
                    "id": "AC-002",
                    "statement": "Declared paths contain the required change.",
                    "required_evidence_types": ["inspection"],
                }
            ],
            "nugget_id": "NUG-002",
            "kernel_profile": "BUILD",
            "consumers": ["workers"],
            "entrypoints": ["pec_render"],
            "validation": [{"id": "VAL-002", "command": "python3 -m py_compile"}],
            "paths": ["docs/program-execution/TASK-002.md"],
        },
    ],
}


def _repo(tmp: Path) -> Path:
    (tmp / "environment/program-execution/campaigns").mkdir(parents=True)
    (tmp / "ops/autonomy").mkdir(parents=True)
    (tmp / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml").write_text(
        HOST_POLICY, encoding="utf-8"
    )
    (tmp / "ops/autonomy/surface_profile.yaml").write_text(HOST_PROFILE, encoding="utf-8")
    (tmp / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml").write_text(
        HOST_STATUS, encoding="utf-8"
    )
    intent = tmp / "intent.yaml"
    dump_yaml(intent, INTENT)
    return tmp


class CompileActivationTests(unittest.TestCase):
    def test_emits_only_allowed_campaign_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            result = compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            campaign_dir = root / "environment/program-execution/campaigns/demo-activate-v1"
            names = {path.name for path in campaign_dir.iterdir() if path.is_file()}
            self.assertEqual(names, ALLOWED_CAMPAIGN_FILES)
            self.assertTrue(FORBIDDEN_CAMPAIGN_FILES.isdisjoint(names))
            self.assertEqual(
                result["wrote"],
                [
                    "environment/program-execution/campaigns/demo-activate-v1/CAMPAIGN_SOURCE.yaml",
                    "environment/program-execution/campaigns/demo-activate-v1/source-integrity-receipt.json",
                ],
            )
            self.assertEqual(
                set(result["patched"]),
                {
                    "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml",
                    "ops/autonomy/surface_profile.yaml",
                    "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml",
                },
            )

    def test_source_is_schema_and_compiler_admissible(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            source_path = (
                root
                / "environment/program-execution/campaigns/demo-activate-v1/CAMPAIGN_SOURCE.yaml"
            )
            pe_root = Path(__file__).resolve().parents[3] / "environment" / "program-execution"
            sys.path.insert(0, str(pe_root / "scripts"))
            from compile_campaign_source import (  # noqa: PLC0415
                _semantic_precheck,
                load_yaml,
                validate_campaign_source,
            )

            src = load_yaml(source_path)
            self.assertEqual(validate_campaign_source(src), [])
            self.assertEqual(_semantic_precheck(src), [])
            self.assertEqual(src["metadata"]["status"], "operator_intake")
            self.assertEqual(src["program"]["definition_status"], "ready")
            self.assertEqual(src["program"]["plan_status"], "Ready")
            self.assertEqual(src["tasks"][0]["nugget_id"], "NUG-001")
            self.assertEqual(src["tasks"][0]["definition_status"], "ready")
            self.assertEqual(src["tasks"][1]["definition_status"], "ready")
            receipt = json.loads(
                source_path.with_name("source-integrity-receipt.json").read_text(encoding="utf-8")
            )
            self.assertTrue(receipt["digest_matches_pack"])
            self.assertEqual(receipt["bytes"], source_path.stat().st_size)

    def test_idempotent_host_patches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            second = compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            self.assertEqual(second["patched"], [])
            policy = (
                root / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
            ).read_text(encoding="utf-8")
            self.assertEqual(policy.count("id: demo-activate-v1"), 1)

    def test_refuses_stub_actions_and_unsealed_plan(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            dump_yaml(
                root / "intent.yaml",
                {
                    **INTENT,
                    "plan_status": "Draft",
                    "tasks": [
                        {
                            "title": "Hollow",
                            "actions": ["implement_task_001"],
                            "acceptance": [
                                {
                                    "id": "AC-001",
                                    "statement": "Hollow is complete and locally verified.",
                                }
                            ],
                        }
                    ],
                },
            )
            with self.assertRaises(CompileError):
                compile_activation(root / "intent.yaml", root)

    def test_rejects_bad_id(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            dump_yaml(root / "intent.yaml", {**INTENT, "campaign_id": "Bad_ID"})
            with self.assertRaises(CompileError):
                compile_activation(root / "intent.yaml", root)

    def test_rejects_forbidden_extra(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            extra = root / "environment/program-execution/campaigns/demo-activate-v1/README.md"
            extra.write_text("nope\n", encoding="utf-8")
            with self.assertRaises(CompileError):
                compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")

    def test_fills_residue_for_title_objective_seed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            dump_yaml(root / "intent.yaml", {**STUB_INTENT, "plan_status": "ConditionallyReady"})
            compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            source_path = (
                root
                / "environment/program-execution/campaigns/demo-activate-v1/CAMPAIGN_SOURCE.yaml"
            )
            from compile_activation_files import load_yaml  # noqa: PLC0415

            src = load_yaml(source_path)
            self.assertEqual(src["program"]["plan_status"], "ConditionallyReady")
            self.assertEqual(src["tasks"][0]["nugget_id"], "NUG-001")
            self.assertTrue(src["tasks"][0]["actions"])
            self.assertTrue(src["tasks"][0]["consumers"])
            self.assertTrue(src["tasks"][0]["entrypoints"])
            self.assertTrue(src["tasks"][0]["validation"])
            self.assertTrue(src["tasks"][0]["acceptance"])
            self.assertTrue((source_path.with_name("source-integrity-receipt.json")).is_file())

    def test_refuses_plan_status_partial(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _repo(Path(raw))
            dump_yaml(root / "intent.yaml", {**INTENT, "plan_status": "Partial"})
            with self.assertRaises(CompileError) as ctx:
                compile_activation(root / "intent.yaml", root, stamp="2026-08-15T00:00:00Z")
            self.assertIn("plan_status", str(ctx.exception))
            self.assertFalse(
                (
                    root
                    / "environment/program-execution/campaigns/demo-activate-v1"
                    / "source-integrity-receipt.json"
                ).is_file()
            )


class CampaignMergeAuthorityTests(unittest.TestCase):
    """Program Execution owns no merge authority.

    The wrapper used to re-export `write_authorization` from
    `ops/autonomy/authorize_merge.py`, which is where that behavior is still
    owned and tested (`tests/ops/autonomy/test_authorize_merge.py`). The campaign
    wrapper must now be fail-closed instead.
    """

    def test_wrapper_exports_no_authorization_writer(self) -> None:
        for name in ("write_authorization", "auth_path", "REPO_SCOPE"):
            self.assertFalse(
                hasattr(authorize_campaign_merge, name),
                msg=f"campaign wrapper still re-exports {name}",
            )

    def test_wrapper_fails_closed_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            before = sorted(item.name for item in root.iterdir())
            self.assertNotEqual(authorize_campaign_merge.main(), 0)
            self.assertEqual(sorted(item.name for item in root.iterdir()), before)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
