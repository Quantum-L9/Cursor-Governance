#!/usr/bin/env python3
"""Kernel hook that fires before pre-commit hooks and tests.

Not an L4 phase. L4 remains local-commit / no-mid-push / authorize-release,
and ``authorize-release`` does not require this receipt
(CANONICAL_LAW KERNEL_PRECOMMIT_HOOK_V1). This module is the only
velocity-path latch for applying tree kernels (Recursive Alignment +
Validate & Repair). WIP/, docs/plans/, and
environment/program-execution/campaigns/ are corpus surfaces owned by
``/ff`` (Improve then RA then Validate & Repair) — this hook must not
L9_AGENT_REQUIRED them. L4 record-kernels is not the corpus apply path.

``precommit`` must run first in ``run_pr_precommit.sh`` and fail closed
before any other hook or test starts, so those checkers fire once.

Every local surface takes this latch, including a bare shell: the receipt
lives under gitignored ``.l9/``, so only unmarked CI skips. A CI job that
sets a known surface marker (the unit tests) still latches.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from ops.autonomy import kernel_predicates  # noqa: E402
from ops.autonomy.kernel_predicates import (  # noqa: E402
    APPLY_REL,
    APPLY_SCHEMA,
    ReportError,
)
from ops.autonomy.surface_detect import (  # noqa: E402
    ADAPTER_KERNEL_SURFACES,
    kernel_latch_surface,
)


class ReceiptLoadError(RuntimeError):
    """An existing kernel receipt could not be read as a JSON object.

    Distinct from absence: a missing file is not a claim. A file that is
    unreadable, not JSON, or not an object *is* a claim that cannot be
    re-derived, and must fail closed (CANONICAL_LAW §6.2.9 item 6).
    """


#: v1 was a stamp: schema, head, kernel file SHAs, a timestamp. Every field was
#: ambient or about files the agent never touched, so writing the claim was
#: cheaper than doing the work (INC-2026-09-14-001). v2 binds the claim to a
#: hashed, path-confined apply report the verifier re-derives.
SCHEMA_V1 = "l9.kernel_receipt.v1"
SCHEMA = "l9.kernel_receipt.v2"
RECEIPT_REL = Path(".l9") / "autonomy" / "kernel-receipt.json"
KERNELS: tuple[tuple[str, str], ...] = (
    ("recursive_alignment", "kernels/Recursive Alignment.md"),
    ("validate_repair", "kernels/Validate & Repair.md"),
)
PLAN_FIXTURE_PREFIX = "skills/l9-plan/fixtures/"
#: Corpus kernels fire on /ff shelf, not at precommit or L4.
CORPUS_SKIP_PREFIXES = (
    "WIP/",
    "docs/plans/",
    "environment/program-execution/campaigns/",
)
#: Same prefixes as CORPUS_SKIP_PREFIXES (pipeline-audit surfaces).
KERNEL_EXEMPT_PREFIXES = CORPUS_SKIP_PREFIXES
#: Compat alias. Live latch is kernel_latch_surface (local + marked CI tests).
#: Surface ids live in ops/autonomy/surface_detect.py (SSOT).
ADAPTER_SURFACES = ADAPTER_KERNEL_SURFACES
#: Executable-plan templates are not Cursor plans. Do not require kernel_pass.
PLAN_SKIP_PREFIXES = (
    PLAN_FIXTURE_PREFIX,
    "environment/contracts/execution/templates/",
    "docs/plans/_TEMPLATE.plan.md",
    *KERNEL_EXEMPT_PREFIXES,
)


def _rel_path(raw: str) -> str:
    return raw.strip().lstrip("./")


def _is_corpus_path(rel: str) -> bool:
    norm = _rel_path(rel)
    for prefix in CORPUS_SKIP_PREFIXES:
        if norm == prefix.rstrip("/") or norm.startswith(prefix):
            return True
    return False


def adapter_tree_kernels_required(environ: Mapping[str, str] | None = None) -> bool:
    """Compat alias of ``kernel_latch_required`` (adapter ``make pr`` only)."""
    source = os.environ if environ is None else environ
    return kernel_latch_required(env=source)


def changed_are_corpus_only(changed_paths: list[str]) -> bool:
    paths = [_rel_path(raw) for raw in changed_paths if raw.strip()]
    if not paths:
        return False
    return all(_is_corpus_path(path) for path in paths)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gov_root_from_env(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("GOV_ROOT") or os.environ.get("L9_GOV_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def workspace_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("L9_L4_WORKSPACE") or os.environ.get("WS")
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd().resolve()


def receipt_path(root: Path) -> Path:
    return root / RECEIPT_REL


def kernel_shas(gov: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for label, rel in KERNELS:
        path = gov / rel
        if not path.is_file():
            raise RuntimeError(f"kernel file missing: {path}")
        out[label] = kernel_predicates.sha256_file(path)
    return out


def load_receipt(root: Path) -> dict[str, Any] | None:
    """Load the kernel receipt, or None when no file exists.

    Absence is a first-class answer (the corpus exemption). An existing file
    that cannot be parsed as a JSON object is a present-and-false claim:
    raise ``ReceiptLoadError`` so callers cannot collapse it into absence.
    """
    path = receipt_path(root)
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except OSError as exc:
        raise ReceiptLoadError(f"kernel receipt exists but is unreadable: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReceiptLoadError(
            f"kernel receipt exists but is not valid JSON: {path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ReceiptLoadError(
            f"kernel receipt exists but is not a JSON object: {path} ({type(data).__name__})"
        )
    return data


def write_receipt(root: Path, data: dict[str, Any]) -> Path:
    path = receipt_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def record(
    root: Path,
    *,
    gov: Path,
    report: Path | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Record the tree-kernel claim, bound to a hashed apply report.

    The report is the artifact that constitutes the claim. It is validated
    BEFORE anything is written, so a failed predicate leaves no receipt behind:
    a caller cannot get a usable receipt by ignoring an exception.

    This does not prove judgment — nothing can re-run an LLM apply
    deterministically. It moves the claim from unfalsifiable to falsifiable: a
    forged ``deltas`` entry names a specific path with a specific note, which a
    reviewer can contradict.

    Args:
        root: Workspace root.
        gov: Governance root.
        report: Apply report path (defaults to APPLY_REL).
        changed_paths: List of changed file paths for diff coverage check.
            If provided, verifies deltas cover the git diff (minus exempt paths).

    Raises:
        ReportError: the report is missing, escapes ``.l9/autonomy/``, has bad
            frontmatter, has empty deltas, or names paths that do not exist.
    """
    root_r = root.resolve()
    target = report if report is not None else Path(APPLY_REL)
    confined = kernel_predicates.confine_report_path(root_r, target)
    structure = kernel_predicates.report_structure(root_r, confined)
    if structure:
        raise ReportError("; ".join(structure))
    # Raises on a delta path that does not exist in this tree.
    deltas = kernel_predicates.load_validated_deltas(root_r, confined)

    live_changed = changed_paths if changed_paths is not None else discover_changed_paths(root_r)
    diff_errors = kernel_predicates.deltas_cover_diff(deltas, live_changed)
    if diff_errors:
        raise ReportError("; ".join(diff_errors))
    data = kernel_predicates.parse_apply_report(confined)
    seed_errors = kernel_predicates.run_v2_predicates(root_r, data, changed_paths=live_changed)
    if seed_errors:
        raise ReportError("; ".join(seed_errors))

    receipt = {
        "schema": SCHEMA,
        "report_rel": confined.relative_to(root_r).as_posix(),
        "report_sha256": kernel_predicates.sha256_file(confined),
        "deltas": deltas,
        "kernel_shas": kernel_shas(gov),
        "applied_at": _utc_now(),
        "agent_id": os.environ.get("L9_MEMORY_AGENT_ID", ""),
        "phase": "recorded",
        # Recorded metadata, deliberately NOT the binding: a later rewrite
        # commit must not force a second LLM apply.
        "head": _git_head(root_r),
        # Record the changed paths that were covered (for audit)
        "changed_paths_count": len(live_changed),
        "changed_paths": live_changed,
    }
    write_receipt(root_r, receipt)
    return receipt


def _git_head(root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def discover_changed_paths(root: Path) -> list[str]:
    """Live git change set used when ``--changed-file`` is omitted.

    Union of ``git diff HEAD`` and untracked files, minus ``.l9/``. Omitting
    ``--changed-file`` is therefore not a skip of ``deltas_cover_diff``.
    """
    found: list[str] = []
    seen: set[str] = set()

    def _add(raw: str) -> None:
        rel = raw.strip()
        while rel.startswith("./"):
            rel = rel[2:]
        if not rel or rel.startswith(".l9/") or rel in seen:
            return
        seen.add(rel)
        found.append(rel)

    for args in (
        ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
    ):
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                _add(line)
    return found


def record_command(root: Path, gov: Path) -> str:
    """A record command that is runnable from a CONSUMER workspace.

    The documented delegated form — ``make -C "$HOME/.cursor-governance" pr
    WS="$(pwd)"`` — leaves the reader standing in the consumer tree, where
    ``ops/autonomy/kernel_gate.py`` does not exist and the ambient ``python3``
    is not the locked governance interpreter. Emit the governance script path
    and that interpreter explicitly, plus the workspace this receipt belongs
    to, so the printed line can simply be pasted.
    """
    locked = gov / ".venv" / "bin" / "python"
    interpreter = str(locked) if locked.is_file() else "python3"
    script = gov / "ops" / "autonomy" / "kernel_gate.py"
    # --report is explicit even though it defaults: the printed line teaches the
    # contract, and the artifact is the point of the command.
    return (
        f'{interpreter} {script} record --workspace "{root}" '
        f'--report "{APPLY_REL.as_posix()}" --changed-file .l9/pr/changed-files.txt'
    )


def template_command(root: Path, gov: Path) -> str:
    locked = gov / ".venv" / "bin" / "python"
    interpreter = str(locked) if locked.is_file() else "python3"
    script = gov / "ops" / "autonomy" / "kernel_gate.py"
    return f'{interpreter} {script} apply-report-template --workspace "{root}"'


def apply_report_template() -> str:
    """Skeleton for the apply report.

    This template is **intentionally unstampable** — empty deltas, findings,
    passes_run, and null unknowns all fail the hardened predicates. Filling
    the template with real content is the work.

    Phase 4 hardening: v2 reports require:
    - Non-empty deltas (both kernels) with real notes
    - Non-empty findings OR audit_scope + passes_run explaining clean state
    - Required passes (context_and_scope_lock, reconciliation_and_convergence)
    - Explicit unknowns key (empty list is OK)
    """
    return (
        "---\n"
        f"schema: {APPLY_SCHEMA}\n"
        "kernels:\n"
        "  - recursive_alignment\n"
        "  - validate_repair\n"
        "convergence_status: converged  # converged | partial | blocked\n"
        "deltas:\n"
        "  # One entry per file you actually changed. Non-empty, real paths.\n"
        "  # Both kernels must have at least one delta.\n"
        "  - path: relative/path/you/changed.py\n"
        "    kernel: recursive_alignment  # or validate_repair\n"
        "    note: what the kernel changed and why  # MUST BE REAL, NOT TEMPLATE\n"
        "findings: []  # UNSTAMPABLE: empty findings require audit_scope + passes_run\n"
        "passes_run: []  # UNSTAMPABLE: must include required passes\n"
        "passes_skipped: []  # List passes you intentionally skipped and why\n"
        "unknowns: null  # UNSTAMPABLE: must be list (empty OK)\n"
        "audit_scope: null  # Required when findings is empty\n"
        "---\n"
        "\n"
        "## Recursive Alignment\n"
        "\n"
        "What the kernel surfaced on this tree, and what you did about it.\n"
        "\n"
        "## Validate & Repair\n"
        "\n"
        "What you validated, what failed, what you repaired. Report Passed /\n"
        "Failed / Skipped / Unknown honestly — a clean report with no validation\n"
        "run is the failure mode this gate exists to catch.\n"
    )


def _agent_required_tree(root: Path, gov: Path) -> str:
    return (
        "=== L9_AGENT_REQUIRED ===\n"
        "ACTION: apply_kernels_then_precommit\n"
        "HOOK: ops/autonomy/kernel_gate.py precommit\n"
        f"WORKSPACE: {root}\n"
        "INSTRUCTIONS:\n"
        "  1. Apply kernels/Recursive Alignment.md to the finished local tree\n"
        "  2. Apply kernels/Validate & Repair.md independently on the same tree\n"
        "  3. Commit any revisions on this stacked branch (no push)\n"
        f"  4. Write the apply report at {APPLY_REL.as_posix()} — frontmatter\n"
        f"     ({APPLY_SCHEMA}, both kernels, convergence_status) and one deltas\n"
        "     entry per file you changed (path + kernel + note). For a skeleton:\n"
        f"       {template_command(root, gov)}\n"
        f"  5. {record_command(root, gov)}\n"
        "  6. Re-run the same command (make precommit-repo / make pr-check / make pr).\n"
        "     Hooks and tests run once after this hook passes.\n"
        "The report IS the receipt. record refuses an absent report, empty deltas, a\n"
        "path outside .l9/autonomy/, or a delta naming a file that does not exist —\n"
        "and verify re-hashes it, so editing the report afterwards fails the gate.\n"
        "Kernels are not an L4 phase. Do not record-kernels / IMPROVE_RECORD to apply them.\n"
        "Do not run pre-commit or pytest first.\n"
        "=== END L9_AGENT_REQUIRED ===\n"
    )


def _agent_required_plan(path: Path) -> str:
    return (
        "=== L9_AGENT_REQUIRED ===\n"
        "ACTION: apply_plan_kernels_then_precommit\n"
        f"PLAN: {path}\n"
        "INSTRUCTIONS:\n"
        "  Apply kernels/Improve.md, then kernels/Recursive Alignment.md, then\n"
        "  kernels/Validate & Repair.md, overwrite this path, write kernel_pass\n"
        "  (three blocks, ran_at in that order). Then re-run make precommit-repo.\n"
        "docs/plans, WIP, and campaigns skip this latch (/ff owns them).\n"
        "=== END L9_AGENT_REQUIRED ===\n"
    )


def verify_tree(root: Path, gov: Path) -> str | None:
    """Return a failure message, or None when the tree-kernel receipt holds.

    Every check re-derives from live files. Nothing recorded in the receipt is
    taken on trust: the report is re-hashed and its predicates re-run, so a
    receipt that was valid when written fails once the report it names is
    edited or deleted.

    Binding is the report digest plus the kernel file SHAs, not HEAD, so a
    later rewrite commit does not force a second LLM apply.
    """
    try:
        receipt = load_receipt(root)
    except ReceiptLoadError as exc:
        return f"FAIL: {exc}\n" + _agent_required_tree(root, gov)
    if receipt is None:
        return _agent_required_tree(root, gov)
    schema = receipt.get("schema")
    if schema == SCHEMA_V1:
        return (
            f"FAIL: kernel-receipt is {SCHEMA_V1}, which asserted a kernel apply with no\n"
            "      artifact behind it and is no longer accepted. Write the apply report\n"
            f"      and re-record to produce {SCHEMA}.\n" + _agent_required_tree(root, gov)
        )
    if schema != SCHEMA:
        return _agent_required_tree(root, gov)
    try:
        current = kernel_shas(gov)
    except RuntimeError as exc:
        return f"FAIL: {exc}\n"
    recorded = receipt.get("kernel_shas")
    if not isinstance(recorded, dict) or recorded != current:
        return (
            "FAIL: kernel-receipt kernel_shas do not match the live kernel files.\n"
            + _agent_required_tree(root, gov)
        )
    recorded_paths = receipt.get("changed_paths")
    if isinstance(recorded_paths, list) and recorded_paths:
        live_changed = [str(p) for p in recorded_paths]
    else:
        live_changed = discover_changed_paths(root)
    errors = kernel_predicates.run_predicates(root, receipt, changed_paths=live_changed)
    if errors:
        detail = "\n".join(f"  {err}" for err in errors)
        return (
            "FAIL: kernel apply report no longer satisfies its own receipt.\n"
            f"{detail}\n" + _agent_required_tree(root, gov)
        )
    return None


def _load_plan_checker(gov: Path):
    scripts = gov / "skills" / "l9-plan" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import validate_plan_kernel_receipt as checker

    return checker


def verify_plans(changed_paths: list[str], *, workspace: Path, gov: Path) -> str | None:
    plans: list[Path] = []
    for raw in changed_paths:
        rel = raw.strip().lstrip("./")
        if not rel.endswith(".plan.md"):
            continue
        if _is_corpus_path(rel):
            continue
        if any(rel.startswith(prefix) for prefix in PLAN_SKIP_PREFIXES):
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = workspace / raw
        if candidate.is_file():
            plans.append(candidate)
    if not plans:
        return None
    try:
        checker = _load_plan_checker(gov)
    except Exception as exc:
        return f"FAIL: plan kernel checker unavailable ({exc})\n"
    for path in plans:
        errors = checker.check_plan(path)
        if errors:
            detail = "\n".join(f"  {err}" for err in errors)
            return f"FAIL: plan kernel_pass {path}\n{detail}\n{_agent_required_plan(path)}"
    return None


def read_changed_file(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def kernel_latch_required(*, env: Mapping[str, str] | None = None) -> bool:
    """True on every local surface; false for unmarked CI.

    A bare local ``make pr`` must not skip. Unmarked CI skips so a
    missing gitignored kernel receipt cannot fail GitHub Actions.

    Marker resolution is owned by ``ops.autonomy.surface_detect``.
    """
    return kernel_latch_surface(env)


def precommit(root: Path, gov: Path, changed_file: Path | None) -> int:
    if not kernel_latch_required():
        print("OK: kernel hook skipped (CI; local surfaces own this latch)")
        return 0
    changed = read_changed_file(changed_file)
    if changed_are_corpus_only(changed):
        print("OK: kernel hook skipped (corpus-only changeset; /ff owns WIP/plans/campaigns)")
        return 0
    tree_fail = verify_tree(root, gov)
    if tree_fail:
        sys.stderr.write(tree_fail)
        return 2
    plan_fail = verify_plans(changed, workspace=root, gov=gov)
    if plan_fail:
        sys.stderr.write(plan_fail)
        return 2
    print("OK: kernel hook (tree receipt + changed plan receipts)")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    root = workspace_root(args.workspace)
    gov = gov_root_from_env(args.gov_root)
    report = Path(args.report) if args.report else None
    changed_paths = (
        read_changed_file(Path(args.changed_file))
        if args.changed_file
        else discover_changed_paths(root)
    )
    try:
        receipt = record(root, gov=gov, report=report, changed_paths=changed_paths)
    except ReportError as exc:
        sys.stderr.write(f"FAIL: apply report rejected — {exc}\n")
        sys.stderr.write("      No receipt was written.\n")
        sys.stderr.write(_agent_required_tree(root, gov))
        return 2
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def cmd_apply_report_template(args: argparse.Namespace) -> int:
    root = workspace_root(args.workspace)
    target = root / APPLY_REL
    if args.write:
        if target.exists() and not args.force:
            sys.stderr.write(f"FAIL: {target} already exists (use --force to overwrite)\n")
            return 2
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(apply_report_template(), encoding="utf-8")
        print(f"template written: {target}")
        print("Fill in deltas with the files you actually changed; empty deltas fail record.")
        return 0
    sys.stdout.write(apply_report_template())
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = workspace_root(args.workspace)
    gov = gov_root_from_env(args.gov_root)
    fail = verify_tree(root, gov)
    if fail:
        sys.stderr.write(fail)
        return 2
    print("OK: kernel receipt matches live kernel SHAs")
    return 0


def cmd_precommit(args: argparse.Namespace) -> int:
    changed = Path(args.changed_file) if args.changed_file else None
    return precommit(
        workspace_root(args.workspace),
        gov_root_from_env(args.gov_root),
        changed,
    )


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--workspace", default=None)
    shared.add_argument("--gov-root", default=None)
    parser = argparse.ArgumentParser(description=__doc__, parents=[shared])
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser(
        "record",
        parents=[shared],
        help="record tree-kernel receipt from a hashed apply report",
    )
    rec.add_argument(
        "--report",
        default=None,
        help=f"apply report path, workspace-relative (default {APPLY_REL.as_posix()})",
    )
    rec.add_argument(
        "--changed-file",
        default=None,
        help="path to file listing changed paths (one per line) for diff coverage check",
    )
    rec.set_defaults(func=cmd_record)

    tpl = sub.add_parser(
        "apply-report-template",
        parents=[shared],
        help="print (or --write) an apply-report skeleton",
    )
    tpl.add_argument("--write", action="store_true", help=f"write it to {APPLY_REL.as_posix()}")
    tpl.add_argument("--force", action="store_true", help="overwrite an existing report")
    tpl.set_defaults(func=cmd_apply_report_template)

    ver = sub.add_parser("verify", parents=[shared], help="check tree-kernel receipt only")
    ver.set_defaults(func=cmd_verify)

    pre = sub.add_parser(
        "precommit",
        parents=[shared],
        help="first hook of precommit-repo (tree + plans)",
    )
    pre.add_argument("--changed-file", default=None)
    pre.set_defaults(func=cmd_precommit)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
