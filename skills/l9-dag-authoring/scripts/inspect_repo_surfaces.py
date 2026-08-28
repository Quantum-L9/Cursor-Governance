#!/usr/bin/env python3
import json
import sys
from pathlib import Path

SURFACES = {
    "dag_dir": "workflows/dags",
    "interface": "workflows/session/interface.py",
    "registry": "workflows/session/registry.py",
    "discovery": "workflows/dags/__init__.py",
    "commands": "commands",
}


def inspect(root):
    root = Path(root)
    rows = {name: {"path": rel, "exists": (root / rel).exists()} for name, rel in SURFACES.items()}
    mandatory = ["dag_dir", "interface", "registry", "discovery"]
    missing = [name for name in mandatory if not rows[name]["exists"]]
    return {
        "status": "BLOCKED" if missing else "PASS",
        "surfaces": rows,
        "missing_mandatory": missing,
    }


def main(argv):
    if len(argv) != 2:
        print(
            json.dumps(
                {"status": "FAIL", "error": "usage: inspect_repo_surfaces.py REPO_ROOT"}, indent=2
            )
        )
        return 2
    result = inspect(argv[1])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 3 if result["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
