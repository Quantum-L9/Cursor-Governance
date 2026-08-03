from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "ops" / "scripts" / "validate_org_policy.py"

SPEC = importlib.util.spec_from_file_location("validate_org_policy", VALIDATOR_PATH)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
# Register before exec_module so dataclasses can resolve the module for
# annotations evaluated under `from __future__ import annotations`.
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class PolicyValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = validator.load_yaml(ROOT / "ORG_INVARIANTS.yaml")
        cls.assertions = validator.load_yaml(ROOT / "governance" / "ASSERTION_TYPES.yaml")
        cls.registered = validator.assertion_versions(cls.assertions, [])

    def validate(self, policy: Any) -> list[Any]:
        findings: list[Any] = []
        validator.validate_policy(policy, self.registered, findings)
        return findings

    def codes(self, findings: list[Any]) -> set[str]:
        return {finding.code for finding in findings}

    def test_repository_policy_passes(self) -> None:
        findings = validator.run_validation(ROOT)
        self.assertEqual([], findings)

    def test_duplicate_invariant_id_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["invariants"].append(copy.deepcopy(policy["invariants"][0]))
        findings = self.validate(policy)
        self.assertIn("INVARIANT_ID_DUPLICATE", self.codes(findings))

    def test_unknown_assertion_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        target = policy["invariants"][0]
        target["assertion"] = {
            "type": "unregistered_assertion",
            "version": 1,
        }
        findings = self.validate(policy)
        self.assertIn("ASSERTION_REFERENCE_UNRESOLVED", self.codes(findings))

    def test_unsupported_assertion_version_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        target = policy["invariants"][0]
        existing = target.get("assertion")
        if not isinstance(existing, dict):
            existing = {
                "type": "repository_owner",
                "version": 1,
            }
            target["assertion"] = existing
        existing["version"] = 999
        findings = self.validate(policy)
        self.assertIn("ASSERTION_REFERENCE_UNRESOLVED", self.codes(findings))

    def test_invalid_policy_state_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["invariants"][0]["policy_state"] = "finished"
        findings = self.validate(policy)
        self.assertIn("INVARIANT_POLICY_STATE_INVALID", self.codes(findings))

    def test_invalid_enforcement_state_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["invariants"][0]["assurance"] = {"effective_enforcement_state": "magical"}
        findings = self.validate(policy)
        self.assertIn("ASSURANCE_ENFORCEMENT_STATE_INVALID", self.codes(findings))

    def test_critical_invariant_requires_violation(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["invariants"][0]["severity"] = "critical"
        policy["invariants"][0].pop("violation", None)
        findings = self.validate(policy)
        self.assertIn("CRITICAL_VIOLATION_MISSING", self.codes(findings))

    def test_blocking_control_without_evidence_fails(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["control_registry"] = [
            {
                "id": "L9-CTRL-999",
                "title": "Invalid blocking claim",
                "implementation_state": "implemented",
                "enforcement_state": "blocking",
                "covers": [policy["invariants"][0]["id"]],
                "evidence": [],
            }
        ]
        findings = self.validate(policy)
        codes = self.codes(findings)
        self.assertIn("FALSE_BLOCKING_CLAIM", codes)
        self.assertIn("FALSE_BLOCKING_IMPLEMENTATION_STATE", codes)

    def test_duplicate_yaml_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.yaml"
            path.write_text("a: 1\na: 2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validator.load_yaml(path)

    def test_release_schema_requires_full_commit(self) -> None:
        schema = validator.load_yaml(ROOT / "releases" / "POLICY_RELEASE.schema.yaml")
        findings: list[Any] = []
        validator.validate_release_schema(schema, findings)
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
