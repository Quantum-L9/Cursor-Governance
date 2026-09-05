"""Host-native Task admission: remediator / recon / issue without PEC.

Program Execution stay fail-closed when a token is presented. These tests
cover the path that must not require a campaign, lease, or runtime.sqlite3.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_GOV_ROOT = Path(__file__).resolve().parents[4]
if str(_GOV_ROOT) not in sys.path:
    sys.path.insert(0, str(_GOV_ROOT))

from environment.agents.lifecycle import compose_start, receipts  # noqa: E402


class HostNativeLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        os.environ["L9_RUNTIME_ROOT"] = self.tmp.name
        self.addCleanup(os.environ.pop, "L9_RUNTIME_ROOT", None)
        os.environ.pop("L9_AUTONOMY_RUNTIME_DB", None)

    @staticmethod
    def _pre(tool_use_id: str, subagent_type: str | None) -> dict:
        tool_input: dict = {"description": "host-native child", "prompt": "no PE token"}
        if subagent_type is not None:
            tool_input["subagent_type"] = subagent_type
        return {
            "hook_event_name": "preToolUse",
            "tool_name": "Task",
            "tool_use_id": tool_use_id,
            "tool_input": tool_input,
        }

    @staticmethod
    def _start(tool_call_id: str, subagent_id: str) -> dict:
        return {
            "hook_event_name": "subagentStart",
            "subagent_id": subagent_id,
            "tool_call_id": tool_call_id,
            "parent_conversation_id": "conv-native",
            "model": "cursor-default",
            "is_parallel_worker": True,
        }

    def test_remediator_without_pe_is_allowed(self) -> None:
        pre = compose_start.compose_host_pre_tool_use(self._pre("tu-rem", "l9-pr-remediation"))
        self.assertEqual(pre["permission"], "allow", pre)
        self.assertEqual(pre["path"], "host-native")
        self.assertTrue(str(pre["lease_id"]).startswith("no-root-lease-"))
        start = compose_start.compose_host_subagent_start(self._start("tu-rem", "sub-rem"))
        self.assertEqual(start["permission"], "allow", start)
        correlation = receipts.load_host_correlation("sub-rem")
        self.assertIsNotNone(correlation)
        self.assertNotIn("runtime_database", correlation)
        self.assertEqual(correlation["tool_call_id"], "tu-rem")

    def test_recon_and_issue_types_are_allowed(self) -> None:
        for tool_use_id, subagent_type in (
            ("tu-recon", "l9-recon"),
            ("tu-issue", "l9-issue-remediation"),
            ("tu-gp", "generalPurpose"),
            ("tu-explore", "explore"),
        ):
            out = compose_start.compose_host_pre_tool_use(self._pre(tool_use_id, subagent_type))
            self.assertEqual(out["permission"], "allow", (subagent_type, out))

    def test_no_token_and_no_type_stays_denied(self) -> None:
        out = compose_start.compose_host_pre_tool_use(self._pre("tu-bare", None))
        self.assertEqual(out["permission"], "deny")
        self.assertIn("admission token", out["reason"])

    def test_token_without_runtime_database_stays_denied(self) -> None:
        payload = self._pre("tu-pe", "l9-pr-remediation")
        payload["tool_input"]["prompt"] = "L9_ADMISSION_TOKEN=admission-doesnotexist"
        out = compose_start.compose_host_pre_tool_use(payload)
        self.assertEqual(out["permission"], "deny")
        self.assertIn("runtime database", out["reason"])

    def test_leftover_pe_db_does_not_block_host_native(self) -> None:
        leftover = Path(self.tmp.name) / "leftover.sqlite3"
        leftover.write_bytes(b"")
        os.environ["L9_AUTONOMY_RUNTIME_DB"] = str(leftover)
        self.addCleanup(os.environ.pop, "L9_AUTONOMY_RUNTIME_DB", None)
        out = compose_start.compose_host_pre_tool_use(self._pre("tu-left", "l9-recon"))
        self.assertEqual(out["permission"], "allow", out)
        self.assertEqual(out["path"], "host-native")

    def test_uncorrelated_start_without_admission_stays_denied(self) -> None:
        out = compose_start.compose_host_subagent_start(self._start("tu-none", "sub-none"))
        self.assertEqual(out["permission"], "deny")

    def test_max_mutation_lanes_denies_third_remediator(self) -> None:
        first = compose_start.compose_host_pre_tool_use(self._pre("tu-m1", "l9-pr-remediation"))
        second = compose_start.compose_host_pre_tool_use(self._pre("tu-m2", "generalPurpose"))
        third = compose_start.compose_host_pre_tool_use(self._pre("tu-m3", "l9-issue-remediation"))
        self.assertEqual(first["permission"], "allow", first)
        self.assertEqual(second["permission"], "allow", second)
        self.assertEqual(third["permission"], "deny", third)
        self.assertIn("max_mutation_lanes", third["reason"])

    def test_max_parallel_denies_fifth_task(self) -> None:
        allowed = []
        for index, subagent_type in enumerate(
            ("l9-recon", "explore", "l9-pr-remediation", "l9-verifier-reviewer")
        ):
            out = compose_start.compose_host_pre_tool_use(
                self._pre(f"tu-p{index}", subagent_type)
            )
            self.assertEqual(out["permission"], "allow", (subagent_type, out))
            allowed.append(out)
        fifth = compose_start.compose_host_pre_tool_use(self._pre("tu-p4", "explore"))
        self.assertEqual(fifth["permission"], "deny", fifth)
        self.assertIn("max_parallel", fifth["reason"])


if __name__ == "__main__":
    unittest.main()
