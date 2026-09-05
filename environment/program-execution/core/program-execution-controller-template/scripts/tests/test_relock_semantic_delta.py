"""PEC-P0-002: a task-scoped relock proves complete semantic containment.

The caller's `--task` list is a requested MAXIMUM scope. The Controller
discovers what changed from the full semantic delta between the lock and the
Blueprint, and admits the relock only when every difference is a definition
inside that scope. Nothing wider may disappear behind a refreshed digest, and a
refused relock alters nothing.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR.parent))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from helpers import make_blueprint, write_yaml  # noqa: E402
from pec.blueprint import (  # noqa: E402
    RESUME_EXACT_MATCH,
    RESUME_LOCK_INVALID,
    RESUME_SCHEMA_INCOMPATIBLE,
    RESUME_SOURCE_UNAVAILABLE,
    RESUME_TARGET_MISMATCH,
    RESUME_TASK_SCOPED_DRIFT,
    RESUME_WIDER_PROGRAM_DRIFT,
    BlueprintError,
    classify_lock_drift,
    relock_tasks,
    verify_program_lock,
    write_program_lock,
)


def _edit(blueprint: Path, name: str, mutate: Any) -> None:
    path = blueprint / name
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(doc)
    write_yaml(path, doc)


def _edit_task(blueprint: Path, task_id: str, **fields: Any) -> None:
    def mutate(doc: dict[str, Any]) -> None:
        for task in doc["tasks"]:
            if task["id"] == task_id:
                task.update(fields)

    _edit(blueprint, "TASK_CARDS.yaml", mutate)


class _Locked(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.blueprint = make_blueprint(self.tmp / "blueprint", two_tasks=True)
        self.lock_path = self.tmp / "program-lock.json"
        write_program_lock(self.blueprint, self.lock_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def assert_refused(self, task_ids: list[str], code: str) -> BlueprintError:
        before = self.lock_path.read_bytes()
        with self.assertRaises(BlueprintError) as caught:
            relock_tasks(self.lock_path, task_ids)
        self.assertEqual(caught.exception.error_code, code, str(caught.exception))
        self.assertEqual(self.lock_path.read_bytes(), before, "a refused relock must write nothing")
        return caught.exception


class ScopeContainmentTests(_Locked):
    def test_task_only_change_inside_scope_passes(self) -> None:
        _edit_task(self.blueprint, "TASK-001", objective="edited")
        outcome = relock_tasks(self.lock_path, ["TASK-001"])
        self.assertEqual(outcome["status"], "RELOCKED")
        self.assertEqual(outcome["relocked"], ["TASK-001"])
        self.assertTrue(verify_program_lock(self.lock_path)[0])

    def test_two_changed_tasks_with_one_named_is_scope_insufficient(self) -> None:
        _edit_task(self.blueprint, "TASK-001", objective="edited 1")
        _edit_task(self.blueprint, "TASK-002", objective="edited 2")
        exc = self.assert_refused(["TASK-001"], "RELOCK_SCOPE_INSUFFICIENT")
        self.assertIn("TASK-002", str(exc))

    def test_scope_wider_than_the_change_relocks_only_what_moved(self) -> None:
        """The scope is a maximum; unchanged tasks in it are not rewritten."""
        _edit_task(self.blueprint, "TASK-002", objective="edited 2")
        outcome = relock_tasks(self.lock_path, ["TASK-001", "TASK-002"])
        self.assertEqual(outcome["relocked"], ["TASK-002"])

    def test_task_plus_gate_change_is_global_drift(self) -> None:
        _edit_task(self.blueprint, "TASK-001", objective="edited")
        _edit(
            self.blueprint,
            "CONVERGENCE_GATES.yaml",
            lambda doc: doc["gates"][0].__setitem__("pass_condition", "weaker"),
        )
        exc = self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")
        self.assertIn("gates", str(exc))

    def test_task_plus_authority_change_is_global_drift(self) -> None:
        _edit_task(self.blueprint, "TASK-001", objective="edited")
        _edit(
            self.blueprint,
            "AUTHORITY_REGISTRY.yaml",
            lambda doc: doc["responsibilities"][0].__setitem__("owner_target_id", "TARGET-999"),
        )
        self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")

    def test_dependency_widening_affecting_another_task_is_global_drift(self) -> None:
        _edit_task(self.blueprint, "TASK-001", objective="edited")
        _edit(
            self.blueprint,
            "DEPENDENCY_GRAPH.yaml",
            lambda doc: doc["edges"].append({"from": "TASK-001", "to": "TASK-002"}),
        )
        exc = self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")
        self.assertIn("dependency_graph", str(exc))

    def test_waiver_expiry_edit_is_not_laundered_by_a_stamp_mask(self) -> None:
        """`expires_at` is program semantics on a waiver, compile noise on evidence."""
        _edit(
            self.blueprint,
            "WAIVER_REGISTER.yaml",
            lambda doc: doc["waivers"].append(
                {
                    "id": "WAIVER-001",
                    "scope": ["GATE-001"],
                    "status": "active",
                    "expires_at": "2030-01-01T00:00:00+00:00",
                    "evidence_ids": [],
                }
            ),
        )
        write_program_lock(self.blueprint, self.lock_path)
        _edit_task(self.blueprint, "TASK-001", objective="edited")
        _edit(
            self.blueprint,
            "WAIVER_REGISTER.yaml",
            lambda doc: doc["waivers"][0].__setitem__("expires_at", "2099-01-01T00:00:00+00:00"),
        )
        exc = self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")
        self.assertIn("waivers", str(exc))

    def test_task_addition_refuses_a_narrow_relock(self) -> None:
        make_blueprint(self.tmp / "blueprint")  # rewrites to one task
        write_program_lock(self.blueprint, self.lock_path)
        make_blueprint(self.tmp / "blueprint", two_tasks=True)
        self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")

    def test_task_removal_refuses_a_narrow_relock(self) -> None:
        make_blueprint(self.tmp / "blueprint")
        self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")

    def test_extra_execution_index_member_refuses(self) -> None:
        (self.blueprint / "EXTRA.yaml").write_text("extra: true\n", encoding="utf-8")
        _edit(
            self.blueprint,
            "EXECUTION_INDEX.yaml",
            lambda doc: doc["required_sources"].append("EXTRA.yaml"),
        )
        self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")

    def test_missing_indexed_member_refuses(self) -> None:
        (self.blueprint / "RISK_REGISTER.yaml").unlink()
        before = self.lock_path.read_bytes()
        with self.assertRaises(BlueprintError):
            relock_tasks(self.lock_path, ["TASK-001"])
        self.assertEqual(self.lock_path.read_bytes(), before)

    def test_unchanged_program_relock_is_idempotent(self) -> None:
        first = relock_tasks(self.lock_path, ["TASK-001"])
        self.assertEqual(first["status"], "CURRENT")
        self.assertEqual(first["relocked"], [])
        digest = json.loads(self.lock_path.read_text(encoding="utf-8"))["lock_digest"]
        second = relock_tasks(self.lock_path, ["TASK-001"])
        self.assertEqual(second["lock_digest"], digest)

    def test_relock_never_replaces_a_task_it_was_not_asked_about(self) -> None:
        _edit_task(self.blueprint, "TASK-002", objective="edited 2")
        self.assert_refused([], "RELOCK_SCOPE_INSUFFICIENT")

    def test_major_schema_mismatch_fails_closed(self) -> None:
        payload = json.loads(self.lock_path.read_text(encoding="utf-8"))
        payload["schema"] = "program-execution-controller.program-lock.v3"
        self.lock_path.write_text(json.dumps(payload), encoding="utf-8")
        self.assert_refused(["TASK-001"], "LOCK_INVALID")

    def test_a_tampered_lock_is_never_relocked(self) -> None:
        payload = json.loads(self.lock_path.read_text(encoding="utf-8"))
        payload["gates"] = []
        self.lock_path.write_text(json.dumps(payload), encoding="utf-8")
        self.assert_refused(["TASK-001"], "LOCK_INVALID")

    def test_source_digests_are_refreshed_only_after_admission(self) -> None:
        """A refused relock leaves the digests attesting the old bytes."""
        _edit_task(self.blueprint, "TASK-001", objective="edited")
        _edit(
            self.blueprint,
            "CONVERGENCE_GATES.yaml",
            lambda doc: doc["gates"][0].__setitem__("pass_condition", "weaker"),
        )
        recorded = json.loads(self.lock_path.read_text(encoding="utf-8"))["source_digests"]
        self.assert_refused(["TASK-001"], "PROGRAM_LOCK_GLOBAL_DRIFT")
        after = json.loads(self.lock_path.read_text(encoding="utf-8"))["source_digests"]
        self.assertEqual(recorded, after)


class ResumeClassificationTests(_Locked):
    def test_exact_match(self) -> None:
        self.assertEqual(classify_lock_drift(self.lock_path)["decision"], RESUME_EXACT_MATCH)

    def test_admission_annotations_are_still_exact(self) -> None:
        _edit(
            self.blueprint,
            "PROGRAM.yaml",
            lambda doc: doc["program"].update(
                {"definition_status": "accepted", "snapshot_at": "2031-01-01T00:00:00+00:00"}
            ),
        )
        result = classify_lock_drift(self.lock_path)
        self.assertEqual(result["decision"], RESUME_EXACT_MATCH)
        self.assertIn("PROGRAM.yaml", result["delta"]["source_digests_moved"])

    def test_task_scoped_drift(self) -> None:
        _edit_task(self.blueprint, "TASK-002", objective="edited")
        result = classify_lock_drift(self.lock_path)
        self.assertEqual(result["decision"], RESUME_TASK_SCOPED_DRIFT)
        self.assertEqual(result["delta"]["tasks_changed"], ["TASK-002"])

    def test_changed_validation_command_is_task_scoped_not_exact(self) -> None:
        _edit_task(
            self.blueprint,
            "TASK-001",
            validation=[
                {
                    "id": "VAL-001",
                    "method": "command",
                    "command_or_inspection": "python3 -c 'print(2)'",
                    "environment": "local",
                    "expected_result": "PASS",
                }
            ],
        )
        self.assertEqual(classify_lock_drift(self.lock_path)["decision"], RESUME_TASK_SCOPED_DRIFT)

    def test_gate_change_is_wider_program_drift(self) -> None:
        _edit(
            self.blueprint,
            "CONVERGENCE_GATES.yaml",
            lambda doc: doc["gates"][0].__setitem__("blocking", False),
        )
        self.assertEqual(
            classify_lock_drift(self.lock_path)["decision"], RESUME_WIDER_PROGRAM_DRIFT
        )

    def test_task_set_change_is_wider_program_drift(self) -> None:
        make_blueprint(self.tmp / "blueprint")
        self.assertEqual(
            classify_lock_drift(self.lock_path)["decision"], RESUME_WIDER_PROGRAM_DRIFT
        )

    def test_program_identity_change_is_target_mismatch(self) -> None:
        _edit(self.blueprint, "PROGRAM.yaml", lambda doc: doc["program"].__setitem__("id", "other"))
        self.assertEqual(classify_lock_drift(self.lock_path)["decision"], RESUME_TARGET_MISMATCH)

    def test_target_repository_change_is_target_mismatch(self) -> None:
        _edit(
            self.blueprint,
            "EXECUTION_TARGETS.yaml",
            lambda doc: doc["targets"][0].__setitem__("repository_id", "repo-b"),
        )
        self.assertEqual(classify_lock_drift(self.lock_path)["decision"], RESUME_TARGET_MISMATCH)

    def test_stale_lock_digest_is_lock_invalid(self) -> None:
        payload = json.loads(self.lock_path.read_text(encoding="utf-8"))
        payload["lock_digest"] = "0" * 64
        self.lock_path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(classify_lock_drift(self.lock_path)["decision"], RESUME_LOCK_INVALID)

    def test_schema_mismatch(self) -> None:
        payload = json.loads(self.lock_path.read_text(encoding="utf-8"))
        payload["schema"] = "program-execution-controller.program-lock.v9"
        self.lock_path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(
            classify_lock_drift(self.lock_path)["decision"], RESUME_SCHEMA_INCOMPATIBLE
        )

    def test_missing_source_is_unavailable(self) -> None:
        (self.blueprint / "TASK_CARDS.yaml").unlink()
        self.assertEqual(classify_lock_drift(self.lock_path)["decision"], RESUME_SOURCE_UNAVAILABLE)

    def test_repeated_classification_is_deterministic(self) -> None:
        _edit_task(self.blueprint, "TASK-002", objective="edited")
        first = classify_lock_drift(self.lock_path)
        second = classify_lock_drift(self.lock_path)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
