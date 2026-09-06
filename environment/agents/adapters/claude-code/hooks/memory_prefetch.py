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

    python3 memory_prefetch.py --session-id <uuid>

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
if str(_GOV_LIB) not in sys.path:
    sys.path.insert(0, str(_GOV_LIB))

from workspace_roots import DROPPED_CAP  # noqa: E402
from workspace_roots import select_workspace_roots as _shared_select_workspace_roots  # noqa: E402

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


def _emit(context: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
        )
    )


def _claude_runtime_marker_present() -> bool:
    """Mirror of session_start_claude_governance.sh lines 89-92.

    This hook is registered in .claude/settings.json, but Cursor sessions on a
    machine that also runs Claude can invoke it (observed: two agent_id=
    claude-code hydrate blocks injected into a Cursor session). An observer
    hook without a runtime guard leaks another surface's identity into this
    one, so absent every Claude marker it must no-op.
    """
    if os.environ.get("CLAUDE_CODE_REMOTE", "") == "true":
        return True
    return any(
        os.environ.get(key)
        for key in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SESSION_ID")
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="memory_prefetch")
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "stamp the receipt for this session id instead of reading stdin "
            "(newest ~/.claude/projects/<project>/<uuid>.jsonl for this conversation)"
        ),
    )
    args = parser.parse_args()

    # Observer-class guard: no Claude runtime marker and no explicit repair
    # invocation (--session-id) means this is another surface's session.
    if not _claude_runtime_marker_present() and not args.session_id:
        print(
            "memory_prefetch: skipped — no Claude runtime marker "
            "(CLAUDECODE/CLAUDE_CODE_*); not this surface",
            file=sys.stderr,
        )
        return 0
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    session_id = args.session_id or str(event.get("session_id", "")) or "unknown-session"

    try:
        contract = st.load_contract()
    except (OSError, json.JSONDecodeError):
        return 0

    namespaces = st.resolve_namespaces(contract) or ["cursor-governance"]
    workspace = st.workspace_root()
    os.environ.setdefault("L9_MEMORY_AGENT_ID", "claude-code")
    os.environ.setdefault("USER_ID", "claude_code_agent")

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
                agent_id="claude-code",
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
                header = f"### {root.name} (namespace={group_id or 'unresolved'})"
                contexts.append(header + "\n" + body if len(roots) > 1 else body)

        degraded = degraded_any or not group_ids
        st.write_receipt(
            contract,
            session_id,
            {
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
            },
        )
        resolved = ", ".join(group_ids) if group_ids else "unresolved"
        lines = [
            "L9 memory: ENFORCED via canonical memory hydrate "
            f"({TRANSPORT}; namespace={resolved}; requested {', '.join(namespaces)}). "
            "Rule 03-graphiti-memory; skill l9-graphiti-memory; CANONICAL_LAW §8.",
            *contexts,
            "Governed writes require this hydration only. Repository isolation is a "
            "dedicated worktree (ops/scripts/agent_worktree_start.sh), history isolation a "
            "branch off fetched origin/main, and collision safety the publication gate. "
            "No phase-lock is required or accepted for repository mutation.",
        ]
        if len(roots) > 1:
            dropped_note = _dropped_summary(dropped)
            lines.insert(
                1,
                f"Multi-repo container: hydrated {len(roots)} of "
                f"{_repo_count(workspace)} repositories under {workspace}. "
                + (f"Excluded — {dropped_note}. " if dropped_note else "")
                + "A namespace is repository identity, never container "
                "identity — resolving one from the container root matches every repo "
                "and returns none.",
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
