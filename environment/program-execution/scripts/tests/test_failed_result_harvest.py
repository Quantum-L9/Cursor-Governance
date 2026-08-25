"""RC-02 regressions: provider terminal failure results are preserved and
published durably instead of being thrown away before batch reconciliation."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

PE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PE_ROOT / "scripts/run_campaign.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Binding:
    provider_ref = "stub-provider"
    execution_profile_ref = "stub-profile"
    agent_ref = "stub-agent"
    surface = "stub-surface"


class _Probe:
    status = "PASS"
    blocked_reason = None


class _FailingPipeline:
    """Provider window that ends in a terminal FAIL with a useful receipt."""

    def _resolve_provider(self, **_kwargs):
        return _Binding(), object(), Path("/tmp")

    def _probe_provider(self, **_kwargs):
        return _Probe()

    def _execute_provider(self, **_kwargs):
        return {
            "status": "FAIL",
            "reason": "peer_execution_timeout",
            "terminal_result": {
                "changed_files": [],
                "generated_data_units": [{"unit_id": "u-1", "kind": "finding"}],
            },
            "dispatch": {"dispatch_id": "d-1"},
        }


class FailedResultHarvestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load("run_campaign_failed_harvest", SCRIPT)

    def test_provider_failure_preserves_terminal_result(self) -> None:
        contract = {"task_id": "TASK-001", "program_digest": "sha256:0", "requested_actions": []}
        with (
            patch.object(self.mod, "_peer_pipeline", return_value=_FailingPipeline()),
            patch.object(self.mod, "_peer_identity", return_value=("agent", "surface", None)),
        ):
            outcome = self.mod._run_peer_execution(Path("/tmp"), contract)
        self.assertEqual(outcome["status"], "FAIL")
        self.assertEqual(outcome["reason"], "peer_execution_timeout")
        self.assertEqual(
            outcome["receipt"]["generated_data_units"], [{"unit_id": "u-1", "kind": "finding"}]
        )
        self.assertEqual(outcome["dispatch_id"], "d-1")

    def test_dispatch_batch_records_non_pass_as_failure_with_outcome(self) -> None:
        units = [
            {"task_id": "TASK-PASS", "grant": {"lease_id": "L1"}, "contract": {}},
            {"task_id": "TASK-FAIL", "grant": {"lease_id": "L2"}, "contract": {}},
        ]

        results = {
            "TASK-PASS": {"status": "PASS", "reason": "", "receipt": {"ok": True}},
            "TASK-FAIL": {
                "status": "FAIL",
                "reason": "boom",
                "receipt": {"generated_data_units": [{"unit_id": "u-2"}]},
            },
        }
        calls: list[str] = []

        def run_by_unit(_workspace, contract_arg):
            task_id = contract_arg["task_id"]
            calls.append(task_id)
            return results[task_id]

        units[0]["contract"] = {"task_id": "TASK-PASS"}
        units[1]["contract"] = {"task_id": "TASK-FAIL"}
        with (
            patch.object(self.mod, "_peer_pipeline", return_value=object()),
            patch.object(self.mod, "_run_peer_execution", side_effect=run_by_unit),
        ):
            outcomes, failures = self.mod._dispatch_peer_batch(Path("/tmp"), units)
        self.assertEqual(sorted(calls), ["TASK-FAIL", "TASK-PASS"])
        self.assertIn("TASK-FAIL", failures)
        self.assertIn("provider status=FAIL (boom)", failures["TASK-FAIL"])
        self.assertNotIn("TASK-PASS", failures)
        # The failed terminal result is harvested, not discarded.
        self.assertEqual(
            outcomes["TASK-FAIL"]["receipt"]["generated_data_units"], [{"unit_id": "u-2"}]
        )
        self.assertEqual(outcomes["TASK-PASS"]["receipt"], {"ok": True})

    def test_missing_grant_still_fails_closed(self) -> None:
        units = [{"task_id": "TASK-NOGRANT", "grant": None, "contract": {}}]
        outcomes, failures = self.mod._dispatch_peer_batch(Path("/tmp"), units)
        self.assertEqual(outcomes, {})
        self.assertIn("no root autonomy grant", failures["TASK-NOGRANT"])

    def test_publish_task_outcome_failed_child_uses_terminal_receipt(self) -> None:
        published: dict = {}

        class _StubPublisher:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

            def publish(self, payload, **kwargs):
                published["payload"] = payload
                published["kwargs"] = kwargs
                return {"published": True}

        stub_module = types.SimpleNamespace(OutcomePublisher=_StubPublisher)
        original_load = self.mod._load_script

        def load_script(name, path):
            if name == "pe_generated_data_outcome_publisher":
                return stub_module
            return original_load(name, path)

        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            (workspace / "runtime").mkdir(parents=True)
            task = {"generated_data_units": [], "graph_id": "graph-1"}
            contract = {"base_sha": "a" * 40, "repository": "Quantum-L9/example"}
            with patch.object(self.mod, "_load_script", side_effect=load_script):
                self.mod.publish_task_outcome(
                    workspace,
                    "campaign-1",
                    task,
                    "TASK-FAIL",
                    contract,
                    None,
                    None,
                    trace=None,
                    terminal_receipt={
                        "generated_data_units": [{"unit_id": "u-3"}],
                        "claimed_status": "failed",
                    },
                    failure_reason="provider status=FAIL (boom)",
                )
            source = json.loads(
                (workspace / "runtime" / "TASK-FAIL.generated-data.source.json").read_text()
            )
            publication = json.loads(
                (workspace / "runtime" / "TASK-FAIL.generated-data.json").read_text()
            )
        self.assertEqual(source["verdict"], "FAILED")
        self.assertEqual(source["failure_reason"], "provider status=FAIL (boom)")
        # Reusable evidence comes from the preserved terminal receipt.
        self.assertEqual(source["generated_data_units"], [{"unit_id": "u-3"}])
        self.assertEqual(published["payload"]["verdict"], "FAILED")
        self.assertFalse(published["kwargs"]["independent_validation_present"])
        self.assertEqual(publication, {"published": True})


if __name__ == "__main__":
    unittest.main()
