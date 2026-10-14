#!/usr/bin/env python3
"""SessionStart memory status: health only, no memory read.

SessionStart reports whether the canonical memory runtime is bound and healthy
(``MemoryControlPlaneClient.health``) and which repository namespaces this
session resolves to locally. It never hydrates, searches, reads conflicts, or
injects resume content: retrieval is on demand
(``python -m ops.memory.cli hydrate "<task>" --workspace <repo>``), and the
``claude-session-start`` hook envelope admits only ``resolve`` / ``health`` /
``capabilities``, so a reintroduced read is refused before a process spawns.

The receipt this hook writes marks that the session started and what memory
health was observed. It is no longer a precondition for repository writes
(``memory_gate.py`` contract): Stop / post-publish hooks read it as the
session-start timestamp and the repository roots in scope. A receipt records
what happened — ``health_only`` when the runtime answered healthy, ``degraded``
when it did not — never ``prefetched``.

Mid-session repair: when the automatic SessionStart stamp is missing, run with
an explicit session id instead of guessing:

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

#: Receipt transport tag: the contract the health probe crossed, not a tool name.
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

from surface_detect import is_claude_gate_surface  # noqa: E402
from workspace_roots import DROPPED_CAP  # noqa: E402
from workspace_roots import select_workspace_roots as _shared_select_workspace_roots  # noqa: E402


def prefetch_agent_id(env: dict[str, str] | None = None) -> str:
    """Writer id for this prefetch run.

    The hook is Claude-owned, but ``--session-id`` is a repair override that
    also runs on Cursor. Hard-coding ``claude-code`` stamped the wrong
    surface onto Cursor hydrate blocks (SESSION_START_SPEC: a Cursor session
    contains zero ``agent_id=claude-code`` hydrate blocks). The identity is
    DERIVED from host markers by ops/memory/agent_identity.py (cursor,
    claude-code-desktop, claude-code-mobile); a configured value never
    overrides it. "" when this process has no derivable identity.
    """
    return st.writer_identity(dict(os.environ if env is None else env))


#: Cloud containers put several repositories side by side. The roots in scope
#: are capped rather than unbounded — and the cap is reported in the emitted
#: text, because a silent truncation reads as "everything was covered".
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
    except Exception:  # noqa: BLE001 — a resolver fault must not drop a root
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
            f"beyond the cap of {_MAX_HYDRATION_ROOTS}, so not in scope this "
            f"session: {', '.join(by_cap)}"
        )
    if by_ns:
        parts.append(f"no namespace of their own: {', '.join(by_ns)}")
    return "; ".join(parts)


sys.path.insert(0, str(MEM))

import memory_bridge as mb  # noqa: E402
import memory_state as st  # noqa: E402


def hook_session_start_payload(
    context: str, system_message: str | None = None
) -> dict[str, object]:
    """SessionStart envelope.

    ``additionalContext`` is a **string**. SESSION_START_SPEC.md §3 and the
    Claude Code provider contract both define it that way, and the host reads
    it as one: an array is not concatenated, it is not injected at all, so the
    prefetch can hydrate successfully and still deliver nothing.

    An earlier revision split the context on newlines to make stdout readable
    one field per line. That traded the wire type for presentation. The
    readability it was after is in the *content* — the context keeps its own
    newlines and its non-ASCII intact (``ensure_ascii=False`` at the emit
    site), which is what a human reading the log needs.
    """
    payload: dict[str, object] = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    if system_message:
        # Shown to the USER, not only the model: a memory read that failed or
        # degraded must never be discoverable only by reading the model context.
        payload["systemMessage"] = system_message
    return payload


def _emit(context: str, system_message: str | None = None) -> None:
    print(
        json.dumps(
            hook_session_start_payload(context, system_message), ensure_ascii=False, indent=2
        )
    )


def _loud_status(detail: str) -> str:
    return f"L9 MEMORY — {detail}"


def _local_namespaces(roots: list[Path]) -> list[str]:
    """Write namespaces the in-scope repositories resolve to, locally.

    ``resolve_namespace_context`` reads the namespace registry and git
    identity; it does not call memory. A root that resolves none is omitted.
    """
    from ops.memory.namespace_context import resolve_namespace_context

    namespaces: list[str] = []
    for root in roots:
        hint = resolve_namespace_context(root).write_namespace_hint
        if hint and hint != "unresolved" and hint not in namespaces:
            namespaces.append(hint)
    return namespaces


def _memory_health(session_id: str) -> dict[str, str]:
    """One bounded ``health`` call: binding, store and projection status only.

    Reads no records. ``UNBOUND`` when the runtime binding fails (the call never
    reached memory), the outcome status otherwise.
    """
    client = mb.memory_client(session_id)
    binding = getattr(client, "binding", None)
    if binding is not None and not getattr(binding, "ok", True):
        reasons = "; ".join(str(r) for r in (getattr(binding, "reasons", None) or []))
        return {"status": "UNBOUND", "detail": reasons or "memory runtime not bound"}
    outcome = client.health()
    status = "OK" if outcome.ok else str(outcome.status.value)
    detail = "" if outcome.ok else str(outcome.error or "")
    return {"status": status, "detail": detail[:300]}


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
    else:
        workspace = session_ws
    # Derived identity overwrites a configured value (the health probe's hook
    # principal reads it). The later receipt uses the in-scope namespaces, so
    # this site does not resolve them early.
    st.bind_identity_env()

    # BEFORE root selection: the namespace predicate imports ops.memory from the
    # governance root, and its except-branch fails OPEN so a resolver fault can
    # never cost the session its memory. Selected before the path was set, that
    # open failure was silent and unconditional — every root looked eligible.
    mb.ensure_importable()
    selection = _hydration_selection(workspace)
    roots, dropped = selection.selected, selection.dropped

    try:
        group_ids = _local_namespaces(roots)
        health = _memory_health(session_id)
        degraded = health["status"] != "OK" or not group_ids
        # Requested = the in-scope repositories' own namespaces (explicit
        # L9_MEMORY_NAMESPACES aside), never a governance-repo constant.
        namespaces = st.resolve_namespaces(contract, group_ids)
        if not receipt_id:
            raise ValueError("refused to stamp a session receipt without a writer identity")
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
                # Repository roots in scope for this session. Nothing was read
                # from memory for them; Stop hooks use them to place write-back.
                "roots": [str(r) for r in roots],
                "memory_health": health,
                # A receipt records what HAPPENED: SessionStart observed health
                # and read no records. ``degraded`` when memory did not answer
                # healthy or no repository resolved a namespace of its own.
                "status": "degraded" if degraded else "health_only",
                "degraded": degraded,
                "exclusive_bind": bool(args.workspace),
            },
            workspace=session_ws,
        )
        resolved = ", ".join(group_ids) if group_ids else "unresolved"
        lines = [
            "L9 memory: HEALTH-ONLY at SessionStart (no records read, nothing hydrated)",
            f"health={health['status']}"
            + (f" ({health['detail']})" if health.get("detail") else ""),
            f"transport={TRANSPORT}",
            f"namespace={resolved}",
            f"requested={', '.join(namespaces) or 'none'}",
            'on_demand=python -m ops.memory.cli hydrate "<task>" --workspace <repo>',
            "rule=03-graphiti-memory",
            "skill=l9-graphiti-memory",
            "law=CANONICAL_LAW §8",
            "note=Repository writes do not require memory hydration.",
            "isolation=dedicated worktree + branch off origin/main + publication gate",
            "phase_lock=not required",
        ]
        if len(roots) > 1:
            dropped_note = _dropped_summary(dropped)
            lines.insert(
                1,
                f"multi_repo={len(roots)} of {_repo_count(workspace)} repositories under "
                f"{workspace} in scope" + (f"; excluded={dropped_note}" if dropped_note else ""),
            )
        loud = None
        if degraded:
            loud = _loud_status(
                "DEGRADED at session start: "
                + (
                    f"memory health {health['status']}"
                    + (f" ({health['detail']})" if health.get("detail") else "")
                    if health["status"] != "OK"
                    else f"namespace unresolved for {', '.join(r.name for r in roots) or workspace}"
                )
                + ". Repository work is unaffected; memory reads and writes may fail. "
                "Repair: make memory-readiness."
            )
        if dropped:
            loud = (loud + " " if loud else "") + _loud_status(
                f"OUT OF SCOPE this session: {_dropped_summary(dropped)}."
            )
        _emit("\n".join(line for line in lines if line), loud)
    except Exception as exc:  # fail-open, never silent
        _emit(
            "L9 memory: health check FAILED at SessionStart ("
            f"{exc}). No session receipt written. Repository work is unaffected; "
            "memory reads and writes may fail until the canonical memory runtime is bound "
            "(make memory-readiness).",
            _loud_status(
                f"health check FAILED at session start ({type(exc).__name__}). "
                "Repair: make memory-readiness."
            ),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
