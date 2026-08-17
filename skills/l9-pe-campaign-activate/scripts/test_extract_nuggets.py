#!/usr/bin/env python3
"""Tests for primed nugget extraction."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from extract_nuggets import extract_nuggets, project_plan_window  # noqa: E402


class ExtractNuggetsTests(unittest.TestCase):
    def test_writes_primed_nuggets_and_assigns_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primed = Path(raw) / "primed"
            stack = primed / "stack-proof.json"
            stack.parent.mkdir(parents=True)
            stack.write_text("{}\n", encoding="utf-8")
            seed = {
                "campaign_id": "demo-activate-v1",
                "plan_status": "Ready",
                "tasks": [
                    {
                        "id": "TASK-001",
                        "title": "Lock",
                        "actions": ["inspect"],
                        "consumers": ["pec"],
                        "entrypoints": ["make campaign"],
                        "validation": [{"command": "true"}],
                    }
                ],
            }
            result = extract_nuggets(seed, primed, stack)
            payload = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "l9.program-execution.nuggets.v1")
            self.assertEqual(result["seed"]["tasks"][0]["nugget_id"], "NUG-001")
            self.assertTrue(
                any(item.get("cites") == "stack-proof.json" for item in payload["nuggets"])
            )
            self.assertTrue(result["stack_cited"])

    def test_hollow_seed_stays_partial(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            primed = Path(raw) / "primed"
            result = project_plan_window(
                {
                    "campaign_id": "demo-activate-v1",
                    "tasks": [{"title": "Hollow"}],
                },
                primed,
                None,
            )
            self.assertEqual(result["plan_status"], "Partial")
            self.assertTrue(Path(result["path"]).is_file())
            self.assertTrue(Path(result["intent_path"]).is_file())


if __name__ == "__main__":
    raise SystemExit(unittest.main())
