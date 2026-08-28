"""Unit tests for local make pr-check pytest path selection (plan T3/T4)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import uuid
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


class NonPythonChangeTests(unittest.TestCase):
    """A shell or config change is not an untested change.

    `select_pr_pytest_paths` filtered the changed set to `.py`, so editing
    `ops/scripts/run_pr_gate.sh` selected nothing and went straight to CI — where
    `ops/scripts/tests/test_bootstrap_invariants.py` (which keys SWALLOW_BASELINE
    on that exact path) failed. Tests that name a file are the tests that assert
    about it.
    """

    CHANGED_SHELL = "ops/scripts/run_pr_gate.sh"

    def test_shell_change_selects_the_tests_that_name_it(self) -> None:
        selected = select_pr_pytest_paths([self.CHANGED_SHELL])
        self.assertIn("ops/scripts/tests/test_bootstrap_invariants.py", selected)

    def test_shell_change_selection_matches_a_name_scan(self) -> None:
        """The machine must find what a careful reader would find by hand."""

        repo_root = Path(__file__).resolve().parents[3]
        expected = {
            path.relative_to(repo_root).as_posix()
            for path in repo_root.rglob("test_*.py")
            if ".venv" not in path.parts
            and self.CHANGED_SHELL in path.read_text(encoding="utf-8", errors="ignore")
        }
        selected = set(select_pr_pytest_paths([self.CHANGED_SHELL]))
        self.assertTrue(expected)
        self.assertTrue(
            expected <= selected,
            f"missed tests that name the file: {sorted(expected - selected)}",
        )

    def test_still_never_emits_repo_root_dot(self) -> None:
        selected = select_pr_pytest_paths([self.CHANGED_SHELL, "Makefile"])
        self.assertNotIn(".", selected)

    def test_unreferenced_non_python_file_selects_nothing(self) -> None:
        """No invented targets when nothing names the file.

        The path is assembled at run time on purpose: writing the literal here
        would make this very module name it, and the scan would then correctly
        select this file — a self-referential pass that proves nothing.
        """

        unreferenced = "/".join(["docs", "plans", uuid.uuid4().hex + ".plan.md"])
        selected = select_pr_pytest_paths([unreferenced])
        self.assertEqual([], selected)

    def test_mixed_change_set_keeps_both_kinds(self) -> None:
        selected = select_pr_pytest_paths([self.CHANGED_SHELL, "ops/scripts/pr_gate_failure.py"])
        self.assertIn("ops/scripts/tests/test_bootstrap_invariants.py", selected)
        self.assertIn("tests/ops/scripts/test_pr_gate_failure.py", selected)
