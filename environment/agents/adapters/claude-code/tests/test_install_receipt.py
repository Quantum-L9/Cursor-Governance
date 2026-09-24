#!/usr/bin/env python3
"""The installer leaves a receipt on every exit path (INV-2, B-04).

Covers acceptance tests T-09, T-10, T-41.

Each case runs the REAL install.sh against a synthetic governance root broken in
one specific way. The audited runtime had NO receipt at all — the installer's
bookkeeping lived below the failure point and inside an `if [ -n "$GOV_PY" ]`
that a missing interpreter never satisfied — so every one of these paths used to
produce silence.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from claude_bootstrap_receipt import NEVER_RAN, read  # noqa: E402

INSTALL = REPO / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"

#: Every component the receipt serialises, in the order install.sh writes them.
COMPONENTS = (
    "shared_bootstrap",
    "settings",
    "skills",
    "commands",
    "rules",
    "capabilities",
    "memory",
    "memory_cli",
    "memory_mcp",
    "mcp",
    "plugins",
)


class InstallReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.gov = self.root / "gov"
        self.gov.mkdir()
        self.workspace = self.root / "ws"
        self.workspace.mkdir()
        self.receipt = self.root / "bootstrap-state.json"
        self.addCleanup(self._tmp.cleanup)

    def _run(self) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt),
            }
        )
        env.pop("L9_GOVERNANCE_DIR", None)
        return subprocess.run(
            [
                "bash",
                str(INSTALL),
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def _receipt(self) -> dict:
        self.assertTrue(self.receipt.is_file(), "every exit path must leave a receipt")
        return json.loads(self.receipt.read_text(encoding="utf-8"))

    # -- T-09: a failure leaves a receipt naming the stage -------------------

    def test_absent_governance_writes_a_failed_receipt(self) -> None:
        """The earliest guard clause — it used to exit 1 before any bookkeeping."""
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        parsed = self._receipt()
        self.assertEqual(parsed["state"], "failed")
        self.assertEqual(parsed["stage"], "startup")
        self.assertTrue(parsed["remediation"], "a failure receipt must name its repair")
        self.assertRegex(parsed["generated_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_missing_interpreter_still_writes_a_receipt(self) -> None:
        """The exact audited shape: governance present, no .venv, no receipt.

        This is the branch that used to `downgrade ... "no receipt written"` and
        then write nothing — recording the problem in a file it declined to
        create.
        """
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        result = self._run()
        self.assertNotEqual(result.returncode, 0, "BLOCKED must exit non-zero")
        parsed = self._receipt()
        self.assertEqual(parsed["state"], "BLOCKED")
        self.assertEqual(parsed["shared_bootstrap"], "BLOCKED")
        self.assertEqual(parsed["workspace"], str(self.workspace))

    def test_receipt_is_parseable_json_without_the_locked_interpreter(self) -> None:
        """It is written in bash precisely because .venv may be the thing missing."""
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        self._run()
        parsed = self._receipt()
        self.assertEqual(parsed["schema"], "l9.claude-bootstrap.v1")
        self.assertIsInstance(parsed["ttl_seconds"], int)
        self.assertIsInstance(parsed.get("reasons"), dict)
        self.assertIn("log_path", parsed)

    def test_receipt_carries_the_ceremony_id_that_generated_it(self) -> None:
        """SessionStart reads back only the receipt its own ceremony stamped."""
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        with mock.patch.dict(os.environ, {"L9_BOOTSTRAP_ID": "1790184611-4242-7"}):
            self._run()
        self.assertEqual(self._receipt()["bootstrap_id"], "1790184611-4242-7")

    def test_receipt_outside_a_ceremony_carries_an_empty_id(self) -> None:
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "L9_BOOTSTRAP_ID"}
        with mock.patch.dict(os.environ, env, clear=True):
            self._run()
        self.assertEqual(self._receipt()["bootstrap_id"], "")

    def test_non_repository_workspace_is_blocked_not_ready(self) -> None:
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        self._run()  # workspace is not a git repo
        parsed = self._receipt()
        for key in ("settings", "skills", "rules"):
            self.assertEqual(parsed[key], "BLOCKED", f"{key} must not read READY")

    # -- Receipt honesty: an unreached component is not a healthy one -------

    def test_incomplete_run_never_serialises_an_unevaluated_component_as_ready(self) -> None:
        """A receipt must not assert total failure and total health at once.

        The observed shape: `"state": "failed"`, `"stage": "shared-bootstrap"`,
        and all eleven components READY with empty reasons — because READY is the
        INITIAL value of every STATUS_* variable and `downgrade` (the only
        mutator) never ran for any of them, the process having died inside stage
        one. The reader then printed "failed — installer failed at stage
        'shared-bootstrap'" directly above "shared_bootstrap: READY".

        Governance absent is the same shape and the earliest one available: the
        guard clause exits at stage `startup`, so the trap writes the receipt
        and NOTHING has been evaluated. On such a run an untouched READY is not
        a verdict, it is an unanswered question.
        """
        result = self._run()  # no CANONICAL_LAW.md — exits before any stage runs
        self.assertNotEqual(result.returncode, 0)
        parsed = self._receipt()
        self.assertEqual(parsed["state"], "failed", "this case must be an INCOMPLETE run")

        reasons = parsed["reasons"]
        unknown = [k for k in COMPONENTS if parsed[k] == "UNKNOWN"]
        self.assertTrue(unknown, "nothing was rewritten, so the honesty rule never fired")
        for key in COMPONENTS:
            self.assertNotEqual(
                parsed[key],
                "READY",
                f"{key} reads READY on a run that never reached it",
            )
            if parsed[key] == "UNKNOWN":
                self.assertIn(
                    "not evaluated",
                    reasons.get(key, ""),
                    f"{key} is UNKNOWN without saying why",
                )
                self.assertIn(parsed["stage"], reasons[key], f"{key} must name the stage reached")
            else:
                # A component that WAS downgraded keeps its verdict and its own
                # recorded reason: DEGRADED and BLOCKED are evidence, and only
                # untouched optimism is rewritten.
                self.assertNotIn("not evaluated", reasons.get(key, ""))
                self.assertTrue(reasons.get(key), f"{key} was downgraded without a reason")

    def test_a_completed_run_keeps_every_verdict_it_actually_reached(self) -> None:
        """The rewrite is scoped to incomplete runs; a finished verdict is evidence.

        This run reaches the installer's own final `write_receipt`, so READY
        means evaluated-and-passed, BLOCKED keeps its recorded reason, and the
        "not evaluated" text must appear nowhere at all.
        """
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        self._run()
        parsed = self._receipt()
        self.assertNotEqual(parsed["state"], "failed", "this case must be a COMPLETE run")
        self.assertEqual(
            parsed["shared_bootstrap"],
            "BLOCKED",
            "the component that actually failed must still name its own failure",
        )
        self.assertTrue(
            parsed["reasons"]["shared_bootstrap"],
            "a downgraded component keeps its recorded reason",
        )
        for key in COMPONENTS:
            self.assertNotIn(
                "not evaluated",
                parsed["reasons"].get(key, ""),
                f"{key}: a completed run must not report anything as unevaluated",
            )

    # -- Interruption: a budget kill is not a failed environment ------------

    def _interrupt_inside_projection(self) -> subprocess.CompletedProcess[str]:
        """Run the real installer and TERM its process group mid-projection.

        Exactly the SessionStart shape: `timeout` expires and signals the group,
        after the shared bootstrap finished and while a later stage is running.
        The observed receipt from that kill said `failed` and listed all eleven
        components "not evaluated", although several had been.
        """
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        scripts = self.gov / "ops" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "bootstrap_agent_environment.sh").write_text("exit 0\n", encoding="utf-8")
        marker = self.root / "projection-started"
        (scripts / "claude_projection.py").write_text(
            "import pathlib, time\n"
            f"pathlib.Path({str(marker)!r}).write_text('x')\n"
            "time.sleep(60)\n",
            encoding="utf-8",
        )
        venv_bin = self.gov / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python3").symlink_to(sys.executable)

        env = dict(os.environ)
        env.update({"HOME": str(self.home), "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt)})
        env.pop("L9_GOVERNANCE_DIR", None)
        proc = subprocess.Popen(
            [
                "bash",
                str(INSTALL),
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                "--quiet",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            start_new_session=True,
        )
        deadline = time.monotonic() + 30
        while not marker.exists():
            if proc.poll() is not None or time.monotonic() > deadline:
                out, err = proc.communicate()
                self.fail(f"installer never reached the projection stage:\n{out}\n{err}")
            time.sleep(0.05)
        os.killpg(proc.pid, signal.SIGTERM)
        out, err = proc.communicate(timeout=30)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    def test_a_signal_records_an_interrupted_receipt_not_a_failed_one(self) -> None:
        result = self._interrupt_inside_projection()
        self.assertEqual(result.returncode, 143, result.stderr)
        parsed = self._receipt()
        self.assertEqual(parsed["state"], "interrupted")
        self.assertEqual(parsed["interrupted_by"], "TERM")
        self.assertEqual(parsed["stage"], "claude-projection")
        self.assertIsInstance(parsed["elapsed_seconds"], int)
        self.assertIn("INTERRUPTED", result.stderr)

    def test_an_interrupted_run_keeps_the_verdicts_its_finished_stages_reached(self) -> None:
        self._interrupt_inside_projection()
        parsed = self._receipt()
        # The shared bootstrap finished and exited 0: evaluated, and READY.
        self.assertEqual(parsed["shared_bootstrap"], "READY")
        self.assertEqual(parsed["reasons"]["shared_bootstrap"], "")
        # The projection it was killed inside never classified its domains.
        expected = "interrupted by SIGTERM at stage claude-projection"
        for key in ("settings", "skills", "commands", "rules", "plugins", "mcp", "memory"):
            self.assertEqual(parsed[key], "UNKNOWN", key)
            self.assertIn(expected, parsed["reasons"][key])

    def test_reader_classifies_an_interrupted_receipt_as_degraded_and_says_why(self) -> None:
        self._interrupt_inside_projection()
        result = read(self.receipt, governance_revision="unknown")
        self.assertEqual(result["state"], "degraded")
        self.assertIn("interrupted by SIGTERM at stage 'claude-projection'", result["reason"])
        self.assertIn("not evaluated:", result["reason"])
        self.assertNotIn("shared_bootstrap", result["reason"].split("not evaluated:")[1])

    def test_reader_keeps_blocked_ahead_of_an_interruption(self) -> None:
        receipt = {
            "schema": "l9.claude-bootstrap.v1",
            "state": "interrupted",
            "overall": "interrupted",
            "stage": "memory-readiness",
            "interrupted_by": "TERM",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "governance_revision": "unknown",
            **{key: "UNKNOWN" for key in COMPONENTS},
            "shared_bootstrap": "BLOCKED",
        }
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        result = read(self.receipt, governance_revision="unknown")
        self.assertEqual(result["state"], "blocked")

    # -- T-10: absence is never_ran, never ready ----------------------------

    def test_absent_receipt_reads_never_ran(self) -> None:
        result = read(self.receipt)
        self.assertEqual(result["state"], NEVER_RAN)
        self.assertIn("never completed", result["reason"])

    def test_reader_classifies_the_failed_receipt(self) -> None:
        self._run()
        # Synthetic gov has no git; install.sh records revision "unknown".
        # Do not probe the live SSOT clone or the reader reports superseded.
        result = read(self.receipt, governance_revision="unknown")
        self.assertEqual(result["state"], "failed")
        self.assertIn("startup", result["reason"])


if __name__ == "__main__":
    unittest.main()
