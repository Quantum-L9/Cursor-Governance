#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

from classify_conversion_disposition import classify_all
from classify_graph_kind import classify
from convert_session_to_langgraph import convert
from validate_command_trigger import validate as validate_command
from validate_langgraph_source import validate as validate_langgraph
from validate_langgraph_source import validate_package
from validate_request import validate as validate_request
from validate_session_dag_source import validate as validate_session

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parents[1]


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
        compile_only = root / "compile_only"
        compile_only.mkdir()
        (compile_only / "graph.py").write_text(
            runtime.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (compile_only / "executor.py").write_text(
            "def compile_graph():\n    return build_graph().compile()\n",
            encoding="utf-8",
        )
        compile_pkg = validate_package(compile_only)
        checks.append(
            (
                "package_compile_only_fails",
                compile_pkg["status"] == "FAIL"
                and "missing_durable_checkpointer" in compile_pkg["errors"],
            )
        )
        ephemeral = root / "ephemeral"
        ephemeral.mkdir()
        (ephemeral / "graph.py").write_text(runtime.read_text(encoding="utf-8"), encoding="utf-8")
        (ephemeral / "executor.py").write_text(
            "from langgraph.checkpoint.memory import MemorySaver\n"
            "def compile_graph():\n"
            "    return build_graph().compile(checkpointer=MemorySaver())\n",
            encoding="utf-8",
        )
        ephemeral_pkg = validate_package(ephemeral)
        checks.append(
            (
                "package_ephemeral_fails",
                ephemeral_pkg["status"] == "FAIL"
                and "ephemeral_checkpointer" in ephemeral_pkg["errors"],
            )
        )
        emitted = convert(
            REPO,
            dag_id="fixture-convert-ok",
            disposition="CONVERT_TO_LANGGRAPH",
            source=PACK / "fixtures" / "convert_ok_session.py",
            emit_dir=root / "ok_graph",
        )
        emit_pkg = validate_package(root / "ok_graph")
        checks.append(("convert_emit_pass", emitted.get("status") == "PASS"))
        checks.append(
            (
                "convert_emit_durable",
                emit_pkg.get("status") == "PASS" and emit_pkg.get("persistence_class") == "durable",
            )
        )
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
        checks.append(
            (
                "convert_requires_id",
                bool(validate_request({"operation": "CONVERT", "repo_root": "/tmp"})),
            )
        )
        checks.append(
            (
                "convert_refuses_retire",
                bool(
                    validate_request(
                        {
                            "operation": "CONVERT",
                            "repo_root": "/tmp",
                            "dag_id": "x",
                            "allow_session_retire": True,
                        }
                    )
                ),
            )
        )
        checks.append(
            (
                "convert_count_is_one",
                classify_all(REPO)["convert_to_langgraph_count"] == 1,
            )
        )
        prose = convert(
            REPO,
            dag_id="prose-convert-fixture",
            disposition="CONVERT_TO_LANGGRAPH",
            source=PACK / "fixtures" / "convert_prose_action.py",
            emit_dir=root / "prose",
        )
        checks.append(("prose_action_refused", prose.get("status") == "FAIL"))
        twin = convert(REPO, dag_id="gmp-execution-v1")
        checks.append(("twin_not_emitted", twin.get("status") == "FAIL"))
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
