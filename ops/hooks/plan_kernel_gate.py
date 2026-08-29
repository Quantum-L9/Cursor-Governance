#!/usr/bin/env python3
"""Plan kernel-pass hook: postToolUse latch + execute deny + inject prefix."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

INJECT_TEXT = (
    "Apply `kernels/Improve.md`, overwrite this path, re-read it, apply "
    "`kernels/Validate & Repair.md`, overwrite the same path, write "
    "`kernel_pass` into this file. Do not create another plan."
)
REQUIRED_REL = Path(".l9") / "plan" / "kernel-pass-required.json"
REQUIRED_SCHEMA = "l9.plan.kernel_pass_required.v1"
MTIME_WINDOW_S = 120 * 60
PLAN_SUFFIX = ".plan.md"
CAMPAIGN_RE = re.compile(r"(?:^|[\s;&|])make(?:\s+\S+)*\s+campaign(?:\s|$)", re.I)
RUN_CAMPAIGN_RE = re.compile(
    r"(?:^|[\s;&|])(?:python3?|\S*python3?)\s+\S*run_campaign\.py\b",
    re.I,
)
PEC_RE = re.compile(r"\bpec\.py\b")
PR_CHECK_RE = re.compile(r"\bmake(?:\s+\S+)*\s+pr-check\b", re.I)
CHECK_INPUT_RE = re.compile(r"campaign-check-input")
PLAN_PATH_RE = re.compile(r"(\S+\.plan\.md)")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_checker():
    scripts = repo_root() / "skills" / "l9-plan" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import validate_plan_kernel_receipt as checker

    return checker


def plans_store() -> Path | None:
    override = os.environ.get("L9_PLANS_STORE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    home = Path.home() / ".cursor" / "plans"
    try:
        if home.exists():
            return home.resolve()
    except OSError:
        return None
    return None


def is_store_plan(path: Path) -> bool:
    store = plans_store()
    if store is None:
        return False
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    if not resolved.name.endswith(PLAN_SUFFIX):
        return False
    return resolved == store or store in resolved.parents


def workspace_from_event(event: dict[str, Any]) -> Path:
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    for key in ("cwd", "working_directory", "workspace"):
        raw = None
        if isinstance(tool_input, dict):
            raw = tool_input.get(key)
        if not raw:
            raw = event.get(key)
        if raw:
            candidate = Path(str(raw)).expanduser()
            if candidate.is_dir():
                return candidate.resolve()
    roots = event.get("workspace_roots") or event.get("workspaceRoots") or []
    if isinstance(roots, list) and roots:
        candidate = Path(str(roots[0])).expanduser()
        if candidate.is_dir():
            return candidate.resolve()
    return Path.cwd().resolve()


def written_path(event: dict[str, Any]) -> Path | None:
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    candidates: list[object] = []
    if isinstance(tool_input, dict):
        candidates.extend(
            [
                tool_input.get("path"),
                tool_input.get("file_path"),
                tool_input.get("filePath"),
            ]
        )
        files = tool_input.get("files")
        if isinstance(files, list) and files:
            candidates.append(files[0])
    candidates.extend(
        [
            event.get("path"),
            event.get("file_path"),
            event.get("filePath"),
        ]
    )
    for raw in candidates:
        if isinstance(raw, str) and raw.strip():
            return Path(raw.strip()).expanduser()
    return None


def required_path(workspace: Path) -> Path:
    return workspace / REQUIRED_REL


def write_required(workspace: Path, plan: Path) -> Path:
    dest = required_path(workspace)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": REQUIRED_SCHEMA,
        "bound_path": str(plan.resolve()),
        "failed_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return dest


def load_required_plan(workspace: Path) -> Path | None:
    dest = required_path(workspace)
    if not dest.is_file():
        return None
    try:
        data = json.loads(dest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    raw = data.get("bound_path") if isinstance(data, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        return None
    return Path(raw.strip())


def plan_fails(path: Path) -> bool:
    checker = _load_checker()
    return bool(checker.check_plan(path))


def _todos_unbuilt(todos: Any) -> bool:
    if not isinstance(todos, list) or not todos:
        return True
    for item in todos:
        if not isinstance(item, dict):
            return True
        status = str(item.get("status", "pending")).lower()
        if status in {"pending", "in_progress"}:
            return True
    return False


def newest_recent_unbuilt_failing() -> Path | None:
    store = plans_store()
    if store is None or not store.is_dir():
        return None
    checker = _load_checker()
    cutoff = time.time() - MTIME_WINDOW_S
    newest: tuple[float, Path] | None = None
    for path in store.glob("*.plan.md"):
        if path.name == "_TEMPLATE.plan.md":
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _body = checker.parse_frontmatter(text)
        if not _todos_unbuilt(fm.get("todos")):
            continue
        if not checker.check_plan(path):
            continue
        if newest is None or mtime > newest[0]:
            newest = (mtime, path)
    return newest[1] if newest else None


def inject_block(workspace: Path) -> str:
    # Corpus kernels (plans / WIP / campaigns) fire on /ff, not mid-session.
    del workspace
    return ""


def extract_command(event: dict[str, Any]) -> str:
    command = str(event.get("command") or event.get("full_command") or "")
    if command.strip():
        return command
    tool_input = event.get("tool_input") or event.get("toolInput") or {}
    if isinstance(tool_input, dict):
        return str(tool_input.get("command") or tool_input.get("cmd") or "")
    return ""


def is_campaign_execute(command: str) -> bool:
    stripped = command.lstrip()
    if stripped.startswith("git ") or stripped.startswith("git\t"):
        return False
    if CHECK_INPUT_RE.search(command) or PEC_RE.search(command) or PR_CHECK_RE.search(command):
        return False
    return bool(RUN_CAMPAIGN_RE.search(command) or CAMPAIGN_RE.search(command))


def argv_plan_paths(command: str) -> list[Path]:
    found: list[Path] = []
    for match in PLAN_PATH_RE.finditer(command):
        found.append(Path(match.group(1)).expanduser())
    return found


def execute_verdict(event: dict[str, Any]) -> tuple[str, str]:
    command = extract_command(event)
    if not is_campaign_execute(command):
        return "allow", ""
    workspace = workspace_from_event(event)
    to_check = argv_plan_paths(command)
    required = load_required_plan(workspace)
    if required is not None:
        to_check.append(required)
    for path in to_check:
        if path.is_file() and plan_fails(path):
            return "deny", (f"plan kernel_pass FAIL for {path}. {INJECT_TEXT}")
    return "allow", ""


def handle_post_tool_use(event: dict[str, Any]) -> None:
    # Store-plan kernel apply is /ff-owned. Do not latch Improve/V&R here.
    del event
    return


def handle_execute_gate(event: dict[str, Any]) -> int:
    permission, message = execute_verdict(event)
    payload: dict[str, Any] = {"permission": permission}
    if message:
        payload["user_message"] = message
    print(json.dumps(payload))
    return 0


def _self_test() -> int:
    checker = _load_checker()
    root = repo_root()
    fixtures = root / "skills" / "l9-plan" / "fixtures"
    errors: list[str] = []
    passing = fixtures / "plan_kernel_pass.plan.md"
    if checker.check_plan(passing):
        errors.append(f"expected PASS for {passing}: {checker.check_plan(passing)}")
    for name, needle in (
        ("plan_kernel_fail_etc.plan.md", "G_PLAN_ETC"),
        ("plan_kernel_fail_either.plan.md", "G_PLAN_EITHER_OR"),
        ("plan_kernel_fail_empty_deltas.plan.md", "G_PLAN_DELTAS"),
        ("plan_kernel_fail_sha.plan.md", "G_PLAN_SHA"),
    ):
        errs = checker.check_plan(fixtures / name)
        blob = " ".join(errs)
        if needle not in blob:
            errors.append(f"{name} missing {needle}: {errs}")

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        plan = ws / "docs" / "plans" / "demo_aaaaaaaa.plan.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("# no receipt\n", encoding="utf-8")
        event = {
            "cwd": str(ws),
            "tool_input": {"path": str(plan), "command": "make campaign INTENT=x.md"},
        }
        handle_post_tool_use(event)
        if required_path(ws).is_file():
            errors.append("postToolUse wrote required.json for a non-store path")
        os.environ["L9_PLANS_STORE"] = str(plan.parent)
        try:
            handle_post_tool_use(event)
            if required_path(ws).is_file():
                errors.append("postToolUse must not latch store plans (/ff owns corpus kernels)")
        finally:
            os.environ.pop("L9_PLANS_STORE", None)

        allow, _msg = execute_verdict({"cwd": str(ws), "command": "make campaign INTENT=x.md"})
        if allow != "allow":
            errors.append("campaign without latch must allow")

        write_required(ws, passing if passing.is_file() else plan)
        # passing fixture must not deny
        deny_perm, _ = execute_verdict(
            {
                "cwd": str(ws),
                "command": "make campaign INTENT=x.md",
            }
        )
        if deny_perm != "allow":
            errors.append("campaign with passing required.json must allow")

        fail_plan = fixtures / "plan_kernel_fail_sha.plan.md"
        write_required(ws, fail_plan)
        deny_perm, msg = execute_verdict({"cwd": str(ws), "command": "make campaign INTENT=x.md"})
        if deny_perm != "deny" or "kernel_pass FAIL" not in msg:
            errors.append(f"expected deny for failing required.json: {deny_perm} {msg}")

        pec_perm, _ = execute_verdict({"cwd": str(ws), "command": "python3 pec.py claim"})
        if pec_perm != "allow":
            errors.append("pec.py must allow")
        pr_perm, _ = execute_verdict({"cwd": str(ws), "command": "make pr-check"})
        if pr_perm != "allow":
            errors.append("make pr-check must allow")

    if errors:
        for err in errors:
            print(f"FAIL: {err}", file=sys.stderr)
        return 1
    print("PASS: plan_kernel_gate self_test")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    raw = sys.stdin.read()
    try:
        event: dict[str, Any] = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        event = {}
    if "--execute-gate" in sys.argv:
        return handle_execute_gate(event)
    handle_post_tool_use(event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
