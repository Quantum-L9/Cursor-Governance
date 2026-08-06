from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.common.imports import load_module


class BootstrapStatusProbeTests(unittest.TestCase):
    def test_probe_is_read_only_and_compact(self) -> None:
        root = Path(__file__).resolve().parents[1]
        probe_module = load_module(
            root / "status_probe.py",
            "pes_test_bootstrap_status_probe",
        )
        render_module = load_module(
            root / "context_renderer.py",
            "pes_test_bootstrap_context_renderer",
        )
        with tempfile.TemporaryDirectory() as directory:
            status = Path(directory) / "program-1/status/PROGRAM_STATUS.json"
            status.parent.mkdir(parents=True)
            status.write_text(json.dumps({"program_id": "program-1", "state": "RUNNING"}))
            value = probe_module.probe_programs(directory)
            rendered = render_module.render_context(value)
            self.assertEqual(value["active_programs"], 1)
            self.assertIn("program-1: RUNNING", rendered)


if __name__ == "__main__":
    unittest.main()
