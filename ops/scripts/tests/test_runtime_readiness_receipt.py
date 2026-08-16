#!/usr/bin/env python3
"""Runtime readiness receipt: UNKNOWN never omitted; mixed SHAs fail closed."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from write_runtime_readiness_receipt import (  # noqa: E402
    NOT_READY,
    REVISION_MISMATCH,
    SCHEMA,
    UNKNOWN,
    build_receipt,
    main,
)


class RuntimeReadinessReceiptTests(unittest.TestCase):
    def _resolved_workspace(self, tmp: str) -> Path:
        """A workspace whose REQUIRED identity components all resolve."""
        workspace = Path(tmp) / "ws"
        (workspace / ".l9" / "memory").mkdir(parents=True)
        self._with_env({"L9_RUNTIME_ROOT": str(Path(tmp) / "l9")})
        return workspace

    def test_omitted_revision_is_unknown_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._resolved_workspace(tmp)
            rc = main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--session-id",
                    "sess",
                    "--omit-governance-revision",
                    "--runtime-script-revision",
                    "abc123",
                ]
            )
            self.assertEqual(rc, 0)
            from write_runtime_readiness_receipt import receipt_path

            data = json.loads(receipt_path(surface="cursor", workspace=workspace).read_text())
            self.assertEqual(data["schema"], SCHEMA)
            self.assertEqual(data["governance_revision"], UNKNOWN)
            self.assertIn("governance_revision", data)
            self.assertEqual(data["runtime_script_revision"], "abc123")
            self.assertEqual(data["overall_status"], "DEGRADED")

    def test_components_describe_the_installed_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._resolved_workspace(tmp)
            main(
                [
                    "--surface",
                    "claude-code",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--governance-revision",
                    "a" * 40,
                    "--runtime-script-revision",
                    "a" * 40,
                    "--session-id",
                    "sess",
                ]
            )
            from write_runtime_readiness_receipt import receipt_path

            data = json.loads(receipt_path(surface="claude-code", workspace=workspace).read_text())
            by_id = {row["id"]: row for row in data["components"]}
            # Every component the receipt claims to describe is observed, not
            # assumed: these exist in this repository and must report PRESENT.
            for component_id in (
                "governance.ssot",
                "environment.generated_llm_rules",
                "environment.skills",
                "adapter.claude-code",
                "session.identity",
                "memory.state_root",
            ):
                self.assertIn(component_id, by_id)
                self.assertEqual(by_id[component_id]["status"], "PRESENT", component_id)
            self.assertNotEqual(by_id["environment.generated_llm_rules"]["digest"], UNKNOWN)
            self.assertEqual(data["overall_status"], "READY")

    def test_unresolved_session_identity_is_not_ready(self) -> None:
        """An unattributable session is not a session PE may mutate from."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._resolved_workspace(tmp)
            main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--governance-revision",
                    "a" * 40,
                    "--runtime-script-revision",
                    "a" * 40,
                    "--session-id",
                    "",
                ]
            )
            from write_runtime_readiness_receipt import receipt_path

            data = json.loads(receipt_path(surface="cursor", workspace=workspace).read_text())
            self.assertEqual(data["overall_status"], NOT_READY)
            self.assertEqual(data["failure_code"], "IDENTITY_UNRESOLVED")
            self.assertIn("session.identity", data["unresolved_required"])

    def test_missing_memory_state_root_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            self._with_env({"L9_RUNTIME_ROOT": str(Path(tmp) / "l9")})
            main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--governance-revision",
                    "a" * 40,
                    "--runtime-script-revision",
                    "a" * 40,
                    "--session-id",
                    "sess",
                ]
            )
            from write_runtime_readiness_receipt import receipt_path

            data = json.loads(receipt_path(surface="cursor", workspace=workspace).read_text())
            self.assertEqual(data["overall_status"], NOT_READY)
            self.assertIn("memory.state_root", data["unresolved_required"])

    def _write(self, workspace: Path, surface: str = "cursor", **extra: str) -> dict:
        argv = [
            "--surface",
            surface,
            "--workspace",
            str(workspace),
            "--governance",
            str(REPO),
            "--governance-revision",
            "a" * 40,
            "--runtime-script-revision",
            "a" * 40,
        ]
        for key, value in extra.items():
            argv += [f"--{key.replace('_', '-')}", value]
        main(argv)
        from write_runtime_readiness_receipt import receipt_path

        return json.loads(receipt_path(surface=surface, workspace=workspace).read_text())

    def test_restamp_records_session_identity(self) -> None:
        """The bootstrap cannot know the session id; SessionStart stamps it."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._resolved_workspace(tmp)
            before = self._write(workspace, session_id="")
            self.assertEqual(before["overall_status"], NOT_READY)
            self.assertIn("session.identity", before["unresolved_required"])

            main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--session-id",
                    "resolved-session",
                    "--restamp-session",
                ]
            )
            from write_runtime_readiness_receipt import receipt_path

            after = json.loads(receipt_path(surface="cursor", workspace=workspace).read_text())
            self.assertEqual(after["session_id"], "resolved-session")
            self.assertEqual(after["overall_status"], "READY")
            # Revisions are carried over, not re-invented.
            self.assertEqual(after["governance_revision"], before["governance_revision"])

    def test_restamp_never_upgrades_a_degraded_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._resolved_workspace(tmp)
            self._write(workspace, session_id="", degraded_count="3")
            main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--session-id",
                    "resolved-session",
                    "--restamp-session",
                ]
            )
            from write_runtime_readiness_receipt import receipt_path

            after = json.loads(receipt_path(surface="cursor", workspace=workspace).read_text())
            self.assertEqual(after["session_id"], "resolved-session")
            self.assertEqual(after["degraded_count"], 3)
            self.assertEqual(after["overall_status"], "DEGRADED")

    def test_restamp_of_legacy_receipt_without_count_stays_degraded(self) -> None:
        """A pre-existing receipt with no degraded_count must not read as zero."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = self._resolved_workspace(tmp)
            self._write(workspace, session_id="sess", degraded_count="2")
            from write_runtime_readiness_receipt import receipt_path

            path = receipt_path(surface="cursor", workspace=workspace)
            legacy = json.loads(path.read_text())
            legacy.pop("degraded_count")
            path.write_text(json.dumps(legacy), encoding="utf-8")

            main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
                    "--governance",
                    str(REPO),
                    "--session-id",
                    "resolved-session",
                    "--restamp-session",
                ]
            )
            after = json.loads(path.read_text())
            self.assertEqual(after["overall_status"], "DEGRADED")

    def test_mixed_known_revisions_not_ready(self) -> None:
        receipt = build_receipt(
            surface="cursor",
            workspace=Path("/tmp/ws-a"),
            governance_revision="aaa111",
            runtime_script_revision="bbb222",
            session_id="sess",
            memory_state_root=UNKNOWN,
            graphiti_state_file=UNKNOWN,
            components=[],
            degraded_count=0,
        )
        self.assertEqual(receipt["overall_status"], NOT_READY)
        self.assertEqual(receipt["failure_code"], REVISION_MISMATCH)

    def test_bound_sha_mismatch_not_ready(self) -> None:
        receipt = build_receipt(
            surface="cursor",
            workspace=Path("/tmp/ws-b"),
            governance_revision="aaa111",
            runtime_script_revision="aaa111",
            session_id="sess",
            memory_state_root=UNKNOWN,
            graphiti_state_file=UNKNOWN,
            components=[],
            degraded_count=0,
            bound_sha="ccc333",
        )
        self.assertEqual(receipt["overall_status"], NOT_READY)
        self.assertEqual(receipt["failure_code"], REVISION_MISMATCH)

    def _with_env(self, env: dict[str, str]) -> None:
        import os

        for key, value in env.items():
            os.environ[key] = value
        self.addCleanup(lambda: [os.environ.pop(k, None) for k in env])


if __name__ == "__main__":
    unittest.main()
