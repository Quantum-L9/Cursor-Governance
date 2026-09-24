#!/usr/bin/env python3
"""session_start_secrets is the SessionStart owner; no values, fail loud."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
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


def _load(name: str = "session_start_secrets") -> Any:
    path = SECRETS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    # Register before exec: a module-level @dataclass resolves its annotations
    # through sys.modules[cls.__module__], which is None for an unregistered
    # module (capability_client.SessionIdentity fails to build otherwise).
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


plane = _load()
capability_client = _load("capability_client")


BINDS_OK = [
    {"name": name, "bound": True, "source": "infisical"}
    for name in ("SEMGREP_APP_TOKEN", "SONAR_TOKEN", "GITHUB_TOKEN", "CONTEXT7_API_KEY")
]
BINDS_NONE = [{**row, "bound": False, "source": "infisical-machine-absent"} for row in BINDS_OK]


HOSTED = {"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"}
AWS_OK = {"ok": True, "code": "OK", "summary": "authorized"}
AWS_DOWN = {"ok": False, "code": "AWS_CLI_NOT_FOUND", "summary": "AWS_CLI_NOT_FOUND"}


def _run(
    login_state: str,
    source: str,
    binds: list[dict[str, Any]],
    argv: list[str],
    env: dict,
    aws: dict | None = None,
    login_failed: mock.MagicMock | None = None,
) -> tuple[dict[str, Any], int, str, str]:
    with (
        mock.patch.dict("os.environ", env, clear=True),
        mock.patch.object(plane, "_aws_probe", return_value=aws or AWS_OK),
        mock.patch.object(plane.login, "ensure_machine_profile", return_value=login_state),
        mock.patch.object(plane.login, "machine_identity", return_value=(source, None)),
        mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
        # Process-global in capability_bind; never let a test leave it set.
        mock.patch.object(plane.cb, "note_login_failed", login_failed or mock.MagicMock()),
        mock.patch("sys.stdout", new_callable=io.StringIO) as out,
        mock.patch("sys.stderr", new_callable=io.StringIO) as err,
    ):
        result = plane.run_plane()
        rc = plane.main(argv)
    return result, rc, out.getvalue(), err.getvalue()


class SessionStartSecretsTests(unittest.TestCase):
    """Claude: the environment machine identity, no AWS step (run as hosted)."""

    def test_an_identity_that_logs_in_binds_and_exits_0(self) -> None:
        result, rc, _, err = _run("env", "env", BINDS_OK, [], HOSTED)
        self.assertTrue(result["plane_ok"])
        self.assertEqual(result["state"], plane.STATE_OK)
        self.assertEqual(result["identity"]["code"], plane.IDENTITY_OK)
        self.assertEqual(result["identity"]["source"], "env")
        self.assertEqual(rc, 0)
        self.assertIn("CONTEXT7_API_KEY=infisical", err)

    def test_context7_is_among_the_names_the_plane_binds(self) -> None:
        self.assertIn("CONTEXT7_API_KEY", plane.BIND_NAMES)

    def test_a_missing_identity_fails_loudly_and_names_the_fix(self) -> None:
        result, rc, _, err = _run("absent", "", BINDS_NONE, [], HOSTED)
        self.assertFalse(result["plane_ok"])
        self.assertEqual(result["identity"]["code"], plane.IDENTITY_ABSENT)
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: no Infisical machine identity", err)
        self.assertIn("L9_INFISICAL_CLIENT_ID", err)
        self.assertIn("L9_INFISICAL_CLIENT_SECRET", err)

    def test_a_refused_identity_fails(self) -> None:
        result, rc, _, err = _run("failed", "env", BINDS_NONE, [], HOSTED)
        self.assertEqual(result["identity"]["code"], plane.IDENTITY_REFUSED)
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: Infisical refused the machine identity", err)

    def test_a_failed_login_is_not_repeated_by_every_bind(self) -> None:
        """One login attempt per plane run, not one per name.

        On an egress-denied host each attempt cost ~1.1 s and the plane made
        four (the identity check, then three binds), 4.5 s of a 30 s
        SessionStart budget spent learning the same thing four times.
        """
        failed = mock.MagicMock()
        _run("failed", "env", BINDS_NONE, [], HOSTED, login_failed=failed)
        failed.assert_called()
        ok = mock.MagicMock()
        _run("env", "env", BINDS_OK, [], HOSTED, login_failed=ok)
        ok.assert_not_called()

    def test_no_surface_is_exempt(self) -> None:
        """The retired carve-out scored a hosted surface's absence as 'not a fault'."""
        for env, aws in (
            (HOSTED, None),
            ({"CLAUDE_CODE_REMOTE_ENVIRONMENT_ID": "ccpool_x"}, AWS_DOWN),
            ({}, AWS_DOWN),
        ):
            with self.subTest(env=env):
                result, rc, _, _ = _run("absent", "", BINDS_NONE, [], env, aws)
                self.assertEqual(result["state"], plane.STATE_FAILED)
                self.assertEqual(rc, 1)

    def test_claude_never_probes_aws(self) -> None:
        with (
            mock.patch.dict("os.environ", HOSTED, clear=True),
            mock.patch.object(plane, "_aws_probe") as probe,
            mock.patch.object(
                plane.login, "ensure_machine_profile", return_value="absent"
            ) as ensure,
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(BINDS_NONE)),
        ):
            result = plane.run_plane()
        probe.assert_not_called()
        ensure.assert_called_once()
        self.assertNotIn("allow_aws_seed", ensure.call_args.kwargs)
        self.assertNotIn("aws", plane.receipt_payload(result))


class OperatorPathTests(unittest.TestCase):
    """Cursor / operator: main's behaviour, unchanged — AWS preflight, then seed."""

    def test_aws_down_fails_with_mains_message_and_never_seeds(self) -> None:
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(plane, "_aws_probe", return_value=AWS_DOWN),
            mock.patch.object(plane.login, "machine_identity", return_value=("", None)),
            mock.patch.object(plane.login, "ensure_machine_profile") as ensure,
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(BINDS_NONE)),
            mock.patch("sys.stderr", new_callable=io.StringIO) as err,
        ):
            result = plane.run_plane()
            rc = plane.main([])
        ensure.assert_not_called()
        self.assertEqual(result["login"], "skipped")
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: AWS CLI is missing or not authorized", err.getvalue())
        self.assertEqual(plane.receipt_payload(result)["aws"]["code"], "AWS_CLI_NOT_FOUND")

    def test_aws_ok_seeds_or_uses_the_profile(self) -> None:
        for state in ("present", "seeded"):
            with self.subTest(state=state):
                with (
                    mock.patch.dict("os.environ", {}, clear=True),
                    mock.patch.object(plane, "_aws_probe", return_value=AWS_OK),
                    mock.patch.object(
                        plane.login, "machine_identity", return_value=("profile", None)
                    ),
                    mock.patch.object(
                        plane.login, "ensure_machine_profile", return_value=state
                    ) as ensure,
                    mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(BINDS_OK)),
                ):
                    result = plane.run_plane()
                self.assertTrue(ensure.call_args.kwargs.get("allow_aws_seed"))
                self.assertTrue(result["plane_ok"])
                self.assertTrue(plane.receipt_payload(result)["aws"]["ok"])

    def test_an_environment_identity_on_an_operator_needs_no_aws(self) -> None:
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(plane, "_aws_probe") as probe,
            mock.patch.object(plane.login, "machine_identity", return_value=("env", None)),
            mock.patch.object(plane.login, "ensure_machine_profile", return_value="env"),
            mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(BINDS_OK)),
        ):
            result = plane.run_plane()
        probe.assert_not_called()
        self.assertTrue(result["plane_ok"])

    def test_json_stdout_has_no_values(self) -> None:
        _, rc, out, _ = _run("env", "env", BINDS_OK, ["--json"], HOSTED)
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["identity"]["ok"], True)
        self.assertNotIn("aws", payload)
        blob = json.dumps(payload)
        self.assertNotIn("client_secret", blob.lower())
        self.assertNotIn("AKIA", blob)

    def test_receipt_out_writes_same_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "secrets-plane.json"
            _, rc, _, _ = _run("env", "env", BINDS_OK, ["--receipt-out", str(dest)], HOSTED)
            self.assertEqual(rc, 0)
            payload = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(payload["identity"]["source"], "env")
            self.assertEqual(len(payload["binds"]), len(plane.BIND_NAMES))

    def test_omit_receipt_out_writes_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "secrets-plane.json"
            _, rc, _, _ = _run("env", "env", BINDS_OK, [], HOSTED)
            self.assertEqual(rc, 0)
            self.assertFalse(dest.exists())

    def test_the_plane_imports_nothing_from_aws(self) -> None:
        import subprocess

        probe = (
            "import sys; sys.path.insert(0, sys.argv[1]); import session_start_secrets; "
            "bad = sorted(m for m in sys.modules if m in "
            "{'aws_cli_preflight','resolve_secret','login_registry','port_aws_to_infisical',"
            "'boto3','botocore'}); print(','.join(bad))"
        )
        out = subprocess.run(
            [sys.executable, "-c", probe, str(SECRETS)],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(out, "", f"AWS modules imported by the plane: {out}")


class SurfaceClassTests(unittest.TestCase):
    """Surface class is reported for context; it no longer exempts anything."""

    HOSTED = {"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"}
    POOL = {
        "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default",
        "CLAUDE_CODE_REMOTE_ENVIRONMENT_ID": "ccpool_selfhosted",
    }
    OPERATOR: dict[str, str] = {}

    def test_surface_class_predicate(self) -> None:
        self.assertEqual(plane.surface_class(self.HOSTED), plane.MODEL_CONTROLLED)
        self.assertEqual(plane.surface_class(self.OPERATOR), plane.OPERATOR)
        # A pool id wins over the hosted type: misreading a pool as hosted would
        # silence a real fault, so the ccpool_ test runs first.
        self.assertEqual(plane.surface_class(self.POOL), plane.SELF_HOSTED)

    def test_predicate_agrees_with_the_capability_client_precedent(self) -> None:
        """The surface predicate now has two owners. Pin them together.

        ``surface_class`` copies the hosted/pool distinction from
        ``capability_client.session_identity``. Copying it is what makes the
        classification reviewable, but it also means the two can drift apart
        silently. This test fails when they stop agreeing.
        """
        # capability_client treats cloud_default as issuing no session identity,
        # with a hosted-specific reason. That is its name for model_controlled.
        hosted_identity = capability_client.session_identity(self.HOSTED)
        self.assertEqual(hosted_identity.reason, "hosted_surface_issues_no_session_identity")
        self.assertEqual(plane.surface_class(self.HOSTED), plane.MODEL_CONTROLLED)

        # An operator machine is neither hosted nor a pool in either module.
        operator_identity = capability_client.session_identity(self.OPERATOR)
        self.assertEqual(operator_identity.reason, "no_session_identity_available")
        self.assertEqual(plane.surface_class(self.OPERATOR), plane.OPERATOR)

        # The pool case, asserted against session_identity's real behaviour
        # rather than against the prefix. session_identity only mints a pool
        # identity when CLAUDE_SESSION_IDENTITY_TOKEN_FILE is present and
        # readable, so the environment has to carry one for this to exercise
        # its pool branch at all.
        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "session-identity.jwt"
            token_file.write_text("not-a-real-token", encoding="utf-8")
            pool_env = dict(self.POOL)
            pool_env["CLAUDE_SESSION_IDENTITY_TOKEN_FILE"] = str(token_file)

            pool_identity = capability_client.session_identity(pool_env)
            # capability_client took its pool branch: it classifies this
            # environment as self-hosted, NOT as the hosted surface.
            self.assertEqual(pool_identity.method, "ccr-session-jwt")
            self.assertIn("self-hosted", pool_identity.detail)
            self.assertNotEqual(pool_identity.reason, "hosted_surface_issues_no_session_identity")
            # And surface_class agrees on the same environment.
            self.assertEqual(plane.surface_class(pool_env), plane.SELF_HOSTED)

        # Precedence is the part that matters: both modules must prefer the
        # pool signal over cloud_default, since this environment carries both.
        self.assertEqual(self.POOL["CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE"], "cloud_default")
        self.assertEqual(plane.surface_class(self.POOL), plane.SELF_HOSTED)
        self.assertNotEqual(plane.surface_class(self.POOL), plane.MODEL_CONTROLLED)

    def test_receipt_carries_state_and_surface_class(self) -> None:
        result, _, _, _ = _run("absent", "", BINDS_NONE, [], HOSTED)
        payload = plane.receipt_payload(result)
        self.assertEqual(payload["state"], plane.STATE_FAILED)
        self.assertEqual(payload["surface_class"], plane.MODEL_CONTROLLED)
        self.assertEqual(payload["identity"]["code"], plane.IDENTITY_ABSENT)


if __name__ == "__main__":
    unittest.main()


class LiteralOutputTests(unittest.TestCase):
    """stderr carries module literals only — never a string from the identity."""

    def test_a_planted_identity_summary_never_reaches_stderr(self) -> None:
        planted = {"ok": False, "code": plane.IDENTITY_ABSENT, "source": "", "summary": "CANARY"}
        with mock.patch.object(plane, "identity_status", return_value=planted):
            _, rc, out, err = _run("absent", "", BINDS_NONE, ["--json"], HOSTED)
        self.assertEqual(rc, 1)
        self.assertNotIn("CANARY", err)
        self.assertIn("no Infisical machine identity", err)

    def test_bind_sources_are_mapped_to_literals(self) -> None:
        odd = [{**row, "source": "CANARY-SOURCE"} for row in BINDS_OK]
        _, _, _, err = _run("env", "env", odd, [], HOSTED)
        self.assertNotIn("CANARY-SOURCE", err)
        self.assertIn("CONTEXT7_API_KEY=unknown", err)
