"""Cursor's canonical memory command line (realignment stage C11).

This is the executable successor of the retired provider client
(``ops/graphiti/graphiti_memory_client.py``): the same operator vocabulary
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
    python -m ops.memory.cli readiness [--workspace DIR] [--json]

Exit codes: ``0`` the operation completed (including ``NO_HITS`` and a dry
run), ``1`` memory refused, was unavailable, or returned an invalid receipt,
``3`` no memory runtime is bound (``ops/memory/runtime_binding.py``).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ops.memory.control_plane_client import (
    MemoryControlPlaneClient,
    OperationOutcome,
    OutcomeStatus,
)
from ops.memory.namespace_context import NamespaceContext, resolve_namespace_context
from ops.memory.runtime_binding import resolve_runtime_binding

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_UNBOUND = 3

_COMPLETED = frozenset({OutcomeStatus.OK, OutcomeStatus.NO_HITS, OutcomeStatus.NOT_COMMITTED})

# The legacy client accepted ``--kind`` with these names; memory classes are
# the canonical vocabulary and the older aliases map onto them.
KIND_ALIASES = {
    "pickup_context": "session_continuation",
    "session_summary": "session_summary",
    "note": "observation",
    "error": "lesson",
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
    return MemoryControlPlaneClient(binding, timeout=float(args.timeout))


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
    context = _context(_workspace(args.workspace), args.group_id)
    namespace = args.group_id or context.write_namespace_hint
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
    _emit(outcome_document(outcome, context=context))
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
    )
    _emit(hydration.as_dict())
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
    return diagnostics.main(argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ops.memory.cli",
        description="Cursor's canonical memory CLI over the l9-graphite-memory control plane.",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="seconds per memory call")
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
    p.set_defaults(func=cmd_readiness)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
