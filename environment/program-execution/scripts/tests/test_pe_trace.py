"""Telemetry semantics for PE-TRACE-001: the writer, and the harvester."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
TRACE_SCRIPT = PE_ROOT / "scripts/pe_trace.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeClock:
    """Deterministic monotonic clock: each read advances by a fixed step."""

    def __init__(self, step: float = 1.0) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        value = self.now
        self.now += self.step
        return value


class TraceWriterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_module("pe_trace_writer_under_test", TRACE_SCRIPT)
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def events(self) -> list[dict]:
        return self.mod.read_events(self.workspace)

    def test_trace_span_records_started_and_passed(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1", clock=FakeClock())
        with trace.span("compile", "compile_campaign_source"):
            pass
        events = self.events()
        self.assertEqual([item["status"] for item in events], ["STARTED", "PASSED"])
        self.assertEqual(events[1]["operation"], "compile_campaign_source")
        self.assertEqual(events[1]["duration_ms"], 1000)
        self.assertIsNone(events[0]["duration_ms"])

    def test_trace_span_records_started_and_failed(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1", clock=FakeClock())
        with self.assertRaises(ValueError):
            with trace.span("compile", "compile_campaign_source"):
                raise ValueError("bad source")
        events = self.events()
        self.assertEqual([item["status"] for item in events], ["STARTED", "FAILED"])
        self.assertEqual(events[1]["error_code"], "ValueError")
        self.assertEqual(events[1]["error_class"], "ValueError")
        self.assertEqual(events[1]["safe_message"], "bad source")
        self.assertEqual(events[1]["duration_ms"], 1000)

    def test_trace_failure_reraises_original_exception(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        sentinel = KeyError("original")
        with self.assertRaises(KeyError) as caught:
            with trace.span("bootstrap", "pec_bootstrap"):
                raise sentinel
        self.assertIs(caught.exception, sentinel)

    def test_trace_appends_valid_jsonl(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        trace.event("TASK_ELIGIBLE", "task", "task_eligible", task_id="TASK-001")
        with trace.span("validation", "validation_command", task_id="TASK-001"):
            pass
        raw = (self.workspace / "telemetry" / "events.jsonl").read_text(encoding="utf-8")
        lines = [line for line in raw.splitlines() if line.strip()]
        self.assertEqual(len(lines), 3)
        for line in lines:
            record = json.loads(line)
            self.assertEqual(record["schema"], "pe.execution-trace.v1")
            for field in (
                "event_id",
                "campaign_id",
                "run_id",
                "event_type",
                "category",
                "operation",
                "status",
                "timestamp",
                "duration_ms",
                "task_id",
                "attempt_number",
                "input_fingerprint",
                "cache_status",
                "error_code",
                "error_class",
                "safe_message",
                "safe_metadata",
            ):
                self.assertIn(field, record)
            # The pre-allowlist field names must not survive anywhere.
            self.assertNotIn("error_message", record)
            self.assertNotIn("metadata", record)

    def test_error_message_is_bounded(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        with self.assertRaises(RuntimeError):
            with trace.span("validation", "validation_command"):
                raise RuntimeError("x" * 5000)
        self.assertEqual(len(self.events()[1]["safe_message"]), 2000)

    def test_buffered_events_flush_on_bind(self) -> None:
        trace = self.mod.ExecutionTrace()
        trace.event("CAMPAIGN_INVOKED", "input", "input_classification")
        self.assertEqual(self.events(), [])
        trace.bind(self.workspace, campaign_id="demo-v1")
        events = self.events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["campaign_id"], "demo-v1")

    def test_telemetry_write_failure_does_not_raise(self) -> None:
        blocked = self.workspace / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        trace = self.mod.ExecutionTrace(blocked, "demo-v1")
        trace.event("CAMPAIGN_INVOKED", "input", "input_classification")
        self.assertFalse(trace.bound)

    def test_single_invocation_uses_one_run_id(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        with trace.span("compile", "compile_campaign_source"):
            pass
        trace.event("TASK_COMPLETED", "task", "task_completed", task_id="TASK-001")
        run_ids = {item["run_id"] for item in self.events()}
        self.assertEqual(run_ids, {trace.run_id})

    def test_resumed_invocation_gets_new_run_id(self) -> None:
        first = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        first.event("CAMPAIGN_INVOKED", "input", "input_classification")
        second = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        second.event("CAMPAIGN_INVOKED", "input", "input_classification")
        self.assertNotEqual(first.run_id, second.run_id)
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["run_ids"], [first.run_id, second.run_id])

    def test_task_events_include_task_id_and_attempt(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        trace.event(
            "TASK_VERIFY_FINISHED",
            "verification",
            "pec_verify",
            status="PASSED",
            task_id="TASK-004",
            attempt_number=2,
            duration_ms=10,
        )
        event = self.events()[0]
        self.assertEqual(event["task_id"], "TASK-004")
        self.assertEqual(event["attempt_number"], 2)

    def test_events_written_before_exception_remain_readable(self) -> None:
        """A killed process keeps every event it already emitted."""
        script = f"""
import sys
sys.path.insert(0, {str(TRACE_SCRIPT.parent)!r})
import pe_trace
trace = pe_trace.ExecutionTrace({str(self.workspace)!r}, "demo-v1")
trace.event("CAMPAIGN_INVOKED", "input", "input_classification")
with trace.span("compile", "compile_campaign_source"):
    pass
trace.event("TASK_ELIGIBLE", "task", "task_eligible", task_id="TASK-001")
import os
os.kill(os.getpid(), 9)
"""
        completed = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=60
        )
        self.assertNotEqual(completed.returncode, 0)
        events = self.events()
        self.assertEqual(len(events), 4)
        self.assertEqual(events[-1]["event_type"], "TASK_ELIGIBLE")

    def test_relocate_moves_events_and_keeps_appending(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        trace.event("CAMPAIGN_INVOKED", "input", "input_classification")
        moved = self.workspace / "recycled"
        trace.rehome(moved)
        trace.event("TASK_ELIGIBLE", "task", "task_eligible", task_id="TASK-001")
        self.assertFalse((self.workspace / "telemetry").exists())
        events = self.mod.read_events(moved)
        self.assertEqual(
            [item["event_type"] for item in events],
            ["CAMPAIGN_INVOKED", "TASK_ELIGIBLE"],
        )

    def test_relocate_appends_to_an_existing_destination(self) -> None:
        """Campaign-wide aggregates survive: an earlier run's events are kept."""
        first = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        first.event("CAMPAIGN_INVOKED", "input", "input_classification")
        staged = self.workspace / "staging"
        second = self.mod.ExecutionTrace(staged, "demo-v1")
        second.event("TASK_ELIGIBLE", "task", "task_eligible", task_id="TASK-001")
        second.relocate(self.workspace / "telemetry" / "events.jsonl")
        events = self.mod.read_events(self.workspace)
        self.assertEqual(
            [item["event_type"] for item in events],
            ["CAMPAIGN_INVOKED", "TASK_ELIGIBLE"],
        )
        self.assertEqual(len({item["run_id"] for item in events}), 2)

    def test_stepped_aside_leaves_the_workspace_clean_then_returns(self) -> None:
        """pec bootstrap refuses a non-empty workspace, so nothing may remain."""
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        trace.event("CAMPAIGN_INVOKED", "input", "input_classification")
        staging = self.workspace.parent / "staging"
        with trace.stepped_aside(staging):
            self.assertFalse((self.workspace / "telemetry").exists())
            trace.event("OPERATION_STARTED", "bootstrap", "pec_bootstrap", status="STARTED")
        self.assertFalse(staging.exists())
        events = self.mod.read_events(self.workspace)
        self.assertEqual(
            [item["event_type"] for item in events],
            ["CAMPAIGN_INVOKED", "OPERATION_STARTED"],
        )

    def test_stepped_aside_returns_home_after_a_failure(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        trace.event("CAMPAIGN_INVOKED", "input", "input_classification")
        staging = self.workspace.parent / "staging"
        with self.assertRaises(RuntimeError):
            with trace.stepped_aside(staging):
                raise RuntimeError("bootstrap failed")
        trace.event("TASK_ELIGIBLE", "task", "task_eligible", task_id="TASK-001")
        self.assertEqual(len(self.mod.read_events(self.workspace)), 2)

    def test_fingerprint_is_deterministic_and_input_sensitive(self) -> None:
        source = self.workspace / "CAMPAIGN_SOURCE.yaml"
        source.write_text("campaign_id: demo-v1\n", encoding="utf-8")
        first = self.mod.fingerprint(source)
        self.assertEqual(first, self.mod.fingerprint(source))
        source.write_text("campaign_id: demo-v2\n", encoding="utf-8")
        self.assertNotEqual(first, self.mod.fingerprint(source))

    def test_fingerprint_ignores_emission_timestamps(self) -> None:
        """A recompiled artifact is re-stamped; that must not hide the repeat."""
        first = self.workspace / "a.yaml"
        second = self.workspace / "a.yaml"
        first.write_text("campaign_id: demo-v1\ncreated_at: '2026-08-18T18:00:00Z'\n")
        before = self.mod.fingerprint(first)
        second.write_text("campaign_id: demo-v1\ncreated_at: '2026-08-18T19:30:41Z'\n")
        self.assertEqual(before, self.mod.fingerprint(second))
        second.write_text("campaign_id: demo-v2\ncreated_at: '2026-08-18T19:30:41Z'\n")
        self.assertNotEqual(before, self.mod.fingerprint(second))

    def test_nested_spans_mark_the_reraise_as_propagated(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        with self.assertRaises(ValueError):
            with trace.span("execute", "execute"):
                with trace.span("worker", "worker_write", task_id="TASK-001"):
                    raise ValueError("boom")
        failed = [item for item in self.events() if item["status"] == "FAILED"]
        self.assertEqual([item["operation"] for item in failed], ["worker_write", "execute"])
        self.assertFalse(failed[0]["safe_metadata"]["propagated"])
        self.assertTrue(failed[1]["safe_metadata"]["propagated"])

    def test_span_prefers_an_exception_supplied_error_code(self) -> None:
        class Coded(RuntimeError):
            error_code = "PEC_PREPARE_FAILED"

        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        with self.assertRaises(Coded):
            with trace.span("task_prepare", "task_worktree_create"):
                raise Coded("worktree branch already exists")
        self.assertEqual(self.events()[1]["error_code"], "PEC_PREPARE_FAILED")


class HarvesterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_module("pe_trace_harvest_under_test", TRACE_SCRIPT)
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write_events(self, records: list[dict]) -> None:
        telemetry = self.workspace / "telemetry"
        telemetry.mkdir(parents=True, exist_ok=True)
        base = {
            "schema": "pe.execution-trace.v1",
            "campaign_id": "demo-v1",
            "run_id": "RUN-0001",
            "event_type": "OPERATION_FINISHED",
            "category": "compile",
            "operation": "compile_campaign_source",
            "status": "PASSED",
            "timestamp": "2026-08-18T18:00:00.000Z",
            "duration_ms": 0,
            "task_id": None,
            "attempt_number": None,
            "input_fingerprint": None,
            "cache_status": None,
            "error_code": None,
            "error_class": None,
            "safe_message": None,
            "safe_metadata": {},
        }
        with open(telemetry / "events.jsonl", "a", encoding="utf-8") as handle:
            for index, record in enumerate(records):
                merged = {**base, "event_id": f"EVT-{index:04d}", **record}
                handle.write(json.dumps(merged, sort_keys=True) + "\n")

    def test_harvester_detects_same_fingerprint_repeated_execution(self) -> None:
        self.write_events(
            [
                {"input_fingerprint": "abc", "duration_ms": 1000},
                {"input_fingerprint": "abc", "duration_ms": 2000},
                {"input_fingerprint": "abc", "duration_ms": 3000},
            ]
        )
        repeated = self.mod.harvest_trace(self.workspace)["repeated_operations"]
        self.assertEqual(len(repeated), 1)
        self.assertEqual(repeated[0]["executions"], 3)
        self.assertEqual(repeated[0]["extra_executions"], 2)
        self.assertEqual(repeated[0]["total_duration_ms"], 6000)
        self.assertEqual(repeated[0]["extra_duration_ms"], 5000)

    def test_harvester_does_not_merge_different_fingerprints(self) -> None:
        self.write_events(
            [
                {"input_fingerprint": "abc", "duration_ms": 1000},
                {"input_fingerprint": "def", "duration_ms": 2000},
            ]
        )
        self.assertEqual(self.mod.harvest_trace(self.workspace)["repeated_operations"], [])

    def test_harvester_does_not_count_started_events_as_executions(self) -> None:
        self.write_events(
            [
                {
                    "event_type": "OPERATION_STARTED",
                    "status": "STARTED",
                    "input_fingerprint": "abc",
                    "duration_ms": None,
                },
                {"input_fingerprint": "abc", "duration_ms": 1000},
            ]
        )
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["repeated_operations"], [])
        self.assertEqual(summary["operation_counts"]["compile_campaign_source"], 1)

    def test_harvester_calculates_time_to_first_write(self) -> None:
        self.write_events(
            [
                {
                    "event_type": "OPERATION_STARTED",
                    "operation": "campaign_run",
                    "category": "input",
                    "status": "STARTED",
                    "timestamp": "2026-08-18T18:00:00.000Z",
                    "duration_ms": None,
                },
                {
                    "event_type": "TASK_FIRST_WRITE",
                    "operation": "task_first_write",
                    "category": "filesystem_write",
                    "status": "INFO",
                    "task_id": "TASK-001",
                    "timestamp": "2026-08-18T18:02:30.000Z",
                    "duration_ms": None,
                },
            ]
        )
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["timing"]["time_to_first_write_ms"], 150_000)

    def test_harvester_calculates_task_eligible_to_first_write(self) -> None:
        self.write_events(
            [
                {
                    "event_type": "TASK_ELIGIBLE",
                    "operation": "task_eligible",
                    "category": "task",
                    "status": "INFO",
                    "task_id": "TASK-001",
                    "timestamp": "2026-08-18T18:00:00.000Z",
                    "duration_ms": None,
                },
                {
                    "event_type": "TASK_FIRST_WRITE",
                    "operation": "task_first_write",
                    "category": "filesystem_write",
                    "status": "INFO",
                    "task_id": "TASK-001",
                    "timestamp": "2026-08-18T18:00:12.000Z",
                    "duration_ms": None,
                },
            ]
        )
        per_task = self.mod.harvest_trace(self.workspace)["per_task"]
        self.assertEqual(per_task["TASK-001"]["eligible_to_first_write_ms"], 12_000)

    def test_harvester_calculates_category_totals(self) -> None:
        self.write_events(
            [
                {"category": "compile", "duration_ms": 1000},
                {"category": "bootstrap", "operation": "pec_bootstrap", "duration_ms": 2000},
                {
                    "category": "worker",
                    "operation": "worker_write",
                    "duration_ms": 4000,
                    "task_id": "TASK-001",
                },
                {
                    "category": "validation",
                    "operation": "validation_command",
                    "duration_ms": 8000,
                    "task_id": "TASK-001",
                },
                {
                    "category": "verification",
                    "operation": "pec_verify",
                    "duration_ms": 500,
                    "task_id": "TASK-001",
                },
                {"category": "workspace", "operation": "workspace_quarantine", "duration_ms": 250},
            ]
        )
        timing = self.mod.harvest_trace(self.workspace)["timing"]
        self.assertEqual(timing["preparation_ms"], 3000)
        self.assertEqual(timing["implementation_ms"], 4000)
        self.assertEqual(timing["validation_ms"], 8000)
        self.assertEqual(timing["verification_ms"], 500)
        self.assertEqual(timing["recovery_ms"], 250)

    def test_harvester_aggregates_error_codes(self) -> None:
        self.write_events(
            [
                {
                    "status": "FAILED",
                    "error_code": "TASK_NOT_SUBMITTED",
                    "task_id": "TASK-001",
                    "duration_ms": 100,
                },
                {
                    "status": "FAILED",
                    "error_code": "TASK_NOT_SUBMITTED",
                    "task_id": "TASK-002",
                    "duration_ms": 200,
                },
                {"status": "FAILED", "error_code": "VALIDATION_MISSING", "duration_ms": 50},
            ]
        )
        failures = self.mod.harvest_trace(self.workspace)["failure_counts"]
        self.assertEqual(failures["TASK_NOT_SUBMITTED"]["count"], 2)
        self.assertEqual(failures["TASK_NOT_SUBMITTED"]["total_duration_ms"], 300)
        self.assertEqual(failures["TASK_NOT_SUBMITTED"]["tasks"], ["TASK-001", "TASK-002"])
        self.assertEqual(failures["VALIDATION_MISSING"]["count"], 1)

    def test_harvester_reads_propagated_from_pre_rename_records(self) -> None:
        """One events.jsonl can span the rename, because `relocate` appends.

        A pre-rename record carries `metadata`, not `safe_metadata`. If the
        harvester ignored it, every legacy propagated failure would be counted
        as its own root cause.
        """
        self.write_events(
            [
                {
                    "status": "FAILED",
                    "error_code": "PEC_PREPARE_FAILED",
                    "task_id": "TASK-001",
                    "duration_ms": 100,
                    "safe_metadata": None,
                    "metadata": {"propagated": False},
                },
                {
                    "status": "FAILED",
                    "operation": "execute",
                    "error_code": "PEC_PREPARE_FAILED",
                    "task_id": "TASK-001",
                    "duration_ms": 900,
                    "safe_metadata": None,
                    "metadata": {"propagated": True},
                },
            ]
        )
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["failure_counts"]["PEC_PREPARE_FAILED"]["count"], 1)
        self.assertEqual(summary["per_task"]["TASK-001"]["failures"], 1)

    def test_harvester_ignores_propagated_failures(self) -> None:
        self.write_events(
            [
                {
                    "status": "FAILED",
                    "error_code": "PEC_PREPARE_FAILED",
                    "task_id": "TASK-001",
                    "duration_ms": 100,
                    "safe_metadata": {"propagated": False},
                },
                {
                    "status": "FAILED",
                    "operation": "execute",
                    "error_code": "PEC_PREPARE_FAILED",
                    "task_id": "TASK-001",
                    "duration_ms": 900,
                    "safe_metadata": {"propagated": True},
                },
            ]
        )
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["failure_counts"]["PEC_PREPARE_FAILED"]["count"], 1)
        self.assertEqual(summary["per_task"]["TASK-001"]["failures"], 1)
        # The enclosing span still consumed real time and is still counted.
        self.assertEqual(summary["operation_counts"]["execute"], 1)

    def test_harvester_counts_retries_and_workspace_recycles(self) -> None:
        self.write_events(
            [
                {
                    "event_type": "TASK_VERIFY_FINISHED",
                    "category": "verification",
                    "operation": "pec_verify",
                    "task_id": "TASK-001",
                    "attempt_number": 3,
                    "duration_ms": 10,
                },
                {"category": "workspace", "operation": "workspace_quarantine", "duration_ms": 5},
                {"category": "workspace", "operation": "workspace_quarantine", "duration_ms": 5},
            ]
        )
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["retry_counts"]["TASK-001"], 2)
        self.assertEqual(summary["workspace_recovery_counts"]["workspace_quarantine"], 2)

    def test_harvester_counts_completed_and_attempted_tasks(self) -> None:
        self.write_events(
            [
                {
                    "event_type": "TASK_ELIGIBLE",
                    "category": "task",
                    "operation": "task_eligible",
                    "status": "INFO",
                    "task_id": "TASK-001",
                    "duration_ms": None,
                },
                {
                    "event_type": "TASK_COMPLETED",
                    "category": "task",
                    "operation": "task_completed",
                    "status": "INFO",
                    "task_id": "TASK-001",
                    "duration_ms": None,
                },
                {
                    "event_type": "TASK_ELIGIBLE",
                    "category": "task",
                    "operation": "task_eligible",
                    "status": "INFO",
                    "task_id": "TASK-002",
                    "duration_ms": None,
                },
            ]
        )
        self.assertEqual(
            self.mod.harvest_trace(self.workspace)["task_counts"],
            {"completed": 1, "attempted": 2},
        )

    def test_campaign_aggregate_spans_multiple_runs(self) -> None:
        self.write_events(
            [
                {"run_id": "RUN-0001", "input_fingerprint": "abc", "duration_ms": 1000},
                {"run_id": "RUN-0002", "input_fingerprint": "abc", "duration_ms": 1000},
            ]
        )
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["run_ids"], ["RUN-0001", "RUN-0002"])
        self.assertEqual(summary["repeated_operations"][0]["executions"], 2)

    def test_harvester_skips_a_torn_final_line(self) -> None:
        self.write_events([{"duration_ms": 1000}])
        with open(self.workspace / "telemetry" / "events.jsonl", "a", encoding="utf-8") as handle:
            handle.write('{"schema": "pe.execution-tr')
        self.assertEqual(self.mod.harvest_trace(self.workspace)["event_count"], 1)

    def test_harvest_of_empty_workspace_returns_schema_shape(self) -> None:
        summary = self.mod.harvest_trace(self.workspace)
        self.assertEqual(summary["schema"], "pe.execution-trace-summary.v1")
        for field in (
            "campaign_id",
            "run_ids",
            "wall_clock_ms",
            "task_counts",
            "operation_counts",
            "failure_counts",
            "retry_counts",
            "repeated_operations",
            "timing",
            "top_time_consumers",
            "per_task",
        ):
            self.assertIn(field, summary)

    def test_write_summary_generates_json_and_markdown(self) -> None:
        self.write_events(
            [
                {"input_fingerprint": "abc", "duration_ms": 1000},
                {"input_fingerprint": "abc", "duration_ms": 1000},
                {
                    "status": "FAILED",
                    "error_code": "TASK_NOT_SUBMITTED",
                    "task_id": "TASK-001",
                    "duration_ms": 10,
                },
            ]
        )
        summary = self.mod.harvest_and_write(self.workspace)
        json_path = self.workspace / "telemetry" / "run-summary.json"
        md_path = self.workspace / "telemetry" / "run-summary.md"
        self.assertTrue(json_path.is_file())
        self.assertTrue(md_path.is_file())
        self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), summary)
        body = md_path.read_text(encoding="utf-8")
        for heading in (
            "Task progress",
            "Time distribution",
            "Time to first code",
            "Top 10 operations by duration",
            "Repeated operations with same inputs",
            "Failure counts",
            "Retry counts",
            "Per-task timings",
            "Workspace / recovery counts",
        ):
            self.assertIn(heading, body)
        self.assertIn("TASK_NOT_SUBMITTED", body)


# A value that must never survive to disk. Distinctive enough that a single
# occurrence anywhere under telemetry/ is unambiguous evidence of a leak.
SENTINEL = "L9_TEST_SECRET_DO_NOT_PERSIST_7f31"


class SecretRedactionTest(unittest.TestCase):
    """No injection path may write a live credential into persisted telemetry.

    The allowlisted record structure is the control being tested; the pattern
    sweep is the backstop. Both are exercised: `test_no_injection_vector...`
    registers the sentinel the way a campaign registers a resolved credential,
    while `test_shaped_credentials...` registers nothing, so only the patterns
    can save it.
    """

    def setUp(self) -> None:
        self.mod = load_module("pe_trace_redaction_under_test", TRACE_SCRIPT)
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(self.mod.clear_registered_secrets)

    def generated_files(self) -> list[Path]:
        """Every file the trace produced, found by walking -- not by name."""
        return sorted(path for path in (self.workspace / "telemetry").rglob("*") if path.is_file())

    def occurrences(self, needle: str) -> dict[str, int]:
        return {
            path.name: path.read_text(encoding="utf-8", errors="replace").count(needle)
            for path in self.generated_files()
        }

    def inject_every_vector(self, secret: str) -> None:
        """Push `secret` through all six paths a value can reach the trace by."""
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")

        # 1. Exception message -- the raw `str(exc)` path.
        with self.assertRaises(RuntimeError):
            with trace.span("compile", "compile_campaign_source"):
                raise RuntimeError(f"upstream rejected credential {secret}")

        # 2. Flat metadata, under a key that is not on the allowlist.
        trace.event("TASK_ELIGIBLE", "task", "task_eligible", metadata={"api_key": secret})

        # 3. Nested metadata, under a key that *is* on the allowlist -- the
        #    container itself has no safe rendering, so the whole value goes.
        trace.event(
            "TASK_ELIGIBLE",
            "task",
            "task_eligible",
            metadata={"count": 1, "verdict": {"headers": {"x-api-key": secret}}},
        )

        # 3b. The secret as a metadata *key*, which is reported by name.
        trace.event("TASK_ELIGIBLE", "task", "task_eligible", metadata={secret: "value"})

        # 4. Credential-bearing URL.
        trace.event(
            "OPERATION_FAILED",
            "task_prepare",
            "task_worktree_create",
            status="FAILED",
            error_code="CLONE_FAILED",
            error_message=f"clone failed for https://svc-account:{secret}@github.com/o/r.git",
        )

        # 5. Authorization header.
        trace.event(
            "OPERATION_FAILED",
            "gate",
            "gate_check",
            status="FAILED",
            error_code="HTTP_401",
            error_message=f'curl -H "Authorization: Bearer {secret}" https://api.example.com',
        )

        # 6. Environment-style assignment.
        trace.event(
            "OPERATION_FAILED",
            "validation",
            "validation_command",
            status="FAILED",
            error_code="VALIDATION_COMMAND_FAILED",
            error_message=f"env was GITHUB_TOKEN={secret} PATH=/usr/bin",
        )

        self.mod.harvest_and_write(self.workspace)

    def test_no_injection_vector_persists_a_registered_secret(self) -> None:
        self.mod.register_secret_value(SENTINEL)
        self.inject_every_vector(SENTINEL)

        found = self.occurrences(SENTINEL)
        # The scan must have actually read the artifacts it claims are clean.
        self.assertIn("events.jsonl", found)
        self.assertIn("run-summary.json", found)
        self.assertIn("run-summary.md", found)
        self.assertEqual(sum(found.values()), 0, f"sentinel survived to disk: {found}")

    def test_trace_stays_useful_after_redaction(self) -> None:
        """Redaction must cost the secret, not the diagnosis."""
        self.mod.register_secret_value(SENTINEL)
        self.inject_every_vector(SENTINEL)
        events = self.mod.read_events(self.workspace)

        failed = [item for item in events if item["status"] == "FAILED"]
        self.assertEqual(
            [item["error_code"] for item in failed],
            ["RuntimeError", "CLONE_FAILED", "HTTP_401", "VALIDATION_COMMAND_FAILED"],
        )
        # The exception's class survives, and its message survives around the
        # hole where the credential was.
        self.assertEqual(failed[0]["error_class"], "RuntimeError")
        self.assertIn("upstream rejected credential", failed[0]["safe_message"])
        self.assertIn("<redacted>", failed[0]["safe_message"])
        # A credential-bearing URL keeps the host, which is the diagnostic part.
        self.assertIn("github.com/o/r.git", failed[1]["safe_message"])
        # Allowlisted scalars pass through; rejected keys are named, not valued.
        nested = [item for item in events if item.get("safe_metadata", {}).get("count") == 1]
        self.assertEqual(nested[0]["safe_metadata"]["count"], 1)
        self.assertEqual(nested[0]["safe_metadata"]["redacted_keys"], ["verdict"])

    def test_shaped_credentials_are_masked_without_registration(self) -> None:
        """The pattern sweep must stand on its own, with an empty registry."""
        cases = {
            "url": "clone https://user:hunter2primary@github.com/o/r.git failed",
            "bearer": 'curl -H "Authorization: Bearer abcdef0123456789xyz" https://api',
            "env": "env had AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMIK7MDENGbPxRfiCY",
            "query": "GET /v1/items?api_key=6f1b9c2d4e8a0b3c5d7e9f1a",
            "github": "remote rejected: ghp_ABCdef0123456789ABCdef0123456789abcd",
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.dBjftJeZ4CVPmB92K27uhbUJU1p1r",
        }
        leaked = {}
        for name, message in cases.items():
            cleaned = self.mod.sanitize_text(message)
            for fragment in (
                "hunter2primary",
                "abcdef0123456789xyz",
                "wJalrXUtnFEMIK7MDENGbPxRfiCY",
                "6f1b9c2d4e8a0b3c5d7e9f1a",
                "ghp_ABCdef0123456789ABCdef0123456789abcd",
                "dBjftJeZ4CVPmB92K27uhbUJU1p1r",
            ):
                if fragment in message and fragment in cleaned:
                    leaked[name] = cleaned
        self.assertEqual(leaked, {}, f"pattern sweep missed: {leaked}")

    def test_persisted_jsonl_stays_parseable_after_redaction(self) -> None:
        """Redaction must not corrupt the line the harvester has to read."""
        self.mod.register_secret_value(SENTINEL)
        self.inject_every_vector(SENTINEL)
        raw = (self.workspace / "telemetry" / "events.jsonl").read_text(encoding="utf-8")
        lines = [line for line in raw.splitlines() if line.strip()]
        self.assertTrue(lines)
        for line in lines:
            json.loads(line)  # raises if a replacement ate a delimiter
        summary_path = self.workspace / "telemetry" / "run-summary.json"
        json.loads(summary_path.read_text(encoding="utf-8"))

    def test_containers_never_reach_safe_metadata(self) -> None:
        trace = self.mod.ExecutionTrace(self.workspace, "demo-v1")
        trace.event(
            "TASK_ELIGIBLE",
            "task",
            "task_eligible",
            metadata={
                "exit_code": 0,
                "count": ["a", "list"],
                "verdict": {"a": "dict"},
                "stage": "prepare",
            },
        )
        safe = self.mod.read_events(self.workspace)[0]["safe_metadata"]
        self.assertEqual(safe["exit_code"], 0)
        self.assertEqual(safe["stage"], "prepare")
        self.assertNotIn("count", safe)
        self.assertNotIn("verdict", safe)
        self.assertEqual(safe["redacted_keys"], ["count", "verdict"])


if __name__ == "__main__":
    unittest.main()
