#!/usr/bin/env python3
"""Cold-start diagnostic contract: stdout purity, probe states, surface identity.

Covers findings F-08, F-09 and F-10.

Every case runs the REAL ops/scripts/bootstrap_agent_environment.sh against a
synthetic governance root, so the gate under probe can be replaced with a stub
that produces each of the three outcomes on demand. Nothing here needs network,
AWS, Infisical or a capability broker.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"
SESSION_START = REPO / "ops" / "hooks" / "session_start_bootstrap.sh"
ENSURE_UV = REPO / "ops" / "scripts" / "ensure_uv_environment.sh"
ENSURE_WIRED = REPO / "ops" / "scripts" / "ensure_workspace_wired.sh"
RENDERER = REPO / "ops" / "scripts" / "render_bootstrap_context.py"

#: A gate that behaves like the real one: the path rule denies a raw push and
#: never denies `make pr`. A stub that denied both would be correctly reported
#: as BROKEN, not ENFORCED - the probe distinguishes those.
GATE_DENY = """#!/usr/bin/env python3
import json, sys
event = json.load(sys.stdin)
command = (event.get("tool_input") or {}).get("command", "")
if "make pr" in command:
    raise SystemExit(0)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Publish path: `git push` is not sanctioned.",
}}))
"""

#: Both probes denied by the path rule - the sanctioned route is closed.
GATE_DENY_EVERYTHING = """#!/usr/bin/env python3
import json, sys
json.load(sys.stdin)
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Publish path: everything is denied.",
}}))
"""

#: A gate that permits everything - the genuine NOT_ENFORCED case.
GATE_ALLOW = """#!/usr/bin/env python3
import json, sys
json.load(sys.stdin)
"""

#: A gate that crashes. Historically indistinguishable from GATE_ALLOW.
GATE_CRASH = """#!/usr/bin/env python3
import sys
print("Traceback (most recent call last):", file=sys.stderr)
raise SystemExit(1)
"""

#: A gate that exits 0 but returns something that carries no decision.
GATE_MALFORMED = """#!/usr/bin/env python3
import sys
json_ish = '{"hookSpecificOutput": {"hookEventName": "PreToolUse"}}'
print(json_ish)
"""


def tree_state(repo: Path) -> str:
    """Everything git can see changing under ``repo``: porcelain status plus
    the worktree diff.

    Ignored paths (``.venv``, ``.l9``, coverage data, ``__pycache__``) are
    excluded by construction, so comparing two snapshots is stable under the
    canonical xdist + coverage runner; a tracked file rewritten, moved, or
    deleted, and any new unignored file, all change the snapshot. Both flags
    are pinned so a developer's git config (``status.showUntrackedFiles=no``,
    ``diff.external``) cannot blind or reshape the comparison.
    """
    git = ["git", "-C", str(repo)]
    status = subprocess.run(
        [*git, "status", "--porcelain", "--untracked-files=normal"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    diff = subprocess.run(
        [*git, "diff", "--no-ext-diff"], capture_output=True, text=True, check=True
    ).stdout
    return status + diff


def run_session_start(home: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run the real Cursor SessionStart hook against a moved HOME.

    resolve_governance_paths() is pinned to $HOME/.cursor-governance by design
    (rule 06 admits no alternate root), so the chain is isolated by moving HOME:
    the caller has already pointed ``home/.cursor-governance`` at this checkout,
    and every artifact the hook writes lands in the temp tree.
    """
    env = {
        **os.environ,
        "HOME": str(home),
        "CURSOR_PROJECT_DIR": str(workspace),
        "GOVERNANCE_BACKUP_SKIP": "1",
    }
    return subprocess.run(
        ["bash", str(SESSION_START)],
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
        # Cursor launches the hook with the workspace as cwd; the hook's
        # `${CURSOR_PROJECT_DIR:-$PWD}` fallbacks must never see the checkout.
        cwd=workspace,
        check=False,
    )


class PlansStoreSnapshot:
    """Byte-level identity of a real ``~/.cursor/plans`` directory.

    Inode, entry names, file bytes, the ``~/.cursor`` sibling listing and the
    pinned store's contents together prove the three mutations the
    plans-store helper performs on a legacy directory did not happen: copy
    (``store`` gains files), rename (``plans.pre-repo-store.*`` sibling),
    replace (symlink).
    """

    def __init__(self, plans: Path, store: Path) -> None:
        self.plans = plans
        self.store = store
        self.inode = os.lstat(plans).st_ino
        self.is_symlink = plans.is_symlink()
        self.is_dir = plans.is_dir()
        self.files = {
            str(p.relative_to(plans)): p.read_bytes()
            for p in sorted(plans.rglob("*"))
            if p.is_file()
        }
        self.siblings = sorted(p.name for p in plans.parent.iterdir())

    def assert_untouched(self, case: unittest.TestCase, evidence: str) -> None:
        plans = self.plans
        case.assertFalse(plans.is_symlink(), f"~/.cursor/plans became a symlink:\n{evidence}")
        case.assertTrue(plans.is_dir(), f"~/.cursor/plans is no longer a directory:\n{evidence}")
        case.assertEqual(os.lstat(plans).st_ino, self.inode, "~/.cursor/plans was replaced")
        after = PlansStoreSnapshot(plans, self.store)
        case.assertEqual(after.files, self.files, "plan file contents changed under SessionStart")
        renamed = [
            name
            for name in after.siblings
            if name.startswith("plans.") and name not in self.siblings
        ]
        case.assertEqual(renamed, [], f"legacy plans directory was renamed aside: {renamed}")
        copied = sorted(str(p.relative_to(self.store)) for p in self.store.rglob("*"))
        case.assertEqual(copied, [], f"legacy plans were copied into the store: {copied}")


class BootstrapFixture(unittest.TestCase):
    """Builds a synthetic governance root whose gate we control."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.gov = root / "gov"
        self.workspace = root / "ws"
        (self.gov / "ops" / "autonomy").mkdir(parents=True)
        (self.gov / "ops" / "scripts").mkdir(parents=True)
        (self.gov / "kernels").mkdir(parents=True)
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic\n", encoding="utf-8")
        for kernel in ("Recursive Alignment.md", "Validate & Repair.md"):
            (self.gov / "kernels" / kernel).write_text("synthetic\n", encoding="utf-8")
        # Reuse the real locked interpreter so the preflight import check passes.
        real_venv = REPO / ".venv"
        if real_venv.is_dir():
            (self.gov / ".venv").symlink_to(real_venv)
        # The real fingerprint helper, so its stream discipline is under test too.
        (self.gov / "ops" / "scripts" / "ensure_uv_environment.sh").write_text(
            ENSURE_UV.read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=False, capture_output=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def install_gate(self, source: str) -> None:
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        gate.write_text(source, encoding="utf-8")
        gate.chmod(0o755)

    def run_bootstrap(
        self, *extra: str, surface: str = "claude-code"
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("L9_GOVERNANCE_SURFACE", None)
        return subprocess.run(
            [
                "bash",
                str(BOOTSTRAP),
                "--surface",
                surface,
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
            check=False,
        )


class StdoutMachineContractTests(BootstrapFixture):
    """F-08 - stdout is the machine channel and carries nothing else."""

    def test_bootstrap_writes_nothing_to_stdout(self) -> None:
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap()
        self.assertEqual(
            proc.stdout,
            "",
            f"bootstrap polluted the machine channel with: {proc.stdout!r}",
        )

    def test_stdout_stays_empty_without_quiet(self) -> None:
        """The contract must not depend on the caller remembering --quiet."""
        self.install_gate(GATE_DENY)
        verbose = self.run_bootstrap()
        quiet = self.run_bootstrap("--quiet")
        self.assertEqual(verbose.stdout, "")
        self.assertEqual(quiet.stdout, "")

    def test_diagnostics_are_still_produced_on_stderr(self) -> None:
        """Redirected, not suppressed."""
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap()
        self.assertIn("publish_path_gate=", proc.stderr)
        self.assertIn("interpreter:", proc.stderr)

    def test_uv_fingerprint_diagnostic_is_stderr_only(self) -> None:
        """F-08 / section 25 - the specific helper that leaked, isolated."""
        proc = subprocess.run(
            ["bash", str(ENSURE_UV), str(REPO), "apply"],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        self.assertEqual(proc.stdout, "", f"ensure_uv wrote to stdout: {proc.stdout!r}")
        self.assertIn("UV:", proc.stderr)

    def test_session_start_stdout_parses_as_one_json_document(self) -> None:
        """The renderer's input contract, asserted with no cleanup whatsoever.

        resolve_governance_paths() is pinned to $HOME/.cursor-governance by
        design (rule 06 admits no alternate root), so the chain is isolated by
        moving HOME instead: the temp HOME's clone points at this checkout, and
        every artifact the hook writes lands in the temp tree.

        "Every artifact" has to be arranged, not assumed. SessionStart does
        not read or emit the plans store. The machine plans store that
        setup_workspace_symlinks.sh wires into ``<ws>/.cursor/plans`` still
        defaults to ``<gov>/docs/plans`` for a consumer workspace, so the
        store is pinned to the workspace through the library's own stamp
        (ops/scripts/lib/cursor_plans_store.sh reads
        ``~/.cursor/l9-plans-store`` first), the workspace gets its own WIP
        root, and the snapshot comparison below proves the checkout is
        untouched.
        """
        home = Path(self._tmp.name) / "home"
        home.mkdir()
        (home / ".cursor-governance").symlink_to(REPO)
        plans_store = self.workspace / "docs" / "plans"
        plans_store.mkdir(parents=True)
        spent = plans_store / "spent_stay_abcd1234.plan.md"
        spent.write_text(
            "---\nname: spent-stay\nbuilt: true\ntodos:\n"
            "  - id: t1\n    content: done\n    status: completed\n---\n\n# stay\n",
            encoding="utf-8",
        )
        (self.workspace / "WIP").mkdir()
        (home / ".cursor").mkdir()
        (home / ".cursor" / "l9-plans-store").write_text(f"{plans_store}\n", encoding="utf-8")
        before = tree_state(REPO)
        proc = run_session_start(home, self.workspace)
        after = tree_state(REPO)
        # No find-first-brace, no line filtering, no take-last-line.
        payload = json.loads(proc.stdout)
        self.assertIsInstance(payload, dict)
        self.assertIn("additional_context", payload)
        self.assertNotIn("### Plan audit", payload["additional_context"])
        self.assertNotIn("audit_pipeline.py", payload["additional_context"])
        self.assertEqual(
            before,
            after,
            "the Cursor SessionStart hook wrote into the checked-out repository; the "
            "plan store, WIP root and every reconciler target must resolve to the temp tree",
        )
        # The plan store the hook wired for this workspace is the temp one.
        wired = self.workspace / ".cursor" / "plans"
        if wired.exists():
            self.assertEqual(wired.resolve(), plans_store.resolve())
        self.assertTrue(
            spent.is_file(),
            "SessionStart must not move a spent plan out of the live store",
        )

        render = subprocess.run(
            [str(REPO / ".venv" / "bin" / "python"), str(RENDERER)],
            input=proc.stdout,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(render.returncode, 0, f"renderer rejected stdout: {render.stdout}")
        # Diagnostics survived; they simply moved off the machine channel.
        self.assertNotEqual(proc.stderr.strip(), "")


class SessionStartPlansStoreTests(BootstrapFixture):
    """SessionStart performs no plans-store mutation (SESSIONSTART_NO_PLAN_SURFACE_V1).

    The direct plan-audit call was removed from the hook, but the hook still
    heals unhealthy links through ``ensure_workspace_wired.sh``, whose default
    plans mode migrates a legacy real ``~/.cursor/plans`` directory into the
    tracked store (copy, rename aside, replace with a symlink). The first
    SessionStart on a legacy machine is a supported initialization path, so the
    hook must wire the workspace links without touching that directory.
    Migration stays with the manual setup commands.
    """

    def _legacy_home(self) -> tuple[Path, Path, PlansStoreSnapshot]:
        """Temp HOME whose ``~/.cursor/plans`` is a legacy real directory.

        The machine store a consumer workspace would migrate into defaults to
        ``<gov>/docs/plans``, i.e. this checkout, so it is pinned to an empty
        temp directory through the library's own first-run stamp
        (``~/.cursor/l9-plans-store``): a migration then lands in ``store``
        instead of polluting the repository, and an empty ``store`` afterwards
        is the proof that no copy happened.
        """
        home = Path(self._tmp.name) / "home"
        home.mkdir()
        (home / ".cursor-governance").symlink_to(REPO)
        store = Path(self._tmp.name) / "store"
        store.mkdir()
        plans = home / ".cursor" / "plans"
        (plans / "BUILT").mkdir(parents=True)
        (home / ".cursor" / "l9-plans-store").write_text(f"{store}\n", encoding="utf-8")
        (plans / "legacy_abcd1234.plan.md").write_text(
            "---\nname: legacy\ntodos: []\n---\n\n# legacy\n", encoding="utf-8"
        )
        (plans / "BUILT" / "old_deadbeef.plan.md").write_text("built\n", encoding="utf-8")
        return home, plans, PlansStoreSnapshot(plans, store)

    def _assert_workspace_wired(self, home: Path, evidence: str) -> None:
        ws = self.workspace
        gc = Path(os.path.realpath(home / ".cursor-governance"))
        self.assertTrue((ws / ".cursor-commands").is_symlink(), evidence)
        self.assertEqual(Path(os.path.realpath(ws / ".cursor-commands")), gc)
        plans_link = ws / ".cursor" / "plans"
        self.assertTrue(plans_link.is_symlink(), evidence)
        self.assertEqual(
            Path(os.path.realpath(plans_link)),
            Path(os.path.realpath(home / ".cursor" / "plans")),
            "workspace .cursor/plans must resolve to the legacy directory as-is",
        )
        law = ws / ".cursor" / "governance" / "CANONICAL_LAW.md"
        self.assertTrue(law.is_symlink(), evidence)
        plugin = home / ".cursor" / "plugins" / "local" / "l9-governance"
        self.assertTrue(plugin.is_symlink(), evidence)
        self.assertEqual(Path(os.path.realpath(plugin)), gc)

    def test_session_start_never_migrates_a_legacy_real_plans_directory(self) -> None:
        home, _plans, snapshot = self._legacy_home()
        before = tree_state(REPO)
        proc = run_session_start(home, self.workspace)
        after = tree_state(REPO)
        evidence = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        payload = json.loads(proc.stdout)
        context = payload["additional_context"]
        self.assertEqual(before, after, "the hook wrote into the checked-out repository")
        snapshot.assert_untouched(self, evidence)
        # Wiring still succeeded: the links ensure_workspace_wired.sh owns exist
        # and the hook reports the links-only heal, not the full-setup fallback
        # (setup_workspace_symlinks.sh migrates unconditionally).
        self._assert_workspace_wired(home, evidence)
        self.assertIn("- wire: auto-wired links-only", context, evidence)
        self.assertNotIn("auto-wired (full setup)", context, evidence)

    def test_links_only_plans_mode_wires_without_touching_the_store(self) -> None:
        """The mode the hook sets, exercised directly on the helper."""
        home, _plans, snapshot = self._legacy_home()
        env = {**os.environ, "HOME": str(home)}
        env["L9_WIRE_LINKS_ONLY"] = "1"
        env["L9_PLANS_STORE_MODE"] = "links-only"
        proc = subprocess.run(
            ["bash", str(ENSURE_WIRED), str(self.workspace)],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            check=False,
        )
        evidence = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        self.assertEqual(proc.returncode, 0, evidence)
        snapshot.assert_untouched(self, evidence)
        self._assert_workspace_wired(home, evidence)
        self.assertNotIn("MIGRATED:", proc.stdout, evidence)
        second = subprocess.run(
            ["bash", str(ENSURE_WIRED), str(self.workspace)],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            check=False,
        )
        self.assertIn("already wired", second.stdout, second.stdout + second.stderr)
        snapshot.assert_untouched(self, second.stdout + second.stderr)

    def test_default_plans_mode_still_migrates_for_manual_callers(self) -> None:
        """Manual setup keeps ownership of the migration; only SessionStart opts out."""
        home, plans, snapshot = self._legacy_home()
        env = {**os.environ, "HOME": str(home)}
        env["L9_WIRE_LINKS_ONLY"] = "1"
        env.pop("L9_PLANS_STORE_MODE", None)
        proc = subprocess.run(
            ["bash", str(ENSURE_WIRED), str(self.workspace)],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
            check=False,
        )
        evidence = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        self.assertEqual(proc.returncode, 0, evidence)
        self.assertIn("MIGRATED:", proc.stdout, evidence)
        self.assertTrue(plans.is_symlink(), evidence)
        renamed = [p for p in plans.parent.iterdir() if p.name.startswith("plans.pre-repo-store.")]
        self.assertEqual(len(renamed), 1, evidence)
        self.assertTrue((renamed[0] / "legacy_abcd1234.plan.md").is_file())
        # The copy went to the pinned temp store, never into this checkout.
        self.assertEqual(Path(os.path.realpath(plans)), Path(os.path.realpath(snapshot.store)))
        self.assertTrue((snapshot.store / "legacy_abcd1234.plan.md").is_file(), evidence)
        self.assertTrue((snapshot.store / "BUILT" / "old_deadbeef.plan.md").is_file(), evidence)

    def test_hook_sets_links_only_plans_mode_on_every_heal(self) -> None:
        """Static twin of the behavioral case: no ENSURE call without the mode."""
        text = SESSION_START.read_text(encoding="utf-8")
        calls = [line for line in text.splitlines() if 'bash "$ENSURE"' in line]
        self.assertGreaterEqual(len(calls), 2, "hook lost its links-only heal / retry")
        for line in calls:
            self.assertIn("L9_PLANS_STORE_MODE=links-only", line, line)
            self.assertIn("L9_WIRE_LINKS_ONLY=1", line, line)


class PublishPathProbeStateTests(BootstrapFixture):
    """F-09 - three states, and PROBE_ERROR is never NOT_ENFORCED."""

    def _state(self, proc: subprocess.CompletedProcess[str]) -> str:
        for line in proc.stderr.splitlines():
            if line.startswith("publish_path_gate="):
                return line.split("=", 1)[1].strip()
        self.fail(f"no publish_path_gate state emitted; stderr was:\n{proc.stderr}")
        raise AssertionError(f"no publish_path_gate state emitted; stderr was:\n{proc.stderr}")

    def test_explicit_deny_reports_enforced(self) -> None:
        self.install_gate(GATE_DENY)
        self.assertEqual(self._state(self.run_bootstrap()), "ENFORCED")

    def test_explicit_allow_reports_not_enforced(self) -> None:
        self.install_gate(GATE_ALLOW)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "NOT_ENFORCED")
        self.assertIn("NOT ENFORCED", proc.stderr)

    def test_gate_crash_reports_probe_error_not_not_enforced(self) -> None:
        """The exact inversion that made every session cry wolf."""
        self.install_gate(GATE_CRASH)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "PROBE_ERROR")
        self.assertNotIn("NOT ENFORCED", proc.stderr)
        self.assertIn("could not reach a verdict", proc.stderr)

    def test_malformed_response_reports_probe_error(self) -> None:
        self.install_gate(GATE_MALFORMED)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "PROBE_ERROR")
        self.assertNotIn("NOT ENFORCED", proc.stderr)

    def test_path_rule_denying_make_pr_reports_not_enforced(self) -> None:
        """`make pr` denied by the path rule means the only route out is closed."""
        self.install_gate(GATE_DENY_EVERYTHING)
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "NOT_ENFORCED")
        self.assertIn("BROKEN", proc.stderr)

    def test_missing_gate_reports_probe_error(self) -> None:
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        if gate.exists():
            gate.unlink()
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "PROBE_ERROR")

    def test_probe_event_carries_cwd(self) -> None:
        """Section 10 - the probe must test policy, not malformed-input handling."""
        recorder = self.gov / "event.json"
        self.install_gate(
            "#!/usr/bin/env python3\n"
            "import json, sys, pathlib\n"
            "event = json.load(sys.stdin)\n"
            f"pathlib.Path({str(recorder)!r}).write_text(json.dumps(event))\n"
            'print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",'
            ' "permissionDecision": "deny",'
            ' "permissionDecisionReason": "Publish path: denied."}}))\n'
        )
        self.run_bootstrap()
        event = json.loads(recorder.read_text(encoding="utf-8"))
        self.assertEqual(event.get("cwd"), str(self.workspace))


class SurfacePropagationTests(BootstrapFixture):
    """F-10 - attribution follows L9_GOVERNANCE_SURFACE, never a constant."""

    def test_claude_code_surface_is_reported_as_claude_code(self) -> None:
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap(surface="claude-code")
        self.assertIn("surface=claude-code", proc.stderr)
        self.assertNotIn("surface=cursor", proc.stderr)

    def test_cursor_surface_still_reports_cursor(self) -> None:
        self.install_gate(GATE_DENY)
        proc = self.run_bootstrap(surface="cursor")
        self.assertIn("surface=cursor", proc.stderr)

    def test_session_start_forwards_the_runtime_surface(self) -> None:
        """The hook must pass the variable through, not a hard-coded id."""
        text = SESSION_START.read_text(encoding="utf-8")
        self.assertIn('--surface "${L9_GOVERNANCE_SURFACE:-cursor}"', text)
        self.assertNotIn("--surface cursor \\", text)

    def test_default_is_cursor_when_variable_absent(self) -> None:
        script = "\n".join(
            [
                "set -u",
                'L9_GOVERNANCE_SURFACE=""',
                'printf "%s\\n" "${L9_GOVERNANCE_SURFACE:-cursor}"',
            ]
        )
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
        self.assertEqual(proc.stdout.strip(), "cursor")


if __name__ == "__main__":
    unittest.main()
