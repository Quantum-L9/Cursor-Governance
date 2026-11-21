"""Option B session excludes: no tracked .gitignore, no blanket .claude/."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HELPER = REPO / "ops" / "scripts" / "lib" / "session_git_excludes.sh"
BOOTSTRAP = REPO / "ops" / "scripts" / "bootstrap_agent_environment.sh"
SETUP = REPO / "ops" / "scripts" / "setup_workspace_symlinks.sh"
INSTALL = REPO / "environment" / "agents" / "adapters" / "claude-code" / "install.sh"
SCRIPT = HERE / "test_session_git_excludes.sh"

BLANKET = (".claude/", "/.claude/", ".claude", "/.claude")


class SessionGitExcludesContractTests(unittest.TestCase):
    def test_helper_exists_and_refuses_blanket(self) -> None:
        text = HELPER.read_text(encoding="utf-8")
        self.assertIn("session_is_forbidden_blanket_claude", text)
        self.assertIn("apply_session_git_excludes", text)
        self.assertIn("apply_machine_session_excludes", text)
        self.assertIn("session_machine_exclude_globs", text)
        self.assertIn("session_prune_session_only_from_machine_file", text)
        self.assertNotRegex(text, r'(?m)^[ \t]*["\']?/?\.claude/?["\']?[ \t]*$')
        machine_fn = text.split("session_machine_exclude_globs()", 1)[1].split("}", 1)[0]
        self.assertNotIn(".mcp.json", machine_fn)
        self.assertIn(".claude/settings.local.json", machine_fn)
        machine_apply = text.split("apply_machine_session_excludes()", 1)[1]
        self.assertNotIn("session_claude_mirror_exclude_globs", machine_apply)

    def test_shared_bootstrap_applies_option_b(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("lib/session_git_excludes.sh", text)
        self.assertIn("apply_session_git_excludes", text)
        for token in BLANKET:
            self.assertNotIn(f'"{token}"', text)

    def test_setup_wires_machine_excludes(self) -> None:
        text = SETUP.read_text(encoding="utf-8")
        self.assertIn("lib/session_git_excludes.sh", text)
        self.assertIn("apply_machine_session_excludes", text)
        self.assertIn("WARN: cannot write global gitignore", text)

    def test_bootstrap_warns_when_session_excludes_fail(self) -> None:
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("could not write session git excludes", text)

    def test_claude_install_reuses_helper(self) -> None:
        text = INSTALL.read_text(encoding="utf-8")
        self.assertIn("session_git_excludes.sh", text)
        self.assertIn("apply_session_claude_mirror_excludes", text)
        self.assertIn("apply_session_untracked_artifact_excludes", text)

    def test_bash_fixture(self) -> None:
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    _git("init", "-q", str(path))
    return path


def _entries(exclude: Path) -> list[str]:
    """Pattern lines of an exclude file; git seeds it with comment lines."""
    lines = exclude.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def _untracked(repo: Path) -> list[str]:
    """Untracked paths git would show; the governed set must contribute none."""
    out = _git("-C", str(repo), "status", "--porcelain", "--untracked-files=all")
    return [line[3:] for line in out.splitlines() if line.startswith("?? ")]


class WriterAppliesSessionExcludesTests(unittest.TestCase):
    """Lane X: every writer into a clone excludes its own output in that clone.

    Reproduces the IB-Odoo_19 report. SessionStart applied the session excludes
    to ONE workspace (`install.sh` / `bootstrap_agent_environment.sh`), and to
    none at all when that workspace was the multi-repo container, while the
    command, skill and memory writers fan out to every repository in the
    container — including one attached after SessionStart ran. The clone that
    never received an exclude showed the governance mirrors and memory latches
    as untracked.
    """

    def setUp(self) -> None:
        import os
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._env = {
            k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "HOME")
        }
        os.environ["GIT_CONFIG_GLOBAL"] = str(self.tmp / "gitconfig")
        os.environ["GIT_CONFIG_SYSTEM"] = "/dev/null"
        os.environ["HOME"] = str(self.tmp / "home")
        (self.tmp / "home").mkdir()
        self.container = self.tmp / "container"
        self.first = _init_repo(self.container / "first")
        # SessionStart-style run: the excludes reach the primary workspace only.
        subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; apply_session_git_excludes "$2"',
                "_",
                str(HELPER),
                str(self.first),
            ],
            check=True,
        )
        # A repository attached after SessionStart (add_repo / register_repo_root).
        self.attached = _init_repo(self.container / "attached")

    def tearDown(self) -> None:
        import os

        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def test_bridge_uses_the_shell_list(self) -> None:
        import sys

        sys.path.insert(0, str(REPO / "ops" / "scripts" / "lib"))
        import session_git_excludes as bridge

        self.assertTrue(bridge.apply_session_git_excludes(self.attached))
        exclude = (
            Path(_git("-C", str(self.attached), "rev-parse", "--absolute-git-dir").strip())
            / "info"
            / "exclude"
        )
        expected = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; session_shared_exclude_globs; session_claude_mirror_exclude_globs',
                "_",
                str(HELPER),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        self.assertEqual(_entries(exclude), expected)
        # Idempotent, and a non-repository is a no-op success.
        self.assertTrue(bridge.apply_session_git_excludes(self.attached))
        self.assertEqual(_entries(exclude), expected)
        self.assertTrue(bridge.apply_session_git_excludes(self.tmp / "not-a-repo"))

    def test_commands_reconciler_excludes_its_mirror_in_every_clone(self) -> None:
        import sys

        sys.path.insert(0, str(REPO / "ops" / "scripts"))
        import reconcile_claude_commands as rc

        rc.reconcile(REPO, workspace=self.container, scopes=("project",))
        manifest = self.attached / ".claude" / "commands" / rc.STATE_NAME
        self.assertTrue(
            manifest.is_file(), "fixture: the reconciler must write into the attached clone"
        )
        self.assertEqual(_untracked(self.attached), [])
        self.assertEqual(_untracked(self.first), [])

    def test_skill_adapters_exclude_their_mirror_in_every_clone(self) -> None:
        import sys

        sys.path.insert(0, str(REPO / "ops" / "scripts"))
        import reconcile_llm_skill_adapters as rs

        rs.reconcile_adapters(REPO, workspace=self.container, skip_user=True)
        skills = self.attached / ".claude" / "skills"
        self.assertTrue(
            any(p.name.startswith("l9-") for p in skills.iterdir()),
            "fixture: the skill adapters must write into the attached clone",
        )
        self.assertEqual(_untracked(self.attached), [])

    def test_memory_latch_excludes_itself_in_an_attached_clone(self) -> None:
        import sys

        sys.path.insert(0, str(REPO))
        from ops.graphiti.hydration import session_latches

        session_latches.write_open_latch(self.attached, "lane-x-session")
        session_latches.write_receipt(self.attached, "lane-x-session", {"status": "closed"})
        self.assertTrue((self.attached / ".l9" / "memory" / "last_opened.json").is_file())
        self.assertEqual(_untracked(self.attached), [])

    def test_linked_worktree_writer_excludes_via_common_dir(self) -> None:
        import sys

        sys.path.insert(0, str(REPO))
        from ops.graphiti.hydration import session_latches

        _git(
            "-C",
            str(self.attached),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "base",
        )
        linked = self.container / "linked"
        _git("-C", str(self.attached), "worktree", "add", "-q", "-b", "wt", str(linked))
        session_latches.write_open_latch(linked, "lane-x-session")
        self.assertEqual(_untracked(linked), [])
        common = Path(
            _git(
                "-C", str(linked), "rev-parse", "--path-format=absolute", "--git-common-dir"
            ).strip()
        )
        self.assertIn("/.l9/", (common / "info" / "exclude").read_text(encoding="utf-8").split())
