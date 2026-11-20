"""Catalog evidence is either admission evidence or the output of an earlier task."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGNS = PE_ROOT / "campaigns"


def _load():
    path = PE_ROOT / "scripts" / "evidence_causality.py"
    spec = importlib.util.spec_from_file_location("evidence_causality_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


causality = _load()


def _task(task_id: str, inputs: list[str], gates: list[str] | None = None) -> dict:
    return {
        "id": task_id,
        "input_evidence_ids": inputs,
        "completion_gate_ids": gates or [],
    }


def _evidence(evidence_id: str, freshness: str, supports: list[str] | None = None) -> dict:
    return {
        "id": evidence_id,
        "freshness": freshness,
        "supports": supports or [],
        "producer": "controller",
    }


class EvidenceCausalityTest(unittest.TestCase):
    def test_task_cannot_consume_evidence_collected_at_itself(self) -> None:
        errors = causality.evidence_input_errors(
            [_task("TASK-001", ["EVID-001", "EVID-002"])],
            [
                _evidence("EVID-001", "bound_at_source_authoring"),
                _evidence("EVID-002", "collect_at_task_001"),
            ],
            [],
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("TASK-001", errors[0])
        self.assertIn("EVID-002", errors[0])
        self.assertIn("own output", errors[0])

    def test_predecessor_pass_can_satisfy_a_later_catalog_input(self) -> None:
        errors = causality.evidence_input_errors(
            [
                _task("TASK-001", ["EVID-001"], ["GATE-001"]),
                _task("TASK-002", ["EVID-001", "EVID-002"]),
            ],
            [
                _evidence("EVID-001", "collect_at_admission"),
                _evidence("EVID-002", "collect_at_task_001"),
            ],
            [{"from": "TASK-001", "to": "TASK-002"}],
        )
        self.assertEqual(errors, [])

    def test_no_earlier_task_can_record_the_catalog_id(self) -> None:
        errors = causality.evidence_input_errors(
            [
                _task("TASK-001", ["EVID-001"]),
                _task("TASK-002", ["EVID-002"]),
            ],
            [
                _evidence("EVID-001", "collect_at_admission"),
                _evidence("EVID-002", "collect_at_task_003"),
            ],
            [{"from": "TASK-001", "to": "TASK-002"}],
            wave_rank={"TASK-001": 0, "TASK-002": 1, "TASK-003": 2},
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("no earlier task", errors[0])
        self.assertIn("EVID-002", errors[0])
        self.assertIn("TASK-003", errors[0])

    def test_collect_after_is_produced_by_the_gate_owner(self) -> None:
        tasks = [
            _task("TASK-002", ["EVID-001"], ["GATE-002"]),
            _task("TASK-003", ["EVID-006"], ["GATE-003"]),
        ]
        evidence = [
            _evidence("EVID-001", "collect_at_admission"),
            _evidence("EVID-006", "collect_after_core_implementation", ["GATE-002", "GATE-003"]),
        ]
        self.assertEqual(
            causality.evidence_input_errors(
                tasks,
                evidence,
                [{"from": "TASK-002", "to": "TASK-003"}],
            ),
            [],
        )
        circular = causality.evidence_input_errors(
            [_task("TASK-002", ["EVID-006"], ["GATE-002"])],
            [_evidence("EVID-006", "collect_after_core_implementation", ["GATE-002"])],
            [],
        )
        self.assertEqual(len(circular), 1)
        self.assertIn("no earlier task", circular[0])

    def test_admission_input_on_every_task_is_not_a_cycle(self) -> None:
        gates = ["GATE-001", "GATE-002"]
        errors = causality.errors_for_campaign_source(
            {
                "evidence_requirements": [
                    _evidence("EVID-001", "collect_at_admission", gates),
                ],
                "tasks": [
                    _task("TASK-001", ["EVID-001"], ["GATE-001"]),
                    _task("TASK-002", ["EVID-001"], ["GATE-002"]),
                ],
                "dependency_edges": [{"from": "TASK-001", "to": "TASK-002"}],
                "waves": [
                    {"id": "W0", "task_ids": ["TASK-001"], "predecessor_wave_ids": []},
                    {
                        "id": "W1",
                        "task_ids": ["TASK-002"],
                        "predecessor_wave_ids": ["W0"],
                    },
                ],
            }
        )
        self.assertEqual(errors, [])

    def test_legacy_catalog_without_freshness_is_not_refused(self) -> None:
        errors = causality.evidence_input_errors(
            [_task("TASK-002", ["EVID-002"])],
            [{"id": "EVID-002", "producer": "controller", "supports": []}],
            [],
        )
        self.assertEqual(errors, [])

    def test_passed_task_marks_the_catalog_id_it_produced(self) -> None:
        tasks = [_task("TASK-001", ["EVID-001"], ["GATE-001"])]
        items = [
            {**_evidence("EVID-001", "collect_at_admission"), "status": "planned"},
            {
                **_evidence("EVID-002", "collect_at_task_001"),
                "status": "planned",
                "result": "INFORMATIONAL",
                "revision": "UNKNOWN",
            },
            {"id": "EVID-RUNTIME-TASK-001-001", "status": "available"},
        ]
        updates = causality.catalog_updates_for_passed_task(
            items,
            "TASK-001",
            tasks,
            revision="abc123",
            source="receipts/verify.json",
            produced_at="2026-11-19T00:00:00Z",
            digest="a" * 64,
        )
        self.assertEqual([item["id"] for item in updates], ["EVID-002"])
        self.assertEqual(updates[0]["status"], "available")
        self.assertEqual(updates[0]["result"], "PASS")
        self.assertEqual(updates[0]["revision"], "abc123")

    def test_level3_source_is_circular_and_admission_campaigns_are_not(self) -> None:
        level3 = yaml.safe_load(
            (CAMPAIGNS / "COMPLETED/level3-make-pr-single-path/CAMPAIGN_SOURCE.yaml").read_text(
                encoding="utf-8"
            )
        )
        level3_errors = causality.errors_for_campaign_source(level3)
        self.assertTrue(any("EVID-002" in error and "TASK-001" in error for error in level3_errors))

        bounded = yaml.safe_load(
            (CAMPAIGNS / "bounded-replanning-v1/CAMPAIGN_SOURCE.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(causality.errors_for_campaign_source(bounded), [])

        hydration = yaml.safe_load(
            (CAMPAIGNS / "session-runtime-hydration-convergence-v2/CAMPAIGN_SOURCE.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(causality.errors_for_campaign_source(hydration), [])


if __name__ == "__main__":
    unittest.main()
