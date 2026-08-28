#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path


def probe(repo_root, dag_id):
    root = Path(repo_root).resolve()
    code = (
        "import workflows.dags; "
        "from workflows.session.registry import get_session_dag; "
        f"d=get_session_dag({dag_id!r}); "
        "assert d is not None; print(d.id)"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], cwd=root, env=env, text=True, capture_output=True
    )
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main(argv):
    if len(argv) != 3:
        print(
            json.dumps(
                {"status": "FAIL", "error": "usage: probe_registration.py REPO_ROOT DAG_ID"},
                indent=2,
            )
        )
        return 2
    result = probe(argv[1], argv[2])
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
