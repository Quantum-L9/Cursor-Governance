#!/usr/bin/env python3
"""The cloud sandbox's own toolchain version is recorded, not just hashed.

`session_deps_cloud.sh` always read `uv --version`, but folded it into a
SHA-256 that nothing can invert. That left the one surface whose uv cannot be
inspected after the fact — the sandbox VM and everything under ~/.l9 are
destroyed together — with no record of it at all, and `[tool.uv]
required-version` was argued from a four-week-old comment instead of evidence.

Two properties matter enough to pin:

* The observation happens on the cloud path and NOT on a developer checkout,
  because a local uv is readable at any time and writing it is noise.
* The fingerprint recipe is unchanged by the observation. That hash is the cache
  key gating every dependency install; changing it silently makes every cloud
  session reinstall its toolchain once. The recipe is pinned literally here so a
  future edit to it has to be deliberate.

Every case runs the REAL scripts against a synthetic tree with stub tool
binaries on PATH, so the asserted versions are deterministic rather than
whatever the machine running the suite happens to have installed.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
HOOKS = REPO / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
DEPS_HELPER = HOOKS / "session_deps_cloud.sh"
SESSION_START = HOOKS / "session_start_claude_governance.sh"

# Deliberately the sandbox-relevant version: 0.8.x is the release that silently
# discards the whole [tool.uv] table on an unknown key, and it exercises semver
# extraction from uv's parenthesised build suffix.
FAKE_UV_RAW = "uv 0.8.0 (3cdf50e09 2026-06-19 x86_64-unknown-linux-gnu)"
FAKE_UV_SEMVER = "0.8.0"
FAKE_NODE = "v22.15.0"
FAKE_PNPM = "9.1.0"
FAKE_NPM = "11.4.2"


def _stub_bin(path: Path, output: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' {output!r}\n", encoding="utf-8")
    path.chmod(0o755)


def _stub_bin_failing(path: Path) -> None:
    """A tool that exists but cannot report a version."""
    path.write_text("#!/usr/bin/env bash\nexit 127\n", encoding="utf-8")
    path.chmod(0o755)


class _SandboxCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.workspace = self.root / "ws"
        self.home.mkdir()
        self.workspace.mkdir()

        # Stub toolchain so versions are deterministic on any developer machine.
        self.bin = self.root / "bin"
        self.bin.mkdir()
        _stub_bin(self.bin / "uv", FAKE_UV_RAW)
        _stub_bin(self.bin / "node", FAKE_NODE)
        _stub_bin(self.bin / "pnpm", FAKE_PNPM)
        _stub_bin(self.bin / "npm", FAKE_NPM)

    def _env(self, *, cloud: bool) -> dict[str, str]:
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env["PATH"] = f"{self.bin}{os.pathsep}{env.get('PATH', '')}"
        if cloud:
            env["CLAUDE_CODE_REMOTE"] = "true"
        else:
            env.pop("CLAUDE_CODE_REMOTE", None)
        return env

    @property
    def observation(self) -> Path:
        return self.home / ".l9" / "claude" / "toolchain-observed.json"

    def _run_deps(self, *, cloud: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                str(DEPS_HELPER),
                "--workspace",
                str(self.workspace),
                "--budget",
                "15",
            ],
            env=self._env(cloud=cloud),
            capture_output=True,
            text=True,
            timeout=120,
        )


class DepsHelperObservationTests(_SandboxCase):
    def test_local_checkout_records_nothing(self) -> None:
        # A developer checkout's uv is readable at any time; recording it would
        # be noise, and the helper must never touch a local toolchain at all.
        proc = self._run_deps(cloud=False)
        self.assertEqual(proc.returncode, 0)
        self.assertFalse(self.observation.exists())
        self.assertIn("not a cloud session", proc.stdout)

    def test_cloud_session_records_uv_verbatim(self) -> None:
        proc = self._run_deps(cloud=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.observation.exists(), proc.stdout)
        data = json.loads(self.observation.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "l9.claude-toolchain-observed.v1")
        self.assertEqual(data["uv_version"], FAKE_UV_SEMVER)
        # The raw string is kept alongside the semver: the build suffix is what
        # identifies WHICH 0.8.0 build the sandbox image shipped.
        self.assertEqual(data["uv_version_raw"], FAKE_UV_RAW)
        self.assertEqual(data["node_version"], FAKE_NODE)
        self.assertTrue(data["observed_at"].endswith("Z"))
        # And it is legible in the hook's own output, not only on disk.
        self.assertIn(f"observed uv {FAKE_UV_SEMVER}", proc.stdout)

    def test_unusable_uv_is_recorded_as_empty_not_as_a_version(self) -> None:
        # "not observed" and "an old version" are different facts. A uv that
        # cannot report a version must not be recorded as some default that a
        # later reader mistakes for evidence.
        #
        # Modelled as a uv that exits non-zero rather than by deleting the stub:
        # the stub directory is PREPENDED to PATH, so an absent stub would simply
        # fall through to the machine's real uv and the test would assert nothing.
        _stub_bin_failing(self.bin / "uv")
        proc = self._run_deps(cloud=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(self.observation.read_text(encoding="utf-8"))
        self.assertEqual(data["uv_version"], "")
        self.assertEqual(data["uv_version_raw"], "none")

    def test_observation_survives_a_cached_toolchain(self) -> None:
        # The observation is about the environment, not about whether an install
        # ran, so the cache short-circuit must not skip it. Without this, the
        # steady state (cached toolchain) is exactly the state that records
        # nothing — which is how the gap went unnoticed.
        (self.workspace / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        venv_py = self.workspace / ".venv" / "bin"
        venv_py.mkdir(parents=True)
        (venv_py / "python").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (venv_py / "python").chmod(0o755)

        first = self._run_deps(cloud=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.observation.unlink()  # prove the SECOND run rewrites it

        second = self._run_deps(cloud=True)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("cached", second.stdout)
        self.assertTrue(
            self.observation.exists(),
            "a cached toolchain still has to record the uv that resolved it",
        )

    def test_fingerprint_recipe_is_unchanged_by_the_observation(self) -> None:
        # This hash is the cache key for every cloud dependency install. If the
        # recipe changes, every existing stamp is invalidated and every cloud
        # session reinstalls once. Pinned literally so that cost is never paid
        # by accident.
        self._run_deps(cloud=True)
        stamps = list((self.home / ".l9" / "claude").glob("deps-*.stamp"))
        self.assertEqual(len(stamps), 1, f"expected exactly one stamp, got {stamps}")
        got = stamps[0].name.removeprefix("deps-").removesuffix(".stamp")

        recipe = f"|uv:{FAKE_UV_RAW}|node:{FAKE_NODE}|pnpm:{FAKE_PNPM}|npm:{FAKE_NPM}"
        expected = hashlib.sha256(recipe.encode()).hexdigest()
        self.assertEqual(
            got,
            expected,
            "fingerprint recipe changed — every cloud stamp is invalidated; "
            "update this test only alongside a deliberate decision to reinstall",
        )


class GraphitiRecordTests(_SandboxCase):
    """The durable half: a cloud-gated, deduped write from the SessionStart hook."""

    def setUp(self) -> None:
        super().setUp()
        self.gov = self.home / ".cursor-governance"
        (self.gov / "ops" / "graphiti").mkdir(parents=True)
        (self.gov / "CANONICAL_LAW.md").write_text("synthetic", encoding="utf-8")
        # The REAL deps helper, at the path the hook resolves it from. Leg 3 reads
        # what leg 1 wrote, so stubbing the observation here would test the two
        # halves in isolation and prove nothing about them meeting.
        gov_hooks = self.gov / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
        gov_hooks.mkdir(parents=True)
        (gov_hooks / DEPS_HELPER.name).write_text(
            DEPS_HELPER.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (self.gov / "ops" / "graphiti" / "graphiti_memory_client.py").write_text(
            "# stub client\n", encoding="utf-8"
        )
        # The hook's locked interpreter. Recording argv is what lets the test
        # assert the write actually happened with the right kind and agent_id,
        # rather than asserting on a log line the hook printed about itself.
        self.argv_log = self.root / "argv.log"
        venv_bin = self.gov / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        stub_py = venv_bin / "python3"
        stub_py.write_text(
            f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> {str(self.argv_log)!r}\nexit 0\n',
            encoding="utf-8",
        )
        stub_py.chmod(0o755)

    def _run_session_start(self, *, cloud: bool) -> subprocess.CompletedProcess[str]:
        env = self._env(cloud=cloud)
        env["CLAUDE_PROJECT_DIR"] = str(self.workspace)
        return subprocess.run(
            ["bash", str(SESSION_START)],
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )

    def _writes(self) -> list[str]:
        if not self.argv_log.exists():
            return []
        return [
            line
            for line in self.argv_log.read_text(encoding="utf-8").splitlines()
            if "graphiti_memory_client.py" in line and " write " in line
        ]

    def _await_stamp(self, timeout: float = 20.0) -> Path | None:
        # The write is detached on purpose: SessionStart has a 30s budget and a
        # hung tunnel must not become a hung hook. So the stamp is polled.
        deadline = time.monotonic() + timeout
        stamp_dir = self.home / ".l9" / "claude"
        while time.monotonic() < deadline:
            found = list(stamp_dir.glob("toolchain-graphiti-*.stamp"))
            if found:
                return found[0]
            time.sleep(0.25)
        return None

    def test_local_session_never_writes_the_fact(self) -> None:
        # Cloud-gated: a developer checkout writing its own uv on every session
        # would be recurring noise in the graph for a fact nobody needs.
        proc = self._run_session_start(cloud=False)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(self._writes(), [])
        self.assertNotIn("sandbox toolchain:", proc.stdout)

    def test_cloud_session_writes_the_version_once_and_stamps(self) -> None:
        proc = self._run_session_start(cloud=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        stamp = self._await_stamp()
        self.assertIsNotNone(stamp, f"no stamp; hook said: {proc.stdout}")
        assert stamp is not None
        self.assertEqual(stamp.name, f"toolchain-graphiti-{FAKE_UV_SEMVER}.stamp")

        writes = self._writes()
        self.assertEqual(len(writes), 1, writes)
        body = writes[0]
        self.assertIn(FAKE_UV_SEMVER, body)
        # Rule 87: every write is pre-classified and carries the writer identity.
        self.assertIn("--kind note", body)
        self.assertIn("--agent-id claude-code", body)

    def test_existing_stamp_skips_the_round_trip(self) -> None:
        stamp_dir = self.home / ".l9" / "claude"
        stamp_dir.mkdir(parents=True, exist_ok=True)
        (stamp_dir / f"toolchain-graphiti-{FAKE_UV_SEMVER}.stamp").touch()
        # The observation must already exist, or the function returns before it
        # ever consults the stamp — which would pass for the wrong reason.
        (stamp_dir / "toolchain-observed.json").write_text(
            json.dumps({"uv_version": FAKE_UV_SEMVER}), encoding="utf-8"
        )

        proc = self._run_session_start(cloud=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._writes(), [])
        self.assertIn("already recorded", proc.stdout)


if __name__ == "__main__":
    unittest.main()
