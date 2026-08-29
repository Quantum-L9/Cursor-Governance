#!/usr/bin/env python3
"""Capability survey exit codes after broker retirement.

The capability-broker experiment never shipped. Registered capabilities report
UNAVAILABLE (survey exit 3). --require still exits 1 when nothing is ENABLED.
--allow-degraded still exits 0 for UNAVAILABLE. Hosted identity classification
is diagnostic only — it does not change capability status to BLOCKED_BY_PLATFORM.

Environments are constructed explicitly rather than inherited.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from capability_client import (  # noqa: E402
    BLOCKED_BY_PLATFORM,
    DEGRADED,
    ENABLED,
    EXIT_BLOCKED_BY_PLATFORM,
    EXIT_DEGRADED,
    EXIT_OK,
    UNAVAILABLE,
    CapabilityClient,
    main,
    session_identity,
)

BASE_ENV = {
    "L9_GOVERNANCE_SURFACE": "claude-code",
    "HOME": "/nonexistent",
}


def hosted_env(**extra: str) -> dict[str, str]:
    """Anthropic-hosted cloud_default: no identity is obtainable, ever."""
    return {**BASE_ENV, "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default", **extra}


class SessionIdentityTests(unittest.TestCase):
    def test_hosted_surface_is_classified_non_retryable(self) -> None:
        identity = session_identity(hosted_env())
        self.assertFalse(identity.available)
        self.assertEqual(identity.reason, "hosted_surface_issues_no_session_identity")
        self.assertEqual(identity.remediation, "none_available_in_repo")
        self.assertTrue(identity.tracking)

    def test_unknown_runtime_is_classified_separately(self) -> None:
        identity = session_identity(BASE_ENV)
        self.assertFalse(identity.available)
        self.assertNotEqual(identity.reason, "hosted_surface_issues_no_session_identity")
        self.assertNotEqual(identity.remediation, "none_available_in_repo")

    def test_workload_identity_file_is_accepted(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".jwt", delete=False) as handle:
            handle.write("token-material")
            path = handle.name
        identity = session_identity({**BASE_ENV, "L9_WORKLOAD_IDENTITY_TOKEN_FILE": path})
        self.assertTrue(identity.available)
        self.assertEqual(identity.method, "workload-identity-jwt")
        Path(path).unlink()


class RetiredStatusTests(unittest.TestCase):
    def test_registered_capability_is_unavailable_even_with_a_broker_url(self) -> None:
        client = CapabilityClient(env=hosted_env(L9_CAPABILITY_BROKER_URL="https://broker.test"))
        status = client.status("sonar.read_issues")
        self.assertEqual(status.status, UNAVAILABLE)
        self.assertIn("retired", status.detail)

    def test_hosted_surface_is_never_reported_as_no_broker_configured(self) -> None:
        client = CapabilityClient(env=hosted_env())
        status = client.status("sonar.read_issues")
        self.assertEqual(status.status, UNAVAILABLE)
        self.assertNotIn("no broker configured", status.detail)

    def test_identity_does_not_enable_a_retired_broker(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("token-material")
            path = handle.name
        client = CapabilityClient(env={**BASE_ENV, "L9_WORKLOAD_IDENTITY_TOKEN_FILE": path})
        status = client.status("sonar.read_issues")
        self.assertEqual(status.status, UNAVAILABLE)
        self.assertNotEqual(status.status, ENABLED)
        Path(path).unlink()

    def test_unregistered_capability_is_unavailable(self) -> None:
        client = CapabilityClient(env=hosted_env())
        self.assertEqual(client.status("nope.not_a_capability").status, UNAVAILABLE)


class ExitCodeTests(unittest.TestCase):
    def _main(self, argv: list[str], env: dict[str, str]) -> int:
        import os

        saved = dict(os.environ)
        os.environ.clear()
        os.environ.update(env)
        try:
            return main(argv)
        finally:
            os.environ.clear()
            os.environ.update(saved)

    def test_survey_exits_degraded_not_blocked(self) -> None:
        self.assertEqual(self._main(["--check"], hosted_env()), EXIT_DEGRADED)

    def test_allow_degraded_exits_0_and_names_what_it_tolerated(self) -> None:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = self._main(["--check", "--allow-degraded"], hosted_env())
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("tolerated (--allow-degraded):", buffer.getvalue())
        self.assertIn("sonar.read_issues", buffer.getvalue())

    def test_require_preserves_the_legacy_contract(self) -> None:
        self.assertEqual(self._main(["--check", "--require", "sonar.read_issues"], hosted_env()), 1)

    def test_survey_prints_retired_not_platform_block(self) -> None:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self._main(["--check"], hosted_env())
        printed = buffer.getvalue()
        self.assertIn("broker=retired", printed)
        self.assertNotIn(f"state={BLOCKED_BY_PLATFORM}", printed)


class VocabularyTests(unittest.TestCase):
    def test_status_words_are_distinct(self) -> None:
        self.assertNotEqual(ENABLED, DEGRADED)
        self.assertNotEqual(DEGRADED, BLOCKED_BY_PLATFORM)
        self.assertNotEqual(UNAVAILABLE, ENABLED)
        self.assertNotEqual(EXIT_DEGRADED, EXIT_BLOCKED_BY_PLATFORM)


if __name__ == "__main__":
    unittest.main()
