#!/usr/bin/env python3
"""Validate l9-git-work-preserve pack structure."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "SKILL.md",
    "agents/meta.yaml",
    "references/diagnose-first-binding.md",
    "references/audit-workflow.md",
    "references/value-diagnosis.md",
    "references/extract-workflow.md",
    "references/prune-policy.md",
    "references/stash-deep-analysis.md",
    "references/output-receipt.schema.yaml",
    "scripts/inventory_git_work.py",
    "scripts/diagnose_ref_value.py",
    "scripts/git_fetch.py",
    "scripts/ff_pipeline.py",
    "scripts/pack_self_test.py",
    "scripts/validate_pack_structure.py",
]


def main() -> int:
    missing = [rel for rel in REQUIRED if not (ROOT / rel).is_file()]
    if missing:
        for m in missing:
            print(f"FAIL: missing {m}", file=sys.stderr)
        return 1
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("L9_GIT_PRUNE_AUTHORIZED", "L9_GIT_STASH_DROP_AUTHORIZED", "diagnose-first"):
        if needle not in text and needle.replace("-", " ") not in text.lower():
            if needle.startswith("L9_"):
                if needle not in text:
                    print(f"FAIL: SKILL.md missing {needle}", file=sys.stderr)
                    return 1
    if "Diagnose-First" not in text and "diagnose-first" not in text.lower():
        print("FAIL: SKILL.md missing diagnose-first binding", file=sys.stderr)
        return 1
    print("PASS: validate_pack_structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
