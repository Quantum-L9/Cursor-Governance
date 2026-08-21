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
    ACCOUNT_FIELDS,
    PLATFORM_PROXY_SENTINEL,
    RUNTIME_MANAGED,
    account_fields_markdown,
    compare,
    parse_env_example,
    parse_network_hosts,
    prohibited_present,
    run,
    safe_value,
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
        # Inject reachability rather than touching the network.
        original = probe_network_posture.reachable
        try:
            probe_network_posture.reachable = lambda host, timeout=0: (
                host
                in (
                    "app.infisical.com",
                    "sonarcloud.io",
                    "github.com",
                    "api.github.com",
                    "pypi.org",
                )
            )
            wide = probe_network_posture.run()
            self.assertFalse(wide["ok"])
            self.assertIn("app.infisical.com", wide["violations"])

            probe_network_posture.reachable = lambda host, timeout=0: (
                host in ("github.com", "api.github.com", "pypi.org")
            )
            tight = probe_network_posture.run()
            self.assertTrue(tight["ok"], tight)
            self.assertEqual(tight["violations"], [])
        finally:
            probe_network_posture.reachable = original


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


#: A value that is obviously synthetic. Never a real credential, in any fixture.
FAKE_SECRET = "NOT-A-REAL-CREDENTIAL-test-fixture"


class ProhibitedKeyPresenceTests(unittest.TestCase):
    """The unenforced half of the DELIBERATELY_ABSENT contract.

    `compare()` filtered these keys out of the expected set so they could never
    be reported missing, and nothing ever checked whether they were PRESENT. A
    pasted Infisical secret produced "all 36 expected variables match".
    """

    def test_a_pasted_credential_is_reported(self) -> None:
        rows = prohibited_present({"INFISICAL_CLIENT_SECRET": FAKE_SECRET})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "INFISICAL_CLIENT_SECRET")
        self.assertEqual(rows[0]["kind"], "prohibited")

    def test_the_value_is_never_returned(self) -> None:
        rows = prohibited_present({"GRAPHITI_MCP_TOKEN": FAKE_SECRET, "SONAR_TOKEN": FAKE_SECRET})
        self.assertNotIn(FAKE_SECRET, repr(rows))

    def test_the_proxy_sentinel_is_not_a_violation(self) -> None:
        """Unsetting it would break the proxying it announces."""
        rows = prohibited_present({"GH_TOKEN": PLATFORM_PROXY_SENTINEL})
        self.assertEqual(rows[0]["kind"], "proxy_sentinel")
        self.assertEqual(run({"GH_TOKEN": PLATFORM_PROXY_SENTINEL})["prohibited_count"], 0)

    def test_a_real_gh_token_is_a_violation(self) -> None:
        rows = prohibited_present({"GH_TOKEN": FAKE_SECRET})
        self.assertEqual(rows[0]["kind"], "prohibited")

    def test_an_otherwise_perfect_environment_still_fails(self) -> None:
        """The regression that matters: clean variables, pasted credential."""
        env = {
            **parse_env_example(),
            "L9_STUB_REVISION": stub_revision_expected(),
            "INFISICAL_CLIENT_SECRET": FAKE_SECRET,
        }
        result = run(env)
        self.assertEqual(result["deviations"], [], "the expected set is clean")
        self.assertEqual(result["prohibited_count"], 1)
        self.assertFalse(result["ok"], "a pasted credential must not report ok")

    def test_absence_remains_the_contract(self) -> None:
        self.assertEqual(prohibited_present({}), [])

    def test_redaction_covers_key_id_suffixes(self) -> None:
        """`_KEY$` alone missed GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID."""
        for key in ("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID", "CEG_API_KEY", "GH_TOKEN"):
            self.assertEqual(safe_value(key, FAKE_SECRET), "<redacted>", key)
        self.assertEqual(safe_value("L9_AUTONOMY_MAX_PARALLEL", "480"), "480")


class NetworkFieldIsPasteReadyTests(unittest.TestCase):
    """Field 3 was a pointer while fields 1 and 2 were paste-ready."""

    def test_hosts_parse_from_the_policy_document(self) -> None:
        hosts = parse_network_hosts()
        self.assertGreater(len(hosts), 5)
        self.assertIn("api.github.com", hosts)

    def test_the_broker_host_is_in_the_pasted_block(self) -> None:
        """Its own table required it; the block a human pastes omitted it, so
        pasting Option B verbatim disabled every authenticated capability."""
        self.assertIn("broker.quantumaipartners.com", parse_network_hosts())

    def test_section_three_carries_hosts_and_a_checksum(self) -> None:
        body = account_fields_markdown(parse_env_example(), "test-rev")
        section = body.split("## 3. Network access", 1)[1]
        for host in parse_network_hosts():
            self.assertIn(host, section)
        self.assertIn("Checksum", section)

    def test_secret_backends_stay_out_of_the_allow_list(self) -> None:
        hosts = parse_network_hosts()
        self.assertNotIn("app.infisical.com", hosts)
        self.assertNotIn("sonarcloud.io", hosts)


class GeneratedFieldsStayInSyncTests(unittest.TestCase):
    """The committed doc is generated from three sources and can drift silently."""

    def test_committed_document_matches_its_sources(self) -> None:
        want = account_fields_markdown(parse_env_example(), stub_revision_expected())
        self.assertEqual(
            ACCOUNT_FIELDS.read_text(encoding="utf-8"),
            want,
            "docs/ACCOUNT_FIELDS.md is stale — run verify_account_env.py --emit-fields",
        )


class StubHardeningTests(unittest.TestCase):
    """Behaviours the stub must carry, expressed against its source."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.stub = (ADAPTER / "web" / "setup.bootstrap.sh").read_text(encoding="utf-8")

    def test_clone_ref_is_verified_not_assumed(self) -> None:
        """Every clone branch can end on the wrong ref; one comparison catches all."""
        self.assertIn("L9_GOVERNANCE_REF_STATE", self.stub)
        self.assertIn("export L9_GOVERNANCE_REVISION=", self.stub)

    def test_broker_host_is_resolved_not_merely_announced(self) -> None:
        self.assertIn("DOES NOT RESOLVE", self.stub)
        self.assertIn("broker_host()", self.stub)

    def test_leaked_names_survive_the_unset(self) -> None:
        """Unsetting in the build process makes the leak invisible afterwards."""
        self.assertIn("L9_ACCOUNT_FIELD_LEAKS", self.stub)

    def test_durable_env_does_not_overclaim_its_reach(self) -> None:
        """It reaches interactive and login shells only; agents run neither."""
        self.assertIn("BASH_ENV", self.stub)
        self.assertNotIn("also unsets them for in-session Bash", self.stub)

    def test_revision_was_bumped_for_these_changes(self) -> None:
        self.assertNotEqual(stub_revision_expected(), "2026-08-21.1")
