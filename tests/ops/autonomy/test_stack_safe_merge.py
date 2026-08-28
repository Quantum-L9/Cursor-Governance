"""stack_safe_merge.py must never emit --squash for a stack parent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HELPER = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "stack_safe_merge.py"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from stack_safe_merge import _execute, merge_argv, select_merge_method  # noqa: E402


def _probe(tmp_path: Path, entries: dict) -> str:
    path = tmp_path / "stack-probe.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return str(path)


def _env(tmp_path: Path, entries: dict) -> dict[str, str]:
    env = {**os.environ, "L9_STACK_PROBE_FILE": _probe(tmp_path, entries)}
    return env


STACKED = {"Quantum-L9/SEO-Bot#53": {"head": "fix/parent", "children": [54]}}
LEAF = {"Quantum-L9/SEO-Bot#53": {"head": "fix/leaf", "children": []}}


def test_parent_selects_merge_commit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, STACKED))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    assert chosen["method"] == "merge"
    assert chosen["children"] == [54]
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", selection=chosen)
    assert "--merge" in argv
    assert "--squash" not in argv


def test_leaf_selects_squash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, LEAF))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    assert chosen["method"] == "squash"
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", selection=chosen)
    assert "--squash" in argv
    assert "--merge" not in argv


def test_cli_print_parent_never_names_squash(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(HELPER), "--repo", "Quantum-L9/SEO-Bot", "--pr", "53", "--print"],
        capture_output=True,
        text=True,
        env=_env(tmp_path, STACKED),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--merge" in proc.stdout
    assert "--squash" not in proc.stdout


def test_cli_json_leaf_is_squash(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(HELPER), "--repo", "Quantum-L9/SEO-Bot", "--pr", "53", "--json"],
        capture_output=True,
        text=True,
        env=_env(tmp_path, LEAF),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["method"] == "squash"
    assert "--squash" in payload["argv"]


def test_parent_omits_delete_branch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, STACKED))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", delete_branch=True, selection=chosen)
    assert "--delete-branch" not in argv
    assert chosen["children"] == [54]


def test_leaf_keeps_delete_branch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, LEAF))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", delete_branch=True, selection=chosen)
    assert "--delete-branch" in argv


def test_execute_parent_skips_delete_ref(monkeypatch) -> None:
    runs: list[list[str]] = []

    def _capture(argv: list[str]) -> int:
        runs.append(argv)
        return 0

    monkeypatch.setattr("stack_safe_merge._run", _capture)
    selection = {
        "repo": "Quantum-L9/SEO-Bot",
        "pr": 53,
        "method": "merge",
        "head": "fix/parent",
        "children": [54],
    }
    assert _execute(selection, delete_branch=True) == 0
    joined = [" ".join(argv) for argv in runs]
    assert not any("DELETE" in line and "refs/heads/" in line for line in joined)
    assert any("pulls/53/merge" in line for line in joined)
