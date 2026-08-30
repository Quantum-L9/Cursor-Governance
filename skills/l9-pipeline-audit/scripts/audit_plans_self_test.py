#!/usr/bin/env python3
"""Self-test for absorbed audit_plans.py (skill-local; not collected by root pytest)."""

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
    if "self_test.py" not in listed:
        errors.append(f"SKILL.md Validation must list self_test.py: {listed}")

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
- Do **not** run `make campaign`.
""",
            encoding="utf-8",
        )
        when = time.time() - (0.15 * 86400.0)
        os.utime(simple_path, (when, when))
        compiled_path = plans / "compiled_live_cafef00d.plan.md"
        compiled_path.write_text(
            """---
name: compiled-live
overview: fixture
compiled: true
todos:
  - id: t1
    content: x
    status: pending
isProject: false
kind: simple
execute_via: cursor-build
---

# PLAN: compiled

## Execute via Cursor Build

Press Build on the current checkout.
- Do **not** run `make campaign`.
""",
            encoding="utf-8",
        )
        os.utime(compiled_path, (when, when))
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
            if not noex or "harvestable" not in noex.get("flags", []):
                errors.append("harvestable flag missing on mixed PE-kind plan")
            compiled = by_name.get("compiled_live_cafef00d.plan.md")
            if not compiled:
                errors.append("compiled: true plan with pending todos must stay unbuilt")
            simple = by_name.get("simple_build_cafecafe.plan.md")
            if not simple:
                errors.append("simple-kind plan missing from findings")
            elif "missing_execute_section" in simple.get("flags", []):
                errors.append("simple-kind plan must not get missing_execute_section")
            recent = by_name.get("recent_unbuilt_aaaaaaaa.plan.md")
            if not recent or "kernel_unfired" not in recent.get("flags", []):
                errors.append("kernel_unfired flag missing on unhardened unbuilt plan")

        missing = run_audit(Path(tmp) / "nope", workspace, "--format", "markdown")
        if missing.returncode != 0 or "no plans dir" not in missing.stdout:
            errors.append(f"missing dir markdown failed: {missing.stdout!r} / {missing.stderr!r}")

        sys.path.insert(0, str(ROOT / "scripts"))
        from harvest_plan_invariants import extract_invariants, reject_implementation

        harvest_src = plans / "harvest_src_aaaaaaaa.plan.md"
        harvest_src.write_text(
            """---
name: harvest-src
overview: Keep the live invariant
todos:
  - id: t1
    content: x
    status: pending
isProject: false
---

# PLAN

| SP-01 | SessionStart stays display-only | quality_gate | proof | true |
""",
            encoding="utf-8",
        )
        harvested = extract_invariants(harvest_src)
        texts = [item["text"] for item in harvested["invariants"]]
        if "SessionStart stays display-only" not in texts:
            errors.append("harvest extractor missed success property")
        if any("```" in item["text"] for item in harvested["invariants"]):
            errors.append("harvest extractor copied a code fence")
        try:
            reject_implementation({"body": "```python\nprint(1)\n```"})
            errors.append("reject_implementation must fail on a code fence")
        except SystemExit:
            pass

    if errors:
        print("FAIL: audit_plans_self_test")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("PASS: audit_plans_self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
