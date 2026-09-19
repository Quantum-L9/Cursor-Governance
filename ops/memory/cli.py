"""Cursor's canonical memory command line (realignment stage C11).

This is the executable successor of the retired provider client (retired at
C11, deleted at C15 — ADR-0033): the same operator vocabulary
(``health``, ``resolve``, ``search``, ``write``, ``hydrate``, ``conflicts``)
routed through :class:`ops.memory.control_plane_client.MemoryControlPlaneClient`
to the bound ``l9-memory`` runtime. It knows no provider, holds no credential
and grants nothing: every verdict is the canonical receipt the control plane
returned, printed as JSON with the outcome status beside it.

Usage (always through the governance interpreter)::

    python -m ops.memory.cli health
    python -m ops.memory.cli resolve [--workspace DIR] [--group-id NS]
    python -m ops.memory.cli search "query" [--limit N] [--tag T ...]
    python -m ops.memory.cli write "fact" --kind lesson [--tag T ...] [--dry-run]
    python -m ops.memory.cli hydrate "task" [--workspace DIR]
    python -m ops.memory.cli conflicts [--workspace DIR]
    python -m ops.memory.cli readiness [--workspace DIR] [--json] [--no-verify-mcp]

Exit codes: ``0`` the operation completed (including ``NO_HITS`` and a dry
run), ``1`` memory refused, was unavailable, or returned an invalid receipt,
``3`` no memory runtime is bound (``ops/memory/runtime_binding.py``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ops.memory.control_plane_client import (
    MemoryControlPlaneClient,
    OperationOutcome,
    OutcomeStatus,
)
from ops.memory.hook_envelope import UnknownHookSurface
from ops.memory.namespace_context import (
    NamespaceContext,
    locate_clone_for_namespace,
    resolve_namespace_context,
)
from ops.memory.runtime_binding import resolve_runtime_binding

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_UNBOUND = 3

_COMPLETED = frozenset({OutcomeStatus.OK, OutcomeStatus.NO_HITS, OutcomeStatus.NOT_COMMITTED})

# The legacy client accepted ``--kind`` with these names; memory classes are
# the canonical vocabulary and the older aliases map onto them. A continuation
# is not a memory class: ``l9-memory write`` accepts only MemoryClass values
# (identity … meta), and hydration selects continuations by the
# ``session_continuation`` *tag* (hydration.py). ``pickup_context`` therefore
# writes an ``episodic`` record carrying that tag; ``session_continuation`` as a
# class exists only on the governed-candidate path (session_contracts.py).
CONTINUATION_TAG = "session_continuation"
KIND_ALIASES = {
    "pickup_context": "episodic",
    "session_summary": "session_summary",
    "note": "observation",
    "error": "lesson",
    "lesson": "procedural",
    "pattern": "insight",
    "rule": "decision",
}


def _workspace(raw: str | None) -> str:
    return str(Path(raw or os.getcwd()).expanduser().resolve())


def _context(workspace: str, explicit: str | None) -> NamespaceContext:
    return resolve_namespace_context(workspace, explicit=explicit)


def _run_at(context: NamespaceContext) -> str:
    # Memory derives the local principal from the directory it is invoked in,
    # so every call runs at the repository root, never at a subdirectory.
    return context.git_root or context.workspace


_PREFETCH_RECEIPT_TTL = 86400


#: Receipt-key suffix stamped by ``memory_writeback.py``. Write-back receipts
#: share the receipts directory with prefetch receipts by design (one mechanism,
#: distinct ids) and must never be read as a write bind.
_WRITEBACK_RECEIPT_SUFFIX = ".writeback"

#: ``status`` values ``memory_prefetch.py`` stamps. A receipt that carries
#: neither is not a prefetch receipt, whatever else is in the directory.
_PREFETCH_RECEIPT_STATUSES = frozenset({"prefetched", "degraded"})


def _current_writer_agent() -> str:
    """The writer identity the prefetch stamps, resolved the same way.

    Mirrors ``memory_state.extract_writer_agent_id`` — including its
    ``unknown-agent`` fallback — so a receipt is matched against the identity
    that produced it rather than against a second convention invented here.
    """
    return os.environ.get("L9_MEMORY_AGENT_ID", "").strip() or "unknown-agent"


def _is_applicable_prefetch_receipt(data: Any, *, writer_agent: str, chat_id: str) -> bool:
    """Whether this receipt is *this* writer/session's prefetch receipt.

    The receipts directory is shared: write-back receipts live beside prefetch
    receipts, and one checkout can be used by several chats and several agents.
    Recency alone therefore identifies nothing, so identity is checked against
    the canonical fields the producer stamps.
    """
    if not isinstance(data, dict):
        return False
    receipt_id = str(data.get("receipt_id") or "")
    if receipt_id.endswith(_WRITEBACK_RECEIPT_SUFFIX):
        return False
    # Positive identification: a prefetch receipt records what happened.
    if str(data.get("status") or "") not in _PREFETCH_RECEIPT_STATUSES:
        return False
    receipt_agent = str(data.get("agent_id") or "").strip()
    if receipt_agent and receipt_agent != writer_agent:
        return False
    # Chat is constrained only when this process can name one; the operator CLI
    # usually cannot, and inventing a chat id would reject every valid receipt.
    if chat_id:
        receipt_chat = str(data.get("conversation_id") or "").strip()
        if receipt_chat and receipt_chat != chat_id:
            return False
    return True


def read_prefetch_bind(workspace: str) -> dict[str, Any] | None:
    """Newest usable SessionStart / repair receipt **for this writer/session**.

    One prefetch binds one write namespace. The receipt lives on the session
    workspace; ``group_id`` is the repo the agent is working in — not a
    hardcoded cursor-governance default.

    Selection is by receipt identity, not directory recency. Taking the newest
    file in the directory let an unrelated write-back receipt, or another
    chat's prefetch, supply the bind: the operator write then inherited the
    wrong namespace, or lost an exclusive bind that was still in force.
    """

    root = Path(workspace) / ".l9" / "memory" / "receipts"
    if not root.is_dir():
        return None
    writer_agent = _current_writer_agent()
    chat_id = os.environ.get("CURSOR_CONVERSATION_ID", "").strip()
    newest: dict[str, Any] | None = None
    newest_mtime = 0.0
    now = time.time()
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mtime = path.stat().st_mtime
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if not _is_applicable_prefetch_receipt(data, writer_agent=writer_agent, chat_id=chat_id):
            continue
        try:
            created = float(data.get("created_at", 0))
        except (TypeError, ValueError):
            continue
        if created and (now - created) >= _PREFETCH_RECEIPT_TTL:
            continue
        # Only a receipt that passed every check above may advance the
        # watermark. Advancing it for a rejected file discarded an older but
        # valid receipt and returned nothing at all.
        if mtime >= newest_mtime:
            newest = data
            newest_mtime = mtime
    return newest


def bound_write_namespace(bind: dict[str, Any] | None) -> str | None:
    if not bind:
        return None
    group_id = str(bind.get("group_id") or "").strip()
    if group_id and group_id != "unresolved":
        return group_id
    ids = [str(item).strip() for item in (bind.get("group_ids") or []) if str(item).strip()]
    ids = [item for item in ids if item != "unresolved"]
    if len(ids) == 1:
        return ids[0]
    return None


def outcome_document(
    outcome: OperationOutcome, *, context: NamespaceContext | None = None
) -> dict[str, Any]:
    receipt = outcome.receipt
    raw = getattr(receipt, "raw", None)
    if raw is None and isinstance(receipt, dict):
        raw = receipt
    document: dict[str, Any] = {
        "operation": outcome.operation,
        "status": str(outcome.status),
        "ok": outcome.status in _COMPLETED,
        "exit_code": outcome.exit_code,
        "latency_ms": outcome.latency_ms,
        "error": outcome.error,
        "receipt": raw,
        "authority": "l9-graphite-memory",
        "transport": "memory-control-plane/v1",
    }
    if context is not None:
        document["namespace"] = {
            "repository_identity": context.repository_identity,
            "write_namespace_hint": context.write_namespace_hint,
            "read_namespace_hints": list(context.read_namespace_hints),
            "method": context.method,
            "warnings": list(context.warnings),
        }
    return document


def exit_code_for(outcome: OperationOutcome) -> int:
    if outcome.status is OutcomeStatus.BINDING_FAILED:
        return EXIT_UNBOUND
    return EXIT_OK if outcome.status in _COMPLETED else EXIT_REFUSED


def _emit(document: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True, default=str) + "\n")


def _client(args: argparse.Namespace) -> MemoryControlPlaneClient:
    binding = resolve_runtime_binding()
    return MemoryControlPlaneClient(
        binding, timeout=float(args.timeout), surface=getattr(args, "surface", None) or None
    )


def cmd_health(args: argparse.Namespace) -> int:
    outcome = _client(args).health()
    _emit(outcome_document(outcome))
    return exit_code_for(outcome)


def cmd_resolve(args: argparse.Namespace) -> int:
    context = _context(_workspace(args.workspace), args.group_id)
    outcome = _client(args).resolve(_run_at(context), explicit=args.group_id)
    _emit(outcome_document(outcome, context=context))
    return exit_code_for(outcome)


def cmd_search(args: argparse.Namespace) -> int:
    context = _context(_workspace(args.workspace), args.group_id)
    outcome = _client(args).search(
        args.query,
        workspace=_run_at(context),
        write_namespace_hint=context.write_namespace_hint,
        read_namespace_hints=context.read_namespace_hints,
        tags=tuple(args.tag),
        limit=args.limit,
        memory_classes=tuple(args.memory_class),
    )
    _emit(outcome_document(outcome, context=context))
    return exit_code_for(outcome)


def cmd_write(args: argparse.Namespace) -> int:
    session_ws = _workspace(args.workspace)
    bind = read_prefetch_bind(session_ws)
    bound_ns = bound_write_namespace(bind)
    session_hint = _context(session_ws, None).write_namespace_hint
    exclusive_bind = bool(bind and bind.get("exclusive_bind")) or (
        bool(bound_ns) and bool(session_hint) and bound_ns != session_hint
    )
    if args.group_id and exclusive_bind and bound_ns and args.group_id != bound_ns:
        _emit(
            {
                "operation": "write",
                "status": "PREFETCH_BOUND",
                "ok": False,
                "error": (
                    f"one prefetch already bound this session to {bound_ns!r}. "
                    f"--group-id {args.group_id!r} would write a different repo. "
                    "Re-run memory_prefetch.py --session-id <chat> --workspace "
                    "<owning-clone> to switch that one bind."
                ),
                "namespace": {
                    "prefetch_bound": bound_ns,
                    "requested": args.group_id,
                },
            }
        )
        return EXIT_REFUSED
    namespace = args.group_id or bound_ns
    run_ws = session_ws
    if namespace:
        located = locate_clone_for_namespace(namespace, from_workspace=session_ws)
        if located is not None:
            run_ws = str(located)
    context = _context(run_ws, namespace)
    if not namespace:
        namespace = context.write_namespace_hint
    if not namespace:
        _emit(
            {
                "operation": "write",
                "status": "NAMESPACE_UNRESOLVED",
                "ok": False,
                "error": "no write namespace: repository not in the registry and no --group-id",
                "namespace": {"repository_identity": context.repository_identity},
            }
        )
        return EXIT_REFUSED
    tags = list(args.tag)
    if args.agent_id:
        tags.append(f"agent:{args.agent_id}")
    if args.kind == "pickup_context" and CONTINUATION_TAG not in tags:
        tags.append(CONTINUATION_TAG)
    outcome = _client(args).write(
        args.content,
        workspace=_run_at(context),
        namespace=namespace,
        memory_class=KIND_ALIASES.get(args.kind, args.kind),
        tags=tuple(tags),
        idempotency_key=args.idempotency_key,
        source=args.source,
        source_id=args.source_id,
        dry_run=args.dry_run,
    )
    document = outcome_document(outcome, context=context)
    # #region agent log
    try:
        from ops.memory.store_compat import _debug

        _debug(
            "H5",
            "cli.py:cmd_write",
            "operator write",
            {
                "status": document.get("status"),
                "ok": document.get("ok"),
                "kind": KIND_ALIASES.get(args.kind, args.kind),
                "dry_run": bool(args.dry_run),
            },
        )
    except Exception:
        # Best-effort debug NDJSON; a log-write failure must not change CLI status.
        pass
    # #endregion
    _emit(document)
    return exit_code_for(outcome)


def cmd_hydrate(args: argparse.Namespace) -> int:
    from ops.memory.hydration import canonical_hydrate

    workspace = _workspace(args.workspace)
    hydration = canonical_hydrate(
        workspace,
        task=args.task,
        session_id=args.session_id,
        client=_client(args),
        explicit_namespace=args.group_id,
        token_budget=args.token_budget,
        max_records=args.max_records,
        continuation_policy=args.continuation_policy,
    )
    document = hydration.as_dict()
    # #region agent log
    try:
        from ops.memory.store_compat import _debug

        _debug(
            "H5",
            "cli.py:cmd_hydrate",
            "operator hydrate",
            {
                "status": document.get("status"),
                "ok": hydration.ok,
                "namespace": (document.get("namespace_context") or {}).get("write_namespace_hint"),
            },
        )
    except Exception:
        # Best-effort debug NDJSON; a log-write failure must not change CLI status.
        pass
    # #endregion
    _emit(document)
    return EXIT_OK if hydration.ok else EXIT_REFUSED


def cmd_conflicts(args: argparse.Namespace) -> int:
    context = _context(_workspace(args.workspace), args.group_id)
    namespace = args.group_id or context.write_namespace_hint
    if not namespace:
        _emit(
            {
                "operation": "conflicts",
                "status": "NAMESPACE_UNRESOLVED",
                "ok": False,
                "error": "no namespace: repository not in the registry and no --group-id",
            }
        )
        return EXIT_REFUSED
    outcome = _client(args).conflicts(workspace=_run_at(context), namespace=namespace)
    _emit(outcome_document(outcome, context=context))
    return exit_code_for(outcome)


def cmd_readiness(args: argparse.Namespace) -> int:
    from ops.memory import diagnostics

    argv = ["--workspace", _workspace(args.workspace)]
    if args.json:
        argv.append("--json")
    if args.binding_only:
        argv.append("--binding-only")
    if not args.verify_mcp:
        argv.append("--no-verify-mcp")
    return diagnostics.main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ops.memory.cli",
        description="Cursor's canonical memory CLI over the l9-graphite-memory control plane.",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds per memory call")
    parser.add_argument(
        "--surface",
        default=None,
        help=(
            "hook-lane surface (ops/config/memory-hook-envelopes.json). Automatic hooks "
            "that reach this CLI by subprocess name theirs; omitted = operator form"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("health", help="canonical memory health receipt")
    p.add_argument("--workspace", default=None, help="accepted for uniform invocation; unused")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("resolve", help="repository identity and namespace hints")
    p.add_argument("--workspace", default=None)
    p.add_argument("--group-id", default=None, help="explicit namespace request")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("search", help="canonical search (full records)")
    p.add_argument("query")
    p.add_argument("--workspace", default=None)
    p.add_argument("--group-id", default=None)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--tag", action="append", default=[], help="required tag (repeatable)")
    p.add_argument("--memory-class", action="append", default=[])
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("write", help="generic canonical write (lessons, decisions, insights)")
    p.add_argument("content")
    p.add_argument("--kind", required=True, help="memory class (legacy kinds are mapped)")
    p.add_argument("--workspace", default=None)
    p.add_argument("--group-id", default=None)
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--agent-id", default=os.environ.get("L9_MEMORY_AGENT_ID") or None)
    p.add_argument("--idempotency-key", default=None)
    p.add_argument("--source", default="cursor-governance")
    p.add_argument("--source-id", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_write)

    p = sub.add_parser("hydrate", help="canonical session hydration with typed continuation")
    p.add_argument("task")
    p.add_argument("--workspace", default=None)
    p.add_argument("--group-id", default=None)
    p.add_argument("--session-id", default=None)
    p.add_argument("--token-budget", type=int, default=1_200)
    p.add_argument("--max-records", type=int, default=40)
    p.add_argument(
        "--continuation-policy",
        choices=("task", "repository_fallback"),
        default="task",
        help=(
            "task (default): resume only a continuation written for this task in this "
            "repository; repository_fallback: with no task match, the newest repository "
            "continuation, marked as a fallback on the receipt"
        ),
    )
    p.set_defaults(func=cmd_hydrate)

    p = sub.add_parser("conflicts", help="evidence only; never a repository lock")
    p.add_argument("--workspace", default=None)
    p.add_argument("--group-id", default=None)
    p.add_argument("--task", default=None, help="accepted for the legacy vocabulary; unused")
    p.set_defaults(func=cmd_conflicts)

    p = sub.add_parser("readiness", help="R0..R9 readiness (ops.memory.diagnostics)")
    p.add_argument("--workspace", default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--binding-only", action="store_true")
    p.add_argument(
        "--verify-mcp",
        dest="verify_mcp",
        action="store_true",
        default=True,
        help="run the R5 MCP handshake — the default; accepted for compatibility",
    )
    p.add_argument(
        "--no-verify-mcp",
        dest="verify_mcp",
        action="store_false",
        help="skip the R5 handshake (it spawns a server for ~1.2s)",
    )
    p.set_defaults(func=cmd_readiness)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        return int(args.func(args))
    except UnknownHookSurface as exc:
        # A hook naming an undeclared surface is a wiring fault in the caller,
        # refused before any memory traffic (ADR-0033 B7).
        _emit(
            {
                "operation": args.cmd,
                "status": "REJECTED",
                "ok": False,
                "error": f"REJECTED:envelope {exc}",
            }
        )
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
