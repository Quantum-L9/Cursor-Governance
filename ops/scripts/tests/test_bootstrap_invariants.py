#!/usr/bin/env python3
"""Static invariants for the mobile bootstrap remediation (T-39 … T-42).

These guard the CLASS of defect the audit found, not individual instances. A
fix that is not defended by a scan comes back the next time someone adds a
convenience `|| true`.

Scope note, stated rather than glossed: `|| true` is not universally wrong.
`mkdir -p x || true` is fine; `pr_url=$(gh pr view ...) || true` is the bug.
Distinguishing them in general needs dataflow analysis this does not have. So
INV-7 is enforced two ways — a precise scan for the shapes that ARE always
wrong, and a per-file baseline that fails when the count grows. The baseline is
a ratchet, not a proof, and is documented as such.
"""

from __future__ import annotations

import os
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

PROMOTION_PATH = (
    "ops/scripts/open_pr_after_gate.sh",
    "ops/scripts/run_pr_gate.sh",
    "ops/scripts/run_pr_security.sh",
    "ops/scripts/bootstrap_agent_environment.sh",
    "environment/agents/adapters/claude-code/install.sh",
    "environment/agents/adapters/claude-code/web/setup.sh",
    "environment/agents/adapters/claude-code/web/setup.bootstrap.sh",
)

#: Ratchet, measured after the remediation. A file may shed occurrences freely;
#: gaining one requires justifying it here, which is the point.
SWALLOW_BASELINE = {
    # 18 since 9ecfc823 ("fail closed on merged-branch reuse"): the added
    # `gh api ... --jq ... 2>/dev/null || true` reads whether the branch's
    # existing PR is merged/closed; a failed read falls through to opening a
    # fresh PR (fail-safe), so the swallow is justified. The commit added the
    # occurrence without bumping this baseline, leaving the ratchet red on main.
    "ops/scripts/open_pr_after_gate.sh": 18,
    # 15 since 0fc6ee6 ("feat/pr train 0"), which added occurrences without
    # bumping this baseline and left the ratchet red on main — the same lapse
    # the open_pr_after_gate note above records. Audited one by one: all 15 are
    # best-effort TELEMETRY around a verdict carried elsewhere. Timing helper
    # and gate-timing write, gate-log appends and reads, the changed-file
    # stderr filter, `wait` on the prefetch pid, and the two
    # attribute_tree_writers.sh calls are diagnostics — the gate's own contract
    # treats attribution as diagnostic, not as the verdict. The two that could
    # plausibly swallow a decision do not: `scratch_hold.py restore --all` is
    # compensated by the separate fail-closed `_scratch_hold_status` check
    # ("fail closed if still open"), and the gate-failure receipt write runs in
    # the already-failing path, so losing it costs a breadcrumb and not the
    # FAIL. Raise this only after the same one-by-one audit.
    "ops/scripts/run_pr_gate.sh": 15,
    "ops/scripts/run_pr_security.sh": 3,
    "ops/scripts/bootstrap_agent_environment.sh": 3,
    "environment/agents/adapters/claude-code/install.sh": 3,
    "environment/agents/adapters/claude-code/web/setup.sh": 19,
    "environment/agents/adapters/claude-code/web/setup.bootstrap.sh": 1,
}

_SWALLOW = re.compile(r"\|\| *(true|echo|:)")

#: Always wrong: a GraphQL-backed gh call whose result decides PR identity,
#: with its failure erased. Must route through gh_graphql() instead.
_RAW_GH_SWALLOW = re.compile(r"\bgh +(pr|repo) +[a-z-]+.*\|\| *true")


def _is_full_line_comment(line: str) -> bool:
    """A shell comment line swallows nothing — it is prose, not a code path.

    The scans below look for an executable shape. A comment that NAMES that
    shape in order to warn against it is the opposite of the defect, and
    counting it was a false positive with a perverse incentive: the ratchet
    fired at the author who documented why a fallback would be wrong, and the
    cheapest way to green was to delete the explanation or to raise the
    baseline, which blinds the file to a real swallow later.

    Measured instance: setup.bootstrap.sh carries

        # || echo 000 fallback would concatenate into "000000" and never match.

    which is why the broker probe does NOT use that fallback.

    Only FULL-line comments are exempt. A trailing comment cannot launder a
    real swallow, so `foo || true  # justified` is still counted.
    """
    return line.lstrip().startswith("#")


RECEIPT_WRITERS = (
    ("environment/agents/adapters/claude-code/install.sh", "bootstrap-state"),
    (
        "environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh",
        "gov-refresh",
    ),
)

#: The audit's §5.3 verified-absent list. `proxy-injected` is the platform's
#: sentinel for a credential it proxies — the absence of credential material,
#: not the presence of it — so it does not count as leakage.
PROHIBITED_SECRETS = (
    "SONAR_TOKEN",
    "SONARCLOUD_TOKEN",
    "SEMGREP_APP_TOKEN",
    "INFISICAL_CLIENT_SECRET",
    "INFISICAL_TOKEN",
    "INFISICAL_PASSWORD",
    "GRAPHITI_MCP_TOKEN",
    "AWS_SESSION_TOKEN",
    "GITHUB_TOKEN",
)
PROXY_SENTINEL = "proxy-injected"


class SwallowedFailureTests(unittest.TestCase):
    """T-39."""

    def test_no_raw_gh_graphql_call_swallows_its_failure(self) -> None:
        offenders = []
        for rel in PROMOTION_PATH:
            for number, line in enumerate((REPO / rel).read_text(encoding="utf-8").splitlines(), 1):
                if _is_full_line_comment(line):
                    continue
                if _RAW_GH_SWALLOW.search(line) and "gh_graphql" not in line:
                    offenders.append(f"{rel}:{number}: {line.strip()}")
        self.assertEqual(offenders, [], "route GraphQL calls through gh_graphql()")

    def test_capability_check_failure_is_never_swallowed(self) -> None:
        """The B-08 shape: `bash bootstrap_agent_env.sh ... || warn` with no count."""
        body = (REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(
            body,
            r"bootstrap_agent_env\.sh[^\n]*\\\n[^\n]*\|\| warn",
            "a capability-plane failure must increment DEGRADED, not merely warn",
        )
        self.assertIn("cap_rc=$?", body)
        self.assertIn("DEGRADED=$((DEGRADED + 1))", body)

    def test_comment_exemption_does_not_launder_a_real_swallow(self) -> None:
        """The exemption is full-line comments only, and nothing wider."""
        counted = lambda text: sum(  # noqa: E731
            len(_SWALLOW.findall(line))
            for line in text.splitlines()
            if not _is_full_line_comment(line)
        )
        # Prose warning against the shape: not a code path, not counted.
        self.assertEqual(0, counted("# || echo 000 fallback would concatenate"))
        self.assertEqual(0, counted("    # never write foo || true here"))
        # A real swallow stays counted, with or without a trailing excuse.
        self.assertEqual(1, counted("git remote set-url origin x || true"))
        self.assertEqual(1, counted("git remote set-url origin x || true  # justified"))
        self.assertEqual(1, counted('printf "%s" "$x" || echo 000'))

    def test_swallow_count_does_not_grow(self) -> None:
        for rel, baseline in SWALLOW_BASELINE.items():
            with self.subTest(file=rel):
                body = (REPO / rel).read_text(encoding="utf-8")
                count = sum(
                    len(_SWALLOW.findall(line))
                    for line in body.splitlines()
                    if not _is_full_line_comment(line)
                )
                self.assertLessEqual(
                    count,
                    baseline,
                    f"{rel} gained a swallowed failure ({count} > {baseline}); "
                    "justify it in SWALLOW_BASELINE or route it through a classifier",
                )


class GateFailClosedTests(unittest.TestCase):
    """T-40."""

    def test_no_gate_registration_exits_zero_when_it_cannot_evaluate(self) -> None:
        import json

        for rel in (
            "environment/agents/adapters/claude-code/settings.template.json",
            ".claude/settings.json",
        ):
            with self.subTest(settings=rel):
                hooks = json.loads((REPO / rel).read_text(encoding="utf-8"))["hooks"]
                for group in hooks.values():
                    for matcher in group:
                        for entry in matcher["hooks"]:
                            command = entry["command"]
                            if "--class gate" not in command:
                                continue
                            self.assertIn("exit 2", command)
                            self.assertNotIn("|| exit 0", command)

    def test_the_launcher_blocks_gates_on_every_failure_path(self) -> None:
        body = (REPO / "environment/agents/adapters/claude-code/hooks/l9_hook_exec.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("INV-1: gates fail closed", body)
        # cannot_run() is the single exit path; a second bare `exit 0` for gates
        # would defeat it.
        self.assertNotRegex(body, r'HOOK_CLASS.*=.*"gate".*\n.*exit 0')


class ReceiptTimestampTests(unittest.TestCase):
    """T-41."""

    def test_every_receipt_writer_emits_a_utc_timestamp(self) -> None:
        for rel, name in RECEIPT_WRITERS:
            with self.subTest(receipt=name):
                body = (REPO / rel).read_text(encoding="utf-8")
                self.assertIn("date -u +%Y-%m-%dT%H:%M:%SZ", body, f"{name} needs a UTC stamp")
                self.assertIn("ttl_seconds", body, f"{name} needs a TTL")

    def test_readers_recompute_state_rather_than_trusting_it(self) -> None:
        for module in ("governance_refresh_receipt", "claude_bootstrap_receipt"):
            body = (REPO / "ops" / "scripts" / f"{module}.py").read_text(encoding="utf-8")
            self.assertIn("ttl", body)
            self.assertIn("expired", body)
            self.assertIn("never_ran", body.replace("NEVER_RAN", "never_ran"))


class SecretAbsenceTests(unittest.TestCase):
    """T-42: the audited zero-static-secret posture must survive every change."""

    def test_no_prohibited_secret_is_present_in_this_process(self) -> None:
        leaked = [
            name
            for name in PROHIBITED_SECRETS
            if os.environ.get(name) and os.environ[name] != PROXY_SENTINEL
        ]
        self.assertEqual(
            leaked, [], "a prohibited credential is present in a model-controlled surface"
        )

    def test_aws_names_hold_only_the_proxy_sentinel_if_present(self) -> None:
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
            value = os.environ.get(name)
            if value:
                self.assertEqual(
                    value,
                    PROXY_SENTINEL,
                    f"{name} holds credential material, not the platform sentinel",
                )

    def test_no_change_introduced_a_committed_secret(self) -> None:
        """The repo's own zero-static-secret validator, over the working tree."""
        result = subprocess.run(
            ["python3", str(REPO / "ops" / "secrets" / "validate_capability_contract.py")],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-2000:])

    def test_the_env_example_still_assigns_no_credential(self) -> None:
        body = (
            REPO / "environment/agents/adapters/claude-code/web/environment.env.example"
        ).read_text(encoding="utf-8")
        for name in (*PROHIBITED_SECRETS, "GH_TOKEN"):
            self.assertNotRegex(
                body, rf"^{name}=.+$", f"{name} must never be assigned in the example"
            )


if __name__ == "__main__":
    unittest.main()
