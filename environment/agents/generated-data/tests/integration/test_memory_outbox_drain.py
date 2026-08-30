from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
GENERATED = ROOT / "environment" / "agents" / "generated-data"
ORCHESTRATION = GENERATED / "orchestration"
for path in (str(ORCHESTRATION), str(ROOT / "environment" / "agents")):
    if path not in sys.path:
        sys.path.insert(0, path)

from delivery_worker import DeliveryWorker, DeliveryWorkerConfiguration
from processor import GeneratedDataProcessor, ProcessingConfiguration
from retry_policy import RetryPolicy
from state_store import PipelineState, PipelineStateStore

ACCEPT_CMD = [
    sys.executable,
    "-c",
    "import json,sys; json.dump({'status':'accepted','memory_id':'m-1','write_receipt_id':'w-1'}, sys.stdout)",
]
FAIL_CMD = [sys.executable, "-c", "import sys; sys.exit(1)"]


def _packet() -> dict:
    return json.loads(
        (GENERATED / "tests" / "fixtures" / "valid-recon-packet.json").read_text(encoding="utf-8")
    )


class MemoryOutboxDrainTests(unittest.TestCase):
    def _enqueue(self, tmp: Path) -> tuple[DeliveryWorker, Path, str, PipelineStateStore]:
        database = tmp / "pipeline.sqlite3"
        store = PipelineStateStore(database)
        processor = GeneratedDataProcessor(
            ProcessingConfiguration(
                repository_root=str(ROOT),
                database_path=str(database),
            ),
            store=store,
        )
        processing = processor.process_packet(
            _packet(),
            actor="drain-test",
            independent_validation_present=True,
            designated_authority_approval=True,
            recurrence_counts={"unit-repo-fact-001": 2, "unit-contract-gap-001": 2},
        )
        outbox = tmp / "outbox" / "memory"
        worker = DeliveryWorker(
            DeliveryWorkerConfiguration(
                repository_root=str(ROOT),
                database_path=str(database),
                memory_mode="outbox",
                memory_outbox=str(outbox),
                route_outbox_root=str(tmp / "routes"),
            ),
            store=store,
        )
        delivery = worker.run_once(actor="drain-test", job_id=processing.job.job_id)
        assert delivery is not None
        self.assertGreaterEqual(delivery.enqueued, 1)
        return worker, outbox, processing.job.job_id, store

    def _drain_worker(
        self,
        tmp: Path,
        *,
        command: list[str],
        retry_policy: RetryPolicy | None = None,
        memory_mode: str = "command",
    ) -> DeliveryWorker:
        return DeliveryWorker(
            DeliveryWorkerConfiguration(
                repository_root=str(ROOT),
                database_path=str(tmp / "pipeline.sqlite3"),
                memory_mode=memory_mode,
                memory_command=tuple(command),
                memory_outbox=str(tmp / "outbox" / "memory"),
                route_outbox_root=str(tmp / "routes"),
            ),
            store=PipelineStateStore(tmp / "pipeline.sqlite3"),
            retry_policy=retry_policy,
        )

    def test_success_advances_submitted_to_accepted_and_removes_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            _worker, outbox, job_id, store = self._enqueue(tmp)
            self.assertTrue(list(outbox.glob("memcand-*.json")))
            drained = self._drain_worker(tmp, command=ACCEPT_CMD).drain_memory_outbox(
                actor="drain-test"
            )
            job = store.get_job(job_id)
            self.assertEqual(job.state, PipelineState.DESTINATION_ACCEPTED)
            self.assertEqual(drained[0]["status"], "accepted")
            self.assertFalse(list(outbox.glob("memcand-*.json")))
            with store.connect() as connection:
                campaign = connection.execute(
                    "SELECT state FROM campaigns WHERE campaign_id = ?",
                    (_packet()["identity"]["campaign_id"],),
                ).fetchone()
            self.assertEqual(campaign["state"], "completed")

    def test_unconfigured_transport_leaves_submitted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            _worker, outbox, job_id, store = self._enqueue(tmp)
            drained = DeliveryWorker(
                DeliveryWorkerConfiguration(
                    repository_root=str(ROOT),
                    database_path=str(tmp / "pipeline.sqlite3"),
                    memory_mode="outbox",
                    memory_command=(),
                    memory_outbox=str(outbox),
                    route_outbox_root=str(tmp / "routes"),
                ),
                store=store,
            ).drain_memory_outbox(actor="drain-test")
            job = store.get_job(job_id)
            self.assertEqual(job.state, PipelineState.DESTINATION_SUBMITTED)
            self.assertEqual(drained[0]["status"], "unconfigured")
            self.assertTrue(list(outbox.glob("memcand-*.json")))
            with store.connect() as connection:
                failed = connection.execute(
                    "SELECT COUNT(*) AS n FROM delivery_attempts WHERE job_id = ? AND status = 'FAILED'",
                    (job_id,),
                ).fetchone()["n"]
            self.assertGreaterEqual(int(failed), 1)

    def test_second_drain_is_idempotent(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            self._enqueue(tmp)
            worker = self._drain_worker(tmp, command=ACCEPT_CMD)
            first = worker.drain_memory_outbox(actor="drain-test")
            second = worker.drain_memory_outbox(actor="drain-test")
            self.assertEqual(first[0]["status"], "accepted")
            self.assertEqual(second, [])

    def test_transient_failure_retries_then_dead_letters(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            _worker, outbox, job_id, store = self._enqueue(tmp)
            retrying = self._drain_worker(
                tmp,
                command=FAIL_CMD,
                retry_policy=RetryPolicy(max_attempts=10),
            ).drain_memory_outbox(actor="drain-test")
            self.assertEqual(retrying[0]["status"], "retry")
            self.assertEqual(store.get_job(job_id).state, PipelineState.RETRY_WAIT)
            self.assertTrue(list(outbox.glob("memcand-*.json")))
            store.transition(
                job_id=job_id,
                expected_state=PipelineState.RETRY_WAIT,
                target_state=PipelineState.DESTINATION_SUBMITTED,
                actor="drain-test",
                payload={"reason": "rearm-for-ceiling"},
            )
            dead = self._drain_worker(
                tmp,
                command=FAIL_CMD,
                retry_policy=RetryPolicy(max_attempts=1),
            ).drain_memory_outbox(actor="drain-test")
            self.assertEqual(dead[0]["status"], "dead_lettered")
            self.assertEqual(store.get_job(job_id).state, PipelineState.DEAD_LETTERED)

    def test_legacy_location_candidates_are_adopted(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            worker, outbox, job_id, store = self._enqueue(tmp)
            files = list(outbox.glob("memcand-*.json"))
            self.assertTrue(files)
            legacy = tmp / "legacy-outbox"
            legacy.mkdir()
            adopted_name = files[0].name
            (legacy / adopted_name).write_bytes(files[0].read_bytes())
            files[0].unlink()
            drain_worker = self._drain_worker(tmp, command=ACCEPT_CMD)
            drain_worker._legacy_memory_outbox_dir = lambda: legacy  # type: ignore[method-assign]
            drained = drain_worker.drain_memory_outbox(actor="drain-test")
            self.assertEqual(drained[0]["status"], "accepted")
            self.assertEqual(store.get_job(job_id).state, PipelineState.DESTINATION_ACCEPTED)
            self.assertFalse(list(outbox.glob("memcand-*.json")))


if __name__ == "__main__":
    unittest.main()
