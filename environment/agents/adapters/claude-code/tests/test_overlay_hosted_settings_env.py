#!/usr/bin/env python3
"""Hosted autonomy overlay must not fork settings.template.json."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO / "environment" / "agents" / "adapters" / "claude-code"))

from overlay_hosted_settings_env import (  # noqa: E402
    REQUIRED_SURFACE,
    apply_overlay,
    overlay_hosted_settings,
    overlay_payload_from_environ,
)


class OverlayHostedSettingsEnvTests(unittest.TestCase):
    def test_copies_autonomy_keys_only(self) -> None:
        payload = overlay_payload_from_environ(
            {
                "L9_AUTONOMY_MAX_PARALLEL": "4",
                "SOME_UPSTREAM_URL": "https://example.invalid/should-not-copy",
                "L9_CAPABILITY_BROKER_URL": "https://broker.invalid",
            }
        )
        self.assertEqual(payload, {"L9_AUTONOMY_MAX_PARALLEL": "4"})

    def test_copies_the_memory_interpreter_so_claude_can_expand_the_mcp_ref(self) -> None:
        """L9_MEMORY_INTERPRETER must reach settings env, or the MCP server dies.

        mcp.template.json renders l9-graphite-memory with command
        "${L9_MEMORY_INTERPRETER}" to keep the tracked .mcp.json machine-agnostic.
        Claude Code expands that at load from the session env, not from the
        SessionStart hook shell where bind_memory_interpreter.sh exports it.
        Observed failure: the server rendered (projection ran in the hook shell,
        saw the variable) and then failed ENOENT at load, while the readiness
        receipt still said memory_mcp=READY because it too ran in that shell.
        """
        payload = overlay_payload_from_environ(
            {"L9_MEMORY_INTERPRETER": "/gov/.venv/bin/python", "SOME_TOKEN": "nope"}
        )
        self.assertEqual(payload, {"L9_MEMORY_INTERPRETER": "/gov/.venv/bin/python"})

        settings: dict = {"env": {}}
        apply_overlay(settings, payload)
        self.assertEqual(settings["env"]["L9_MEMORY_INTERPRETER"], "/gov/.venv/bin/python")

    def test_unbound_memory_interpreter_is_not_written_as_empty(self) -> None:
        """An empty binding must stay absent, so _requires_env still gates the server."""
        self.assertEqual(overlay_payload_from_environ({"L9_MEMORY_INTERPRETER": ""}), {})

    def test_surface_id_cannot_be_overwritten(self) -> None:
        settings = {"env": {"L9_GOVERNANCE_SURFACE": "claude-code-mobile"}}
        apply_overlay(settings, {"L9_AUTONOMY_ENABLED": "false"})
        self.assertEqual(settings["env"]["L9_GOVERNANCE_SURFACE"], REQUIRED_SURFACE)
        self.assertEqual(settings["env"]["L9_AUTONOMY_ENABLED"], "false")

    @staticmethod
    def _build(base: Path) -> tuple[Path, Path]:
        workspace = base / "ws"
        (workspace / ".claude").mkdir(parents=True)
        (workspace / ".claude" / "settings.json").write_text(
            json.dumps(
                {
                    "env": {
                        "L9_GOVERNANCE_SURFACE": "claude-code",
                        "L9_AUTONOMY_MAX_PARALLEL": "480",
                    }
                }
            ),
            encoding="utf-8",
        )
        home = base / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(
            json.dumps({"env": {"L9_GOVERNANCE_SURFACE": "claude-code"}}),
            encoding="utf-8",
        )
        return workspace, home

    def test_writes_workspace_local_and_user_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            written = overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_MAX_PARALLEL": "8"},
            )
            self.assertEqual(written, ["workspace-local", "user"])
            local_env = json.loads(
                (workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8")
            )["env"]
            user_env = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))[
                "env"
            ]
            self.assertEqual(local_env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertEqual(user_env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertEqual(local_env["L9_GOVERNANCE_SURFACE"], "claude-code")

    def test_tracked_workspace_settings_is_never_modified(self) -> None:
        """The regression this overlay caused: a tracked GENERATED artifact was
        patched in place, dirtying a clean checkout at every SessionStart."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            tracked = workspace / ".claude" / "settings.json"
            before = tracked.read_bytes()
            overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={
                    "L9_AUTONOMY_MAX_PARALLEL": "8",
                    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
                },
            )
            self.assertEqual(tracked.read_bytes(), before)

    def test_tracked_settings_does_not_clobber_the_reconciler_projection(self) -> None:
        """When settings.json is repo-owned, the local file's env is the fresh
        projection and the tracked file's is unrelated repository content —
        possibly from another revision. Re-seeding from the tracked file would
        overwrite the new projection with a stale one at every SessionStart."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            subprocess.run(["git", "add", ".claude/settings.json"], cwd=workspace, check=True)
            # A key only the stale committed file carries: it must not come back.
            tracked = workspace / ".claude" / "settings.json"
            stale = json.loads(tracked.read_text(encoding="utf-8"))
            stale["env"]["L9_RETIRED_KEY"] = "from-an-older-revision"
            tracked.write_text(json.dumps(stale), encoding="utf-8")

            # What the reconciler projected from the CURRENT template.
            local = workspace / ".claude" / "settings.local.json"
            local.write_text(
                json.dumps({"env": {"L9_SIGNAL": "from-current-template"}}), encoding="utf-8"
            )

            overlay_hosted_settings(
                workspace=workspace, home=home, environ={"L9_AUTONOMY_MAX_PARALLEL": "8"}
            )

            env = json.loads(local.read_text(encoding="utf-8"))["env"]
            self.assertEqual(env["L9_SIGNAL"], "from-current-template")
            self.assertEqual(env["L9_AUTONOMY_MAX_PARALLEL"], "8")
            self.assertNotIn("L9_RETIRED_KEY", env, "the stale tracked env must not be re-seeded")

    def test_ownership_probe_is_bounded_and_agrees_with_the_reconciler(self) -> None:
        """PR #611 review (Copilot): no timeout on a SessionStart-path call.

        Bounded now. The timeout answers True rather than the reviewer's
        suggested settings.json fallback, so it agrees with
        reconcile_claude_settings._path_is_git_tracked: that one resolves the
        same unknown to True and has therefore just written the current
        projection into the local file. Seeding from the tracked file here
        would overwrite it with an unrelated env.
        """
        import overlay_hosted_settings_env as ov

        calls: list[dict] = []

        def fake_run(*args, **kwargs):
            calls.append(kwargs)
            raise subprocess.TimeoutExpired(cmd="git", timeout=kwargs.get("timeout"))

        with tempfile.TemporaryDirectory() as tmp:
            workspace, _ = self._build(Path(tmp))
            local = workspace / ".claude" / "settings.local.json"
            local.write_text(json.dumps({"env": {}}), encoding="utf-8")
            original = ov.subprocess.run
            ov.subprocess.run = fake_run
            try:
                self.assertTrue(ov._local_env_is_authoritative(workspace, local))
            finally:
                ov.subprocess.run = original

        self.assertTrue(calls, "the probe must actually invoke git")
        self.assertEqual(calls[0].get("timeout"), ov.GIT_QUERY_TIMEOUT_S)

    def test_untracked_settings_still_seeds_env_from_settings_json(self) -> None:
        """Governance owns an untracked settings.json, so it holds the
        authoritative projection and the local file seeds from it as before."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            overlay_hosted_settings(
                workspace=workspace, home=home, environ={"L9_AUTONOMY_MAX_PARALLEL": "8"}
            )
            env = json.loads(
                (workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8")
            )["env"]
            self.assertEqual(env["L9_GOVERNANCE_SURFACE"], "claude-code")

    def test_local_file_carries_complete_env_not_just_overlay_keys(self) -> None:
        """Written whole because Claude Code's precedence table does not say
        whether `env` merges key-by-key or is taken whole from the top scope.
        A fragment would drop L9_GOVERNANCE_SURFACE under the second reading."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_ENABLED": "true"},
            )
            local_env = json.loads(
                (workspace / ".claude" / "settings.local.json").read_text(encoding="utf-8")
            )["env"]
            # inherited from the tracked file, absent from the overlay payload
            self.assertEqual(local_env["L9_AUTONOMY_MAX_PARALLEL"], "480")
            self.assertEqual(local_env["L9_GOVERNANCE_SURFACE"], "claude-code")
            self.assertEqual(local_env["L9_AUTONOMY_ENABLED"], "true")

    def test_preserves_unrelated_keys_already_in_local_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace, home = self._build(Path(tmp))
            local = workspace / ".claude" / "settings.local.json"
            local.write_text(
                json.dumps({"permissions": {"allow": ["Bash(ls:*)"]}}), encoding="utf-8"
            )
            overlay_hosted_settings(
                workspace=workspace,
                home=home,
                environ={"L9_AUTONOMY_ENABLED": "true"},
            )
            data = json.loads(local.read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"], {"allow": ["Bash(ls:*)"]})
            self.assertEqual(data["env"]["L9_AUTONOMY_ENABLED"], "true")


if __name__ == "__main__":
    unittest.main()


def test_reconciler_keeps_the_keys_the_overlay_owns(tmp_path) -> None:
    """Two governance components must not fight over one `env` block.

    `env` is a managed key, so the reconciler took it wholly from the template.
    overlay_hosted_settings_env copies hosted account values — including keys
    the template deliberately does not carry — into the same user-scope file.
    Observed on a healthy container: the overlay added L9_L4_LOCAL_AUTONOMY and
    L9_WORKTREE_ISOLATION, the reconciler reported that correct state as drift
    and would strip them on the next write, and the overlay put them back. A
    check that reports ok=false on a correctly configured container teaches the
    reader to ignore it.
    """
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[5]
    sys.path.insert(0, str(repo / "ops" / "scripts"))
    import reconcile_claude_settings as rc

    template = {"env": {"L9_GOVERNANCE_SURFACE": "claude-code"}}
    existing = {
        "env": {
            "L9_GOVERNANCE_SURFACE": "claude-code",
            "L9_L4_LOCAL_AUTONOMY": "1",
            "L9_WORKTREE_ISOLATION": "1",
            "SOMETHING_UNMANAGED": "x",
        }
    }

    merged = rc.merge_user_settings(template, existing, root=repo)
    env = merged["env"]
    assert env["L9_L4_LOCAL_AUTONOMY"] == "1", "overlay-owned key must survive"
    assert env["L9_WORKTREE_ISOLATION"] == "1", "overlay-owned key must survive"
    # Preservation is scoped to keys the overlay declares — it widens nothing.
    assert "SOMETHING_UNMANAGED" not in env

    # And a key the overlay owns but the file does not carry is not invented.
    absent = rc.merge_user_settings(template, {"env": dict(template["env"])}, root=repo)
    assert "L9_L4_LOCAL_AUTONOMY" not in absent["env"]

    # The key list comes from the overlay module, never a second hand-kept copy.
    assert "L9_L4_LOCAL_AUTONOMY" in rc._overlay_env_keys(repo)
