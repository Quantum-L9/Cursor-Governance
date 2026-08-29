#!/usr/bin/env python3
"""Kernel hook that fires before pre-commit hooks and tests.

Not an L4 phase. L4 remains local-commit / no-mid-push / authorize-release.
This module is the only velocity-path latch for applying tree kernels
(Recursive Alignment + Validate & Repair). WIP/, docs/plans/, and
environment/program-execution/campaigns/ are corpus surfaces owned by
``/ff`` (Improve then RA then Validate & Repair) — this hook must not
L9_AGENT_REQUIRED them. L4 record-kernels is not the corpus apply path.

``precommit`` must run first in ``run_pr_precommit.sh`` and fail closed
before any other hook or test starts, so those checkers fire once.

Cursor (``CURSOR_AGENT`` / ``L9_GOVERNANCE_SURFACE=cursor`` / unset surface
with no Claude markers) does **not** take this latch. Tree kernels stay a
Claude Code / adapter-surface ceremony. Cursor scoped-commits after
``make precommit-repo`` without a kernel receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.kernel_receipt.v1"
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
#: Tree-kernel latch is adapter-surface only. Cursor is the primary plane
#: and must not stall commit/push on Recursive Alignment receipts.
ADAPTER_KERNEL_SURFACES = frozenset({"claude-code", "codex", "gemini", "manus"})
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


def changed_are_corpus_only(changed_paths: list[str]) -> bool:
    paths = [_rel_path(raw) for raw in changed_paths if raw.strip()]
    if not paths:
        return False
    return all(_is_corpus_path(path) for path in paths)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        out[label] = _sha256_file(path)
    return out


def load_receipt(root: Path) -> dict[str, Any] | None:
    path = receipt_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_receipt(root: Path, data: dict[str, Any]) -> Path:
    path = receipt_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def record(root: Path, *, gov: Path) -> dict[str, Any]:
    """Honor-system stamp after the agent applied the two tree kernels."""
    receipt = {
        "schema": SCHEMA,
        "head": _git_head(root),
        "kernel_shas": kernel_shas(gov),
        "applied_at": _utc_now(),
        "agent_id": os.environ.get("L9_MEMORY_AGENT_ID", ""),
        "phase": "recorded",
    }
    write_receipt(root, receipt)
    return receipt


def _git_head(root: Path) -> str:
    import subprocess

    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _agent_required_tree(root: Path) -> str:
    return (
        "=== L9_AGENT_REQUIRED ===\n"
        "ACTION: apply_kernels_then_precommit\n"
        "HOOK: ops/autonomy/kernel_gate.py precommit\n"
        f"WORKSPACE: {root}\n"
        "INSTRUCTIONS:\n"
        "  1. Apply kernels/Recursive Alignment.md to the finished local tree\n"
        "  2. Apply kernels/Validate & Repair.md independently on the same tree\n"
        "  3. Commit any revisions on this stacked branch (no push)\n"
        "  4. python3 ops/autonomy/kernel_gate.py record --workspace <this workspace>\n"
        "  5. Re-run the same command (make precommit-repo / make pr-check / make pr).\n"
        "     Hooks and tests run once after this hook passes.\n"
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
    """Return a failure message, or None when the tree-kernel receipt is valid.

    Receipt is bound to kernel file SHAs, not HEAD, so a later rewrite commit
    does not force a second LLM apply.
    """
    receipt = load_receipt(root)
    if receipt is None or receipt.get("schema") != SCHEMA:
        return _agent_required_tree(root)
    try:
        current = kernel_shas(gov)
    except RuntimeError as exc:
        return f"FAIL: {exc}\n"
    recorded = receipt.get("kernel_shas")
    if not isinstance(recorded, dict) or recorded != current:
        return (
            "FAIL: kernel-receipt kernel_shas do not match the live kernel files.\n"
            + _agent_required_tree(root)
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


def kernel_latch_required(*, env: dict[str, str] | None = None) -> bool:
    """True only on Claude Code / peer adapter runtimes.

    Cursor sessions set ``CURSOR_AGENT``. CI and a bare shell have neither
    that nor an adapter surface id — they skip, so a Cursor-authored PR is
    not blocked in GitHub Actions for a missing kernel receipt.
    """
    source = os.environ if env is None else env
    surface = (source.get("L9_GOVERNANCE_SURFACE") or "").strip().lower()
    if surface in ADAPTER_KERNEL_SURFACES:
        return True
    if source.get("CLAUDECODE") or source.get("CLAUDE_CODE_ENTRYPOINT"):
        return True
    if source.get("CLAUDE_CODE_REMOTE") == "true":
        return True
    if source.get("CLAUDE_CODE_SESSION_ID"):
        return True
    return False


def precommit(root: Path, gov: Path, changed_file: Path | None) -> int:
    if not kernel_latch_required():
        print(
            "OK: kernel hook skipped "
            "(Cursor / non-adapter surface; Claude Code owns this latch)"
        )
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
    receipt = record(workspace_root(args.workspace), gov=gov_root_from_env(args.gov_root))
    print(json.dumps(receipt, indent=2, sort_keys=True))
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
        help="stamp tree-kernel receipt after applying kernels",
    )
    rec.set_defaults(func=cmd_record)

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
