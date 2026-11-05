#!/usr/bin/env python3
"""The installer restores its mounts and verifies them (B-16, B-21, B-22).

Covers acceptance tests T-23, T-24, T-25.

None of these ran on the audited environment, because install.sh was never
reached: `.claude/rules` and `.claude/skills` were absent and `.git/info/exclude`
still held only git's default template — which is how the audit established that
the installer had not executed at all.

The shared bootstrap is stubbed so these exercise the ADAPTER's own wiring
without a network round trip; the shared half has its own suite.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]


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
BootstrapTree = _FIXTURES.BootstrapTree
put = _FIXTURES.put
snapshot = _FIXTURES.snapshot

REPO = Path(__file__).resolve().parents[5]
INSTALL = REPO / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"


class InstallMountTests(unittest.TestCase):
    """Runs the real install.sh against the real governance tree."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        (self.home / ".claude").mkdir(parents=True)
        self.workspace = self.root / "consumer"
        self.workspace.mkdir()
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        self.receipt = self.root / "bootstrap-state.json"
        self.addCleanup(self._tmp.cleanup)

    def _materialized_artifacts(self) -> list[str]:
        """The wiring files the settings reconciler writes into a workspace.

        Read from the reconciler that writes them rather than restated here, for
        the same reason install.sh reads it: two copies of this list drift, and
        the drift is silent -- a glob dropped from one side is only visible as
        untracked dirt or as a consumer forced to `git add -f`.
        """
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "ops" / "scripts" / "reconcile_claude_settings.py"),
                "--print-workspace-artifacts",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        artifacts = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        self.assertTrue(artifacts, "reconciler reported no workspace artifacts")
        return artifacts

    def _run(self, workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt),
                # The shared bootstrap needs network and a uv sync; its own suite
                # covers it. Skipping it here keeps this test about the adapter.
                "L9_SKIP_SHARED_BOOTSTRAP": "1",
                "L9_GRAPHITI_PROBE_SKIP": "1",
            }
        )
        env.pop("L9_GOVERNANCE_DIR", None)
        return subprocess.run(
            [
                "bash",
                str(INSTALL),
                "--governance",
                str(REPO),
                "--workspace",
                str(workspace or self.workspace),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    # -- T-24 ---------------------------------------------------------------

    def test_mounts_and_excludes_are_installed_and_verified(self) -> None:
        result = self._run()
        self.assertIn(result.returncode, (0, 1), result.stderr[-2000:])

        claude = self.workspace / ".claude"
        self.assertTrue((claude / "settings.json").is_file(), "settings triad not installed")
        self.assertTrue((claude / "hooks").is_dir(), "hooks not installed")

        exclude = self.workspace / ".git" / "info" / "exclude"
        self.assertTrue(exclude.is_file())
        body = exclude.read_text(encoding="utf-8")
        # The whole projected set, not a subset: .mcp.json is a render of
        # mcp.template.json and shows as untracked in every consumer that does not
        # commit it. Asserting the full list is what stops a glob being dropped.
        for glob in (
            ".claude/skills",
            ".claude/rules",
            ".claude/commands",
            ".mcp.json",
            ".claude/settings.local.json",
        ):
            self.assertIn(glob, body, f"{glob} must be excluded from the consumer repo")
        for blanket in (".claude/", "/.claude/", ".claude", "/.claude"):
            self.assertNotIn(
                blanket,
                body.splitlines(),
                f"{blanket} is Option A and hides committable consumer wiring",
            )
        # The materialized wiring is the FOURTH category, and tracked-ness
        # decides it (install.sh, "Tracked-ness decides, exactly as
        # reconcile_claude_settings.settings_is_git_tracked already defines the
        # ownership signal"). This workspace has no commits, so settings.json and
        # the two hooks are untracked: governance injected them, so governance
        # contains them rather than leaving untracked dirt after every session.
        # The tracked branch — where they are repo content and must stay
        # visible — is asserted by
        # test_committed_consumer_wiring_is_left_visible below.
        for artifact in self._materialized_artifacts():
            self.assertIn(
                artifact,
                body,
                f"{artifact} was injected and untracked here, so it must be contained",
            )

    def test_excludes_are_honoured_inside_a_linked_worktree(self) -> None:
        """The globs must land where git READS them, not merely be written.

        `git rev-parse --git-dir` in a linked worktree is .git/worktrees/<name>/,
        but git reads $GIT_COMMON_DIR/info/exclude — so writing to the former is a
        silent no-op. Rules 49/96 give every mutating agent its own worktree, so
        that is the normal case, not the exotic one. The primary-clone test above
        cannot catch this: there the two directories are the same path.

        Asserts through `git check-ignore` rather than a file location, so the
        contract is the outcome and a future relocation stays free.
        """
        subprocess.run(
            ["git", "-C", str(self.workspace), "commit", "-q", "--allow-empty", "-m", "base"],
            check=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@t",
            },
        )
        linked = self.root / "linked"
        subprocess.run(
            ["git", "-C", str(self.workspace), "worktree", "add", "-q", "-b", "wt", str(linked)],
            check=True,
        )
        self.assertNotEqual(
            subprocess.run(
                ["git", "-C", str(linked), "rev-parse", "--git-dir"], capture_output=True, text=True
            ).stdout.strip(),
            subprocess.run(
                ["git", "-C", str(linked), "rev-parse", "--git-common-dir"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "fixture is not a linked worktree — the two dirs must differ",
        )

        result = self._run(workspace=linked)
        self.assertIn(result.returncode, (0, 1), result.stderr[-2000:])

        # Probe each path itself, never a child: the installer mounts
        # .claude/rules and .claude/skills as SYMLINKS into governance, and
        # check-ignore refuses a pathspec "beyond a symbolic link".
        for glob in (
            ".claude/skills",
            ".claude/rules",
            ".claude/commands",
            ".mcp.json",
            ".claude/settings.local.json",
        ):
            self.assertEqual(
                0,
                subprocess.run(["git", "-C", str(linked), "check-ignore", glob]).returncode,
                f"{glob} written but not honoured by git inside a linked worktree",
            )
        # Fourth category, same rule as the primary-clone test: this worktree's
        # branch carries only an empty commit, so the materialized wiring is
        # untracked and must be contained — and contained where git READS it,
        # which is the point of this test.
        for artifact in self._materialized_artifacts():
            self.assertEqual(
                0,
                subprocess.run(["git", "-C", str(linked), "check-ignore", artifact]).returncode,
                f"{artifact} written but not honoured by git inside a linked worktree",
            )

    def test_committed_consumer_wiring_is_left_visible(self) -> None:
        """The other half of "tracked-ness decides": repo content is not excluded.

        A consumer that legitimately commits its `.claude` wiring must not have
        governance exclude it underneath — that would force `git add -f` on every
        subsequent edit to a file the repository owns. This branch had no
        coverage at all: the assertion here previously ran unconditionally and so
        only ever exercised the untracked case, which is why it disagreed with
        the installer instead of describing it.
        """
        git_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }
        artifacts = self._materialized_artifacts()
        for artifact in artifacts:
            target = self.workspace / artifact
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# committed by the consumer\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.workspace), "add", "--", *artifacts], check=True, env=git_env
        )
        subprocess.run(
            ["git", "-C", str(self.workspace), "commit", "-q", "-m", "consumer wiring"],
            check=True,
            env=git_env,
        )

        result = self._run()
        self.assertIn(result.returncode, (0, 1), result.stderr[-2000:])

        body = (self.workspace / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        for artifact in artifacts:
            self.assertNotIn(
                artifact,
                body,
                f"{artifact} is tracked repo content and must not be excluded",
            )

    def test_install_is_idempotent(self) -> None:
        self._run()
        settings = self.workspace / ".claude" / "settings.json"
        first = settings.read_bytes()
        exclude = self.workspace / ".git" / "info" / "exclude"
        first_exclude = exclude.read_bytes()
        self._run()
        self.assertEqual(settings.read_bytes(), first)
        self.assertEqual(exclude.read_bytes(), first_exclude, "excludes must not accumulate")

    def test_receipt_records_the_wired_workspace(self) -> None:
        self._run()
        parsed = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(parsed["workspace"], str(self.workspace))

    # -- T-25 ---------------------------------------------------------------

    def test_unrelated_consumer_hooks_are_preserved(self) -> None:
        """SEO-Bot ships its own .claude/hooks/session-start.sh. Different file,
        different owner — the installer must not touch it."""
        hooks = self.workspace / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        foreign = hooks / "session-start.sh"
        foreign.write_text("#!/usr/bin/env bash\necho 'consumer owned'\n", encoding="utf-8")
        before = foreign.read_bytes()
        self._run()
        self.assertTrue(foreign.is_file(), "a consumer's own hook must survive install")
        self.assertEqual(
            foreign.read_bytes(), before, "a consumer's own hook must be byte-identical"
        )

    def test_marketplace_skip_does_not_degrade_plugins(self) -> None:
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt),
                "L9_SKIP_SHARED_BOOTSTRAP": "1",
                "L9_GRAPHITI_PROBE_SKIP": "1",
                "SKIP_PLUGIN_MARKETPLACE": "true",
            }
        )
        env.pop("L9_GOVERNANCE_DIR", None)
        result = subprocess.run(
            [
                "bash",
                str(INSTALL),
                "--governance",
                str(REPO),
                "--workspace",
                str(self.workspace),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr[-2000:])
        parsed = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(parsed["plugins"], "READY")
        self.assertIn(parsed.get("commands"), ("READY", "DEGRADED"))
        self.assertTrue((self.workspace / ".claude" / "commands").is_dir())

    def test_check_mode_uses_live_ssot_not_workspace_clone(self) -> None:
        """Hosted `make claude-install-check` passes CURDIR as --governance."""
        fake_gov = self.root / "workspace-clone"
        fake_gov.mkdir()
        (fake_gov / "CANONICAL_LAW.md").write_text("clone, not SSOT\n", encoding="utf-8")
        env = dict(os.environ)
        env.update(
            {
                "HOME": str(self.home),
                "L9_CLAUDE_BOOTSTRAP_RECEIPT": str(self.receipt),
                "L9_SKIP_SHARED_BOOTSTRAP": "1",
                "L9_GRAPHITI_PROBE_SKIP": "1",
                "SKIP_PLUGIN_MARKETPLACE": "true",
                "L9_GOVERNANCE_DIR": str(REPO),
            }
        )
        result = subprocess.run(
            [
                "bash",
                str(INSTALL),
                "--check",
                "--governance",
                str(fake_gov),
                "--workspace",
                str(self.workspace),
                "--quiet",
            ],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        combined = result.stdout + result.stderr
        self.assertIn("is not the live SSOT", combined)
        parsed = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(parsed["plugins"], "READY")
        self.assertNotEqual(parsed["shared_bootstrap"], "BLOCKED")
        live_sha = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(parsed["governance_revision"], live_sha)


class LockedInterpreterPinTests(unittest.TestCase):
    """T-23: full-script preflight fails closed before any consumer probes.

    The two independent, tracked clones have matching source provenance. Python
    is a genuine isolated fixture venv; uv/network/mutators are guarded. These
    are observational checks, not Claude runtime-semantics migration or apply.
    """

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
            "    assert os.environ['L9_GOVERNANCE_SURFACE'] == 'claude-code'\n"
            "    return SimpleNamespace(write_namespace_hint='fixture', method='fixture')\n",
        )

    def _run(self) -> subprocess.CompletedProcess[str]:
        before = snapshot(self.tree.root)
        result = subprocess.run(
            [
                "/bin/bash",
                str(self.tree.source / "ops/scripts/bootstrap_agent_environment.sh"),
                "--surface",
                "claude-code",
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
                "--check",
            ],
            capture_output=True,
            text=True,
            env=self.tree.env,
            cwd=self.workspace,
            timeout=45,
            check=False,
        )
        self.assertEqual(snapshot(self.tree.root), before, result.stderr)
        self.assertEqual(result.stdout, "", result.stdout)
        self.assertNotIn("FORBIDDEN", result.stderr)
        self.assertNotIn("revision UNKNOWN", result.stderr)
        return result

    def _assert_blocked_before_consumers(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("UNLOCKED FALLBACK", result.stderr)
        self.assertNotIn("Agent environment ready", result.stderr)
        for consumer in (
            "Canonical checker",
            "Publish-path",
            "SessionStart secrets",
            "Repository-scoped identity",
            "Readiness preflight",
        ):
            self.assertNotIn(consumer, result.stderr)

    def test_absent_locked_interpreter_is_reported_not_silently_replaced(self) -> None:
        for alias in ("python3", "python"):
            (self.gov / ".venv/bin" / alias).unlink()
        # No sync/fingerprint metadata probe may lend an ambient interpreter to
        # this absent-locked-Python preflight case.
        (self.tree.bin / "uv").unlink()
        result = self._run()
        self._assert_blocked_before_consumers(result)
        self.assertIn(
            f"locked interpreter ABSENT under {self.gov}/.venv — "
            "every governed gate will fail closed",
            result.stderr,
        )
        self.assertIn(
            f"repair: uv sync --locked in {self.gov} (needs pypi.org and astral.sh egress)",
            result.stderr,
        )

    def test_pin_mismatch_names_the_pin_and_the_fetch_host(self) -> None:
        # Exercise the real version guard, not a fake successful interpreter.
        # Preserve actionable pin/fetch repair detail without reaching consumers.
        put(self.gov / ".python-version", "9.99\n")
        result = self._run()
        self._assert_blocked_before_consumers(result)
        self.assertIn(
            "agent-bootstrap WARN: locked .venv prefix/version/pydantic/yaml verification "
            "failed — fail-closed before consumers",
            result.stderr,
        )
        self.assertNotIn("locked interpreter ABSENT", result.stderr)
        self.assertIn("declared Python pin: 9.99", result.stderr)
        self.assertIn("repair: uv sync --locked", result.stderr)
        self.assertIn("needs pypi.org and astral.sh egress", result.stderr)

    def test_matching_pin_is_silent(self) -> None:
        result = self._run()
        self.assertNotIn("pins 3.12", result.stderr)
        self.assertIn("locked interpreter:", result.stderr)


if __name__ == "__main__":
    unittest.main()
