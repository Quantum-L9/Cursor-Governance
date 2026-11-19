#!/usr/bin/env python3
"""Positive and known-bad packet tests for the campaign ZIP verification scope."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from verify_series import (  # noqa: E402
    ROOT,
    validate_gate_graph,
    validate_phase_launch,
    validate_root,
    validate_writer_ownership,
)


def phase(n: str) -> dict:
    return json.loads((ROOT / "phases" / n / "CAMPAIGN.json").read_text())


class SeriesNegativeControls(unittest.TestCase):
    def test_positive_full_artifact(self):
        validate_root(ROOT)

    def test_reject_same_file_two_agents(self):
        spec = phase("P4_Full_Loop")
        shared = "app/engines/enrichment_sweep.py"
        doc = next(lane for lane in spec["lanes"] if lane["id"] == "DOC")
        doc["write_paths"]["https://github.com/Quantum-L9/Enrichment.Inference.Engine"].append(
            shared
        )
        with self.assertRaisesRegex(ValueError, "write-scope collision"):
            validate_writer_ownership(spec)

    def test_reject_wildcard_docs_collision(self):
        spec = phase("P0_Domain_Docs")
        writer = next(lane for lane in spec["lanes"] if lane["id"] == "ESPEC")
        writer["write_paths"]["https://github.com/Quantum-L9/Enrichment.Inference.Engine"].append(
            "docs/adr/ADR-999-new.md"
        )
        with self.assertRaisesRegex(ValueError, "write-scope collision"):
            validate_writer_ownership(spec)

    def test_reject_makefile(self):
        spec = phase("P4_Full_Loop")
        writer = next(lane for lane in spec["lanes"] if lane["id"] == "SWEEP")
        writer["write_paths"]["https://github.com/Quantum-L9/Enrichment.Inference.Engine"].append(
            "Makefile"
        )
        with self.assertRaisesRegex(ValueError, "forbidden Makefile"):
            validate_writer_ownership(spec)

    def test_reject_repo_make_implementation(self):
        spec = phase("P4_Full_Loop")
        writer = next(lane for lane in spec["lanes"] if lane["id"] == "SWEEP")
        writer["write_paths"]["https://github.com/Quantum-L9/Enrichment.Inference.Engine"].append(
            "Repo.mk"
        )
        with self.assertRaisesRegex(ValueError, "forbidden Repo.mk"):
            validate_writer_ownership(spec)

    def test_reject_repo_scope_expansion(self):
        spec = phase("P0_Domain_Docs")
        writer = next(lane for lane in spec["lanes"] if lane["id"] == "DOC")
        writer["write_paths"]["https://github.com/Quantum-L9/.github"] = [
            "semantics/invariants.yaml"
        ]
        writer["writable_repositories"].append("https://github.com/Quantum-L9/.github")
        with self.assertRaisesRegex(ValueError, "out-of-scope writable"):
            validate_writer_ownership(spec)

    def test_reject_missing_e2e_publication_gate(self):
        spec = phase("P4_Full_Loop")
        pub = next(g for g in spec["gates"] if g["id"] == "G_PUBLISH")
        pub["depends_on"].remove("G_E2E_CODE")
        with self.assertRaisesRegex(ValueError, "prepublication predecessors"):
            validate_gate_graph(spec, 4)

    def test_reject_missing_doc_publication_gate(self):
        spec = phase("P4_Full_Loop")
        pub = next(g for g in spec["gates"] if g["id"] == "G_PUBLISH")
        pub["depends_on"].remove("G_DOC_PREP")
        with self.assertRaisesRegex(ValueError, "prepublication predecessors"):
            validate_gate_graph(spec, 4)

    def test_reject_docker_before_publish(self):
        spec = phase("P4_Full_Loop")
        g = next(g for g in spec["gates"] if g["id"] == "G_RAIL")
        g["depends_on"] = ["G_SWEEP"]
        with self.assertRaisesRegex(ValueError, "Docker rail must depend"):
            validate_gate_graph(spec, 4)

    def test_reject_gate_deadlock(self):
        spec = phase("P4_Full_Loop")
        g = next(g for g in spec["gates"] if g["id"] == "G_E2E_CODE")
        g["depends_on"] = ["G_RAIL"]
        with self.assertRaisesRegex(ValueError, "gate cycle"):
            validate_gate_graph(spec, 4)

    def test_reject_new_phase_activation(self):
        with self.assertRaisesRegex(ValueError, "phase incorrectly reactivates CTO"):
            validate_phase_launch(
                "**HOLD until explicit operator activation**", "Activate every phase independently"
            )

    def test_reject_path_escaping_repo(self):
        spec = phase("P2_Bidirectional_Reliability")
        writer = next(lane for lane in spec["lanes"] if lane["id"] == "OUT")
        writer["write_paths"]["https://github.com/Quantum-L9/Enrichment.Inference.Engine"].append(
            "../Makefile"
        )
        with self.assertRaisesRegex(ValueError, "invalid relative write path"):
            validate_writer_ownership(spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
