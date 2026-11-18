#!/usr/bin/env python3
"""The only writer of a simple-plan projection and its section receipt.

Runs, in order: memory-prefetch receipt, GAR run-file verification,
PLAN_DOCUMENT validation, projection with a required ``--execute-via`` and
``--workspace``, then section-receipt generation and validation. A missing
GAR run file, an undeclared field, or an unbound baseline or success
property exits non-zero and does not write the plan.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from paths import safe_cli_path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parents[2]
VALIDATOR = REPO / "skills" / "l9-plan" / "scripts" / "validate_plan_document.py"
RENDERER = REPO / "skills" / "l9-plan" / "scripts" / "render_plan_pe_autonomy.py"
GENERATE = SCRIPTS / "generate_plan_section_receipt.py"
VALIDATE_RECEIPT = SCRIPTS / "validate_plan_section_receipt.py"
GAR_SCRIPTS = REPO / "skills" / "l9-global-architect" / "scripts"

NOT_DECLARED = "unknown — not declared"
UNBOUND_BASELINE = "unbound — re-render"
UNBOUND_PROOF = "unbound — no "


def _gar_module():
    if str(GAR_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(GAR_SCRIPTS))
    sys.dont_write_bytecode = True
    import write_plan_run

    return write_plan_run


def _run(cmd: list[str], *, workspace: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if workspace is not None:
        env["L9_PLAN_WORKSPACE"] = str(workspace)
    return subprocess.run(cmd, cwd=Path.cwd(), text=True, capture_output=True, env=env)


def _sibling_receipt(plan_md: Path) -> Path:
    """The only receipt path admit_plan.py will read."""
    name = plan_md.name
    suffix = ".plan.md"
    if name.endswith(suffix):
        receipt_name = name[: -len(suffix)] + ".section-receipt.json"
    else:
        receipt_name = name + ".section-receipt.json"
    return plan_md.with_name(receipt_name)


def _marker_hits(text: str) -> list[str]:
    hits: list[str] = []
    if NOT_DECLARED in text:
        hits.append("unknown — not declared")
    if UNBOUND_BASELINE in text:
        hits.append("unbound baseline")
    if UNBOUND_PROOF in text:
        hits.append("unbound success property")
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--execute-via", required=True, choices=["cursor-build", "embedded"])
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--gar-run", required=True)
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--out-receipt", default=None)
    args = parser.parse_args(argv)

    try:
        plan_json = safe_cli_path(args.plan_json)
        workspace = safe_cli_path(args.workspace)
        out_md = safe_cli_path(args.out_md)
        gar_run = safe_cli_path(args.gar_run)
        canonical = _sibling_receipt(out_md)
        if args.out_receipt is None:
            out_receipt = canonical
        else:
            out_receipt = safe_cli_path(args.out_receipt)
    except SystemExit as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if out_receipt.resolve() != canonical.resolve():
        print(
            f"FAIL: --out-receipt must be the sibling {canonical.name} that admit_plan.py reads",
            file=sys.stderr,
        )
        return 2

    if not gar_run.is_file():
        print(f"FAIL: GAR run file is absent: {gar_run}", file=sys.stderr)
        return 1
    problems = _gar_module().verify_run(gar_run, workspace=workspace)
    if problems:
        print("FAIL: GAR run file", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1

    prefetch = workspace / ".l9" / "memory" / "plan-prefetch.json"
    if not prefetch.is_file():
        print(f"FAIL: memory prefetch receipt missing: {prefetch}", file=sys.stderr)
        return 1
    try:
        prefetch_body = json.loads(prefetch.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: memory prefetch receipt is not JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(prefetch_body, dict) or not prefetch_body:
        print("FAIL: memory prefetch receipt is empty", file=sys.stderr)
        return 1

    validated = _run([sys.executable, str(VALIDATOR), str(plan_json)], workspace=workspace)
    if validated.returncode != 0:
        sys.stderr.write(validated.stdout)
        sys.stderr.write(validated.stderr)
        return validated.returncode or 1

    rendered = _run(
        [
            sys.executable,
            str(RENDERER),
            str(plan_json),
            f"--execute-via={args.execute_via}",
            "--workspace",
            str(workspace),
        ],
        workspace=workspace,
    )
    hits = _marker_hits(rendered.stdout)
    if rendered.returncode != 0 or hits:
        sys.stderr.write(rendered.stderr)
        detail = ", ".join(hits) if hits else f"renderer exit {rendered.returncode}"
        print(f"FAIL: projection refused: {detail}", file=sys.stderr)
        return rendered.returncode or 2

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(rendered.stdout, encoding="utf-8")
    generated = _run(
        [
            sys.executable,
            str(GENERATE),
            "--plan-json",
            str(plan_json),
            "--plan-md",
            str(out_md),
            "--out",
            str(out_receipt),
            "--gar-invoked",
            "--gar-run",
            str(gar_run),
        ],
        workspace=workspace,
    )
    if generated.returncode != 0:
        sys.stderr.write(generated.stdout)
        sys.stderr.write(generated.stderr)
        return generated.returncode or 1
    checked = _run([sys.executable, str(VALIDATE_RECEIPT), str(out_receipt)], workspace=workspace)
    sys.stdout.write(checked.stdout)
    if checked.returncode != 0:
        sys.stderr.write(checked.stderr)
        sys.stderr.write(checked.stdout)
        return checked.returncode or 1

    scripts = str(SCRIPTS)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from admit_plan import check_plan

    admit_errors = check_plan(out_md)
    if admit_errors:
        print("FAIL: pipeline output is not admissible", file=sys.stderr)
        for err in admit_errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    hooks = REPO / "ops" / "hooks"
    if str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))
    import plan_kernel_gate

    plan_kernel_gate.clear_pipeline_required(workspace, out_md)
    toplevel = _gar_module().planned_workspace(workspace)
    if toplevel != workspace.resolve():
        plan_kernel_gate.clear_pipeline_required(toplevel, out_md)
    _warn_outside_checkout(out_md, toplevel)
    print(f"PASS: wrote {out_md}")
    return 0


def _warn_outside_checkout(out_md: Path, toplevel: Path) -> None:
    """Say so when the plan landed outside the checkout being planned.

    In a Cursor-Governance checkout `.cursor/plans` is a symlink to the primary
    SSOT clone's `docs/plans`, so `--out-md .cursor/plans/...` from a worktree
    wrote the plan into another checkout: it never reached this branch, and it
    dirtied the SSOT clone. Not fatal (a consumer may want that), but never silent.
    """
    real = out_md.resolve()
    try:
        real.relative_to(toplevel.resolve())
    except ValueError:
        print(
            f"WARN: plan written outside this checkout ({toplevel}): {real}. "
            "It will not be committed on this branch; in a Cursor-Governance "
            "checkout use --out-md docs/plans/<slug>.plan.md instead.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())
