"""The gh auth probe exercises an authenticated API call, never `gh auth status`."""

from __future__ import annotations

import unittest
from unittest import mock

from adapters.github.common import auth_probe, gh_transport


class _Result:
    def __init__(self, exit_code: int, stdout: str) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = ""
        self.stdout_digest = "sha256:" + "0" * 64
        self.stderr_digest = "sha256:" + "0" * 64


class AuthProbeTests(unittest.TestCase):
    def _probe(self, result: _Result) -> tuple[dict, list[list[str]]]:
        calls: list[list[str]] = []

        def fake_run(self, argv, timeout_seconds=120):
            calls.append(list(argv))
            return result

        with (
            mock.patch.object(gh_transport.GhTransport, "run", fake_run),
            mock.patch.object(auth_probe.shutil, "which", return_value="/usr/bin/gh"),
        ):
            return auth_probe.probe("."), calls

    def test_pass_requires_an_authenticated_login(self) -> None:
        report, calls = self._probe(_Result(0, '{"login": "openclaw-igorbot"}'))
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(calls, [["api", "user"]])

    def test_exit_zero_without_a_login_is_blocked(self) -> None:
        report, _ = self._probe(_Result(0, "not json"))
        self.assertEqual(report["status"], "BLOCKED")

    def test_never_gates_on_auth_status(self) -> None:
        _, calls = self._probe(_Result(1, ""))
        self.assertTrue(all("auth" not in argv for argv in calls), calls)


if __name__ == "__main__":
    unittest.main()
