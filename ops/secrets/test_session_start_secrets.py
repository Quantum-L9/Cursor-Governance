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


def _run(
    login_state: str, source: str, binds: list[dict[str, Any]], argv: list[str], env: dict
) -> tuple[dict[str, Any], int, str, str]:
    with (
        mock.patch.dict("os.environ", env, clear=True),
        mock.patch.object(plane.login, "ensure_machine_profile", return_value=login_state),
        mock.patch.object(plane.login, "machine_identity", return_value=(source, None)),
        mock.patch.object(plane.cb, "bind_status", side_effect=_bind_status(binds)),
        mock.patch("sys.stdout", new_callable=io.StringIO) as out,
        mock.patch("sys.stderr", new_callable=io.StringIO) as err,
    ):
        result = plane.run_plane()
        rc = plane.main(argv)
    return result, rc, out.getvalue(), err.getvalue()


class SessionStartSecretsTests(unittest.TestCase):
    """Infisical is the only plane; the machine identity is the one bootstrap."""

    def test_an_identity_that_logs_in_binds_and_exits_0(self) -> None:
        result, rc, _, err = _run("env", "env", BINDS_OK, [], {})
        self.assertTrue(result["plane_ok"])
        self.assertEqual(result["state"], plane.STATE_OK)
        self.assertEqual(result["identity"]["code"], plane.IDENTITY_OK)
        self.assertEqual(result["identity"]["source"], "env")
        self.assertEqual(rc, 0)
        self.assertIn("CONTEXT7_API_KEY=infisical", err)

    def test_context7_is_among_the_names_the_plane_binds(self) -> None:
        self.assertIn("CONTEXT7_API_KEY", plane.BIND_NAMES)

    def test_a_missing_identity_fails_loudly_and_names_the_fix(self) -> None:
        result, rc, _, err = _run("absent", "", BINDS_NONE, [], {})
        self.assertFalse(result["plane_ok"])
        self.assertEqual(result["identity"]["code"], plane.IDENTITY_ABSENT)
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: no Infisical machine identity", err)
        self.assertIn("L9_INFISICAL_CLIENT_ID", err)
        self.assertIn("L9_INFISICAL_CLIENT_SECRET", err)

    def test_a_refused_identity_fails(self) -> None:
        result, rc, _, err = _run("failed", "env", BINDS_NONE, [], {})
        self.assertEqual(result["identity"]["code"], plane.IDENTITY_REFUSED)
        self.assertEqual(rc, 1)
        self.assertIn("FAILED: Infisical refused the machine identity", err)

    def test_no_surface_is_exempt(self) -> None:
        """The retired carve-out scored a hosted surface's absence as 'not a fault'."""
        for env in (
            {"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"},
            {"CLAUDE_CODE_REMOTE_ENVIRONMENT_ID": "ccpool_x"},
            {},
        ):
            with self.subTest(env=env):
                result, rc, _, _ = _run("absent", "", BINDS_NONE, [], env)
                self.assertEqual(result["state"], plane.STATE_FAILED)
                self.assertEqual(rc, 1)

    def test_json_stdout_has_no_values(self) -> None:
        _, rc, out, _ = _run("env", "env", BINDS_OK, ["--json"], {})
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
            _, rc, _, _ = _run("env", "env", BINDS_OK, ["--receipt-out", str(dest)], {})
            self.assertEqual(rc, 0)
            payload = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(payload["identity"]["source"], "env")
            self.assertEqual(len(payload["binds"]), len(plane.BIND_NAMES))

    def test_omit_receipt_out_writes_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "secrets-plane.json"
            _, rc, _, _ = _run("env", "env", BINDS_OK, [], {})
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
        result, _, _, _ = _run("absent", "", BINDS_NONE, [], self.HOSTED)
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
            _, rc, out, err = _run("absent", "", BINDS_NONE, ["--json"], {})
        self.assertEqual(rc, 1)
        self.assertNotIn("CANARY", err)
        self.assertIn("no Infisical machine identity", err)

    def test_bind_sources_are_mapped_to_literals(self) -> None:
        odd = [{**row, "source": "CANARY-SOURCE"} for row in BINDS_OK]
        _, _, _, err = _run("env", "env", odd, [], {})
        self.assertNotIn("CANARY-SOURCE", err)
        self.assertIn("CONTEXT7_API_KEY=unknown", err)
