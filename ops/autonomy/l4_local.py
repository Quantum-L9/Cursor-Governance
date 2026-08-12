#!/usr/bin/env python3
"""L4 local autonomy — stacked local commits, no mid-execution push, kernel gate.

SSOT doctrine: ops/autonomy/surface_profile.yaml (l4_local_autonomy).
State + receipts live under <workspace>/.l9/autonomy/ (gitignored).

Phases:
  executing          — local commits on stacked branch; push/PR denied
  kernels_recorded   — Recursive Alignment + Validate & Repair recorded
  release_authorized — scoped push + PR using PULL_REQUEST_TEMPLATE allowed
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.l4_local_phase/v1"
RECEIPT_SCHEMA = "l9.l4_local_release_receipt/v1"
STATE_REL = Path(".l9/autonomy/l4-local-phase.json")
RECEIPT_REL = Path(".l9/autonomy/l4-release-receipt.json")

KERNEL_RECURSIVE_ALIGNMENT = "kernels/Recursive Alignment.md"
KERNEL_VALIDATE_REPAIR = "kernels/Validate & Repair.md"

PHASE_EXECUTING = "executing"
PHASE_KERNELS = "kernels_recorded"
PHASE_RELEASE = "release_authorized"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def workspace_root(explicit: str | None = None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser()
    else:
        env = os.environ.get("L9_L4_WORKSPACE") or os.environ.get("WS")
        candidate = Path(env).expanduser() if env else Path.cwd()
    return _validated_git_root(candidate)


def workspace_from_event(event: dict[str, Any]) -> Path:
    """Resolve workspace from a Claude/Cursor hook event, else cwd git root."""
    tool_input = event.get("tool_input") or {}
    if isinstance(tool_input, dict):
        for key in ("cwd", "working_directory", "workspace"):
            val = tool_input.get(key)
            if val:
                return Path(str(val)).expanduser().resolve()
    for key in ("cwd", "working_directory", "workspace"):
        val = event.get(key)
        if val:
            return Path(str(val)).expanduser().resolve()
    return workspace_root()


def _validated_git_root(candidate: Path) -> Path:
    """Resolve a workspace only when it is an existing git work tree."""
    root = candidate.resolve()
    if not root.is_dir():
        raise RuntimeError(f"L4 workspace is not a directory: {root}")
    git_meta = root / ".git"
    if not git_meta.exists():
        raise RuntimeError(f"L4 workspace is not a git work tree: {root}")
    return root


STATE_FILENAME = "l4-local-phase.json"
RECEIPT_FILENAME = "l4-release-receipt.json"


def _autonomy_dir(root: Path) -> Path:
    """Return <git-root>/.l9/autonomy after validating the work tree."""
    base = _validated_git_root(root)
    return base.joinpath(".l9", "autonomy")


def state_path(root: Path) -> Path:
    return _autonomy_dir(root).joinpath(STATE_FILENAME)


def receipt_path(root: Path) -> Path:
    return _autonomy_dir(root).joinpath(RECEIPT_FILENAME)


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def current_branch(root: Path) -> str:
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD")


def current_head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def write_autonomy_json(root: Path, filename: str, data: dict[str, Any]) -> None:
    """Write JSON under .l9/autonomy using an allowlisted filename only."""
    if filename not in {STATE_FILENAME, RECEIPT_FILENAME}:
        raise RuntimeError(f"refusing non-allowlisted L4 filename: {filename}")
    base = _validated_git_root(root)
    # Sonar-recognized sanitizer: realpath + commonpath (see render_principals.under_root).
    autonomy_base = os.path.realpath(os.path.join(str(base), ".l9", "autonomy"))
    os.makedirs(autonomy_base, exist_ok=True)
    target = os.path.realpath(os.path.join(autonomy_base, filename))
    if os.path.commonpath([autonomy_base, target]) != autonomy_base:
        raise RuntimeError(f"L4 state path escapes autonomy dir: {target}")
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(payload)


def load_phase(root: Path) -> dict[str, Any] | None:
    return load_json(state_path(root))


def load_receipt(root: Path) -> dict[str, Any] | None:
    return load_json(receipt_path(root))


def begin(
    root: Path,
    *,
    contract_id: str | None = None,
    stacked_base: str | None = None,
) -> dict[str, Any]:
    branch = current_branch(root)
    if branch in {"main", "master", "HEAD"}:
        raise RuntimeError(
            f"L4 begin refused on '{branch}' — create/checkout a stacked feature branch first"
        )
    state = {
        "schema": SCHEMA,
        "phase": PHASE_EXECUTING,
        "contract_id": contract_id or f"l4-{_utc_now()}",
        "stacked_branch": branch,
        "stacked_base": stacked_base or os.environ.get("PR_BASE", "origin/main"),
        "started_at": _utc_now(),
        "kernels": {
            "recursive_alignment": {"path": KERNEL_RECURSIVE_ALIGNMENT, "status": "pending"},
            "validate_repair": {"path": KERNEL_VALIDATE_REPAIR, "status": "pending"},
        },
        "head_sha_at_begin": current_head(root),
    }
    write_autonomy_json(root, STATE_FILENAME, state)
    rp = receipt_path(root)
    if rp.is_file():
        rp.unlink()
    return state


def record_kernels(
    root: Path,
    *,
    recursive_alignment: str = "passed",
    validate_repair: str = "passed",
    notes: str | None = None,
) -> dict[str, Any]:
    state = load_phase(root)
    if state is None:
        state = begin(root)
    if state.get("phase") not in {PHASE_EXECUTING, PHASE_KERNELS, PHASE_RELEASE}:
        raise RuntimeError(f"invalid phase for kernel record: {state.get('phase')}")
    for label, status in (
        ("recursive_alignment", recursive_alignment),
        ("validate_repair", validate_repair),
    ):
        if status not in {"passed", "failed"}:
            raise RuntimeError(f"kernel status must be passed|failed, got {status!r}")
        entry = dict(state.setdefault("kernels", {}).get(label) or {})
        entry["status"] = status
        entry["ran_at"] = _utc_now()
        entry["path"] = (
            KERNEL_RECURSIVE_ALIGNMENT if label == "recursive_alignment" else KERNEL_VALIDATE_REPAIR
        )
        state["kernels"][label] = entry
    if notes:
        state["kernel_notes"] = notes
    ra = state["kernels"]["recursive_alignment"]["status"]
    vr = state["kernels"]["validate_repair"]["status"]
    if ra == "passed" and vr == "passed":
        state["phase"] = PHASE_KERNELS
        state.pop("blockers", None)
    else:
        state["phase"] = PHASE_EXECUTING
        state["blockers"] = ["kernel_gate_failed"]
    write_autonomy_json(root, STATE_FILENAME, state)
    return state


def authorize_release(root: Path) -> dict[str, Any]:
    state = load_phase(root)
    if state is None:
        raise RuntimeError("no L4 phase — run: python3 ops/autonomy/l4_local.py begin")
    kernels = state.get("kernels") or {}
    ra = (kernels.get("recursive_alignment") or {}).get("status")
    vr = (kernels.get("validate_repair") or {}).get("status")
    if ra != "passed" or vr != "passed":
        raise RuntimeError(
            "release denied — record both kernels as passed first "
            f"(recursive_alignment={ra}, validate_repair={vr}). "
            "Run kernels/Recursive Alignment.md then kernels/Validate & Repair.md "
            "on the finished local tree, then: "
            "python3 ops/autonomy/l4_local.py record-kernels"
        )
    branch = current_branch(root)
    if branch != state.get("stacked_branch"):
        raise RuntimeError(
            f"branch drift: phase started on {state.get('stacked_branch')!r}, now on {branch!r}"
        )
    head = current_head(root)
    state["phase"] = PHASE_RELEASE
    state["authorized_at"] = _utc_now()
    state["head_sha"] = head
    write_autonomy_json(root, STATE_FILENAME, state)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "phase": PHASE_RELEASE,
        "contract_id": state.get("contract_id"),
        "stacked_branch": branch,
        "stacked_base": state.get("stacked_base"),
        "head_sha": head,
        "authorized_at": state["authorized_at"],
        "kernels": state.get("kernels"),
        "pr_template": "PULL_REQUEST_TEMPLATE.md",
        "doctrine": "l4_local_autonomy",
    }
    write_autonomy_json(root, RECEIPT_FILENAME, receipt)
    return receipt


def pr_open_for_branch(root: Path, branch: str | None = None) -> bool:
    """True when gh reports an open PR for the current branch (remediation path)."""
    del branch  # branch inferred by gh from HEAD
    proc = subprocess.run(
        ["gh", "pr", "view", "--json", "state", "-q", ".state"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return False
    return proc.stdout.strip().upper() == "OPEN"


def _allow_from_receipt(
    root: Path, receipt: dict[str, Any], state: dict[str, Any] | None, branch: str
) -> tuple[bool, str] | None:
    if receipt.get("phase") != PHASE_RELEASE:
        return None
    if receipt.get("stacked_branch") and receipt["stacked_branch"] != branch:
        return False, (
            f"L4 receipt is for branch {receipt['stacked_branch']!r}, "
            f"current is {branch!r} — begin a new L4 phase or switch branch"
        )
    if state and state.get("phase") == PHASE_RELEASE and state.get("stacked_branch") == branch:
        return True, "L4 release_authorized"
    if receipt.get("head_sha") == current_head(root):
        return True, "L4 receipt matches HEAD"
    if pr_open_for_branch(root, branch):
        return True, "L4 remediation push on open PR"
    return False, (
        "L4 receipt stale (HEAD moved after authorize without open PR). "
        "Re-run kernels + authorize-release, or open PR from authorized tip first."
    )


def _allow_from_phase(state: dict[str, Any] | None) -> tuple[bool, str]:
    if state is None:
        return False, (
            "L4 local autonomy: mid-execution remote denied. "
            "Commit locally on a stacked branch, finish the program/contract, "
            "run kernels/Recursive Alignment.md then kernels/Validate & Repair.md, "
            "then: python3 ops/autonomy/l4_local.py begin && "
            "python3 ops/autonomy/l4_local.py record-kernels && "
            "python3 ops/autonomy/l4_local.py authorize-release"
        )
    phase = state.get("phase")
    if phase == PHASE_RELEASE:
        return True, "L4 release_authorized (phase)"
    if phase == PHASE_KERNELS:
        return False, (
            "L4 kernels recorded but release not authorized — run: "
            "python3 ops/autonomy/l4_local.py authorize-release"
        )
    return False, (
        f"L4 phase={phase}: no mid-execution push/PR. Finish locally, run "
        "Recursive Alignment + Validate & Repair, then authorize-release."
    )


def release_allows_remote(root: Path) -> tuple[bool, str]:
    """Return (allowed, reason) for git push / gh pr create."""
    if os.environ.get("L9_L4_LOCAL_AUTONOMY", "1").strip() in {"0", "false", "False", "no"}:
        return True, "L9_L4_LOCAL_AUTONOMY disabled"
    if os.environ.get("L9_LOCAL_PUSH_AUTHORIZED", "").strip():
        return True, "L9_LOCAL_PUSH_AUTHORIZED breakglass"

    receipt = load_receipt(root)
    state = load_phase(root)
    branch = current_branch(root)
    if receipt:
        decided = _allow_from_receipt(root, receipt, state, branch)
        if decided is not None:
            return decided
    return _allow_from_phase(state)


def status_dict(root: Path) -> dict[str, Any]:
    allowed, reason = release_allows_remote(root)
    return {
        "workspace": str(root),
        "branch": current_branch(root),
        "head": current_head(root),
        "phase": (load_phase(root) or {}).get("phase"),
        "receipt": load_receipt(root),
        "state": load_phase(root),
        "remote_allowed": allowed,
        "reason": reason,
        "kernels_required": [KERNEL_RECURSIVE_ALIGNMENT, KERNEL_VALIDATE_REPAIR],
        "pr_template": "PULL_REQUEST_TEMPLATE.md",
    }


def cmd_begin(args: argparse.Namespace) -> int:
    state = begin(
        workspace_root(args.workspace),
        contract_id=args.contract_id,
        stacked_base=args.base,
    )
    print(json.dumps(state, indent=2))
    return 0


def cmd_record_kernels(args: argparse.Namespace) -> int:
    state = record_kernels(
        workspace_root(args.workspace),
        recursive_alignment=args.recursive_alignment,
        validate_repair=args.validate_repair,
        notes=args.notes,
    )
    print(json.dumps(state, indent=2))
    return 0


def cmd_authorize(args: argparse.Namespace) -> int:
    receipt = authorize_release(workspace_root(args.workspace))
    print(json.dumps(receipt, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(json.dumps(status_dict(workspace_root(args.workspace)), indent=2))
    return 0


def cmd_check_remote(args: argparse.Namespace) -> int:
    allowed, reason = release_allows_remote(workspace_root(args.workspace))
    print(json.dumps({"allowed": allowed, "reason": reason}, indent=2))
    return 0 if allowed else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="L4 local autonomy phase / release receipt CLI")
    p.add_argument("--workspace", default=None, help="Workspace root (default: cwd / WS)")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("begin", help="Start L4 local execution on current stacked branch")
    b.add_argument("--contract-id", default=None)
    b.add_argument("--base", default=None, help="Stacked base ref (default PR_BASE/origin/main)")
    b.set_defaults(func=cmd_begin)

    k = sub.add_parser(
        "record-kernels",
        help="Record Recursive Alignment + Validate & Repair results",
    )
    k.add_argument("--recursive-alignment", default="passed", choices=["passed", "failed"])
    k.add_argument("--validate-repair", default="passed", choices=["passed", "failed"])
    k.add_argument("--notes", default=None)
    k.set_defaults(func=cmd_record_kernels)

    a = sub.add_parser("authorize-release", help="Authorize push/PR after kernels passed")
    a.set_defaults(func=cmd_authorize)

    s = sub.add_parser("status", help="Show L4 phase + remote eligibility")
    s.set_defaults(func=cmd_status)

    c = sub.add_parser("check-remote", help="Exit 0 if push/PR allowed, else 2")
    c.set_defaults(func=cmd_check_remote)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
