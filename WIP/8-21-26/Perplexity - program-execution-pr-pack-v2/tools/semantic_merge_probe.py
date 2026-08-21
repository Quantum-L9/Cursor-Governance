#!/usr/bin/env python3
"""tools/semantic_merge_probe.py"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
try: import yaml
except ImportError: print("FAIL: PyYAML required", file=sys.stderr); sys.exit(2)

def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0: raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True); p.add_argument("--base", required=True)
    p.add_argument("--branches", nargs="+", required=True); p.add_argument("--semantic-contracts", nargs="+", required=True)
    p.add_argument("--test-command", default="pytest -q"); p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    contracts = [yaml.safe_load(Path(c).read_text()) for c in args.semantic_contracts]
    selected_tests = sorted({t for c in contracts for t in c.get("direct_tests", [])})
    verdict = {"base": args.base, "branches": args.branches, "selected_tests": selected_tests}
    with tempfile.TemporaryDirectory() as tmp:
        trial_path = Path(tmp) / "trial-merge"
        run(["git", "worktree", "add", "--detach", str(trial_path), args.base], cwd=args.repo)
        try:
            for branch in args.branches:
                merge_out = run(["git", "merge", "--no-commit", "--no-ff", branch], cwd=str(trial_path), check=False)
                if "CONFLICT" in merge_out:
                    verdict.update({"verdict": "FAIL", "reason": f"textual conflict merging {branch}", "detail": merge_out})
                    args.out.write_text(json.dumps(verdict, indent=2)); print(json.dumps(verdict, indent=2)); sys.exit(1)
            test_result = subprocess.run(args.test_command.split(), cwd=str(trial_path), capture_output=True, text=True)
            verdict["verdict"] = "PASS" if test_result.returncode == 0 else "FAIL"
            verdict["test_stdout"] = test_result.stdout[-4000:]; verdict["test_stderr"] = test_result.stderr[-2000:]
        finally:
            run(["git", "worktree", "remove", "--force", str(trial_path)], cwd=args.repo, check=False)
    args.out.write_text(json.dumps(verdict, indent=2)); print(json.dumps(verdict, indent=2))
    sys.exit(0 if verdict["verdict"] == "PASS" else 1)

if __name__ == "__main__":
    main()
