"""Consumer exec-env provisioning: the requirements fallback chain.

A consumer repo without a `[project]` table (an Odoo addon suite, for
example) cannot be editable-installed, so `uv pip install -e .[dev]` fails.
The provisioning must fall back to the repo's canonical dev dependencies
(`requirements-dev.txt`, then `requirements.txt`) instead of leaving an
empty venv whose validation commands fail with "No module named pytest".
"""

from __future__ import annotations

import sys
import unittest
import unittest.mock as mock
from pathlib import Path

from helpers import SCRIPTS

sys.path.insert(0, str(SCRIPTS))
from pec import exec_env

VENV_PYTHON = Path("/tmp/env-root/.venv/bin/python3")
# _consumer_project_python consults _provisioned_python three times: for the
# existing env, the venv-creation condition, and the final python.
PROVISION_SEQUENCE = [None, None, VENV_PYTHON]


class _Subprocess:
    """Fake subprocess.run recording argv; return codes per command index."""

    def __init__(self, results: list[int]) -> None:
        self.results = results
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        return mock.Mock(returncode=self.results[len(self.calls) - 1])


class ConsumerProvisioningTests(unittest.TestCase):
    def _run(self, results: list[int], cwd: Path, is_file):
        fake = _Subprocess(results)
        with mock.patch.object(exec_env, "exec_env_root", return_value=Path("/tmp/env-root")), \
                mock.patch.object(
                    exec_env, "_provisioned_python", side_effect=list(PROVISION_SEQUENCE)
                ), mock.patch.object(exec_env, "_existing_venv_python", return_value=None), \
                mock.patch.object(exec_env.shutil, "which", return_value="/usr/local/bin/uv"), \
                mock.patch.object(exec_env.subprocess, "run", fake), \
                mock.patch.object(Path, "is_file", is_file):
            result = exec_env._consumer_project_python(cwd)
        return result, fake

    def test_editable_failure_falls_back_to_requirements_dev(self) -> None:
        cwd = Path("/tmp/consumer-repo")
        result, fake = self._run([0, 1, 0], cwd, lambda path: True)
        self.assertEqual(result, VENV_PYTHON)
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(fake.calls[2][-2:], ["-r", str(cwd / "requirements-dev.txt")])

    def test_requirements_txt_used_when_dev_absent(self) -> None:
        cwd = Path("/tmp/consumer-repo")

        def fake_is_file(path_or_instance):
            name = getattr(path_or_instance, "name", str(path_or_instance))
            return name in {"pyproject.toml", "requirements.txt"}

        result, fake = self._run([0, 1, 0], cwd, fake_is_file)
        self.assertEqual(result, VENV_PYTHON)
        self.assertEqual(len(fake.calls), 3)
        self.assertEqual(fake.calls[2][-2:], ["-r", str(cwd / "requirements.txt")])

    def test_all_installs_failing_returns_the_bare_venv_python(self) -> None:
        cwd = Path("/tmp/consumer-repo")
        result, fake = self._run([0, 1, 1, 1], cwd, lambda path: True)
        self.assertEqual(result, VENV_PYTHON)
        self.assertEqual(len(fake.calls), 4)


if __name__ == "__main__":
    unittest.main()
