#!/usr/bin/env python3
"""Hydrate memory before either planning skill drafts.

Cursor ``beforeSubmitPrompt`` runs this after the skill router. When the
route (or an explicit CLI invoke) names ``l9-plan`` or ``l9-plan-simple``,
the hook calls the operator CLI — ``hydrate`` then ``conflicts`` — and
writes ``.l9/memory/plan-prefetch.json``. Planning skills cite that receipt
as ``MEMORY_PREFETCH`` before emit. SessionStart hydrate is not a substitute:
a plan can start hours later, on a different task, with a stale capsule.

This is the operator / hook adapter (ADR-0030). It is not
``memory.write_governed`` and it does not import a provider client.

Fail-open on the hook path: stdout is always ``{"continue": true}``. A
refused or unbound plane records SKIP/WARN; it does not block the prompt.
Kill switch: ``L9_PLAN_MEMORY_PREFETCH=0``.
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

SCHEMA = "l9.plan_memory_prefetch.v1"
RECEIPT_REL = Path(".l9/memory/plan-prefetch.json")
PLAN_SKILLS = frozenset({"l9-plan", "l9-plan-simple"})
FRESH_SECONDS = 900
PLAN_MODES = frozenset({"plan", "planning"})


def _enabled() -> bool:
    if os.environ.get("L9_PLAN_MEMORY_PREFETCH", "1").strip() == "0":
        return False
    memory = os.environ.get("L9_MEMORY_ENABLED") or os.environ.get("GRAPHITI_MEMORY_ENABLED")
    return (memory or "1").strip() != "0"


def _now() -> datetime:
    return datetime.now(UTC)


def extract_prompt(payload: dict[str, Any]) -> str:
    for key in ("prompt", "user_message", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _workspace(payload: dict[str, Any], explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    roots = payload.get("workspace_roots") or payload.get("workspaceRoots") or []
    if isinstance(roots, str):
        roots = [roots]
    if isinstance(roots, list):
        for raw in roots:
            if isinstance(raw, str) and raw.strip():
                return Path(raw).expanduser().resolve()
    return Path(os.getcwd()).resolve()


def _interpreter(gov_root: Path) -> Path:
    locked = gov_root / ".venv" / "bin" / "python"
    return locked if locked.is_file() else Path(sys.executable)


def _gov_root() -> Path:
    configured = os.environ.get("L9_GOVERNANCE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    ssot = Path.home() / ".cursor-governance"
    if (ssot / "ops" / "memory" / "cli.py").is_file():
        return ssot
    return Path(__file__).resolve().parents[2]


def route_skill_names(receipt: dict[str, Any] | None) -> set[str]:
    if not isinstance(receipt, dict) or receipt.get("status") != "routed":
        return set()
    decision = receipt.get("decision") or {}
    names: set[str] = set()
    primary = decision.get("primary") or {}
    if isinstance(primary, dict) and primary.get("name"):
        names.add(str(primary["name"]))
    for item in decision.get("supporting") or []:
        if isinstance(item, dict) and item.get("name"):
            names.add(str(item["name"]))
    return names


def load_route_receipt(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort read of the conversation route written by the skill router."""
    root = _gov_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from ops.skill_routing.session_locator import locator_from_payload, receipt_path_for
    except ImportError:
        return None
    locator = locator_from_payload(payload)
    if locator is None:
        return None
    path = receipt_path_for(locator)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def planning_requested(
    payload: dict[str, Any],
    *,
    route: dict[str, Any] | None = None,
    force: bool = False,
) -> bool:
    if force:
        return True
    for key in ("composer_mode", "composerMode", "mode"):
        if str(payload.get(key) or "").strip().lower() in PLAN_MODES:
            return True
    names = route_skill_names(route if route is not None else load_route_receipt(payload))
    if names & PLAN_SKILLS:
        return True
    prompt = extract_prompt(payload).lower()
    return prompt.startswith("/l9-plan") or prompt.startswith("/l9-plan-simple")


def conflicts_cite(document: dict[str, Any]) -> dict[str, Any]:
    """GMP Phase 0 MEMORY_PREFETCH fields — never episode names."""
    receipt = document.get("receipt")
    src = receipt if isinstance(receipt, dict) else document
    ns = document.get("namespace")
    namespace = ""
    if isinstance(ns, dict):
        namespace = str(ns.get("write_namespace_hint") or ns.get("repository_identity") or "")
    namespace = str(src.get("namespace") or namespace or "")
    conflicts = src.get("conflicts", document.get("conflicts"))
    if isinstance(conflicts, list):
        conflict_value: Any = len(conflicts)
    else:
        conflict_value = conflicts
    return {
        "namespace": namespace,
        "snapshot_digest": src.get("snapshot_digest") or src.get("current_snapshot_digest"),
        "checked_record_count": src.get("checked_record_count"),
        "conflicts": conflict_value,
        "policy_version": src.get("policy_version"),
    }


def _fresh(receipt: dict[str, Any], *, workspace: Path, task: str) -> bool:
    if receipt.get("schema") != SCHEMA:
        return False
    if str(receipt.get("workspace") or "") != str(workspace):
        return False
    if str(receipt.get("task") or "") != task:
        return False
    issued = str(receipt.get("issued_at") or "")
    try:
        then = datetime.fromisoformat(issued)
    except ValueError:
        return False
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    return (_now() - then).total_seconds() < FRESH_SECONDS


def memcli_argv(interpreter: Path, *args: str) -> list[str]:
    return [str(interpreter), "-m", "ops.memory.cli", *args]


def run_memcli(argv: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — locked interpreter + fixed module
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_json(stdout: str) -> dict[str, Any]:
    text = (stdout or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start < 0:
            return {}
        try:
            data = json.loads(text[start:])
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def prefetch(
    *,
    workspace: Path,
    gov_root: Path,
    task: str,
    skills: list[str],
    dry_run: bool = False,
    runner: Any = run_memcli,
) -> dict[str, Any]:
    target = workspace / RECEIPT_REL
    try:
        existing = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        existing = {}
    if isinstance(existing, dict) and _fresh(existing, workspace=workspace, task=task):
        existing["status"] = "REUSED"
        return existing

    interpreter = _interpreter(gov_root)
    hydrate_argv = memcli_argv(interpreter, "hydrate", task, "--workspace", str(workspace))
    conflicts_argv = memcli_argv(interpreter, "conflicts", "--workspace", str(workspace))
    if dry_run:
        body = {
            "schema": SCHEMA,
            "status": "DRY_RUN",
            "workspace": str(workspace),
            "task": task,
            "skills": skills,
            "issued_at": _now().isoformat(),
            "hydrate_argv": hydrate_argv,
            "conflicts_argv": conflicts_argv,
            "conflicts": {
                "namespace": "",
                "snapshot_digest": None,
                "checked_record_count": None,
                "conflicts": None,
                "policy_version": None,
            },
        }
        return body
    hydrate_proc = runner(hydrate_argv, cwd=gov_root)
    conflicts_proc = runner(conflicts_argv, cwd=gov_root)
    hydrate_doc = _parse_json(hydrate_proc.stdout)
    conflicts_doc = _parse_json(conflicts_proc.stdout)
    ok = hydrate_proc.returncode == 0 and conflicts_proc.returncode == 0
    body = {
        "schema": SCHEMA,
        "status": "OK" if ok else "WARN",
        "workspace": str(workspace),
        "task": task,
        "skills": skills,
        "issued_at": _now().isoformat(),
        "hydrate": {
            "status": hydrate_doc.get("status"),
            "ok": hydrate_doc.get("ok"),
            "returncode": hydrate_proc.returncode,
        },
        "conflicts": conflicts_cite(conflicts_doc),
        "conflicts_returncode": conflicts_proc.returncode,
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
    return body


def _skip_receipt(workspace: Path, reason: str) -> dict[str, Any]:
    body = {
        "schema": SCHEMA,
        "status": "SKIP",
        "reason": reason,
        "issued_at": _now().isoformat(),
        "workspace": str(workspace),
    }
    try:
        target = workspace / RECEIPT_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        pass
    return body


def run_for_payload(
    payload: dict[str, Any],
    *,
    workspace: Path | None = None,
    task: str = "",
    force: bool = False,
    dry_run: bool = False,
    runner: Any = run_memcli,
) -> dict[str, Any]:
    ws = _workspace(payload, workspace)
    if not _enabled():
        return _skip_receipt(ws, "disabled")
    route = load_route_receipt(payload) if not force else None
    if not planning_requested(payload, route=route, force=force):
        return {"status": "SKIP", "reason": "not a planning prompt"}
    skills = sorted(route_skill_names(route) & PLAN_SKILLS) or sorted(PLAN_SKILLS)
    objective = task or extract_prompt(payload) or "current task"
    return prefetch(
        workspace=ws,
        gov_root=_gov_root(),
        task=objective[:300],
        skills=skills,
        dry_run=dry_run,
        runner=runner,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=None)
    parser.add_argument("--task", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--hook", action="store_true", help="beforeSubmitPrompt adapter")
    args, _unknown = parser.parse_known_args(argv)

    payload: dict[str, Any] = {}
    read_stdin = args.hook or (not args.task and not args.force and not sys.stdin.isatty())
    if read_stdin:
        try:
            raw = sys.stdin.read()
        except OSError:
            raw = ""
        try:
            loaded = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            payload = loaded

    force = args.force or bool(args.task)
    result = run_for_payload(
        payload,
        workspace=args.workspace,
        task=args.task,
        force=force,
        dry_run=args.dry_run,
    )
    if args.hook or "conversation_id" in payload:
        print(json.dumps({"continue": True}))
    else:
        print(f"plan memory prefetch: {result.get('status')}")
        cite = result.get("conflicts")
        if isinstance(cite, dict) and cite.get("namespace"):
            print(
                "MEMORY_PREFETCH: "
                f"namespace={cite.get('namespace')} "
                f"snapshot_digest={cite.get('snapshot_digest')} "
                f"checked_record_count={cite.get('checked_record_count')} "
                f"conflicts={cite.get('conflicts')} "
                f"policy_version={cite.get('policy_version')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
