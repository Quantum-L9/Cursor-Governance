#!/usr/bin/env python3
"""Regression guards for the workflow action-pin validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "validate_workflow_action_pins.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("validate_workflow_action_pins", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class WorkflowPinTests(unittest.TestCase):
    def _run(self, mod, uses_line: str) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wd = root / ".github" / "workflows"
            wd.mkdir(parents=True)
            (wd / "wf.yml").write_text(
                f"jobs:\n  x:\n    steps:\n      - uses: {uses_line}\n", encoding="utf-8"
            )
            orig_root, orig_dir = mod.ROOT, mod.WORKFLOW_DIR
            try:
                mod.ROOT, mod.WORKFLOW_DIR = root, wd
                return mod.main()
            finally:
                mod.ROOT, mod.WORKFLOW_DIR = orig_root, orig_dir

    def test_real_repo_workflows_are_pinned(self) -> None:
        # The shipped workflows must satisfy the pin policy.
        self.assertEqual(_load_mod().main(), 0)

    def test_floating_tag_fails(self) -> None:
        self.assertEqual(self._run(_load_mod(), "actions/checkout@v4"), 1)

    def test_branch_ref_fails(self) -> None:
        self.assertEqual(self._run(_load_mod(), "actions/checkout@main"), 1)

    def test_full_sha_passes(self) -> None:
        self.assertEqual(
            self._run(_load_mod(), "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"), 0
        )

    def test_first_party_org_tag_allowed(self) -> None:
        self.assertEqual(
            self._run(_load_mod(), "Quantum-L9/.github/.github/workflows/governance-pr.yml@v1"), 0
        )

    def test_local_action_exempt(self) -> None:
        self.assertEqual(self._run(_load_mod(), "./.github/actions/local"), 0)

    def test_malformed_uses_fails_closed(self) -> None:
        self.assertEqual(self._run(_load_mod(), "someorg/foo"), 1)


if __name__ == "__main__":
    unittest.main()
