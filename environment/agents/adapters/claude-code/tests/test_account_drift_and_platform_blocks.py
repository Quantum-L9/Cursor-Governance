#!/usr/bin/env python3
"""Account-field drift is detectable; platform blocks are classified, not faked.

Covers audit findings B-06, B-07, B-09, B-10, B-14 and acceptance tests
T-31 … T-38.

An agent cannot write the three account fields, so the goal is not repair but
DETECTION plus exact paste-ready text. And three findings are not repairable in
this repository at all — those must report a distinct non-success state rather
than being absorbed into a green banner or misreported as configuration gaps.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPO = ADAPTER.parents[3]
sys.path.insert(0, str(ADAPTER))
sys.path.insert(0, str(REPO / "ops" / "secrets"))
sys.path.insert(0, str(REPO / "ops" / "scripts"))

import probe_broker  # noqa: E402
import probe_network_posture  # noqa: E402
from verify_account_env import (  # noqa: E402
    RUNTIME_MANAGED,
    account_fields_markdown,
    compare,
    parse_env_example,
    run,
    stub_revision_actual,
    stub_revision_expected,
)

#: Exactly what the audit measured in the live runtime.
AUDITED_ENV = {
    "L9_AUTONOMY_MAX_PARALLEL": "4",
    "L9_AUTONOMY_MAX_MUTATION_LANES": "2",
    "L9_GOVERNANCE_SURFACE": "claude-code",
    # L9_CAPABILITY_BROKER_URL and CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS absent.
}


class AccountEnvDriftTests(unittest.TestCase):
    """T-32: each of the four B-07 deviations is caught individually."""

    def setUp(self) -> None:
        self.expected = parse_env_example()

    def _deviation(self, key: str, env: dict[str, str]) -> dict[str, str] | None:
        return next((d for d in compare(self.expected, env) if d["key"] == key), None)

    def test_missing_broker_url_is_caught(self) -> None:
        row = self._deviation("L9_CAPABILITY_BROKER_URL", AUDITED_ENV)
        self.assertIsNotNone(row)
        self.assertEqual(row["kind"], "missing")
        self.assertIn("broker.quantumaipartners.com", row["expected"])

    def test_missing_subagent_ceiling_is_caught(self) -> None:
        row = self._deviation("CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS", AUDITED_ENV)
        self.assertIsNotNone(row)
        self.assertEqual(row["expected"], "480")

    def test_cursor_default_parallelism_is_caught(self) -> None:
        row = self._deviation("L9_AUTONOMY_MAX_PARALLEL", AUDITED_ENV)
        self.assertIsNotNone(row)
        self.assertEqual((row["expected"], row["actual"]), ("480", "4"))

    def test_cursor_default_mutation_lanes_is_caught(self) -> None:
        row = self._deviation("L9_AUTONOMY_MAX_MUTATION_LANES", AUDITED_ENV)
        self.assertIsNotNone(row)
        self.assertEqual((row["expected"], row["actual"]), ("128", "2"))

    def test_a_matching_environment_reports_no_deviations(self) -> None:
        self.assertEqual(compare(self.expected, dict(self.expected)), [])

    def test_deliberately_absent_keys_are_never_reported_missing(self) -> None:
        """GH_TOKEN's absence is the contract, not drift."""
        for key in ("GH_TOKEN", "SONAR_TOKEN", "INFISICAL_CLIENT_SECRET"):
            self.assertNotIn(key, self.expected)

    def test_runtime_managed_keys_are_excluded(self) -> None:
        """The harness decrements spawn depth per nesting level; comparing it
        statically reports permanent drift no paste can fix."""
        self.assertIn("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH", RUNTIME_MANAGED)
        env = {**self.expected, "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"}
        self.assertEqual(compare(self.expected, env), [])


class StubRevisionTests(unittest.TestCase):
    """T-31: a pasted stub that predates HEAD is otherwise invisible."""

    def test_head_carries_a_revision(self) -> None:
        self.assertTrue(stub_revision_expected(), "setup.bootstrap.sh must stamp a revision")

    def test_mismatch_is_reported_with_both_revisions(self) -> None:
        result = run({**AUDITED_ENV, "L9_STUB_REVISION": "1999-01-01.0"})
        self.assertTrue(result["stub_drift"])
        self.assertEqual(result["stub_revision_actual"], "1999-01-01.0")
        self.assertEqual(result["stub_revision_expected"], stub_revision_expected())

    def test_unrecorded_revision_is_drift(self) -> None:
        """The audited state: a stub cached before the stamp existed."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(stub_revision_actual({}, Path(tmp) / "absent.env"), "")
        self.assertTrue(run(dict(AUDITED_ENV))["stub_drift"])

    def test_matching_revision_is_not_drift(self) -> None:
        env = {**parse_env_example(), "L9_STUB_REVISION": stub_revision_expected()}
        self.assertFalse(run(env)["stub_drift"])

    def test_stub_writes_its_revision_into_the_session_env(self) -> None:
        stub = (ADAPTER / "web" / "setup.bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("export L9_STUB_REVISION=", stub)


class AccountFieldsDocumentTests(unittest.TestCase):
    """T-33: paste-ready text plus a checksum to confirm the paste landed."""

    def test_document_carries_every_expected_key_and_a_checksum(self) -> None:
        expected = parse_env_example()
        body = account_fields_markdown(expected, "test-rev")
        for key in expected:
            self.assertIn(f"{key}=", body)
        self.assertIn("Checksum", body)
        self.assertIn("test-rev", body)

    def test_generated_document_is_committed(self) -> None:
        self.assertTrue((REPO / "docs" / "ACCOUNT_FIELDS.md").is_file())


class NetworkPostureTests(unittest.TestCase):
    """T-34: the contradiction is resolved by a recorded decision plus a probe."""

    def test_decision_document_exists_and_picks_a_posture(self) -> None:
        body = (REPO / "docs" / "NETWORK_POSTURE.md").read_text(encoding="utf-8")
        self.assertIn("least privilege", body.lower())
        self.assertIn("app.infisical.com", body)
        self.assertIn("sonarcloud.io", body)

    def test_probe_asserts_the_chosen_posture(self) -> None:
        result = probe_network_posture.run.__wrapped__ if hasattr(
            probe_network_posture.run, "__wrapped__"
        ) else None
        # Inject reachability rather than touching the network.
        original = probe_network_posture.reachable
        try:
            probe_network_posture.reachable = lambda host, timeout=0: host in (
                "app.infisical.com", "sonarcloud.io", "github.com", "api.github.com", "pypi.org"
            )
            wide = probe_network_posture.run()
            self.assertFalse(wide["ok"])
            self.assertIn("app.infisical.com", wide["violations"])

            probe_network_posture.reachable = lambda host, timeout=0: host in (
                "github.com", "api.github.com", "pypi.org"
            )
            tight = probe_network_posture.run()
            self.assertTrue(tight["ok"], tight)
            self.assertEqual(tight["violations"], [])
        finally:
            probe_network_posture.reachable = original
        del result


class PlatformBlockTests(unittest.TestCase):
    """T-35, T-36, T-37: classify; never fake, never collapse."""

    HOSTED = {
        "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default",
        "L9_GOVERNANCE_SURFACE": "claude-code",
        "HOME": "/nonexistent",
    }

    def test_hosted_surface_names_identity_as_the_primary_blocker(self) -> None:
        result = probe_broker.run(dict(self.HOSTED))
        self.assertEqual(result["primary_blocker"], probe_broker.IDENTITY)
        self.assertEqual(result["identity_reason"], "hosted_surface_issues_no_session_identity")
        self.assertEqual(result["remediation"], "none_available_in_repo")

    def test_identity_outranks_reachability_even_with_a_broker_url(self) -> None:
        """T-36: never reported as a configuration gap the operator could close."""
        env = {**self.HOSTED, "L9_CAPABILITY_BROKER_URL": "https://broker.invalid/l9"}
        result = probe_broker.run(env, timeout=1)
        self.assertEqual(result["primary_blocker"], probe_broker.IDENTITY)
        self.assertNotEqual(result["primary_blocker"], probe_broker.CONFIGURATION)

    def test_dns_absence_is_distinguished_from_a_policy_block(self) -> None:
        """T-37: the distinction the audit could not make from the client side."""
        env = {**self.HOSTED, "L9_CAPABILITY_BROKER_URL": "https://broker.invalid/l9"}
        result = probe_broker.run(env, timeout=1)
        self.assertEqual(result["dns"], "no_dns_record")
        self.assertIn("NOT DEPLOYED", result["reachability_note"])

    def test_identified_runtime_without_a_url_blames_configuration(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as handle:
            handle.write("token-material")
            path = handle.name
        env = {"L9_GOVERNANCE_SURFACE": "claude-code", "L9_WORKLOAD_IDENTITY_TOKEN_FILE": path}
        result = probe_broker.run(env)
        self.assertEqual(result["primary_blocker"], probe_broker.CONFIGURATION)
        Path(path).unlink()


class DegradedModeContractTests(unittest.TestCase):
    """T-38: the still-valid operation set is written down, not inferred."""

    def setUp(self) -> None:
        self.body = (REPO / "docs" / "DEGRADED_MODE_CONTRACT.md").read_text(encoding="utf-8")

    def test_enumerates_what_still_works(self) -> None:
        for tool in ("git", "gh api", "uv", "pre-commit", "node"):
            self.assertIn(tool, self.body)

    def test_enumerates_what_does_not(self) -> None:
        for broken in ("sonar.read_issues", "context7.mcp", "gitguardian.mcp", "GraphQL"):
            self.assertIn(broken, self.body)

    def test_carries_the_anchor_the_client_points_at(self) -> None:
        from capability_client import PLATFORM_BLOCK_TRACKING

        anchor = PLATFORM_BLOCK_TRACKING.split("#", 1)[1]
        self.assertIn(f'id="{anchor}"', self.body)

    def test_refuses_the_paste_a_secret_escape_hatch(self) -> None:
        self.assertIn("never", self.body.lower())
        self.assertIn("SONAR_TOKEN", self.body)
        self.assertIn("INFISICAL_CLIENT_SECRET", self.body)


if __name__ == "__main__":
    unittest.main()
