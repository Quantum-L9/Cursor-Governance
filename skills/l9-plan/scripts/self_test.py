#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from sync_cursor_plan_template import _under_repo  # noqa: E402

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

    # Helpers smoke (legacy + default PE/autonomy projector)
    for cmd in (
        [sys.executable, "scripts/render_plan_markdown.py", "fixtures/plan_pass.json"],
        [sys.executable, "scripts/render_plan_pe_autonomy.py", "fixtures/plan_pass.json"],
        [sys.executable, "scripts/emit_gmp_phase0.py", "fixtures/plan_pass.json"],
    ):
        proc = run(cmd)
        if proc.returncode != 0:
            errors.append(f"helper failed: {' '.join(cmd)}\n{proc.stderr}")

    pe = run([sys.executable, "scripts/render_plan_pe_autonomy.py", "fixtures/plan_pass.json"])
    if pe.returncode == 0:
        out = pe.stdout
        for needle in (
            "environment/program-execution",
            "@autonomy",
            "isProject: false",
            "Execute via @environment/program-execution",
        ):
            if needle not in out:
                errors.append(f"render_plan_pe_autonomy.py missing required marker: {needle}")
    else:
        errors.append(f"PE autonomy render failed\n{pe.stderr}")

    build = run(
        [
            sys.executable,
            "scripts/render_plan_pe_autonomy.py",
            "fixtures/plan_pass.json",
            "--execute-via=cursor-build",
        ]
    )
    if build.returncode == 0:
        out = build.stdout
        if "Execute via Cursor Build" not in out:
            errors.append("cursor-build render missing Execute via Cursor Build")
        if "kind: simple" not in out or "execute_via: cursor-build" not in out:
            errors.append("cursor-build render missing kind/execute_via frontmatter")
        if "make -C" in out and "campaign INTENT" in out:
            errors.append("cursor-build render retained make campaign pipeline")
        if "## Execute via @environment/program-execution" in out:
            errors.append("cursor-build render retained PE execute heading")
        if "run through **[@environment/program-execution]" in out:
            errors.append("cursor-build render retained PE Execute blockquote")
        if "pipeline: environment/program-execution" in out:
            errors.append("cursor-build render retained PE machine-stub pipeline")
        if "project→Lock→claim→render→autonomy lanes" in out:
            errors.append("cursor-build render retained PE convergence next-action")
    else:
        errors.append(f"cursor-build render failed\n{build.stderr}")

    # Local Cursor mirror: optional, but fail-closed when present and drifted.
    sync = run([sys.executable, "scripts/sync_cursor_plan_template.py", ".", "--check"])
    if sync.returncode not in {0, 1}:
        errors.append(
            f"sync_cursor_plan_template.py --check errored ({sync.returncode}): "
            f"{sync.stdout}\n{sync.stderr}"
        )
    elif sync.returncode == 1:
        errors.append(
            "Cursor _TEMPLATE.plan.md drifted from SSOT — run "
            "python3 scripts/sync_cursor_plan_template.py .\n"
            f"{sync.stderr}"
        )

    # Governed consumer layout: .cursor/plans → external home plans dir.
    with tempfile.TemporaryDirectory() as tmp:
        fake_repo = Path(tmp) / "repo"
        home_plans = Path(tmp) / "home-plans"
        (fake_repo / ".cursor").mkdir(parents=True)
        home_plans.mkdir()
        os.symlink(home_plans, fake_repo / ".cursor" / "plans")
        try:
            mirror = _under_repo(fake_repo, ".cursor", "plans", "_TEMPLATE.plan.md")
            expected = (fake_repo / ".cursor" / "plans" / "_TEMPLATE.plan.md").resolve()
            if mirror.resolve() != expected:
                errors.append(f"symlink mirror path unexpected: {mirror}")
        except SystemExit as exc:
            errors.append(f"home-symlink .cursor/plans wrongly rejected: {exc}")
        try:
            _under_repo(fake_repo, "..", "escape")
            errors.append("expected .. segment to be rejected")
        except SystemExit:
            # Expected: path-traversal ".." must raise SystemExit; no error to record.
            pass

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("PASS: self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
