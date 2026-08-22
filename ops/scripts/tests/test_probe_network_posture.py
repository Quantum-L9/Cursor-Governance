"""Narrow tests for probe_network_posture so scoped pr-check infers this file."""

from __future__ import annotations

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_network_posture as posture  # noqa: E402


class ProbeNetworkPostureTests(unittest.TestCase):
    def test_reachable_true_on_http_error(self) -> None:
        with patch.object(
            posture,
            "https_exchange",
            side_effect=urllib.error.HTTPError("https://x/", 403, "no", None, None),
        ):
            self.assertTrue(posture.reachable("github.com", timeout=1))

    def test_reachable_false_on_url_error(self) -> None:
        with patch.object(
            posture,
            "https_exchange",
            side_effect=urllib.error.URLError("blocked"),
        ):
            self.assertFalse(posture.reachable("app.infisical.com", timeout=1))

    def test_run_ok_when_required_open_and_forbidden_blocked(self) -> None:
        def _fake(host: str, timeout: int = 10) -> bool:
            return host in posture.MUST_REACH

        with patch.object(posture, "reachable", side_effect=_fake):
            result = posture.run(timeout=1)
        self.assertTrue(result["ok"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["missing_required"], [])


if __name__ == "__main__":
    unittest.main()
