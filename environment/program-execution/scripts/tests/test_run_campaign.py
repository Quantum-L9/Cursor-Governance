from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"
ACTIVATE = PE_ROOT.parents[1] / "skills/l9-pe-campaign-activate/scripts/compile_activation_files.py"

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

READY_SEED = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "plan_status": "Ready",
    "tasks": [
        {
            "id": "TASK-001",
            "title": "Lock current state",
            "objective": "Record baseline.",
            "actions": ["inspect_repository_head"],
            "consumers": ["pec"],
            "entrypoints": ["make campaign"],
            "validation": [{"command": "python3 -c 'print(0)'"}],
            "nugget_id": "nugget-task-001",
            "acceptance": [
                {
                    "id": "AC-001",
                    "statement": "Baseline is recorded.",
                    "required_evidence_types": ["runtime_behavior"],
                }
            ],
        },
        {
            "id": "TASK-002",
            "title": "Implement change",
            "objective": "Edit declared paths only.",
            "actions": ["edit_only_declared_paths"],
            "consumers": ["pec"],
            "entrypoints": ["make campaign"],
            "validation": [{"command": "python3 -c 'print(0)'"}],
            "nugget_id": "nugget-task-002",
            "acceptance": [
                {
                    "id": "AC-002",
                    "statement": "Declared paths contain the change.",
                    "required_evidence_types": ["runtime_behavior"],
                }
            ],
        },
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


def _write_task_output(worktree: Path, rel: str, title: str) -> str:
    path = worktree / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{Path(rel).stem} implemented for tests: {title}\n" + ("x" * 48) + "\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(worktree), "add", "--", rel], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(worktree), "commit", "-m", f"pec: {Path(rel).stem} output"],
        check=True,
        capture_output=True,
    )
    sha = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return sha.stdout.strip()


def _stack_ok(seed, primed_dir):
    path = Path(primed_dir) / str(seed["campaign_id"]) / "stack-proof.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "l9.program-execution.stack-proof.v1",
        "status": "pass",
        "tools": [],
        "path": str(path),
    }
    path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    return receipt


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
    _dump(tmp / "intent.yaml", READY_SEED)
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

    def test_cli_refuses_until_shortcut(self) -> None:
        self.mod.refuse_live_until_shortcut("close")
        self.mod.refuse_live_until_shortcut("merge")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("L9_CAMPAIGN_UNTIL_DEBUG", None)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.refuse_live_until_shortcut("activate")
            self.assertIn("CAMPAIGN_UNTIL is not a live campaign path", str(ctx.exception))
        with patch.dict(os.environ, {"L9_CAMPAIGN_UNTIL_DEBUG": "1"}):
            self.mod.refuse_live_until_shortcut("activate")

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

    def test_require_remote_campaign_branch_missing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.require_remote_campaign_branch(root, "demo-activate-v1")
            self.assertIn("remote campaign/demo-activate-v1 missing", str(ctx.exception))

    def test_pushes_campaign_branch_before_execute(self) -> None:
        order: list[str] = []

        def emit(intent: Path, repo_root: Path) -> dict[str, object]:
            campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True, exist_ok=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
            return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)
            self.mod.run_campaign(
                root / "intent.yaml",
                until="execute",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=emit,
                    compile_source=lambda source, target: None,
                    validate_blueprint=lambda target: [],
                    admit=lambda blueprint: {},
                    pec_bootstrap=lambda workspace, blueprint: {
                        "ok": True,
                        "draft": False,
                        "output": "ok",
                    },
                    arm=lambda workspace, campaign_id: None,
                    push_integration=lambda worktree, campaign_id: order.append("push"),
                    execute=lambda workspace, campaign_id: order.append("execute") or {},
                    make_pr=lambda worktree, campaign_id: {
                        "number": 1,
                        "url": "https://example.test/1",
                    },
                    close=lambda workspace, campaign_id: order.append("close") or {},
                ),
            )
        self.assertEqual(order[:2], ["push", "execute"])

    def test_write_and_commit_output_refuses_stub(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_init(root)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.write_and_commit_output(root, "docs/program-execution/TASK-001.md", "x")
            self.assertIn("refuse stub", str(ctx.exception))

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
                l9_root=Path(raw) / "l9",
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            campaign_dir = root / "environment/program-execution/campaigns/demo-activate-v1"
            names = {path.name for path in campaign_dir.iterdir() if path.is_file()}
            self.assertEqual(names, self.mod.ALLOWED_CAMPAIGN_FILES)
            self.assertEqual(report.stages_completed, ["activate"])
            self.assertTrue(
                (Path(raw) / "l9" / "primed" / "demo-activate-v1" / "stack-proof.json").is_file()
            )
            self.assertNotIn("INTENT.yaml", names)
            ledger = yaml.safe_load(
                (root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml").read_text(
                    encoding="utf-8"
                )
            )
            row = next(item for item in ledger["campaigns"] if item["id"] == "demo-activate-v1")
            self.assertEqual(row["lifecycle"], "in_progress")
            self.assertEqual(row["launched_by"], "make campaign")
            self.assertIn("operator_ack", row["notes"])
            policy = yaml.safe_load(
                (
                    root / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml"
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
            payload = self.mod.activate_pec_runtime(workspace, campaign_id="demo-activate-v1")
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
                    l9_root=Path(raw) / "l9",
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=emit,
                        compile_source=lambda source, target: None,
                        validate_blueprint=lambda target: [],
                        admit=lambda blueprint: {"accepted": True},
                        pec_bootstrap=lambda workspace, blueprint: {
                            "ok": True,
                            "draft": False,
                            "output": "lock",
                        },
                        arm=lambda workspace, campaign_id: {"task_id": "TASK-001"},
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
                        authorize_and_merge=lambda host_repo, number: (
                            merged.append((host_repo, number)) or {}
                        ),
                    ),
                )
            self.assertEqual(ctx.exception.exit_code, 2)
            self.assertIn("host-only merge", str(ctx.exception))
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
            with self.assertRaises((self.mod.CampaignError, self.activate.CompileError)):
                self.mod.run_campaign(
                    brief,
                    until="activate",
                    primary=other_primary,
                    repo_root=root,
                    l9_root=Path(raw) / "l9",
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=self.activate.compile_activation,
                    ),
                )
            campaign_dir = root / "environment/program-execution/campaigns/pe-memory"
            self.assertFalse((campaign_dir / "source-integrity-receipt.json").is_file())

    def test_refuses_hash_campaign_id(self) -> None:
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.refuse_hash_campaign_id("pe-8c9f6de43b25")
        self.assertIn("intent.v1", str(ctx.exception))

    def test_draft_bootstrap_is_not_a_live_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)

            def emit(intent: Path, repo_root: Path) -> dict[str, object]:
                campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
                campaign.mkdir(parents=True, exist_ok=True)
                (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
                (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
                return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="bootstrap",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=Path(raw) / "l9",
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=emit,
                        compile_source=lambda source, target: None,
                        validate_blueprint=lambda target: [],
                        admit=lambda blueprint: {},
                        pec_bootstrap=lambda workspace, blueprint: {
                            "ok": True,
                            "draft": True,
                            "output": "draft-honest",
                        },
                    ),
                )
            self.assertIn("admission-draft", str(ctx.exception))

    def test_until_arm_records_tunnel_stages(self) -> None:
        calls: list[str] = []

        def emit(intent: Path, repo_root: Path) -> dict[str, object]:
            campaign = repo_root / "environment/program-execution/campaigns/demo-activate-v1"
            campaign.mkdir(parents=True, exist_ok=True)
            (campaign / "CAMPAIGN_SOURCE.yaml").write_text("schema: x\n", encoding="utf-8")
            (campaign / "source-integrity-receipt.json").write_text("{}\n", encoding="utf-8")
            return {"wrote": ["CAMPAIGN_SOURCE.yaml"]}

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "root"
            root.mkdir()
            _dump(root / "intent.yaml", ACTIVATE_SEED)
            l9 = Path(raw) / "l9"
            report = self.mod.run_campaign(
                root / "intent.yaml",
                until="arm",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=emit,
                    compile_source=lambda source, target: calls.append("compile") or None,
                    validate_blueprint=lambda target: calls.append("validate") or [],
                    admit=lambda blueprint: calls.append("admit") or {},
                    pec_bootstrap=lambda workspace, blueprint: (
                        calls.append("bootstrap") or {"ok": True, "draft": False, "output": "ok"}
                    ),
                    arm=lambda workspace, campaign_id: calls.append("arm") or {},
                ),
            )
            self.assertEqual(
                report.stages_completed,
                ["activate", "blueprint", "admit", "bootstrap", "arm"],
            )
            self.assertEqual(calls, ["compile", "validate", "admit", "bootstrap", "arm"])
            launch = json.loads(
                (l9 / "programs/demo-activate-v1/runtime/LAUNCH.json").read_text(encoding="utf-8")
            )
            self.assertEqual(launch["campaign_id"], "demo-activate-v1")
            self.assertTrue(launch["only_pec_workspace"])
            self.assertEqual(launch["claimed_task"], "TASK-001")
            self.assertTrue(launch["reconcile_required"])
            self.assertFalse(launch["load_operator_brief"])
            self.assertFalse(launch["operator_ack_required"])
            self.assertTrue(launch["pec_ready_empty_is_expected"])
            self.assertEqual(launch["max_task_minutes"], 15)
            self.assertIn("write_tree", launch)

    def test_quarantine_moves_occupied_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            occupied = Path(raw) / "programs" / "demo-activate-v1"
            occupied.mkdir(parents=True)
            leftover = occupied / "runtime" / "state.sqlite"
            leftover.parent.mkdir(parents=True)
            leftover.write_text("stale\n", encoding="utf-8")
            moved = self.mod.quarantine_occupied(occupied)
            self.assertIsNotNone(moved)
            self.assertFalse(occupied.exists())
            self.assertTrue((moved / "runtime" / "state.sqlite").is_file())

    def test_refuses_dirty_target_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            dest = Path(raw) / "target"
            dest.mkdir()
            _git_init(dest)
            (dest / "dirty.txt").write_text("no\n", encoding="utf-8")
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.default_ensure_target_checkout(dest, "Quantum-L9/Cursor-Governance")
            self.assertIn("dirty", str(ctx.exception))

    def test_real_admit_bootstrap_reconcile_claims_task_001(self) -> None:
        """No mocks on the live tunnel: leftover pec dir cannot block claim."""
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            leftover = l9 / "programs" / "demo-activate-v1" / "runtime"
            leftover.mkdir(parents=True)
            (leftover / "state.sqlite").write_text("stale-draft\n", encoding="utf-8")
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            report = self.mod.run_campaign(
                root / "intent.yaml",
                until="arm",
                primary=Path(raw) / "primary",
                repo_root=root,
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            self.assertEqual(
                report.stages_completed,
                ["activate", "blueprint", "admit", "bootstrap", "arm"],
            )
            workspace = l9 / "programs" / "demo-activate-v1"
            self.assertTrue((workspace / "runtime" / "state.sqlite").is_file())
            stale_dirs = list((l9 / "programs" / "stale").glob("demo-activate-v1-*"))
            self.assertEqual(len(stale_dirs), 1)
            pec = PE_ROOT / "core/program-execution-controller-template/scripts/pec.py"
            status = subprocess.run(
                [sys.executable, str(pec), "status", "--workspace", str(workspace)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            payload = json.loads(status.stdout)
            self.assertFalse(payload.get("admission_draft"))
            task = next(item for item in payload["tasks"] if item["id"] == "TASK-001")
            self.assertEqual(task["runtime_state"], "LEASED")
            task_two = next(item for item in payload["tasks"] if item["id"] == "TASK-002")
            self.assertNotEqual(task_two["runtime_state"], "LEASED")
            self.assertEqual(task_two["definition_status"], "ready")
            self.assertEqual(payload["current"]["task_id"], "TASK-001")
            self.assertTrue((workspace / "runtime" / "TASK-002.source.json").is_file())
            stack = json.loads((workspace / "runtime" / "STACK.json").read_text(encoding="utf-8"))
            self.assertEqual(stack["integration_branch"], "campaign/demo-activate-v1")
            self.assertEqual(stack["stack"][0]["pr_base"], "campaign/demo-activate-v1")
            self.assertEqual(stack["stack"][1]["pr_base"], "pec/w0/task-001")
            self.assertNotIn("main", stack["stack"][0]["pr_base"])
            card = (workspace / "runtime" / "TASK-001.md").read_text(encoding="utf-8")
            self.assertIn("Budget: 15 minutes", card)
            self.assertIn("never main", card)
            self.assertNotIn("PE- Memory", card)
            self.assertLess(len(card.splitlines()), 18)
            self.assertTrue((workspace / "runtime" / "TASK-002.md").is_file())

    def test_pr_stack_never_uses_main(self) -> None:
        stack = self.mod.build_pr_stack(
            "demo-activate-v1",
            [
                {"id": "TASK-001", "title": "First", "wave_id": "W0"},
                {"id": "TASK-002", "title": "Second", "wave_id": "W1"},
            ],
        )
        bases = [item["pr_base"] for item in stack["stack"]]
        self.assertEqual(bases, ["campaign/demo-activate-v1", "pec/w0/task-001"])
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.refuse_unstacked_pr_base("origin/main")
        self.assertIn("stack", str(ctx.exception))

    def test_run_cmd_times_out(self) -> None:
        with self.assertRaises(self.mod.CampaignError) as ctx:
            self.mod.run_cmd([sys.executable, "-c", "import time; time.sleep(5)"], timeout=1)
        self.assertIn("timed out after 1s", str(ctx.exception))

    def test_host_campaign_ids_only_complete_or_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            status = root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml"
            status.write_text(
                "schema: l9.program-execution.campaign-status-ledger.v1\n"
                "campaigns:\n"
                "  - id: live-one\n    lifecycle: in_progress\n"
                "  - id: done-one\n    lifecycle: complete\n"
                "  - id: dead-one\n    lifecycle: cancelled\n",
                encoding="utf-8",
            )
            ids = self.mod.host_campaign_ids(root)
            self.assertIn("done-one", ids)
            self.assertIn("dead-one", ids)
            self.assertNotIn("live-one", ids)

    def test_donor_rejected_when_origin_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            donor = Path(raw) / "donor"
            dest = Path(raw) / "dest"
            donor.mkdir()
            _git_init(donor)
            self.assertFalse(self.mod.donor_matches_repository(donor, "Quantum-L9/l9-ci-core"))
            with self.assertRaises(self.mod.CampaignError):
                self.mod.default_ensure_target_checkout(
                    dest, "Quantum-L9/definitely-missing-repo-xyz", donor=donor
                )

    def test_isolate_quarantines_dirty_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primary = Path(raw) / "primary"
            worktree = Path(raw) / "wt"
            primary.mkdir()
            _git_init(primary)
            subprocess.run(
                ["git", "-C", str(primary), "branch", "feat/demo-activate-v1"],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(primary),
                    "worktree",
                    "add",
                    str(worktree),
                    "feat/demo-activate-v1",
                ],
                check=True,
                capture_output=True,
            )
            (worktree / "dirty.txt").write_text("no\n", encoding="utf-8")
            self.assertTrue(self.mod.is_dirty(worktree))

            def fake_git(*args: str) -> str:
                if args[:2] == ("fetch", "origin"):
                    return ""
                raise self.mod.CampaignError("stop after quarantine")

            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.isolate_worktree(primary, "demo-activate-v1", worktree, git_fn=fake_git)
            self.assertIn("stop after quarantine", str(ctx.exception))
            self.assertFalse(worktree.exists())
            stale = list((Path(raw) / "stale").glob("wt-*"))
            self.assertEqual(len(stale), 1)
            self.assertTrue((stale[0] / "dirty.txt").is_file())

    def test_policy_remediation_scope_is_stacked_only(self) -> None:
        policy = yaml.safe_load(
            (PE_ROOT / "campaigns/CAMPAIGN_EXECUTION_POLICY.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            policy["publish"]["remediations"]["scope"],
            "stacked_prs_opened_by_this_run",
        )
        self.assertNotEqual(
            policy["publish"]["remediations"]["scope"],
            "all_open_prs_in_target_repo",
        )

    def test_two_task_fixture_reaches_completed(self) -> None:
        opened: list[str] = []
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw) / "host")
            l9 = Path(raw) / "l9"
            target = l9 / "program-worktrees" / "demo-activate-v1"
            target.mkdir(parents=True)
            _git_init(target)
            with self.assertRaises(self.mod.CampaignError) as ctx:
                self.mod.run_campaign(
                    root / "intent.yaml",
                    until="close",
                    primary=Path(raw) / "primary",
                    repo_root=root,
                    l9_root=l9,
                    hooks=self.mod.Hooks(
                        context7_stack=_stack_ok,
                        write_task_output=_write_task_output,
                        compile_activation=self.activate.compile_activation,
                        make_pr=lambda worktree, campaign_id: (
                            opened.append(campaign_id)
                            or {"number": 7, "url": "https://example.test/7"}
                        ),
                    ),
                )
            self.assertIn("INCOMPLETE", str(ctx.exception))
            self.assertIn("skip CHANGE", str(ctx.exception))
            self.assertEqual(opened, [])

    def test_until_stages_unchanged(self) -> None:
        self.assertEqual(
            self.mod.UNTIL_STAGES,
            (
                "activate",
                "blueprint",
                "admit",
                "bootstrap",
                "arm",
                "execute",
                "pr",
                "close",
            ),
        )

    def test_plan_window_writes_nuggets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = _host_repo(Path(raw))
            l9 = Path(raw) / "l9"
            self.mod.run_campaign(
                root / "intent.yaml",
                until="activate",
                primary=Path(raw) / "other-primary",
                repo_root=root,
                l9_root=l9,
                hooks=self.mod.Hooks(
                    context7_stack=_stack_ok,
                    write_task_output=_write_task_output,
                    compile_activation=self.activate.compile_activation,
                ),
            )
            nuggets = l9 / "primed" / "demo-activate-v1" / "nuggets.json"
            self.assertTrue(nuggets.is_file())
            payload = json.loads(nuggets.read_text(encoding="utf-8"))
            self.assertTrue(any(item.get("cites") == "stack-proof.json" for item in payload["nuggets"]))

    def test_incomplete_skips_change(self) -> None:
        decision = self.mod.dispatch_kernel_change(
            {"kernel_verdict": "INCOMPLETE", "gates": {"validation": "INCOMPLETE"}}
        )
        self.assertEqual(decision["action"], "skip_change")
        self.assertFalse(decision["diagnosed"])

    def test_fail_diagnoses_then_reverifies(self) -> None:
        calls: list[str] = []
        result = self.mod.apply_fail_change(
            {"kernel_verdict": "FAIL", "gates": {"validation": "FAIL"}},
            rewrite=lambda: calls.append("rewrite"),
            reverify=lambda: calls.append("reverify") or {"kernel_verdict": "PASS"},
        )
        self.assertEqual(decision := result["action"], "change")
        self.assertTrue(result["diagnosed"])
        self.assertEqual(calls, ["rewrite", "reverify"])
        self.assertEqual(result["reverify"]["kernel_verdict"], "PASS")
        self.assertEqual(decision, "change")


if __name__ == "__main__":
    unittest.main()
