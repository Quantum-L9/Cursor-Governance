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
            "  note: leftover invariant\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--workspace",
                str(ws),
                "--format",
                "json",
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

    if errors:
        print("FAIL: l9-pipeline-audit self_test")
        for item in errors:
            print(f"  - {item}")
        return 1
    print("PASS: l9-pipeline-audit self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
