#!/usr/bin/env python3
"""Unit tests for ops/secrets sync + resolve (mocked AWS; no live secret values)."""

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
        with mock.patch.object(
            resolve,
            "fetch_secret_string",
            return_value=(json.dumps({"token": secret_value}), None),
        ):
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
        self.assertRegex(stdout, r"OK handle=ref:[0-9a-f]{12}")
        self.assertNotIn("openclaw-igorbot/github", stdout)
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
            self.assertIn("UNREGISTERED", out.getvalue())

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
            self.assertIn("NOT_PROVISIONED", out.getvalue())

    def test_split_id(self) -> None:
        self.assertEqual(
            resolve.split_id("openclaw-igorbot/github#token"),
            ("openclaw-igorbot/github", "token"),
        )


if __name__ == "__main__":
    unittest.main()
