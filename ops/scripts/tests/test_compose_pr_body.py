#!/usr/bin/env python3
"""Mechanical PR-body prefill must fill measured facts and leave judgment empty."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "scripts"))

from compose_pr_body import (  # noqa: E402
    SCHEMA,
    UNMEASURED,
    MechanicalFacts,  # noqa: E402
    compose_pr_body,
    write_handoff,
)

TEMPLATE = """## Problem

```
paste the error / failing output here, or delete this block and describe the gap
```

Closes #

## Fix

<!-- What you changed -->

## Risk

- [ ] Low — additive, reversible, no data or contract change
- [ ] Medium — touches shared code, config, or a public interface
- [ ] High — breaking change, migration, IAM/network, or irreversible

## Evidence

```
$ pytest -q
$ ruff check . && pyright
```

## Gates

- [ ] Regression test added that fails without this fix
- [ ] No secrets, tokens, or customer data in code, tests, fixtures, or logs

## Files touched

<!-- FILES-TOUCHED:START -->
_pending — the bot fills this in on push_
<!-- FILES-TOUCHED:END -->
"""


class ComposePrBodyTests(unittest.TestCase):
    def test_mechanical_fill_leaves_unverified_boxes_unchecked(self) -> None:
        facts = MechanicalFacts(
            commits=["fix: fill PR body from receipts"],
            changed_files=["M\tops/scripts/open_pr_after_gate.sh"],
            issue_closes=[172],
            gate_receipt={
                "schema": "l9.pr_gate_receipt.v2",
                "head": "abc",
                "passed_at": "2026-08-21T00:00:00Z",
            },
            l4_receipt={"phase": "release_authorized", "head_sha": "abc"},
            template_path=".github/PULL_REQUEST_TEMPLATE.md",
        )
        result = compose_pr_body(facts, TEMPLATE)
        self.assertIn("fix: fill PR body from receipts", result.body)
        self.assertIn("M\tops/scripts/open_pr_after_gate.sh", result.body)
        self.assertIn("Closes #172", result.body)
        self.assertIn("gate-receipt.json present", result.body)
        self.assertIn("- [x] `make pr` local gate receipt present", result.body)
        self.assertIn("- [x] L4 release receipt present", result.body)
        self.assertIn(f"- [ ] CI green — {UNMEASURED}", result.body)
        self.assertIn(
            f"- [ ] Low — additive, reversible, no data or contract change — {UNMEASURED}",
            result.body,
        )
        self.assertIn(
            f"- [ ] Regression test added that fails without this fix — {UNMEASURED}",
            result.body,
        )
        self.assertNotIn("- [x] Low", result.body)
        self.assertNotIn("- [x] Regression test", result.body)
        self.assertIn("Risk", result.needs_completion)
        self.assertIn("commits", result.mechanical_filled)

    def test_root_governance_template_fills_summary_not_unverified_boxes(self) -> None:
        root = (REPO / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        facts = MechanicalFacts(
            commits=["fix: compose PR body"],
            changed_files=["M\tops/scripts/compose_pr_body.py"],
            issue_closes=[172],
            gate_receipt={"schema": "l9.pr_gate_receipt.v2", "head": "abc", "passed_at": "t"},
            l4_receipt={"phase": "release_authorized", "head_sha": "abc"},
        )
        result = compose_pr_body(facts, root)
        self.assertIn("fix: compose PR body", result.body)
        self.assertIn("M\tops/scripts/compose_pr_body.py", result.body)
        self.assertIn("Closes #172", result.body)
        self.assertIn("- [x] **L4 local autonomy**", result.body)
        self.assertIn("- [x] **Post-exec kernels**", result.body)
        self.assertIn("**All CI gates green**", result.body)
        self.assertIn(UNMEASURED, result.body)
        self.assertNotIn("- [x] **All CI gates green**", result.body)
        self.assertNotIn("- [x] Bug fix", result.body)
        self.assertIn("Type of Change", result.needs_completion)

    def test_missing_receipts_do_not_self_certify(self) -> None:
        facts = MechanicalFacts(commits=["wip"], changed_files=["A\tfoo.py"])
        result = compose_pr_body(facts, TEMPLATE)
        self.assertIn(f"- [ ] `make pr` local gate receipt — {UNMEASURED}", result.body)
        self.assertIn(f"- [ ] L4 release receipt — {UNMEASURED}", result.body)
        self.assertNotIn("- [x] `make pr`", result.body)
        self.assertNotIn("- [x] L4 release", result.body)

    def test_no_template_still_lists_commits_and_files(self) -> None:
        facts = MechanicalFacts(
            commits=["subject one"],
            changed_files=["A\tnew.py"],
            campaign_body="Campaign note",
        )
        result = compose_pr_body(facts, None)
        self.assertIn("Campaign note", result.body)
        self.assertIn("subject one", result.body)
        self.assertIn("A\tnew.py", result.body)

    def test_handoff_lists_judgment_and_mechanical(self) -> None:
        facts = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tx"],
            template_path="PULL_REQUEST_TEMPLATE.md",
        )
        result = compose_pr_body(facts, TEMPLATE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr-body-completion.json"
            write_handoff(path, result=result, facts=facts, pr_number=12)
            doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["pr_number"], 12)
        self.assertEqual(doc["commit_count"], 1)
        self.assertIn("Risk", doc["needs_completion"])


if __name__ == "__main__":
    unittest.main()
