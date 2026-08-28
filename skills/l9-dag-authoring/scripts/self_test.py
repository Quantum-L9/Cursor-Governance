#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from classify_graph_kind import classify
from validate_command_trigger import validate as validate_command
from validate_langgraph_source import validate as validate_langgraph
from validate_request import validate as validate_request
from validate_session_dag_source import validate as validate_session


def main():
    checks = []
    checks.append(
        (
            "request_valid",
            not validate_request(
                {"operation": "CREATE", "repo_root": "/tmp", "graph_kind": "AUTO"}
            ),
        )
    )
    checks.append(
        (
            "request_rejects_bad_op",
            bool(validate_request({"operation": "BOGUS", "repo_root": "/tmp"})),
        )
    )
    checks.append(
        (
            "langgraph_register_rejected",
            bool(
                validate_request(
                    {
                        "operation": "REGISTER",
                        "repo_root": "/tmp",
                        "dag_id": "x",
                        "graph_kind": "LANGGRAPH_RUNTIME",
                    }
                )
            ),
        )
    )
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        session = root / "session_dag.py"
        session.write_text(
            "from workflows.session.interface import SessionDAG, SessionNode, SessionEdge\n"
            "from workflows.session.registry import register_session_dag\n"
            "DEMO_DAG = SessionDAG(\n"
            "    id='demo', name='Demo', version='1',\n"
            "    description='x', nodes=[], edges=[],\n"
            ")\n"
            "register_session_dag(DEMO_DAG)\n",
            encoding="utf-8",
        )
        checks.append(("classifies_session", classify(session)["graph_kind"] == "SESSION_GUIDANCE"))
        checks.append(
            (
                "session_source_accepts_canonical_binding",
                validate_session(session)["status"] == "PASS",
            )
        )
        runtime = root / "runtime.py"
        runtime.write_text(
            "from langgraph.graph import StateGraph\n"
            "def build_graph():\n"
            "    return StateGraph(dict)\n",
            encoding="utf-8",
        )
        checks.append(
            ("classifies_langgraph", classify(runtime)["graph_kind"] == "LANGGRAPH_RUNTIME")
        )
        checks.append(("langgraph_source_valid", validate_langgraph(runtime)["status"] == "PASS"))
        mixed = root / "mixed.py"
        mixed.write_text(
            "from langgraph.graph import StateGraph\n"
            "from workflows.session.interface import SessionDAG\n"
            "G = StateGraph(dict)\n"
            "D = SessionDAG(id='m', name='M', version='1', description='', nodes=[], edges=[])\n",
            encoding="utf-8",
        )
        checks.append(("mixed_graph_blocks", classify(mixed)["status"] == "BLOCKED"))
        cmd = root / "demo.md"
        cmd.write_text(
            "---\ndag: demo\ndag_file: workflows/dags/demo_dag.py\n---\n"
            "# /demo\nExecute the registered graph.\n",
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
