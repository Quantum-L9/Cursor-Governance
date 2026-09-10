#!/usr/bin/env python3
"""aws_cli_preflight never prints secret values; fail-loud on missing CLI."""

from __future__ import annotations

import importlib.util
import io
import json
import unittest
import unittest.mock as mock
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SECRETS = Path(__file__).resolve().parent


def _load() -> Any:
    path = SECRETS / "aws_cli_preflight.py"
    spec = importlib.util.spec_from_file_location("aws_cli_preflight", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


preflight = _load()


class AwsCliPreflightTests(unittest.TestCase):
    def test_missing_binary_is_not_found(self) -> None:
        with mock.patch.object(preflight.shutil, "which", return_value=None):
            result = preflight.probe()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], preflight.AWS_CLI_NOT_FOUND)
        self.assertIn("secrets plane cannot start", result["summary"])

    def test_fail_helper_reuses_repair(self) -> None:
        first = preflight._fail(preflight.TIMEOUT)
        second = preflight._fail(preflight.AWS_NOT_AUTHORIZED)
        self.assertEqual(first["code"], preflight.TIMEOUT)
        self.assertIn(preflight.REPAIR, first["summary"])
        self.assertIn(preflight.REPAIR, second["summary"])

    def test_sts_failure_is_not_authorized(self) -> None:
        def runner(_cmd: list[str], **_kwargs: Any) -> Any:
            return SimpleNamespace(returncode=255, stdout="", stderr="AccessDenied")

        with mock.patch.object(preflight.shutil, "which", return_value="/usr/bin/aws"):
            result = preflight.probe(runner=runner)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], preflight.AWS_NOT_AUTHORIZED)
        self.assertNotIn("AccessDenied", result["summary"])

    def test_sts_ok_does_not_echo_account(self) -> None:
        payload = {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/ops"}

        def runner(_cmd: list[str], **_kwargs: Any) -> Any:
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")

        with mock.patch.object(preflight.shutil, "which", return_value="/usr/bin/aws"):
            result = preflight.probe(runner=runner)
        self.assertTrue(result["ok"])
        blob = json.dumps(result)
        self.assertNotIn("123456789012", blob)
        self.assertNotIn("arn:aws:iam", blob)

    def test_main_fail_writes_banner_to_stderr(self) -> None:
        with mock.patch.object(
            preflight,
            "probe",
            return_value={"ok": False, "code": "AWS_CLI_NOT_FOUND", "summary": "down"},
        ):
            with mock.patch("sys.stderr", new_callable=io.StringIO) as err:
                rc = preflight.main([])
        self.assertEqual(rc, 1)
        self.assertIn("FAILED", err.getvalue())
        self.assertIn("secrets plane cannot start", err.getvalue())


if __name__ == "__main__":
    unittest.main()
