"""Behavior of GATE-S0-BASELINE-CHARACTERIZED in both of its states.

The merged state is unreachable from this branch -- ``pinned_to_main`` cannot
be set until W7 lands on ``origin/main`` -- so it is proven here by fixture or
it is never proven at all. The unmet state is asserted against the live
registry, because a gate that only ever runs against fixtures says nothing
about the repository it guards.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

PE_ROOT = Path(__file__).resolve().parents[2]
GATE = PE_ROOT / "scripts/gate_s0_baseline.py"
HARDENING = PE_ROOT / "tests/hardening"
REGISTRY = PE_ROOT / "conformance/counterexamples/v2-gaps-registry.yaml"

MERGE_SHA = "a" * 40


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load("pes_gate_s0_baseline_under_test", GATE)


def _verdicts(conditions) -> dict[str, bool]:
    return {item.id: item.passed for item in conditions}


def _detail(conditions, condition_id: str) -> str:
    return next(item.detail for item in conditions if item.id == condition_id)


class LiveTreeTests(unittest.TestCase):
    """What the gate says about this repository, right now."""

    def test_only_the_main_pin_is_outstanding(self) -> None:
        conditions = gate.evaluate(verify_ancestry=False)
        unmet = [item.id for item in conditions if not item.passed]
        self.assertEqual(
            unmet,
            ["pinned_to_main"],
            "S0 is characterized; the only thing left is the merge pin",
        )

    def test_the_outstanding_condition_says_what_to_do(self) -> None:
        conditions = gate.evaluate(verify_ancestry=False)
        self.assertIn("pinned_to_main", _detail(conditions, "pinned_to_main"))

    def test_recorded_digest_is_the_live_reproduction_surface(self) -> None:
        registry = gate.load_registry()
        self.assertEqual(
            registry["baseline"]["characterized_reproduction_digest"],
            gate.reproduction_digest(registry, HARDENING),
        )


class FixtureStateTests(unittest.TestCase):
    """States this branch cannot reach, held by fixture."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.hardening = self.tmp / "hardening"
        shutil.copytree(HARDENING, self.hardening)
        self.registry_path = self.tmp / "registry.yaml"
        self.registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        self._write(self.registry)

    def _write(self, registry: dict) -> None:
        self.registry_path.write_text(yaml.safe_dump(registry), encoding="utf-8")

    def _mutate(self, **baseline_fields) -> dict:
        registry = copy.deepcopy(self.registry)
        registry["baseline"].update(baseline_fields)
        registry["baseline"]["characterized_reproduction_digest"] = gate.reproduction_digest(
            registry, self.hardening
        )
        return registry

    def _evaluate(self, registry: dict):
        self._write(registry)
        return gate.evaluate(
            registry_path=self.registry_path,
            hardening=self.hardening,
            verify_ancestry=False,
        )

    def test_merged_state_passes_every_condition(self) -> None:
        conditions = self._evaluate(self._mutate(pinned_to_main=MERGE_SHA))
        self.assertTrue(
            all(item.passed for item in conditions),
            f"unmet: {[i.id for i in conditions if not i.passed]}",
        )

    def test_malformed_main_pin_is_refused(self) -> None:
        conditions = self._evaluate(self._mutate(pinned_to_main="HEAD"))
        self.assertFalse(_verdicts(conditions)["pinned_to_main"])
        self.assertIn("not a 40-character", _detail(conditions, "pinned_to_main"))

    def test_forensic_commit_cannot_be_presented_as_the_characterized_pin(self) -> None:
        forensic = self.registry["baseline"]["forensic_commit"]
        conditions = self._evaluate(self._mutate(characterized_at=forensic))
        self.assertFalse(_verdicts(conditions)["forensic_pin_not_live"])
        self.assertIn("evidence, not a live pin", _detail(conditions, "forensic_pin_not_live"))

    def test_forensic_commit_cannot_be_presented_as_the_main_pin(self) -> None:
        forensic = self.registry["baseline"]["forensic_commit"]
        conditions = self._evaluate(self._mutate(pinned_to_main=forensic))
        self.assertFalse(_verdicts(conditions)["forensic_pin_not_live"])

    def test_forensic_pin_unbound_from_the_legacy_field_is_refused(self) -> None:
        registry = self._mutate(forensic_commit="b" * 40)
        conditions = self._evaluate(registry)
        self.assertFalse(_verdicts(conditions)["forensic_pin_not_live"])
        self.assertIn("baseline_commit", _detail(conditions, "forensic_pin_not_live"))

    def test_edited_counterexample_is_caught_as_drift(self) -> None:
        """Re-characterization is required when the reproduction surface moves."""
        registry = self._mutate(pinned_to_main=MERGE_SHA)
        self._write(registry)
        target = self.hardening / "test_hardening_leases.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
        conditions = gate.evaluate(
            registry_path=self.registry_path,
            hardening=self.hardening,
            verify_ancestry=False,
        )
        self.assertFalse(_verdicts(conditions)["reproduction_not_drifted"])
        self.assertIn(
            "moved since characterization",
            _detail(conditions, "reproduction_not_drifted"),
        )

    def test_missing_test_file_is_a_reproduction_failure_not_a_drift_report(self) -> None:
        registry = self._mutate(pinned_to_main=MERGE_SHA)
        self._write(registry)
        (self.hardening / "test_hardening_gates.py").unlink()
        conditions = gate.evaluate(
            registry_path=self.registry_path,
            hardening=self.hardening,
            verify_ancestry=False,
        )
        verdicts = _verdicts(conditions)
        self.assertFalse(verdicts["counterexamples_reproduce"])
        self.assertIn("CE-GATE-001", _detail(conditions, "counterexamples_reproduce"))

    def test_conditions_are_independent(self) -> None:
        """One unmet condition must not mask another."""
        registry = copy.deepcopy(self.registry)
        registry["baseline"]["characterized_reproduction_digest"] = "sha256:" + "0" * 64
        conditions = self._evaluate_raw(registry)
        verdicts = _verdicts(conditions)
        self.assertFalse(verdicts["reproduction_not_drifted"])
        self.assertFalse(verdicts["pinned_to_main"])

    def _evaluate_raw(self, registry: dict):
        self._write(registry)
        return gate.evaluate(
            registry_path=self.registry_path,
            hardening=self.hardening,
            verify_ancestry=False,
        )

    def test_absent_baseline_block_still_reports_reproduction(self) -> None:
        registry = copy.deepcopy(self.registry)
        del registry["baseline"]
        conditions = self._evaluate_raw(registry)
        verdicts = _verdicts(conditions)
        self.assertFalse(verdicts["baseline_block_present"])
        self.assertIn("counterexamples_reproduce", verdicts)

    def test_incomplete_baseline_block_names_the_missing_keys(self) -> None:
        registry = copy.deepcopy(self.registry)
        del registry["baseline"]["orchestrator_plane_a"]
        conditions = self._evaluate_raw(registry)
        self.assertFalse(_verdicts(conditions)["baseline_block_present"])
        self.assertIn("orchestrator_plane_a", _detail(conditions, "baseline_block_present"))

    def test_unreadable_registry_fails_closed(self) -> None:
        missing = self.tmp / "absent.yaml"
        conditions = gate.evaluate(
            registry_path=missing,
            hardening=self.hardening,
            verify_ancestry=False,
        )
        self.assertEqual([item.id for item in conditions], ["registry_parses"])
        self.assertFalse(conditions[0].passed)


class RenderTests(unittest.TestCase):
    def test_json_report_names_the_unmet_conditions(self) -> None:
        conditions = gate.evaluate(verify_ancestry=False)
        payload = json.loads(gate.render(conditions, as_json=True))
        self.assertEqual(payload["gate"], gate.GATE_ID)
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["unmet"], ["pinned_to_main"])

    def test_text_report_marks_each_condition(self) -> None:
        conditions = gate.evaluate(verify_ancestry=False)
        text = gate.render(conditions, as_json=False)
        self.assertIn(gate.GATE_ID, text)
        self.assertIn("[FAIL] pinned_to_main", text)
        self.assertIn("BLOCKED: pinned_to_main", text)


if __name__ == "__main__":
    unittest.main()
