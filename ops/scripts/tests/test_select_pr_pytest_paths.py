"""Unit tests for local make pr-check pytest path selection (plan T3/T4)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from select_pr_pytest_paths import select_pr_pytest_paths  # noqa: E402

PE = "environment/program-execution/peer_execution/autonomy/tests"
GENERATED = "environment/agents/generated-data/tests"


def _registry(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "suites": [
                    {"id": "repo-root", "owned_paths": ["."]},
                    {"id": "claude-code-autonomy", "owned_paths": [PE]},
                    {"id": "generated-data", "owned_paths": [GENERATED]},
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


class SelectPrPytestPathsTests(unittest.TestCase):
    def test_autonomy_only_change_excludes_pe_and_generated_data(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = _registry(Path(raw) / "python-contract.json")
            selected = select_pr_pytest_paths(
                [
                    "ops/autonomy/merge_gate.py",
                    "tests/ops/autonomy/test_merge_gate.py",
                ],
                registry=registry,
            )
        self.assertIn("tests/ops/autonomy/test_merge_gate.py", selected)
        self.assertNotIn(".", selected)
        self.assertFalse(any(PE in item or item == PE for item in selected))
        self.assertFalse(any(GENERATED in item or item == GENERATED for item in selected))

    def test_never_emits_repo_root_dot(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = _registry(Path(raw) / "python-contract.json")
            selected = select_pr_pytest_paths(
                ["ops/scripts/run_pr_gate.sh", "ops/scripts/select_pr_pytest_paths.py"],
                registry=registry,
            )
        self.assertNotIn(".", selected)

    def test_non_dot_owned_path_still_selects_that_suite(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = _registry(Path(raw) / "python-contract.json")
            selected = select_pr_pytest_paths(
                [f"{PE}/test_worker.py"],
                registry=registry,
            )
        self.assertIn(f"{PE}/test_worker.py", selected)
        self.assertNotIn(".", selected)
        self.assertNotIn(GENERATED, selected)

    def test_unowned_impl_without_inferred_test_stays_in_its_tests_dir(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            registry = _registry(Path(raw) / "python-contract.json")
            selected = select_pr_pytest_paths(
                ["ops/scripts/no_such_helper_xyz.py"],
                registry=registry,
            )
        self.assertNotIn(".", selected)
        self.assertNotIn(PE, selected)
        self.assertNotIn(GENERATED, selected)
        self.assertTrue(selected)
        self.assertTrue(
            any(item.startswith("ops/scripts") for item in selected),
            selected,
        )


if __name__ == "__main__":
    unittest.main()
