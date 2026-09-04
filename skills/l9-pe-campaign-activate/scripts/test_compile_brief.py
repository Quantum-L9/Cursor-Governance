#!/usr/bin/env python3
"""Tests for the campaign brief IR compiler."""

from __future__ import annotations

import json
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

    def test_memo_release_files_become_task_paths(self) -> None:
        text = (
            "owner: Igor Beylin\n"
            "target_repo: Quantum-L9/Enrichment.Inference.Engine\n\n"
            "Final architectural judgment\n\n"
            "It is:\n"
            "a Wave-0 isolation campaign that restores RuleEngine inference.\n\n"
            "1. Release A — Deterministic RuleEngine inference\n\n"
            "Restore the PlasticOS inference_rules contract.\n\n"
            "Files:\n\n"
            "- `app/main.py` (T4)\n"
            "- `tests/test_inference_wiring.py` (create)\n"
            "- `domains/plasticos/spec.yaml` (read-only fixture)\n\n"
            "In `rule_loader.py`, keep load_rules(path).\n\n"
            "2. Release B — One Alembic lineage\n\n"
            "One migration tree.\n\n"
            "Files:\n\n"
            "- `alembic.ini`\n"
            "- `migrations/versions/001_initial_schema.py`\n"
            "- `alembic/versions/0002_perplexity_api_key_default.py` (orphan; do not import)\n"
        )
        seed = brief_to_seed(text, filename="eie-inference-isolation-v1.md")
        self.assertEqual(
            seed["tasks"][0]["paths"],
            ["app/main.py", "tests/test_inference_wiring.py"],
        )
        self.assertEqual(
            seed["tasks"][1]["paths"],
            ["alembic.ini", "migrations/versions/001_initial_schema.py"],
        )

    def test_companion_plan_document_files_become_task_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            companion = {
                "mode": "plan",
                "title": "Tip",
                "objective": "Resolve the tip",
                "todos": [
                    {
                        "id": "T1",
                        "task": "Add resolver",
                        "files": ["ops/scripts/resolve_stack_tip.py"],
                    }
                ],
            }
            (root / "companion.json").write_text(json.dumps(companion), encoding="utf-8")
            plan = root / "demo.plan.md"
            plan.write_text(
                "---\n"
                "name: Tip\n"
                "overview: Resolve the tip\n"
                "todos:\n"
                "  - id: T1\n"
                "    content: Add resolver\n"
                "---\n\n"
                "# PLAN: Tip\n\n"
                "> Projected from validated PLAN_DOCUMENT `companion.json`\n",
                encoding="utf-8",
            )
            result = compile_brief(plan, output=root / "out.yaml")
            self.assertEqual(
                result["seed"]["tasks"][0]["paths"],
                ["ops/scripts/resolve_stack_tip.py"],
            )


class NormalizedFrontmatterTests(unittest.TestCase):
    """A byte-order mark or CRLF endings must not hide a declared header."""

    PLAN = (
        "---\n"
        "name: Tip\n"
        "overview: Resolve the tip\n"
        "todos:\n"
        "  - id: T1\n"
        "    content: Add resolver\n"
        "---\n\n"
        "# PLAN: Tip\n"
    )

    def test_parse_frontmatter_sees_through_a_bom(self) -> None:
        from compile_brief import parse_frontmatter

        self.assertEqual(parse_frontmatter("﻿" + self.PLAN)["name"], "Tip")

    def test_parse_frontmatter_sees_through_crlf(self) -> None:
        from compile_brief import parse_frontmatter

        self.assertEqual(parse_frontmatter(self.PLAN.replace("\n", "\r\n"))["name"], "Tip")

    def test_bom_crlf_plan_compiles_as_a_plan_not_a_memo(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            plan = root / "demo.plan.md"
            plan.write_bytes(b"\xef\xbb\xbf" + self.PLAN.replace("\n", "\r\n").encode("utf-8"))
            result = compile_brief(plan, output=root / "out.yaml")
            self.assertEqual(result["seed"]["title"], "Tip")
            self.assertEqual(result["seed"]["tasks"][0]["title"], "Add resolver")


class CompanionPlanDocumentTests(unittest.TestCase):
    PLAN = (
        "---\n"
        "name: Tip\n"
        "overview: Resolve the tip\n"
        "todos:\n"
        "  - id: T1\n"
        "    content: Add resolver\n"
        "---\n\n"
        "# PLAN: Tip\n\n"
        "> Projected from validated PLAN_DOCUMENT `{cite}`\n"
    )
    COMPANION = {
        "mode": "plan",
        "title": "Tip",
        "objective": "Resolve the tip",
        "todos": [{"id": "T1", "task": "Add resolver", "files": ["ops/scripts/x.py"]}],
    }

    def test_a_cited_absolute_path_outside_the_plan_directory_is_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            foreign = elsewhere / "companion.json"
            foreign.write_text(json.dumps(self.COMPANION), encoding="utf-8")
            plans = root / "plans"
            plans.mkdir()
            plan = plans / "demo.plan.md"
            plan.write_text(self.PLAN.format(cite=foreign), encoding="utf-8")
            result = compile_brief(plan, output=root / "out.yaml")
            self.assertNotIn("paths", result["seed"]["tasks"][0])

    def test_a_cited_companion_beside_the_plan_is_still_read_by_basename(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "companion.json").write_text(json.dumps(self.COMPANION), encoding="utf-8")
            plan = root / "demo.plan.md"
            plan.write_text(
                self.PLAN.format(cite="/anywhere/else/companion.json"), encoding="utf-8"
            )
            result = compile_brief(plan, output=root / "out.yaml")
            self.assertEqual(result["seed"]["tasks"][0]["paths"], ["ops/scripts/x.py"])

    def test_a_cited_but_unparsable_companion_is_an_error_not_an_absence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "companion.json").write_text('{"todos": [', encoding="utf-8")
            plan = root / "demo.plan.md"
            plan.write_text(self.PLAN.format(cite="companion.json"), encoding="utf-8")
            with self.assertRaises(BriefError) as ctx:
                compile_brief(plan, output=root / "out.yaml")
            self.assertIn("companion.json", str(ctx.exception))
            self.assertIn("does not parse", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
