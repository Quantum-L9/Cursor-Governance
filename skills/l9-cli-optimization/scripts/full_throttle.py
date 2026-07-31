#!/usr/bin/env python3
"""Full-throttle activation harness: flip a repo's off-by-default flags on, prove
them with the repo's OWN tests in an isolated git worktree, and back out any flag
whose activation regresses tests.

This is the execution half of the skill's *full-throttle activation mode* (see
`references/full-throttle-activation.md`). It relaxes Identity-Lock #1's
`dormant_by_design` clause **for testing** and pays for it with strong
compensating controls that keep #2 (safety) and #3 (no quota/backpressure
bypass) intact:

  1. danger flags are never flipped (polarity-aware classifier in
     `flag_inventory.py`);
  2. every flip is validated by execution — a flag that breaks the repo's tests
     is reverted and reclassified `empirically_unsafe` (never assumed safe);
  3. all flip+test happens in a throwaway `git worktree`; the real working tree
     is never mutated; the PR is the human gate and is never merged here.

MODE=plan (default) emits the inventory + classification + would-flip set and
touches nothing. MODE=apply runs flip→test→back-out in the worktree and writes
the proven flip-set + test delta for `build_flag_activation_pack.py`.

Stdlib-only. The ONLY execution is `subprocess.run` of the repo's declared test
command inside the isolated worktree — never a network or deploy action (deploy/
publish/external flags are danger-class and excluded before any test runs).
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flag_inventory import classify_flag, flip_flag, inventory_flags, summarize  # noqa: E402

MAX_BACKOUT_PASSES = 6  # bounded, in the spirit of the skill's three-cycle law


def _run(cmd: list[str], cwd: str | Path | None = None, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True,
                          capture_output=True, check=False, timeout=timeout)


def discover_test_cmd(root: Path) -> list[str] | None:
    """Best-effort discovery of the repo's own test command (no execution)."""
    py = root / "pyproject.toml"
    if py.is_file():
        txt = py.read_text(encoding="utf-8", errors="ignore")
        if "[tool.pytest" in txt or "pytest" in txt:
            return ["python3", "-m", "pytest", "-q"]
    mk = root / "Makefile"
    if mk.is_file():
        for line in mk.read_text(encoding="utf-8", errors="ignore").splitlines():
            if re.match(r"^test\s*:", line):
                return ["make", "test"]
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
            if isinstance(data.get("scripts"), dict) and "test" in data["scripts"]:
                return ["npm", "test", "--silent"]
        except (OSError, json.JSONDecodeError):
            pass
    if (root / "tox.ini").is_file():
        return ["tox"]
    return None


def _test_command_is_dangerous(test_cmd: list[str]) -> str | None:
    """A test command that itself deploys/publishes is danger — do not run it."""
    joined = " ".join(test_cmd).lower()
    cls, reason = classify_flag("cmd_" + re.sub(r"[^a-z]+", "_", joined), joined, staged=False)
    return reason if cls == "danger" else None


def _worktree_add(repo: Path) -> tuple[str, str]:
    wt = tempfile.mkdtemp(prefix="full-throttle-")
    r = _run(["git", "-C", str(repo), "worktree", "add", "--detach", wt, "HEAD"])
    if r.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {r.stderr.strip()}")
    return wt, wt


def _worktree_remove(repo: Path, wt: str) -> None:
    _run(["git", "-C", str(repo), "worktree", "remove", "--force", wt])


def _apply_flips(wt: Path, flags: list[dict]) -> None:
    """Apply every flag in `flags` to files under the worktree (in place)."""
    by_file: dict[str, list[dict]] = {}
    for f in flags:
        by_file.setdefault(f["file"], []).append(f)
    for rel, fs in by_file.items():
        path = wt / rel
        text = path.read_text(encoding="utf-8", errors="ignore")
        # apply highest line first so earlier line numbers stay valid
        for f in sorted(fs, key=lambda x: -x["line"]):
            text = flip_flag(text, f)
        path.write_text(text, encoding="utf-8")


def _reset_worktree(wt: Path, repo: Path) -> None:
    _run(["git", "-C", str(wt), "checkout", "--", "."])


def _run_tests(wt: Path, test_cmd: list[str]) -> dict:
    r = _run(test_cmd, cwd=wt)
    return {"returncode": r.returncode, "passed": r.returncode == 0,
            "stdout_tail": "\n".join(r.stdout.splitlines()[-15:]),
            "stderr_tail": "\n".join(r.stderr.splitlines()[-15:])}


def _bisect_back_out(wt: Path, repo: Path, flippable: list[dict], test_cmd: list[str]) -> tuple[list[dict], list[dict], int]:
    """Return (safe_flags, breaker_flags, passes). A flag is a breaker if the
    proven-safe subset stays green without it but regresses with it. Bounded
    group-halving keeps this within MAX_BACKOUT_PASSES."""
    safe = list(flippable)
    breakers: list[dict] = []
    passes = 0
    suspects = list(flippable)
    while suspects and passes < MAX_BACKOUT_PASSES:
        passes += 1
        _reset_worktree(wt, repo)
        _apply_flips(wt, safe)
        result = _run_tests(wt, test_cmd)
        if result["passed"]:
            break
        # halve the suspect set: drop one half, keep testing
        if len(suspects) == 1:
            breaker = suspects[0]
            breakers.append(breaker)
            safe = [f for f in safe if f is not breaker]
            suspects = []
            _reset_worktree(wt, repo)
            _apply_flips(wt, safe)
            if _run_tests(wt, test_cmd)["passed"]:
                break
            suspects = list(safe)  # more than one breaker; keep isolating
            continue
        mid = len(suspects) // 2
        drop, keep = suspects[:mid], suspects[mid:]
        trial = [f for f in safe if f not in drop]
        _reset_worktree(wt, repo)
        _apply_flips(wt, trial)
        if _run_tests(wt, test_cmd)["passed"]:
            # a breaker is in `drop`; remove that half and narrow
            safe = trial
            breakers.extend(drop)
            suspects = list(safe)
        else:
            # a breaker is in `keep` (may also be in drop); narrow to keep
            suspects = keep
    return safe, breakers, passes


def run_activation(root: Path, test_cmd: list[str] | None, mode: str, overrides: dict | None = None) -> dict:
    root = root.resolve()
    rows = inventory_flags(root, overrides)
    flippable = [f for f in rows if f["decision"] == "flip" and not f.get("no_flip")]
    report: dict = {
        "repo": str(root),
        "mode": mode,
        "inventory": rows,
        "summary": summarize(rows),
        "would_flip": [f["flag"] for f in flippable],
    }

    if mode == "plan":
        report["note"] = "PLAN mode: no worktree, no test run, nothing mutated. " \
                         "Re-run with MODE=apply (or --mode apply) to prove and package the flips."
        return report

    # apply mode
    is_git = (root / ".git").exists() or _run(["git", "-C", str(root), "rev-parse", "--git-dir"]).returncode == 0
    if not is_git:
        report["error"] = "apply mode requires a git repository (isolated worktree)"
        report["applied"] = False
        return report
    test_cmd = test_cmd or discover_test_cmd(root)
    if not test_cmd:
        report["error"] = "no test command discovered; pass --test-cmd to prove flips"
        report["applied"] = False
        return report
    danger_cmd = _test_command_is_dangerous(test_cmd)
    if danger_cmd:
        report["error"] = f"refusing to run a deploy/publish test command: {danger_cmd}"
        report["applied"] = False
        return report

    report["test_command"] = test_cmd
    wt_raw, _ = _worktree_add(root)
    wt = Path(wt_raw)
    try:
        baseline = _run_tests(wt, test_cmd)
        report["baseline_test"] = baseline
        if not flippable:
            report["applied"] = False
            report["note"] = "no non-danger flip candidates"
            return report
        safe, breakers, passes = _bisect_back_out(wt, root, flippable, test_cmd)
        _reset_worktree(wt, root)
        _apply_flips(wt, safe)
        activated_test = _run_tests(wt, test_cmd)
        diff = _run(["git", "-C", str(wt), "diff"]).stdout
        report.update({
            "applied": bool(safe) and activated_test["passed"],
            "activated_flags": [f["flag"] for f in safe],
            "activated_flag_rows": safe,
            "backed_out_flags": [{"flag": f["flag"], "file": f["file"], "line": f["line"],
                                  "classification": "empirically_unsafe",
                                  "reason": "activation regressed the repo's tests"} for f in breakers],
            "back_out_passes": passes,
            "activated_test": activated_test,
            "diff": diff,
            "test_delta": {
                "baseline_passed": baseline["passed"],
                "activated_passed": activated_test["passed"],
                "flags_off": 0,
                "flags_on": len(safe),
            },
        })
        if breakers and not safe:
            report["note"] = "every flip candidate regressed tests; flipping nothing"
        return report
    finally:
        _worktree_remove(root, wt_raw)


def run_all(repos: list[Path], test_cmd: list[str] | None, mode: str) -> dict:
    results = []
    for repo in repos:
        try:
            results.append(run_activation(repo, test_cmd, mode))
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            results.append({"repo": str(repo), "mode": mode, "error": str(exc), "applied": False})
    matrix = [{
        "repo": r["repo"],
        "activated": r.get("activated_flags", r.get("would_flip", [])),
        "danger_excluded": r.get("summary", {}).get("held_danger", []),
        "staged_excluded": r.get("summary", {}).get("held_staged", []),
        "empirically_unsafe": [b["flag"] for b in r.get("backed_out_flags", [])],
        "tests_pass": r.get("activated_test", {}).get("passed"),
        "error": r.get("error"),
    } for r in results]
    return {"mode": mode, "results": results, "matrix": matrix}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", type=Path, nargs="+")
    parser.add_argument("--mode", choices=["plan", "apply"], default="plan")
    parser.add_argument("--test-cmd", help="explicit test command (shell-quoted); overrides discovery")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    test_cmd = shlex.split(args.test_cmd) if args.test_cmd else None
    for repo in args.repos:
        if not repo.is_dir():
            print(f"FAIL: not a directory: {repo}", file=sys.stderr)
            return 2
    if len(args.repos) == 1:
        result = run_activation(args.repos[0], test_cmd, args.mode)
    else:
        result = run_all(args.repos, test_cmd, args.mode)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
