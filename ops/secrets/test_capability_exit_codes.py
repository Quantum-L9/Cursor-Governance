#!/usr/bin/env python3
"""Capability survey exit codes distinguish "fix it" from "you cannot" (INV-4).

Covers audit findings B-10, B-19 and acceptance tests T-02, T-03, T-04, T-36.

Two defects meet here. `--check` without `--require` used to `return 0`
unconditionally, so a caller surveying the plane read a total outage as success
(B-19). And `status()` tested the broker URL before the session identity, so a
runtime that can NEVER mint a broker-verifiable identity was reported as "no
broker configured" — which reads as a missing environment field and sent
operators to fix something no field can fix (B-10).

Environments are constructed explicitly rather than inherited, so these assert
on the classifier rather than on whatever the host session happens to be.
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
        """A misconfigured self-hosted runtime has a remedy; a hosted one does not."""
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


class StatusPrecedenceTests(unittest.TestCase):
    """T-36: identity is evaluated before the broker URL, and the order matters."""

    def test_hosted_surface_is_blocked_not_degraded_even_with_a_broker_url(self) -> None:
        client = CapabilityClient(env=hosted_env(L9_CAPABILITY_BROKER_URL="https://broker.test"))
        status = client.status("sonar.read_issues")
        self.assertEqual(status.status, BLOCKED_BY_PLATFORM)

    def test_hosted_surface_is_never_reported_as_no_broker_configured(self) -> None:
        """The precise misdirection the audit observed."""
        client = CapabilityClient(env=hosted_env())
        status = client.status("sonar.read_issues")
        self.assertEqual(status.status, BLOCKED_BY_PLATFORM)
        self.assertNotIn("no broker configured", status.detail)

    def test_identified_runtime_without_a_broker_is_degraded(self) -> None:
        """With an identity in hand, a missing URL IS the operator's to fix."""
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("token-material")
            path = handle.name
        client = CapabilityClient(env={**BASE_ENV, "L9_WORKLOAD_IDENTITY_TOKEN_FILE": path})
        status = client.status("sonar.read_issues")
        self.assertEqual(status.status, DEGRADED)
        self.assertIn("no broker configured", status.detail)
        Path(path).unlink()

    def test_unregistered_capability_is_unavailable(self) -> None:
        client = CapabilityClient(env=hosted_env())
        self.assertEqual(client.status("nope.not_a_capability").status, "UNAVAILABLE")


class ExitCodeTests(unittest.TestCase):
    """T-02, T-03, T-04. main() reads os.environ, so each case patches it."""

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

    def test_blocked_by_platform_exits_4(self) -> None:
        self.assertEqual(self._main(["--check"], hosted_env()), EXIT_BLOCKED_BY_PLATFORM)

    def test_degraded_exits_3(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("token-material")
            path = handle.name
        env = {**BASE_ENV, "L9_WORKLOAD_IDENTITY_TOKEN_FILE": path}
        self.assertEqual(self._main(["--check"], env), EXIT_DEGRADED)
        Path(path).unlink()

    def test_allow_degraded_exits_0_and_names_what_it_tolerated(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("token-material")
            path = handle.name
        env = {**BASE_ENV, "L9_WORKLOAD_IDENTITY_TOKEN_FILE": path}
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rc = self._main(["--check", "--allow-degraded"], env)
        self.assertEqual(rc, EXIT_OK)
        self.assertIn("tolerated (--allow-degraded):", buffer.getvalue())
        self.assertIn("sonar.read_issues", buffer.getvalue())
        Path(path).unlink()

    def test_allow_degraded_does_not_rescue_blocked_by_platform(self) -> None:
        """INV-4: a state this repository cannot repair never exits 0."""
        self.assertEqual(
            self._main(["--check", "--allow-degraded"], hosted_env()),
            EXIT_BLOCKED_BY_PLATFORM,
        )

    def test_require_preserves_the_legacy_contract(self) -> None:
        self.assertEqual(self._main(["--check", "--require", "sonar.read_issues"], hosted_env()), 1)

    def test_survey_prints_the_platform_block_detail(self) -> None:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self._main(["--check"], hosted_env())
        printed = buffer.getvalue()
        self.assertIn(f"state={BLOCKED_BY_PLATFORM}", printed)
        self.assertIn("reason=hosted_surface_issues_no_session_identity", printed)
        self.assertIn("remediation=none_available_in_repo", printed)
        self.assertIn("tracking=", printed)


class VocabularyTests(unittest.TestCase):
    def test_status_words_are_distinct(self) -> None:
        self.assertNotEqual(ENABLED, DEGRADED)
        self.assertNotEqual(DEGRADED, BLOCKED_BY_PLATFORM)
        self.assertNotEqual(EXIT_DEGRADED, EXIT_BLOCKED_BY_PLATFORM)


if __name__ == "__main__":
    unittest.main()
