import json
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

from classify_conversion_disposition import (  # noqa: E402
    classify_all,
    classify_request,
)
from classify_graph_kind import classify  # noqa: E402
from convert_session_to_langgraph import convert  # noqa: E402
from validate_command_trigger import validate as validate_command  # noqa: E402
from validate_langgraph_source import (  # noqa: E402
    validate as validate_langgraph,
)
from validate_langgraph_source import (  # noqa: E402
    validate_package,
)
from validate_request import validate as validate_request  # noqa: E402
from validate_session_dag_source import validate as validate_session  # noqa: E402

REPO = PACK.parents[1]


def test_request_contract():
    assert (
        validate_request({"operation": "CREATE", "repo_root": "/tmp", "graph_kind": "AUTO"}) == []
    )
    # graph_kind is optional and defaults to AUTO.
    assert validate_request({"operation": "CREATE", "repo_root": "/tmp"}) == []
    assert validate_request({"operation": "BOGUS", "repo_root": "/tmp"})
    assert validate_request(
        {
            "operation": "REGISTER",
            "repo_root": "/tmp",
            "dag_id": "x",
            "graph_kind": "LANGGRAPH_RUNTIME",
        }
    )
    assert validate_request({"operation": "CONVERT", "repo_root": "/tmp"})
    assert (
        validate_request(
            {"operation": "CONVERT", "repo_root": "/tmp", "dag_id": "intelligence-harvest-v1"}
        )
        == []
    )
    assert validate_request(
        {
            "operation": "CONVERT",
            "repo_root": "/tmp",
            "dag_id": "intelligence-harvest-v1",
            "allow_session_retire": True,
        }
    )


def test_graph_kind_classification(tmp_path):
    session = tmp_path / "session.py"
    session.write_text("from workflows.session.interface import SessionDAG\n", encoding="utf-8")
    assert classify(session)["graph_kind"] == "SESSION_GUIDANCE"
    runtime = tmp_path / "runtime.py"
    runtime.write_text("from langgraph.graph import StateGraph\n", encoding="utf-8")
    assert classify(runtime)["graph_kind"] == "LANGGRAPH_RUNTIME"
    mixed = tmp_path / "mixed.py"
    mixed.write_text(
        "from langgraph.graph import StateGraph\n"
        "from workflows.session.interface import SessionDAG\n",
        encoding="utf-8",
    )
    assert classify(mixed)["status"] == "BLOCKED"


def test_session_validator_canonical(tmp_path):
    f = tmp_path / "x.py"
    f.write_text(
        "from workflows.session.interface import SessionDAG, SessionNode, SessionEdge\n"
        "from workflows.session.registry import register_session_dag\n"
        "X_DAG=SessionDAG(id='x',name='X',version='1',description='x',nodes=[],edges=[])\n"
        "register_session_dag(X_DAG)\n",
        encoding="utf-8",
    )
    assert validate_session(f)["status"] == "PASS"


def test_session_validator_rejects_unregistered(tmp_path):
    f = tmp_path / "x.py"
    f.write_text(
        "from workflows.session.interface import SessionDAG\nX=SessionDAG(id='x')\n",
        encoding="utf-8",
    )
    assert validate_session(f)["status"] == "FAIL"


def test_langgraph_validator(tmp_path):
    f = tmp_path / "x.py"
    f.write_text(
        "from langgraph.graph import StateGraph\ndef build():\n    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    assert validate_langgraph(f)["status"] == "PASS"
    bad = tmp_path / "bad.py"
    bad.write_text(
        "from langgraph.graph import StateGraph\n"
        "from workflows.session.registry import register_session_dag\n"
        "def build():\n"
        "    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    assert validate_langgraph(bad)["status"] == "FAIL"


def test_validate_package_compile_only_fails(tmp_path):
    pkg = tmp_path / "compile_only"
    pkg.mkdir()
    (pkg / "graph.py").write_text(
        "from langgraph.graph import StateGraph\ndef build():\n    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    (pkg / "executor.py").write_text(
        "from workflows.dags.x.graph import build\n\n"
        "def compile_graph():\n"
        "    return build().compile()\n",
        encoding="utf-8",
    )
    result = validate_package(pkg)
    assert result["status"] == "FAIL"
    assert result["persistence_class"] == "none"
    assert "missing_durable_checkpointer" in result["errors"]


def test_validate_package_memory_saver_fails(tmp_path):
    pkg = tmp_path / "ephemeral"
    pkg.mkdir()
    (pkg / "graph.py").write_text(
        "from langgraph.graph import StateGraph\ndef build():\n    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    (pkg / "executor.py").write_text(
        "from langgraph.checkpoint.memory import MemorySaver\n"
        "from workflows.dags.x.graph import build\n\n"
        "def compile_graph():\n"
        "    return build().compile(checkpointer=MemorySaver())\n",
        encoding="utf-8",
    )
    result = validate_package(pkg)
    assert result["status"] == "FAIL"
    assert result["persistence_class"] == "ephemeral"
    assert "ephemeral_checkpointer" in result["errors"]


def test_command_validator(tmp_path):
    f = tmp_path / "cmd.md"
    f.write_text(
        "---\ndag: x\ndag_file: workflows/dags/x_dag.py\n---\n# /x\nTrigger only.\n",
        encoding="utf-8",
    )
    assert validate_command(f, "x")["status"] == "PASS"


def test_command_rejects_legacy_path(tmp_path):
    f = tmp_path / "cmd.md"
    f.write_text(
        "---\ndag: x\ndag_file: .cursor-commands/workflows/dags/x_dag.py\n---\n", encoding="utf-8"
    )
    assert validate_command(f, "x")["status"] == "FAIL"


def test_receipt_renderer(tmp_path):
    out = tmp_path / "receipt.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "render_receipt.py"),
            "--operation",
            "VALIDATE",
            "--status",
            "PASS",
            "--dag-id",
            "x",
            "--check",
            "structure",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["skill"] == "l9-dag-authoring"
    assert data["version"] == "2.3.0"
    assert data["status"] == "PASS"
    assert data.get("persistence_class") is None


def test_ownership_policy_contains_sprawl_guard():
    text = (PACK / "policies" / "ownership-boundary.yaml").read_text(encoding="utf-8")
    assert "no_new_skill_solely_because_a_dag_exists" in text
    assert "l9-update-command" in text
    kinds = (PACK / "policies" / "graph-kinds.yaml").read_text(encoding="utf-8")
    assert "SESSION_GUIDANCE" in kinds and "LANGGRAPH_RUNTIME" in kinds
    assert "deprecated_pending_convert" in kinds
    assert "convert_disposition_classification" in text
    catalog = (PACK / "policies" / "session-deprecation.yaml").read_text(encoding="utf-8")
    assert "intelligence-harvest-v1" in catalog
    assert "CONVERT_TO_LANGGRAPH" in catalog


def test_convert_request_and_receipt(tmp_path):
    fixture = json.loads((PACK / "fixtures" / "convert_langgraph.json").read_text(encoding="utf-8"))
    fixture["repo_root"] = str(REPO)
    assert validate_request(fixture) == []
    unknown = json.loads((PACK / "fixtures" / "convert_unknown.json").read_text(encoding="utf-8"))
    unknown["repo_root"] = str(REPO)
    assert validate_request(unknown) == []
    out = tmp_path / "receipt.json"
    subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "render_receipt.py"),
            "--operation",
            "CONVERT",
            "--status",
            "PASS",
            "--dag-id",
            "intelligence-harvest-v1",
            "--disposition",
            "CONVERT_TO_LANGGRAPH",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "2.3.0"
    assert data["disposition"] == "CONVERT_TO_LANGGRAPH"


def test_classifier_catalog_dispositions():
    twin = classify_request(REPO, "gmp-execution-v1")
    assert twin["status"] == "PASS"
    assert twin["disposition"] == "DELETE_TWIN"
    absorb = classify_request(REPO, "dag-authoring-v1")
    assert absorb["status"] == "PASS"
    assert absorb["disposition"] == "ABSORB_INTO_SKILL"
    convert_row = classify_request(REPO, "intelligence-harvest-v1")
    assert convert_row["disposition"] == "CONVERT_TO_LANGGRAPH"
    assert convert_row["status"] in {"PASS", "BLOCKED"}
    if convert_row["status"] == "BLOCKED":
        assert convert_row["reason"] == "twin_StateGraph_already_exists"
    summary = classify_all(REPO)
    assert summary["convert_to_langgraph_count"] == 1
    unknown = classify_request(REPO, "not-a-catalog-id")
    assert unknown["status"] == "BLOCKED"
    assert unknown["reason"] == "unknown_catalog_id"
    langgraph_source = classify(PACK / "fixtures" / "convert_langgraph_source.py")
    assert langgraph_source["graph_kind"] == "LANGGRAPH_RUNTIME"


def test_converter_refuses_non_convert_and_prose(tmp_path):
    refused = convert(REPO, dag_id="gmp-execution-v1")
    assert refused["status"] == "FAIL"
    assert refused["disposition"] == "DELETE_TWIN"
    prose = convert(
        REPO,
        dag_id="prose-convert-fixture",
        disposition="CONVERT_TO_LANGGRAPH",
        source=PACK / "fixtures" / "convert_prose_action.py",
        emit_dir=tmp_path / "prose",
    )
    assert prose["status"] == "FAIL"
    assert prose["reason"] == "prose_action_refused"


def test_converter_emits_script_session(tmp_path):
    out = tmp_path / "ok_graph"
    result = convert(
        REPO,
        dag_id="fixture-convert-ok",
        disposition="CONVERT_TO_LANGGRAPH",
        source=PACK / "fixtures" / "convert_ok_session.py",
        emit_dir=out,
    )
    assert result["status"] == "PASS"
    assert (out / "graph.py").is_file()
    assert validate_langgraph(out / "graph.py")["status"] == "PASS"
    package = validate_package(out)
    assert package["status"] == "PASS"
    assert package["persistence_class"] == "durable"
    text = (out / "graph.py").read_text(encoding="utf-8")
    assert "register_session_dag" not in text
    executor = (out / "executor.py").read_text(encoding="utf-8")
    assert "register_session_dag" not in executor
    assert "checkpointer=" in executor
    assert "thread_id" in executor
    assert "invoke(None, config)" in executor
    assert "self.compiled.invoke(payload, config)" not in executor


def test_validate_package_none_checkpointer_fails(tmp_path):
    pkg = tmp_path / "none_saver"
    pkg.mkdir()
    (pkg / "graph.py").write_text(
        "from langgraph.graph import StateGraph\ndef build():\n    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    (pkg / "executor.py").write_text(
        "from workflows.dags.x.graph import build\n\n"
        "def compile_graph():\n"
        "    return build().compile(checkpointer=None)\n",
        encoding="utf-8",
    )
    result = validate_package(pkg)
    assert result["status"] == "FAIL"
    assert result["persistence_class"] == "none"
    assert "missing_durable_checkpointer" in result["errors"]


def test_validate_package_unknown_checkpointer_fails(tmp_path):
    pkg = tmp_path / "unknown_saver"
    pkg.mkdir()
    (pkg / "graph.py").write_text(
        "from langgraph.graph import StateGraph\ndef build():\n    return StateGraph(dict)\n",
        encoding="utf-8",
    )
    (pkg / "executor.py").write_text(
        "from workflows.dags.x.graph import build\n\n"
        "def compile_graph(saver):\n"
        "    return build().compile(checkpointer=saver)\n",
        encoding="utf-8",
    )
    result = validate_package(pkg)
    assert result["status"] == "FAIL"
    assert result["persistence_class"] == "none"
    assert "missing_durable_checkpointer" in result["errors"]
