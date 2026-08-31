#!/usr/bin/env python3
"""Autonomous PR-body compile fills measured facts; no judgment leftover."""

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
    MechanicalFacts,
    compose_pr_body,
    write_handoff,
)

TEMPLATE = """<!-- L9_PROTECTED_ROOT_PR -->

## Protected-root

### Paths

- ` `

### Edit mode (pick one per path)

- [ ] **Append-only** — existing lines kept
- [ ] **Justified rewrite** — commit contains ALLOW-ROOT-DELETION

### Why a root file

<!-- What cannot be done in a non-root path. Composer fills. -->

### Proof of necessity (rewrites only)

<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->

## Problem

```
paste the error / failing output here, or delete this block and describe the gap
```

Closes #

## Type of Change

- [ ] Bug fix
- [ ] Feature / enhancement
- [ ] Refactor (no behavior change)
- [ ] Documentation
- [ ] CI / governance change
- [ ] Breaking change (see rollback below)

## Fix

<!-- What you changed -->

## Risk

- [ ] Low — additive, reversible, no data or contract change
- [ ] Medium — touches shared code, config, or a public interface
- [ ] High — breaking change, migration, IAM/network, or irreversible

Blast radius:
Rollback:

## Evidence

```
$ pytest -q
$ ruff check . && pyright
```

## Gates

- [ ] Regression test added that fails without this fix
- [ ] No secrets, tokens, or customer data in code, tests, fixtures, or logs

## Reviewer focus

<!-- Where to look hardest. Trade-offs accepted. Deferred follow-ups, with issue links. -->

## Changes by intent

**Added**
- `path/to/new_file.py` — why this file needs to exist

**Modified**
- `path/to/existing.py` — what changed in it and why

**Deleted**
- `path/to/dead.py` — why it is safe to remove

## Files touched

<!-- FILES-TOUCHED:START -->
_pending — the bot fills this in on push_
<!-- FILES-TOUCHED:END -->
"""


class ComposePrBodyTests(unittest.TestCase):
    def test_autonomous_fill_checks_risk_and_type(self) -> None:
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
            template_path=".github/pull_request_template.md",
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
            "- [x] Medium — touches shared code, config, or a public interface", result.body
        )
        self.assertIn("- [x] CI / governance change", result.body)
        self.assertIn("Rollback: revert this PR", result.body)
        self.assertIn(
            "`ops/scripts/open_pr_after_gate.sh` — fix: fill PR body from receipts", result.body
        )
        self.assertIn("- N/A — no additive_only root files", result.body)
        self.assertEqual(result.needs_completion, [])
        self.assertIn("commits", result.mechanical_filled)

    def test_one_template_fills_summary_and_protected_top(self) -> None:
        root = (REPO / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        facts = MechanicalFacts(
            commits=["docs: compose PR body"],
            changed_files=["M\tAGENTS.md"],
            issue_closes=[172],
            gate_receipt={"schema": "l9.pr_gate_receipt.v2", "head": "abc", "passed_at": "t"},
            l4_receipt={"phase": "release_authorized", "head_sha": "abc"},
            additive_only_paths=["AGENTS.md"],
        )
        result = compose_pr_body(facts, root)
        self.assertIn("<!-- L9_PROTECTED_ROOT_PR -->", result.body)
        self.assertIn("- `AGENTS.md`", result.body)
        self.assertIn("- [x] **Append-only**", result.body)
        self.assertIn("docs: compose PR body", result.body)
        self.assertIn("Closes #172", result.body)
        self.assertIn("append-only — none.", result.body)
        self.assertEqual(result.needs_completion, [])
        self.assertIn("protected-root", result.mechanical_filled)

    def test_protected_rewrite_checks_justified(self) -> None:
        facts = MechanicalFacts(
            commits=["fix: rewrite agents fragment"],
            changed_files=["M\tAGENTS.md"],
            additive_only_paths=["AGENTS.md"],
            deletion_markers={"AGENTS.md": "fold stale pointer"},
        )
        result = compose_pr_body(facts, TEMPLATE)
        self.assertIn("- [x] **Justified rewrite**", result.body)
        self.assertIn("AGENTS.md: fold stale pointer", result.body)
        self.assertIn("- [x] Breaking change", result.body)

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

    def test_handoff_lists_empty_needs_completion(self) -> None:
        facts = MechanicalFacts(
            commits=["a"],
            changed_files=["M\tx"],
            template_path=".github/pull_request_template.md",
        )
        result = compose_pr_body(facts, TEMPLATE)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pr-body-completion.json"
            write_handoff(path, result=result, facts=facts, pr_number=12)
            doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["schema"], SCHEMA)
        self.assertEqual(doc["pr_number"], 12)
        self.assertEqual(doc["commit_count"], 1)
        self.assertEqual(doc["needs_completion"], [])


if __name__ == "__main__":
    unittest.main()
