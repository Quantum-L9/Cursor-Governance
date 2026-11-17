"""``sync_org_pr_template``: the pinned org PR template is a checked projection.

The pin exists so ``make pr`` can compose a PR body in sessions that cannot reach
the private ``<owner>/.github``. It must carry the exact commit and digest it was
read at, and ``--check`` must report drift rather than paper over it.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import org_dotgithub  # noqa: E402
import sync_org_pr_template as sync  # noqa: E402

SHA = "a" * 40


def _org(text: str, sha: str = SHA) -> org_dotgithub.OrgFile:
    return org_dotgithub.OrgFile(text=text, sha=sha, transport="rest")


class SyncOrgPrTemplateTests(unittest.TestCase):
    def test_write_pins_bytes_commit_and_digest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(sync.org_dotgithub, "read_org_file", return_value=_org("T\n")):
                receipt = sync.write("Quantum-L9", root)
            target = root / "Quantum-L9"
            self.assertEqual((target / sync.TEMPLATE_NAME).read_text(encoding="utf-8"), "T\n")
            stored = json.loads((target / sync.RECEIPT_NAME).read_text(encoding="utf-8"))
        self.assertEqual(stored, receipt)
        self.assertEqual(receipt["revision"], SHA)
        self.assertEqual(receipt["sha256"], sync.digest("T\n"))
        self.assertEqual(receipt["authority_repository"], "Quantum-L9/.github")

    def test_check_passes_when_the_pin_matches_the_live_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(sync.org_dotgithub, "read_org_file", return_value=_org("T\n")):
                sync.write("Quantum-L9", root)
                self.assertIsNone(sync.check("Quantum-L9", root))

    def test_check_reports_a_stale_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(sync.org_dotgithub, "read_org_file", return_value=_org("T\n")):
                sync.write("Quantum-L9", root)
            moved = _org("T2\n", "b" * 40)
            with mock.patch.object(sync.org_dotgithub, "read_org_file", return_value=moved):
                problem = sync.check("Quantum-L9", root)
        self.assertIsNotNone(problem)
        self.assertIn("stale", problem or "")

    def test_check_reports_a_tampered_pin_without_reading_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(sync.org_dotgithub, "read_org_file", return_value=_org("T\n")):
                sync.write("Quantum-L9", root)
            (root / "Quantum-L9" / sync.TEMPLATE_NAME).write_text("edited\n", encoding="utf-8")
            with mock.patch.object(sync.org_dotgithub, "read_org_file") as live:
                problem = sync.check("Quantum-L9", root)
            live.assert_not_called()
        self.assertIn("does not match its receipt", problem or "")

    def test_main_exits_2_when_the_live_template_is_unreachable(self) -> None:
        down = org_dotgithub.OrgFileError("HTTP 403")
        with mock.patch.object(sync.org_dotgithub, "read_org_file", side_effect=down):
            self.assertEqual(sync.main([]), 2)


if __name__ == "__main__":
    unittest.main()
