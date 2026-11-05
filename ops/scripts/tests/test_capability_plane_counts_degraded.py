#!/usr/bin/env python3
"""Retired broker never runs or counts; only the chosen secrets failure degrades.

Every bootstrap invocation executes the exact copied script in tracked source
and governance clones with matching known SHA, a genuine isolated locked venv,
complete dependency stubs and guarded tools. Apply collaborators and secrets
receipts are fixture-only; no checkout venv, live identity or service is used.
"""

from __future__ import annotations

import importlib.util
import json
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
BootstrapTree = _FIXTURES.BootstrapTree
git = _FIXTURES.git
put = _FIXTURES.put
snapshot = _FIXTURES.snapshot


class _PlaneBootstrapCase(unittest.TestCase):
    """Guarded synthetic apply fixture. Carries no tests of its own."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tree = BootstrapTree(Path(self._tmp.name))
        self.root = self.tree.root
        self.gov = self.tree.gov
        self.workspace = self.tree.ws
        self.tree.stub_apply()
        self.sha = git(self.tree.source, "rev-parse", "HEAD")
        self.assertEqual(git(self.gov, "rev-parse", "HEAD"), self.sha)
        put(
            self.gov / "ops/memory/namespace_context.py",
            "import os\nfrom types import SimpleNamespace\n"
            "def resolve_namespace_context(root):\n"
            "    assert os.environ['L9_GOVERNANCE_SURFACE'] == 'cursor'\n"
            "    return SimpleNamespace(write_namespace_hint='fixture', method='fixture')\n",
        )
        self.receipt_argv = self.root / "receipt-argv.json"
        put(
            self.gov / "ops/scripts/write_runtime_readiness_receipt.py",
            "import json, os, sys\nfrom pathlib import Path\n"
            "assert os.environ['L9_GOVERNANCE_SURFACE'] == 'cursor'\n"
            "args = sys.argv[1:]\n"
            "def value(flag):\n    return args[args.index(flag) + 1]\n"
            "assert value('--surface') == 'cursor'\n"
            f"assert value('--governance') == {str(self.gov)!r}\n"
            f"assert value('--workspace') == {str(self.workspace)!r}\n"
            f"assert value('--governance-revision') == {self.sha!r}\n"
            f"assert value('--runtime-script-revision') == {self.sha!r}\n"
            f"Path({str(self.receipt_argv)!r}).write_text(json.dumps(args))\n",
        )

    def _write_owner(self, *, exit_code: int, receipt: dict[str, object] | None = None) -> None:
        """Fake the canonical secrets API; its only write is the fixture receipt."""
        owner = self.gov / "ops/secrets/session_start_secrets.py"
        dest = self.workspace / ".l9/session/secrets-plane.json"
        payload = receipt if receipt is not None else {"ok": exit_code == 0, "state": "fixture"}
        put(
            owner,
            "import os, sys\nfrom pathlib import Path\n"
            f"assert Path(__file__).resolve() == Path({str(owner)!r}).resolve()\n"
            "assert os.environ['L9_GOVERNANCE_SURFACE'] == 'cursor'\n"
            "assert os.environ['PYTHONDONTWRITEBYTECODE'] == '1'\n"
            f"assert sys.argv[1:] == ['--receipt-out', {str(dest)!r}]\n"
            f"dest = Path({str(dest)!r})\n"
            f"assert dest.resolve().is_relative_to(Path({str(self.workspace)!r}).resolve())\n"
            "print('FIXTURE_AUTH_NOT_LIVE')\n"
            f"dest.write_text({json.dumps(payload)!r}, encoding='utf-8')\n"
            f"raise SystemExit({exit_code})\n",
        )

    def _run(self, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        before_source = snapshot(self.tree.source)
        before_gov = snapshot(self.gov)
        result = subprocess.run(
            [
                "/bin/bash",
                str(self.tree.source / "ops/scripts/bootstrap_agent_environment.sh"),
                "--surface",
                "cursor",
                "--governance",
                str(self.gov),
                "--workspace",
                str(self.workspace),
            ],
            capture_output=True,
            text=True,
            env={**self.tree.env, **(extra_env or {})},
            cwd=self.workspace,
            timeout=45,
            check=False,
        )
        self.assertEqual(snapshot(self.tree.source), before_source, result.stderr)
        self.assertEqual(snapshot(self.gov), before_gov, result.stderr)
        self.assertEqual(result.stdout, "", result.stdout)
        self.assertNotIn("FORBIDDEN", result.stderr)
        self.assertNotIn("revision UNKNOWN", result.stderr)
        self.assertIn("locked interpreter:", result.stderr)
        self.assertIn(
            "gates importable: pydantic + pyyaml + jsonschema (locked env)", result.stderr
        )
        self.assertIn("publish_path_gate=ENFORCED", result.stderr)
        self.assertIn("FIXTURE_AUTH_NOT_LIVE", result.stderr)
        return result

    def _degraded_count(self) -> int:
        argv = json.loads(self.receipt_argv.read_text(encoding="utf-8"))
        return int(argv[argv.index("--degraded-count") + 1])


class RetiredCapabilityPlaneTests(_PlaneBootstrapCase):
    def test_retired_plane_does_not_degrade_or_call_the_stub(self) -> None:
        self._write_owner(exit_code=0)
        stub = self.gov / "ops/secrets/bootstrap_agent_env.sh"
        marker = self.root / "retired-broker-invoked"
        put(
            stub,
            f"#!/bin/bash\necho STUB_RAN >&2\n/bin/touch '{marker}'\nexit 1\n",
            executable=True,
        )
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn("secrets plane: session_start_secrets.py", result.stderr)
        self.assertNotIn("STUB_RAN", result.stderr)
        self.assertFalse(marker.exists(), "retired broker must never execute")
        self.assertIn("Agent environment ready", result.stderr)  # synthetic apply only
        self.assertEqual(self._degraded_count(), 0)


class SecretsPlaneNoSurfaceExemptionTests(_PlaneBootstrapCase):
    """Infisical is the only plane and no surface is exempt from binding it.

    The retired AWS carve-out scored a hosted surface's missing plane as "not a
    fault". Every surface now binds through its machine identity, so a hosted
    surface that did not bind degrades exactly like any other.
    """

    HOSTED = {"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"}

    def test_a_hosted_surface_without_an_identity_degrades(self) -> None:
        self._write_owner(exit_code=1)
        result = self._run(self.HOSTED)
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn("session_start_secrets failed", result.stderr)
        self.assertNotIn("unavailable by surface", result.stderr)
        self.assertNotIn("Agent environment ready", result.stderr)
        self.assertEqual(self._degraded_count(), 1)

    def test_owner_failure_still_degrades(self) -> None:
        """The negative: a surface that should have bound, and did not."""
        self._write_owner(exit_code=1)
        result = self._run()
        self.assertEqual(result.returncode, 6, result.stderr)
        self.assertIn("session_start_secrets failed", result.stderr)
        self.assertNotIn("unavailable by surface", result.stderr)
        self.assertNotIn("Agent environment ready", result.stderr)
        self.assertEqual(self._degraded_count(), 1)

    def test_plane_ok_says_nothing_about_the_surface(self) -> None:
        """state=ok reports the identity and prints no exemption line."""
        self._write_owner(
            exit_code=0,
            receipt={"ok": True, "state": "ok", "surface_class": "operator", "binds": []},
        )
        result = self._run(self.HOSTED)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("unavailable by surface", result.stderr)
        self.assertEqual(self._degraded_count(), 0)


if __name__ == "__main__":
    unittest.main()
