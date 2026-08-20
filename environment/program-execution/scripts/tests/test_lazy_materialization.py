"""Arming renders the frontier; the tail of the program materializes on demand.

Rendering a source contract costs two `pec` subprocesses, and arming used to pay
that for every locked task -- so a 35-task campaign spent most of preparation
describing work that could not start yet. The frontier is the part that can.

The safety property is the one worth guarding: a task is never claimed without a
registered source contract, whether it was armed up front or deferred. These
tests pin both halves -- what arming skips, and where the skipped work reappears.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

TESTS_DIR = Path(__file__).resolve().parent
PE_ROOT = TESTS_DIR.parents[1]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_run_campaign import _load  # type: ignore[import-not-found]  # noqa: E402


def _chain(length: int) -> list[dict[str, Any]]:
    """A strictly sequential program: every task waits on the one before it."""
    return [
        {"id": f"TASK-{index:03d}", "depends_on": [f"TASK-{index - 1:03d}"] if index > 1 else []}
        for index in range(1, length + 1)
    ]


def _fan_out(width: int) -> list[dict[str, Any]]:
    """One root task that `width` independent tasks all wait on."""
    tasks: list[dict[str, Any]] = [{"id": "TASK-001", "depends_on": []}]
    tasks += [
        {"id": f"TASK-{index:03d}", "depends_on": ["TASK-001"]} for index in range(2, width + 2)
    ]
    return tasks


class DependencyDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_lazy_depth", SCRIPT)

    def test_a_chain_deepens_by_one_per_link(self) -> None:
        depth = self.mod.dependency_depth(_chain(4))
        self.assertEqual(depth, {"TASK-001": 0, "TASK-002": 1, "TASK-003": 2, "TASK-004": 3})

    def test_independent_tasks_are_all_startable(self) -> None:
        depth = self.mod.dependency_depth([{"id": "TASK-001"}, {"id": "TASK-002"}])
        self.assertEqual(set(depth.values()), {0})

    def test_depth_follows_the_longest_path_not_the_shortest(self) -> None:
        tasks = [
            {"id": "TASK-001", "depends_on": []},
            {"id": "TASK-002", "depends_on": ["TASK-001"]},
            {"id": "TASK-003", "depends_on": ["TASK-001", "TASK-002"]},
        ]
        self.assertEqual(self.mod.dependency_depth(tasks)["TASK-003"], 2)

    def test_the_frozen_lock_spelling_of_the_edge_is_read_too(self) -> None:
        """`pec bootstrap` renames `depends_on` to `dependencies`."""
        tasks = [
            {"id": "TASK-001", "dependencies": []},
            {"id": "TASK-002", "dependencies": ["TASK-001"]},
        ]
        self.assertEqual(self.mod.dependency_depth(tasks)["TASK-002"], 1)

    def test_a_dependency_on_nothing_known_does_not_block(self) -> None:
        """An out-of-program reference is not this function's to adjudicate."""
        tasks = [{"id": "TASK-001", "depends_on": ["SOMETHING-ELSE"]}]
        self.assertEqual(self.mod.dependency_depth(tasks)["TASK-001"], 0)

    def test_a_cycle_terminates_instead_of_recursing(self) -> None:
        tasks = [
            {"id": "TASK-001", "depends_on": ["TASK-002"]},
            {"id": "TASK-002", "depends_on": ["TASK-001"]},
        ]
        self.assertEqual(set(self.mod.dependency_depth(tasks)), {"TASK-001", "TASK-002"})


class FrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_lazy_frontier", SCRIPT)

    def test_a_long_chain_arms_only_the_first_two_links(self) -> None:
        frontier = self.mod.materialization_frontier(_chain(35))
        self.assertEqual(frontier, ["TASK-001", "TASK-002"])

    def test_lookahead_covers_the_whole_next_wave_not_one_task(self) -> None:
        """Width is not deferred -- everything runnable next is armed."""
        frontier = self.mod.materialization_frontier(_fan_out(30))
        self.assertEqual(len(frontier), 31)

    def test_the_frontier_advances_as_tasks_complete(self) -> None:
        tasks = _chain(35)
        self.assertEqual(
            self.mod.materialization_frontier(tasks, completed=["TASK-001"]),
            ["TASK-002", "TASK-003"],
        )
        self.assertEqual(
            self.mod.materialization_frontier(tasks, completed=["TASK-001", "TASK-002"]),
            ["TASK-003", "TASK-004"],
        )

    def test_a_finished_program_has_nothing_left_to_arm(self) -> None:
        tasks = _chain(3)
        done = [str(task["id"]) for task in tasks]
        self.assertEqual(self.mod.materialization_frontier(tasks, completed=done), [])

    def test_a_small_program_is_armed_whole(self) -> None:
        """Deferral is a saving on large programs, never a cost on small ones."""
        self.assertEqual(len(self.mod.materialization_frontier(_chain(2))), 2)

    def test_no_lookahead_arms_only_what_can_start(self) -> None:
        frontier = self.mod.materialization_frontier(_chain(5), lookahead=0)
        self.assertEqual(frontier, ["TASK-001"])


class OnDemandMaterializationTests(unittest.TestCase):
    """Where the work arming skipped reappears."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_lazy_demand", SCRIPT)

    def _workspace(self, tmp: Path, *, registered: str | None = None) -> Path:
        (tmp / "contracts" / "source").mkdir(parents=True)
        (tmp / "runtime").mkdir(parents=True)
        if registered:
            (tmp / "contracts" / "source" / f"{registered}.json").write_text("{}", encoding="utf-8")
        return tmp

    def test_a_deferred_task_is_registered_when_it_is_needed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = self._workspace(Path(raw))
            with unittest.mock.patch.object(self.mod, "register_task_contract") as register:
                self.mod.ensure_task_contract(workspace, "TASK-009")
            register.assert_called_once_with(workspace, "TASK-009")

    def test_an_already_armed_task_is_not_registered_twice(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            workspace = self._workspace(Path(raw), registered="TASK-001")
            with unittest.mock.patch.object(self.mod, "register_task_contract") as register:
                self.mod.ensure_task_contract(workspace, "TASK-001")
            register.assert_not_called()

    def test_claiming_a_task_materializes_its_contract_first(self) -> None:
        """The safety property: a claim is refused without a source contract."""
        source = SCRIPT.read_text(encoding="utf-8")
        body = source[source.index("def default_execute(") :]
        materialize = body.index("ensure_task_contract(workspace, task_id)")
        claim = body.index('"claim",')
        self.assertLess(
            materialize,
            claim,
            "default_execute claims a task before materializing its contract",
        )


if __name__ == "__main__":
    unittest.main()
