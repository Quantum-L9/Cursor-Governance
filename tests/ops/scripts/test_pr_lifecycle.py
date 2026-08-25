"""Capability-graph PR lifecycle: improve, preflight, soft-empty, gate receipt."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
L4 = ROOT / "ops" / "autonomy" / "l4_local.py"


def git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(tmp_path: Path, *, feature: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / ".gitignore").write_text(".l9/\n", encoding="utf-8")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git_in(repo, "add", ".gitignore", "README.md")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    git_in(repo, "branch", "origin-main")
    if feature:
        git_in(repo, "checkout", "-b", "feat/stack")
        (repo / "a.txt").write_text("a\n", encoding="utf-8")
        git_in(repo, "add", "a.txt")
        git_in(repo, "commit", "-m", "local work")
    return repo


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


def test_resolver_empty_fails_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=False)
    proc = _run(
        ["bash", str(SCRIPTS / "resolve_changed_files.sh")],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "PR_ALLOW_EMPTY": "0"},
    )
    assert proc.returncode == 1
    assert "empty change set" in proc.stderr


def test_resolver_empty_soft_pass(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=False)
    proc = _run(
        ["bash", str(SCRIPTS / "resolve_changed_files.sh")],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "PR_ALLOW_EMPTY": "1"},
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert "SOURCE:empty" in proc.stderr


def test_preflight_fails_on_main(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=False)
    proc = _run(
        ["bash", str(SCRIPTS / "pr_preflight.sh"), str(repo)],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert proc.returncode == 1
    assert "main" in proc.stderr or "main" in proc.stdout


def test_preflight_fails_without_l4(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    proc = _run(
        ["bash", str(SCRIPTS / "pr_preflight.sh"), str(repo)],
        cwd=repo,
        env={"PR_BASE": "main", "WS": str(repo), "L9_L4_LOCAL_AUTONOMY": "1"},
    )
    assert proc.returncode == 1
    assert "make improve" in proc.stderr


def test_preflight_passes_after_authorize(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    env = {"L9_L4_LOCAL_AUTONOMY": "1", "WS": str(repo), "PR_BASE": "main"}
    assert (
        _run(["python3", str(L4), "--workspace", str(repo), "begin"], cwd=repo, env=env).returncode
        == 0
    )
    assert (
        _run(
            ["python3", str(L4), "--workspace", str(repo), "record-kernels"],
            cwd=repo,
            env=env,
        ).returncode
        == 0
    )
    assert (
        _run(
            ["python3", str(L4), "--workspace", str(repo), "authorize-release"],
            cwd=repo,
            env=env,
        ).returncode
        == 0
    )
    proc = _run(
        ["bash", str(SCRIPTS / "pr_preflight.sh"), str(repo)],
        cwd=repo,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK: pr-preflight" in proc.stdout


def test_improve_record_refused_without_phase(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    proc = _run(
        ["bash", str(SCRIPTS / "run_improve.sh")],
        cwd=repo,
        env={"WS": str(repo), "IMPROVE_RECORD": "1", "PR_BASE": "main"},
    )
    assert proc.returncode == 1
    assert "IMPROVE_RECORD refused" in proc.stderr


def test_improve_begin_then_record(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    env = {"WS": str(repo), "PR_BASE": "main", "IMPROVE_RECORD": "0"}
    begin = _run(["bash", str(SCRIPTS / "run_improve.sh")], cwd=repo, env=env)
    assert begin.returncode == 0, begin.stderr
    assert "L9_AGENT_REQUIRED" in begin.stdout
    rec = _run(
        ["bash", str(SCRIPTS / "run_improve.sh")],
        cwd=repo,
        env={**env, "IMPROVE_RECORD": "1"},
    )
    assert rec.returncode == 0, rec.stderr
    receipt = json.loads((repo / ".l9" / "autonomy" / "l4-release-receipt.json").read_text())
    assert receipt["phase"] == "release_authorized"


def test_gate_receipt_skip_on_unchanged_state(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    digest = subprocess.check_output(
        ["bash", "-c", "git status --porcelain | cksum | awk '{print $1}'"],
        cwd=str(repo),
        text=True,
    ).strip()
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-receipt.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_receipt.v1",
                "head": head,
                "worktree_digest": digest,
                "pr_base": "main",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_gate.sh")],
        cwd=repo,
        env={"WS": str(repo), "PR_BASE": "main", "PR_LOCK_WAIT_S": "1"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "receipt reuse" in proc.stdout


def _state_digest(repo: Path, pr_base: str = "main") -> tuple[str, str]:
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    digest = subprocess.check_output(
        ["bash", "-c", "git status --porcelain | cksum | awk '{print $1}'"],
        cwd=str(repo),
        text=True,
    ).strip()
    return head, digest


def test_gate_failure_receipt_refuses_second_full_gate(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    head, digest = _state_digest(repo)
    node = (
        "environment/program-execution/scripts/tests/test_run_campaign.py::"
        "RunCampaignTests::test_until_activate_from_memo"
    )
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-failure.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v1",
                "head": head,
                "worktree_digest": digest,
                "pr_base": "main",
                "failed_nodes": [node],
                "failed_hooks": [],
                "recheck_command": f".venv/bin/pytest {node}",
                "message": "STOP LOOPING",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_gate.sh")],
        cwd=repo,
        env={"WS": str(repo), "PR_BASE": "main", "PR_LOCK_WAIT_S": "1"},
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode == 2, output
    assert "STOP LOOPING" in output
    assert node in output
    assert "governance contract surface" not in output
    assert "===== test session starts" not in output


def test_gate_pass_receipt_wins_over_stale_failure(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    head, digest = _state_digest(repo)
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    payload = {"head": head, "worktree_digest": digest, "pr_base": "main"}
    (receipt_dir / "gate-receipt.json").write_text(
        json.dumps({"schema": "l9.pr_gate_receipt.v1", **payload}) + "\n",
        encoding="utf-8",
    )
    (receipt_dir / "gate-failure.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v1",
                **payload,
                "failed_nodes": ["tests/x.py::test_x"],
                "failed_hooks": [],
                "recheck_command": "pytest tests/x.py::test_x",
                "message": "STOP LOOPING",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_gate.sh")],
        cwd=repo,
        env={"WS": str(repo), "PR_BASE": "main", "PR_LOCK_WAIT_S": "1"},
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "receipt reuse" in proc.stdout
    assert "STOP LOOPING" not in proc.stdout


def test_gate_failure_receipt_clears_when_digest_changes(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    head, digest = _state_digest(repo)
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-failure.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v1",
                "head": head,
                "worktree_digest": digest,
                "pr_base": "main",
                "failed_nodes": ["tests/x.py::test_x"],
                "failed_hooks": [],
                "recheck_command": "pytest tests/x.py::test_x",
                "message": "STOP LOOPING",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (repo / "dirty.txt").write_text("changed\n", encoding="utf-8")
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_gate.sh")],
        cwd=repo,
        env={"WS": str(repo), "PR_BASE": "main", "PR_LOCK_WAIT_S": "1"},
    )
    output = proc.stdout + proc.stderr
    assert "FAIL receipt matches unchanged state" not in output
    assert proc.returncode != 2


def test_precommit_reuses_changed_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    listed = tmp_path / "changed.txt"
    listed.write_text("", encoding="utf-8")
    # CI Test Suite has no pre-commit CLI. Empty list must PASS without it.
    slim_path = "/usr/bin:/bin"
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(repo)],
        cwd=repo,
        env={
            "WS": str(repo),
            "PR_BASE": "main",
            "PR_CHANGED_FILE": str(listed),
            "PATH": slim_path,
        },
    )
    assert proc.returncode == 0, proc.stderr
    assert "no changed files for pre-commit" in proc.stdout


def test_precommit_missing_binary_fails_after_files(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    listed = tmp_path / "changed.txt"
    listed.write_text("a.txt\n", encoding="utf-8")
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(repo)],
        cwd=repo,
        env={
            "WS": str(repo),
            "PR_BASE": "main",
            "PR_CHANGED_FILE": str(listed),
            "PATH": "/usr/bin:/bin",
        },
    )
    assert proc.returncode == 1
    assert "INTERNAL leaf of make pr-check" in proc.stderr
    assert "Do not run 'pre-commit install'" in proc.stderr


def test_precommit_repo_fails_closed_on_tracked_dirt(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    (repo / "a.txt").write_text("dirty\n", encoding="utf-8")
    listed = tmp_path / "changed.txt"
    listed.write_text("a.txt\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "pre-commit"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    proc = _run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(repo)],
        cwd=repo,
        env={
            "WS": str(repo),
            "PR_BASE": "main",
            "PR_CHANGED_FILE": str(listed),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
        },
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "tracked files dirty after precommit-repo" in proc.stdout
    assert "Do not auto-stage" in proc.stdout


def test_pr_check_does_not_double_run_precommit_repo() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "pr-check: precommit-repo" not in makefile
    assert "pr: precommit-repo" not in makefile
    assert "pr-check: capability-contract-validate" not in makefile
    assert "push: precommit-repo backup" in makefile
    assert "push: precommit backup" not in makefile


def test_pr_full_owns_corpus_validators() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "pr-full: capability-contract-validate" in makefile
    for name in (
        "validate_legacy_doctrine_residue.py",
        "validate_workflow_action_pins.py",
        "validate_governance_contract_surface.py",
        "validate_git_denial_residue.py",
    ):
        assert name in makefile


def test_precommit_skip_list_drops_corpus_hooks() -> None:
    precommit = (ROOT / "ops" / "scripts" / "run_pr_precommit.sh").read_text(encoding="utf-8")
    for hook in (
        "repo-hygiene",
        "legacy-doctrine-residue",
        "rules-check",
        "skills-check",
    ):
        assert hook in precommit
    assert "SKIP_LIST=" in precommit


def test_gate_domain_gates_corpus_validators() -> None:
    gate = (ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text(encoding="utf-8")
    assert "=== governance contract surface (always-run) ===" not in gate
    assert "domain-gated" in gate
    assert "validate_capability_contract.py" in gate
    assert "make pr-full owns corpus" in gate


def test_gate_does_not_rerun_ruff() -> None:
    gate = (ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text(encoding="utf-8")
    precommit = (ROOT / "ops" / "scripts" / "run_pr_precommit.sh").read_text(encoding="utf-8")
    assert "--- ruff (changed Python) ---" not in gate
    assert "--- lint-ruff (changed Python) ---" in precommit


def test_workflow_action_pins() -> None:
    proc = _run(
        ["python3", str(SCRIPTS / "validate_workflow_action_pins.py")],
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_baseline_ratchet_caller_is_absent() -> None:
    assert not (ROOT / ".github" / "workflows" / "baseline-ratchet-caller.yml").exists()
    assert not (ROOT / ".l9" / "baselines" / "test-quarantine.yml").exists()


def test_open_pr_after_gate_skips_merged_pr() -> None:
    script = (SCRIPTS / "open_pr_after_gate.sh").read_text(encoding="utf-8")
    # A MERGED/CLOSED PR found by head-branch lookup can never carry new branch
    # commits — the gate must clear it and fall through to fresh PR creation.
    assert 'gh api "repos/${owner}/${name}/pulls/${pr_number}" --jq \'.state\'' in script
    assert 'pr_state" != "OPEN"' in script
    assert "opening a new PR" in script
