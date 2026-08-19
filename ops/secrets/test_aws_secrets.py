#!/usr/bin/env python3
"""Unit tests for ops/secrets sync + resolve (mocked AWS; no live secret values)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SECRETS = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    path = SECRETS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sync = _load("sync_secrets_registry")
resolve = _load("resolve_secret")


class SyncRegistryTests(unittest.TestCase):
    def test_aws_discover_adds_new_and_merges_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            prior = td / "registry.yaml"
            prior.write_text(
                "schema_version: '1.0.0'\n"
                "namespace: openclaw-igorbot\n"
                "region_default: us-east-1\n"
                "source: {}\n"
                "secrets:\n"
                "  - secret_id: openclaw-igorbot/github\n"
                "    enabled: true\n"
                "    region: us-east-1\n"
                "    provisioned: true\n"
                "    origin: aws_sm\n"
                "    keys:\n"
                "      - json_key: token\n"
                "        note: kept-annotation\n",
                encoding="utf-8",
            )
            overlays = td / "overlays.yaml"
            overlays.write_text(
                "schema_version: '1.0.0'\noverlays:\n"
                "  - secret_id: openclaw-igorbot/ui-session-github\n"
                "    enabled: true\n"
                "    region: us-east-1\n"
                "    provisioned: false\n"
                "    origin: governance_overlay\n"
                "    keys:\n"
                "      - json_key: storage_state\n",
                encoding="utf-8",
            )
            ids_file = td / "aws-ids.json"
            ids_file.write_text(
                json.dumps(
                    [
                        "openclaw-igorbot/github",
                        "openclaw-igorbot/vercel",
                    ]
                ),
                encoding="utf-8",
            )

            def fake_inspect(secret_id: str, region: str, **kwargs: Any) -> Any:
                if secret_id.endswith("/vercel"):
                    return ["token"], None
                return None, None

            with mock.patch.object(sync, "inspect_json_keys", side_effect=fake_inspect):
                rc = sync.main(
                    [
                        "--out",
                        str(prior),
                        "--overlays",
                        str(overlays),
                        "--aws-ids-file",
                        str(ids_file),
                        "--json-summary",
                    ]
                )
            self.assertEqual(rc, 0)
            text = prior.read_text(encoding="utf-8")
            self.assertIn("openclaw-igorbot/github", text)
            self.assertIn("openclaw-igorbot/vercel", text)
            self.assertIn("ui-session-github", text)
            self.assertIn("kept-annotation", text)
            self.assertIn("authority: cursor-governance", text)
            self.assertNotIn("igorbot_csv", text)
            self.assertNotIn("Quantum-L9/igorbot", text)
            self.assertNotIn("ghp_", text)

    def test_no_external_repo_fetch_helpers(self) -> None:
        self.assertFalse(hasattr(sync, "fetch_csv_gh"))
        self.assertFalse(hasattr(sync, "fetch_csv_http"))
        self.assertFalse(hasattr(sync, "DEFAULT_GH_REPO"))


class ResolveSecretTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.td = Path(self.tmp.name)
        self.registry_path = self.td / "registry.yaml"
        self.registry_path.write_text(
            "schema_version: '1.0.0'\n"
            "namespace: openclaw-igorbot\n"
            "region_default: us-east-1\n"
            "source: {authority: cursor-governance}\n"
            "secrets:\n"
            "  - secret_id: openclaw-igorbot/github\n"
            "    enabled: true\n"
            "    region: us-east-1\n"
            "    provisioned: true\n"
            "    origin: aws_sm\n"
            "    keys:\n"
            "      - json_key: token\n"
            "  - secret_id: openclaw-igorbot/ui-session-github\n"
            "    enabled: true\n"
            "    region: us-east-1\n"
            "    provisioned: false\n"
            "    origin: governance_overlay\n"
            "    keys:\n"
            "      - json_key: storage_state\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_check_ok_never_echoes_value(self) -> None:
        secret_value = "SUPER_SECRET_TOKEN_VALUE_XYZ"
        # --check is non-value-bearing: it probes metadata, never the value. The
        # value fetcher is mocked so that a regression which reintroduced it would
        # be caught by the assert_not_called below rather than silently passing.
        with mock.patch.object(
            resolve,
            "fetch_secret_string",
            return_value=(json.dumps({"token": secret_value}), None),
        ) as fetch:
            with mock.patch.object(resolve, "probe_secret_metadata", return_value=None):
                with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                        rc = resolve.main(
                            [
                                "--ref",
                                "openclaw-igorbot/github#token",
                                "--check",
                                "--registry",
                                str(self.registry_path),
                            ]
                        )
                        stdout = out.getvalue()
                        stderr = err.getvalue()
        self.assertEqual(rc, 0)
        fetch.assert_not_called()
        self.assertIn("OK", stdout)
        self.assertNotIn("openclaw-igorbot", stdout)
        self.assertNotIn("token", stdout.lower().replace("super_secret_token_value_xyz", ""))
        self.assertNotIn(secret_value, stdout)
        self.assertNotIn(secret_value, stderr)
        self.assertNotIn("#token", stdout)
        self.assertNotIn("#token", stderr)

    def test_unregistered_fail_closed(self) -> None:
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            rc = resolve.main(
                [
                    "--ref",
                    "openclaw-igorbot/nope#token",
                    "--check",
                    "--registry",
                    str(self.registry_path),
                ]
            )
            self.assertEqual(rc, 1)
            self.assertIn("FAIL", out.getvalue())

    def test_not_provisioned(self) -> None:
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            rc = resolve.main(
                [
                    "--ref",
                    "openclaw-igorbot/ui-session-github#storage_state",
                    "--check",
                    "--registry",
                    str(self.registry_path),
                ]
            )
            self.assertEqual(rc, 1)
            self.assertIn("FAIL", out.getvalue())

    def test_split_id(self) -> None:
        self.assertEqual(
            resolve.split_id("openclaw-igorbot/github#token"),
            ("openclaw-igorbot/github", "token"),
        )


class RawResolutionTrustBoundaryTests(unittest.TestCase):
    """F-05 — raw resolution is trusted-operator-only; --check stays open.

    No live AWS access: ``fetch_secret_string`` is always mocked, and the denial
    cases additionally assert it was never reached. The fixture value below is a
    synthetic placeholder, never a credential, and every case asserts it does not
    reach any output stream.
    """

    FAKE_VALUE = "PLACEHOLDER_NOT_A_CREDENTIAL_0000"
    REF = "openclaw-igorbot/github#token"

    #: A model-controlled surface with no operator claim.
    MODEL_ENV = {"L9_GOVERNANCE_SURFACE": "claude-code"}
    #: An operator claim raised from inside a model runtime — must be refused.
    ESCALATION_ENV = {"L9_GOVERNANCE_SURFACE": "operator", "CLAUDECODE": "1"}
    #: A genuine operator shell: operator id, no model-runtime markers.
    TRUSTED_ENV = {"L9_GOVERNANCE_SURFACE": "operator"}

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.registry_path = Path(self.tmp.name) / "registry.yaml"
        self.registry_path.write_text(
            "schema_version: '1.0.0'\n"
            "namespace: openclaw-igorbot\n"
            "region_default: us-east-1\n"
            "source: {authority: cursor-governance}\n"
            "secrets:\n"
            "  - secret_id: openclaw-igorbot/github\n"
            "    enabled: true\n"
            "    region: us-east-1\n"
            "    provisioned: true\n"
            "    origin: aws_sm\n"
            "    keys:\n"
            "      - json_key: token\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run_cli(self, env: dict[str, str], *extra: str) -> tuple[int, str, str, Any, Any, Any]:
        """Run main() under a simulated surface with BOTH provider paths mocked.

        Returning the value fetcher and the metadata prober separately is what
        lets each case assert which provider operation actually happened.
        """
        argv = ["--ref", self.REF, "--registry", str(self.registry_path), *extra]
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch.object(
                resolve,
                "fetch_secret_string",
                return_value=(json.dumps({"token": self.FAKE_VALUE}), None),
            ) as fetch:
                with mock.patch.object(
                    resolve, "probe_secret_metadata", return_value=None
                ) as probe:
                    with mock.patch.object(resolve, "_emit_secret_value") as emit:
                        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                                rc = resolve.main(argv)
                                return (
                                    rc,
                                    out.getvalue(),
                                    err.getvalue(),
                                    fetch,
                                    probe,
                                    emit,
                                )

    def _assert_no_value_escaped(self, stdout: str, stderr: str, emit: Any) -> None:
        # _emit_secret_value writes to raw fd 1, so a captured-stdout assertion
        # alone would pass vacuously. Assert the emitter itself was never called.
        emit.assert_not_called()
        self.assertNotIn(self.FAKE_VALUE, stdout)
        self.assertNotIn(self.FAKE_VALUE, stderr)

    # --- A: model-controlled raw resolution is refused -----------------------

    def test_model_controlled_raw_resolution_is_denied(self) -> None:
        rc, stdout, stderr, fetch, _probe, emit = self._run_cli(self.MODEL_ENV)
        self.assertEqual(rc, 1)
        # Refusal happens before retrieval, not after.
        fetch.assert_not_called()
        self._assert_no_value_escaped(stdout, stderr, emit)
        # Attributable to the trust boundary, not to AWS availability.
        self.assertIn("DENIED", stderr)
        self.assertIn("model-controlled", stderr)
        self.assertNotIn("AWS_CLI_NOT_FOUND", stderr)

    def test_operator_claim_from_model_runtime_is_refused(self) -> None:
        rc, stdout, stderr, fetch, _probe, emit = self._run_cli(self.ESCALATION_ENV)
        self.assertEqual(rc, 1)
        fetch.assert_not_called()
        self._assert_no_value_escaped(stdout, stderr, emit)
        self.assertIn("claim refused", stderr)

    def test_value_path_is_guarded_against_direct_import(self) -> None:
        """The boundary holds for callers that skip the CLI entirely."""
        with mock.patch.dict(os.environ, self.MODEL_ENV, clear=True):
            with mock.patch.object(resolve, "fetch_secret_string") as fetch:
                with self.assertRaises(PermissionError):
                    resolve.resolve_ref(self.REF, "us-east-1")
        fetch.assert_not_called()

    # --- B: --check stays available to model-controlled surfaces -------------

    def test_check_remains_permitted_on_model_controlled_surface(self) -> None:
        """A: --check succeeds and NEVER reaches the value fetcher."""
        rc, stdout, stderr, fetch, probe, emit = self._run_cli(self.MODEL_ENV, "--check")
        self.assertEqual(rc, 0)
        self.assertIn("OK", stdout)
        # The whole point of the amendment: no raw secret bytes enter the process.
        fetch.assert_not_called()
        self._assert_no_value_escaped(stdout, stderr, emit)
        self.assertNotIn("DENIED", stderr)
        del probe

    def test_check_uses_metadata_probe_exactly_once(self) -> None:
        """B: the reachability answer comes from metadata, not from the value."""
        _rc, _stdout, _stderr, fetch, probe, _emit = self._run_cli(self.MODEL_ENV, "--check")
        probe.assert_called_once()
        fetch.assert_not_called()
        # The probe is asked about the secret object, never about the field.
        self.assertEqual(probe.call_args.args[0], "openclaw-igorbot/github")

    def test_probe_ref_needs_no_trust_and_no_value(self) -> None:
        with mock.patch.dict(os.environ, self.MODEL_ENV, clear=True):
            with mock.patch.object(
                resolve,
                "fetch_secret_string",
                return_value=(json.dumps({"token": self.FAKE_VALUE}), None),
            ) as fetch:
                with mock.patch.object(resolve, "probe_secret_metadata", return_value=None):
                    self.assertIsNone(resolve.probe_ref(self.REF, "us-east-1"))
        fetch.assert_not_called()

    def test_probe_never_issues_get_secret_value(self) -> None:
        """The argv actually handed to the provider carries no value operation."""
        seen: list[list[str]] = []

        def fake_runner(cmd: list[str], **_kwargs: Any) -> Any:
            seen.append(cmd)
            return SimpleNamespace(returncode=0, stdout="arn:aws:secretsmanager:x", stderr="")

        with mock.patch.dict(os.environ, self.MODEL_ENV, clear=True):
            self.assertIsNone(resolve.probe_ref(self.REF, "us-east-1", runner=fake_runner))
        self.assertEqual(len(seen), 1)
        self.assertIn("describe-secret", seen[0])
        self.assertNotIn("get-secret-value", seen[0])
        self.assertNotIn("SecretString", seen[0])

    # --- C: trusted raw resolution keeps its existing behavior ---------------

    def test_trusted_operator_raw_resolution_still_works(self) -> None:
        rc, stdout, stderr, fetch, probe, emit = self._run_cli(self.TRUSTED_ENV)
        self.assertEqual(rc, 0)
        fetch.assert_called_once()
        emit.assert_called_once_with(self.FAKE_VALUE)
        # The value path is not routed through metadata first.
        probe.assert_not_called()
        self.assertNotIn("DENIED", stderr)
        self.assertEqual(stdout, "")

    def test_trusted_operator_provider_error_is_unchanged(self) -> None:
        with mock.patch.dict(os.environ, self.TRUSTED_ENV, clear=True):
            with mock.patch.object(
                resolve, "fetch_secret_string", return_value=(None, "AWS_CLI_NOT_FOUND")
            ):
                with mock.patch.object(resolve, "_emit_secret_value") as emit:
                    with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                        rc = resolve.main(
                            ["--ref", self.REF, "--registry", str(self.registry_path)]
                        )
                        stderr = err.getvalue()
        self.assertEqual(rc, 1)
        emit.assert_not_called()
        self.assertIn("FAIL", stderr)
        self.assertNotIn("DENIED", stderr)

    # --- F/G/H: metadata failures map to the EXISTING canonical vocabulary ---

    @staticmethod
    def _runner(returncode: int, stdout: str = "", stderr: str = "") -> Any:
        def run(_cmd: list[str], **_kwargs: Any) -> Any:
            return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

        return run

    def test_metadata_object_not_found(self) -> None:
        """F: describe-secret ResourceNotFoundException -> NOT_FOUND."""
        runner = self._runner(255, stderr="An error occurred (ResourceNotFoundException)")
        self.assertEqual(resolve.probe_ref(self.REF, "us-east-1", runner=runner), "NOT_FOUND")

    def test_metadata_empty_arn_is_not_found(self) -> None:
        self.assertEqual(
            resolve.probe_ref(self.REF, "us-east-1", runner=self._runner(0, stdout="None")),
            "NOT_FOUND",
        )

    def test_aws_cli_unavailable(self) -> None:
        """G: missing binary keeps its own canonical code, not a generic error."""

        def missing(_cmd: list[str], **_kwargs: Any) -> Any:
            raise FileNotFoundError(2, "No such file or directory: 'aws'")

        self.assertEqual(
            resolve.probe_ref(self.REF, "us-east-1", runner=missing), "AWS_CLI_NOT_FOUND"
        )

    def test_provider_timeout(self) -> None:
        def slow(_cmd: list[str], **_kwargs: Any) -> Any:
            raise subprocess.TimeoutExpired(cmd="aws", timeout=6)

        self.assertEqual(resolve.probe_ref(self.REF, "us-east-1", runner=slow), "TIMEOUT")

    def test_provider_auth_failure_maps_to_canonical_code_without_leaking_stderr(self) -> None:
        """H: auth/access-denied has no dedicated code here; it canonicalises."""
        leak = "AccessDeniedException: User arn:aws:iam::1234:user/svc is not authorized"
        runner = self._runner(255, stderr=leak)
        code = resolve.probe_ref(self.REF, "us-east-1", runner=runner)
        self.assertEqual(code, "RESOLUTION_ERROR")
        self.assertIn(code, resolve._KNOWN_ERROR_CODES)
        # Provider stderr is canonicalised away, never returned to the caller.
        self.assertNotIn("arn:aws:iam", code)
        self.assertNotIn("AccessDenied", code)

    # --- I: field membership is an inventory question ------------------------

    def test_field_membership_comes_from_registry_not_provider(self) -> None:
        """The registry declares keys, so an undeclared field fails without AWS."""
        registry = resolve.load_registry(self.registry_path)
        self.assertTrue(resolve.ref_registered(registry, "openclaw-igorbot/github#token"))
        self.assertFalse(resolve.ref_registered(registry, "openclaw-igorbot/github#nope"))

        # End to end: an undeclared field is rejected before any provider call.
        with mock.patch.dict(os.environ, self.MODEL_ENV, clear=True):
            with mock.patch.object(resolve, "fetch_secret_string") as fetch:
                with mock.patch.object(resolve, "probe_secret_metadata") as probe:
                    with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                        rc = resolve.main(
                            [
                                "--ref",
                                "openclaw-igorbot/github#nope",
                                "--check",
                                "--registry",
                                str(self.registry_path),
                            ]
                        )
                        stdout = out.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("FAIL", stdout)
        fetch.assert_not_called()
        probe.assert_not_called()


class PortAwsToInfisicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _load("port_aws_to_infisical")

    def test_dry_run_never_emits_secret_values(self) -> None:
        secret = "sk-live-SUPER-SECRET-VALUE-9f3a"
        lines = self.port.format_dry_run(
            aws_ids=["openclaw-igorbot/github"],
            used_env={"GITHUB_TOKEN": f"openclaw-igorbot/github#{secret}"},
            structured_counts={"github": 1},
            skipped_root_count=0,
            root_count=1,
        )
        blob = "\n".join(lines)
        self.assertNotIn(secret, blob)
        self.assertIn("/ GITHUB_TOKEN", blob)
        self.assertIn("openclaw-igorbot/github", blob)
        self.assertIn("count=1", blob)

    def test_die_message_is_status_only(self) -> None:
        with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
            with self.assertRaises(SystemExit) as raised:
                self.port._die("create failed", status=409)
            self.assertEqual(raised.exception.code, 1)
            text = err.getvalue()
        self.assertIn("create failed", text)
        self.assertIn("status=409", text)
        self.assertNotIn("secretValue", text)
        self.assertNotIn("sk-", text)


if __name__ == "__main__":
    unittest.main()
