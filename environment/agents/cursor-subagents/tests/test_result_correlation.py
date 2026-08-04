from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PATH = ROOT / "result_bridge.py"
FIXTURE_PATH = Path(__file__).with_name("test_result_bridge.py")


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matching_assignment(document: dict[str, Any]) -> dict[str, Any]:
    identity = document["identity"]
    assignment = document["assignment"]
    spec: dict[str, Any] = {
        "campaign_id": identity["campaign_id"],
        "graph_id": identity["graph_id"],
        "action_id": identity["action_id"],
        "agent_id": identity["agent_id"],
        "lease_id": identity["lease_id"],
        "base_sha": identity["base_sha"],
        "role": assignment["role"],
        "allowed_paths": list(assignment["allowed_paths"]),
        "forbidden_paths": list(assignment["forbidden_paths"]),
    }
    if "subject_agent_id" in assignment:
        spec["subject_agent_id"] = assignment["subject_agent_id"]
    return spec


class AssignmentCorrelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = _load("l9_cursor_subagent_result_bridge", BRIDGE_PATH)
        cls.fixture = _load("l9_cursor_subagent_result_fixture", FIXTURE_PATH)

    def valid(self, **kwargs: Any) -> dict[str, Any]:
        return self.fixture.valid_document(**kwargs)

    def test_matching_assignment_is_accepted(self) -> None:
        document = self.valid()
        normalized = self.bridge.validate_result_against_assignment(
            document, matching_assignment(document)
        )
        self.assertRegex(normalized["provenance"]["artifact_digest"], r"^[0-9a-f]{64}$")

    def test_wrong_campaign_is_rejected(self) -> None:
        document = self.valid()
        spec = matching_assignment(document)
        spec["campaign_id"] = "some-other-campaign"
        with self.assertRaises(self.bridge.AssignmentCorrelationError):
            self.bridge.validate_result_against_assignment(document, spec)

    def test_wrong_base_sha_is_rejected(self) -> None:
        document = self.valid()
        spec = matching_assignment(document)
        spec["base_sha"] = "b" * 40
        with self.assertRaises(self.bridge.AssignmentCorrelationError):
            self.bridge.validate_result_against_assignment(document, spec)

    def test_role_mismatch_is_rejected(self) -> None:
        document = self.valid()
        spec = matching_assignment(document)
        spec["role"] = "test"
        with self.assertRaises(self.bridge.AssignmentCorrelationError):
            self.bridge.validate_result_against_assignment(document, spec)

    def test_changed_file_outside_allowed_is_rejected(self) -> None:
        document = self.valid(role="test", result_kind="TestReport")
        document["identity"]["agent_id"] = "cursor-test-1"
        document["deliverable"]["files_changed"] = ["bounded/elsewhere.py"]
        with self.assertRaises(self.bridge.AssignmentCorrelationError):
            self.bridge.validate_result_against_assignment(document, matching_assignment(document))

    def test_forbidden_path_touched_is_rejected(self) -> None:
        document = self.valid(role="test", result_kind="TestReport")
        document["identity"]["agent_id"] = "cursor-test-1"
        document["deliverable"]["files_changed"] = ["environment/program-execution/core/pec.py"]
        spec = matching_assignment(document)
        spec["allowed_paths"] = ["environment/**"]
        spec["forbidden_paths"] = ["environment/program-execution/core/**"]
        with self.assertRaises(self.bridge.AssignmentCorrelationError):
            self.bridge.validate_result_against_assignment(document, spec)

    def test_changed_file_inside_allowed_is_accepted(self) -> None:
        document = self.valid(role="test", result_kind="TestReport")
        document["identity"]["agent_id"] = "cursor-test-1"
        document["deliverable"]["files_changed"] = [
            "environment/agents/cursor-subagents/tests/test_new.py"
        ]
        normalized = self.bridge.validate_result_against_assignment(
            document, matching_assignment(document)
        )
        self.assertEqual(normalized["assignment"]["role"], "test")

    def test_reviewer_subject_mismatch_is_rejected(self) -> None:
        document = self.valid(role="verifier_reviewer", result_kind="VerificationReviewReport")
        document["identity"]["agent_id"] = "cursor-reviewer-1"
        document["assignment"]["subject_agent_id"] = "cursor-executor-9"
        spec = matching_assignment(document)
        spec["subject_agent_id"] = "cursor-executor-1"
        with self.assertRaises(self.bridge.AssignmentCorrelationError):
            self.bridge.validate_result_against_assignment(document, spec)


if __name__ == "__main__":
    unittest.main()
