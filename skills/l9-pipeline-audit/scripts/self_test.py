#!/usr/bin/env python3
"""Self-test for l9-pipeline-audit (skill-local; not collected by root pytest)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_pipeline.py"
HARVEST = ROOT / "scripts" / "run_intelligence_harvest.py"


def main() -> int:
    errors: list[str] = []
    listed = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "l9-intelligence-harvest" not in listed:
        errors.append("SKILL.md must name l9-intelligence-harvest as harvest owner")
    if "l9-harvest-pipeline" not in listed:
        errors.append("SKILL.md must forbid l9-harvest-pipeline")
    if "make campaign" not in listed:
        errors.append("SKILL.md must prohibit make campaign")

    harvest_pack = ROOT.parent / "l9-intelligence-harvest" / "scripts" / "bind_request.py"
    if not harvest_pack.is_file():
        errors.append("l9-intelligence-harvest bind_request.py missing after ff")

    absorbed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_plans_self_test.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    if absorbed.returncode != 0:
        errors.append(f"audit_plans_self_test failed: {absorbed.stdout}{absorbed.stderr}")

    with tempfile.TemporaryDirectory(prefix="l9-pipeline-audit-") as tmp:
        ws = Path(tmp)
        (ws / "docs" / "plans").mkdir(parents=True)
        (ws / "WIP").mkdir()
        camp = ws / "environment" / "program-execution" / "campaigns" / "spent-with-objective"
        camp.mkdir(parents=True)
        (camp / "CAMPAIGN_SOURCE.yaml").write_text(
            "metadata:\n  campaign_id: spent-with-objective\n  status: complete\n"
            "operator_directive:\n  objective: keep this invariant\n",
            encoding="utf-8",
        )
        (ws / "WIP" / "INVENTORY.yaml").write_text(
            "entries:\n"
            "- path: WIP/8-28-26/topic/note.md\n"
            "  status: possible-landed\n"
            "  note: leftover invariant\n"
            "- path: WIP/8-28-26/topic/landed.md\n"
            "  status: landed\n",
            encoding="utf-8",
        )
        (ws / "WIP" / "8-28-26" / "topic").mkdir(parents=True)
        (ws / "WIP" / "8-28-26" / "topic" / "note.md").write_text("keep\n", encoding="utf-8")
        (ws / "WIP" / "8-28-26" / "topic" / "landed.md").write_text("gone\n", encoding="utf-8")
        (ws / "docs" / "plans" / "README.md").write_text(
            "1. `pe_loop_compiled_8-28-26`\n",
            encoding="utf-8",
        )
        (ws / "docs" / "plans" / "pe_loop_compiled_8-28-26.plan.md").write_text(
            "---\nname: compiled packet\ncompiled: true\ntodos:\n"
            "  - id: a\n    content: run\n    status: pending\n---\n\n# x\n",
            encoding="utf-8",
        )
        (ws / "docs" / "plans" / "spent_done.plan.md").write_text(
            "---\nname: spent\nbuilt: true\ntodos:\n"
            "  - id: a\n    content: done\n    status: completed\n---\n\n# y\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--workspace",
                str(ws),
                "--gov-root",
                str(ws),
                "--format",
                "json",
                "--archive-spent",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append(f"audit_pipeline exit {proc.returncode}: {proc.stderr}")
        else:
            payload = json.loads(proc.stdout)
            names = {row["name"] for row in payload.get("harvestable", [])}
            if "spent-with-objective" not in names:
                errors.append("complete campaign with objective must be harvestable")
            if "note.md" not in names:
                errors.append("possible-landed WIP must be harvestable")
            if not payload.get("plans_store_ok"):
                errors.append("temp workspace docs/plans must count as tracked store")
            next_names = [row.get("name") for row in payload.get("next") or []]
            next_stems = [
                Path(str(row.get("path") or "")).name.replace(".plan.md", "")
                for row in payload.get("next") or []
            ]
            if "pe_loop_compiled_8-28-26" not in next_names and (
                "pe_loop_compiled_8-28-26" not in next_stems
            ):
                errors.append(f"compiled packet must be NEXT: {next_names}")
            if "note.md" not in next_names:
                errors.append(f"possible-landed WIP must be NEXT: {next_names}")
            if not (ws / "docs" / "plans" / "built" / "spent_done.plan.md").is_file():
                errors.append("spent root plan must archive to built/")
            if (ws / "docs" / "plans" / "spent_done.plan.md").exists():
                errors.append("spent root plan must leave the live root")
            if not (ws / "WIP" / "_archived" / "8-28-26" / "topic" / "landed.md").is_file():
                errors.append("landed WIP must archive to WIP/_archived/")
            if not (ws / "WIP" / "8-28-26" / "topic" / "note.md").is_file():
                errors.append("possible-landed WIP must stay for harvest")
        session = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--workspace",
                str(ws),
                "--gov-root",
                str(ws),
                "--format",
                "session-start",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if session.returncode != 0 or "NEXT 1:" not in session.stdout:
            errors.append(f"session-start report missing NEXT: {session.stdout!r}")
        if "tracked docs/plans" not in session.stdout:
            errors.append("session-start must confirm tracked docs/plans")

    if errors:
        print("FAIL: l9-pipeline-audit self_test")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS: l9-pipeline-audit self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
