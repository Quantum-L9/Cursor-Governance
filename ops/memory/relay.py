"""The relay carrier's outbox: hook records the agent must write to hosted memory.

On a relay surface (``ops/memory/hook_carrier.py``) the hook lane opens no
local store. ``MemoryControlPlaneClient`` admits a record against its hook
envelope and then *enqueues* it here, with the exact arguments for the matching
tool on the account-managed Memory connector:

=====================  =====================================
hook-lane operation    connector tool
=====================  =====================================
``write``              ``memory.write_agent``
``ingest_candidate``   ``memory.ingest_governed_candidate``
``close``              ``memory.close``
=====================  =====================================

The agent makes each call and acknowledges it with the receipt id the
connector returned (``python -m ops.memory.relay ack``). An entry without an
acknowledgement is still owed: the Stop hook (``memory_relay_gate.py``) asks
for it. Nothing here talks to memory; the outbox is a queue of obligations,
not a store, and an acknowledgement records the agent's claim of the hosted
receipt id — the hosted receipt itself is the authority (L9-EVIDENCE-001).

Files, both append-only JSON Lines under ``<workspace>/.l9/memory/relay/``:

- ``outbox.jsonl`` — ``{id, surface, operation, tool, arguments, created_at}``.
  ``id`` is a digest of operation + tool + arguments, so re-enqueueing the same
  record (a retried hook) is a no-op rather than a duplicate obligation.
- ``acks.jsonl`` — ``{id, receipt_id, acked_at}``.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import sys
import uuid
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RELAY_REL = Path(".l9") / "memory" / "relay"
OUTBOX_NAME = "outbox.jsonl"
ACKS_NAME = "acks.jsonl"

#: Hook-lane operation -> account-connector tool. The only operations that
#: write; reads keep their local transport and distill is not relayed (the
#: hosted service distills server-side only, CANONICAL_LAW §8.10 item 7).
CONNECTOR_TOOLS: Mapping[str, str] = {
    "write": "memory.write_agent",
    "ingest_candidate": "memory.ingest_governed_candidate",
    "close": "memory.close",
}


class RelayError(ValueError):
    """An outbox operation was refused; the message says why."""


def relay_dir(workspace: str | Path) -> Path:
    return Path(workspace) / RELAY_REL


def entry_id(operation: str, tool: str, arguments: Mapping[str, Any]) -> str:
    """Stable id: the same record queued twice is one obligation."""

    body = json.dumps(
        {"operation": operation, "tool": tool, "arguments": dict(arguments)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


@contextlib.contextmanager
def _locked(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".lock").open("a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # A torn line is evidence, not data; it is never treated as an ack.
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append(path: Path, row: Mapping[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n")


def enqueue(
    workspace: str | Path,
    *,
    surface: str | None,
    operation: str,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Queue one record for the agent; returns the (possibly existing) entry."""

    tool = CONNECTOR_TOOLS.get(operation)
    if tool is None:
        msg = f"operation {operation!r} is not relayed (relayed: {sorted(CONNECTOR_TOOLS)})"
        raise RelayError(msg)
    directory = relay_dir(workspace)
    ident = entry_id(operation, tool, arguments)
    with _locked(directory):
        for row in _read(directory / OUTBOX_NAME):
            if row.get("id") == ident:
                return row
        row = {
            "id": ident,
            "surface": surface or "operator",
            "operation": operation,
            "tool": tool,
            "arguments": dict(arguments),
            "created_at": datetime.now(UTC).isoformat(),
        }
        _append(directory / OUTBOX_NAME, row)
    return row


def acks(workspace: str | Path) -> dict[str, dict[str, Any]]:
    return {str(row.get("id")): row for row in _read(relay_dir(workspace) / ACKS_NAME)}


def pending(workspace: str | Path) -> list[dict[str, Any]]:
    """Outbox entries with no acknowledgement, oldest first."""

    acked = acks(workspace)
    return [row for row in _read(relay_dir(workspace) / OUTBOX_NAME) if row.get("id") not in acked]


def ack(workspace: str | Path, ident: str, receipt_id: str) -> dict[str, Any]:
    """Record the hosted receipt id for one entry. Refuses anything but a UUID."""

    try:
        receipt = str(uuid.UUID(str(receipt_id).strip()))
    except ValueError as exc:
        msg = f"receipt {receipt_id!r} is not a connector receipt id (a UUID)"
        raise RelayError(msg) from exc
    directory = relay_dir(workspace)
    with _locked(directory):
        if not any(row.get("id") == ident for row in _read(directory / OUTBOX_NAME)):
            msg = f"no outbox entry {ident!r} in {directory}"
            raise RelayError(msg)
        existing = {str(row.get("id")): row for row in _read(directory / ACKS_NAME)}
        if ident in existing:
            return existing[ident]
        row = {"id": ident, "receipt_id": receipt, "acked_at": datetime.now(UTC).isoformat()}
        _append(directory / ACKS_NAME, row)
        entry = next(r for r in _read(directory / OUTBOX_NAME) if r.get("id") == ident)
    if entry.get("operation") == "close":
        _discharge_close(Path(workspace), entry.get("arguments") or {}, receipt)
    return row


def _discharge_close(workspace: Path, arguments: Mapping[str, Any], receipt: str) -> None:
    """Promote the session's local close obligation once its relayed close is acked.

    ``close_session`` persists ``close_incomplete`` for a ``RELAYED`` close, because
    nothing was committed then. The hosted close receipt is what commits it; without
    this the next SessionStart reports a CLOSE_GAP for a session that did close.
    Only an obligation for the same session and idempotency key is promoted.
    """
    session_id = str(arguments.get("session_id") or "")
    key = str(arguments.get("idempotency_key") or "")
    if not session_id or not key:
        return
    try:
        from ops.graphiti.hydration import session_latches as latches
    except Exception:  # noqa: BLE001 - the ack stands; the obligation stays visible
        return
    current = latches.load_close_receipt(workspace, session_id)
    if not current or str(current.get("close_idempotency_key") or "") != key:
        return
    if latches.receipt_is_successful_close(current):
        return
    latches.write_receipt(
        workspace,
        session_id,
        {
            **current,
            "status": latches.STATUS_CLOSED_CANONICALLY,
            "canonical_operation_id": receipt,
            "write_count": max(1, int(current.get("write_count") or 0)),
            "failure_class": None,
            "last_error_code": None,
        },
    )


def instruction(workspace: str | Path, entries: Sequence[Mapping[str, Any]]) -> str:
    """What the agent must do for each owed entry, as one block of text."""

    lines = [
        f"L9 MEMORY RELAY — {len(entries)} hook record(s) are owed to the shared Memory 3.0 "
        "store (hook carrier: relay; CANONICAL_LAW §8.11). For EACH entry below, call the "
        "named tool on the account-managed L9 Memory connector with exactly these arguments, "
        "then acknowledge it with the receipt_id the tool returned:",
    ]
    for row in entries:
        args = json.dumps(row.get("arguments") or {}, sort_keys=True, ensure_ascii=False)
        lines.append(
            f"- [{row.get('id')}] {row.get('operation')} from {row.get('surface')}: "
            f"call {row.get('tool')} {args}"
        )
        lines.append(
            f"  then: python -m ops.memory.relay ack {row.get('id')} --receipt <receipt_id> "
            f'--workspace "{workspace}"'
        )
    lines.append(
        "A refusal from the connector is the verdict: report it, do not retry through another "
        "door (no memory.ingest, no operator CLI write)."
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ops.memory.relay", description=__doc__)
    parser.add_argument("--workspace", default=".", help="repository root holding .l9/")
    # Accepted after the subcommand too (the Stop hook's instruction puts it there);
    # SUPPRESS keeps a value given before the subcommand from being overwritten.
    after = argparse.ArgumentParser(add_help=False)
    after.add_argument("--workspace", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pending", parents=[after], help="print owed entries as JSON")
    sub.add_parser("status", parents=[after], help="print counts")
    sub.add_parser("instructions", parents=[after], help="print the connector calls still owed")
    ack_p = sub.add_parser("ack", parents=[after], help="record the connector receipt")
    ack_p.add_argument("id")
    ack_p.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if args.command == "pending":
        print(json.dumps(pending(workspace), indent=2, sort_keys=True, ensure_ascii=False))
        return 0
    if args.command == "status":
        owed = pending(workspace)
        total = len(_read(relay_dir(workspace) / OUTBOX_NAME))
        print(json.dumps({"total": total, "acked": total - len(owed), "pending": len(owed)}))
        return 0
    if args.command == "instructions":
        owed = pending(workspace)
        print(instruction(workspace, owed) if owed else "L9 MEMORY RELAY — nothing owed")
        return 0
    try:
        row = ack(workspace, args.id, args.receipt)
    except RelayError as exc:
        print(f"relay: REFUSED — {exc}", file=sys.stderr)
        return 1
    print(json.dumps(row, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
