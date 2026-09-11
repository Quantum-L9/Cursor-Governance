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
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = "l9.plan_memory_prefetch.v1"
RECEIPT_REL = Path(".l9/memory/plan-prefetch.json")
PLAN_SKILLS = frozenset({"l9-plan", "l9-plan-simple"})
FRESH_SECONDS = 900
PLAN_MODES = frozenset({"plan", "planning"})

# --- Bounded fail-open budget ------------------------------------------------
# The Cursor slot for this hook is 20s (ops/hooks/hooks.json.template), but the
# memory control plane gives EVERY child call its own 30s timeout
# (ops/memory/control_plane_client.py). Sequential unbounded children could
# therefore burn the whole slot inside the first call and let Cursor kill the
# adapter before it wrote a receipt or printed {"continue": true} — the
# advertised fail-open path could not actually execute. One outer deadline now
# governs every child: no call may outlive what remains of it, and
# EMIT_RESERVE_SECONDS is what the hook keeps for itself to record DEGRADED,
# write the receipt, and continue.
HOOK_SLOT_SECONDS = 20.0
EMIT_RESERVE_SECONDS = 4.0
PREFETCH_DEADLINE_SECONDS = HOOK_SLOT_SECONDS - EMIT_RESERVE_SECONDS
PER_CALL_CAP_SECONDS = 6.0
MIN_CALL_SECONDS = 1.0
#: Shell convention for "killed on timeout"; never a memory-plane exit code.
TIMEOUT_RETURNCODE = 124

# Planner-facing context bounds (mirrors the SessionStart adapter,
# ops/graphiti/hydration/compile_session_packet.py).
CONTEXT_SECTION_LIMIT = 6
CONTEXT_SECTION_CHARS = 900
CONTEXT_BUDGET_CHARS = 4000
SEARCH_LIMIT = 6

#: Memory states the planner must be able to tell apart. A no-hit is memory
#: answering "nothing relevant"; DEGRADED is memory not answering at all. They
#: were once both reported as a bare WARN/OK pair, so a silent transport
#: failure was indistinguishable from a genuinely empty namespace.
STATE_HIT = "HIT"
STATE_NO_HIT = "NO_HIT"
STATE_DEGRADED = "DEGRADED"
STATE_CONFLICT = "CONFLICT"
STATE_CLEAN = "CLEAN"


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


def hydrate_state(document: dict[str, Any], returncode: int) -> str:
    """HIT / NO_HIT / DEGRADED from a canonical hydrate receipt.

    ``ops.memory.cli hydrate`` exits 0 only for the two answering statuses
    (``OK``/``NO_HITS``); anything else — unbound runtime, timeout, refused
    namespace, invalid receipt — is memory failing to answer, which is not the
    same fact as an empty namespace and must not be reported as one.
    """
    if returncode != 0:
        return STATE_DEGRADED
    status = str(document.get("status") or "").upper()
    if status not in {"OK", "NO_HITS"}:
        return STATE_DEGRADED
    record_ids = document.get("record_ids")
    count = document.get("record_count")
    records = (
        len(record_ids)
        if isinstance(record_ids, list)
        else (count if isinstance(count, int) else 0)
    )
    if records or document.get("continuation"):
        return STATE_HIT
    return STATE_NO_HIT


def conflicts_state(cite: dict[str, Any], returncode: int) -> str:
    """CONFLICT only when the authoritative service reports conflict evidence."""
    if returncode != 0:
        return STATE_DEGRADED
    conflicts = cite.get("conflicts")
    if isinstance(conflicts, int) and conflicts > 0:
        return STATE_CONFLICT
    if conflicts is None:
        return STATE_DEGRADED
    return STATE_CLEAN


def search_context(document: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    """Bounded planner-facing context from a canonical search receipt.

    ``ops.memory.cli search`` ("canonical search (full records)") emits the
    record through the same front door — ``outcome_document`` keeps the raw
    receipt — and is the only sanctioned content seam available to this hook.
    ``hydrate`` deliberately emits an integration-receipt shape of ids,
    digests and statuses with **no content** (``CanonicalHydration.as_dict``),
    and this adapter runs under the ambient interpreter from a
    ``#!/usr/bin/env python3`` shim, so it cannot import ``ops.memory``
    in-process the way the SessionStart adapter does. Nothing here reaches
    behind ``ops/memory`` and no provider client is imported.
    """
    receipt = document.get("receipt")
    if not isinstance(receipt, dict):
        return [], 0
    sections: list[dict[str, Any]] = []
    used = 0
    for hit in receipt.get("hits") or []:
        if len(sections) >= CONTEXT_SECTION_LIMIT or used >= CONTEXT_BUDGET_CHARS:
            break
        if not isinstance(hit, dict):
            continue
        record = hit.get("record")
        if not isinstance(record, dict):
            continue
        content = str(record.get("content") or "").strip()
        if not content:
            continue
        room = min(CONTEXT_SECTION_CHARS, CONTEXT_BUDGET_CHARS - used)
        text = content[:room]
        used += len(text)
        sections.append(
            {
                "record_id": str(record.get("record_id") or "")[:64],
                "memory_class": str(record.get("memory_class") or ""),
                "namespace": str(record.get("namespace") or ""),
                "content": text,
                "truncated": len(text) < len(content),
            }
        )
    return sections, used


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


def _text(stream: Any) -> str:
    if isinstance(stream, bytes):
        return stream.decode("utf-8", errors="replace")
    return stream if isinstance(stream, str) else ""


def run_memcli(
    argv: list[str], *, cwd: Path, timeout: float = PER_CALL_CAP_SECONDS
) -> subprocess.CompletedProcess[str]:
    """One bounded child. ``TimeoutExpired`` propagates to ``call_memcli``."""
    return subprocess.run(  # noqa: S603 — locked interpreter + fixed module
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


class Deadline:
    """One outer budget shared by every child call of a single prefetch."""

    def __init__(self, seconds: float = PREFETCH_DEADLINE_SECONDS) -> None:
        self._end = time.monotonic() + max(0.0, seconds)

    def remaining(self) -> float:
        return max(0.0, self._end - time.monotonic())

    def budget(self, cap: float = PER_CALL_CAP_SECONDS) -> float:
        return min(cap, self.remaining())


def call_memcli(
    runner: Any, argv: list[str], *, cwd: Path, deadline: Deadline
) -> subprocess.CompletedProcess[str]:
    """Run one child inside what is left of the outer deadline.

    Below ``MIN_CALL_SECONDS`` the call is not attempted at all: starting a
    child that cannot finish only guarantees the reserve is spent too.
    """
    budget = deadline.budget()
    if budget < MIN_CALL_SECONDS:
        return subprocess.CompletedProcess(
            argv, TIMEOUT_RETURNCODE, stdout="", stderr="prefetch deadline exhausted"
        )
    try:
        return runner(argv, cwd=cwd, timeout=budget)
    except subprocess.TimeoutExpired as expired:
        # Bounded fail-open: a hung or unbound memory runtime becomes DEGRADED
        # evidence on the receipt, never a hook Cursor has to kill. Caught here
        # rather than inside run_memcli so an injected runner is bounded too.
        return subprocess.CompletedProcess(
            argv,
            TIMEOUT_RETURNCODE,
            stdout=_text(expired.stdout),
            stderr="memory CLI timed out",
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
    deadline_seconds: float = PREFETCH_DEADLINE_SECONDS,
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
    search_argv = memcli_argv(
        interpreter, "search", task, "--workspace", str(workspace), "--limit", str(SEARCH_LIMIT)
    )
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
            "search_argv": search_argv,
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

    deadline = Deadline(deadline_seconds)
    hydrate_proc = call_memcli(runner, hydrate_argv, cwd=gov_root, deadline=deadline)
    hydrate_doc = _parse_json(hydrate_proc.stdout)
    h_state = hydrate_state(hydrate_doc, hydrate_proc.returncode)

    # Content only matters when hydration found something. Skipping the search
    # on NO_HIT/DEGRADED leaves the remaining budget to the conflicts call.
    context: list[dict[str, Any]] = []
    context_chars = 0
    search_returncode: int | None = None
    if h_state == STATE_HIT:
        search_proc = call_memcli(runner, search_argv, cwd=gov_root, deadline=deadline)
        search_returncode = search_proc.returncode
        if search_proc.returncode == 0:
            context, context_chars = search_context(_parse_json(search_proc.stdout))

    conflicts_proc = call_memcli(runner, conflicts_argv, cwd=gov_root, deadline=deadline)
    conflicts_doc = _parse_json(conflicts_proc.stdout)
    cite = conflicts_cite(conflicts_doc)
    c_state = conflicts_state(cite, conflicts_proc.returncode)

    if h_state == STATE_DEGRADED:
        state = STATE_DEGRADED
    elif c_state == STATE_CONFLICT:
        state = STATE_CONFLICT
    else:
        state = h_state
    degraded = h_state == STATE_DEGRADED or c_state == STATE_DEGRADED
    body = {
        "schema": SCHEMA,
        # `status` stays the coarse OK/WARN signal existing readers key on;
        # `state` is the one a planner reasons with.
        "status": "WARN" if degraded else "OK",
        "state": state,
        "workspace": str(workspace),
        "task": task,
        "skills": skills,
        "issued_at": _now().isoformat(),
        "hydrate": {
            "state": h_state,
            "status": hydrate_doc.get("status"),
            "ok": hydrate_doc.get("ok"),
            "returncode": hydrate_proc.returncode,
            "timed_out": hydrate_proc.returncode == TIMEOUT_RETURNCODE,
            "record_count": hydrate_doc.get("record_count"),
            "namespace_context": hydrate_doc.get("namespace_context"),
            "repository_state_digest": hydrate_doc.get("repository_state_digest"),
            "task_signature": hydrate_doc.get("task_signature"),
        },
        # The hydrated memory the planner actually reads. Bounded, provenance
        # preserved per section, and never repository authority: current git
        # state wins over anything recorded here.
        "context": context,
        "context_chars": context_chars,
        "context_truncated": any(section["truncated"] for section in context),
        "search_returncode": search_returncode,
        "conflicts": cite,
        "conflicts_state": c_state,
        "conflicts_returncode": conflicts_proc.returncode,
        "budget": {
            "deadline_seconds": deadline_seconds,
            "remaining_seconds": round(deadline.remaining(), 3),
            "reserve_seconds": EMIT_RESERVE_SECONDS,
        },
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        # Fail-open: an unwritable workspace must not block the prompt. The
        # body is still returned, so the caller keeps the evidence in hand.
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
        # Fail-open: a SKIP receipt is evidence, not a gate. An unwritable
        # workspace must not block the prompt.
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
        state = result.get("state")
        suffix = f" state={state}" if state else ""
        context = result.get("context")
        if isinstance(context, list) and context:
            suffix += f" context_sections={len(context)} chars={result.get('context_chars')}"
        print(f"plan memory prefetch: {result.get('status')}{suffix}")
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
