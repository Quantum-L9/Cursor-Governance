"""`autonomy/policy_loader.py` is generated; its JSON sources are the truth.

The module embeds the policies to avoid runtime filesystem I/O, which means a
JSON edit that is not re-embedded silently ships the old policy. This test makes
that drift a test failure instead of a production surprise.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from autonomy.policy_loader import load_example, load_golden_spec, load_policy

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "ops/scripts/regenerate_autonomy_policy_loader.py"


def _generator_module():
    specification = importlib.util.spec_from_file_location(
        "regenerate_autonomy_policy_loader",
        GENERATOR,
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class PolicyEmbeddingTests(unittest.TestCase):
    def test_embedded_module_matches_its_json_sources(self) -> None:
        module = _generator_module()
        rendered = module.render_module(ROOT)
        current = (ROOT / "autonomy/policy_loader.py").read_text(encoding="utf-8")
        self.assertEqual(
            rendered,
            current,
            msg="autonomy/policy_loader.py is stale; run "
            "python3 ops/scripts/regenerate_autonomy_policy_loader.py",
        )

    def test_check_mode_reports_clean_tree(self) -> None:
        module = _generator_module()
        self.assertEqual(module.main(["--check", "--root", str(ROOT)]), 0)

    def test_every_json_source_is_reachable_through_the_loader(self) -> None:
        module = _generator_module()
        for name in module.collect_policies(ROOT):
            self.assertIsNotNone(load_policy(name))
        for name in module.collect_examples(ROOT):
            self.assertIsNotNone(load_example(name))
        for name in module.collect_golden(ROOT):
            self.assertIsNotNone(load_golden_spec(name))

    def test_resource_policy_carries_the_swarm_ceilings(self) -> None:
        policy = load_policy("resource-classes")
        self.assertEqual(policy["schema_version"], "2.0.0")
        self.assertEqual(policy["global"]["provider_concurrency_ceiling"], 500)
        self.assertEqual(policy["global"]["reserved_control_slots"], 20)
        self.assertEqual(policy["global"]["fill_policy"], "saturate")
        for name, config in policy["classes"].items():
            self.assertIn("capacity", config, msg=f"{name} must declare a capacity")
            if config.get("mutation"):
                continue
            self.assertGreaterEqual(int(config["capacity"]), 1)
        for name in ("repository_mutation", "remediation_mutation"):
            self.assertEqual(
                policy["classes"][name]["conflict_policy"],
                "exclusive_claims_only",
            )

    def test_campaign_budgets_are_not_legacy_ceilings(self) -> None:
        budgets = load_example("w7-campaign.json")["budgets"]
        self.assertGreater(budgets["max_read_agents"], 4)
        self.assertGreater(budgets["max_mutation_agents"], 1)
        self.assertGreater(budgets["max_poll_agents"], 3)

    def test_role_maxima_allow_swarm_cardinality(self) -> None:
        roles = load_example("w7-deployment.json")["required_roles"]
        self.assertGreaterEqual(roles["recon"]["max"], 320)
        self.assertGreaterEqual(roles["executor"]["max"], 128)
        self.assertGreaterEqual(roles["verifier"]["max"], 160)
        for role in ("failure_classifier", "remediator"):
            self.assertIn(role, roles)


if __name__ == "__main__":
    unittest.main()
