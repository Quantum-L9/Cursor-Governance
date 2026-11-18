#!/usr/bin/env python3
"""Self-test for shelf_plans.py. Not collected by root pytest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SHELF = Path(__file__).resolve().parent / "shelf_plans.py"
PLAN = ".plan.md"


def _plan(name: str, body: str, *, age_days: float | None = None) -> None:
    path = Path(name)
    path.write_text(body, encoding="utf-8")
    if age_days is not None:
        stamp = time.time() - (age_days * 86400)
        os.utime(path, (stamp, stamp))


def _run(workspace: Path, plans: Path, *extra: str) -> dict:
    env = os.environ.copy()
    env["L9_REPO_WRITE_LOCK"] = "0"
    proc = subprocess.run(
        [
            sys.executable,
            str(SHELF),
            "--workspace",
            str(workspace),
            "--plans-dir",
            str(plans),
            "--format",
            "json",
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


def main() -> int:
    errors: list[str] = []
    import tempfile

    with tempfile.TemporaryDirectory(prefix="l9-shelf-plans-") as tmp:
        workspace = Path(tmp)
        plans = workspace / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "README.md").write_text("1. `live_queue_item`\n", encoding="utf-8")
        finished = """---
name: finished without status
todos:
  - id: a
    content: done
    status: completed
---

# finished
"""
        pending = """---
name: never started
todos:
  - id: a
    content: later
    status: pending
---

# pending
"""
        partial = """---
name: started
todos:
  - id: a
    content: done
    status: completed
  - id: b
    content: left
    status: pending
---

# partial
"""
        _plan(str(plans / f"finished_no_status{PLAN}"), finished, age_days=30)
        (plans / "finished_no_status.plan.json").write_text("{}\n", encoding="utf-8")
        _plan(str(plans / f"old_pending{PLAN}"), pending, age_days=30)
        _plan(str(plans / f"started{PLAN}"), partial, age_days=1)
        _plan(str(plans / f"live_queue_item{PLAN}"), pending, age_days=40)
        _plan(
            str(plans / f"compiled_packet{PLAN}"),
            pending.replace("name: never started", "name: compiled\ncompiled: true"),
            age_days=40,
        )
        _plan(str(plans / f"touched_recently{PLAN}"), pending, age_days=1)
        _plan(
            str(plans / f"old_superseded{PLAN}"),
            pending.replace("name: never started", "name: old\nstatus: superseded"),
            age_days=40,
        )
        stale_dir = plans / "stale"
        stale_dir.mkdir()
        _plan(str(stale_dir / f"done_in_stale{PLAN}"), finished, age_days=30)
        dup_dir = plans / "partially-built"
        dup_dir.mkdir()
        dup_body = partial
        (dup_dir / f"already_partial{PLAN}").write_text(dup_body, encoding="utf-8")
        (plans / f"already_partial{PLAN}").write_text(dup_body, encoding="utf-8")

        dry = _run(workspace, plans)
        if (plans / f"finished_no_status{PLAN}").is_file() is False:
            errors.append("dry-run moved a plan")
        names = {row["action"] + ":" + row["name"]: row for row in dry["actions"]}
        expect = {
            f"move:finished_no_status{PLAN}": "built",
            f"move:old_pending{PLAN}": "stale",
            f"move:started{PLAN}": "partially-built",
            f"move:old_superseded{PLAN}": "archive/superseded",
            f"move:done_in_stale{PLAN}": "built",
            f"keep:live_queue_item{PLAN}": "live_queue",
            f"keep:compiled_packet{PLAN}": "compiled",
            f"keep:touched_recently{PLAN}": "recent",
            f"drop:already_partial{PLAN}": "duplicate",
        }
        for key, field in expect.items():
            row = names.get(key)
            if row is None:
                errors.append(f"missing {key}")
                continue
            if field not in {row.get("dest"), row.get("reason")}:
                errors.append(f"{key} -> {row}")

        applied = _run(workspace, plans, "--apply")
        if applied["apply"] is not True:
            errors.append("apply flag did not stick")
        built = plans / "BUILT" / f"finished_no_status{PLAN}"
        if not built.is_file():
            built = plans / "built" / f"finished_no_status{PLAN}"
        if not built.is_file():
            errors.append("finished plan did not reach the built shelf")
        else:
            text = built.read_text(encoding="utf-8")
            if "status: built" not in text or "built: true" not in text:
                errors.append("built shelf did not record status and built: true")
            companion = built.parent / "finished_no_status.plan.json"
            if not companion.is_file():
                errors.append("companion did not move with the plan")
        if (plans / f"old_pending{PLAN}").exists():
            errors.append("stale plan stayed at the root")
        if not (plans / "stale" / f"old_pending{PLAN}").is_file():
            errors.append("never-started plan did not reach stale/")
        if not (plans / "partially-built" / f"started{PLAN}").is_file():
            errors.append("partial plan did not reach partially-built/")
        if (plans / f"live_queue_item{PLAN}").is_file() is False:
            errors.append("README live queue plan left the root")
        if (plans / f"already_partial{PLAN}").exists():
            errors.append("identical root duplicate was kept")
        superseded = plans / "archive" / "superseded" / f"old_superseded{PLAN}"
        if not superseded.is_file():
            errors.append("superseded plan did not reach archive/superseded")
        if (plans / "stale" / f"done_in_stale{PLAN}").exists():
            errors.append("todo-complete plan stayed in stale/")

    if errors:
        print("FAIL: shelf_plans_self_test")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS: shelf_plans_self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
