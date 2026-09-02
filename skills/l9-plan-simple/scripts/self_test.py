#!/usr/bin/env python3
"""Pack self-test for l9-plan-simple GAR wire + section receipt (both handoff modes)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REPO = ROOT.parents[1]
PLAN_PASS = REPO / "skills" / "l9-plan" / "fixtures" / "plan_pass.json"
RENDER = REPO / "skills" / "l9-plan" / "scripts" / "render_plan_pe_autonomy.py"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generate_plan_section_receipt import build_receipt  # noqa: E402
from validate_plan_section_receipt import check_receipt  # noqa: E402

# Repo-root paths: the scripts confine CLI arguments to the working directory,
# so the SKILL.md Validation block is documented and run from the repo root.
INVOKED = [
    "skills/l9-plan/scripts/validate_plan_document.py",
    "skills/l9-plan-simple/scripts/generate_plan_section_receipt.py",
    "skills/l9-plan-simple/scripts/validate_plan_section_receipt.py",
    "skills/l9-plan-simple/scripts/self_test.py",
]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def _skill_validation_scripts() -> list[str]:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    block = re.search(r"## Validation\s+.*?```bash\n(.*?)```", text, re.S)
    if not block:
        return []
    return re.findall(r"skills/[a-zA-Z0-9_.-]+/scripts/[a-zA-Z0-9_./-]+\.py", block.group(1))


def _render(dest: Path, mode: str = "cursor-build") -> None:
    proc = _run(
        [
            sys.executable,
            str(RENDER),
            str(PLAN_PASS),
            f"--execute-via={mode}",
        ],
        cwd=REPO,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"render failed: {proc.stderr or proc.stdout}")
    dest.write_text(proc.stdout, encoding="utf-8")


def main() -> int:
    errors: list[str] = []
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "l9-global-architect" not in skill:
        errors.append("SKILL.md does not invoke l9-global-architect upstream")
    if "generate_plan_section_receipt.py" not in skill:
        errors.append("SKILL.md missing generate_plan_section_receipt.py")
    if "validate_plan_section_receipt.py" not in skill:
        errors.append("SKILL.md missing validate_plan_section_receipt.py")

    listed = _skill_validation_scripts()
    if not listed:
        errors.append("SKILL.md ## Validation bash block missing or has no scripts")
    for name in INVOKED:
        if name != "skills/l9-plan-simple/scripts/self_test.py" and name not in listed:
            errors.append(f"SKILL.md Validation missing invoked script: {name}")

    if not PLAN_PASS.is_file():
        errors.append(f"missing fixture {PLAN_PASS}")
        print("\n".join(errors), file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        plan_md = Path(tmp) / "pass.plan.md"
        _render(plan_md)
        hold = ROOT / "fixtures" / "_self_test"
        hold.mkdir(parents=True, exist_ok=True)
        live_json = hold / "plan_pass.json"
        live_md = hold / "pass.plan.md"
        live_receipt = hold / "pass.receipt.json"
        fail_md = hold / "fail.plan.md"
        fail_receipt = hold / "fail.receipt.json"
        extra: tuple[Path, ...] = ()
        try:
            live_json.write_bytes(PLAN_PASS.read_bytes())
            live_md.write_text(plan_md.read_text(encoding="utf-8"), encoding="utf-8")
            receipt = build_receipt(live_json, live_md, gar_invoked=True, gar_run_id="self-test")
            live_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            pass_errors = check_receipt(live_receipt)
            if pass_errors:
                errors.append("expected PASS receipt failed:\n  " + "\n  ".join(pass_errors))

            stripped = live_md.read_text(encoding="utf-8").replace("## Rollback\n", "## Removed\n")
            fail_md.write_text(stripped, encoding="utf-8")
            fail_built = build_receipt(live_json, fail_md, gar_invoked=True, gar_run_id="self-test")
            fail_receipt.write_text(json.dumps(fail_built, indent=2) + "\n", encoding="utf-8")
            fail_errors = check_receipt(fail_receipt)
            if not any("Rollback" in err for err in fail_errors):
                errors.append(
                    "missing-Rollback fixture did not emit G_MD_SECTION for Rollback: "
                    + repr(fail_errors)
                )

            no_gar = build_receipt(live_json, live_md, gar_invoked=False, gar_run_id=None)
            if no_gar["status"] != "fail":
                errors.append("receipt with gar_upstream.invoked=false must status=fail")

            if receipt.get("handoff_mode") != "cursor-build":
                errors.append(f"cursor-build receipt handoff_mode: {receipt.get('handoff_mode')!r}")

            # Embedded handoff: same receipt shape, judged against its own mode.
            emb_md = hold / "embedded.plan.md"
            emb_receipt = hold / "embedded.receipt.json"
            extra = (emb_md, emb_receipt)
            _render(emb_md, mode="embedded")
            emb_built = build_receipt(live_json, emb_md, gar_invoked=True, gar_run_id="self-test")
            emb_receipt.write_text(json.dumps(emb_built, indent=2) + "\n", encoding="utf-8")
            if emb_built.get("handoff_mode") != "embedded":
                errors.append(f"embedded receipt handoff_mode: {emb_built.get('handoff_mode')!r}")
            emb_errors = check_receipt(emb_receipt)
            if emb_errors:
                errors.append(
                    "expected PASS embedded receipt failed:\n  " + "\n  ".join(emb_errors)
                )
        finally:
            for path in (live_json, live_md, live_receipt, fail_md, fail_receipt, *extra):
                if path.exists():
                    path.unlink()
            if hold.exists() and not any(hold.iterdir()):
                hold.rmdir()

    if errors:
        print("FAIL: l9-plan-simple self_test", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    print("PASS: l9-plan-simple self_test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
