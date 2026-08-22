from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_peer_task_pipeline.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_peer_task_pipeline_test", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunPeerTaskPipelineFrontDoorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load()

    def test_source_does_not_set_campaign_tunnel(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("L9_CAMPAIGN_TUNNEL", text)

    def test_main_refuses_without_tunnel(self) -> None:
        env = os.environ.copy()
        env.pop("L9_CAMPAIGN_TUNNEL", None)
        env.pop("L9_ALLOW_PEC_DIRECT", None)
        self._assert_cli_refused(env)

    def test_main_refuses_when_tunnel_already_exported(self) -> None:
        env = os.environ.copy()
        env.pop("L9_ALLOW_PEC_DIRECT", None)
        env["L9_CAMPAIGN_TUNNEL"] = "1"
        self._assert_cli_refused(env)

    def test_pec_helper_cannot_mutate(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            self.mod._pec(Path("/tmp/l9-unused-campaign-workspace"), "claim", "TASK-001")
        self.assertIn("not a live campaign front door", str(ctx.exception))
        self.assertIn("campaign INTENT=", str(ctx.exception))

    def _assert_cli_refused(self, env: dict[str, str]) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "TASK-001",
                    "--workspace",
                    str(workspace),
                    "--agent-ref",
                    "cursor",
                    "--surface",
                    "local",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertIn("not a live campaign front door", payload["error"])
        self.assertIn("campaign INTENT=", payload["error"])
        self.assertEqual(payload["error_code"], "PE_CAMPAIGN_INPUT_REJECTED")
        self.assertTrue(payload["nothing_executed"])
        self.assertFalse(payload["manual_stage_bypass_permitted"])


if __name__ == "__main__":
    unittest.main()
