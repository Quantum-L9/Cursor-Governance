"""FAIL receipt parser, refuse message, and afterShellExecution payload."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HELPER = ROOT / "ops" / "scripts" / "pr_gate_failure.py"
HOOK = ROOT / "ops" / "hooks" / "pr_gate_failure_shell.sh"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("pr_gate_failure", HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = _load()


def test_parse_failed_nodes_and_hooks() -> None:
    log = "\n".join(
        [
            "FAILED tests/test_run_campaign.py::T::test_until_activate_from_memo",
            "FAILED tests/test_validate.py::T::test_repository_promotion_is_valid",
            "- hook id: ruff-format",
            "- files were modified by this hook",
            "- hook id: ruff",
            "- exit code: 1",
        ]
    )
    nodes = mod.parse_failed_nodes(log)
    assert nodes[0].endswith("test_until_activate_from_memo")
    assert nodes[1].endswith("test_repository_promotion_is_valid")
    assert mod.parse_failed_hooks(log) == ["ruff"]


def test_refuse_prints_stop_looping(tmp_path: Path) -> None:
    path = tmp_path / "gate-failure.json"
    digest = "abc 123 origin/main"
    path.write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v2",
                "paths_digest": "abc",
                "content_digest": "123",
                "pr_base": "origin/main",
                "failed_nodes": ["tests/x.py::test_x"],
                "failed_hooks": [],
                "recheck_command": ".venv/bin/pytest tests/x.py::test_x",
                "message": "STOP LOOPING",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["python3", str(HELPER), "refuse", str(path), digest],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "STOP LOOPING" in proc.stdout
    assert "tests/x.py::test_x" in proc.stdout
    assert ".venv/bin/pytest tests/x.py::test_x" in proc.stdout


def test_refuse_miss_is_zero(tmp_path: Path) -> None:
    path = tmp_path / "gate-failure.json"
    path.write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v2",
                "paths_digest": "abc",
                "content_digest": "123",
                "pr_base": "origin/main",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["python3", str(HELPER), "refuse", str(path), "abc 999 origin/main"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_after_shell_emits_stop_looping(tmp_path: Path) -> None:
    receipt = tmp_path / ".l9" / "pr" / "gate-failure.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v2",
                "paths_digest": "h",
                "content_digest": "d",
                "pr_base": "origin/main",
                "failed_nodes": ["tests/x.py::test_x"],
                "failed_hooks": [],
                "recheck_command": ".venv/bin/pytest tests/x.py::test_x",
                "message": "STOP LOOPING",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = json.dumps(
        {
            "command": "PR_REMEDIATE=0 make -C /tmp/gov pr WS=/tmp/ws",
            "cwd": str(tmp_path),
            "exitCode": 1,
        }
    )
    proc = subprocess.run(
        ["python3", str(HELPER), "after-shell"],
        check=False,
        capture_output=True,
        text=True,
        input=payload,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert "STOP LOOPING" in doc["additional_context"]
    assert "STOP LOOPING" in doc["agent_message"]
    assert "tests/x.py::test_x" in doc["additional_context"]
    assert "do not AwaitShell another make pr" in doc["agent_message"]


def test_after_shell_fail_open_without_receipt(tmp_path: Path) -> None:
    payload = json.dumps({"command": "make pr", "cwd": str(tmp_path), "exitCode": 1})
    proc = subprocess.run(
        ["python3", str(HELPER), "after-shell"],
        check=False,
        capture_output=True,
        text=True,
        input=payload,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {}


def test_hook_script_fail_open_without_receipt(tmp_path: Path) -> None:
    payload = json.dumps({"command": "make pr-check", "cwd": str(tmp_path), "exitCode": 2})
    proc = subprocess.run(
        ["bash", str(HOOK)],
        check=False,
        capture_output=True,
        text=True,
        input=payload,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {}


def _receipt(path: Path, *, head_sha: str | None) -> str:
    """A FAIL receipt naming a hook rewrite, as run_pr_gate.sh writes one."""

    doc = {
        "schema": "l9.pr_gate_failure.v2",
        "paths_digest": "abc",
        "content_digest": "123",
        "pr_base": "origin/main",
        "failed_nodes": [],
        "failed_hooks": ["end-of-file-fixer"],
        "recheck_command": "",
        "message": "STOP LOOPING",
    }
    if head_sha is not None:
        doc["head_sha"] = head_sha
    path.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    return "abc 123 origin/main"


def _refuse(path: Path, digest: str, *, head_sha: str | None) -> subprocess.CompletedProcess[str]:
    argv = ["python3", str(HELPER), "refuse", str(path), digest]
    if head_sha is not None:
        argv += ["--head-sha", head_sha]
    return subprocess.run(argv, check=False, capture_output=True, text=True)


def test_refuse_still_blocks_when_head_is_unchanged(tmp_path: Path) -> None:
    """The loop-breaker must keep refusing a genuinely unchanged tree."""

    path = tmp_path / "gate-failure.json"
    digest = _receipt(path, head_sha="deadbeef")
    proc = _refuse(path, digest, head_sha="deadbeef")
    assert proc.returncode == 2
    assert "STOP LOOPING" in proc.stdout


def test_committing_a_hook_rewrite_releases_the_loop_breaker(tmp_path: Path) -> None:
    """Regression: the gate's own instruction must be reachable.

    A pre-commit hook rewrites a tracked file *before* the receipt is written,
    so the receipt already holds the rewritten bytes. The gate then says
    "commit the rewrite, then re-run". Committing moves HEAD but leaves the
    working tree byte-identical, so the content digest still matches. Without a
    recorded head sha the loop-breaker refused that instructed re-run forever,
    and the only escape was deleting the receipt by hand.
    """

    path = tmp_path / "gate-failure.json"
    digest = _receipt(path, head_sha="head-before-commit")
    proc = _refuse(path, digest, head_sha="head-after-commit")
    assert proc.returncode == 0, "committing the rewrite must release the loop-breaker"
    assert "STOP LOOPING" not in proc.stdout


def test_legacy_receipt_without_head_sha_keeps_digest_only_behavior(tmp_path: Path) -> None:
    """A receipt from before this change must be no weaker than it was."""

    path = tmp_path / "gate-failure.json"
    digest = _receipt(path, head_sha=None)
    assert _refuse(path, digest, head_sha="any-head").returncode == 2
    assert _refuse(path, digest, head_sha=None).returncode == 2


def test_content_change_still_releases_regardless_of_head(tmp_path: Path) -> None:
    path = tmp_path / "gate-failure.json"
    _receipt(path, head_sha="same-head")
    proc = _refuse(path, "different 456 origin/main", head_sha="same-head")
    assert proc.returncode == 0
