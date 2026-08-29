#!/usr/bin/env python3
"""Validate l9-repo-sync pack structure (this pack only)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "SKILL.md",
    "agents/meta.yaml",
    "references/clone-map.md",
    "references/diagnose-first.md",
    "references/execute.md",
    "references/forbidden.md",
    "scripts/ff.sh",
    "scripts/self_test.py",
    "scripts/validate_pack_structure.py",
]

GIT_PRIMITIVES = (
    "git switch",
    "git checkout",
    "git merge",
    "git pull",
    "git clone",
    "git reset",
)


def _heading_is_forbidden_or_incident(heading: str) -> bool:
    low = heading.lower()
    return "forbidden" in low or "incident" in low


def primitives_only_under_allowed_headings(text: str) -> list[str]:
    """Return primitive hits that are not under Forbidden/incident headings."""
    errors: list[str] = []
    current = ""
    for line in text.splitlines():
        if line.startswith("#"):
            current = line.lstrip("#").strip()
            continue
        for prim in GIT_PRIMITIVES:
            if prim in line and not _heading_is_forbidden_or_incident(current):
                errors.append(f"{prim!r} under heading {current!r}: {line.strip()}")
    return errors


def main() -> int:
    missing = [rel for rel in REQUIRED if not (ROOT / rel).is_file()]
    if missing:
        for item in missing:
            print(f"FAIL: missing {item}", file=sys.stderr)
        return 1

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("GOVERNANCE_SYNC_PUSH=0", "GOVERNANCE_SYNC_HARD_RESET=0"):
        if needle not in skill:
            print(f"FAIL: SKILL.md missing {needle}", file=sys.stderr)
            return 1
    if "name: l9-repo-sync" not in skill:
        print("FAIL: SKILL.md name must be l9-repo-sync", file=sys.stderr)
        return 1
    if not re.search(r"^disable-model-invocation:\s*true", skill, re.M):
        print("FAIL: disable-model-invocation must be true (explicit /ff only)", file=sys.stderr)
        return 1
    if "Never delete unique files" not in skill:
        print("FAIL: SKILL.md must forbid deleting unique files", file=sys.stderr)
        return 1

    execute = (ROOT / "references/execute.md").read_text(encoding="utf-8")
    for needle in (
        "GOVERNANCE_SYNC_PUSH=0",
        "GOVERNANCE_SYNC_HARD_RESET=0",
        "CURSOR_GOVERNANCE_DIR=",
        "reset --keep",
        "scripts/ff.sh",
        "all",
        "l9-ff-hold",
    ):
        if needle not in execute:
            print(f"FAIL: execute.md missing {needle}", file=sys.stderr)
            return 1
    if "stash -u" in execute and "does **not** call" not in execute:
        print("FAIL: execute.md must not teach stash -u as the mutate path", file=sys.stderr)
        return 1

    forbidden = (ROOT / "references/forbidden.md").read_text(encoding="utf-8")
    for prim in GIT_PRIMITIVES:
        if prim not in forbidden:
            print(f"FAIL: forbidden.md must name {prim}", file=sys.stderr)
            return 1
    if "Deleting dirty" not in forbidden:
        print("FAIL: forbidden.md must name deleting dirt to unblock /ff", file=sys.stderr)
        return 1

    ff_sh = (ROOT / "scripts/ff.sh").read_text(encoding="utf-8")
    live = "\n".join(line for line in ff_sh.splitlines() if not line.lstrip().startswith("#"))
    if "HEAD...origin" in live:
        print("FAIL: ff.sh must not use triple-dot colliding (no merge-base)", file=sys.stderr)
        return 1
    if "diff --name-only HEAD" not in ff_sh:
        print("FAIL: ff.sh must park all dirty tracked vs HEAD", file=sys.stderr)
        return 1

    for rel in ("SKILL.md", "references/execute.md", "references/diagnose-first.md"):
        hits = primitives_only_under_allowed_headings((ROOT / rel).read_text(encoding="utf-8"))
        if rel.endswith("diagnose-first.md"):
            hits = [
                h
                for h in hits
                if "reset --keep" not in h
                and "merge --ff-only" not in h
                and "do not switch" not in h.lower()
                and "git switch" not in h
            ]
        if rel.endswith("execute.md") or rel.endswith("SKILL.md"):
            hits = [
                h
                for h in hits
                if "reset --keep" not in h
                and "merge --ff-only" not in h
                and "git switch" not in h
            ]
        if hits:
            for hit in hits:
                print(f"FAIL: {rel} {hit}", file=sys.stderr)
            return 1

    print("PASS: validate_pack_structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
