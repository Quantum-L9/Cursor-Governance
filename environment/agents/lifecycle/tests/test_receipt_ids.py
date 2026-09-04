"""Lifecycle receipt paths never trust a supplied identifier (SA-F09).

An assignment_id or subagent_id is chosen by a host or a subagent. Building a
receipt path from it unsanitized let ``../../escape`` write above the agents
runtime root; every path helper now refuses anything outside the one receipt
identifier grammar shared with the result receipts.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from environment.agents.lifecycle import compose_start, compose_stop, receipts

TRAVERSALS = ("../../escape", "../evil", "a/b", "x y", "", "..")


class ReceiptIdentifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name
        self.addCleanup(os.environ.pop, "L9_RUNTIME_ROOT", None)

    def _escaped_files(self) -> list[str]:
        root = Path(self.tmp.name)
        return sorted(str(path) for path in root.rglob("*.json") if "escape" in path.name)

    def test_every_path_helper_refuses_unsafe_identifiers(self) -> None:
        helpers = (
            receipts.assignment_path,
            receipts.dispatch_path,
            receipts.return_path,
            receipts.raw_result_path,
            receipts.host_correlation_path,
            receipts.host_stop_path,
        )
        for helper in helpers:
            for value in TRAVERSALS:
                with self.assertRaises(ValueError, msg=f"{helper.__name__}({value!r})"):
                    helper(value)
        with self.assertRaises(ValueError):
            receipts.write_pr_remediation_assignment({"assignment_id": "../../escape"})
        with self.assertRaises(ValueError):
            receipts.write_host_stop("../../escape", {"status": "COMPLETED"})

    def test_safe_identifiers_stay_inside_the_receipt_root(self) -> None:
        root = Path(self.tmp.name).resolve()
        for value in ("admission-abc123", "sub-100", "task:1.2_3"):
            for helper in (receipts.assignment_path, receipts.host_correlation_path):
                path = helper(value)
                self.assertTrue(str(path.resolve()).startswith(str(root)), path)

    def test_synthetic_start_denies_a_traversal_assignment_id(self) -> None:
        out = compose_start.compose_subagent_start(
            {
                "assignment_id": "../../escape",
                "subagent_role": "recon",
                "skip_deployment_check": True,
                "require_lease": False,
            }
        )
        self.assertEqual(out["permission"], "deny", out)
        self.assertIn("assignment_id", out["reason"])
        self.assertEqual(self._escaped_files(), [])

    def test_host_start_denies_a_traversal_subagent_id(self) -> None:
        out = compose_start.compose_host_subagent_start(
            {"subagent_id": "../../escape", "tool_call_id": "tu-1"}
        )
        self.assertEqual(out["permission"], "deny", out)
        self.assertIn("subagent_id", out["reason"])
        self.assertEqual(self._escaped_files(), [])

    def test_stop_quarantines_a_traversal_identifier(self) -> None:
        for payload in (
            {"subagent_id": "../../escape", "status": "COMPLETED", "output": "done"},
            {"assignment_id": "../../escape", "output": "done"},
        ):
            out = compose_stop.compose_subagent_stop(payload)
            self.assertEqual(out["status"], "QUARANTINED", out)
        self.assertEqual(self._escaped_files(), [])


if __name__ == "__main__":
    unittest.main()
