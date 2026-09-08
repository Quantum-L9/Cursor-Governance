"""MemoryCandidate ingress goes through the canonical control plane (stage C10)."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

ADAPTER = Path(__file__).resolve().parents[1] / "adapters" / "ingest_memory_candidate.py"
REPO = Path(__file__).resolve().parents[4]


def _load():
    spec = importlib.util.spec_from_file_location("sgd_ingest_memory_candidate", ADAPTER)
    if spec is None or spec.loader is None:
        raise RuntimeError(ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate() -> dict:
    return {
        "kind": "MemoryCandidate",
        "candidate_id": "memcand-testdryrun00000001",
        "source": {
            "agent_id": "cursor",
            "campaign_id": "campaign-1",
            "action_id": "TASK-1",
            "packet_id": "packet-1",
        },
        "knowledge": {
            "unit_id": "unit-1",
            "statement": "Task TASK-1 changed files: README.md",
            "primary_class": "implementation_surface",
        },
    }


class _Receipt:
    def __init__(self, status: str = "admitted") -> None:
        self.status = status
        self.record_id = "rec-1" if status in {"admitted", "duplicate"} else None
        self.receipt_id = "wr-1"
        self.admission_reasons = ("ok",)
        self.warnings = ()


class _Outcome:
    def __init__(self, status: str = "admitted") -> None:
        self.receipt = _Receipt(status)
        self.status = types.SimpleNamespace(value="OK")
        self.ok = status in {"admitted", "duplicate"}
        self.error = None


class _Client:
    def __init__(self, status: str = "admitted") -> None:
        self.binding = types.SimpleNamespace(ok=True, reasons=())
        self.calls: list[dict[str, Any]] = []
        self._status = status

    def write(self, content: str, **kwargs: Any) -> _Outcome:
        self.calls.append({"content": content, **kwargs})
        return _Outcome(self._status)


class IngestMemoryCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load()
        self.client = _Client()

    def test_dry_run_calls_no_memory(self) -> None:
        result = self.module.ingest_candidate(
            _candidate(), dry_run=True, client=self.client, workspace=REPO
        )
        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["group_id"], "cursor-governance")
        self.assertEqual(self.client.calls, [])

    def test_write_crosses_the_control_plane_with_an_idempotency_key(self) -> None:
        result = self.module.ingest_candidate(_candidate(), client=self.client, workspace=REPO)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["memory_id"], "rec-1")
        call = self.client.calls[0]
        self.assertEqual(call["namespace"], "cursor-governance")
        self.assertEqual(call["memory_class"], "insight")
        self.assertEqual(call["idempotency_key"], "sgd:memcand-testdryrun00000001")
        self.assertIn("sgd", call["tags"])
        self.assertIn("implementation_surface", call["tags"])
        self.assertEqual(call["source"], "generated-data")

    def test_duplicate_is_reported_as_deduplicated(self) -> None:
        client = _Client(status="duplicate")
        result = self.module.ingest_candidate(_candidate(), client=client, workspace=REPO)
        self.assertEqual(result["status"], "deduplicated")

    def test_rejected_verdict_is_visible_not_a_success(self) -> None:
        client = _Client(status="rejected")
        result = self.module.ingest_candidate(_candidate(), client=client, workspace=REPO)
        self.assertEqual(result["status"], "rejected")

    def test_main_dry_run_reads_stdin(self) -> None:
        stdin = types.SimpleNamespace(buffer=io.BytesIO(json.dumps(_candidate()).encode("utf-8")))
        stdout = io.StringIO()
        with patch.object(sys, "stdin", stdin), patch.object(sys, "stdout", stdout):
            code = self.module.main(["--dry-run", "--workspace", str(REPO)])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "accepted")

    def test_recorded_repository_maps_to_registry_namespace(self) -> None:
        candidate = _candidate()
        candidate["source"]["repository"] = "Quantum-L9/Cursor-Governance"
        result = self.module.ingest_candidate(
            candidate, dry_run=True, client=self.client, workspace=REPO
        )
        self.assertEqual(result["group_id"], "cursor-governance")

    def test_unknown_repository_fails_closed(self) -> None:
        candidate = _candidate()
        candidate["source"]["repository"] = "Quantum-L9/does-not-exist"
        with self.assertRaises(RuntimeError):
            self.module.ingest_candidate(
                candidate, dry_run=True, client=self.client, workspace=REPO
            )
        self.assertEqual(self.client.calls, [])

    def test_no_provider_client_is_imported(self) -> None:
        src = ADAPTER.read_text(encoding="utf-8")
        # Assembled from parts: this file sits outside tests/ and is scanned too.
        provider_tool = "add_" + "memory"
        for forbidden in ("graphiti_memory_client", "episode_contract", provider_tool, "call_tool"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
