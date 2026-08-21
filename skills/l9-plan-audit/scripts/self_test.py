#!/usr/bin/env python3
"""Self-test for l9-plan-audit (skill-local; not collected by root pytest)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_plans.py"

EXECUTE = "## Execute via @environment/program-execution + autonomy (required)\n"


def _write_plan(
    directory: Path,
    name: str,
    *,
    todos: str,
    body_extra: str = "",
    include_execute: bool = True,
    mtime_age_days: float = 0.0,
) -> Path:
    path = directory / name
    execute = EXECUTE if include_execute else "# No execute section\n"
    text = f"""---
name: {path.stem}
overview: fixture
todos:
{todos}
isProject: false
---

# PLAN: fixture

{execute}
{body_extra}
"""
    path.write_text(text, encoding="utf-8")
    when = time.time() - (mtime_age_days * 86400.0)
    os.utime(path, (when, when))
    return path


def run_audit(plans_dir: Path, workspace: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(AUDIT),
        "--plans-dir",
        str(plans_dir),
        "--workspace",
        str(workspace),
        "--window-days",
        "7",
        "--format",
        "json",
        "--limit",
        "10",
        *extra,
    ]
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def skill_validation_scripts() -> list[str]:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    block = re.search(r"## Validation\s+.*?```bash\n(.*?)```", text, re.S)
    if not block:
        return []
    return re.findall(r"scripts/([a-zA-Z0-9_./-]+\.py)", block.group(1))


def main() -> int:
    errors: list[str] = []

    listed = skill_validation_scripts()
    if listed != ["self_test.py"]:
        errors.append(f"SKILL.md Validation scripts mismatch: {listed}")

    for required in (
        ROOT / "SKILL.md",
        ROOT / "agents" / "meta.yaml",
        ROOT / "references" / "staleness-rules.md",
        AUDIT,
    ):
        if not required.is_file():
            errors.append(f"missing required file: {required}")

    with tempfile.TemporaryDirectory(prefix="l9-plan-audit-") as tmp:
        plans = Path(tmp) / "plans"
        plans.mkdir()
        workspace = Path(tmp) / "ws"
        workspace.mkdir()
        head = "abcdef0123456789abcdef0123456789abcdef01"
        git_dir = workspace / ".git"
        git_dir.mkdir()
        (git_dir / "refs" / "heads").mkdir(parents=True)
        (git_dir / "refs" / "heads" / "main").write_text(head + "\n", encoding="utf-8")
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")

        _write_plan(
            plans,
            "_TEMPLATE.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=0.0,
        )
        _write_plan(
            plans,
            "us_date_unbuilt_8-20-26.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=1.0,
        )
        _write_plan(
            plans,
            "recent_unbuilt_aaaaaaaa.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=1.0,
        )
        _write_plan(
            plans,
            "completed_bbbbbbbb.plan.md",
            todos="  - id: t1\n    content: x\n    status: completed\n",
            mtime_age_days=1.0,
        )
        _write_plan(
            plans,
            "old_unbuilt_cccccccc.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=30.0,
        )
        _write_plan(
            plans,
            "empty_todos_dddddddd.plan.md",
            todos="[]\n",
            mtime_age_days=0.5,
        )
        built_marked = plans / "built_marked_abababab.plan.md"
        built_marked.write_text(
            """---
name: built_marked_abababab
overview: fixture
built: true
status: built
todos:
  - id: t1
    content: leftover pending after Build
    status: pending
isProject: false
---

# PLAN: fixture

## Execute via @environment/program-execution + autonomy (required)
""",
            encoding="utf-8",
        )
        os.utime(built_marked, (time.time(), time.time()))
        nested = plans / "built"
        nested.mkdir()
        _write_plan(
            nested,
            "shelved_unbuilt_abababab.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=0.0,
        )
        _write_plan(
            plans,
            "drift_eeeeeeee.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            body_extra=(
                "## immutable_baseline\n\ncommit_sha: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n"
            ),
            mtime_age_days=0.2,
        )
        _write_plan(
            plans,
            "dup_slug_11111111.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=2.0,
        )
        _write_plan(
            plans,
            "dup_slug_22222222.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            mtime_age_days=0.1,
        )
        _write_plan(
            plans,
            "no_execute_ffffffff.plan.md",
            todos="  - id: t1\n    content: x\n    status: in_progress\n",
            include_execute=False,
            mtime_age_days=0.3,
        )
        simple_path = plans / "simple_build_cafecafe.plan.md"
        simple_path.write_text(
            """---
name: simple-build
overview: fixture
todos:
  - id: t1
    content: x
    status: pending
isProject: false
kind: simple
execute_via: cursor-build
---

# PLAN: simple

## Execute via Cursor Build

Press Build on the current checkout.
- Do not run `make campaign`.
""",
            encoding="utf-8",
        )
        when = time.time() - (0.15 * 86400.0)
        os.utime(simple_path, (when, when))
        _write_plan(
            plans,
            "match_baseline_99999999.plan.md",
            todos="  - id: t1\n    content: x\n    status: pending\n",
            body_extra=f"## immutable_baseline\n\ncommit_sha: {head}\n",
            mtime_age_days=0.4,
        )

        proc = run_audit(plans, workspace)
        if proc.returncode != 0:
            errors.append(f"audit exit {proc.returncode}: {proc.stderr}")
        else:
            import json

            try:
                payload = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"json parse failed: {exc}\n{proc.stdout}")
                payload = {}
            names = {Path(f["path"]).name for f in payload.get("findings", [])}
            if "recent_unbuilt_aaaaaaaa.plan.md" not in names:
                errors.append("expected recent unbuilt in findings")
            if "us_date_unbuilt_8-20-26.plan.md" not in names:
                errors.append("expected US M-D-YY unbuilt in findings")
            if "completed_bbbbbbbb.plan.md" in names:
                errors.append("completed plan must be excluded")
            if "built_marked_abababab.plan.md" in names:
                errors.append("built: true plan must be excluded even with pending todos")
            if "shelved_unbuilt_abababab.plan.md" in names:
                errors.append("plans in built/ must be excluded (top-level glob only)")
            if "old_unbuilt_cccccccc.plan.md" in names:
                errors.append("old unbuilt outside window must be excluded")
            if "_TEMPLATE.plan.md" in names:
                errors.append("template must be excluded")
            by_name = {Path(f["path"]).name: f for f in payload.get("findings", [])}
            empty = by_name.get("empty_todos_dddddddd.plan.md")
            if not empty or "empty_todos" not in empty.get("flags", []):
                errors.append("empty_todos flag missing")
            drift = by_name.get("drift_eeeeeeee.plan.md")
            if not drift or "baseline_drift" not in drift.get("flags", []):
                errors.append("baseline_drift flag missing")
            match = by_name.get("match_baseline_99999999.plan.md")
            if match and "baseline_drift" in match.get("flags", []):
                errors.append("matching baseline incorrectly flagged")
            old_dup = by_name.get("dup_slug_11111111.plan.md")
            if not old_dup or "superseded" not in old_dup.get("flags", []):
                errors.append("older dup slug should be superseded")
            noex = by_name.get("no_execute_ffffffff.plan.md")
            if not noex or "missing_execute_section" not in noex.get("flags", []):
                errors.append("missing_execute_section flag missing")
            if not noex or "in_progress" not in noex.get("flags", []):
                errors.append("in_progress flag missing")
            simple = by_name.get("simple_build_cafecafe.plan.md")
            if not simple:
                errors.append("simple-kind plan missing from findings")
            elif "missing_execute_section" in simple.get("flags", []):
                errors.append("simple-kind plan must not get missing_execute_section")

        missing = run_audit(Path(tmp) / "nope", workspace, "--format", "markdown")
        if missing.returncode != 0 or "no plans dir" not in missing.stdout:
            errors.append(f"missing dir markdown failed: {missing.stdout!r} / {missing.stderr!r}")

    if errors:
        print("FAIL: l9-plan-audit self_test")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("PASS: l9-plan-audit self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
