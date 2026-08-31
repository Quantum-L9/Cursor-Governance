#!/usr/bin/env python3
"""L4 local autonomy — stacked local commits, no mid-execution push.

SSOT doctrine: ops/autonomy/surface_profile.yaml (l4_local_autonomy).
State + receipts live under <workspace>/.l9/autonomy/ (gitignored).

Tree kernels are owned by ops/autonomy/kernel_gate.py (first step of
precommit-repo). They are not an L4 phase.

Phases:
  executing          — local commits on stacked branch; push/PR denied
  kernels_recorded   — compat only; record-kernels still stamps kernel_gate
  release_authorized — scoped push + PR using PULL_REQUEST_TEMPLATE allowed
"""

from __future__ import annotations

import argparse
import hashlib
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


def _hook_home_sentinels() -> frozenset[Path]:
    """Hook process dirs that are never a repo workspace (Cursor/Claude homes)."""
    home = Path.home().resolve()
    return frozenset({home, home / ".cursor", home / ".claude"})


def _cursor_project_slug(root: Path) -> str:
    return "-".join(root.resolve().parts).lstrip("-")


def _usable_dir(raw: object) -> Path | None:
    if not raw:
        return None
    try:
        path = Path(str(raw)).expanduser().resolve()
    except OSError:
        return None
    if path in _hook_home_sentinels() or not path.is_dir():
        return None
    return path


def _event_workspace_roots(event: dict[str, Any]) -> list[Path]:
    raw = event.get("workspace_roots") or event.get("workspaceRoots") or []
    if not isinstance(raw, list):
        return []
    out: list[Path] = []
    for item in raw:
        path = _usable_dir(item)
        if path is not None and path not in out:
            out.append(path)
    return out


def _pick_event_workspace(event: dict[str, Any], candidates: list[Path]) -> Path | None:
    """Prefer the root that matches this conversation's Cursor project folder."""
    if not candidates:
        return None
    transcript = str(event.get("transcript_path") or "").replace("/", "-")
    for cand in candidates:
        slug = _cursor_project_slug(cand)
        if slug and slug in transcript:
            return cand
    ssot = _usable_dir(Path.home() / ".cursor-governance")
    if ssot is not None:
        for cand in candidates:
            if cand == ssot:
                return cand
    return candidates[0]


def workspace_from_event(event: dict[str, Any]) -> Path:
    """Resolve workspace from a Claude/Cursor hook event, else cwd git root.

    Cursor beforeShellExecution often sends ``cwd=""`` and the real checkout in
    ``workspace_roots``. Empty cwd must not fall through to the hook process
    cwd (``~/.cursor`` / ``~/.claude``), which is not a git work tree.
    """
    tool_input = event.get("tool_input") or {}
    explicit: Path | None = None
    if isinstance(tool_input, dict):
        for key in ("cwd", "working_directory", "workspace"):
            explicit = _usable_dir(tool_input.get(key))
            if explicit is not None:
                break
    if explicit is None:
        for key in ("cwd", "working_directory", "workspace"):
            explicit = _usable_dir(event.get(key))
            if explicit is not None:
                break
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    for root in _event_workspace_roots(event):
        if root not in candidates:
            candidates.append(root)
    picked = _pick_event_workspace(event, candidates)
    if picked is not None:
        return picked
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


def _expand_state_dir(raw: str, root: Path) -> Path:
    text = raw.strip().replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def workspace_identity(root: Path) -> str:
    """Stable identity of the workspace an L4 state file belongs to.

    The resolved git work tree, because the L4 unit is the WORKTREE, not the
    repository: rule 49 gives one mutating agent one checkout, and two
    worktrees of the same repo are two independent L4 subjects.
    """
    return str(_validated_git_root(root))


def _workspace_slug(root: Path) -> str:
    """Directory segment that keeps one workspace's state out of another's."""
    identity = workspace_identity(root)
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    return f"{Path(identity).name}-{digest}"


def _autonomy_dir(root: Path) -> Path:
    """Resolve the L4 state directory.

    ``L9_AUTONOMY_STATE_DIR`` relocates state outside the worktree when set
    (template default: ``$HOME/.l9/autonomy``). Unset, or a leftover receipt
    that only exists under ``<workspace>/.l9/autonomy``, keeps the gitignored
    worktree fallback. This function never deletes the old receipt.

    A relocated directory is namespaced per workspace. It used to be shared:
    every repository on the machine read and wrote ONE ``~/.l9/autonomy``, and
    the state files carried ``stacked_branch`` but no workspace, so a release
    authorized in one repo satisfied ``release_allows_remote`` in a different
    repo whose branch happened to share the name. A fleet where every repo
    carries the same branch name made that the normal case rather than the
    edge one. Namespacing removes the collision; the identity check in
    :func:`_state_workspace_conflict` still refuses a file that reaches this
    workspace by any other route.
    """
    base = _validated_git_root(root)
    legacy = base.joinpath(".l9", "autonomy")
    env = os.environ.get("L9_AUTONOMY_STATE_DIR", "").strip()
    if env:
        chosen = _expand_state_dir(env, base)
        if chosen == legacy:
            return chosen
        scoped = chosen / _workspace_slug(root)
        if not (scoped / RECEIPT_FILENAME).is_file() and (legacy / RECEIPT_FILENAME).is_file():
            return legacy
        return scoped
    return legacy


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
    """The checked-out branch, including on a repository with no commits.

    `rev-parse --abbrev-ref HEAD` cannot answer for an unborn HEAD -- it fails
    with "ambiguous argument 'HEAD'". A freshly `git init`-ed repository is a
    legitimate state, and this runs inside the execution gate, so raising there
    turned every policy question in such a repository into an
    INTERNAL_EVALUATION_ERROR denial. `branch --show-current` answers without a
    commit; `rev-parse` stays the fallback for a detached HEAD, which
    `--show-current` reports as empty.
    """
    try:
        branch = _git(root, "branch", "--show-current")
    except RuntimeError:
        branch = ""
    if branch:
        return branch
    try:
        return _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    except RuntimeError:
        return ""


def current_head(root: Path) -> str:
    """The HEAD sha, or "" when HEAD is unborn or unreadable."""
    try:
        return _git(root, "rev-parse", "HEAD")
    except RuntimeError:
        return ""


#: Where a PR template may live in the RELEASED repository, in the order
#: `ops/scripts/open_pr_after_gate.sh` searches. GitHub's default filename is
#: `.github/pull_request_template.md` (this repo's only body).
#:
#: The governance clone's own template is the publisher's LAST resort and is
#: deliberately absent here: naming it in a receipt written for a consumer
#: would report the governance default as if it were that repo's template.
PR_TEMPLATE_CANDIDATES: tuple[str, ...] = (
    ".github/pull_request_template.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/PULL_REQUEST_TEMPLATE.md",
)


def resolve_pr_template(root: Path) -> str | None:
    """The released repo's own PR template, workspace-relative, or None.

    `null` is the correct and informative answer for a repository that ships no
    template — the publisher will fall back to the governance clone, and saying
    so honestly is what lets a reader tell the two cases apart. Previously this
    field was the literal string "PULL_REQUEST_TEMPLATE.md" in every receipt,
    whether or not the released repo had one.

    Existence is matched on the directory listing, not Path.is_file alone, so a
    case-insensitive volume cannot return `.github/PULL_REQUEST_TEMPLATE.md`
    for a file created as `pull_request_template.md`.
    """
    for rel in PR_TEMPLATE_CANDIDATES:
        candidate = root / rel
        parent = candidate.parent
        if not parent.is_dir():
            continue
        try:
            names = os.listdir(parent)
        except OSError:
            continue
        if Path(rel).name in names and candidate.is_file():
            return rel
    return None


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def write_autonomy_json(root: Path, filename: str, data: dict[str, Any]) -> None:
    """Write JSON under the resolved L4 state directory using an allowlisted filename only."""
    if filename not in {STATE_FILENAME, RECEIPT_FILENAME}:
        raise RuntimeError(f"refusing non-allowlisted L4 filename: {filename}")
    # Route through _autonomy_dir so L9_AUTONOMY_STATE_DIR is honoured on writes
    # (same path as load_phase / load_receipt) rather than hardcoding <workspace>/.l9/autonomy.
    autonomy_dir = _autonomy_dir(root)
    # Sonar-recognized sanitizer: realpath + commonpath (see render_principals.under_root).
    autonomy_base = os.path.realpath(str(autonomy_dir))
    os.makedirs(autonomy_base, exist_ok=True)
    target = os.path.realpath(os.path.join(autonomy_base, filename))
    if os.path.commonpath([autonomy_base, target]) != autonomy_base:
        raise RuntimeError(f"L4 state path escapes autonomy dir: {target}")
    # Stamp the subject. A state file that cannot name its own workspace cannot
    # be checked against the one asking to push, which is exactly how a receipt
    # written for one repo came to authorize another. Stamped in place, not on a
    # copy, so the dict a caller keeps (and returns) is the one on disk.
    data["workspace"] = workspace_identity(root)
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
        # Name the directory, not just the branch. A refusal that says only
        # "refused on 'main'" reads as a policy error when the real cause is
        # usually that the command ran from the wrong tree -- a hook, a
        # subshell, or a compound command that changed directory. IMP-06's
        # second clause: say which repository was resolved, and name the flag
        # that retargets it.
        raise RuntimeError(
            f"L4 begin refused on '{branch}' in {root} — "
            "create/checkout a stacked feature branch first, "
            "or did you mean --workspace <target repo>?"
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
        try:
            from kernel_gate import record as stamp_kernel_hook

            stamp_kernel_hook(root, gov=Path(__file__).resolve().parents[2])
        except Exception as exc:
            state["kernel_hook_stamp"] = f"failed:{exc}"
    else:
        state["phase"] = PHASE_EXECUTING
        state["blockers"] = ["kernel_gate_failed"]
    write_autonomy_json(root, STATE_FILENAME, state)
    return state


def authorize_release(root: Path) -> dict[str, Any]:
    state = load_phase(root)
    if state is None:
        raise RuntimeError("no L4 phase — run: python3 ops/autonomy/l4_local.py begin")
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
        "pr_template": resolve_pr_template(root),
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
            "then: python3 ops/autonomy/l4_local.py begin && "
            "python3 ops/autonomy/l4_local.py authorize-release. "
            "Kernels fire as the first precommit-repo hook "
            "(ops/autonomy/kernel_gate.py), not as an L4 phase."
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
        f"L4 phase={phase}: no mid-execution push/PR. Finish locally, then "
        "authorize-release. Kernels fire in kernel_gate.py before precommit."
    )


def _state_workspace_conflict(root: Path, doc: dict[str, Any] | None, kind: str) -> str | None:
    """Reason to refuse `doc`, or None when it belongs to this workspace.

    Fails closed on an UNSTAMPED file as well as a foreign one. An unstamped
    file predates workspace stamping, and at that time state was shared
    machine-wide — so it is precisely the file that cannot be shown to belong
    here. Re-authorizing is cheap; honouring another workspace's release is not.
    """
    if not doc:
        return None
    ours = workspace_identity(root)
    stamped = str(doc.get("workspace") or "").strip()
    if stamped == ours:
        return None
    if not stamped:
        return (
            f"L4 {kind} carries no workspace stamp — it predates workspace-scoped "
            "state, when one directory was shared by every repository on the "
            "machine. Re-run: python3 ops/autonomy/l4_local.py begin && "
            "python3 ops/autonomy/l4_local.py authorize-release"
        )
    return (
        f"L4 {kind} belongs to workspace {stamped!r}, current is {ours!r} — a "
        "release authorized in another checkout does not authorize this one. "
        "Re-run begin + authorize-release here."
    )


def release_allows_remote(root: Path) -> tuple[bool, str]:
    """Return (allowed, reason) for git push / gh pr create."""
    if os.environ.get("L9_L4_LOCAL_AUTONOMY", "1").strip() in {"0", "false", "False", "no"}:
        return True, "L9_L4_LOCAL_AUTONOMY disabled"
    if os.environ.get("L9_LOCAL_PUSH_AUTHORIZED", "").strip():
        return True, "L9_LOCAL_PUSH_AUTHORIZED breakglass"

    receipt = load_receipt(root)
    state = load_phase(root)
    # Identity before contents. Branch name and HEAD sha are not identity: every
    # repository in a fleet may carry the same branch name, and that is what let
    # one repo's receipt authorize a push in another.
    for doc, kind in ((receipt, "receipt"), (state, "phase")):
        conflict = _state_workspace_conflict(root, doc, kind)
        if conflict:
            return False, conflict

    branch = current_branch(root)
    if receipt:
        decided = _allow_from_receipt(root, receipt, state, branch)
        if decided is not None:
            return decided
    return _allow_from_phase(state)


def status_dict(root: Path) -> dict[str, Any]:
    allowed, reason = release_allows_remote(root)
    receipt = load_receipt(root)
    head = current_head(root)
    pinned = str((receipt or {}).get("head_sha") or "")
    stale = bool(pinned and head and pinned != head)
    return {
        "workspace": str(root),
        "branch": current_branch(root),
        "head": head,
        "phase": (load_phase(root) or {}).get("phase"),
        "receipt": receipt,
        "state": load_phase(root),
        "remote_allowed": allowed,
        "reason": reason,
        "stale": stale,
        "kernels_required": [KERNEL_RECURSIVE_ALIGNMENT, KERNEL_VALIDATE_REPAIR],
        "pr_template": resolve_pr_template(root),
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
