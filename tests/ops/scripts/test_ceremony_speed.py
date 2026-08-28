"""Ceremony speed: local xdist injection, fetch-receipt reuse, security list reuse."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
LIB = SCRIPTS / "lib" / "fetch_receipt.sh"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_python_test_suites import (  # noqa: E402
    REGISTRY_PATH,
    _load_json,
    local_changed_file_xdist_args,
    validate_registry,
)


def _run(
    args: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


def git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git_in(repo, "add", "README.md")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    git_in(repo, "update-ref", "refs/remotes/origin/main", sha)
    return repo


def _source_lib(
    script: str, *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return _run(
        ["bash", "-c", f"source '{LIB}' && {script}"],
        cwd=cwd,
        env=env,
    )


def test_local_xdist_two_files_injects() -> None:
    args = local_changed_file_xdist_args(
        "local",
        ["tests/ops/scripts/test_a.py", "tests/ops/scripts/test_b.py"],
        ["-q"],
    )
    assert args == ["-n", "auto"]


def test_local_xdist_one_file_stays_serial() -> None:
    args = local_changed_file_xdist_args(
        "local",
        ["tests/ops/scripts/test_a.py"],
        ["-q"],
    )
    assert args == []


def test_local_xdist_ci_profile_does_not_inject() -> None:
    args = local_changed_file_xdist_args(
        "ci",
        ["tests/a.py", "tests/b.py"],
        [],
    )
    assert args == []


def test_local_xdist_respects_existing_dash_n() -> None:
    args = local_changed_file_xdist_args(
        "local",
        ["tests/a.py", "tests/b.py"],
        ["-n", "1"],
    )
    assert args == []


def test_local_xdist_none_scoped_is_noop() -> None:
    assert local_changed_file_xdist_args("local", None, ["-q"]) == []


def test_ci_profile_argv_still_declares_xdist() -> None:
    registry = _load_json(REGISTRY_PATH)
    suites = validate_registry(registry)
    root = next(item for item in suites if item["id"] == "repo-root")
    assert "-n" in root["profiles"]["ci"]["argv"]
    assert "-n" not in root["profiles"]["local"]["argv"]


def test_command_sequence_suites_do_not_append_user_args() -> None:
    registry = _load_json(REGISTRY_PATH)
    suites = validate_registry(registry)
    seq = [item for item in suites if item["kind"] == "command_sequence"]
    assert seq
    assert all(not item["append_user_pytest_args"] for item in seq)


def test_fetch_receipt_reusable_when_fresh_and_sha_matches(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "refs/remotes/origin/main"], text=True
    ).strip()
    proc = _source_lib(
        f'fetch_receipt_write "{repo}" main "{sha}" && fetch_receipt_reusable "{repo}" main',
        cwd=repo,
        env={"FETCH_RECEIPT_TTL_S": "60"},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    receipt = json.loads((repo / ".l9/pr/fetch-receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema"] == "l9.fetch_receipt.v1"
    assert receipt["fetched_sha"] == sha
    assert receipt["base_ref"] == "main"


def test_fetch_receipt_stale_is_not_reusable(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    sha = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "refs/remotes/origin/main"], text=True
    ).strip()
    stale = (
        (datetime.now(UTC) - timedelta(seconds=120))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    path = repo / ".l9/pr/fetch-receipt.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema": "l9.fetch_receipt.v1",
                "base_ref": "main",
                "fetched_sha": sha,
                "fetched_at": stale,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _source_lib(
        f'fetch_receipt_reusable "{repo}" main',
        cwd=repo,
        env={"FETCH_RECEIPT_TTL_S": "60"},
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_fetch_receipt_sha_mismatch_is_not_reusable(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    path = repo / ".l9/pr/fetch-receipt.json"
    path.parent.mkdir(parents=True)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path.write_text(
        json.dumps(
            {
                "schema": "l9.fetch_receipt.v1",
                "base_ref": "main",
                "fetched_sha": "0" * 40,
                "fetched_at": now,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _source_lib(
        f'fetch_receipt_reusable "{repo}" main',
        cwd=repo,
        env={"FETCH_RECEIPT_TTL_S": "60"},
    )
    assert proc.returncode == 1


def test_open_pr_script_reuses_fetch_receipt() -> None:
    text = (SCRIPTS / "open_pr_after_gate.sh").read_text(encoding="utf-8")
    assert "fetch_receipt_reusable" in text
    assert 'git fetch origin "$BASE_REF"' in text


def test_security_skips_resolve_when_pr_changed_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    listed = tmp_path / "changed.txt"
    listed.write_text("README.md\n", encoding="utf-8")
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_security.sh"), "--mode", "advisory", str(repo)],
        cwd=repo,
        env={
            "WS": str(repo),
            "PR_CHANGED_FILE": str(listed),
            "PR_SECURITY_ADVISORY": "1",
        },
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out
    assert "skip resolve_changed_files.sh (PR_CHANGED_FILE)" in out
    assert "SOURCE:" not in out


def test_gate_script_records_timing_keys() -> None:
    text = (SCRIPTS / "run_pr_gate.sh").read_text(encoding="utf-8")
    assert "gate-timing.json" in text
    assert "digest_ms" in text
    assert "writers_ms" in text
    assert "fetch_ms" in text
    assert "total_ms" in text
    assert 'PR_CHANGED_FILE="$changed_file"' in text
    assert "fetch_receipt_reusable" in text
    assert "--pe-manifest" in text
    assert "# Heal missing gitignored .cursor links" in text
    assert 'L9_WIRE_LINKS_ONLY=1 bash "$GOV_ROOT/ops/scripts/ensure_workspace_wired.sh"' in text
    assert ".meta" in text
