from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PairAlignmentTests(unittest.TestCase):
    def test_contract_family_and_ownership(self):
        p = yaml.safe_load(
            (ROOT / "program-execution-blueprint-template/PROGRAM.yaml").read_text()
        )["program"]
        c = yaml.safe_load(
            (ROOT / "program-execution-controller-template/CONTROLLER.yaml").read_text()
        )["controller"]
        self.assertEqual(p["contracts"]["pair"], "program-execution-system.v2")
        self.assertEqual(c["contracts"]["pair"], "program-execution-system.v2")
        self.assertEqual(c["contracts"]["blueprint"], p["contracts"]["blueprint"])

    def test_runtime_fields_do_not_leak_into_blueprint(self):
        tasks = yaml.safe_load(
            (ROOT / "program-execution-blueprint-template/TASK_CARDS.yaml").read_text()
        )["tasks"]
        gates = yaml.safe_load(
            (ROOT / "program-execution-blueprint-template/CONVERGENCE_GATES.yaml").read_text()
        )["gates"]
        self.assertTrue(
            all(not ({"status", "runtime_state", "depends_on"} & set(t)) for t in tasks)
        )
        self.assertTrue(all(not ({"status", "result"} & set(g)) for g in gates))

    def test_rendered_contract_schema_identity(self):
        s = json.loads(
            (
                ROOT / "program-execution-controller-template/schemas/task-contract.schema.json"
            ).read_text()
        )
        self.assertEqual(s["$id"], "program-execution-controller.rendered-contract.v2")
        self.assertEqual(s["properties"]["schema"]["const"], s["$id"])


if __name__ == "__main__":
    unittest.main()
