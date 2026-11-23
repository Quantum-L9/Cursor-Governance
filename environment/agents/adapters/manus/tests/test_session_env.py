"""The Manus session start must leave the machine readable by every later gate.

Two failures this locks down, both observed on a fresh Manus cloud sandbox:

* `$HOME/.cursor-governance` absent. `resolve_governance_paths.sh` refuses
  anything else, and the `symlinks-check` pre-commit hook is
  `pass_filenames: false`, so every `make pr` failed on a clean tree with an
  error naming a path the session never created. The helper delegates the
  clone to `governance_sync.sh` (stubbed here) instead of linking the
  workspace: a link follows the workspace's branch and cannot stay at main.
* `L9_GOVERNANCE_SURFACE` unset. `is_cursor_host_surface()` fails closed to
  Cursor, so that same hook demanded desktop plugin links on a Manus host.

The helper must also stay non-destructive: a real checkout, a symlink, and an
env file it did not write are all reported and left alone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
SCRIPT = ADAPTER / "session_env.sh"
MARKER = "# L9 Manus surface binding"


def _run(home: Path, governance: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(SCRIPT), "--governance", str(governance), *extra],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class SessionEnvTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.home = root / "home"
        self.home.mkdir()
        self.governance = root / "governance"
        (self.governance / "skills").mkdir(parents=True)
        (self.governance / "CANONICAL_LAW.md").write_text("# law\n", encoding="utf-8")
        fixture = self.governance / "environment/agents/adapters/manus"
        fixture.mkdir(parents=True)
        shutil.copy(ADAPTER / "environment.env.example", fixture / "environment.env.example")
        sync = self.governance / "ops" / "scripts" / "governance_sync.sh"
        sync.parent.mkdir(parents=True)
        sync.write_text(
            "#!/usr/bin/env bash\n"
            "set -eu\n"
            'target="${CURSOR_GOVERNANCE_DIR:?}"\n'
            'mkdir -p "$target/skills"\n'
            'printf "# law\\n" >"$target/CANONICAL_LAW.md"\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_check_is_observational(self) -> None:
        result = _run(self.home, self.governance, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ssot=ABSENT", result.stderr)
        self.assertIn("env=ABSENT", result.stderr)
        self.assertIn("result=ATTENTION", result.stderr)
        self.assertFalse((self.home / ".cursor-governance").exists())
        self.assertFalse((self.home / ".l9" / "cloud-session.env").exists())

    def test_apply_provisions_ssot_and_declares_the_surface(self) -> None:
        result = _run(self.home, self.governance)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ssot=PROVISIONED", result.stderr)
        self.assertIn("result=READY", result.stderr)

        ssot = self.home / ".cursor-governance"
        self.assertTrue(ssot.is_dir())
        self.assertFalse(ssot.is_symlink())
        self.assertTrue((ssot / "CANONICAL_LAW.md").is_file())

        env_file = self.home / ".l9" / "cloud-session.env"
        text = env_file.read_text(encoding="utf-8")
        self.assertIn(MARKER, text)
        self.assertIn("export L9_GOVERNANCE_SURFACE=manus", text)
        self.assertIn(f"export L9_GOVERNANCE_DIR='{self.governance}'", text)
        for profile in (self.home / ".bashrc", self.home / ".profile"):
            self.assertEqual(
                profile.read_text(encoding="utf-8").count("cloud-session.env"),
                1,
                f"{profile} must source the session env exactly once",
            )

    def test_apply_is_idempotent(self) -> None:
        first = _run(self.home, self.governance)
        second = _run(self.home, self.governance)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("ssot=OK", second.stderr)
        self.assertIn("env=WROTE", second.stderr)
        for profile in (self.home / ".bashrc", self.home / ".profile"):
            self.assertEqual(profile.read_text(encoding="utf-8").count("cloud-session.env"), 1)

    def test_a_real_checkout_is_not_replaced(self) -> None:
        real = self.home / ".cursor-governance"
        (real / "skills").mkdir(parents=True)
        (real / "CANONICAL_LAW.md").write_text("# law\n", encoding="utf-8")
        result = _run(self.home, self.governance)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ssot=OK", result.stderr)
        self.assertFalse(real.is_symlink())
        self.assertTrue((real / "CANONICAL_LAW.md").is_file())

    def test_a_symlink_is_reported_not_repointed(self) -> None:
        other = Path(self._tmp.name) / "other"
        (other / "skills").mkdir(parents=True)
        (other / "CANONICAL_LAW.md").write_text("# law\n", encoding="utf-8")
        link = self.home / ".cursor-governance"
        link.symlink_to(other)
        result = _run(self.home, self.governance)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ssot=SYMLINK", result.stderr)
        self.assertEqual(Path(os.path.realpath(link)), Path(os.path.realpath(other)))

    def test_a_foreign_env_file_is_not_overwritten(self) -> None:
        env_file = self.home / ".l9" / "cloud-session.env"
        env_file.parent.mkdir(parents=True)
        env_file.write_text("export L9_GOVERNANCE_SURFACE=cursor\n", encoding="utf-8")
        result = _run(self.home, self.governance)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("env=FOREIGN", result.stderr)
        self.assertEqual(
            env_file.read_text(encoding="utf-8"), "export L9_GOVERNANCE_SURFACE=cursor\n"
        )


if __name__ == "__main__":
    unittest.main()
