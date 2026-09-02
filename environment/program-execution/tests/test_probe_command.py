from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from peer_execution.imports import pe_script


class ProbeCommandTests(unittest.TestCase):
    def test_probe_is_truthful_inventory_not_all_hosts_gate(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(root)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            environment["L9_PROGRAM_HOME"] = temporary
            completed = subprocess.run(
                [sys.executable, "-B", str(root / "scripts/probe_execution_adapters.py")],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["receipts"]), 12)
            self.assertGreater(report["status_counts"].get("BLOCKED", 0), 0)

    def test_executable_peer_probe_is_truthful_inventory_not_all_hosts_gate(self) -> None:
        root = Path(__file__).resolve().parents[1]
        repo = root.parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(root)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(root / "scripts/probe_executable_peers.py"),
                    "--json",
                    "--runtime",
                    temporary,
                ],
                cwd=repo,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertEqual(report["status"], "PASS", report)
            self.assertGreater(report["status_counts"].get("BLOCKED", 0), 0)
            cursor = next(peer for peer in report["peers"] if peer["agent_id"] == "cursor")
            self.assertEqual(cursor["gate"], "ok")
            self.assertTrue(cursor["bindings"])
            self.assertTrue(all(binding["status"] == "BLOCKED" for binding in cursor["bindings"]))
            self.assertNotIn("PASS", [binding["status"] for binding in cursor["bindings"]])

    def test_binding_outcome_keeps_honest_blocked_and_fails_structural(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
        _binding_outcome = pe_script("probe_executable_peers")._binding_outcome

        self.assertEqual(_binding_outcome({"status": "READY"}), "READY")
        self.assertEqual(
            _binding_outcome(
                {
                    "status": "BLOCKED",
                    "checks": {
                        "canonical_binding": "PASS",
                        "provider_conformance": "PASS",
                        "execution_profile": "PASS",
                        "provider_routable": "PASS",
                        "provider_probe": "BLOCKED",
                        "provider_probe_integrity": "PASS",
                        "autonomy_provider": "PASS",
                        "autonomy_conformance": "PASS",
                        "execution_gateway": "PASS",
                    },
                }
            ),
            "BLOCKED",
        )
        self.assertEqual(
            _binding_outcome(
                {
                    "status": "BLOCKED",
                    "checks": {
                        "canonical_binding": "FAIL",
                        "provider_probe": "BLOCKED",
                    },
                }
            ),
            "FAIL",
        )

    def test_executable_peer_probe_fails_closed_without_bindings(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root))
        probe = pe_script("probe_executable_peers").probe

        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary) / "runtime"
            report = probe(root, Path(temporary), runtime)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(report.get("errors"))


if __name__ == "__main__":
    unittest.main()
