#!/usr/bin/env python3
"""Unit tests for ui-operator console + jit drafter (no live browser)."""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path
from typing import Any

UI = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    path = UI / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


console = _load("console")
jit = _load("jit_drafter")


class CartridgeValidationTests(unittest.TestCase):
    def test_github_cartridge_shape_and_allowlist(self) -> None:
        path = UI / "cartridges" / "github-packages-actions-access.yaml"
        data = console.load_yaml(path)
        self.assertEqual(console.validate_cartridge_shape(data), [])
        self.assertEqual(console.check_allowlist(data), [])
        self.assertIn("ensure_actions_read_access", data["mutation_allowlist"])
        self.assertIn("change_visibility", data["forbidden"])

    def test_allowlist_blocks_unknown_mutation(self) -> None:
        cartridge = {
            "schema_version": "1.0.0",
            "id": "x",
            "version": "1",
            "site": "t",
            "goal": "g",
            "auth": {"refs": ["openclaw-igorbot/github#token"]},
            "mutation_allowlist": ["ok_mut"],
            "forbidden": ["bad"],
            "journey": [{"step": "s", "mutation": "not_allowed"}],
        }
        errs = console.check_allowlist(cartridge)
        self.assertTrue(any("not on allowlist" in e for e in errs))


class ConsoleModeTests(unittest.TestCase):
    def test_validate_github_cartridge(self) -> None:
        path = UI / "cartridges" / "github-packages-actions-access.yaml"
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "r.yaml"
            with mock.patch.object(console, "resolve_check", return_value=(True, "OK ref=x")):
                rc = console.run_console(
                    cartridge_path=path,
                    mode="validate",
                    approve=False,
                    actor="test",
                    receipt_path=receipt,
                )
            self.assertEqual(rc, 0)
            text = receipt.read_text(encoding="utf-8")
            self.assertIn("verdict: VALIDATED", text)
            self.assertIn("openclaw-igorbot/github#token", text)
            self.assertNotIn("ghp_", text)

    def test_run_blocks_without_approve(self) -> None:
        path = UI / "cartridges" / "github-packages-actions-access.yaml"
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "r.yaml"
            with mock.patch.object(console, "resolve_check", return_value=(True, "OK ref=x")):
                rc = console.run_console(
                    cartridge_path=path,
                    mode="run",
                    approve=False,
                    actor="test",
                    receipt_path=receipt,
                )
            self.assertEqual(rc, 1)
            self.assertIn("missing_human_approve", receipt.read_text(encoding="utf-8"))

    def test_dry_run(self) -> None:
        path = UI / "cartridges" / "github-packages-actions-access.yaml"
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "r.yaml"
            with mock.patch.object(console, "resolve_check", return_value=(True, "OK ref=x")):
                rc = console.run_console(
                    cartridge_path=path,
                    mode="dry_run",
                    approve=False,
                    actor="test",
                    receipt_path=receipt,
                )
            self.assertEqual(rc, 0)
            self.assertIn("verdict: DRY_RUN", receipt.read_text(encoding="utf-8"))


class JitDrafterTests(unittest.TestCase):
    def test_draft_writes_approve_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "draft.yaml"
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                with mock.patch("sys.stderr", new_callable=io.StringIO):
                    rc = jit.main(
                        [
                            "--site",
                            "vercel",
                            "--goal",
                            "tune project env",
                            "--url",
                            "https://vercel.com/example",
                            "--out",
                            str(out),
                        ]
                    )
            self.assertEqual(rc, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("human_approve_required: true", text)
            self.assertIn("0.1.0-draft", text)


if __name__ == "__main__":
    unittest.main()
