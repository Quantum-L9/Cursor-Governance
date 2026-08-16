from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml
from helpers import make_blueprint, run_cli


class BootstrapAdmissionTest(unittest.TestCase):
    def test_draft_blueprint_is_rejected_without_flag(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = make_blueprint(temp / "blueprint")
            program_path = blueprint / "PROGRAM.yaml"
            program = yaml.safe_load(program_path.read_text(encoding="utf-8"))
            program["program"]["definition_status"] = "draft"
            program_path.write_text(
                yaml.safe_dump(program, sort_keys=False),
                encoding="utf-8",
            )
            result = run_cli(
                "bootstrap",
                "--workspace",
                str(temp / "runtime"),
                "--blueprint",
                str(blueprint),
                expect=2,
            )
            self.assertIn("admission-draft", result["error"])
            self.assertIn("make campaign", result["error"])

    def test_admission_draft_flag_refused_without_allow_env(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = make_blueprint(temp / "blueprint")
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("L9_ALLOW_ADMISSION_DRAFT", None)
                result = run_cli(
                    "bootstrap",
                    "--workspace",
                    str(temp / "runtime"),
                    "--blueprint",
                    str(blueprint),
                    "--admission-draft",
                    expect=2,
                )
            self.assertIn("not a live campaign path", result["error"])

    def test_admission_draft_does_not_mark_tasks_ready(self) -> None:
        with TemporaryDirectory() as raw:
            temp = Path(raw)
            blueprint = make_blueprint(temp / "blueprint")
            program_path = blueprint / "PROGRAM.yaml"
            program = yaml.safe_load(program_path.read_text(encoding="utf-8"))
            program["program"]["definition_status"] = "draft"
            program_path.write_text(
                yaml.safe_dump(program, sort_keys=False),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"L9_ALLOW_ADMISSION_DRAFT": "1"}):
                boot = run_cli(
                    "bootstrap",
                    "--workspace",
                    str(temp / "runtime"),
                    "--blueprint",
                    str(blueprint),
                    "--admission-draft",
                )
            self.assertEqual(boot["definition_status"], "draft")
            status = run_cli("status", "--workspace", str(temp / "runtime"))
            self.assertEqual(status["definition_status"], "draft")
            self.assertTrue(status["admission_draft"])
            self.assertEqual(status["campaign_status"]["runtime_status"], "operator_intake")
            self.assertEqual(status["campaign_status"]["source_status"], "operator_intake")
            nxt = run_cli("next", "--workspace", str(temp / "runtime"))
            self.assertEqual(nxt["ready"], [])
            self.assertTrue(nxt["admission_draft"])


if __name__ == "__main__":
    unittest.main()
