#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def validate(path, expected_dag_id=None):
    p = Path(path)
    if not p.is_file():
        return {"status": "FAIL", "errors": [f"missing command file: {p}"]}
    text = p.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors = []
    if ".cursor-commands/workflows/dags" in text:
        errors.append("stale .cursor-commands DAG path present")
    if len(lines) > 80:
        errors.append(f"command is not thin: {len(lines)} lines > 80")
    if expected_dag_id and not re.search(
        rf"(?m)^dag:\s*[\"']?{re.escape(expected_dag_id)}[\"']?\s*$", text
    ):
        errors.append("expected dag id not declared in command frontmatter")
    if not re.search(r"(?m)^dag_file:\s*[^\n]*workflows/dags/[^\n]+\.py\s*$", text):
        errors.append("command does not point at canonical workflows/dags/*.py path")
    phase_headers = len(re.findall(r"(?im)^#{2,}\s*(phase|step)\b", text))
    if phase_headers >= 3:
        errors.append("command duplicates workflow phases instead of remaining trigger-only")
    return {"status": "FAIL" if errors else "PASS", "errors": errors, "line_count": len(lines)}


def main(argv):
    if len(argv) not in {2, 3}:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "errors": ["usage: validate_command_trigger.py COMMAND_FILE [DAG_ID]"],
                },
                indent=2,
            )
        )
        return 2
    result = validate(argv[1], argv[2] if len(argv) == 3 else None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
