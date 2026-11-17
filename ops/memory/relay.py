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
acknowledgement is still owed: the Stop hook (``memory_writeback._relay_gate``)
asks for it. Nothing here talks to memory; the outbox is a queue of
obligations, not a store, and an acknowledgement records the agent's claim of
the hosted receipt id — the hosted receipt itself is the authority
(L9-EVIDENCE-001).

When the connector *refuses* the call (``status: rejected``, e.g. "namespace did
not match any write grant") the agent records that verdict with
``python -m ops.memory.relay refuse <id> --receipt <rejection receipt_id>
--reason "..."``. An ack would claim a hosted write that never landed, so a
refusal is its own record: the entry stops blocking Stop (rule 42
"Satisfiability": no correct action could otherwise clear it) but stays listed by
``pending``, ``status`` and the gate, exactly as ``session_debt.py defer``
discharges the turn without closing the item. A later ``ack`` supersedes the
refusal; a refusal never supersedes an ack.

Files, all append-only JSON Lines under ``<workspace>/.l9/memory/relay/``:

- ``outbox.jsonl`` — ``{id, surface, operation, tool, arguments, created_at}``.
  ``id`` is a digest of operation + tool + arguments, so re-enqueueing the same
  record (a retried hook) is a no-op rather than a duplicate obligation.
- ``acks.jsonl`` — ``{id, receipt_id, acked_at}``.
- ``refusals.jsonl`` — ``{id, receipt_id, reason, refused_at}``; the connector's
  rejection receipt and reason. Several per entry are kept; the last is shown.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import sys
import uuid
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RELAY_REL = Path(".l9") / "memory" / "relay"
OUTBOX_NAME = "outbox.jsonl"
ACKS_NAME = "acks.jsonl"
REFUSALS_NAME = "refusals.jsonl"

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


#: Files the relay may open, by fixed name only.
RELAY_FILES = frozenset({OUTBOX_NAME, ACKS_NAME, REFUSALS_NAME, ".lock", "gate.json"})


def relay_dir(workspace: str | Path) -> Path:
    """``<workspace>/.l9/memory/relay``, bounded to a real repository root.

    ``workspace`` reaches here from hook state and from the ``--workspace`` the
    agent passes, so it is never trusted as given: it must resolve to a git
    repository root, and the relay directory must resolve inside it.
    """
    root_r = os.path.realpath(os.path.expanduser(str(workspace)))
    if not os.path.exists(os.path.join(root_r, ".git")):
        msg = f"{workspace} is not a repository root (no .git); refusing to place a relay outbox"
        raise RelayError(msg)
    relay_r = os.path.realpath(os.path.join(root_r, *RELAY_REL.parts))
    if os.path.commonpath([root_r, relay_r]) != root_r:
        msg = f"relay directory escapes {root_r}"
        raise RelayError(msg)
    return Path(relay_r)


def relay_file(directory: Path, name: str) -> Path:
    """One of the relay's fixed files, resolved inside ``directory``."""

    if name not in RELAY_FILES:
        msg = f"{name!r} is not a relay file"
        raise RelayError(msg)
    dir_r = os.path.realpath(str(directory))
    path_r = os.path.realpath(os.path.join(dir_r, name))
    if os.path.commonpath([dir_r, path_r]) != dir_r:
        msg = f"{name!r} escapes {dir_r}"
        raise RelayError(msg)
    return Path(path_r)


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
    # directory is relay_dir()'s bounded result; the lock is a fixed relay file.
    directory.mkdir(parents=True, exist_ok=True)  # NOSONAR pythonsecurity:S8707
    lock = relay_file(directory, ".lock")
    with lock.open("a", encoding="utf-8") as handle:  # NOSONAR pythonsecurity:S8707
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    # path is relay_file()'s bounded result (fixed name inside relay_dir()).
    for line in path.read_text(encoding="utf-8").splitlines():  # NOSONAR pythonsecurity:S8707
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
    # path is relay_file()'s bounded result (fixed name inside relay_dir()).
    with path.open("a", encoding="utf-8") as handle:  # NOSONAR pythonsecurity:S8707
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
        for row in _read(relay_file(directory, OUTBOX_NAME)):
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
        _append(relay_file(directory, OUTBOX_NAME), row)
    return row


def acks(workspace: str | Path) -> dict[str, dict[str, Any]]:
    return {str(row.get("id")): row for row in _read(relay_file(relay_dir(workspace), ACKS_NAME))}


def refusals(workspace: str | Path) -> dict[str, dict[str, Any]]:
    """The latest recorded connector refusal per entry id."""

    return {
        str(row.get("id")): row for row in _read(relay_file(relay_dir(workspace), REFUSALS_NAME))
    }


def pending(workspace: str | Path) -> list[dict[str, Any]]:
    """Outbox entries with no acknowledgement, oldest first.

    A refused entry is still listed (it is not discharged), carrying its latest
    refusal under ``"refusal"``; the Stop gate asks only for rows without one.
    """

    directory = relay_dir(workspace)
    acked = acks(workspace)
    refused = refusals(workspace)
    rows: list[dict[str, Any]] = []
    for row in _read(relay_file(directory, OUTBOX_NAME)):
        ident = str(row.get("id"))
        if ident in acked:
            continue
        if ident in refused:
            row = {**row, "refusal": refused[ident]}
        rows.append(row)
    return rows


def _receipt_uuid(receipt_id: str) -> str:
    try:
        return str(uuid.UUID(str(receipt_id).strip()))
    except ValueError as exc:
        msg = f"receipt {receipt_id!r} is not a connector receipt id (a UUID)"
        raise RelayError(msg) from exc


def ack(workspace: str | Path, ident: str, receipt_id: str) -> dict[str, Any]:
    """Record the hosted receipt id for one entry. Refuses anything but a UUID.

    An ack supersedes any earlier refusal of the same entry.
    """

    receipt = _receipt_uuid(receipt_id)
    directory = relay_dir(workspace)
    with _locked(directory):
        if not any(row.get("id") == ident for row in _read(relay_file(directory, OUTBOX_NAME))):
            msg = f"no outbox entry {ident!r} in {directory}"
            raise RelayError(msg)
        existing = {str(row.get("id")): row for row in _read(relay_file(directory, ACKS_NAME))}
        if ident in existing:
            return existing[ident]
        row = {"id": ident, "receipt_id": receipt, "acked_at": datetime.now(UTC).isoformat()}
        _append(relay_file(directory, ACKS_NAME), row)
        entry = next(r for r in _read(relay_file(directory, OUTBOX_NAME)) if r.get("id") == ident)
    if entry.get("operation") == "close":
        _discharge_close(Path(workspace), entry.get("arguments") or {}, receipt)
    return row


def refuse(workspace: str | Path, ident: str, receipt_id: str, reason: str) -> dict[str, Any]:
    """Record the connector's refusal of one entry, with its rejection receipt id.

    The entry stops blocking the Stop gate but stays listed. The receipt must be
    the connector's (a UUID) and the reason must be stated: a refusal is the
    verdict the agent reports, never a way to silence an entry it did not try.
    An acknowledged entry cannot be refused — a refusal never supersedes a
    hosted receipt.
    """

    receipt = _receipt_uuid(receipt_id)
    text = " ".join(str(reason or "").split())
    if not text:
        msg = "a refusal must state the connector's reason (--reason)"
        raise RelayError(msg)
    directory = relay_dir(workspace)
    with _locked(directory):
        if not any(row.get("id") == ident for row in _read(relay_file(directory, OUTBOX_NAME))):
            msg = f"no outbox entry {ident!r} in {directory}"
            raise RelayError(msg)
        acked = {str(row.get("id")): row for row in _read(relay_file(directory, ACKS_NAME))}
        if ident in acked:
            msg = (
                f"entry {ident!r} is already acknowledged with receipt "
                f"{acked[ident].get('receipt_id')}; a refusal cannot supersede a hosted receipt"
            )
            raise RelayError(msg)
        for row in _read(relay_file(directory, REFUSALS_NAME)):
            if row.get("id") == ident and row.get("receipt_id") == receipt:
                return row
        row = {
            "id": ident,
            "receipt_id": receipt,
            "reason": text,
            "refused_at": datetime.now(UTC).isoformat(),
        }
        _append(relay_file(directory, REFUSALS_NAME), row)
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
        lines.extend(
            [
                f"- [{row.get('id')}] {row.get('operation')} from {row.get('surface')}: "
                f"call {row.get('tool')} {args}",
                f"  then: python -m ops.memory.relay ack {row.get('id')} --receipt <receipt_id> "
                f'--workspace "{workspace}"',
                f"  or, if the connector refuses: python -m ops.memory.relay refuse "
                f"{row.get('id')} --receipt <receipt_id> "
                f'--reason "<connector reason>" --workspace "{workspace}"',
            ]
        )
        refusal = row.get("refusal")
        if isinstance(refusal, Mapping):
            lines.append(
                f"  REFUSED by the connector (receipt {refusal.get('receipt_id')}): "
                f"{refusal.get('reason')} — not blocking; an ack supersedes it"
            )
    lines.append(
        "A refusal from the connector is the verdict: record it with `refuse` (the rejection "
        "receipt_id and the connector's reason) and report it; do not retry through another "
        "door (no memory.ingest, no operator CLI write). A refused entry stops blocking Stop "
        "but stays listed until a later ack supersedes it."
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
    refuse_p = sub.add_parser(
        "refuse", parents=[after], help="record the connector's refusal (non-blocking, visible)"
    )
    refuse_p.add_argument("id")
    refuse_p.add_argument("--receipt", required=True, help="the rejection receipt_id")
    refuse_p.add_argument("--reason", required=True, help="the connector's stated reason")
    args = parser.parse_args(argv)
    try:
        return _run(args.command, Path(args.workspace), args)
    except RelayError as exc:
        print(f"relay: REFUSED — {exc}", file=sys.stderr)
        return 1


def _run(command: str, workspace: Path, args: argparse.Namespace) -> int:
    if command == "pending":
        print(json.dumps(pending(workspace), indent=2, sort_keys=True, ensure_ascii=False))
    elif command == "status":
        owed = pending(workspace)
        total = len(_read(relay_file(relay_dir(workspace), OUTBOX_NAME)))
        refused = sum(1 for row in owed if row.get("refusal"))
        print(
            json.dumps(
                {
                    "total": total,
                    "acked": total - len(owed),
                    "pending": len(owed),
                    "refused": refused,
                }
            )
        )
    elif command == "instructions":
        owed = pending(workspace)
        print(instruction(workspace, owed) if owed else "L9 MEMORY RELAY — nothing owed")
    elif command == "refuse":
        print(json.dumps(refuse(workspace, args.id, args.receipt, args.reason), sort_keys=True))
    else:
        print(json.dumps(ack(workspace, args.id, args.receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
