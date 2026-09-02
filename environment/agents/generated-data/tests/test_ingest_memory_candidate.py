from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ADAPTER = Path(__file__).resolve().parents[1] / "adapters" / "ingest_memory_candidate.py"


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


def _install_client_fake(*, group_id: str = "cursor-governance") -> list:
    calls: list = []
    client = types.ModuleType("ops.graphiti.graphiti_memory_client")
    client.call_tool = lambda *args, **kwargs: calls.append((args, kwargs)) or {"uuid": "fake"}
    client.load_env = lambda: None
    client.resolve_group_id = lambda *_args, **_kwargs: {
        "group_id": group_id,
        "readonly": False,
    }
    client.target_repo = lambda _args: Path(".")
    sys.modules["ops.graphiti.graphiti_memory_client"] = client
    identity = types.ModuleType("ops.graphiti.hydration.identity")
    identity.resolve_write_identity = lambda **_kwargs: {
        "agent_id": "cursor",
        "user_id": "cursor_agent",
        "surface": "cursor",
    }
    identity.envelope_body = lambda body, **_kwargs: body
    sys.modules.setdefault("ops.graphiti.hydration", types.ModuleType("ops.graphiti.hydration"))
    sys.modules["ops.graphiti.hydration.identity"] = identity
    return calls


class IngestMemoryCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load()

    def test_dry_run_does_not_call_graphiti(self) -> None:
        calls = _install_client_fake()
        result = self.module.ingest_candidate(_candidate(), dry_run=True)
        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["dry_run"])
        self.assertEqual(calls, [])

    def test_main_dry_run_reads_stdin(self) -> None:
        calls = _install_client_fake()
        stdin = types.SimpleNamespace(buffer=io.BytesIO(json.dumps(_candidate()).encode("utf-8")))
        stdout = io.StringIO()
        with patch.object(sys, "stdin", stdin), patch.object(sys, "stdout", stdout):
            code = self.module.main(["--dry-run"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(calls, [])

    def test_forbidden_group_fails_closed(self) -> None:
        calls = _install_client_fake(group_id="main")
        with self.assertRaises(RuntimeError):
            self.module.ingest_candidate(_candidate(), dry_run=True)
        self.assertEqual(calls, [])

    def test_recorded_repository_maps_to_registry_group(self) -> None:
        captured: list = []

        def fake_resolve(*args, **kwargs):
            captured.append((args, kwargs))
            return {"group_id": "cursor-governance", "readonly": False}

        calls = _install_client_fake()
        client = sys.modules["ops.graphiti.graphiti_memory_client"]
        client.resolve_group_id = fake_resolve
        candidate = _candidate()
        candidate["source"]["repository"] = "Quantum-L9/Cursor-Governance"
        result = self.module.ingest_candidate(candidate, dry_run=True)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(calls, [])
        self.assertTrue(captured)
        self.assertEqual(captured[0][1].get("explicit"), "cursor-governance")

    def test_unknown_repository_fails_closed(self) -> None:
        calls = _install_client_fake()
        candidate = _candidate()
        candidate["source"]["repository"] = "Quantum-L9/does-not-exist"
        with self.assertRaises(RuntimeError):
            self.module.ingest_candidate(candidate, dry_run=True)
        self.assertEqual(calls, [])

    def test_former_github_alias_still_maps_to_group(self) -> None:
        captured: list = []

        def fake_resolve(*args, **kwargs):
            captured.append((args, kwargs))
            return {"group_id": "l9-infra", "readonly": False}

        calls = _install_client_fake()
        client = sys.modules["ops.graphiti.graphiti_memory_client"]
        client.resolve_group_id = fake_resolve
        candidate = _candidate()
        candidate["source"]["repository"] = "Quantum-L9/l9-infra"
        result = self.module.ingest_candidate(candidate, dry_run=True)
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(calls, [])
        self.assertTrue(captured)
        self.assertEqual(captured[0][1].get("explicit"), "l9-infra")


if __name__ == "__main__":
    unittest.main()
