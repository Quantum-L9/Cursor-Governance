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
import re
import shutil
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

    @staticmethod
    def _registered_command() -> str:
        settings = json.loads((CLAUDE_DIR / "settings.template.json").read_text(encoding="utf-8"))
        for matcher in settings["hooks"]["SessionStart"]:
            for entry in matcher["hooks"]:
                if "session_start_claude_governance.sh" in entry["command"]:
                    return entry["command"]
        raise AssertionError("governance hook is not registered on SessionStart")

    def test_registration_reaches_the_committed_copy_when_governance_is_absent(self) -> None:
        """The REGISTERED command, not just the hook, must deliver NOT FOUND.

        Every registration dispatches through the launcher inside
        $HOME/.cursor-governance, so when governance is absent the launcher is
        absent too — and an observer registration that simply `exit 0`s on a
        missing launcher can never deliver the one line that says the
        environment was never provisioned. The committed consumer copy exists
        for exactly that session (SESSION_START_SPEC: Mobile/Web survival),
        which is only true if the registration falls back to it.
        """
        command = self._registered_command()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            project = Path(tmp) / "consumer"
            (project / ".claude" / "hooks").mkdir(parents=True)
            copy = project / ".claude" / "hooks" / "session_start_claude_governance.sh"
            copy.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
            env = _base_env(home)
            env["CLAUDE_PROJECT_DIR"] = str(project)
            proc = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                env=env,
                cwd=tmp,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
            self.assertIn("governance SSOT: NOT FOUND", _context(proc.stdout))

    def test_registration_stays_silent_when_neither_launcher_nor_copy_exists(self) -> None:
        """No launcher, no committed copy: an observer still fails open."""
        command = self._registered_command()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            project = Path(tmp) / "consumer"
            project.mkdir()
            env = _base_env(home)
            env["CLAUDE_PROJECT_DIR"] = str(project)
            proc = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                env=env,
                cwd=tmp,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0)
            self.assertEqual(proc.stdout.strip(), "")


class BoundedSubEngineTest(unittest.TestCase):
    """Every multi-second sub-engine runs inside what is LEFT of the budget.

    The platform discards a hook's output when the hook reaches its `timeout`,
    so a sub-engine that runs past the ceiling does not degrade the context —
    it deletes it. A hosted session measured this hook at 29,620 ms against a
    30,000 ms ceiling with the readiness emitter and the projection engine
    running unbounded after the repair. Each must be declined by name when the
    remaining budget cannot cover it, run under the remaining budget when it
    can, and be reported as TIMED OUT when it exceeds that.
    """

    def _fake_governance(self, tmp: Path, *, readiness_body: str) -> Path:
        gov = tmp / "home" / ".cursor-governance"
        (gov / "ops" / "scripts" / "lib").mkdir(parents=True)
        (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
        (gov / "ops" / "scripts" / "lib" / "run_with_timeout.sh").write_text(
            RUN_WITH_TIMEOUT.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (gov / "ops" / "scripts" / "claude_projection.py").write_text(
            textwrap.dedent(
                """
                import pathlib, sys
                pathlib.Path(sys.argv[0]).with_suffix(".ran").write_text("ran")
                print("projection=ok")
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        (gov / "ops" / "scripts" / "emit_claude_readiness.py").write_text(
            readiness_body, encoding="utf-8"
        )
        return gov

    def _run(self, tmp: Path, *, budget: str) -> str:
        env = _base_env(tmp / "home")
        env["L9_SESSION_START_BUDGET"] = budget
        proc = subprocess.run(
            ["bash", str(HOOK)],
            capture_output=True,
            text=True,
            env=env,
            cwd=tmp,
            timeout=120,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        return _context(proc.stdout)

    READINESS_STUB = (
        "import pathlib, sys\n"
        'pathlib.Path(sys.argv[0]).with_suffix(".ran").write_text("ran")\n'
        'print("--- claude readiness receipt ---")\n'
        'print("receipt_source=stub")\n'
    )

    def test_engines_are_declined_by_name_when_the_budget_cannot_cover_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gov = self._fake_governance(root, readiness_body=self.READINESS_STUB)
            # 8 s total minus reserve (4), grace (2) and the child's one-second
            # margin leaves 1 s: below every floor — while the parent's 2 s
            # deadline still lets the child reach the end and declare complete.
            context = self._run(root, budget="8")
            self.assertIn("claude projection: DEFERRED", context)
            self.assertIn("claude readiness: DEFERRED", context)
            self.assertFalse(
                (gov / "ops" / "scripts" / "claude_projection.ran").exists(),
                "a projection that cannot fit must not be started",
            )
            self.assertFalse(
                (gov / "ops" / "scripts" / "emit_claude_readiness.ran").exists(),
                "a readiness rebuild that cannot fit must not be started",
            )

    def test_engines_run_and_report_when_the_budget_covers_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gov = self._fake_governance(root, readiness_body=self.READINESS_STUB)
            context = self._run(root, budget="120")
            self.assertNotIn("DEFERRED", context)
            self.assertIn("claude projection: ok", context)
            self.assertIn("receipt_source=stub", context)
            self.assertTrue((gov / "ops" / "scripts" / "claude_projection.ran").exists())
            self.assertTrue((gov / "ops" / "scripts" / "emit_claude_readiness.ran").exists())

    def test_an_engine_that_outlives_the_budget_is_reported_as_timed_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(root, readiness_body="import time\ntime.sleep(300)\n")
            # 16 s minus reserve (4), grace (2) and the one-second margin
            # leaves 9 s: enough to START the emitter (floor 8), not enough
            # for a 300 s stall to finish. The parent's deadline is 10 s, so
            # the child names the timeout and still completes.
            started = time.monotonic()
            context = self._run(root, budget="16")
            elapsed = time.monotonic() - started
            self.assertIn("claude readiness: TIMED OUT", context)
            self.assertNotIn("PARTIAL", context, "a named timeout is a complete run")
            self.assertLess(elapsed, 30, "the stall must be cut at the remaining budget")


class SkipVisibilityTest(unittest.TestCase):
    """Launcher skips recorded during THIS SessionStart reach the session.

    Sibling hooks run concurrently and may dispatch against the pre-refresh
    governance revision; the launcher records the resulting skip in its log,
    and this hook surfaces the entries stamped at or after its own start —
    and only those, so a skip from six weeks ago is not reported as today's.
    """

    def test_only_skips_from_this_session_start_are_surfaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            (home / ".l9" / "claude").mkdir(parents=True)
            skip_log = home / ".l9" / "claude" / "hook-skips.log"
            skip_log.write_text(
                "2020-01-01T00:00:00Z observer stale_hook.py hook file absent\n"
                "2999-01-01T00:00:00Z observer bootstrap_capability_preflight.sh "
                "hook file absent\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                ["bash", str(HOOK)],
                capture_output=True,
                text=True,
                env=_base_env(home),
                cwd=tmp,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
            context = _context(proc.stdout)
            self.assertIn("hook skips this SessionStart", context)
            self.assertIn("bootstrap_capability_preflight.sh hook file absent", context)
            self.assertNotIn("stale_hook.py", context)


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


class SelfImposedDeadlineTest(unittest.TestCase):
    """The hook lands inside its budget on its own, without being signalled.

    PartialEmitOnTerminationTest passed throughout the production failure it
    was written for, because it signals the whole PROCESS GROUP: the stalled
    grandchild dies too, the foreground command returns, and the queued trap
    dispatches at once. The harness is not that kind: it cancels at its
    `timeout` and reads nothing, and bash will not run a trap while the script
    sits in a foreground child — so the armed, correct trap never got a turn
    and the session received no governance context at all.

    This test therefore sends NO signal. It asserts the property the harness
    actually needs: the hook speaks before the deadline arrives.
    """

    def test_emits_before_the_deadline_with_no_signal_at_all(self) -> None:
        budget = 8
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            gov = home / ".cursor-governance"
            (gov / "ops" / "autonomy").mkdir(parents=True)
            (home / ".l9").mkdir(parents=True)
            (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
            # Stalls in a FOREGROUND child — the exact shape that starves a trap.
            (gov / "ops" / "autonomy" / "profile_loader.py").write_text(
                "import time\ntime.sleep(600)\n", encoding="utf-8"
            )
            env = _base_env(home)
            env["L9_SESSION_START_BUDGET"] = str(budget)

            started = time.monotonic()
            proc = subprocess.run(
                ["bash", str(HOOK)],
                capture_output=True,
                text=True,
                env=env,
                cwd=tmp,
                # Generous, so a hook that hangs FAILS here rather than being
                # rescued by a timeout that stands in for the harness's kill.
                timeout=120,
                check=False,
            )
            elapsed = time.monotonic() - started

        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr[-400:]}")
        self.assertLess(
            elapsed,
            budget,
            "the hook must emit BEFORE the registration timeout, not be killed at it",
        )
        context = _context(proc.stdout)
        self.assertIn("PARTIAL", context, "the truncation must be declared, not hidden")
        self.assertIn(
            "L9 Governance",
            context,
            "lines accumulated before the deadline must survive it",
        )

    def test_partial_is_declared_once(self) -> None:
        """The parent owns the declaration; a child racing it double-reports."""
        budget = 8
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            gov = home / ".cursor-governance"
            (gov / "ops" / "autonomy").mkdir(parents=True)
            (home / ".l9").mkdir(parents=True)
            (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
            (gov / "ops" / "autonomy" / "profile_loader.py").write_text(
                "import time\ntime.sleep(600)\n", encoding="utf-8"
            )
            env = _base_env(home)
            env["L9_SESSION_START_BUDGET"] = str(budget)
            proc = subprocess.run(
                ["bash", str(HOOK)],
                capture_output=True,
                text=True,
                env=env,
                cwd=tmp,
                timeout=120,
                check=False,
            )
        self.assertEqual(
            _context(proc.stdout).count("the context above is PARTIAL"),
            1,
            "exactly one PARTIAL declaration",
        )


class ReceiptGenerationTest(unittest.TestCase):
    """Every bootstrap generates its receipt, then reads THAT receipt.

    Observed on a hosted session: SessionStart printed an earlier session's
    receipt ("ready … 1056s ago") as the verdict of a bootstrap that generated
    nothing; and a session that ran the installer printed the expired verdict it
    had just replaced and never read the receipt the installer wrote.
    """

    # Fake installer: records its ceremony id, stamps it into the receipt it
    # writes, and counts runs. Fake reader: records the id it was bound to and
    # reports whether the on-disk receipt carries it.
    INSTALLER = textwrap.dedent(
        """\
        #!/usr/bin/env bash
        d="$HOME/.l9/claude"; mkdir -p "$d"
        echo run >>"$d/installer-runs"
        printf '%s' "${L9_BOOTSTRAP_ID:-}" >"$d/installer-id"
        printf '{"state": "READY", "bootstrap_id": "%s"}\\n' "${L9_BOOTSTRAP_ID:-}" \\
          >"$d/bootstrap-state.json"
        """
    )

    READER = textwrap.dedent(
        """\
        import json, pathlib, sys
        home = pathlib.Path.home() / ".l9" / "claude"
        want = None
        if "--bootstrap-id" in sys.argv:
            want = sys.argv[sys.argv.index("--bootstrap-id") + 1]
        if want is not None:
            (home / "reader-id").write_text(want)
        try:
            got = json.loads((home / "bootstrap-state.json").read_text()).get("bootstrap_id", "")
        except Exception:
            got = None
        state = "ready" if want is not None and got == want else "unknown"
        if "--json" in sys.argv:
            print(json.dumps({"state": state}))
        else:
            print(f"claude bootstrap: {state} — stub (receipt id {got}, ceremony id {want})")
        """
    )

    def _fake_governance(self, tmp: Path, *, installer_body: str | None = None) -> Path:
        gov = tmp / "home" / ".cursor-governance"
        (gov / "ops" / "scripts" / "lib").mkdir(parents=True)
        (gov / "environment" / "agents" / "adapters" / "claude-code").mkdir(parents=True)
        (gov / "CANONICAL_LAW.md").write_text("law\n", encoding="utf-8")
        (gov / "ops" / "scripts" / "lib" / "run_with_timeout.sh").write_text(
            RUN_WITH_TIMEOUT.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (gov / "ops" / "scripts" / "claude_bootstrap_receipt.py").write_text(
            self.READER, encoding="utf-8"
        )
        (gov / "environment" / "agents" / "adapters" / "claude-code" / "install.sh").write_text(
            installer_body if installer_body is not None else self.INSTALLER, encoding="utf-8"
        )
        return gov

    def _run(self, tmp: str, budget: str = "120", extra_env: dict[str, str] | None = None) -> str:
        env = _base_env(Path(tmp) / "home")
        env["L9_SESSION_START_BUDGET"] = budget
        env.update(extra_env or {})
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
        return _context(proc.stdout)

    def test_every_bootstrap_generates_its_receipt(self) -> None:
        """A READY receipt already on disk does not excuse a generation."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(root)
            state = root / "home" / ".l9" / "claude"
            state.mkdir(parents=True)
            (state / "bootstrap-state.json").write_text(
                '{"state": "READY", "bootstrap_id": "an-earlier-session"}', encoding="utf-8"
            )
            first = self._run(tmp)
            second = self._run(tmp)
            runs = (state / "installer-runs").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(runs), 2, "each bootstrap must generate its own receipt")
            for context in (first, second):
                self.assertIn("bootstrap receipt: generated this bootstrap", context)
                self.assertIn("claude bootstrap: ready", context)
            self.assertEqual(list(state.glob("*.attempted")), [], "no once-per-revision marker")

    def test_reader_is_bound_to_the_receipt_this_bootstrap_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(root)
            self._run(tmp)
            state = root / "home" / ".l9" / "claude"
            installer_id = (state / "installer-id").read_text(encoding="utf-8")
            reader_id = (state / "reader-id").read_text(encoding="utf-8")
            self.assertTrue(installer_id, "the installer must receive a ceremony id")
            self.assertEqual(reader_id, installer_id, "read back the receipt just generated")

    def test_generation_is_not_started_when_the_budget_cannot_cover_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(root, installer_body="#!/usr/bin/env bash\nsleep 300\n")
            state = root / "home" / ".l9" / "claude"
            state.mkdir(parents=True)
            (state / "bootstrap-state.json").write_text(
                '{"state": "READY", "bootstrap_id": "an-earlier-session"}', encoding="utf-8"
            )
            # 5s total minus the 4s reserve leaves nothing for a >=15s generation.
            context = self._run(tmp, budget="5")
            self.assertIn("bootstrap receipt: NOT GENERATED", context)
            self.assertNotIn("generated this bootstrap", context)
            # The earlier session's READY receipt is not reported as this one's.
            self.assertIn("claude bootstrap: unknown", context)
            self.assertNotIn("claude bootstrap: ready", context)

    def test_a_generation_the_budget_cut_short_is_timed_out_not_failed(self) -> None:
        """rc 124 is `timeout` expiring, and the log tail is where it stopped.

        The hosted receipt read "installer FAILED rc=124 — agent bootstrap:
        surface=claude-code ..." — the installer's banner, which says nothing
        about the stage the budget ran out in.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(
                root,
                installer_body=(
                    "#!/usr/bin/env bash\necho 'banner line'\necho 'reached stage-x'\nsleep 300\n"
                ),
            )
            context = self._run(
                tmp,
                extra_env={
                    "L9_BOOTSTRAP_GENERATE_BUDGET": "2",
                    "L9_BOOTSTRAP_GENERATE_MIN": "1",
                    "L9_BOOTSTRAP_DETACH": "0",
                },
            )
            self.assertIn("bootstrap receipt: installer TIMED OUT after 2s (hook budget)", context)
            self.assertIn("reached stage-x", context)
            self.assertNotIn("installer FAILED", context)

    def test_an_installer_the_budget_does_not_cover_finishes_detached(self) -> None:
        """The deadline no longer kills the installer: it completes on its own.

        Killing it at the deadline left the bootstrap receipt INTERRUPTED with
        capabilities and memory never evaluated (2026-09-24, SIGTERM at stage
        memory-readiness after a 15 s clamp).
        """
        if shutil.which("setsid") is None:
            self.skipTest("setsid (util-linux) is not installed; the bounded fallback applies")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            done = root / "installer-finished"
            self._fake_governance(
                root,
                installer_body=(
                    "#!/usr/bin/env bash\necho 'reached stage-x'\nsleep 4\n"
                    f"echo finished > '{done}'\n"
                ),
            )
            started = time.monotonic()
            context = self._run(
                tmp,
                extra_env={"L9_BOOTSTRAP_GENERATE_BUDGET": "1", "L9_BOOTSTRAP_GENERATE_MIN": "1"},
            )
            self.assertLess(time.monotonic() - started, 4, "the hook must not wait it out")
            self.assertIn("bootstrap receipt: installer still running after 1s", context)
            self.assertIn("NOT killed", context)
            self.assertIn("reached stage-x", context)
            self.assertNotIn("TIMED OUT", context)
            deadline = time.monotonic() + 15
            while not done.exists() and time.monotonic() < deadline:
                time.sleep(0.2)
            self.assertTrue(done.exists(), "the detached installer must run to completion")

    def test_a_stale_session_budget_is_named(self) -> None:
        """Settings are read before this session's governance refresh."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gov = self._fake_governance(root)
            template = gov / "environment" / "agents" / "adapters" / "claude-code"
            (template / "settings.template.json").write_text(
                '{"env": {"L9_SESSION_START_BUDGET": "240"}}\n', encoding="utf-8"
            )
            context = self._run(tmp, budget="120")
            self.assertIn("SessionStart budget: 120s loaded at session start", context)
            self.assertIn("registers 240s", context)
            (template / "settings.template.json").write_text(
                '{"env": {"L9_SESSION_START_BUDGET": "120"}}\n', encoding="utf-8"
            )
            self.assertNotIn("SessionStart budget:", self._run(tmp, budget="120"))

    def test_a_failed_generation_is_reported_and_not_masked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_governance(
                root, installer_body="#!/usr/bin/env bash\necho 'boom' >&2\nexit 1\n"
            )
            context = self._run(tmp)
            self.assertIn("bootstrap receipt: installer FAILED rc=1", context)
            self.assertIn("boom", context)
            self.assertNotIn("claude bootstrap: ready", context)


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

    def test_session_start_hook_default_matches_the_configured_budget(self) -> None:
        """The hook's ``${L9_SESSION_START_BUDGET:-N}`` fallback is the configured budget.

        Lockstep alone cannot see a coordinated regression: PR #648 moved budget
        and registration 30 -> 60, and a stale merge resolution in #652 restored
        both to 30. They still agreed, so the lockstep test stayed green while
        every hosted session ran under half the budget the hook was sized for.
        The hook's own fallback kept 60, and this pins the template to it.
        """
        template = json.loads(self.TEMPLATE.read_text(encoding="utf-8"))
        configured = int(template["env"]["L9_SESSION_START_BUDGET"])
        hook = CLAUDE_DIR / "hooks" / "session_start_claude_governance.sh"
        defaults = {
            int(m) for m in re.findall(r"\$\{L9_SESSION_START_BUDGET:-(\d+)\}", hook.read_text())
        }
        self.assertTrue(defaults, "hook no longer reads L9_SESSION_START_BUDGET with a fallback")
        self.assertEqual(
            defaults,
            {configured},
            f"hook falls back to {sorted(defaults)}s but the template configures {configured}s",
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
