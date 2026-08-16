#!/usr/bin/env python3
"""Tests for the campaign brief IR compiler."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from compile_brief import (  # noqa: E402
    BriefError,
    brief_to_seed,
    compile_brief,
    slugify_filename,
    title_from_filename,
)

FIXTURE = SCRIPT_DIR / "fixtures" / "pe-memory-class.md"
ACTIVATE = {
    "campaign_id": "demo-activate-v1",
    "title": "Demo Activate",
    "objective": "Activate a proper PE campaign from the minimum file set.",
    "tasks": [{"title": "Lock current state", "objective": "Record baseline."}],
}


class CompileBriefTests(unittest.TestCase):
    def test_slug_and_title_from_pe_memory_filename(self) -> None:
        self.assertEqual(slugify_filename("PE- Memory.md"), "pe-memory")
        self.assertEqual(title_from_filename("PE- Memory.md"), "PE Memory")

    def test_pe_memory_class_fixture(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        seed = brief_to_seed(text, filename="PE- Memory.md")
        self.assertEqual(seed["campaign_id"], "pe-memory")
        self.assertEqual(seed["title"], "PE Memory")
        self.assertEqual(len(seed["tasks"]), 7)
        self.assertEqual(
            seed["tasks"][0]["title"],
            "Prove canonical memory and freeze legacy behavior",
        )
        self.assertIn("l9-graphiti-memory", seed["objective"])
        self.assertIn("Collapse every agent-facing memory lifecycle", seed["objective"])
        self.assertNotIn("older complete memory lifecycle", seed["objective"])
        self.assertEqual(seed["target"]["repository_id"], "Quantum-L9/Cursor-Governance")
        self.assertEqual(seed["problem_statement"], text)
        self.assertEqual(seed["owner"], "Igor Beylin")

    def test_collision_assigns_v2(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        seed = brief_to_seed(text, filename="PE- Memory.md", existing_ids={"pe-memory"})
        self.assertEqual(seed["campaign_id"], "pe-memory-v2")

    def test_architecture_only_fails_closed(self) -> None:
        with self.assertRaises(BriefError) as ctx:
            brief_to_seed(
                "Deep audit verdict\n\nNo numbered work items here.\n",
                filename="empty-audit.md",
            )
        self.assertIn("will not invent tasks", str(ctx.exception))

    def test_yaml_passthrough(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "seed.yaml"
            path.write_text(yaml.safe_dump(ACTIVATE), encoding="utf-8")
            out = Path(raw) / "out.yaml"
            result = compile_brief(path, output=out)
            self.assertEqual(result["seed"]["campaign_id"], "demo-activate-v1")
            self.assertEqual(len(result["seed"]["tasks"]), 1)

    def test_intent_v1_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "intent.yaml"
            path.write_text(
                yaml.safe_dump(
                    {
                        "schema": "program-execution.intent.v1",
                        "objective": "Make repo X achieve Y.",
                        "targets": ["Quantum-L9/l9-ci-core"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(BriefError) as ctx:
                compile_brief(path, output=Path(raw) / "out.yaml")
            self.assertIn("program-execution.intent.v1", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
