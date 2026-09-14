import subprocess, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "check_feature_tree.py"
FIXTURES = ROOT / "tests" / "fixtures" / "feature_trees"

def run_checker(tree_name, extra_args=None):
    cmd = [sys.executable, str(TOOL), "--tree", str(FIXTURES / tree_name), "--repo-root", str(ROOT), "--json"]
    if extra_args: cmd += extra_args
    return subprocess.run(cmd, capture_output=True, text=True)

def test_valid_tree_passes():
    result = run_checker("valid.yaml")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["verdict"] == "PASS"
    assert data["merge_order"] == ["PE-010", "PE-020"]

def test_cycle_detected():
    result = run_checker("invalid_cycle.yaml")
    assert result.returncode == 1
    assert "FT001" in result.stdout

def test_parallel_scope_collision_detected():
    result = run_checker("invalid_parallel_scope.yaml")
    assert result.returncode == 1
    assert "FT005" in result.stdout

def test_diff_scope_pass_and_fail():
    ok = run_checker("valid.yaml", ["--node", "PE-010", "--diff-files", "tools/check_feature_tree.py"])
    assert ok.returncode == 0
    bad = run_checker("valid.yaml", ["--node", "PE-010", "--diff-files", "some/other/file.py"])
    assert bad.returncode == 1
    assert "FT031" in bad.stdout
