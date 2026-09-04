from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


class ThinProviderArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.repo_root = cls.root.parents[1]
        cls.registry = yaml.safe_load(
            (cls.root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(
                encoding="utf-8"
            )
        )
        cls.adapter_schema = json.loads(
            (
                cls.root
                / "conformance/schemas/execution-adapter-spec.schema.json"
            ).read_text(encoding="utf-8")
        )

    def test_bounded_execution_is_not_a_provider(self) -> None:
        adapter_ids = {item["adapter_id"] for item in self.registry["adapters"]}
        self.assertNotIn("claude-code-bounded-autonomy", adapter_ids)
        self.assertFalse(
            (self.root / "adapters/claude-code-bounded-autonomy").exists()
        )
        self.assertTrue((self.root / "peer_execution/autonomy").is_dir())

    def test_peer_provider_descriptors_are_identity_neutral(self) -> None:
        validator = Draft202012Validator(self.adapter_schema)
        for item in self.registry["adapters"]:
            descriptor = yaml.safe_load(
                (self.root / item["descriptor"]).read_text(encoding="utf-8")
            )
            self.assertEqual(list(validator.iter_errors(descriptor)), [])
            identity = descriptor.get("identity") or {}
            if identity.get("binding") == "peer_runtime_binding":
                self.assertNotIn("agent_ref", identity)

    def test_peer_bound_provider_modules_are_hook_only(self) -> None:
        forbidden_bases = {"BaseExecutionAdapter", "PeerExecutionAdapter", "DriverExecutionAdapter"}
        forbidden_modules = {
            "peer_execution.base",
            "peer_execution.core_receipts",
            "peer_execution.receipts",
            "peer_execution.runtime_store",
        }
        for item in self.registry["adapters"]:
            descriptor = yaml.safe_load(
                (self.root / item["descriptor"]).read_text(encoding="utf-8")
            )
            provider = self.root / item["provider_module"]
            if item.get("status") == "non_routable":
                tree = ast.parse(provider.read_text(encoding="utf-8"))
                self.assertFalse(
                    any(
                        isinstance(node, ast.Assign)
                        and any(
                            isinstance(target, ast.Name) and target.id == "PROVIDER_CLASS"
                            for target in node.targets
                        )
                        for node in ast.walk(tree)
                    ),
                    provider,
                )
                continue
            tree = ast.parse(provider.read_text(encoding="utf-8"))
            exported = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module or "", forbidden_modules)
                    if (descriptor.get("identity") or {}).get("binding") == "peer_runtime_binding":
                        self.assertNotIn(
                            node.module or "",
                            {
                                "peer_execution.context",
                                "peer_execution.permissions",
                                "peer_execution.approvals",
                                "peer_execution.terminal_receipts",
                                "peer_execution.driver_execution",
                            },
                        )
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        name = getattr(base, "id", getattr(base, "attr", ""))
                        self.assertNotIn(name, forbidden_bases)
                if isinstance(node, ast.Assign):
                    exported = exported or any(
                        isinstance(target, ast.Name) and target.id == "PROVIDER_CLASS"
                        for target in node.targets
                    )
            self.assertTrue(exported, provider)

    def test_topology_uses_provider_and_profile_refs(self) -> None:
        bindings_path = self.repo_root / "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
        bindings = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
        schema = json.loads(
            (
                self.repo_root
                / "environment/agents/schemas/peer-runtime-bindings.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(bindings)), [])
        for peer in bindings["peers"].values():
            for binding in (peer.get("execution") or {}).get("bindings") or []:
                self.assertIn("provider_ref", binding)
                self.assertIn("execution_profile_ref", binding)
                self.assertNotIn("adapter_id", binding)


if __name__ == "__main__":
    unittest.main()
