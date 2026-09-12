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


def _operator_trust() -> Any:
    """A surface that MAY hold raw secret material.

    These cases are about the seeding path itself — AWS preflight, the Infisical
    machine profile, what is printed on failure — and that path only exists on a
    surface `surface_trust` lets hold raw values. The surface was previously
    implicit, which meant the suite asserted the seeding path while running
    inside a model-controlled runtime, where governance forbids it. Pinning it
    makes each case say which half of the boundary it is testing.
    """
    return plane.surface_trust.SurfaceTrust(
        surface="operator",
        trust_class=plane.surface_trust.TRUSTED_OPERATOR,
        raw_secret_allowed=True,
        reason="test: registered trusted-operator class",
    )


def _model_trust(surface: str = "claude-code") -> Any:
    """A surface that MUST NOT hold raw secret material."""
    return plane.surface_trust.SurfaceTrust(
        surface=surface,
        trust_class=plane.surface_trust.MODEL_CONTROLLED,
        raw_secret_allowed=False,
        reason=f"test: '{surface}' is a registered model-controlled surface",
    )


def _trust(decision: Any) -> Any:
    return mock.patch.object(plane.surface_trust, "classify", return_value=decision)


class SessionStartSecretsTests(unittest.TestCase):
    def test_aws_fail_skips_seed_and_exits_1(self) -> None:
        binds = [
            {"name": "SEMGREP_APP_TOKEN", "bound": False, "source": "unbound"},
            {"name": "SONAR_TOKEN", "bound": False, "source": "unbound"},
            {"name": "GITHUB_TOKEN", "bound": False, "source": "unbound"},
        ]
        with (
            _trust(_operator_trust()),
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
            _trust(_operator_trust()),
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
            _trust(_operator_trust()),
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
            _trust(_operator_trust()),
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
                _trust(_operator_trust()),
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
                _trust(_operator_trust()),
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


class ModelControlledBoundaryTests(unittest.TestCase):
    """A surface that may not hold raw material is not a degraded surface.

    The AWS/Infisical seeding path is prohibited on a model-controlled surface,
    not merely unavailable: `surface_trust` says such a caller "receives
    *capabilities*, never values". Reporting its absence as a plane FAILURE made
    `bootstrap_agent_environment.sh` count a degradation, `install.sh` map exit 6
    to STATUS_SHARED=DEGRADED, and — `downgrade` being monotone — pinned the
    whole bootstrap receipt DEGRADED on every hosted session, against a condition
    whose only printed repair ("install AWS CLI v2") governance forbids here.
    """

    def _binds(self) -> list[dict[str, Any]]:
        return [
            {"name": "SEMGREP_APP_TOKEN", "bound": False, "source": "capability"},
            {"name": "SONAR_TOKEN", "bound": False, "source": "capability"},
            {"name": "GITHUB_TOKEN", "bound": False, "source": "capability"},
        ]

    def test_model_surface_does_not_probe_and_exits_zero(self) -> None:
        with (
            _trust(_model_trust()),
            mock.patch.object(plane.aws_preflight, "probe") as probe,
            mock.patch.object(plane.login, "ensure_machine_profile") as ensure,
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(self._binds())),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            result = plane.run_plane()
            rc = plane.main([])
        # The preflight is never run: probing for a CLI whose repair is
        # prohibited here would report a failure about a path that does not apply.
        probe.assert_not_called()
        ensure.assert_not_called()
        self.assertTrue(result["plane_ok"])
        self.assertEqual(result["login"], plane.NOT_APPLICABLE)
        self.assertEqual(result["aws"]["code"], plane.NOT_ATTEMPTED)
        self.assertEqual(rc, 0, "a by-design boundary must not be counted as a degradation")

    def test_the_boundary_is_reported_not_swallowed(self) -> None:
        with (
            _trust(_model_trust()),
            mock.patch.object(plane.aws_preflight, "probe"),
            mock.patch.object(plane.login, "ensure_machine_profile"),
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(self._binds())),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            plane.main([])
        text = err.getvalue()
        self.assertIn("model-controlled", text)
        self.assertIn("by design", text)
        self.assertNotIn("FAILED", text, "a by-design absence is not a failure")
        # Still names what is and is not bound, so the exit-0 is legible.
        self.assertIn("SEMGREP_APP_TOKEN=capability", text)

    def test_a_model_surface_never_reaches_the_seed_even_with_aws_present(self) -> None:
        """The branch is the boundary, not the AWS CLI's availability.

        A model-controlled runtime that happens to have a working `aws` must
        still not seed — otherwise the carve-out would become a capability test
        instead of a trust-boundary one.
        """
        with (
            _trust(_model_trust()),
            mock.patch.object(
                plane.aws_preflight,
                "probe",
                return_value={"ok": True, "code": "OK", "summary": "ok"},
            ) as probe,
            mock.patch.object(plane.login, "ensure_machine_profile") as ensure,
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(self._binds())),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            result = plane.run_plane()
        probe.assert_not_called()
        ensure.assert_not_called()
        self.assertEqual(result["login"], plane.NOT_APPLICABLE)

    def test_receipt_out_on_a_model_surface_is_well_formed(self) -> None:
        """`--receipt-out` writes before the boundary arm is reached.

        `main` persists the receipt ahead of every exit path, so the early
        return must still carry each declared field. A missing `aws.summary`
        would be written as an empty string rather than raising, which is why
        this is asserted on the file and not only on the in-memory object.
        """
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "secrets-plane.json"
            with (
                _trust(_model_trust()),
                mock.patch.object(plane.aws_preflight, "probe"),
                mock.patch.object(plane.login, "ensure_machine_profile"),
                mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(self._binds())),
                mock.patch("sys.stderr", new_callable=io.StringIO),
            ):
                rc = plane.main(["--receipt-out", str(dest)])
            self.assertEqual(rc, 0)
            payload = json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["login"], plane.NOT_APPLICABLE)
        self.assertEqual(payload["aws"]["code"], plane.NOT_ATTEMPTED)
        self.assertNotEqual(payload["aws"]["summary"], "")
        self.assertEqual(len(payload["binds"]), 3)

    def test_an_operator_surface_still_fails_loud(self) -> None:
        """The carve-out must not weaken the surface it does not apply to."""
        with (
            _trust(_operator_trust()),
            mock.patch.object(
                plane.aws_preflight,
                "probe",
                return_value={"ok": False, "code": "AWS_CLI_NOT_FOUND", "summary": "down"},
            ),
            mock.patch.object(plane.login, "ensure_machine_profile"),
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(self._binds())),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            rc = plane.main([])
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: AWS CLI is missing or not authorized", err.getvalue())

    def test_the_branch_is_the_shared_classifier_not_a_surface_env_read(self) -> None:
        """One place decides. This file must not grow a second surface check.

        `surface_trust.classify` default-denies, and refuses an operator claim
        raised from inside a model runtime — properties a local
        `L9_GOVERNANCE_SURFACE` read here would not have.
        """
        source = (SECRETS / "session_start_secrets.py").read_text(encoding="utf-8")
        self.assertIn("surface_trust.classify()", source)
        self.assertIn("raw_secret_allowed", source)
        # The property is "reads no environment here", not "never says the
        # variable's name" — the docstring names it precisely to say it is NOT
        # read. Assert on the code: the module imports no `os` at all.
        self.assertNotIn("os.environ", source)
        self.assertNotIn("getenv", source)
        self.assertNotIn("\nimport os", source)


if __name__ == "__main__":
    unittest.main()
