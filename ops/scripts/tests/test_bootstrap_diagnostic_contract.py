#!/usr/bin/env python3
"""Cold-start diagnostic contract: stdout purity, probe states, surface identity.

Covers findings F-08, F-09 and F-10.

Every case runs the REAL ops/scripts/bootstrap_agent_environment.sh against a
synthetic source/governance/workspace/HOME tree, using the readiness suite's
locked-prefix/version fixtures and guarded tools. Check probes use only the
stateless path-rule API. Legacy SessionStart/wiring cases copy their exact
owners and stub activation/auth/apply collaborators; no live tree, venv,
network, AWS, Infisical or capability broker is used.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _bootstrap_fixtures():
    """Load the shared bootstrap fixtures by file path, not as ``tests.ops...``.

    Under ``--import-mode=importlib`` the name ``tests`` is whichever regular
    ``tests`` package was imported first (e.g.
    ``environment/agents/adapters/claude-agent-sdk/tests``), so a dotted import
    of ``tests.ops.scripts`` fails or succeeds on collection order alone.
    """
    name = "_l9_bootstrap_readiness_fixtures"
    module = sys.modules.get(name)
    if module is None:
        path = _REPO_ROOT / "tests" / "ops" / "scripts" / "test_agent_bootstrap_readiness.py"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


_FIXTURES = _bootstrap_fixtures()
REAL_PYTHON = _FIXTURES.REAL_PYTHON
BootstrapTree = _FIXTURES.BootstrapTree
put = _FIXTURES.put
snapshot = _FIXTURES.snapshot

REPO = Path(__file__).resolve().parents[3]
SESSION_START = REPO / "ops" / "hooks" / "session_start_bootstrap.sh"

#: A gate that behaves like the real one: the path rule denies a raw push and
#: never denies `make pr`. A stub that denied both would be correctly reported
#: as BROKEN, not ENFORCED - the probe distinguishes those.
GATE_DENY = """def publish_path_workflow_deny(command):
    if command == "make push":
        return "Publish path: `make push` is not sanctioned."
    assert command == "make pr", command
    return None
"""

#: Both probes denied by the path rule - the sanctioned route is closed.
GATE_DENY_EVERYTHING = """def publish_path_workflow_deny(command):
    return "Publish path: everything is denied."
"""

#: A gate that permits everything - the genuine NOT_ENFORCED case.
GATE_ALLOW = """def publish_path_workflow_deny(command):
    return None
"""

#: A gate that crashes. Historically indistinguishable from GATE_ALLOW.
GATE_CRASH = """def publish_path_workflow_deny(command):
    raise RuntimeError("fixture path-rule crash")
"""

#: A gate that exits 0 but returns something that carries no decision.
GATE_MALFORMED = """def publish_path_workflow_deny(command):
    print('{"hookSpecificOutput": {"hookEventName": "PreToolUse"}}')
    return None
"""


def run_session_start(tree: BootstrapTree) -> subprocess.CompletedProcess[str]:
    """Run the exact copied hook; all reachable writers are fixture-owned."""
    env = {
        **tree.env,
        "CURSOR_PROJECT_DIR": str(tree.ws),
        "GOVERNANCE_BACKUP_SKIP": "1",
        # No detached writer may outlive TemporaryDirectory cleanup.
        "L9_BOOTSTRAP_SYNC": "1",
    }
    return subprocess.run(
        ["/bin/bash", str(tree.gov / "ops/hooks/session_start_bootstrap.sh")],
        capture_output=True,
        text=True,
        timeout=45,
        env=env,
        cwd=tree.ws,
        input="",
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
    """Reuse the full-script readiness fixture, never the checkout's venv."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = BootstrapTree(Path(self._tmp.name))
        self.gov = self.tree.gov
        self.workspace = self.tree.ws
        put(
            self.gov / "ops/memory/namespace_context.py",
            "import os\nfrom types import SimpleNamespace\n"
            "def resolve_namespace_context(root):\n"
            "    assert os.environ['L9_GOVERNANCE_SURFACE'] in ('manus', 'cursor', 'claude-code')\n"
            "    return SimpleNamespace(write_namespace_hint='fixture', method='fixture')\n",
        )

    def isolate_session_writers(self) -> None:
        """Copy only admitted owners; activation/auth/apply stay explicit stubs.

        No installer, backup, memory provider, worktree reconciler or full-setup
        fallback is materialized. Mutation commands reject every path outside
        this fixture, and exported functions preserve guards even when the
        exact SessionStart hook prepends platform-specific PATH entries.
        """
        self.tree.stub_apply()
        # SessionStart executes governance's bootstrap, whereas BootstrapTree's
        # apply fixture executes source's. Stub the writer at both actual owners.
        shutil.copy2(
            self.tree.source / "ops/scripts/lib/session_git_excludes.sh",
            self.gov / "ops/scripts/lib/session_git_excludes.sh",
        )
        for name in (
            "ops/hooks/session_start_bootstrap.sh",
            "ops/scripts/ensure_workspace_wired.sh",
            "ops/scripts/resolve_governance_paths.sh",
            "ops/scripts/render_bootstrap_context.py",
            "ops/scripts/lib/workspace_kind.sh",
            "ops/scripts/lib/workspace_link_health.sh",
            "ops/scripts/lib/cursor_plans_store.sh",
            "ops/scripts/lib/plugin_siblings.sh",
        ):
            original = REPO / name
            target = self.gov / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original, target)
            self.assertEqual(target.read_bytes(), original.read_bytes())
        (self.gov / "skills").mkdir()
        (self.tree.home / ".cursor-governance").symlink_to(self.gov)
        put(
            self.gov / "ops/scripts/governance_activate_fresh.sh",
            "#!/bin/bash\necho 'STATUS action=fixture sha=unknown remote_sha=unknown "
            "detail=isolated-no-network'\n",
            executable=True,
        )
        put(
            self.gov / "ops/secrets/session_start_secrets.py",
            "import json, os, sys\nfrom pathlib import Path\n"
            "assert os.environ['L9_GOVERNANCE_SURFACE'] in ('cursor', 'claude-code')\n"
            "print('FIXTURE_AUTH_NOT_LIVE')\n"
            "dest = Path(sys.argv[sys.argv.index('--receipt-out')+1])\n"
            "dest.write_text(json.dumps({'ok': True}))\n",
        )
        self.tree.env.update(
            L9_GOVERNANCE_SURFACE="cursor",
            L9_GOVERNANCE_DIR=str(self.gov),
            ALLOW_METADATA_PY="1",
            PYTHONDONTWRITEBYTECODE="1",
            GRAPHITI_MEMORY_ENABLED="0",
            TMPDIR=str(self.tree.root / "tmp"),
        )
        (self.tree.root / "tmp").mkdir()
        # Python checks both lexical paths and symlink targets before a writer
        # is invoked. The temporary root itself is never an admitted operand.
        guard = self.tree.root / "guard_mutation.py"
        put(
            guard,
            "import os, subprocess, sys\nfrom pathlib import Path\n"
            f"root = Path({str(self.tree.root)!r}).resolve()\n"
            "tool, *args = sys.argv[1:]\n"
            "for arg in args:\n"
            "    if arg.startswith('-') or (tool.endswith('/chmod') and arg == '+x'):\n"
            "        continue\n"
            "    path = Path(os.path.abspath(arg))\n"
            "    if path == root or not path.is_relative_to(root) or "
            "not path.resolve().is_relative_to(root):\n"
            "        raise SystemExit('FORBIDDEN external mutation: ' + arg)\n"
            "raise SystemExit(subprocess.run([tool, *args], check=False).returncode)\n",
        )
        for name in ("mkdir", "rm", "mv", "cp", "ln", "chmod", "mktemp"):
            tool = shutil.which(name)
            self.assertIsNotNone(tool)
            put(
                self.tree.bin / name,
                "#!/bin/bash\n"
                f"exec {shlex.quote(REAL_PYTHON)} -B -I {shlex.quote(str(guard))} "
                f'{shlex.quote(str(tool))} "$@"\n',
                executable=True,
            )
        for name in ("wc",):
            (self.tree.bin / name).symlink_to(shutil.which(name))
        shell_env = self.tree.root / "fixture_shell_env.sh"
        put(
            shell_env,
            "\n".join(
                f'{tool.name}() {{ {shlex.quote(str(tool))} "$@"; }}; export -f {tool.name}'
                for tool in sorted(self.tree.bin.iterdir())
            )
            + "\n",
        )
        self.tree.env["BASH_ENV"] = str(shell_env)

    def install_gate(self, source: str) -> None:
        gate = self.gov / "ops" / "autonomy" / "local_execution_gate.py"
        put(
            gate,
            source + "\nif __name__ == '__main__':\n"
            "    raise RuntimeError('FORBIDDEN full recording gate in check')\n",
        )

    def run_bootstrap(
        self, *extra: str, surface: str = "claude-code"
    ) -> subprocess.CompletedProcess[str]:
        before = snapshot(self.tree.root)
        proc = subprocess.run(
            [
                "/bin/bash",
                str(self.tree.source / "ops/scripts/bootstrap_agent_environment.sh"),
                "--surface",
                surface,
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                "--check",
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=45,
            env=self.tree.env,
            cwd=self.workspace,
            check=False,
        )
        self.assertEqual(snapshot(self.tree.root), before, proc.stderr)
        self.assertEqual(proc.returncode, 6, proc.stderr)  # observational auth is UNKNOWN
        self.assertIn("observed auth UNKNOWN", proc.stderr)
        self.assertNotIn("Agent environment ready", proc.stderr)
        self.assertNotIn("FORBIDDEN", proc.stderr)
        return proc


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
        proc = self.tree.unchanged_check("ops/scripts/ensure_uv_environment.sh", code=0)
        self.assertEqual(proc.stdout, "", f"ensure_uv wrote to stdout: {proc.stdout!r}")
        self.assertIn("UV:", proc.stderr)

    def test_session_start_stdout_parses_as_one_json_document(self) -> None:
        """The renderer's input contract, asserted with no cleanup whatsoever.

        resolve_governance_paths() is pinned to $HOME/.cursor-governance by
        design (rule 06 admits no alternate root), so the chain is isolated by
        moving HOME and copying exact owners: the temp HOME's clone points at
        synthetic governance, never this checkout or its installed interpreter.

        "Every artifact" has to be arranged, not assumed. SessionStart does
        not read or emit the plans store. The machine plans store that
        setup_workspace_symlinks.sh wires into ``<ws>/.cursor/plans`` still
        defaults to ``<gov>/docs/plans`` for a consumer workspace, so the
        store is pinned to the workspace through the library's own stamp
        (ops/scripts/lib/cursor_plans_store.sh reads
        ``~/.cursor/l9-plans-store`` first), and the snapshot comparison
        below includes ignored paths, modes and mtimes in both copied owners.
        """
        self.isolate_session_writers()
        home = self.tree.home
        plans_store = self.workspace / "docs" / "plans"
        plans_store.mkdir(parents=True)
        spent = plans_store / "spent_stay_abcd1234.plan.md"
        spent.write_text(
            "---\nname: spent-stay\nbuilt: true\ntodos:\n"
            "  - id: t1\n    content: done\n    status: completed\n---\n\n# stay\n",
            encoding="utf-8",
        )
        (home / ".cursor").mkdir()
        (home / ".cursor" / "l9-plans-store").write_text(f"{plans_store}\n", encoding="utf-8")
        before = (snapshot(self.tree.source), snapshot(self.gov))
        proc = run_session_start(self.tree)
        after = (snapshot(self.tree.source), snapshot(self.gov))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("FORBIDDEN", proc.stderr)
        # No find-first-brace, no line filtering, no take-last-line.
        payload = json.loads(proc.stdout)
        self.assertIsInstance(payload, dict)
        self.assertIn("additional_context", payload)
        self.assertNotIn("### Plan audit", payload["additional_context"])
        self.assertNotIn("audit_pipeline.py", payload["additional_context"])
        self.assertEqual(
            before,
            after,
            "the Cursor SessionStart hook wrote into a copied owner; the "
            "plan store and every writer target must resolve to the temp HOME/workspace",
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
            [
                str(self.gov / ".venv/bin/python"),
                str(self.gov / "ops/scripts/render_bootstrap_context.py"),
            ],
            input=proc.stdout,
            capture_output=True,
            text=True,
            timeout=30,
            env=self.tree.env,
            cwd=self.workspace,
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
        ``<gov>/docs/plans``, so it is pinned to an empty
        temp directory through the library's own first-run stamp
        (``~/.cursor/l9-plans-store``): a migration then lands in ``store``
        instead of polluting the repository, and an empty ``store`` afterwards
        is the proof that no copy happened.
        """
        self.isolate_session_writers()
        home = self.tree.home
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
        before = self._owner_state()
        proc = run_session_start(self.tree)
        after = self._owner_state()
        evidence = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        self.assertEqual(proc.returncode, 0, evidence)
        self.assertNotIn("FORBIDDEN", proc.stderr, evidence)
        payload = json.loads(proc.stdout)
        context = payload["additional_context"]
        self.assertEqual(before, after, "the hook wrote into a copied owner")
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
        env = dict(self.tree.env)
        env["L9_WIRE_LINKS_ONLY"] = "1"
        env["L9_PLANS_STORE_MODE"] = "links-only"
        before = self._owner_state()
        proc = subprocess.run(
            [
                "/bin/bash",
                str(self.gov / "ops/scripts/ensure_workspace_wired.sh"),
                str(self.workspace),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            env=env,
            cwd=self.workspace,
            check=False,
        )
        evidence = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        self.assertEqual(proc.returncode, 0, evidence)
        self.assertNotIn("FORBIDDEN", evidence)
        self.assertEqual(self._owner_state(), before, evidence)
        snapshot.assert_untouched(self, evidence)
        self._assert_workspace_wired(home, evidence)
        self.assertNotIn("MIGRATED:", proc.stdout, evidence)
        second = subprocess.run(
            [
                "/bin/bash",
                str(self.gov / "ops/scripts/ensure_workspace_wired.sh"),
                str(self.workspace),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            env=env,
            cwd=self.workspace,
            check=False,
        )
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertNotIn("FORBIDDEN", second.stdout + second.stderr)
        self.assertEqual(self._owner_state(), before, second.stdout + second.stderr)
        self.assertIn("already wired", second.stdout, second.stdout + second.stderr)
        snapshot.assert_untouched(self, second.stdout + second.stderr)

    def test_default_plans_mode_still_migrates_for_manual_callers(self) -> None:
        """Manual setup keeps ownership of the migration; only SessionStart opts out."""
        home, plans, snapshot = self._legacy_home()
        env = dict(self.tree.env)
        env["L9_WIRE_LINKS_ONLY"] = "1"
        env.pop("L9_PLANS_STORE_MODE", None)
        before = self._owner_state()
        proc = subprocess.run(
            [
                "/bin/bash",
                str(self.gov / "ops/scripts/ensure_workspace_wired.sh"),
                str(self.workspace),
            ],
            capture_output=True,
            text=True,
            timeout=45,
            env=env,
            cwd=self.workspace,
            check=False,
        )
        evidence = f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        self.assertEqual(proc.returncode, 0, evidence)
        self.assertNotIn("FORBIDDEN", evidence)
        self.assertEqual(self._owner_state(), before, evidence)
        self.assertIn("MIGRATED:", proc.stdout, evidence)
        self.assertTrue(plans.is_symlink(), evidence)
        renamed = [p for p in plans.parent.iterdir() if p.name.startswith("plans.pre-repo-store.")]
        self.assertEqual(len(renamed), 1, evidence)
        self.assertTrue((renamed[0] / "legacy_abcd1234.plan.md").is_file())
        # The copy went to the pinned temp store, never into this checkout.
        self.assertEqual(Path(os.path.realpath(plans)), Path(os.path.realpath(snapshot.store)))
        self.assertTrue((snapshot.store / "legacy_abcd1234.plan.md").is_file(), evidence)
        self.assertTrue((snapshot.store / "BUILT" / "old_deadbeef.plan.md").is_file(), evidence)

    def _owner_state(self) -> tuple[dict, dict]:
        return snapshot(self.tree.source), snapshot(self.gov)

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

    def test_stateless_probe_carries_workspace_cwd_and_surface(self) -> None:
        """Section 10 - check evaluates the path API, never a recording event CLI."""
        self.install_gate(
            "import os\nfrom pathlib import Path\n"
            "def publish_path_workflow_deny(command):\n"
            f"    assert Path.cwd() == Path({str(self.workspace)!r})\n"
            "    assert os.environ['L9_GOVERNANCE_SURFACE'] == 'claude-code'\n"
            "    assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1'\n"
            "    assert command in ('make push', 'make pr'), command\n"
            "    return 'Publish path: denied.' if command == 'make push' else None\n"
        )
        proc = self.run_bootstrap()
        self.assertEqual(self._state(proc), "ENFORCED")
        self.assertIn("path-rule-only diagnostic; NOT host enforcement", proc.stderr)


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
