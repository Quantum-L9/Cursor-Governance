#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

OPS = ["CREATE", "UPDATE", "VALIDATE", "REGISTER", "COMMAND_BIND", "CONVERT"]
DISPOSITIONS = ["DELETE_TWIN", "ABSORB_INTO_SKILL", "CONVERT_TO_LANGGRAPH"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--operation", required=True, choices=OPS)
    ap.add_argument("--status", required=True, choices=["PASS", "PARTIAL", "BLOCKED", "FAIL"])
    ap.add_argument("--dag-id")
    ap.add_argument("--disposition", choices=DISPOSITIONS)
    ap.add_argument("--target-skill")
    ap.add_argument("--emitted-runtime")
    ap.add_argument("--surviving-runtime")
    ap.add_argument("--check", action="append", default=[])
    ap.add_argument("--changed", action="append", default=[])
    ap.add_argument("--unknown", action="append", default=[])
    ap.add_argument("--note", action="append", default=[])
    ap.add_argument("--out")
    ns = ap.parse_args()
    payload = {
        "skill": "l9-dag-authoring",
        "version": "2.2.0",
        "operation": ns.operation,
        "status": ns.status,
        "dag_id": ns.dag_id,
        "disposition": ns.disposition,
        "target_skill": ns.target_skill,
        "emitted_runtime": ns.emitted_runtime,
        "surviving_runtime": ns.surviving_runtime,
        "checks": [{"id": c, "status": "PASS"} for c in ns.check],
        "changed_surfaces": ns.changed,
        "unknowns": ns.unknown,
        "notes": ns.note,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if ns.out:
        Path(ns.out).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
