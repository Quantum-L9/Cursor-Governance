#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keep in parity with SKILL.md ## Validation fenced block.
INVOKED = [
    "validate_pack_structure.py",
    "validate_exemplary_skill.py",
    "route_plan.py",
    "validate_plan_document.py",
    "self_test.py",
]


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def skill_validation_scripts() -> list[str]:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    block = re.search(r"## Validation\s+.*?```bash\n(.*?)```", text, re.S)
    if not block:
        return []
    names = re.findall(r"scripts/([a-zA-Z0-9_./-]+\.py)", block.group(1))
    return names


def main() -> int:
    errors: list[str] = []
    listed = skill_validation_scripts()
    if not listed:
        errors.append("SKILL.md ## Validation bash block missing or has no scripts")
    for name in INVOKED:
        if name != "self_test.py" and name not in listed:
            errors.append(f"SKILL.md Validation missing invoked script: {name}")
    for name in listed:
        if name not in INVOKED:
            errors.append(f"SKILL.md Validation lists uninvoked script: {name}")

    checks = [
        [sys.executable, "scripts/validate_pack_structure.py", "."],
        [sys.executable, "scripts/validate_exemplary_skill.py", "."],
        [sys.executable, "scripts/route_plan.py", "--self-test"],
        [sys.executable, "scripts/validate_plan_document.py", "fixtures/plan_pass.json"],
    ]
    for cmd in checks:
        proc = run(cmd)
        if proc.returncode != 0:
            errors.append(
                f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}"
            )

    # Fail fixtures must fail
    fail_cases = [
        ("fixtures/plan_fail_format.json", "G_SCHEMA"),
        ("fixtures/plan_fail_shallow.json", "G_"),
        ("fixtures/plan_fail_ungrounded.json", "G_TODO_GROUND"),
        ("fixtures/plan_fail_quality.json", "G_"),
    ]
    for rel, needle in fail_cases:
        proc = run([sys.executable, "scripts/validate_plan_document.py", rel])
        if proc.returncode == 0:
            errors.append(f"expected FAIL for {rel}")
        elif needle not in proc.stdout and needle not in proc.stderr:
            errors.append(
                f"expected {needle} in failure output for {rel}\n{proc.stdout}\n{proc.stderr}"
            )

    # Helpers smoke
    for cmd in (
        [sys.executable, "scripts/render_plan_markdown.py", "fixtures/plan_pass.json"],
        [sys.executable, "scripts/emit_gmp_phase0.py", "fixtures/plan_pass.json"],
    ):
        proc = run(cmd)
        if proc.returncode != 0:
            errors.append(f"helper failed: {' '.join(cmd)}\n{proc.stderr}")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
