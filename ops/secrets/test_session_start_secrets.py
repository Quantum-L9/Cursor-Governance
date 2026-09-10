#!/usr/bin/env python3
"""session_start_secrets is the SessionStart owner; no values, fail loud."""

from __future__ import annotations

import importlib.util
import io
import json
import unittest
import unittest.mock as mock
from pathlib import Path
from typing import Any

SECRETS = Path(__file__).resolve().parent


def _bind_status(rows: list[dict[str, Any]]) -> Any:
    by_name = {str(row["name"]): row for row in rows}

    def _lookup(name: str) -> dict[str, Any]:
        return by_name[name]

    return _lookup


def _load() -> Any:
    path = SECRETS / "session_start_secrets.py"
    spec = importlib.util.spec_from_file_location("session_start_secrets", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


plane = _load()


class SessionStartSecretsTests(unittest.TestCase):
    def test_aws_fail_skips_seed_and_exits_1(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": False, "source": "unbound"},
            {"name": "SONAR_TOKEN", "bound": False, "source": "unbound"},
            {"name": "GITHUB_TOKEN", "bound": False, "source": "unbound"},
        ]
        with (
            mock.patch.object(
                plane.aws_preflight,
                "probe",
                return_value={"ok": False, "code": "AWS_CLI_NOT_FOUND", "summary": "down"},
            ),
            mock.patch.object(plane.login, "ensure_machine_profile") as ensure,
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            result = plane.run_plane()
            rc = plane.main([])
        self.assertFalse(result["plane_ok"])
        self.assertEqual(result["login"], "skipped")
        ensure.assert_not_called()
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: AWS CLI is missing or not authorized", err.getvalue())
        self.assertNotIn("AKIA", err.getvalue())

    def test_aws_ok_with_profile_does_not_reseed(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical-cli"},
            {"name": "SONAR_TOKEN", "bound": True, "source": "infisical-cli"},
            {"name": "GITHUB_TOKEN", "bound": True, "source": "env"},
        ]
        with (
            mock.patch.object(
                plane.aws_preflight,
                "probe",
                return_value={"ok": True, "code": "OK", "summary": "ok"},
            ),
            mock.patch.object(plane.login, "ensure_machine_profile", return_value="present"),
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            result = plane.run_plane()
            rc = plane.main(["--json"])
        self.assertTrue(result["plane_ok"])
        self.assertEqual(result["login"], "present")
        self.assertEqual(rc, 0)
        self.assertIn("SEMGREP_APP_TOKEN=infisical-cli", err.getvalue())
        self.assertNotIn("client_secret", err.getvalue())

    def test_login_failed_is_plane_failure(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": False, "source": "unbound"},
            {"name": "SONAR_TOKEN", "bound": False, "source": "unbound"},
            {"name": "GITHUB_TOKEN", "bound": False, "source": "unbound"},
        ]
        with (
            mock.patch.object(
                plane.aws_preflight,
                "probe",
                return_value={"ok": True, "code": "OK", "summary": "ok"},
            ),
            mock.patch.object(plane.login, "ensure_machine_profile", return_value="failed"),
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            result = plane.run_plane()
            rc = plane.main([])
        self.assertFalse(result["plane_ok"])
        self.assertEqual(result["login"], "failed")
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: Infisical machine profile failed", err.getvalue())

    def test_json_stdout_has_no_values(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical-cli"},
            {"name": "SONAR_TOKEN", "bound": True, "source": "infisical-cli"},
            {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical-cli"},
        ]
        with (
            mock.patch.object(
                plane.aws_preflight,
                "probe",
                return_value={"ok": True, "code": "OK", "summary": "ok"},
            ),
            mock.patch.object(plane.login, "ensure_machine_profile", return_value="present"),
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
            mock.patch("sys.stdout", new_callable=io.StringIO) as out,
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            rc = plane.main(["--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["login"], "present")
        blob = json.dumps(payload)
        self.assertNotIn("secret", blob.lower())


if __name__ == "__main__":
    unittest.main()
