#!/usr/bin/env python3
import json
import sys
from pathlib import Path

OPS = {"CREATE", "UPDATE", "VALIDATE", "REGISTER", "COMMAND_BIND"}


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["request must be an object"]
    if data.get("operation") not in OPS:
        errors.append("operation must be one of " + ",".join(sorted(OPS)))
    root = data.get("repo_root")
    if not isinstance(root, str) or not root.strip():
        errors.append("repo_root is required")
    if (
        data.get("operation") in {"UPDATE", "VALIDATE", "REGISTER", "COMMAND_BIND"}
        and not data.get("dag_path")
        and not data.get("dag_id")
    ):
        errors.append("dag_path or dag_id required for non-CREATE operation")
    if data.get("operation") == "COMMAND_BIND" and not data.get("command_path"):
        errors.append("command_path required for COMMAND_BIND")
    return errors


def main(argv):
    if len(argv) != 2:
        print(
            json.dumps(
                {"status": "FAIL", "errors": ["usage: validate_request.py request.json"]}, indent=2
            )
        )
        return 2
    data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    errors = validate(data)
    print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
