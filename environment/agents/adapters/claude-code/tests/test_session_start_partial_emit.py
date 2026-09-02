#!/usr/bin/env python3
"""SessionStart emits context on EVERY exit path, including the ones it loses.

The hook's header declares a FAIL-OPEN contract: "Every failure degrades to a
smaller context blob; the script always exits 0." Both halves were false for the
two failure modes that actually occur in a hosted container:

  * Budget kill. Everything accumulates in a bash array and is emitted by ONE
    call on the last line, so a SIGTERM at the registration's `timeout` threw all
    of it away. A harness log recorded `duration_ms 30008, exit_code 1,
    aborted true` for this hook, and the session received NO governance context —
    not a smaller blob, none.
  * Missing SSOT. `emit_bootstrap_status "$PY"` referenced an unset variable
    under `set -u`, so the branch whose whole purpose is to say "governance SSOT
    NOT FOUND — web/setup.sh must clone it" died with `PY: unbound variable`
    before it could say anything.

Network-free: every case runs against a synthetic $HOME.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

CLAUDE_DIR = Path(__file__).resolve().parent.parent
HOOK = CLAUDE_DIR / "hooks" / "session_start_claude_governance.sh"
REPO_ROOT = Path(__file__).resolve().parents[5]
RUN_WITH_TIMEOUT = REPO_ROOT / "ops" / "scripts" / "lib" / "run_with_timeout.sh"


def _context(stdout: str) -> str:
    """Parse the hook's single JSON document and return its additionalContext."""
    payload = json.loads(stdout)
    return payload["hookSpecificOutput"]["additionalContext"]


def _base_env(home: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "LANG", "LC_ALL", "TERM"}}
    env.update({"HOME": str(home), "CLAUDECODE": "1"})
    # Never let the test touch a real remote.
    env.pop("CLAUDE_CODE_REMOTE", None)
    return env


class MissingSsotTest(unittest.TestCase):
    """The 'SSOT NOT FOUND' branch must be able to reach the operator."""

    def test_emits_valid_json_and_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / ".l9").mkdir(parents=True)
            proc = subprocess.run(
                ["bash", str(HOOK)],
                capture_output=True,
                text=True,
                env=_base_env(home),
                cwd=tmp,
                timeout=60,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                f"hook must exit 0 (fail-open). stderr={proc.stderr[-400:]}",
            )
            self.assertNotIn("unbound variable", proc.stderr)
            context = _context(proc.stdout)
            self.assertIn("governance SSOT: NOT FOUND", context)


class PartialEmitOnTerminationTest(unittest.TestCase):
    """A budget kill degrades the context; it does not delete it."""

    def test_sigterm_to_process_group_still_emits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            gov = home / ".cursor-governance"
            (gov / "ops" / "autonomy").mkdir(parents=True)
            (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
            # Stalls the hook mid-run, exactly where the real profile loader sits.
            (gov / "ops" / "autonomy" / "profile_loader.py").write_text(
                "import time\ntime.sleep(120)\n", encoding="utf-8"
            )
            out = Path(tmp) / "out.json"
            with out.open("w", encoding="utf-8") as sink:
                # start_new_session puts the hook in its own process group, so the
                # signal below reaches the whole tree the way the harness's
                # timeout reap does — signalling only the direct child would leave
                # bash blocked on its python grandchild and prove nothing.
                proc = subprocess.Popen(
                    ["bash", str(HOOK)],
                    stdout=sink,
                    stderr=subprocess.DEVNULL,
                    env=_base_env(home),
                    cwd=tmp,
                    start_new_session=True,
                )
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if out.stat().st_size == 0 and proc.poll() is None:
                        time.sleep(0.4)
                        # Give the hook time to accumulate lines before the kill.
                        if time.monotonic() > deadline - 26:
                            break
                    else:
                        break
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                try:
                    proc.wait(timeout=20)
                except subprocess.TimeoutExpired:  # pragma: no cover
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    self.fail("hook did not exit after SIGTERM")

            stdout = out.read_text(encoding="utf-8")
            self.assertTrue(stdout.strip(), "SIGTERM must not produce an empty stdout")
            context = _context(stdout)
            self.assertIn("PARTIAL", context, "the truncation must be declared, not hidden")
            self.assertIn(
                "L9 Governance",
                context,
                "the lines accumulated before the kill must survive it",
            )


class RepairBudgetTest(unittest.TestCase):
    """The repair is sized by what is LEFT, and records that it was attempted."""

    def _fake_governance(self, tmp: Path, *, installer_body: str) -> Path:
        gov = tmp / "home" / ".cursor-governance"
        (gov / "ops" / "scripts" / "lib").mkdir(parents=True)
        (gov / "environment" / "agents" / "adapters" / "claude-code").mkdir(parents=True)
        (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
        (gov / "ops" / "scripts" / "lib" / "run_with_timeout.sh").write_text(
            RUN_WITH_TIMEOUT.read_text(encoding="utf-8"), encoding="utf-8"
        )
        # Reader stub: reports a non-ready receipt, which is what arms the repair.
        (gov / "ops" / "scripts" / "claude_bootstrap_receipt.py").write_text(
            textwrap.dedent(
                """
                import sys
                if "--json" in sys.argv:
                    print('{"state": "degraded"}')
                else:
                    print("claude bootstrap: degraded — stub")
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (gov / "environment" / "agents" / "adapters" / "claude-code" / "install.sh").write_text(
            installer_body, encoding="utf-8"
        )
        return gov

    def test_defers_when_the_budget_cannot_cover_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(root, installer_body="#!/usr/bin/env bash\nsleep 300\n")
            env = _base_env(root / "home")
            # 5s total minus the 4s reserve leaves nothing for a >=15s repair.
            env["L9_SESSION_START_BUDGET"] = "5"
            proc = subprocess.run(
                ["bash", str(HOOK)],
                capture_output=True,
                text=True,
                env=env,
                cwd=tmp,
                timeout=120,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            context = _context(proc.stdout)
            self.assertIn("bootstrap repair: DEFERRED", context)
            self.assertNotIn(
                "running the installer once",
                context,
                "a repair that cannot finish must not be started",
            )

    def test_marker_is_written_on_attempt_not_on_success(self) -> None:
        """Otherwise an unfinishable repair re-arms every session, forever."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(
                root, installer_body="#!/usr/bin/env bash\necho 'boom' >&2\nexit 1\n"
            )
            env = _base_env(root / "home")
            env["L9_SESSION_START_BUDGET"] = "120"
            proc = subprocess.run(
                ["bash", str(HOOK)],
                capture_output=True,
                text=True,
                env=env,
                cwd=tmp,
                timeout=120,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            context = _context(proc.stdout)
            self.assertIn("running the installer once", context)
            self.assertIn("bootstrap repair: FAILED", context)

            markers = list((root / "home" / ".l9" / "claude").glob("*.attempted"))
            self.assertEqual(
                len(markers), 1, "a FAILED repair must still record that it was attempted"
            )
            body = markers[0].read_text(encoding="utf-8")
            self.assertIn("attempted", body)
            self.assertIn("failed rc=", body, "the outcome is recorded alongside the attempt")


class BudgetRegistrationLockstepTest(unittest.TestCase):
    """A hook's self-imposed budget must agree with the ceiling it runs under.

    ``_l9_budget_left`` sizes every bounded sub-operation from
    ``L9_SESSION_START_BUDGET``, and the harness kills the hook at the
    registration's ``timeout``. If those two numbers drift apart the clamping is
    computed against a window that does not exist: too high and the repair is
    launched with more time than it has (the original 90-in-30 defect, restored
    by a config edit instead of a code edit); too low and it is declined while
    time remains.

    Nothing renders one from the other, so nothing but this test keeps them
    together. Same shape for the Stop hook: ``L9_MEMORY_WRITEBACK_BUDGET`` is
    what ``memory_writeback.py`` divides between repositories, and it must fit
    UNDER the registration timeout with room to write the receipt — a budget
    equal to the ceiling is a budget that ends in a kill.
    """

    TEMPLATE = CLAUDE_DIR / "settings.template.json"
    PROJECTED = REPO_ROOT / ".claude" / "settings.json"
    WRITEBACK = CLAUDE_DIR / "hooks" / "memory_writeback.py"

    @staticmethod
    def _timeout_for(settings: dict, event: str, hook_file: str) -> int:
        for matcher in settings["hooks"][event]:
            for entry in matcher["hooks"]:
                if hook_file in entry["command"]:
                    return int(entry["timeout"])
        raise AssertionError(f"{hook_file} is not registered on {event}")

    def _settings(self):
        for path in (self.TEMPLATE, self.PROJECTED):
            yield path, json.loads(path.read_text(encoding="utf-8"))

    def test_session_start_budget_equals_its_registration_timeout(self) -> None:
        for path, settings in self._settings():
            budget = int(settings["env"]["L9_SESSION_START_BUDGET"])
            timeout = self._timeout_for(
                settings, "SessionStart", "session_start_claude_governance.sh"
            )
            self.assertEqual(
                budget,
                timeout,
                f"{path.name}: L9_SESSION_START_BUDGET={budget} but the hook is "
                f"killed at timeout={timeout}",
            )

    def test_writeback_budget_fits_under_its_registration_timeout(self) -> None:
        for path, settings in self._settings():
            budget = int(settings["env"]["L9_MEMORY_WRITEBACK_BUDGET"])
            timeout = self._timeout_for(settings, "Stop", "memory_writeback.py")
            self.assertLess(
                budget,
                timeout,
                f"{path.name}: a write-back budget of {budget}s under a "
                f"{timeout}s ceiling leaves nothing to record the outcome",
            )

    def test_writeback_module_default_matches_the_configured_budget(self) -> None:
        """The env value is the override; the module constant is the fallback."""
        template = json.loads(self.TEMPLATE.read_text(encoding="utf-8"))
        configured = float(template["env"]["L9_MEMORY_WRITEBACK_BUDGET"])
        source = self.WRITEBACK.read_text(encoding="utf-8")
        line = next(ln for ln in source.splitlines() if ln.startswith("DEFAULT_TOTAL_BUDGET"))
        default = float(line.split("=", 1)[1].strip())
        self.assertEqual(
            default,
            configured,
            "an unset L9_MEMORY_WRITEBACK_BUDGET must not silently change the budget",
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
