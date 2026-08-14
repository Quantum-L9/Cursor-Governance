#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

PACK_ROOT = Path(__file__).resolve().parents[1]
OVERLAY = PACK_ROOT / "repo_overlay"
PE = OVERLAY / "environment/program-execution"


def _load_apply_module():
    path = PACK_ROOT / "scripts/apply_pr_pack.py"
    spec = importlib.util.spec_from_file_location("peer_pack_apply", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load apply_pr_pack")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout.strip()


class BlockerRepairTests(unittest.TestCase):
    def test_import_ownership_is_complete_after_declared_common_move(self) -> None:
        apply_text = (PACK_ROOT / "scripts/apply_pr_pack.py").read_text(encoding="utf-8")
        self.assertIn(
            (
                '"environment/program-execution/adapters/common",\n'
                '        "environment/program-execution/peer_execution",'
            ),
            apply_text,
        )
        direct = {path.stem for path in (PE / "peer_execution").glob("*.py")}
        moved = {"approvals", "base", "errors", "models", "protocol", "receipts"}
        required = set()
        for path in (PE / "peer_execution").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                    required.add(node.module.split(".", 1)[0])
        self.assertFalse(required - direct - moved)
        self.assertIn("digests", direct)
        self.assertIn("imports", direct)

    def test_every_routable_registry_provider_is_thin(self) -> None:
        registry = yaml.safe_load(
            (PE / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        forbidden_bases = {"BaseExecutionAdapter", "PeerExecutionAdapter", "DriverExecutionAdapter"}
        forbidden_modules = {
            "peer_execution.base",
            "peer_execution.core_receipts",
            "peer_execution.receipts",
            "peer_execution.runtime_store",
        }
        for entry in registry["adapters"]:
            provider = PE / entry["provider_module"]
            self.assertTrue(provider.is_file(), entry["adapter_id"])
            tree = ast.parse(provider.read_text(encoding="utf-8"))
            exported = any(
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "PROVIDER_CLASS"
                    for target in node.targets
                )
                for node in ast.walk(tree)
            )
            if entry.get("status") == "non_routable":
                self.assertFalse(exported, entry["adapter_id"])
                continue
            self.assertTrue(exported, entry["adapter_id"])
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module or "", forbidden_modules, entry["adapter_id"])
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        name = getattr(base, "id", getattr(base, "attr", ""))
                        self.assertNotIn(name, forbidden_bases, entry["adapter_id"])

    def test_peer_providers_do_not_load_generic_context_or_permission_policy(self) -> None:
        peer_ids = {
            "cursor-foreground",
            "cursor-background",
            "claude-code-direct",
            "chatgpt-manual-handoff",
            "codex-cloud",
            "gemini-review",
            "manus-cloud",
        }
        registry = yaml.safe_load(
            (PE / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
        )
        for entry in registry["adapters"]:
            if entry["adapter_id"] not in peer_ids:
                continue
            text = (PE / entry["provider_module"]).read_text(encoding="utf-8")
            self.assertNotIn("peer_execution.context", text)
            self.assertNotIn("peer_execution.permissions", text)
            self.assertNotIn("peer_execution.approvals", text)

    def test_attempt_receipt_is_durable_before_collect_pass_receipt(self) -> None:
        source = (PE / "peer_execution/execution.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        collect = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "collect"
        )
        calls = []
        for node in ast.walk(collect):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    calls.append((node.lineno, node.func.attr))
        write_line = min(line for line, name in calls if name == "_write_attempt_receipt")
        append_line = min(line for line, name in calls if name == "_append")
        self.assertLess(write_line, append_line)
        self.assertIn("attempt receipt target escapes Controller attempts root", source)
        self.assertIn("conflicting evidence", source)

    def test_pipeline_requests_controller_abort_on_post_claim_failures(self) -> None:
        text = (PE / "scripts/run_peer_task_pipeline.py").read_text(encoding="utf-8")
        self.assertIn('"abort-execution"', text)
        for reason in (
            "pre_execution_controller_failure",
            "provider_probe_blocked_after_admission",
            "controller_start_failure",
            "peer_execution_failure",
            "attempt_handoff_or_verification_failure",
            "controller_verification_failed",
        ):
            self.assertIn(reason, text)

    def test_governed_porter_is_retargeted_and_has_no_stock_rollback(self) -> None:
        apply_text = (PACK_ROOT / "scripts/apply_pr_pack.py").read_text(encoding="utf-8")
        self.assertIn("5707ea8cefd15cfd5b80a9c1503e3f03119f6adc", apply_text)
        self.assertIn("feat/kernel-pack-new-branch-default", apply_text)
        self.assertIn("def require_landing_base", apply_text)
        self.assertNotIn("_rollback_clean_base", apply_text)
        self.assertNotIn("0fbd477", apply_text)
        self.assertNotIn("def patch_controller_abort", apply_text)

    def test_governed_porter_skips_overlay_conftest_and_appends_thin_validator(self) -> None:
        apply = _load_apply_module()
        self.assertIn("conftest.py", apply.OVERLAY_SKIP)
        apply_text = (PACK_ROOT / "scripts/apply_pr_pack.py").read_text(encoding="utf-8")
        self.assertIn("def patch_makefile_additive", apply_text)
        self.assertIn("validate_thin_providers.py", apply_text)
        self.assertIn("def patch_conftest_additive", apply_text)
        self.assertIn("environment/program-execution/peer_execution", apply_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
