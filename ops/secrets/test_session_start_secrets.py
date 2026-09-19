#!/usr/bin/env python3
"""session_start_secrets is the SessionStart owner; no values, fail loud."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
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
        # Pinned to an operator surface, where this contract is unchanged. The
        # surface was previously implicit, which made the assertion depend on
        # the machine the suite happened to run on; see SurfaceCarveOutTests
        # for the model-controlled case.
        with (
            mock.patch.dict("os.environ", {}, clear=True),
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
            {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical"},
            {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
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
        self.assertIn("SEMGREP_APP_TOKEN=infisical", err.getvalue())
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
            {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical"},
            {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
            {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"},
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
        self.assertEqual(payload["aws"]["ok"], True)
        self.assertEqual(payload["aws"]["code"], "OK")
        self.assertEqual(payload["aws"]["summary"], "ok")
        self.assertEqual(payload["binds"][0]["source"], "infisical")
        blob = json.dumps(payload)
        self.assertNotIn("secret", blob.lower())
        self.assertNotIn("AKIA", blob)

    def test_receipt_out_writes_same_object(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical"},
            {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
            {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "secrets-plane.json"
            with (
                mock.patch.object(
                    plane.aws_preflight,
                    "probe",
                    return_value={"ok": True, "code": "OK", "summary": "authorized"},
                ),
                mock.patch.object(plane.login, "ensure_machine_profile", return_value="present"),
                mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
                mock.patch("sys.stderr", new_callable=io.StringIO),
            ):
                rc = plane.main(["--receipt-out", str(dest)])
            self.assertEqual(rc, 0)
            payload = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["aws"]["summary"], "authorized")
            self.assertEqual(len(payload["binds"]), 3)

    def test_omit_receipt_out_writes_no_file(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": True, "source": "infisical"},
            {"name": "SONAR_TOKEN", "bound": True, "source": "infisical"},
            {"name": "GITHUB_TOKEN", "bound": True, "source": "infisical"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "secrets-plane.json"
            with (
                mock.patch.object(
                    plane.aws_preflight,
                    "probe",
                    return_value={"ok": True, "code": "OK", "summary": "ok"},
                ),
                mock.patch.object(plane.login, "ensure_machine_profile", return_value="present"),
                mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
                mock.patch("sys.stderr", new_callable=io.StringIO),
            ):
                rc = plane.main([])
            self.assertEqual(rc, 0)
            self.assertFalse(dest.exists())


class SurfaceCarveOutTests(unittest.TestCase):
    """An absent AWS CLI is a fault everywhere EXCEPT a model-controlled surface.

    That surface holds no Infisical bind by design, so scoring its absence as a
    bootstrap fault is a false DEGRADED. A present-but-broken CLI stays a fault
    on every surface, including that one.
    """

    HOSTED = {"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"}
    POOL = {
        "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default",
        "CLAUDE_CODE_REMOTE_ENVIRONMENT_ID": "ccpool_selfhosted",
    }
    OPERATOR: dict[str, str] = {}

    def _plane(self, env: dict[str, str], code: str) -> tuple[dict[str, Any], int, str]:
        binds = [
            {"name": name, "bound": False, "source": "unbound"}
            for name in ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "GITHUB_TOKEN")
        ]
        probe = {"ok": False, "code": code, "summary": f"{code} — down"}
        with (
            mock.patch.dict("os.environ", env, clear=True),
            mock.patch.object(plane.aws_preflight, "probe", return_value=probe),
            mock.patch.object(plane.login, "ensure_machine_profile") as ensure,
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            result = plane.run_plane()
            rc = plane.main([])
            ensure.assert_not_called()
        return result, rc, err.getvalue()

    def test_surface_class_predicate(self) -> None:
        self.assertEqual(plane.surface_class(self.HOSTED), plane.MODEL_CONTROLLED)
        self.assertEqual(plane.surface_class(self.OPERATOR), plane.OPERATOR)
        # A pool id wins over the hosted type: misreading a pool as hosted would
        # silence a real fault, so the ccpool_ test runs first.
        self.assertEqual(plane.surface_class(self.POOL), plane.SELF_HOSTED)

    def test_hosted_missing_cli_is_unavailable_by_surface_and_exits_0(self) -> None:
        result, rc, err = self._plane(self.HOSTED, plane.aws_preflight.AWS_CLI_NOT_FOUND)
        self.assertEqual(result["state"], plane.STATE_UNAVAILABLE_BY_SURFACE)
        self.assertEqual(result["surface_class"], plane.MODEL_CONTROLLED)
        self.assertEqual(rc, 0)
        # Visible, but not as a fault, and never as something to repair here.
        self.assertIn("unavailable by surface", err)
        self.assertNotIn("FAILED", err)
        # The plane still reports that it did not bind. Truth is preserved.
        self.assertFalse(result["plane_ok"])
        self.assertFalse(plane.receipt_payload(result)["ok"])

    def test_hosted_broken_cli_is_still_a_failure(self) -> None:
        for code in ("AWS_NOT_AUTHORIZED", "TIMEOUT"):
            with self.subTest(code=code):
                result, rc, err = self._plane(self.HOSTED, code)
                self.assertEqual(result["state"], plane.STATE_FAILED)
                self.assertEqual(rc, 1)
                self.assertIn("FAILED: AWS CLI is missing or not authorized", err)

    def test_pool_and_operator_missing_cli_still_degrade(self) -> None:
        for label, env in (("self_hosted", self.POOL), ("operator", self.OPERATOR)):
            with self.subTest(surface=label):
                result, rc, err = self._plane(env, plane.aws_preflight.AWS_CLI_NOT_FOUND)
                self.assertEqual(result["state"], plane.STATE_FAILED)
                self.assertEqual(rc, 1)
                self.assertIn("FAILED: AWS CLI is missing or not authorized", err)

    def test_receipt_carries_state_and_surface_class(self) -> None:
        result, _, _ = self._plane(self.HOSTED, plane.aws_preflight.AWS_CLI_NOT_FOUND)
        payload = plane.receipt_payload(result)
        self.assertEqual(payload["state"], plane.STATE_UNAVAILABLE_BY_SURFACE)
        self.assertEqual(payload["surface_class"], plane.MODEL_CONTROLLED)
        self.assertEqual(payload["aws"]["code"], plane.aws_preflight.AWS_CLI_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
