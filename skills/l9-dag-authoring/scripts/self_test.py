#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from validate_command_trigger import validate as validate_command
from validate_request import validate as validate_request
from validate_session_dag_source import validate as validate_dag


def main():
    checks = []
    checks.append(
        ("request_valid", not validate_request({"operation": "CREATE", "repo_root": "/tmp"}))
    )
    checks.append(
        (
            "request_rejects_bad_op",
            bool(validate_request({"operation": "BOGUS", "repo_root": "/tmp"})),
        )
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        dag = root / "demo_dag.py"
        dag.write_text(
            "from workflows.session.interface import SessionDAG, SessionNode, SessionEdge\n"
            "from workflows.session.registry import register_session_dag\n"
            "DEMO_DAG = SessionDAG(id='demo', name='Demo', version='1', "
            "description='x', nodes=[SessionNode(id='start')], edges=[])\n"
            "register_session_dag(DEMO_DAG)\n",
            encoding="utf-8",
        )
        checks.append(
            ("dag_source_accepts_canonical_binding", validate_dag(dag)["status"] == "PASS")
        )
        cmd = root / "demo.md"
        cmd.write_text(
            "---\ndag: demo\ndag_file: workflows/dags/demo_dag.py\n---\n"
            "# /demo\nExecute the registered DAG.\n",
            encoding="utf-8",
        )
        checks.append(
            (
                "thin_command_accepts_canonical_path",
                validate_command(cmd, "demo")["status"] == "PASS",
            )
        )
        bad = root / "bad.md"
        bad.write_text(
            "---\ndag: demo\ndag_file: .cursor-commands/workflows/dags/demo_dag.py\n---\n",
            encoding="utf-8",
        )
        checks.append(
            ("thin_command_rejects_stale_path", validate_command(bad, "demo")["status"] == "FAIL")
        )
    failed = [name for name, ok in checks if not ok]
    print(
        json.dumps(
            {
                "status": "FAIL" if failed else "PASS",
                "checks": [{"id": n, "status": "pass" if ok else "fail"} for n, ok in checks],
                "failed": failed,
            },
            indent=2,
        )
    )
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
