"""R3: the runtime store has an authoritative schema version and one transaction model."""

from __future__ import annotations

import sqlite3
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR.parent))

from pec.state import (  # noqa: E402
    RUNTIME_SCHEMA_KEY,
    RUNTIME_SCHEMA_VERSION,
    StateDB,
    StateError,
)

_TASK = {
    "id": "TASK-001",
    "title": "t",
    "wave_id": "W0",
    "workstream_id": "WS-01",
    "target_id": "TARGET-001",
    "repository_id": "repo-a",
    "execution_kind": "repo_local",
    "objective": "o",
    "risk_tier": "T2",
    "definition_status": "ready",
}


def _legacy_v1(path: Path) -> None:
    """A runtime written before the verification_mechanisms column existed."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE tasks (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, wave_id TEXT NOT NULL,
          workstream_id TEXT NOT NULL, target_id TEXT NOT NULL, repository_id TEXT,
          execution_kind TEXT NOT NULL, objective TEXT NOT NULL, dependencies TEXT NOT NULL,
          required_decisions TEXT NOT NULL, blocking_unknowns TEXT NOT NULL,
          required_evidence TEXT NOT NULL, completion_gates TEXT NOT NULL,
          authorization_ceiling TEXT NOT NULL, required_acceptance TEXT NOT NULL,
          required_validation_commands TEXT NOT NULL, risk_tier TEXT NOT NULL,
          definition_status TEXT NOT NULL, runtime_state TEXT NOT NULL,
          scope_status TEXT NOT NULL, source_contract_path TEXT, source_contract_digest TEXT,
          rendered_contract_path TEXT, rendered_contract_digest TEXT, base_sha TEXT,
          branch TEXT, worktree TEXT, lease_id TEXT, attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT
        );
        INSERT INTO tasks VALUES (
          'TASK-001','t','W0','WS-01','TARGET-001','repo-a','repo_local','o','[]','[]','[]',
          '[]','[]','{}','[]','[]','T2','ready','EXECUTING','exact',NULL,NULL,NULL,NULL,
          NULL,NULL,NULL,NULL,0,NULL
        );
        """
    )
    conn.commit()
    conn.close()


class SchemaVersionTests(unittest.TestCase):
    def test_fresh_database_is_stamped_at_the_current_version(self) -> None:
        with TemporaryDirectory() as raw:
            db = StateDB(Path(raw) / "state.sqlite")
            try:
                self.assertEqual(db.schema_version(), RUNTIME_SCHEMA_VERSION)
            finally:
                db.close()

    def test_legacy_v1_runtime_migrates_and_keeps_its_rows(self) -> None:
        with TemporaryDirectory() as raw:
            path = Path(raw) / "state.sqlite"
            _legacy_v1(path)
            db = StateDB(path)
            try:
                self.assertEqual(db.schema_version(), RUNTIME_SCHEMA_VERSION)
                task = db.task("TASK-001")
                assert task is not None
                self.assertEqual(task["runtime_state"], "EXECUTING")
                self.assertEqual(task["verification_mechanisms"], [])
            finally:
                db.close()

    def test_interrupted_migration_completes_on_the_next_open(self) -> None:
        """Version is the LAST write: a column added without the stamp re-migrates."""
        with TemporaryDirectory() as raw:
            path = Path(raw) / "state.sqlite"
            _legacy_v1(path)
            conn = sqlite3.connect(path)
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN verification_mechanisms TEXT NOT NULL DEFAULT '[]'"
            )
            conn.commit()
            conn.close()
            db = StateDB(path)
            try:
                self.assertEqual(db.schema_version(), RUNTIME_SCHEMA_VERSION)
            finally:
                db.close()
            # Idempotent: a second open changes nothing.
            db = StateDB(path)
            try:
                self.assertEqual(db.schema_version(), RUNTIME_SCHEMA_VERSION)
            finally:
                db.close()

    def test_future_schema_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            path = Path(raw) / "state.sqlite"
            db = StateDB(path)
            db.set_meta(RUNTIME_SCHEMA_KEY, RUNTIME_SCHEMA_VERSION + 1)
            db.close()
            with self.assertRaises(StateError) as caught:
                StateDB(path)
            self.assertEqual(caught.exception.error_code, "RUNTIME_SCHEMA_INCOMPATIBLE")

    def test_unreadable_version_fails_closed(self) -> None:
        with TemporaryDirectory() as raw:
            path = Path(raw) / "state.sqlite"
            StateDB(path).close()
            conn = sqlite3.connect(path)
            conn.execute("UPDATE meta SET value='\"garbage\"' WHERE key=?", (RUNTIME_SCHEMA_KEY,))
            conn.commit()
            conn.close()
            with self.assertRaises(StateError):
                StateDB(path)


class ControllerTransactionTests(unittest.TestCase):
    def _db(self, root: Path) -> StateDB:
        db = StateDB(root / "state.sqlite")
        db.upsert_task(_TASK)
        return db

    def test_primitives_autocommit_outside_a_transaction(self) -> None:
        with TemporaryDirectory() as raw:
            db = self._db(Path(raw))
            db.transition_task("TASK-001", "ELIGIBLE")
            other = StateDB(Path(raw) / "state.sqlite")
            try:
                self.assertEqual(other.task("TASK-001")["runtime_state"], "ELIGIBLE")  # type: ignore[index]
            finally:
                other.close()
                db.close()

    def test_nested_primitives_commit_together_or_not_at_all(self) -> None:
        with TemporaryDirectory() as raw:
            db = self._db(Path(raw))
            other = StateDB(Path(raw) / "state.sqlite")
            try:
                with self.assertRaises(RuntimeError):
                    with db.controller_transaction():
                        db.transition_task("TASK-001", "ELIGIBLE")
                        db.set_meta("global_halt", True)
                        raise RuntimeError("boom")
                self.assertEqual(db.task("TASK-001")["runtime_state"], "WAITING")  # type: ignore[index]
                self.assertFalse(db.get_meta("global_halt", False))
                with db.controller_transaction():
                    db.transition_task("TASK-001", "ELIGIBLE")
                    db.set_meta("global_halt", True)
                    # Not visible to another connection until COMMIT.
                    self.assertEqual(other.task("TASK-001")["runtime_state"], "WAITING")  # type: ignore[index]
                self.assertEqual(other.task("TASK-001")["runtime_state"], "ELIGIBLE")  # type: ignore[index]
                self.assertTrue(other.get_meta("global_halt"))
            finally:
                other.close()
                db.close()

    def test_on_commit_hooks_run_after_commit_and_never_after_rollback(self) -> None:
        with TemporaryDirectory() as raw:
            db = self._db(Path(raw))
            fired: list[str] = []
            try:
                with self.assertRaises(RuntimeError):
                    with db.controller_transaction():
                        db.on_commit(lambda: fired.append("rolled-back"))
                        raise RuntimeError("boom")
                with db.controller_transaction():
                    db.on_commit(lambda: fired.append("committed"))
                    self.assertEqual(fired, [])
                self.assertEqual(fired, ["committed"])
                db.on_commit(lambda: fired.append("immediate"))
                self.assertEqual(fired, ["committed", "immediate"])
            finally:
                db.close()

    def test_nested_transactions_join_the_outer_one(self) -> None:
        with TemporaryDirectory() as raw:
            db = self._db(Path(raw))
            try:
                with db.controller_transaction():
                    with db.controller_transaction():
                        db.transition_task("TASK-001", "ELIGIBLE")
                    self.assertTrue(db.in_transaction)
                self.assertFalse(db.in_transaction)
                self.assertEqual(db.task("TASK-001")["runtime_state"], "ELIGIBLE")  # type: ignore[index]
            finally:
                db.close()

    def test_concurrent_writers_serialize_on_the_single_writer_lock(self) -> None:
        with TemporaryDirectory() as raw:
            path = Path(raw) / "state.sqlite"
            self._db(Path(raw)).close()
            errors: list[BaseException] = []

            def bump(n: int) -> None:
                db = StateDB(path)
                try:
                    for _ in range(n):
                        with db.controller_transaction():
                            current = int(db.get_meta("counter", 0))
                            db.set_meta("counter", current + 1)
                except BaseException as exc:  # noqa: BLE001 - collected for the assertion
                    errors.append(exc)
                finally:
                    db.close()

            threads = [threading.Thread(target=bump, args=(25,)) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            db = StateDB(path)
            try:
                self.assertEqual(db.get_meta("counter"), 100)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
