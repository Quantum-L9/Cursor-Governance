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

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
REPO = ADAPTER.parents[3]
sys.path.insert(0, str(ADAPTER))
sys.path.insert(0, str(REPO / "ops" / "secrets"))
sys.path.insert(0, str(REPO / "ops" / "scripts"))

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
    # CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS absent. L9_CAPABILITY_BROKER_URL
    # is retired and must not appear in the expected set.
}


class AccountEnvDriftTests(unittest.TestCase):
    """T-32: each of the four B-07 deviations is caught individually."""

    def setUp(self) -> None:
        self.expected = parse_env_example()

    def _deviation(self, key: str, env: dict[str, str]) -> dict[str, str] | None:
        return next((d for d in compare(self.expected, env) if d["key"] == key), None)

    def test_retired_broker_url_is_not_expected(self) -> None:
        """Capability-broker experiment never shipped; absence is the contract."""
        self.assertNotIn("L9_CAPABILITY_BROKER_URL", self.expected)
        row = self._deviation("L9_CAPABILITY_BROKER_URL", AUDITED_ENV)
        self.assertIsNone(row)

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
        """The audited state: a stub cached before the stamp existed.

        The premise is that no revision is recorded anywhere, so the session-env
        fallback has to be pointed at an absent file. Letting it read the real
        `~/.l9/cloud-session.env` made this pass only on a machine that has no
        such file — green in CI, red on any governed session that stamps one.
        """
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "absent.env"
            self.assertEqual(stub_revision_actual({}, absent), "")
            result = run(dict(AUDITED_ENV), session_env=absent)
        self.assertTrue(result["stub_drift"])
        self.assertEqual(result["stub_revision_actual"], "")

    def test_matching_revision_is_not_drift(self) -> None:
        env = {**parse_env_example(), "L9_STUB_REVISION": stub_revision_expected()}
        self.assertFalse(run(env)["stub_drift"])

    def test_stub_writes_its_revision_into_the_session_env(self) -> None:
        stub = (ADAPTER / "web" / "setup.bootstrap.sh").read_text(encoding="utf-8")
        lib = (ADAPTER / "lib" / "cloud_account_env.sh").read_text(encoding="utf-8")
        self.assertIn("export L9_STUB_REVISION", stub)
        self.assertIn("export L9_STUB_REVISION=", lib)
        self.assertIn("l9_write_cloud_session_env", stub)


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
    """Hosted Claude Code no longer probes the retired capability broker.

    Identity/reachability classification for the retired broker lives under
    ops/secrets/_archived/capability-broker/tests/. This adapter must not
    re-introduce that probe as a SessionStart or install health check.
    """

    def test_session_start_does_not_invoke_probe_broker(self) -> None:
        src = (ADAPTER / "hooks" / "session_start_claude_governance.sh").read_text(encoding="utf-8")
        self.assertNotIn("probe_broker.py", src)
        self.assertIn("capability_broker=retired", src)

    def test_install_does_not_probe_the_broker(self) -> None:
        src = (ADAPTER / "install.sh").read_text(encoding="utf-8")
        self.assertNotIn("probe_broker.py", src)
        self.assertIn("capability broker experiment retired", src)

    def test_bootstrap_does_not_export_or_probe_broker_url(self) -> None:
        src = (ADAPTER / "web" / "setup.bootstrap.sh").read_text(encoding="utf-8")
        self.assertNotIn("L9_CAPABILITY_BROKER_URL", src)
        self.assertIn("cloud_account_env.sh", src)

    def test_cloud_env_lib_strips_retired_broker_url(self) -> None:
        src = (ADAPTER / "lib" / "cloud_account_env.sh").read_text(encoding="utf-8")
        self.assertIn("L9_CAPABILITY_BROKER_URL", src)
        self.assertIn("l9_normalize_cloud_account_env", src)


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


class PasteIntegrityTests(unittest.TestCase):
    """A fence-contaminated paste must fail loudly instead of executing prose.

    docs/account-fields/SETUP_SCRIPT.md renders the stub inside a fenced code
    block. Selecting the section rather than the fence body puts the fence lines
    into the Setup script field. A fence is three backticks: bash reads an empty
    command substitution plus one leftover backtick, which opens a substitution
    that runs to the closing fence.

    Measured 2026-08-22 with the pre-fix stub: the backticks in its own comments
    closed and reopened that substitution, pushing comment prose out of comment
    position so bash executed English as commands, ran git clone with an empty
    target directory, and exited 127 with the environment half-built.

    Two properties keep that from recurring, and both are asserted here rather
    than trusted: the stub carries no backticks, and it detects being swallowed
    into a substitution and refuses.
    """

    STUB = ADAPTER / "web" / "setup.bootstrap.sh"

    def setUp(self) -> None:
        self.body = self.STUB.read_text(encoding="utf-8")

    def test_stub_contains_no_backticks(self) -> None:
        """Every backtick here is markdown decoration and a live detonator."""
        offenders = [
            f"{n}: {line}" for n, line in enumerate(self.body.splitlines(), 1) if "`" in line
        ]
        self.assertEqual(
            [],
            offenders,
            "setup.bootstrap.sh must stay backtick-free; a stray backtick lets a "
            "pasted markdown fence execute the surrounding comment prose as shell:\n"
            + "\n".join(offenders),
        )

    def test_stub_carries_both_paste_markers(self) -> None:
        """The docs tell a human to select between these; they must exist."""
        self.assertIn("L9-PASTE-BEGIN", self.body)
        self.assertIn("L9-PASTE-END", self.body)

    def test_stub_is_syntactically_valid(self) -> None:
        proc = subprocess.run(["bash", "-n", str(self.STUB)], capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)

    def _run(self, script: str, env_extra: dict[str, str]) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "init-script.sh"
            path.write_text(script, encoding="utf-8")
            home = Path(tmp) / "home"
            home.mkdir()
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(home),
                # Deliberately unreachable: this test is about paste integrity,
                # not about cloning, and it must not touch the network.
                "L9_GOVERNANCE_REMOTE": str(Path(tmp) / "no-such-repo.git"),
                **env_extra,
            }
            return subprocess.run(
                ["bash", str(path)],
                capture_output=True,
                text=True,
                env=env,
                stdin=subprocess.DEVNULL,
                timeout=120,
            )

    def test_fence_contaminated_paste_is_refused_by_name(self) -> None:
        """The exact bad paste: heading, fences, stub, and trailing prose."""
        fence = "`" * 3
        contaminated = "\n".join(
            [
                "## Paste this",
                "",
                fence + "bash",
                self.body.rstrip(),
                fence,
                "",
                "## Verify the paste took",
                "",
                "Start a NEW session, then:",
                "",
            ]
        )
        proc = self._run(contaminated, {"CLAUDE_CODE_REMOTE": "true"})

        self.assertIn("L9 bootstrap FATAL", proc.stderr)
        self.assertIn("markdown fence", proc.stderr)
        # The pre-fix signature: comment prose reaching the shell as commands.
        # These words appear only inside comments, so seeing them reported as
        # commands means the comment structure was destroyed again.
        for prose in ("arrives:", "succeeds:", "unreliable"):
            self.assertNotIn(
                f"{prose} command not found",
                proc.stderr,
                "comment prose is being executed as shell again",
            )
        # And the guard must stop the run before it reaches the clone.
        self.assertNotIn("governance clone FAILED", proc.stderr)

    def test_clean_paste_is_not_flagged(self) -> None:
        """The guard must not fire on the paste the documentation asks for."""
        proc = self._run(self.body, {"CLAUDE_CODE_REMOTE": "true"})
        self.assertNotIn("L9 bootstrap FATAL", proc.stderr)
        # Proof it ran past the guard and down the real path.
        self.assertIn("governance clone FAILED", proc.stderr)

    def test_clean_paste_on_local_cli_exits_zero(self) -> None:
        """Not a cloud session: the stub is a no-op, guard included."""
        proc = self._run(self.body, {})
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertNotIn("L9 bootstrap FATAL", proc.stderr)


if __name__ == "__main__":
    unittest.main()
