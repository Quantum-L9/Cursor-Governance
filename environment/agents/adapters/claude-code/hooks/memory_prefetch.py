#!/usr/bin/env python3
"""SessionStart prefetch — thin wrap of the canonical session hydration (stage C8).

Every repository this session works in is hydrated through the canonical
memory control plane (``ops.memory.hydration.canonical_hydrate`` via the
Cursor session-packet compiler); nothing here calls a provider or the retired
legacy client. The receipt this hook writes is the ONLY memory precondition a
governed write may carry (``memory_gate.py``), so it records what happened —
a hydration that resolved no namespace is ``degraded``, never ``prefetched``.

Mid-session repair: when the automatic SessionStart stamp is stale or missing,
run with an explicit session id instead of guessing:

    python3 memory_prefetch.py --session-id <uuid> --workspace <owning-clone>

Find your session id as the newest
``~/.claude/projects/<project>/<uuid>.jsonl`` for this conversation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"

#: Receipt transport tag: the contract the hydration crossed, not a tool name.
TRANSPORT = "memory-control-plane/v1"


def _governance_lib() -> Path:
    """Locate ops/scripts/lib by walking up, not by counting parents.

    A hard-coded parents[N] silently binds to the wrong directory the moment
    this hook is moved or re-nested, and the failure mode is an ImportError at
    SessionStart on a fail-open path — i.e. a silently degraded session.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "ops" / "scripts" / "lib"
        if (candidate / "workspace_roots.py").is_file():
            return candidate
    raise ModuleNotFoundError("ops/scripts/lib/workspace_roots.py not found above this hook")


_GOV_LIB = _governance_lib()
_GOV_SCRIPTS = _GOV_LIB.parent
_GOV_AUTONOMY = _GOV_LIB.parent.parent / "autonomy"
for _path in (_GOV_LIB, _GOV_SCRIPTS, _GOV_AUTONOMY):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from classify_hydrate_state import classify as classify_hydrate_state  # noqa: E402
from surface_detect import is_claude_gate_surface  # noqa: E402
from workspace_roots import DROPPED_CAP  # noqa: E402
from workspace_roots import select_workspace_roots as _shared_select_workspace_roots  # noqa: E402


def prefetch_agent_id(env: dict[str, str] | None = None) -> str:
    """Writer id for this prefetch run.

    The hook is Claude-owned, but ``--session-id`` is a repair override that
    also runs on Cursor. Hard-coding ``claude-code`` stamped the wrong
    surface onto Cursor hydrate blocks (SESSION_START_SPEC: a Cursor session
    contains zero ``agent_id=claude-code`` hydrate blocks).
    """
    return "claude-code" if is_claude_gate_surface(env) else "cursor"


#: Cloud containers put several repositories side by side. Hydrating each costs
#: one packet of context, so the count is capped rather than unbounded — and the
#: cap is reported in the emitted text, because a silent truncation reads as
#: "everything was covered".
_MAX_HYDRATION_ROOTS = 6


def _repo_count(workspace: Path) -> int:
    try:
        return sum(1 for child in workspace.iterdir() if (child / ".git").exists())
    except OSError:
        return 0


def _resolves_to_own_namespace(root: Path) -> bool:
    """True when this repository resolves to a write namespace of its OWN.

    An unresolved identity has nothing to hydrate from, and filtering here
    rather than after compiling stops an unusable root from consuming a slot
    under the cap. The namespace context is the sole identity producer since
    stage C2; the shared read namespace it may add is never a write target.
    """
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        from ops.memory.namespace_context import resolve_namespace_context

        return bool(resolve_namespace_context(root).write_namespace_hint)
    except Exception:  # noqa: BLE001 — a resolver fault must not lose hydration
        return True


def _hydration_roots(workspace: Path) -> list[Path]:
    """Repository roots to hydrate, in resolution order.

    A namespace identifies a REPOSITORY (rules/96, §3). Resolving one from a
    multi-repo container root matches all of them and returns none, so the
    session hydrated zero facts and every memory write was refused — while the
    store itself was healthy. When the workspace is a repository this returns
    it unchanged; when it is a container of repositories it returns the
    repositories that resolve to their own namespace, each hydrated under it.
    """
    return _hydration_selection(workspace).selected


def _hydration_selection(workspace: Path):
    """`_hydration_roots`, keeping the roots it dropped and why."""
    return _shared_select_workspace_roots(
        workspace,
        cap=_MAX_HYDRATION_ROOTS,
        predicate=_resolves_to_own_namespace,
    )


def _dropped_summary(dropped: list[tuple[Path, str]]) -> str:
    """Name every excluded repository and the rule that excluded it."""
    if not dropped:
        return ""
    by_cap = [p.name for p, reason in dropped if reason == DROPPED_CAP]
    by_ns = [p.name for p, reason in dropped if reason != DROPPED_CAP]
    parts = []
    if by_cap:
        parts.append(
            f"beyond the cap of {_MAX_HYDRATION_ROOTS}, so NOT hydrated this "
            f"session: {', '.join(by_cap)}"
        )
    if by_ns:
        parts.append(f"no namespace of their own: {', '.join(by_ns)}")
    return "; ".join(parts)


sys.path.insert(0, str(MEM))

import memory_bridge as mb  # noqa: E402
import memory_state as st  # noqa: E402


def hook_session_start_payload(context: str) -> dict[str, object]:
    """SessionStart envelope a human can audit without unescaping.

    Claude Code still requires one JSON document. A compact string value hid
    every field behind ``\\n`` and ``\\u00a7``. One array element per line
    keeps the host contract (additionalContext arrays concatenate) and makes
    stdout one field/value per line.
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context.split("\n"),
        }
    }


def _emit(context: str) -> None:
    print(json.dumps(hook_session_start_payload(context), ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(prog="memory_prefetch")
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "repair: the RAW chat id for the writer receipt (and the session id "
            "when stdin has none) — exactly what memory_gate.py names in its "
            "denial. The receipt key is composed here, once; a precomposed "
            "<writer>__<chat> key for this writer is reduced, never doubled. "
            "Newest ~/.claude/projects/<project>/<uuid>.jsonl"
        ),
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help=(
            "git root of the repository being mutated. Repair from a session "
            "opened in a different clone MUST pass this so the receipt and "
            "hydrate namespace match the edited repo, not the session cwd."
        ),
    )
    args = parser.parse_args()

    # Canonical surface guard. --session-id is the explicit repair override;
    # ordinary hook execution must never infer Claude identity from a private
    # marker list.
    if not is_claude_gate_surface() and not args.session_id:
        print(
            "memory_prefetch: skipped — canonical surface detector says this is not Claude",
            file=sys.stderr,
        )
        return 0
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    try:
        session_id = st.resolve_session_id(event=event, cli_arg=args.session_id)
    except ValueError:
        session_id = args.session_id or os.environ.get("CURSOR_SESSION_ID") or "unknown-session"
    # One composition of the writer receipt key, from the same raw identity the
    # gate names in its denial hint (audit P573-F1): the file stamped here is
    # the file the gate looks up.
    try:
        writer_agent, receipt_chat = st.receipt_identity(event=event, cli_arg=args.session_id)
        receipt_id = st.compose_receipt_id(writer_agent, receipt_chat)
    except ValueError:
        receipt_id = ""
    chat_id, _chat_key = st.extract_chat_id(event)

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0

    session_ws = st.workspace_root()
    if args.workspace:
        workspace = Path(args.workspace).expanduser().resolve()
        namespaces = []
    else:
        workspace = session_ws
        namespaces = st.resolve_namespaces(contract)
    agent_id = prefetch_agent_id()
    os.environ.setdefault("L9_MEMORY_AGENT_ID", agent_id)
    os.environ.setdefault(
        "USER_ID", "claude_code_agent" if agent_id == "claude-code" else "cursor_agent"
    )

    # BEFORE root selection: the namespace predicate imports ops.memory from the
    # governance root, and its except-branch fails OPEN so a resolver fault can
    # never cost the session its memory. Selected before the path was set, that
    # open failure was silent and unconditional — every root looked eligible.
    mb.ensure_importable()
    selection = _hydration_selection(workspace)
    roots, dropped = selection.selected, selection.dropped

    try:
        from ops.graphiti.hydration.compile_session_packet import compile_and_format

        contexts: list[str] = []
        group_ids: list[str] = []
        packet_ids: list[str] = []
        memory_statuses: dict[str, str] = {}
        continuation_ids: dict[str, str] = {}
        degraded_any = False

        for root in roots:
            compiled = compile_and_format(
                project_dir=root,
                conversation_id=session_id,
                agent_id=agent_id,
            )
            packet = compiled.get("packet") or {}
            group_id = str(packet.get("group_id") or "")
            stats = packet.get("hydrate_stats") or {}
            if group_id and group_id != "unresolved":
                group_ids.append(group_id)
            else:
                degraded_any = True
            if packet.get("degraded"):
                degraded_any = True
            memory_statuses[root.name] = str(stats.get("memory_status") or "unknown")
            if stats.get("continuation_record_id"):
                continuation_ids[root.name] = str(stats["continuation_record_id"])
            if packet.get("packet_id"):
                packet_ids.append(str(packet["packet_id"]))
            body = compiled.get("additional_context") or ""
            if body:
                hydrate_degraded, _hydrate_reason = classify_hydrate_state(body)
                if hydrate_degraded:
                    degraded_any = True
                header = f"### {root.name} (namespace={group_id or 'unresolved'})"
                contexts.append(header + "\n" + body if len(roots) > 1 else body)

        degraded = degraded_any or not group_ids
        if not receipt_id:
            raise ValueError("prefetch refused to stamp a session-scoped write-gate receipt")
        st.write_receipt(
            contract,
            receipt_id,
            {
                "session_id": session_id,
                "agent_id": st.extract_writer_agent_id(event),
                "conversation_id": chat_id,
                "namespaces": namespaces,
                "transport": TRANSPORT,
                "group_id": group_ids[0] if len(group_ids) == 1 else "",
                "group_ids": group_ids,
                "hydrated_roots": [str(r) for r in roots],
                "packet_id": packet_ids[0] if packet_ids else None,
                "packet_ids": packet_ids,
                "memory_statuses": memory_statuses,
                "continuation_record_ids": continuation_ids,
                # A receipt records what HAPPENED, not what was attempted. Writing
                # "prefetched" over a hydration that resolved no namespace and
                # returned nothing made the precondition self-satisfying: the gate
                # saw a fresh receipt, never re-hydrated, and the session ran
                # memory-blind for the full TTL while every surface reported it
                # satisfied.
                "status": "degraded" if degraded else "prefetched",
                "degraded": degraded,
                "exclusive_bind": bool(args.workspace),
            },
            workspace=session_ws,
        )
        resolved = ", ".join(group_ids) if group_ids else "unresolved"
        lines = [
            "L9 memory: ENFORCED",
            f"transport={TRANSPORT}",
            f"namespace={resolved}",
            f"requested={', '.join(namespaces) or 'none'}",
            "rule=03-graphiti-memory",
            "skill=l9-graphiti-memory",
            "law=CANONICAL_LAW §8",
            *contexts,
            "note=Governed writes require this hydration only.",
            "isolation=dedicated worktree + branch off origin/main + publication gate",
            "phase_lock=not required",
        ]
        if len(roots) > 1:
            dropped_note = _dropped_summary(dropped)
            lines.insert(
                1,
                f"multi_repo=hydrated {len(roots)} of "
                f"{_repo_count(workspace)} under {workspace}"
                + (f"; excluded={dropped_note}" if dropped_note else ""),
            )
        _emit("\n".join(line for line in lines if line))
    except Exception as exc:  # fail-open
        _emit(
            "L9 memory: prefetch DEGRADED ("
            f"{exc}). No receipt written; governed writes remain fail-closed until the "
            "canonical memory runtime is bound (make memory-readiness). Operator-only "
            "override: L9_MEMORY_ENFORCEMENT_BREAKGLASS. next="
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
