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
    "Apply `kernels/Improve.md`, then `kernels/Recursive Alignment.md`, "
    "then `kernels/Validate & Repair.md`, overwrite this path, write "
    "`kernel_pass` (those three blocks in ran_at order). Store plans apply "
    "on /ff, not as a mid-session inject. Do not create another plan."
)
REQUIRED_REL = Path(".l9") / "plan" / "kernel-pass-required.json"
REQUIRED_SCHEMA = "l9.plan.kernel_pass_required.v1"
PIPELINE_REL = Path(".l9") / "plan" / "pipeline-required.json"
PIPELINE_SCHEMA = "l9.plan.pipeline_required.v1"
MTIME_WINDOW_S = 120 * 60
PLAN_SUFFIX = ".plan.md"
CAMPAIGN_RE = re.compile(r"(?:^|[\s;&|])make(?:\s+\S+)*\s+campaign(?:\s|$)", re.I)
RUN_CAMPAIGN_RE = re.compile(
    r"(?:^|[\s;&|])(?:python3?|\S*python3?)\s+\S*run_campaign\.py\b",
    re.I,
)
PEC_RE = re.compile(r"\bpec\.py\b")
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
    if CHECK_INPUT_RE.search(command) or PEC_RE.search(command):
        return False
    return bool(RUN_CAMPAIGN_RE.search(command) or CAMPAIGN_RE.search(command))


def argv_plan_paths(command: str) -> list[Path]:
    found: list[Path] = []
    for match in PLAN_PATH_RE.finditer(command):
        found.append(Path(match.group(1)).expanduser())
    return found


def execute_verdict(event: dict[str, Any]) -> tuple[str, str]:
    command = extract_command(event)
    workspace = workspace_from_event(event)
    if pipeline_latch_denies(command, workspace):
        latch = load_pipeline_required(workspace) or {}
        reason = str(latch.get("reason") or "plan is not admitted")
        return (
            "deny",
            "plan pipeline latch is set ("
            + reason
            + "). Run skills/l9-plan-simple/scripts/run_plan_pipeline.py. "
            "The latch clears only after that pipeline passes.",
        )
    if not is_campaign_execute(command):
        return "allow", ""
    to_check = argv_plan_paths(command)
    required = load_required_plan(workspace)
    if required is not None:
        to_check.append(required)
    for path in to_check:
        if path.is_file() and plan_fails(path):
            return "deny", (f"plan kernel_pass FAIL for {path}. {INJECT_TEXT}")
    return "allow", ""


def _admit_plan(path: Path) -> list[str]:
    """Load simple-plan admission without stealing the kernel checker's modules.

    ``validate_plan_kernel_receipt`` imports ``paths`` from ``skills/l9-plan``.
    ``admit_plan`` imports a different ``paths`` from ``skills/l9-plan-simple``.
    A shared ``sys.modules['paths']`` makes admission fail closed for the wrong
    reason and then sets the Build latch.
    """
    scripts = repo_root() / "skills" / "l9-plan-simple" / "scripts"
    script_text = str(scripts)
    displaced: dict[str, Any] = {}
    for name in ("paths", "plan_sections", "validate_plan_section_receipt", "admit_plan"):
        loaded = sys.modules.get(name)
        loaded_file = str(getattr(loaded, "__file__", "") or "")
        if loaded is not None and script_text not in loaded_file:
            displaced[name] = sys.modules.pop(name)
    if script_text not in sys.path:
        sys.path.insert(0, script_text)
    try:
        import admit_plan

        return admit_plan.check_plan(path)
    except Exception as exc:
        return [f"G_ADMIT: checker unavailable: {exc}"]
    finally:
        for name, module in displaced.items():
            sys.modules[name] = module


def pipeline_required_path(workspace: Path) -> Path:
    return workspace / PIPELINE_REL


def write_pipeline_required(workspace: Path, reason: str, plan: str | None) -> None:
    path = pipeline_required_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    bound: str | None = None
    if plan:
        try:
            bound = str(Path(plan).expanduser().resolve())
        except OSError:
            bound = plan
    body = {
        "schema": PIPELINE_SCHEMA,
        "reason": reason,
        "plan": bound,
        "repair": "skills/l9-plan-simple/scripts/run_plan_pipeline.py",
        "written_at": datetime.now(UTC).isoformat(),
    }
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def load_pipeline_required(workspace: Path) -> dict[str, Any] | None:
    """Return the Build latch, or None when the workspace has no latch.

    An unreadable latch stays set. Build must not treat a corrupt file as clear.
    """
    path = pipeline_required_path(workspace)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": PIPELINE_SCHEMA, "reason": "pipeline latch is unreadable", "plan": None}
    if not isinstance(data, dict):
        return {"schema": PIPELINE_SCHEMA, "reason": "pipeline latch is invalid", "plan": None}
    return data


def clear_pipeline_required(workspace: Path, plan: Path | None = None) -> bool:
    """Remove the latch after the pipeline admits ``plan``.

    A latch bound to a different plan stays. A latch with no plan (the host
    plan tool wrote one before a file existed) clears for the plan that passed.
    """
    path = pipeline_required_path(workspace)
    data = load_pipeline_required(workspace)
    if data is None or not path.is_file():
        return False
    bound = data.get("plan")
    if plan is not None and isinstance(bound, str) and bound.strip():
        try:
            if Path(bound).expanduser().resolve() != plan.expanduser().resolve():
                return False
        except OSError:
            return False
    path.unlink()
    return True


def is_pipeline_repair(command: str) -> bool:
    return "run_plan_pipeline.py" in command


def is_controller_or_publish(command: str) -> bool:
    if PEC_RE.search(command) or CHECK_INPUT_RE.search(command):
        return True
    return bool(re.search(r"(?:^|[\s;&|])make(?:\s+\S+)*\s+pr(?:\s|$)", command, re.I))


def is_build_admission(command: str) -> bool:
    """True for commands that execute a plan: campaign, GMP, or a .plan.md argv."""
    if is_campaign_execute(command):
        return True
    if re.search(r"gmp_executor\.py|\bl9-plan-build\b", command, re.I):
        return True
    return bool(argv_plan_paths(command))


def pipeline_latch_denies(command: str, workspace: Path) -> bool:
    if is_pipeline_repair(command) or is_controller_or_publish(command):
        return False
    if not is_build_admission(command):
        return False
    return load_pipeline_required(workspace) is not None


def handle_post_tool_use(event: dict[str, Any]) -> None:
    # Store-plan kernel apply stays /ff-owned. This latch is the plan pipeline
    # admission, a different file, and it does not delete the plan.
    workspace = workspace_from_event(event)
    tool = str(event.get("tool_name") or event.get("toolName") or "")
    path = written_path(event)
    if path is not None and path.name.endswith(PLAN_SUFFIX):
        if path.is_file():
            errors = _admit_plan(path)
            if errors:
                write_pipeline_required(workspace, "; ".join(errors[:8]), str(path))
        return
    if "CreatePlan" in tool or tool.lower() in {"create_plan", "createplan"}:
        write_pipeline_required(
            workspace,
            "host plan tool payload seen; file gate still required",
            None,
        )


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
        if not pipeline_required_path(ws).is_file():
            errors.append("postToolUse must write the pipeline latch for an unadmitted plan")
        os.environ["L9_PLANS_STORE"] = str(plan.parent)
        try:
            handle_post_tool_use(event)
            if required_path(ws).is_file():
                errors.append("postToolUse must not latch store plans (/ff owns corpus kernels)")
        finally:
            os.environ.pop("L9_PLANS_STORE", None)

        # Kernel cases below are independent of the pipeline latch postToolUse just set.
        latch = pipeline_required_path(ws)
        if latch.is_file():
            latch.unlink()

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
        pr_perm, _ = execute_verdict({"cwd": str(ws), "command": "OPEN_PR=0 make pr"})
        if pr_perm != "allow":
            errors.append("OPEN_PR=0 make pr must allow")

        write_pipeline_required(ws, "unadmitted plan", str(plan))
        latched, latched_msg = execute_verdict(
            {"cwd": str(ws), "command": "make campaign INTENT=x.md"}
        )
        if latched != "deny" or "pipeline latch" not in latched_msg:
            errors.append(f"campaign must deny while the pipeline latch is set: {latched}")
        gmp, gmp_msg = execute_verdict(
            {"cwd": str(ws), "command": "python3 workflows/gmp_executor.py"}
        )
        if gmp != "deny" or "pipeline latch" not in gmp_msg:
            errors.append(f"gmp executor must deny while the pipeline latch is set: {gmp}")
        repair, _ = execute_verdict(
            {
                "cwd": str(ws),
                "command": "python3 skills/l9-plan-simple/scripts/run_plan_pipeline.py",
            }
        )
        if repair != "allow":
            errors.append("run_plan_pipeline.py must be allowed while the latch is set")
        pec_latched, _ = execute_verdict({"cwd": str(ws), "command": "python3 pec.py claim"})
        if pec_latched != "allow":
            errors.append("pec.py must allow while the pipeline latch is set")
        if not clear_pipeline_required(ws, plan) or pipeline_required_path(ws).is_file():
            errors.append("clear_pipeline_required did not remove a matching latch")
        write_pipeline_required(ws, "other plan", str(plan))
        if clear_pipeline_required(ws, ws / "other.plan.md"):
            errors.append("clear must not drop a latch bound to a different plan")
        if not pipeline_required_path(ws).is_file():
            errors.append("mismatched clear removed the latch")
        write_pipeline_required(ws, "host plan tool payload seen", None)
        if not clear_pipeline_required(ws, plan) or pipeline_required_path(ws).is_file():
            errors.append("an unbound latch must clear after the pipeline admits a plan")

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
