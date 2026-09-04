"""The Cursor result adapter never lets a document attest its own authority.

SA-F03: a verifier/reviewer document's ``subject_agent_id`` is judged against
the rendered assignment only; an assignment without a subject rejects the
document rather than adopting whatever the document names.
SA-F04: writable and forbidden paths come from the assignment only; an empty
writable grant admits no changed files, and the assignment's role may be
spelled in the autonomy vocabulary (``executor``) the host persists.
"""

from __future__ import annotations

import unittest
from typing import Any

from environment.agents.results.adapters import cursor_subagent

BASE_SHA = "a" * 40
bridge = cursor_subagent.result_bridge


def _document(
    role: str,
    kind: str,
    *,
    agent_id: str = "agent-1",
    files_changed: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    subject_agent_id: str | None = None,
) -> dict[str, Any]:
    assignment: dict[str, Any] = {
        "role": role,
        "objective": "o",
        "input_artifact_ids": [],
        "allowed_paths": allowed_paths if allowed_paths is not None else ["docs/**"],
        "forbidden_paths": [],
    }
    if subject_agent_id is not None:
        assignment["subject_agent_id"] = subject_agent_id
    return {
        "schema": bridge.RESULT_SCHEMA,
        "schema_version": "1.0.0",
        "result_id": "r1",
        "result_kind": kind,
        "status": "completed",
        "identity": {
            "campaign_id": "c1",
            "graph_id": "g1",
            "action_id": "a1",
            "agent_id": agent_id,
            "lease_id": "l1",
            "base_sha": BASE_SHA,
        },
        "assignment": assignment,
        "deliverable": {
            "summary": "s",
            "findings": [],
            "files_read": [],
            "files_changed": files_changed or [],
            "evidence": [],
            "commands_executed": [],
            "validations": [],
            "unresolved_items": [],
            "recommended_next_actions": [],
            "reuse_assessment": {"reusable_data_found": False, "confidence": 0.0},
            "visibility": "campaign_local",
        },
        "provenance": {"produced_at": "2026-09-02T00:00:00Z"},
    }


def _assignment(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "campaign_id": "c1",
        "graph_id": "g1",
        "action_id": "a1",
        "agent_id": "agent-1",
        "lease_id": "l1",
        "base_sha": BASE_SHA,
        "result_role": "recon",
        "allowed_paths": [],
        "forbidden_paths": [],
    }
    base.update(overrides)
    return base


class ReviewSubjectTests(unittest.TestCase):
    def test_reviewer_without_assignment_subject_is_rejected(self) -> None:
        document = _document(
            "verifier_reviewer", "VerificationReviewReport", subject_agent_id="anyone-the-doc-names"
        )
        with self.assertRaises(bridge.ResultValidationError) as caught:
            cursor_subagent.normalize(
                document, assignment=_assignment(result_role="verifier_reviewer")
            )
        self.assertIn("subject_agent_id", str(caught.exception))

    def test_reviewer_subject_mismatch_is_rejected(self) -> None:
        document = _document(
            "verifier_reviewer", "VerificationReviewReport", subject_agent_id="someone-else"
        )
        with self.assertRaises(bridge.AssignmentCorrelationError):
            cursor_subagent.normalize(
                document,
                assignment=_assignment(
                    result_role="verifier_reviewer", subject_agent_id="cursor-exec"
                ),
            )

    def test_reviewer_subject_from_assignment_is_accepted(self) -> None:
        document = _document(
            "verifier_reviewer", "VerificationReviewReport", subject_agent_id="cursor-exec"
        )
        normalized = cursor_subagent.normalize(
            document,
            assignment=_assignment(result_role="reviewer", subject_agent_id="cursor-exec"),
        )
        self.assertEqual(normalized["assignment"]["subject_agent_id"], "cursor-exec")


class WritableScopeTests(unittest.TestCase):
    def test_document_cannot_supply_its_own_writable_paths(self) -> None:
        document = _document(
            "pr_remediation",
            "PRRemediationReport",
            files_changed=["ops/secrets/x"],
            allowed_paths=["ops/**"],
        )
        with self.assertRaises(bridge.AssignmentCorrelationError) as caught:
            cursor_subagent.normalize(
                document, assignment=_assignment(result_role="pr_remediation")
            )
        self.assertIn("no writable paths", str(caught.exception))

    def test_assignment_paths_govern_changed_files(self) -> None:
        document = _document(
            "pr_remediation", "PRRemediationReport", files_changed=["ops/secrets/x"]
        )
        with self.assertRaises(bridge.AssignmentCorrelationError):
            cursor_subagent.normalize(
                document,
                assignment=_assignment(
                    result_role="remediator",
                    allowed_paths=["ops/**"],
                    forbidden_paths=["ops/secrets/**"],
                ),
            )
        normalized = cursor_subagent.normalize(
            _document("pr_remediation", "PRRemediationReport", files_changed=["ops/tools/x"]),
            assignment=_assignment(
                result_role="remediator",
                allowed_paths=["ops/**"],
                forbidden_paths=["ops/secrets/**"],
            ),
        )
        self.assertEqual(normalized["deliverable"]["files_changed"], ["ops/tools/x"])

    def test_autonomy_role_spelling_on_the_assignment_is_accepted(self) -> None:
        normalized = cursor_subagent.normalize(
            _document("test", "TestReport", files_changed=["docs/x.md"]),
            assignment=_assignment(result_role="executor", allowed_paths=["docs/**"]),
        )
        self.assertEqual(normalized["assignment"]["role"], "test")


if __name__ == "__main__":
    unittest.main()
