# ruff: noqa: E402
import json
import subprocess
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SCRIPTS = PACK / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_command_trigger import validate as validate_command
from validate_request import validate as validate_request
from validate_session_dag_source import validate as validate_dag


def test_request_contract():
    assert validate_request({"operation": "CREATE", "repo_root": "/tmp"}) == []
    assert validate_request({"operation": "BOGUS", "repo_root": "/tmp"})


def test_dag_validator_canonical(tmp_path):
    f = tmp_path / "x.py"
    f.write_text(
        "from workflows.session.interface import SessionDAG, SessionNode, SessionEdge\n"
        "from workflows.session.registry import register_session_dag\n"
        "X_DAG=SessionDAG(id='x',name='X',version='1',description='x',nodes=[SessionNode(id='start')],edges=[])\n"
        "register_session_dag(X_DAG)\n",
        encoding="utf-8",
    )
    assert validate_dag(f)["status"] == "PASS"


def test_dag_validator_rejects_unregistered(tmp_path):
    f = tmp_path / "x.py"
    f.write_text(
        "from workflows.session.interface import SessionDAG\nX=SessionDAG(id='x')\n",
        encoding="utf-8",
    )
    assert validate_dag(f)["status"] == "FAIL"


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
    assert data["status"] == "PASS"


def test_ownership_policy_contains_sprawl_guard():
    text = (PACK / "policies" / "ownership-boundary.yaml").read_text(encoding="utf-8")
    assert "no_new_skill_solely_because_a_dag_exists" in text
    assert "l9-update-command" in text
