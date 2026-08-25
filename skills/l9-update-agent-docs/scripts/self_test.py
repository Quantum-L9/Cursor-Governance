#!/usr/bin/env python3
"""Prove l9-update-agent-docs cites both kernels and does not wrap them."""

from __future__ import annotations

import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SKILL = PACK / "SKILL.md"
# Split so a pack-wide grep for the wrap tokens stays empty (SP-02).
FORBIDDEN = (
    "Ker" + "nel bind",
    "artifact" + "_type:",
    "ai_coding" + "_alignment_kernel",
    "ai_coding" + "_execution_kernel",
)


def main() -> int:
    text = SKILL.read_text(encoding="utf-8")
    errors: list[str] = []
    for token in FORBIDDEN:
        if token in text:
            errors.append(f"forbidden kernel wrap token: {token}")
    if "kernels/Recursive Alignment.md" not in text:
        errors.append("missing path citation to kernels/Recursive Alignment.md")
    if "kernels/Validate & Repair.md" not in text:
        errors.append("missing path citation to kernels/Validate & Repair.md")
    for token in ("Passed", "Failed", "Skipped", "Unknown", "NotApplicable"):
        if token not in text:
            errors.append(f"missing honest-validation status: {token}")
    if "authority pointer" not in text.lower() and "load pointer" not in text.lower():
        errors.append("CLAUDE.md pointer role not stated")
    # Prohibition mentions are allowed; a Write-table destination is not.
    write_section = ""
    if "### Step 3 — Write" in text:
        write_section = text.split("### Step 3 — Write", 1)[1]
        if "### Step 4" in write_section:
            write_section = write_section.split("### Step 4", 1)[0]
    for invented in ("ARCHITECTURE.md", "INVARIANTS.md"):
        for line in write_section.splitlines():
            if line.startswith("|") and f"`{invented}`" in line:
                errors.append(f"invented write target: {invented}")
    if errors:
        print("FAIL")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
