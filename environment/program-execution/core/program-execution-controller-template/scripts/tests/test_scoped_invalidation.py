"""Editing one task's definition must not invalidate the other tasks.

The Program Lock freezes the blueprint by file digest, and every task card lives
in one file, so changing `TASK-002`'s validation command used to mark the whole
lock stale: `TASK-001` became unready and its verification gate read STALE even
though its own definition had not moved. The only cure was a fresh workspace,
which discards the completed history of every task to adopt one new definition.

These tests pin the separation between definition state and execution history --
in both directions. Scoping is a precision improvement, not a relaxation, so the
cases where drift *cannot* be attributed to a task must still fail closed.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR.parent))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import yaml  # noqa: E402
from helpers import (  # type: ignore[import-not-found]  # noqa: E402
    CONTROLLER_ROOT,
    make_blueprint,
    write_yaml,
)
from pec.blueprint import (  # noqa: E402
    relock_tasks,
    stale_task_ids,
    task_definition_digest,
    verify_program_lock,
    write_program_lock,
)
from pec.controller import (  # noqa: E402
    ControllerError,
    bootstrap,
    open_runtime,
    relock_definitions,
    task_readiness,
)


def _edit_validation(blueprint: Path, task_id: str) -> None:
    """Change one task's validation command, leaving every other card alone."""
    path = blueprint / "TASK_CARDS.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    for task in doc["tasks"]:
        if task["id"] == task_id:
            task["validation"][0]["command_or_inspection"] = "python3 -c 'print(1)'"
    write_yaml(path, doc)


def _locked(lock_path: Path) -> dict[str, dict[str, Any]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    return {str(task["id"]): task for task in lock["tasks"]}


class ScopedStalenessTests(unittest.TestCase):
    def test_an_unedited_task_is_not_stale(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
            lock_path = tmp / "program-lock.json"
            write_program_lock(blueprint, lock_path)

            _edit_validation(blueprint, "TASK-002")

            self.assertFalse(
                verify_program_lock(lock_path)[0],
                "file-level verification should still see the changed task card",
            )
            self.assertEqual(stale_task_ids(lock_path), {"TASK-002"})

    def test_nothing_is_stale_when_nothing_changed(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
            lock_path = tmp / "program-lock.json"
            write_program_lock(blueprint, lock_path)

            self.assertEqual(stale_task_ids(lock_path), set())

    def test_a_program_wide_edit_declines_to_scope(self) -> None:
        """Authority, gates and evidence describe the program, not one task."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
            lock_path = tmp / "program-lock.json"
            write_program_lock(blueprint, lock_path)

            catalog = blueprint / "EVIDENCE_CATALOG.yaml"
            doc = yaml.safe_load(catalog.read_text(encoding="utf-8"))
            doc["schema_version"] = "2.0.1"
            write_yaml(catalog, doc)

            self.assertIsNone(stale_task_ids(lock_path))

    def test_a_tampered_lock_declines_to_scope(self) -> None:
        """A lock that misdescribes itself is not evidence about any task."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
            lock_path = tmp / "program-lock.json"
            write_program_lock(blueprint, lock_path)

            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            payload["tasks"][0]["objective"] = "something nobody locked"
            lock_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

            self.assertIsNone(stale_task_ids(lock_path))

    def test_an_added_task_declines_to_scope(self) -> None:
        """Adding work changes the shape of the program, not one definition."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint = make_blueprint(tmp / "blueprint")
            lock_path = tmp / "program-lock.json"
            write_program_lock(blueprint, lock_path)

            grown = make_blueprint(blueprint, two_tasks=True)
            self.assertEqual(grown, blueprint)
            self.assertIsNone(stale_task_ids(lock_path))

    def test_a_missing_blueprint_file_declines_to_scope(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
            lock_path = tmp / "program-lock.json"
            write_program_lock(blueprint, lock_path)

            (blueprint / "TASK_CARDS.yaml").unlink()
            self.assertIsNone(stale_task_ids(lock_path))


class RelockTests(unittest.TestCase):
    def _drifted(self, tmp: Path) -> tuple[Path, Path]:
        blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
        lock_path = tmp / "program-lock.json"
        write_program_lock(blueprint, lock_path)
        _edit_validation(blueprint, "TASK-002")
        return blueprint, lock_path

    def test_relocking_adopts_only_the_edited_definition(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            _, lock_path = self._drifted(tmp)
            before = _locked(lock_path)

            outcome = relock_tasks(lock_path, ["TASK-002"])
            after = _locked(lock_path)

            self.assertEqual(outcome["relocked"], ["TASK-002"])
            self.assertEqual(
                task_definition_digest(after["TASK-001"]),
                task_definition_digest(before["TASK-001"]),
                "an unedited task's frozen definition changed during a relock",
            )
            self.assertNotEqual(
                task_definition_digest(after["TASK-002"]),
                task_definition_digest(before["TASK-002"]),
            )
            self.assertEqual(
                after["TASK-002"]["required_validation_commands"],
                ["python3 -c 'print(1)'"],
            )

    def test_a_relocked_lock_verifies_again(self) -> None:
        """The relock must resolve the staleness, not merely rename it."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            _, lock_path = self._drifted(tmp)

            relock_tasks(lock_path, ["TASK-002"])

            ok, errors = verify_program_lock(lock_path)
            self.assertTrue(ok, errors)
            self.assertEqual(stale_task_ids(lock_path), set())

    def test_the_relock_reports_which_definition_replaced_which(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            _, lock_path = self._drifted(tmp)
            before = _locked(lock_path)

            outcome = relock_tasks(lock_path, ["TASK-002"])

            moved = outcome["definitions"]["TASK-002"]
            self.assertEqual(moved["from"], task_definition_digest(before["TASK-002"]))
            self.assertEqual(moved["to"], task_definition_digest(_locked(lock_path)["TASK-002"]))
            self.assertNotEqual(outcome["previous_lock_digest"], outcome["lock_digest"])

    def test_relocking_a_task_the_blueprint_no_longer_has_is_refused(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            _, lock_path = self._drifted(tmp)

            with self.assertRaises(Exception) as caught:
                relock_tasks(lock_path, ["TASK-404"])
            self.assertIn("TASK-404", str(caught.exception))


class CompletedHistorySurvivesTests(unittest.TestCase):
    """SP-03: editing a later task leaves earlier work, and its receipts, alone."""

    def _runtime(self, tmp: Path) -> tuple[Path, Path]:
        blueprint = make_blueprint(tmp / "blueprint", two_tasks=True)
        workspace = tmp / "workspace"
        bootstrap(workspace, blueprint, CONTROLLER_ROOT)
        return blueprint, workspace

    def _complete(self, workspace: Path, task_id: str) -> None:
        """Put a task in the state a finished task is in, receipts included."""
        db, _ = open_runtime(workspace)
        try:
            db.update_task(
                task_id,
                scope_status="exact",
                source_contract_path=str(workspace / "contracts/source" / f"{task_id}.json"),
                source_contract_digest="digest-of-the-definition-it-was-built-from",
            )
            db.transition_task(task_id, "ELIGIBLE")
            db.transition_task(task_id, "COMPLETED")
        finally:
            db.close()
        receipt = workspace / "receipts" / "verification" / f"{task_id}.json"
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({"task_id": task_id, "verdict": "PASSED_LOCAL"}), "utf-8")

    def _task(self, workspace: Path, task_id: str) -> dict[str, Any]:
        db, _ = open_runtime(workspace)
        try:
            return dict(db.task(task_id) or {})
        finally:
            db.close()

    def test_a_completed_task_keeps_its_state_and_receipt(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint, workspace = self._runtime(tmp)
            self._complete(workspace, "TASK-001")
            receipt = workspace / "receipts" / "verification" / "TASK-001.json"
            before = receipt.read_bytes()

            _edit_validation(blueprint, "TASK-002")
            outcome = relock_definitions(workspace, actor="test")

            self.assertEqual(outcome["relocked"], ["TASK-002"])
            task = self._task(workspace, "TASK-001")
            self.assertEqual(task["runtime_state"], "COMPLETED")
            self.assertEqual(task["scope_status"], "exact")
            self.assertEqual(
                task["source_contract_digest"],
                "digest-of-the-definition-it-was-built-from",
                "a completed task lost the provenance of what produced its code",
            )
            self.assertEqual(receipt.read_bytes(), before)

    def test_the_edited_task_loses_the_contract_built_from_the_old_definition(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint, workspace = self._runtime(tmp)
            self._complete(workspace, "TASK-001")
            db, _ = open_runtime(workspace)
            try:
                db.update_task("TASK-002", scope_status="exact", source_contract_digest="stale")
            finally:
                db.close()

            _edit_validation(blueprint, "TASK-002")
            relock_definitions(workspace, actor="test")

            task = self._task(workspace, "TASK-002")
            self.assertEqual(task["scope_status"], "intent_only")
            self.assertIsNone(task["source_contract_digest"])
            self.assertEqual(
                task["required_validation_commands"],
                ["python3 -c 'print(1)'"],
                "the relocked task is still running the definition that was replaced",
            )

    def test_an_edit_to_a_later_task_leaves_the_earlier_one_ready(self) -> None:
        """The blocker that used to hit every task in the program."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint, workspace = self._runtime(tmp)

            _edit_validation(blueprint, "TASK-002")

            db, _ = open_runtime(workspace)
            try:
                first = db.task("TASK-001")
                assert first is not None
                _, blockers = task_readiness(db, first, workspace)
            finally:
                db.close()
            self.assertNotIn("program_lock_stale_or_invalid", blockers)

    def test_a_program_wide_edit_still_refuses_to_relock(self) -> None:
        """Fail closed when the drift cannot be attributed to a task."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint, workspace = self._runtime(tmp)

            catalog = blueprint / "EVIDENCE_CATALOG.yaml"
            doc = yaml.safe_load(catalog.read_text(encoding="utf-8"))
            doc["schema_version"] = "2.0.1"
            write_yaml(catalog, doc)

            with self.assertRaises(ControllerError) as caught:
                relock_definitions(workspace, actor="test")
            self.assertIn("fresh workspace", str(caught.exception))

    def test_relocking_records_provenance_for_the_definition_change(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint, workspace = self._runtime(tmp)
            self._complete(workspace, "TASK-001")

            _edit_validation(blueprint, "TASK-002")
            relock_definitions(workspace, actor="test")

            lines = (
                (workspace / "runtime" / "definition-provenance.jsonl")
                .read_text(encoding="utf-8")
                .strip()
                .splitlines()
            )
            record = json.loads(lines[-1])
            self.assertEqual(sorted(record["definitions"]), ["TASK-002"])
            self.assertNotEqual(record["previous_lock_digest"], record["lock_digest"])
            self.assertEqual(record["actor"], "test")

    def test_a_completed_task_whose_own_definition_moved_is_recorded_as_superseded(self) -> None:
        """History survives, and the record says the definition moved under it."""
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            blueprint, workspace = self._runtime(tmp)
            self._complete(workspace, "TASK-001")

            _edit_validation(blueprint, "TASK-001")
            outcome = relock_definitions(workspace, actor="test")

            self.assertEqual(outcome["superseded_after_completion"], ["TASK-001"])
            self.assertEqual(self._task(workspace, "TASK-001")["runtime_state"], "COMPLETED")

    def test_an_unchanged_blueprint_is_a_no_op(self) -> None:
        with TemporaryDirectory() as raw:
            tmp = Path(raw)
            _, workspace = self._runtime(tmp)

            outcome = relock_definitions(workspace, actor="test")

            self.assertEqual(outcome["status"], "CURRENT")
            self.assertFalse((workspace / "runtime" / "definition-provenance.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
