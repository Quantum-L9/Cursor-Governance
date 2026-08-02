from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from autonomy.cli import command_init, command_plan


class CliTests(unittest.TestCase):
    def test_init_and_plan(self) -> None:
        campaign = {
            "campaign_id": "cli-campaign",
            "objective": "CLI test",
            "actions": [
                {
                    "action_id": "a",
                    "objective": "A",
                    "depends_on": [],
                    "resources": [{"key": "service:test", "mode": "read"}],
                    "mutation": False,
                }
            ],
            "runtime": {},
            "completed_operations": [],
            "checkpoints": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            campaign_path = root / "campaign.json"
            campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    command_init(
                        Namespace(campaign=str(campaign_path), state_root=str(root / "state"))
                    ),
                    0,
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["campaign_id"], "cli-campaign")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    command_plan(
                        Namespace(
                            campaign_id="cli-campaign",
                            state_root=str(root / "state"),
                            total_lanes=4,
                            mutation_lanes=2,
                        )
                    ),
                    0,
                )
            plan = json.loads(output.getvalue())
            self.assertEqual(plan["selected"], ["a"])


if __name__ == "__main__":
    unittest.main()
