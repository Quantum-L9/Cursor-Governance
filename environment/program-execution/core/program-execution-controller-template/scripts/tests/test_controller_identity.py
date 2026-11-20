from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from helpers import SCRIPTS, bootstrap_repo, run_cli

sys.path.insert(0, str(SCRIPTS))
from pec.common import ControllerError
from pec.controller import _controller_identity


class ControllerIdentityTest(unittest.TestCase):
    """A runtime hosted by the sealed template still names its Controller."""

    def test_template_hosted_runtime_is_named_for_its_program(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw))
            config = json.loads((workspace / "config" / "controller.json").read_text())
            lock = json.loads((workspace / "runtime" / "program-lock.json").read_text())
            self.assertNotIn("{{", config["controller_id"])
            self.assertEqual(config["controller_id"], f"controller-{lock['program']['id']}")
            self.assertRegex(config["controller_id"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def test_handoff_receipt_carries_the_concrete_identity(self) -> None:
        with TemporaryDirectory() as raw:
            _, _, workspace = bootstrap_repo(Path(raw))
            handoff = run_cli(
                "export-handoff",
                "--workspace",
                str(workspace),
                "--actor",
                "operator",
                "--output",
                str(workspace / "receipts" / "handoffs" / "handoff.json"),
            )
            config = json.loads((workspace / "config" / "controller.json").read_text())
            self.assertEqual(handoff["controller_id"], config["controller_id"])
            self.assertNotIn("{{", handoff["controller_id"])

    def test_an_instantiated_controller_keeps_its_declared_id(self) -> None:
        self.assertEqual(_controller_identity({"id": "pec-prod-01"}, "any-program"), "pec-prod-01")

    def test_a_program_id_is_normalized_into_the_id_grammar(self) -> None:
        self.assertEqual(
            _controller_identity({"id": "{{CONTROLLER_ID}}"}, "Demo_Program v2"),
            "controller-demo-program-v2",
        )

    def test_no_identity_is_invented_without_a_program(self) -> None:
        with self.assertRaises(ControllerError):
            _controller_identity({"id": "{{CONTROLLER_ID}}"}, "")


if __name__ == "__main__":
    unittest.main()
