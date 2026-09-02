"""SC-05: collect_evidence --memory-lookup is read-only and fail-closed."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from collect_evidence import memory_lookup  # noqa: E402


class MemoryLookupTests(unittest.TestCase):
    def test_fail_closed_when_graphiti_client_missing(self) -> None:
        with TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(RuntimeError) as ctx:
                memory_lookup("PICKUP", repo_root=root)
            self.assertIn("fail-closed", str(ctx.exception))

    def test_cli_memory_lookup_does_not_write_catalog(self) -> None:
        import collect_evidence as mod

        with TemporaryDirectory() as raw:
            root = Path(raw)
            catalog = root / "EVIDENCE_CATALOG.yaml"
            catalog.write_text("evidence: []\n", encoding="utf-8")
            with patch.object(
                mod,
                "memory_lookup",
                return_value={"status": "PASS", "mode": "read_only", "result": {}},
            ):
                rc = mod.main(
                    [
                        "--blueprint",
                        str(root),
                        "--evidence-id",
                        "EVID-002",
                        "--revision",
                        "deadbeef",
                        "--memory-lookup",
                        "q",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertEqual(catalog.read_text(encoding="utf-8"), "evidence: []\n")
