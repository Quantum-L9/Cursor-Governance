#!/usr/bin/env python3
"""Governance refresh receipt: a claim that cannot expire always reads healthy.

Covers audit finding B-05 and acceptance tests T-07, T-08, T-41.

The receipt this replaces was the single word `fresh` plus a short SHA. It was
written once at environment-build time and still read `fresh 941ab77` days
later, while the clone it described sat four commits behind main. Every case
below is therefore built from a receipt that LIES at write time — `state:
"fresh"` — to prove the reader ignores that field and derives state itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from governance_refresh_receipt import (  # noqa: E402
    FRESH,
    NEVER_RAN,
    STALE,
    UNKNOWN,
    evaluate,
    read,
)

HOOK = (
    REPO
    / "environment"
    / "agents"
    / "adapters"
    / "claude-code"
    / "hooks"
    / "session_start_claude_governance.sh"
)

NOW = datetime(2026, 8, 21, 2, 9, 0, tzinfo=UTC)
SHA_A = "941ab775c3e6d2a4d8b0425b10e9cb32b9a8e403"
SHA_B = "b406feeb4734f7029c36d718a68b004cacd6a68a"


def receipt(**overrides: object) -> dict[str, object]:
    """A receipt that claims to be fresh. Tests override one signal at a time."""
    base: dict[str, object] = {
        "schema": "l9.governance-refresh.v1",
        "outcome": "fetched",
        "local_sha": SHA_A,
        "origin_sha": SHA_A,
        "refreshed_at": (NOW - timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ttl_seconds": 3600,
        "commits_behind": 0,
        "state": "fresh",
    }
    base.update(overrides)
    return base


class RefreshStateTests(unittest.TestCase):
    def test_recent_and_converged_is_fresh(self) -> None:
        self.assertEqual(evaluate(receipt(), now=NOW)["state"], FRESH)

    # -- T-07: expiry dominates the written claim ---------------------------

    def test_receipt_older_than_ttl_is_unknown_not_fresh(self) -> None:
        stamp = (NOW - timedelta(seconds=8 * 3600)).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = evaluate(receipt(refreshed_at=stamp), now=NOW)
        self.assertEqual(result["state"], UNKNOWN)
        self.assertIn("expired", result["reason"])
        # The written claim is carried for forensics but never obeyed.
        self.assertEqual(result["state_at_write"], "fresh")

    def test_expiry_outranks_every_other_healthy_signal(self) -> None:
        stamp = (NOW - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertEqual(
            evaluate(receipt(refreshed_at=stamp, commits_behind=0), now=NOW)["state"], UNKNOWN
        )

    def test_unparseable_timestamp_is_unknown(self) -> None:
        self.assertEqual(evaluate(receipt(refreshed_at="fresh 941ab77"), now=NOW)["state"], UNKNOWN)

    # -- T-08: divergence and distance demote to stale ----------------------

    def test_commits_behind_is_stale(self) -> None:
        result = evaluate(receipt(commits_behind=4), now=NOW)
        self.assertEqual(result["state"], STALE)
        self.assertIn("4 commits behind", result["reason"])

    def test_diverged_shas_are_stale(self) -> None:
        result = evaluate(receipt(local_sha=SHA_A, origin_sha=SHA_B), now=NOW)
        self.assertEqual(result["state"], STALE)

    def test_unknown_distance_is_not_treated_as_zero(self) -> None:
        """-1 means 'shallow clone, cannot count'. It must not read as current."""
        self.assertEqual(evaluate(receipt(commits_behind=-1), now=NOW)["state"], FRESH)
        self.assertEqual(
            evaluate(receipt(commits_behind=-1, origin_sha=SHA_B), now=NOW)["state"], STALE
        )

    def test_reset_failed_is_stale_and_fetch_failed_is_unknown(self) -> None:
        self.assertEqual(evaluate(receipt(outcome="reset-failed"), now=NOW)["state"], STALE)
        self.assertEqual(
            evaluate(receipt(outcome="fetch-failed", origin_sha="unknown"), now=NOW)["state"],
            UNKNOWN,
        )

    # -- absence is its own state -------------------------------------------

    def test_absent_receipt_is_never_ran_not_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = read(Path(tmp) / "absent.json", now=NOW)
        self.assertEqual(result["state"], NEVER_RAN)

    def test_malformed_receipt_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gov-refresh.json"
            path.write_text("fresh 941ab77\n", encoding="utf-8")
            self.assertEqual(read(path, now=NOW)["state"], UNKNOWN)


class HookWriterTests(unittest.TestCase):
    """The hook must emit parseable JSON with a UTC timestamp (INV-2, T-41).

    It writes with printf rather than python3 deliberately — it has to leave a
    trace on a runtime with no usable interpreter, which is exactly the runtime
    whose staleness we are trying to detect. That makes 'is it valid JSON?' a
    real question worth asserting.
    """

    def test_hook_writes_parseable_timestamped_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            gov = home / ".cursor-governance"
            gov.mkdir()
            (gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(gov)], check=True)
            receipt_file = home / "receipt.json"

            env = {
                "HOME": str(home),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "CLAUDE_CODE_REMOTE": "true",
                "L9_GOV_REFRESH_RECEIPT": str(receipt_file),
                "CLAUDE_PROJECT_DIR": str(home),
            }
            result = subprocess.run(
                ["bash", str(HOOK)], capture_output=True, text=True, env=env, check=False
            )
            self.assertEqual(result.returncode, 0, "SessionStart hooks must never block")
            self.assertTrue(receipt_file.is_file(), "a failed fetch still leaves a receipt")

            parsed = json.loads(receipt_file.read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema"], "l9.governance-refresh.v1")
            # No remote is configured, so the fetch cannot succeed: origin is
            # genuinely unobserved and must not be recorded as equal to local.
            self.assertEqual(parsed["outcome"], "fetch-failed")
            self.assertEqual(parsed["origin_sha"], "unknown")
            self.assertRegex(parsed["refreshed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertIsInstance(parsed["ttl_seconds"], int)
            self.assertEqual(read(receipt_file)["state"], UNKNOWN)

            # The hook still emits exactly one JSON document on stdout (F-08).
            json.loads(result.stdout)

    def test_projection_reports_an_absent_receipt_as_never_ran(self) -> None:
        """The SessionStart projection must use the receipt READER, not a second
        inline parser.

        The old projection had no notion of an absent or expired receipt, so it
        reported silence as nothing-to-say and a stale receipt as current — the
        same defect as B-04/B-05, one layer up. This drives the real hook against
        the real repository as its governance clone, with a HOME that carries no
        receipts at all.
        """
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            gov = home / ".cursor-governance"
            gov.symlink_to(REPO)
            env = {
                "HOME": str(home),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "CLAUDE_CODE_REMOTE": "false",
                "CLAUDE_PROJECT_DIR": str(REPO),
            }
            result = subprocess.run(
                ["bash", str(HOOK)], capture_output=True, text=True, env=env, check=False
            )
            self.assertEqual(result.returncode, 0, "SessionStart must never block")
            context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
            self.assertIn("never_ran", context, "an absent receipt must be named, not omitted")
            self.assertIn("governance refresh", context)


if __name__ == "__main__":
    unittest.main()
