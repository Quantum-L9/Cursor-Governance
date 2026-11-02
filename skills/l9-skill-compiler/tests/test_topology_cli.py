"""SCAN_SKILL_TOPOLOGY command line: usage, request validation, decision output."""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "scan_skill_topology.py")
FIX = os.path.join(HERE, "fixtures", "repo", "skills")


def run(*args):
    return subprocess.run(
        [sys.executable, SCRIPT, *args], capture_output=True, text=True, check=False
    )


def write(tmp_path, payload):
    path = tmp_path / "request.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return str(path)


def test_help_prints_usage_and_contract():
    proc = run("--help")
    assert proc.returncode == 0
    assert "usage: scan_skill_topology.py" in proc.stdout
    assert "references/topology-scan.md" in proc.stdout
    assert "Traceback" not in proc.stderr


def test_missing_request_fails_cleanly(tmp_path):
    proc = run(str(tmp_path / "absent.json"))
    assert proc.returncode == 2
    assert "cannot read request" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_invalid_json_fails_cleanly(tmp_path):
    proc = run(write(tmp_path, "{not json"))
    assert proc.returncode == 2
    assert "not valid JSON" in proc.stderr


def test_request_without_subject_mapping_fails(tmp_path):
    proc = run(write(tmp_path, {"proposed_name": "x"}))
    assert proc.returncode == 2
    assert "`subject` mapping" in proc.stderr


def test_non_string_subject_field_fails(tmp_path):
    proc = run(write(tmp_path, {"subject": {"proposed_name": ["l9-x"]}}))
    assert proc.returncode == 2
    assert "proposed_name" in proc.stderr


def test_valid_request_emits_a_decision(tmp_path):
    request = write(
        tmp_path,
        {"subject": {"proposed_name": "l9-skill-compiler", "existing_skill": "l9-skill-compiler"}},
    )
    proc = run(request, FIX)
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["stage"] == "SCAN_SKILL_TOPOLOGY"
    assert doc["decision"] == "REPLACE_EXISTING"
    assert doc["decided_by"] == "deterministic_rule"
    assert isinstance(doc["candidates"], list)
