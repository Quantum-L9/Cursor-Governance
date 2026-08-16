from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"
ACTIVATE = (
    PE_ROOT.parents[1] / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"
)

HOST_ALLOWLIST = """schema: l9.program-execution.campaign-compile-allowlist.v1
schema_version: 1.0.0
campaign_ids:
  - bounded-replanning-v1
"""

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

ACTIVATE_SEED = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "tasks": [
        {"title": "Lock current state", "objective": "Record baseline."},
        {"title": "Implement change", "objective": "Edit declared paths only."},
    ],
}

INTENT_V1 = {
    "schema": "program-execution.intent.v1",
    "objective": "Make repo X achieve Y.",
    "targets": ["Quantum-L9/l9-ci-core"],
}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _dump(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _host_repo(tmp: Path) -> Path:
    (tmp / "environment/program-execution/campaigns").mkdir(parents=True)
    (tmp / "ops/autonomy").mkdir(parents=True)
    (tmp / "environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml").write_text(
        HOST_ALLOWLIST, encoding="utf-8"
    )
    (tmp / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml").write_text(
        HOST_POLICY, encoding="utf-8"
    )
    (tmp / "ops/autonomy/surface_profile.yaml").write_text(HOST_PROFILE, encoding="utf-8")
    (tmp / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml").write_text(
        HOST_STATUS, encoding="utf-8"
    )
    _dump(tmp / "intent.yaml", ACTIVATE_SEED)
    return tmp


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


class RunCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_under_test", SCRIPT)
        cls.activate = _load("compile_activation_under_test", ACTIVATE)

    def test_rejects_intent_v1(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "intent.yaml"
            _dump(path, INTENT_V1)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.load_activate_seed(path)
            self.assertIn("program-execution.intent.v1", str(ctx.exception))
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.resolve_operator_intent(path, host_root=Path(raw))
            self.assertIn("program-execution.intent.v1", str(ctx.exception))

    def test_refuses_dirty_primary_writes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            primary.mkdir()
            _git_init(primary)
            (primary / "dirty.txt").write_text("no\n", encoding="utf-8")
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.refuse_write_to_dirty_primary(primary, primary)
            self.assertIn("dirty primary", str(ctx.exception))

    def test_until_activate_emits_allowed_set(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            report = self.mod.run_campaign(
                root / "intent.yaml",
                until="activate",
                primary=other_primary,
                repo_root=root,
                hooks=self.mod.Hooks(compile_activation=self.activate.compile_activation),
            )
            campaign_dir = root / "environment/program-execution/campaigns/demo-activate-v1"
            names = {path.name for path in campaign_dir.iterdir() if path.is_file()}
            self.assertEqual(names, self.mod.ALLOWED_CAMPAIGN_FILES)
            self.assertEqual(report.stages_completed, ["activate"])
            self.assertNotIn("INTENT.yaml", names)
            ledger = yaml.safe_load(
                (
                    root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
                ).read_text(encoding="utf-8")
            )
            row = next(item for item in ledger["campaigns"] if item["id"] == "demo-activate-v1")
            self.assertEqual(row["lifecycle"], "in_progress")
            self.assertEqual(row["launched_by"], "make campaign")
            self.assertIn("operator_ack", row["notes"])
            policy = yaml.safe_load(
                (
                    root
                    / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
                ).read_text(encoding="utf-8")
            )
            prow = next(item for item in policy["campaigns"] if item["id"] == "demo-activate-v1")
            self.assertEqual(prow["lifecycle"], "in_progress")

    def test_phase0_ack_is_not_forged(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            blueprint = Path(raw) / "blueprint"
            blueprint.mkdir()
            (blueprint / "PHASE0_USER_CONFIG.yaml").write_text(
                "schema: program-execution-blueprint.phase0-user-config.v2\n"
                "operator_ack:\n  name: Igor Beylin\n  acknowledged_at: null\n"
                "program_deploying: false\n"
                "completeness:\n  phase0_complete: false\n"
                "notes: template\n",
                encoding="utf-8",
            )
            self.mod.annotate_phase0_without_forging_ack(blueprint)
            data = yaml.safe_load((blueprint / "PHASE0_USER_CONFIG.yaml").read_text())
            self.assertIsNone(data["operator_ack"]["acknowledged_at"])
            self.assertEqual(data["operator_ack"]["name"], "Igor Beylin")
            self.assertFalse(data["program_deploying"])
            self.assertFalse(data["completeness"]["phase0_complete"])
            self.assertIn("never forge", data["notes"])

    def test_pec_runtime_marked_active(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw) / "program"
            payload = self.mod.activate_pec_runtime(
                workspace, campaign_id="demo-activate-v1"
            )
            self.assertEqual(payload["runtime_status"], "active")
            stored = json.loads(
                (workspace / "runtime" / "campaign-status.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["runtime_status"], "active")
            self.assertEqual(stored["campaign_id"], "demo-activate-v1")
            self.assertTrue(stored["activated_at"])

    def test_no_merge_on_red_checks(self) -> None:
        merged: list[tuple[str, int]] = []

        def emit(intent: Path, repo_root: Path) -> dict[str, object]:
            campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True, exist_ok=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
            status = repo_root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
            status.parent.mkdir(parents=True, exist_ok=True)
            if not status.is_file():
                status.write_text(HOST_STATUS, encoding="utf-8")
            return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="merge",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    hooks=self.mod.Hooks(
                        compile_activation=emit,
                        compile_source=lambda source, target: None,
                        validate_blueprint=lambda target: [],
                        pec_bootstrap=lambda workspace, blueprint: {
                            "ok": True,
                            "draft": True,
                            "output": "draft-honest",
                        },
                        make_pr=lambda worktree, campaign_id: {
                            "number": 99,
                            "url": "https://example.test/99",
                        },
                        pr_status=lambda host_repo, number: {
                            "number": 99,
                            "url": "https://example.test/99",
                            "green": False,
                            "mergeable": False,
                            "sha": "",
                        },
                        authorize_and_merge=lambda host_repo, number: merged.append(
                            (host_repo, number)
                        )
                        or {},
                    ),
                )
            self.assertEqual(ctx.exception.exit_code, 2)
            self.assertIn("not green", str(ctx.exception))
            self.assertEqual(merged, [])

    def test_until_activate_from_memo(self) -> None:
        fixture = (
            PE_ROOT.parents[1]
            / "skills/l9-pe-campaign-activate/scripts/fixtures/pe-memory-class.md"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            brief = Path(raw) / "PE- Memory.md"
            brief.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
            other_primary = Path(raw) / "other-primary"
            other_primary.mkdir()
            report = self.mod.run_campaign(
                brief,
                until="activate",
                primary=other_primary,
                repo_root=root,
                hooks=self.mod.Hooks(compile_activation=self.activate.compile_activation),
            )
            self.assertEqual(report.campaign_id, "pe-memory")
            campaign_dir = root / "environment/program-execution/campaigns/pe-memory"
            names = {path.name for path in campaign_dir.iterdir() if path.is_file()}
            self.assertEqual(names, self.mod.ALLOWED_CAMPAIGN_FILES)
            self.assertNotIn("INTENT.yaml", names)
            source = yaml.safe_load(
                (campaign_dir / "CAMPAIGN_SOURCE.yaml").read_text(encoding="utf-8")
            )
            self.assertEqual(len(source["tasks"]), 7)


if __name__ == "__main__":
    unittest.main()
