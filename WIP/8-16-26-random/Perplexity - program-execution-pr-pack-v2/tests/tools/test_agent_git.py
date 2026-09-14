import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "agent_git.py"

def _run(args, cwd):
    return subprocess.run([sys.executable, str(TOOL), "--cwd", str(cwd)] + args, capture_output=True, text=True)

def _git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)

def test_doctor_refuses_shared_checkout_or_protected_branch(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    _git(["init", "-b", "main"], repo); _git(["commit", "--allow-empty", "-m", "init"], repo)
    result = _run(["doctor"], repo)
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "shared/primary checkout" in combined or "protected branch" in combined

def test_doctor_passes_in_isolated_worktree_on_feature_branch(tmp_path):
    repo = tmp_path / "repo"; repo.mkdir()
    _git(["init", "-b", "main"], repo); _git(["commit", "--allow-empty", "-m", "init"], repo)
    wt = tmp_path / "wt-a"
    _git(["worktree", "add", "-b", "feat/a", str(wt)], repo)
    result = _run(["doctor"], wt)
    assert result.returncode == 0
    assert "PASS" in result.stdout

def test_claim_rejects_duplicate_branch(tmp_path):
    origin = tmp_path / "origin.git"
    _git(["init", "--bare", "-b", "main", str(origin)], tmp_path)
    repo = tmp_path / "repo"
    _git(["clone", str(origin), str(repo)], tmp_path)
    _git(["commit", "--allow-empty", "-m", "init"], repo)
    _git(["push", "origin", "main"], repo)
    wt1 = tmp_path / "wt-1"
    _git(["worktree", "add", "-b", "feat/dup", str(wt1)], repo)
    result = _run(["claim", "--branch", "feat/dup", "--path", str(tmp_path / "wt-2"),
                   "--base", "main", "--agent-id", "agentB"], repo)
    assert result.returncode == 1
    assert "already checked out" in (result.stdout + result.stderr)
