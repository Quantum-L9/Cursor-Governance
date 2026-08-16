#!/usr/bin/env python3
"""WIP corpus: date buckets, loose filing, hash prune, Legal Defense skip."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from wip_corpus import (  # noqa: E402
    INVENTORY_REL,
    build_inventory,
    file_loose,
    is_date_bucket,
    is_secret_glob,
    main,
    prune,
    sha256_file,
    should_skip,
    today_bucket,
    walk_wip_files,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _init_repo(tmp: Path) -> Path:
    root = tmp / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "wip-corpus@test.local")
    _git(root, "config", "user.name", "WIP Corpus Test")
    landed = root / "docs" / "landed.md"
    landed.parent.mkdir()
    landed.write_text("same-bytes\n", encoding="utf-8")
    unique = root / "docs" / "other.md"
    unique.write_text("other-bytes\n", encoding="utf-8")
    _git(root, "add", "docs/landed.md", "docs/other.md")
    _git(root, "commit", "-m", "seed")
    return root


class WipCorpusTests(unittest.TestCase):
    def test_date_bucket_naming_m_d_yy(self) -> None:
        stamp = datetime(2026, 8, 16, tzinfo=UTC)
        self.assertEqual(today_bucket(stamp), "8-16-26")
        self.assertTrue(is_date_bucket("8-16-26"))
        self.assertTrue(is_date_bucket("8-14-26"))
        self.assertFalse(is_date_bucket("2026-08-16"))
        self.assertFalse(is_date_bucket("CG"))

    def test_loose_file_filing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            wip = root / "WIP"
            wip.mkdir(parents=True)
            (wip / "note.md").write_text("loose\n", encoding="utf-8")
            (wip / "INVENTORY.yaml").write_text("schema: keep\n", encoding="utf-8")
            moved = file_loose(root, now=datetime(2026, 8, 16))
            self.assertEqual(moved, ["WIP/8-16-26/note.md"])
            self.assertFalse((wip / "note.md").exists())
            self.assertTrue((wip / "8-16-26" / "note.md").is_file())
            self.assertTrue((wip / "INVENTORY.yaml").is_file())

    def test_same_hash_non_wip_pruned_plus_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_repo(Path(tmp))
            candidate = root / "WIP" / "8-16-26" / "copy.md"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("same-bytes\n", encoding="utf-8")
            _git(root, "add", "WIP/8-16-26/copy.md")
            _git(root, "commit", "-m", "wip copy")
            receipt = prune(root, now=datetime(2026, 8, 16, 12, 0, tzinfo=UTC))
            self.assertIsNotNone(receipt)
            assert receipt is not None
            self.assertFalse(candidate.exists())
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "l9.wip.prune_receipt.v1")
            self.assertEqual(payload["removed"][0]["wip_path"], "WIP/8-16-26/copy.md")
            self.assertEqual(payload["removed"][0]["landed_path"], "docs/landed.md")
            self.assertEqual(payload["removed"][0]["action"], "removed")
            landed_hash = sha256_file(root / "docs" / "landed.md")
            self.assertEqual(payload["removed"][0]["sha256"], landed_hash)

    def test_empty_file_not_pruned_against_empty_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_repo(Path(tmp))
            (root / ".governance-build-lock").write_text("", encoding="utf-8")
            _git(root, "add", ".governance-build-lock")
            _git(root, "commit", "-m", "empty lock")
            empty = root / "WIP" / "8-16-26" / "PE-Template.md"
            empty.parent.mkdir(parents=True)
            empty.write_text("", encoding="utf-8")
            receipt = prune(root)
            self.assertIsNone(receipt)
            self.assertTrue(empty.is_file())

    def test_unique_bytes_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_repo(Path(tmp))
            unique = root / "WIP" / "8-16-26" / "only-here.md"
            unique.parent.mkdir(parents=True)
            unique.write_text("unique-wip-bytes\n", encoding="utf-8")
            receipt = prune(root)
            self.assertIsNone(receipt)
            self.assertTrue(unique.is_file())
            data = build_inventory(root)
            paths = [row["path"] for row in data["entries"]]
            self.assertIn("WIP/8-16-26/only-here.md", paths)
            self.assertEqual(data["entries"][0]["status"], "active")

    def test_legal_defense_never_walked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "ws"
            secret = root / "WIP" / "Legal Defense" / "case.md"
            secret.parent.mkdir(parents=True)
            secret.write_text("private\n", encoding="utf-8")
            visible = root / "WIP" / "8-16-26" / "ok.md"
            visible.parent.mkdir(parents=True)
            visible.write_text("ok\n", encoding="utf-8")
            walked = [p.as_posix() for p in walk_wip_files(root)]
            self.assertTrue(any(path.endswith("WIP/8-16-26/ok.md") for path in walked))
            self.assertFalse(any("Legal Defense" in path for path in walked))
            data = build_inventory(root)
            self.assertEqual([row["path"] for row in data["entries"]], ["WIP/8-16-26/ok.md"])

    def test_secret_globs_never_staged(self) -> None:
        self.assertTrue(is_secret_glob("WIP/8-16-26/google_oauth_client.json"))
        self.assertTrue(is_secret_glob("WIP/foo_credentials.json"))
        self.assertTrue(is_secret_glob("WIP/x_client_secret.json"))
        self.assertTrue(should_skip("WIP/Legal Defense/x.md"))
        with tempfile.TemporaryDirectory() as tmp:
            root = _init_repo(Path(tmp))
            secret = root / "WIP" / "8-16-26" / "google_oauth_client.json"
            secret.parent.mkdir(parents=True)
            secret.write_text('{"client_secret":"x"}\n', encoding="utf-8")
            rc = main(["hygiene", "--root", str(root), "--now", "2026-08-16"])
            self.assertEqual(rc, 0)
            self.assertTrue(secret.is_file())
            inventory = (root / INVENTORY_REL).read_text(encoding="utf-8")
            self.assertNotIn("oauth", inventory)
            listed = subprocess.run(
                ["git", "-C", str(root), "ls-files", "--", "WIP"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn("oauth", listed)


if __name__ == "__main__":
    unittest.main()
