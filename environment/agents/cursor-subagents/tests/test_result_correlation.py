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

    # ------------------------------------------------------------ SA-F04 grammar

    def _mutating(self, files_changed: list[str]) -> dict[str, Any]:
        document = self.valid(role="test", result_kind="TestReport")
        document["identity"]["agent_id"] = "cursor-test-1"
        document["deliverable"]["files_changed"] = files_changed
        return document

    def test_path_grammar_is_the_capability_gateway_grammar(self) -> None:
        gateway = self.bridge._capability_gateway()
        cases = (
            ("src/*", "src/a/b.py"),
            ("autonomy/**", "autonomy/x/y.py"),
            ("docs/", "docs/a.md"),
            ("docs", "docs/a.md"),
            ("*.py", "a/b.py"),
            ("environment/agents/*/tests/*", "environment/agents/x/tests/t.py"),
        )
        for pattern, path in cases:
            self.assertEqual(
                self.bridge._path_matches_any(path, [pattern]),
                gateway.path_matches(pattern, path),
                (pattern, path),
            )
        # The audit's divergence case: `src/*` crosses `/` under the gateway.
        document = self._mutating(["src/a/b.py"])
        spec = matching_assignment(document)
        spec["allowed_paths"] = ["src/*"]
        normalized = self.bridge.validate_result_against_assignment(document, spec)
        self.assertEqual(normalized["deliverable"]["files_changed"], ["src/a/b.py"])

    def test_empty_writable_grant_admits_no_changed_files(self) -> None:
        document = self._mutating(["environment/agents/cursor-subagents/tests/test_new.py"])
        spec = matching_assignment(document)
        spec["allowed_paths"] = []
        with self.assertRaises(self.bridge.AssignmentCorrelationError) as caught:
            self.bridge.validate_result_against_assignment(document, spec)
        self.assertIn("no writable paths", str(caught.exception))
        # A read-only-shaped mutating result (nothing changed) is still fine.
        document = self._mutating([])
        spec = matching_assignment(document)
        spec["allowed_paths"] = []
        self.bridge.validate_result_against_assignment(document, spec)

    def test_action_scope_narrows_campaign_scope(self) -> None:
        document = self._mutating(["environment/program-execution/x.py"])
        spec = matching_assignment(document)
        spec["allowed_paths"] = ["environment/**"]
        spec["action_allowed_paths"] = ["environment/agents/**"]
        with self.assertRaises(self.bridge.AssignmentCorrelationError) as caught:
            self.bridge.validate_result_against_assignment(document, spec)
        self.assertIn("action", str(caught.exception))
        document = self._mutating(["environment/agents/x.py"])
        spec = matching_assignment(document)
        spec["allowed_paths"] = ["environment/**"]
        spec["action_allowed_paths"] = ["environment/agents/**"]
        self.bridge.validate_result_against_assignment(document, spec)

    def test_traversal_or_absolute_changed_path_is_rejected(self) -> None:
        for path in ("../outside.py", "/etc/passwd", "environment/../ops/secrets/x"):
            document = self._mutating([path])
            spec = matching_assignment(document)
            spec["allowed_paths"] = ["**"]
            with self.assertRaises(self.bridge.AssignmentCorrelationError, msg=path):
                self.bridge.validate_result_against_assignment(document, spec)

    # ------------------------------------------------------------ SA-F01 vocabulary

    def test_canonical_cursor_role_maps_autonomy_roles(self) -> None:
        expected = {
            "recon": "recon",
            "remediator": "pr_remediation",
            "executor": "test",
            "evidence_writer": "documentation",
            "reviewer": "verifier_reviewer",
            "verifier": "verifier_reviewer",
        }
        for autonomy_role, cursor_role in expected.items():
            self.assertEqual(self.bridge.canonical_cursor_role(autonomy_role), cursor_role)
            self.assertEqual(self.bridge.AUTONOMY_ROLE_TO_CURSOR_ROLE[autonomy_role], cursor_role)
        for cursor_role in self.bridge.ROLE_TO_RESULT_KIND:
            self.assertEqual(self.bridge.canonical_cursor_role(cursor_role), cursor_role)

    # ------------------------------------------------------------ SA-F08 promotion

    def test_unfinished_document_findings_are_not_promotable(self) -> None:
        for status in ("partial", "blocked", "failed"):
            document = self.valid()
            document["status"] = status
            document["deliverable"]["findings"][0]["proposed_routes"] = [
                "memory",
                "contracts",
                "evidence",
            ]
            packet = self.bridge.to_generated_data_packet(document, repository="local/test")
            self.assertEqual(packet["primary_result"]["completion_status"], status)
            self.assertEqual(packet["generated_data_units"][0]["proposed_routes"], ["evidence"])
            document["deliverable"]["findings"][0]["proposed_routes"] = ["memory"]
            packet = self.bridge.to_generated_data_packet(document, repository="local/test")
            self.assertEqual(packet["generated_data_units"][0]["proposed_routes"], ["evidence"])
        completed = self.valid()
        completed["deliverable"]["findings"][0]["proposed_routes"] = ["memory", "contracts"]
        packet = self.bridge.to_generated_data_packet(completed, repository="local/test")
        self.assertEqual(
            packet["generated_data_units"][0]["proposed_routes"], ["memory", "contracts"]
        )


if __name__ == "__main__":
    unittest.main()
