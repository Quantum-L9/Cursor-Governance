"""Capability-graph PR lifecycle: improve, preflight, soft-empty, gate receipt."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
L4 = ROOT / "ops" / "autonomy" / "l4_local.py"
KERNEL_GATE = ROOT / "ops" / "autonomy" / "kernel_gate.py"


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
    paths, content = _state_digest(repo)
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-receipt.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_receipt.v2",
                "paths_digest": paths,
                "content_digest": content,
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
    """Ask the gate for its own digest instead of reimplementing it.

    This helper used to carry a shell copy of the algorithm. That duplication is
    what made the digest expensive to correct: every change had to be made twice,
    in two languages, and a drifting copy would let these tests pass while the
    real gate did something else. The digest now also covers the gate's own
    code, which a copy could not have known to include.
    """
    out = subprocess.check_output(
        ["bash", str(SCRIPTS / "run_pr_gate.sh"), "--print-state-digest"],
        cwd=str(repo),
        text=True,
        env={**os.environ, "WS": str(repo), "PR_BASE": pr_base},
    ).split()
    return out[0], out[1]


def test_gate_failure_receipt_refuses_second_full_gate(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    paths, content = _state_digest(repo)
    node = (
        "environment/program-execution/scripts/tests/test_run_campaign.py::"
        "RunCampaignTests::test_until_activate_from_memo"
    )
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-failure.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v2",
                "paths_digest": paths,
                "content_digest": content,
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
    paths, content = _state_digest(repo)
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    payload = {"paths_digest": paths, "content_digest": content, "pr_base": "main"}
    (receipt_dir / "gate-receipt.json").write_text(
        json.dumps({"schema": "l9.pr_gate_receipt.v2", **payload}) + "\n",
        encoding="utf-8",
    )
    (receipt_dir / "gate-failure.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v2",
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
    paths, content = _state_digest(repo)
    receipt_dir = repo / ".l9" / "pr"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "gate-failure.json").write_text(
        json.dumps(
            {
                "schema": "l9.pr_gate_failure.v2",
                "paths_digest": paths,
                "content_digest": content,
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
    assert "INTERNAL leaf of make pr" in proc.stderr
    assert "Do not run 'pre-commit install'" in proc.stderr


def _stamp_kernel(repo: Path) -> None:
    assert (
        _run(
            [
                "python3",
                str(KERNEL_GATE),
                "record",
                "--workspace",
                str(repo),
                "--gov-root",
                str(ROOT),
            ],
            cwd=repo,
        ).returncode
        == 0
    )


def test_precommit_repo_kernel_hook_fails_before_hooks(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
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
    assert proc.returncode == 2, proc.stdout + proc.stderr
    combined = proc.stdout + proc.stderr
    assert "apply_kernels_then_precommit" in combined
    assert "tracked files dirty after precommit-repo" not in combined
    assert "lint-ruff" not in combined


def test_precommit_repo_fails_closed_on_tracked_dirt(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path, feature=True)
    _stamp_kernel(repo)
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


def test_precommit_script_runs_kernel_hook_first() -> None:
    precommit = (ROOT / "ops" / "scripts" / "run_pr_precommit.sh").read_text(encoding="utf-8")
    kernel_at = precommit.find("kernel_gate.py")
    hook_at = precommit.find("pre-commit run")
    ruff_at = precommit.find("--- ruff (locked writer)")
    assert kernel_at != -1
    assert kernel_at < hook_at < ruff_at
    readers_branch = precommit.find('STAGE" == "readers"')
    assert readers_branch != -1
    assert kernel_at < readers_branch or "_run_kernel" in precommit


def test_precommit_skip_lists_are_disjoint() -> None:
    precommit = (ROOT / "ops" / "scripts" / "run_pr_precommit.sh").read_text(encoding="utf-8")
    for hook in (
        "repo-hygiene",
        "legacy-doctrine-residue",
        "rules-check",
        "skills-check",
    ):
        assert hook in precommit
    assert "_WRITER_SKIP=" in precommit
    assert "_READER_SKIP=" in precommit
    assert "_READER_HOOKS=" in precommit
    assert "_WRITER_HOOKS=" in precommit
    writer_hooks = "end-of-file-fixer,trailing-whitespace"
    reader_hooks = (
        "check-merge-conflict,check-added-large-files,check-yaml,"
        "no-hardcoded-paths,gh-package-deps-preflight"
    )
    assert writer_hooks in precommit
    assert reader_hooks in precommit
    for hook in writer_hooks.split(","):
        assert hook not in reader_hooks
    for hook in reader_hooks.split(","):
        assert hook not in writer_hooks


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
    assert "--- lint-ruff (changed Python) ---" not in precommit
    assert precommit.count("--- ruff (locked writer) ---") == 1
    assert "ruff,ruff-format" in precommit
    assert "check --fix" in precommit
    assert "quiescing and retrying pre-commit once" not in gate
    assert "PR_PRECOMMIT_STAGE=writers" in gate or 'PR_PRECOMMIT_STAGE="$stage"' in gate
    assert gate.count('git status --porcelain >"$status_before"') == 1


def test_early_overlap_is_pr_goal_only() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    gate = (ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text(encoding="utf-8")
    open_pr = (SCRIPTS / "open_pr_after_gate.sh").read_text(encoding="utf-8")
    assert "pr: export PR_EARLY_OVERLAP = 1" in makefile
    pr_check = makefile.split("pr-check:", 1)[1].split("\n\n", 1)[0]
    assert "PR_EARLY_OVERLAP" not in pr_check
    assert "PR_EARLY_OVERLAP:-0" in gate
    assert "--reuse-receipt" in open_pr
    assert "l4-preflight.json" in open_pr
    assert "check-remote" in open_pr
    assert "L4 preflight receipt reused" in open_pr
    early = gate.find("--- early overlap")
    wave = gate.find("=== reader wave")
    assert early != -1 and wave != -1
    assert early < wave
    assert gate.find("FAIL: early overlap blocked publish") < wave


def test_gate_hard_stop_precedes_pytest() -> None:
    gate = (ROOT / "ops" / "scripts" / "run_pr_gate.sh").read_text(encoding="utf-8")
    dirt = gate.find("Do not rebase status_before over that dirt")
    pytest_at = gate.find("--- pytest ---")
    wave = gate.find("=== reader wave")
    assert dirt != -1
    assert pytest_at != -1
    assert dirt < pytest_at
    assert dirt < wave
    assert "unset PR_OVERLAP PR_OVERLAP_TELEMETRY PR_STACK PR_REMEDIATE" in gate
    assert "quiescing and retrying pre-commit once" not in gate
    assert 'source "$SCRIPT_DIR/lib/resolve_pr_stack.sh"' in gate
    heal_at = gate.find("=== generated heal (serialized writer) ===")
    wave_at = gate.find("=== reader wave")
    assert heal_at != -1 and wave_at != -1
    assert heal_at < wave_at
    assert "_wave_start sync " not in gate
    heal_block = gate[heal_at:wave_at]
    assert "_gate_run_projection_heal" in heal_block
    fn_at = gate.find("_gate_run_projection_heal() {")
    assert fn_at != -1 and fn_at < heal_at
    assert "--check --quiet --no-receipt" not in gate[fn_at:heal_at]


def test_workflow_action_pins() -> None:
    proc = _run(
        ["python3", str(SCRIPTS / "validate_workflow_action_pins.py")],
        cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_gate_code_change_invalidates_the_receipt(tmp_path: Path) -> None:
    """A receipt must not survive a change to the gate that issued it.

    The digest hashed the workspace tree. When $WS is a linked worktree the gate
    runs from $GOV_ROOT, a different checkout, so editing run_pr_gate.sh left the
    digest identical and the previous version's verdict was reused against the
    new one. Validating a gate fix then required deleting the receipt by hand.

    Isolated on a copied gate tree so the real repository is never mutated:
    GOV_ROOT is derived as <script dir>/../.., which makes the copy authoritative.
    """
    gov = tmp_path / "gov"
    (gov / "ops").mkdir(parents=True)
    shutil.copytree(SCRIPTS, gov / "ops" / "scripts")
    shutil.copytree(ROOT / "ops" / "config", gov / "ops" / "config")
    gate = gov / "ops" / "scripts" / "run_pr_gate.sh"

    repo = _init_repo(tmp_path, feature=True)

    def digest() -> list[str]:
        return subprocess.check_output(
            ["bash", str(gate), "--print-state-digest"],
            cwd=str(repo),
            text=True,
            env={**os.environ, "WS": str(repo), "PR_BASE": "main"},
        ).split()

    before = digest()
    target = gov / "ops" / "scripts" / "run_python_test_suites.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# behaviour change\n", "utf-8")
    after = digest()

    assert before[0] == after[0], "workspace paths did not change"
    assert before[1] != after[1], "gate-code change must change the content digest"
    assert before[2] == after[2] == "main"


def test_baseline_ratchet_caller_is_absent() -> None:
    assert not (ROOT / ".github" / "workflows" / "baseline-ratchet-caller.yml").exists()
    assert not (ROOT / ".l9" / "baselines" / "test-quarantine.yml").exists()


def test_open_pr_after_gate_handles_landed_pr() -> None:
    script = (SCRIPTS / "open_pr_after_gate.sh").read_text(encoding="utf-8")
    # A landed PR found by head-branch lookup can never carry new branch
    # commits. REST returns the state lowercase ("open"/"closed"), so the
    # keeper branch matches case-insensitively and never clears an
    # actually-open PR.
    assert 'case "$pr_state" in' in script
    assert "open | OPEN) ;;" in script
    # merged_at distinguishes the two landed outcomes: a MERGED PR means the
    # branch name is spent (AGENTS.md §17 reused_after_merge) and the gate
    # fails with move-to-a-new-branch instructions; only a closed-but-unmerged
    # PR falls through to fresh PR creation.
    assert '[.state, (.merged_at // "")] | @tsv' in script
    assert "never reused after its PR merges" in script
    assert "closed, not merged" in script
    assert "opening a new PR" in script


def test_open_pr_after_gate_remediates_defaults_to_one() -> None:
    script = (SCRIPTS / "open_pr_after_gate.sh").read_text(encoding="utf-8")
    assert 'PR_REMEDIATE="${PR_REMEDIATE:-1}"' in script
    assert 'PR_REMEDIATE="${PR_REMEDIATE:-0}"' not in script
