#!/usr/bin/env python3
"""Self-test for l9-audit-plans (skill-local; not collected by root pytest)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELF = ROOT / "scripts" / "shelf_plans.py"
REFINE = ROOT / "scripts" / "refine_plans.py"
INVOKE = ROOT / "scripts" / "run_audit_plans.py"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _plan(
    name: str,
    statuses: list[str],
    *,
    compiled: bool = False,
    status: str | None = None,
    harvested: bool = False,
    compiled_into: str | None = None,
    contents: list[str] | None = None,
) -> str:
    rows = []
    for idx, todo_status in enumerate(statuses, start=1):
        content = (contents[idx - 1] if contents and idx - 1 < len(contents) else "x")
        rows.append(f"  - id: t{idx}\n    content: {content}\n    status: {todo_status}")
    todos = "\n".join(rows)
    extra = ""
    if compiled:
        extra += "compiled: true\n"
    if status:
        extra += f"status: {status}\n"
    if harvested:
        extra += "harvested: true\n"
    if compiled_into:
        extra += f"compiled_into: {compiled_into}\n"
    return f"---\nname: {name}\n{extra}todos:\n{todos}\nisProject: false\n---\n\n# PLAN\n"


def _run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)


def _fm(path: Path) -> dict:
    sys.path.insert(0, str(ROOT.parents[0] / "l9-pipeline-audit" / "scripts"))
    from audit_plans import parse_frontmatter

    fm, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return fm


def main() -> int:
    errors: list[str] = []
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    shelves = (ROOT / "references" / "shelves.md").read_text(encoding="utf-8")
    refine = (ROOT / "references" / "refine.md").read_text(encoding="utf-8")
    concerns = (ROOT / "references" / "concerns.md").read_text(encoding="utf-8")
    for body, label in ((skill, "SKILL.md"), (shelves, "shelves.md"), (refine, "refine.md")):
        if "`partially-built/`" not in body and "partially-built" not in body:
            errors.append(f"{label} must name partially-built/")
        if "`stale/`" not in body and "stale/" not in body:
            errors.append(f"{label} must name stale/")
    if "absorb" in refine.lower() and "No `absorb`" not in refine:
        errors.append("refine.md must forbid absorb")
    if "references/refine.md" not in skill or "references/concerns.md" not in skill:
        errors.append("SKILL.md must cite refine.md and concerns.md")
    if "run_audit_plans.py" not in skill:
        errors.append("SKILL.md must invoke run_audit_plans.py")
    if "L9_AUDIT_PLANS_REFINE=0" not in skill:
        errors.append("SKILL.md must name the refine kill switch")
    if "SessionStart must not" not in skill and "SessionStart" not in skill:
        errors.append("SKILL.md must keep SessionStart off refine")
    if "ceremony_" not in concerns:
        errors.append("concerns.md must list ceremony_")
    live_table = skill.split("Retired", 1)[0]
    if "| `backlog/` |" in live_table:
        errors.append("SKILL.md must not list backlog/ as a live shelf")

    import tempfile

    with tempfile.TemporaryDirectory(prefix="l9-audit-plans-") as tmp:
        plans = Path(tmp) / "plans"
        plans.mkdir()
        _write(plans / "README.md", "## Live queue\n\n1. `keep_me_9-5-26`\n\n## Score law\n")
        _write(plans / "_TEMPLATE.plan.md", _plan("template", ["pending"]))
        _write(plans / "keep_me_9-5-26.plan.md", _plan("keep", ["pending"]))
        _write(plans / "leftover_started.plan.md", _plan("started", ["completed", "pending"]))
        _write(plans / "leftover_unbuilt.plan.md", _plan("parked", ["pending", "pending"]))
        _write(plans / "leftover_done.plan.md", _plan("done", ["completed", "completed"]))
        _write(plans / "partial" / "dup.plan.md", _plan("dup", ["completed", "pending"]))
        _write(
            plans / "partially-built" / "dup.plan.md",
            _plan("dup", ["completed", "pending"]),
        )
        _write(plans / "pending" / "old_pending.plan.md", _plan("old", ["pending"]))
        _write(plans / "backlog" / "old_backlog.plan.md", _plan("old2", ["pending"]))
        proc = _run(
            [
                sys.executable,
                str(SHELF),
                "--plans-dir",
                str(plans),
                "--workspace",
                tmp,
                "--today",
                "2026-09-05",
                "--format",
                "json",
            ]
        )
        if proc.returncode != 0:
            errors.append(f"shelf_plans.py failed: {proc.stdout}{proc.stderr}")
        else:
            if (plans / "partial").exists():
                errors.append("partial/ must be removed")
            if (plans / "pending").exists():
                errors.append("pending/ must be removed")
            if (plans / "backlog").exists():
                errors.append("backlog/ must be removed")
            if not (plans / "keep_me_9-5-26.plan.md").is_file():
                errors.append("current plan must stay at root")
            if str(_fm(plans / "keep_me_9-5-26.plan.md").get("status")) != "current":
                errors.append("root missing status must heal to current")
            if not (plans / "partially-built" / "leftover_started.plan.md").is_file():
                errors.append("started leftover must go to partially-built/")
            started_fm = _fm(plans / "partially-built" / "leftover_started.plan.md")
            if started_fm.get("status") != "partially-built":
                errors.append("leave-root status must match dest folder")
            if not (plans / "stale" / "leftover_unbuilt.plan.md").is_file():
                errors.append("parked unbuilt must go to stale/")
            if _fm(plans / "stale" / "leftover_unbuilt.plan.md").get("status") != "stale":
                errors.append("stale donor must have status stale")
            if not (plans / "built" / "leftover_done.plan.md").is_file():
                errors.append("finished leftover must go to built/")

        dest_win = Path(tmp) / "dest-win"
        dest_win.mkdir()
        _write(dest_win / "README.md", "1. `keep`\n")
        _write(
            dest_win / "same_slug_aaaa1111.plan.md",
            _plan("incoming", ["completed", "pending"], contents=["incoming done", "new leftover"]),
        )
        _write(
            dest_win / "partially-built" / "same_slug_bbbb2222.plan.md",
            _plan(
                "keeper",
                ["completed", "pending"],
                status="partially-built",
                contents=["done", "keep me"],
            ),
        )
        dest_before = (dest_win / "partially-built" / "same_slug_bbbb2222.plan.md").read_text(
            encoding="utf-8"
        )
        _run(
            [
                sys.executable,
                str(SHELF),
                "--plans-dir",
                str(dest_win),
                "--workspace",
                tmp,
                "--today",
                "2026-09-05",
                "--format",
                "json",
            ]
        )
        dest_after = (dest_win / "partially-built" / "same_slug_bbbb2222.plan.md").read_text(
            encoding="utf-8"
        )
        if dest_before != dest_after:
            errors.append("started dest must win over all-pending same-slug src")
        if (dest_win / "same_slug_aaaa1111.plan.md").is_file():
            errors.append("same-slug src should be removed after dest-wins")

        refine_dir = Path(tmp) / "refine"
        refine_dir.mkdir()
        _write(
            refine_dir / "README.md",
            "## Live queue\n\n1. `ceremony_live`\n\n## Next\n",
        )
        _write(refine_dir / "_TEMPLATE.plan.md", _plan("template", ["pending"]))
        _write(
            refine_dir / "ceremony_live.plan.md",
            _plan("live", ["pending"], status="current", contents=["keep live"]),
        )
        _write(
            refine_dir / "stale" / "ceremony_old.plan.md",
            _plan(
                "old ceremony",
                ["pending", "pending"],
                status="stale",
                contents=["unique leftover from stale", "AGENTS.md already says this"],
            ),
        )
        _write(
            refine_dir / "stale" / "n8n_foreign.plan.md",
            _plan("foreign", ["pending"], status="stale", contents=["other repo leftover"]),
        )
        _write(
            refine_dir / "stale" / "ff_gap.plan.md",
            _plan("ff gap", ["pending"], status="stale", contents=["unique ff leftover"]),
        )
        first = _run(
            [sys.executable, str(REFINE), "--plans-dir", str(refine_dir), "--format", "json"]
        )
        if first.returncode != 0:
            errors.append(f"refine failed: {first.stdout}{first.stderr}")
        else:
            live = _fm(refine_dir / "ceremony_live.plan.md")
            contents = [str(t.get("content")) for t in live.get("todos") or []]
            if "unique leftover from stale" not in contents:
                errors.append("fold must append unique leftover onto same-concern root")
            if "AGENTS.md already says this" not in contents:
                errors.append("leftover must not drop because AGENTS.md mentions it")
            donor = _fm(refine_dir / "stale" / "ceremony_old.plan.md")
            if donor.get("harvested") is not True:
                errors.append("folded donor must set harvested true")
            if donor.get("status") != "stale":
                errors.append("fold must keep folder status")
            if donor.get("compiled_into") != "ceremony_live.plan.md":
                errors.append("fold must set compiled_into survivor")
            foreign = _fm(refine_dir / "stale" / "n8n_foreign.plan.md")
            if foreign.get("harvested") is True:
                errors.append("other-repo must stay untagged")
            if not (refine_dir / "stale" / "n8n_foreign.plan.md").is_file():
                errors.append("other-repo must stay stale")
            if not (refine_dir / "compiled_ff.plan.md").is_file():
                errors.append("compile must emit one packet per concern")
            compiled = _fm(refine_dir / "compiled_ff.plan.md")
            if compiled.get("status") != "current" or compiled.get("compiled") is not True:
                errors.append("compiled packet must be status current and compiled true")
            ff_donor = _fm(refine_dir / "stale" / "ff_gap.plan.md")
            if ff_donor.get("harvested") is not True:
                errors.append("compiled donor must be harvested")
            readme = (refine_dir / "README.md").read_text(encoding="utf-8")
            if "`compiled_ff`" not in readme or "`ceremony_live`" not in readme:
                errors.append("README live-queue must list remaining root plans")
            if "1. `keep_me_9-5-26`" in readme:
                errors.append("README must not keep stale numbered names")

        second = _run(
            [sys.executable, str(REFINE), "--plans-dir", str(refine_dir), "--format", "json"]
        )
        if second.returncode != 0:
            errors.append(f"second refine failed: {second.stdout}{second.stderr}")
        else:
            payload = json.loads(second.stdout)
            actions = " ".join(payload.get("actions") or [])
            if "fold ceremony_old" in actions or "compile ff_gap" in actions:
                errors.append("second refine must omit harvested donors")
            if len(list(refine_dir.glob("compiled_*.plan.md"))) != 1:
                errors.append("second refine must not emit a second compiled packet")

        skip_env = os.environ.copy()
        skip_env["L9_AUDIT_PLANS_REFINE"] = "0"
        skipped = _run(
            [
                sys.executable,
                str(INVOKE),
                "--plans-dir",
                str(refine_dir),
                "--workspace",
                tmp,
                "--today",
                "2026-09-05",
                "--format",
                "json",
            ],
            env=skip_env,
        )
        if skipped.returncode != 0:
            errors.append(f"invoke kill switch failed: {skipped.stdout}{skipped.stderr}")
        else:
            body = json.loads(skipped.stdout)
            if not body.get("refine_skipped"):
                errors.append("L9_AUDIT_PLANS_REFINE=0 must skip refine")

    if errors:
        print("FAIL: l9-audit-plans self_test")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("PASS: l9-audit-plans self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
