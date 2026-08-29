#!/usr/bin/env python3
import json
import sys
from pathlib import Path

OPS = {"CREATE", "UPDATE", "VALIDATE", "REGISTER", "COMMAND_BIND", "CONVERT"}
GRAPH_KINDS = {"AUTO", "SESSION_GUIDANCE", "LANGGRAPH_RUNTIME", "UNKNOWN"}
NON_CREATE = {"UPDATE", "VALIDATE", "REGISTER", "COMMAND_BIND", "CONVERT"}


def validate(data):
    errors = []
    if not isinstance(data, dict):
        return ["request must be an object"]
    if data.get("operation") not in OPS:
        errors.append("operation must be one of " + ",".join(sorted(OPS)))
    root = data.get("repo_root")
    if not isinstance(root, str) or not root.strip():
        errors.append("repo_root is required")
    graph_kind = data.get("graph_kind", "AUTO")
    if graph_kind not in GRAPH_KINDS:
        errors.append("graph_kind must be one of " + ",".join(sorted(GRAPH_KINDS)))
    if graph_kind == "UNKNOWN" and data.get("allow_mutation"):
        errors.append("UNKNOWN graph_kind blocks mutation")
    if data.get("operation") in NON_CREATE and not data.get("dag_path") and not data.get("dag_id"):
        errors.append("dag_path or dag_id required for non-CREATE operation")
    if data.get("operation") == "COMMAND_BIND" and not data.get("command_path"):
        errors.append("command_path required for COMMAND_BIND")
    if data.get("operation") == "REGISTER" and graph_kind == "LANGGRAPH_RUNTIME":
        errors.append(
            "REGISTER is SessionDAG registry-specific; "
            "use VALIDATE/UPDATE for LangGraph runtime binding"
        )
    if data.get("allow_session_retire") is True:
        errors.append("allow_session_retire is refused this wave")
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
