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

from select_pr_pytest_paths import (  # noqa: E402
    root_collect_ignores,
    select_pr_pytest_paths,
)

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


class UncollectableTargetTests(unittest.TestCase):
    """A target the root conftest excludes is not a repo-root pytest target.

    Handing such a path to the repo-root suite as an explicit argument overrides
    `collect_ignore` and fails on import, which is what blocked `make pr` on any
    change under `peer_execution/`. These use the real registry and conftest
    because the behavior is about this repository's actual topology.
    """

    PEER_CORE = "environment/program-execution/peer_execution"

    def test_root_collect_ignores_names_the_peer_execution_tree(self) -> None:
        self.assertIn(self.PEER_CORE, root_collect_ignores())

    def test_peer_core_impl_change_emits_no_repo_root_target(self) -> None:
        selected = select_pr_pytest_paths([f"{self.PEER_CORE}/base.py"])
        self.assertFalse(
            [item for item in selected if item.startswith(self.PEER_CORE)],
            msg=f"emitted an uncollectable peer_execution target: {selected}",
        )

    def test_owned_autonomy_suite_is_still_routed(self) -> None:
        """The drop must not swallow a nested path a non-root suite owns."""
        selected = select_pr_pytest_paths([f"{self.PEER_CORE}/autonomy/scheduler.py"])
        self.assertIn(f"{self.PEER_CORE}/autonomy/tests/test_scheduler.py", selected)

    def test_root_conftest_change_is_not_a_collect_target(self) -> None:
        selected = select_pr_pytest_paths(["conftest.py"])
        self.assertNotIn("conftest.py", selected)


if __name__ == "__main__":
    unittest.main()
