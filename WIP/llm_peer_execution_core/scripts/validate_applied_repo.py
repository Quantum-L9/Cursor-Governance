#!/usr/bin/env python3
"""Run deterministic PR gates after applying the pack to Cursor-Governance."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_SHA = "0fbd477e507d33ee52f2a87c2d9eb77c15b6a492"
EXPECTED_RUFF_VERSION = "ruff 0.16.0"
COMMAND_TIMEOUT_SECONDS = 300


def run(
    repo: Path,
    name: str,
    argv: list[str],
    env: dict[str, str] | None = None,
    *,
    timeout_seconds: int = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        result = subprocess.run(
            argv,
            cwd=repo,
            env=merged,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "argv": argv,
            "returncode": 124,
            "stdout": str(exc.stdout or "")[-12000:],
            "stderr": f"timed out after {timeout_seconds}s",
            "status": "FAIL",
        }
    return {
        "name": name,
        "argv": argv,
        "returncode": result.returncode,
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-12000:],
        "status": "PASS" if result.returncode == 0 else "FAIL",
    }


def _untracked_files(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=repo,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError("git ls-files failed while collecting untracked files")
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def _changed_python_files(repo: Path, untracked: list[str]) -> list[str]:
    tracked = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMRT",
            BASE_SHA,
            "--",
            "*.py",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if tracked.returncode != 0:
        raise RuntimeError("git diff failed while collecting changed Python files")
    paths = {line.strip() for line in tracked.stdout.splitlines() if line.strip()}
    paths.update(path for path in untracked if path.endswith(".py"))
    return sorted(path for path in paths if (repo / path).is_file())


def _ruff_executable(repo: Path) -> str | None:
    local = repo / ".venv/bin/ruff"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    return shutil.which("ruff")


def ruff_gates(repo: Path, changed_python: list[str]) -> list[dict[str, Any]]:
    executable = _ruff_executable(repo)
    if executable is None:
        reason = "ruff 0.16.0 is unavailable in the validation environment"
        return [
            {
                "name": "ruff_version",
                "argv": ["ruff", "--version"],
                "returncode": None,
                "stdout": "",
                "stderr": reason,
                "status": "SKIPPED",
            },
            {
                "name": "ruff_check_changed_python",
                "argv": ["ruff", "check", "<changed-python>"],
                "returncode": None,
                "stdout": "",
                "stderr": reason,
                "status": "SKIPPED",
                "changed_python_files": len(changed_python),
            },
            {
                "name": "ruff_format_check_changed_python",
                "argv": ["ruff", "format", "--check", "<changed-python>"],
                "returncode": None,
                "stdout": "",
                "stderr": reason,
                "status": "SKIPPED",
                "changed_python_files": len(changed_python),
            },
        ]

    version = run(repo, "ruff_version", [executable, "--version"], timeout_seconds=30)
    if version["status"] == "PASS" and version["stdout"].strip() != EXPECTED_RUFF_VERSION:
        version["status"] = "FAIL"
        version["stderr"] = (
            f"expected {EXPECTED_RUFF_VERSION!r}, observed {version['stdout'].strip()!r}"
        )
    if version["status"] != "PASS":
        return [version]
    if not changed_python:
        return [
            version,
            {
                "name": "ruff_changed_python",
                "argv": [executable, "<changed-python>"],
                "returncode": 0,
                "stdout": "no changed Python files",
                "stderr": "",
                "status": "PASS",
                "changed_python_files": 0,
            },
        ]
    check = run(repo, "ruff_check_changed_python", [executable, "check", *changed_python])
    check["changed_python_files"] = len(changed_python)
    format_check = run(
        repo,
        "ruff_format_check_changed_python",
        [executable, "format", "--check", *changed_python],
    )
    format_check["changed_python_files"] = len(changed_python)
    return [version, check, format_check]


def _overall_status(base_match: bool, results: list[dict[str, Any]]) -> str:
    if not base_match or any(item["status"] == "FAIL" for item in results):
        return "FAIL"
    if any(item["status"] == "UNKNOWN" for item in results):
        return "UNKNOWN"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.expanduser().resolve()
    pe = repo / "environment/program-execution"
    python = sys.executable
    gates = [
        (
            "thin_provider_conformance",
            [python, "-B", str(pe / "scripts/validate_thin_providers.py")],
            {"PYTHONPATH": str(pe), "PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "program_execution_adapter_validation",
            [python, "-B", str(pe / "scripts/validate_execution_adapters.py")],
            {"PYTHONPATH": str(pe), "PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "program_execution_conformance",
            [python, "-B", str(pe / "scripts/run_conformance.py")],
            {"PYTHONPATH": str(pe), "PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "peer_binding_schema",
            [
                python,
                "-B",
                "environment/agents/tools/validate_executable_peers.py",
                "--schema-only",
            ],
            {"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "peer_execution_structure",
            [python, "-B", "environment/agents/tools/validate_executable_peers.py"],
            {"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "autonomy_contracts",
            [python, "-B", "ops/scripts/validate_autonomy_contracts.py"],
            {"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "shared_bounded_autonomy",
            [
                python,
                "-B",
                "environment/program-execution/peer_execution/autonomy/validate_autonomy.py",
            ],
            {"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "program_execution_manifest",
            [python, "-B", str(pe / "scripts/validate_manifest.py")],
            {"PYTHONDONTWRITEBYTECODE": "1"},
        ),
        (
            "task_pipeline_cli_loads",
            [python, "-B", str(pe / "scripts/run_peer_task_pipeline.py"), "--help"],
            {"PYTHONPATH": str(pe), "PYTHONDONTWRITEBYTECODE": "1"},
        ),
    ]
    results = [run(repo, name, argv, env) for name, argv, env in gates]
    results.append(
        run(
            repo,
            "git_diff_check_tracked",
            ["git", "diff", "--check", BASE_SHA, "--"],
            timeout_seconds=60,
        )
    )

    untracked = _untracked_files(repo)
    untracked_errors: list[str] = []
    for rel in sorted(untracked):
        checked = subprocess.run(
            ["git", "diff", "--no-index", "--check", "--", "/dev/null", rel],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if checked.returncode not in {0, 1}:
            untracked_errors.append(
                f"{rel}: {checked.stdout[-2000:]}{checked.stderr[-2000:]}"
            )
    results.append(
        {
            "name": "git_diff_check_untracked",
            "argv": ["git", "diff", "--no-index", "--check", "/dev/null", "<untracked>"],
            "returncode": 0 if not untracked_errors else 1,
            "stdout": "\n".join(untracked_errors),
            "stderr": "",
            "status": "PASS" if not untracked_errors else "FAIL",
            "untracked_files_checked": len(untracked),
        }
    )

    changed_python = _changed_python_files(repo, untracked)
    # Static checker is best-effort. Missing Ruff is reported as SKIPPED.
    results.extend(ruff_gates(repo, changed_python))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    ).stdout.strip()
    base_match = head == BASE_SHA
    report = {
        "schema": "l9.peer-execution.pr-pack-validation.v2",
        "bound_repository": "Quantum-L9/Cursor-Governance",
        "bound_base_sha": BASE_SHA,
        "observed_head": head,
        "base_match": base_match,
        "status": _overall_status(base_match, results),
        "gates": results,
        "live_peer_probe": "NOT_RUN_ENVIRONMENT_DEPENDENT",
        "remote_mutation": "NONE",
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output.expanduser().resolve()
        if output.is_symlink():
            raise RuntimeError(f"refusing symlinked validation output: {output}")
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    if report["status"] == "PASS":
        return 0
    if report["status"] == "UNKNOWN":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
