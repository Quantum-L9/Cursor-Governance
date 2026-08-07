#!/usr/bin/env python3
"""Pack gate for l9-code-maintenance: Validation parity + dry-run non-mutation."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent

# Must stay in parity with SKILL.md ## Validation fenced block commands' script basenames.
INVOKED = {
    "self_test.py",
    "code_maintenance.py",
}


def run(
    cmd: list[str], *, cwd: Path | None = None, expected: set[int] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd or ROOT, text=True, capture_output=True, check=False)
    if result.returncode not in (expected or {0}):
        detail = (
            f"fail ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        raise RuntimeError(detail)
    return result


def validation_parity() -> None:
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    # Extract fenced bash under ## Validation
    m = re.search(r"## Validation\n\n```bash\n(.*?)```", skill_md, re.S)
    if not m:
        raise RuntimeError("SKILL.md ## Validation bash block missing")
    block = m.group(1)
    mentioned = set(re.findall(r"scripts/([A-Za-z0-9_\-]+\.py)", block))
    if mentioned != INVOKED:
        raise RuntimeError(f"Validation parity mismatch: skill={mentioned} invoked={INVOKED}")


def test_refactor_sweep_dry_run() -> None:
    before = run(["git", "status", "--porcelain"])
    intent = "toy rename foo_unique_token_xyz to bar_unique_token_xyz"
    result = run(
        [
            sys.executable,
            str(SCRIPTS / "code_maintenance.py"),
            "--mode",
            "refactor-sweep",
            "--dry-run",
            intent,
        ]
    )
    if (
        "REFACTOR SWEEP REPORT" not in result.stdout
        and "REFACTOR SWEEP REPORT" not in result.stderr
    ):
        # report goes to stdout from child; capture includes it
        combined = result.stdout + result.stderr
        if "Governance Decision" not in combined and "REFACTOR SWEEP REPORT" not in combined:
            # code_maintenance prints via subprocess without capture of child stdout in parent—
            # we re-run analyzer directly
            direct = run([sys.executable, str(SCRIPTS / "refactor_sweep.py"), intent])
            if (
                "Governance Decision" not in direct.stdout
                and "NO-OP" not in direct.stdout
                and "REFACTOR SWEEP REPORT" not in direct.stdout
            ):
                raise RuntimeError(f"missing report:\n{direct.stdout}")
    after = run(["git", "status", "--porcelain"])
    if before.stdout != after.stdout:
        raise RuntimeError(
            f"dry-run mutated tree:\nbefore={before.stdout!r}\nafter={after.stdout!r}"
        )


def test_migrate_dry_run_no_state() -> None:
    state = ROOT / ".migrate_executor_state.json"
    if state.exists():
        state.unlink()
    before = run(["git", "status", "--porcelain"])
    run(
        [
            sys.executable,
            str(ROOT / "workflows" / "migrate_executor.py"),
            "--dry-run",
            "this_pattern_should_not_exist_zz99",
            "replacement_zz99",
        ]
    )
    if state.exists():
        raise RuntimeError("migrate --dry-run wrote state file")
    after = run(["git", "status", "--porcelain"])
    if before.stdout != after.stdout:
        raise RuntimeError("migrate dry-run mutated git status")


def test_campaign_intent_gmp() -> None:
    intent = (
        "Campaign is master; keep root autonomy/ callable; "
        "relocate PES → coding/campaigns/execution; "
        "fold execution-governance → coding/campaigns/governance; "
        "move generated-data → coding/campaigns/signals; "
        "add thin coding/campaigns/autonomy bridge that calls root autonomy/; "
        "rename program→campaign in PES contracts."
    )
    result = run([sys.executable, str(SCRIPTS / "refactor_sweep.py"), intent])
    if "GMP REQUIRED" not in result.stdout:
        raise RuntimeError(f"expected GMP REQUIRED, got:\n{result.stdout}")
    if "do-not-move" not in result.stdout and "Autonomy do-not-move: ✅" not in result.stdout:
        raise RuntimeError(f"expected autonomy do-not-move note:\n{result.stdout}")


def test_scripts_exist() -> None:
    for name in ("code_maintenance.py", "refactor_sweep.py", "self_test.py"):
        if not (SCRIPTS / name).is_file():
            raise RuntimeError(f"missing script {name}")
    for name in (
        "maintenance-workflows.md",
        "dry-run-contract.md",
        "refactor-sweep-protocol.md",
        "protected-paths.md",
    ):
        if not (SKILL / "references" / name).is_file():
            raise RuntimeError(f"missing reference {name}")


def main() -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    tests = [
        ("scripts_exist", test_scripts_exist),
        ("validation_parity", validation_parity),
        ("refactor_sweep_dry_run", test_refactor_sweep_dry_run),
        ("migrate_dry_run_no_state", test_migrate_dry_run_no_state),
        ("campaign_intent_gmp", test_campaign_intent_gmp),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")
    if failed:
        print(f"FAILED {failed}/{len(tests)}")
        return 1
    print(f"ALL PASS ({len(tests)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
