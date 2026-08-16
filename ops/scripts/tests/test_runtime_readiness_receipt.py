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
    def test_omitted_revision_is_unknown_not_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            home = Path(tmp) / "home"
            home.mkdir()
            env = {"L9_RUNTIME_ROOT": str(Path(tmp) / "l9")}
            self._with_env(env)
            rc = main(
                [
                    "--surface",
                    "cursor",
                    "--workspace",
                    str(workspace),
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
