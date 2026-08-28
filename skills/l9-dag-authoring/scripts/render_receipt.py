#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--operation",
        required=True,
        choices=["CREATE", "UPDATE", "VALIDATE", "REGISTER", "COMMAND_BIND"],
    )
    ap.add_argument("--status", required=True, choices=["PASS", "PARTIAL", "BLOCKED", "FAIL"])
    ap.add_argument("--dag-id")
    ap.add_argument("--check", action="append", default=[])
    ap.add_argument("--changed", action="append", default=[])
    ap.add_argument("--unknown", action="append", default=[])
    ap.add_argument("--note", action="append", default=[])
    ap.add_argument("--out")
    ns = ap.parse_args()
    payload = {
        "skill": "l9-dag-authoring",
        "version": "2.0.0",
        "operation": ns.operation,
        "status": ns.status,
        "dag_id": ns.dag_id,
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
