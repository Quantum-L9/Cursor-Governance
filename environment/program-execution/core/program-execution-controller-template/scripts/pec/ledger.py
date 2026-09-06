"""The append-only event ledger: SQLite is the chain, the file is its projection.

`events.jsonl` used to be the chain itself: `append` counted its lines to mint
the next sequence and wrote outside any transaction, so a crash between a state
row and its event, or two Controller processes appending at once, left the
runtime disagreeing with its own history (PEC-P1-004).

Now every event is allocated and inserted under the Controller's single-writer
transaction (`StateDB.append_event`), together with the state change it
records, and only after that transaction commits is the line appended to the
file and the row marked projected. The file stays for human and tool
consumption; its order is the committed sequence, never a count of lines.
Startup reconciliation (`runtime.reconcile_runtime`) re-projects whatever a
crash left pending. A file that disagrees with the chain -- shorter, longer,
or edited -- is an integrity failure, never adopted.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import canonical_json, digest_object, utc_now


class LedgerError(RuntimeError):
    pass


#: Legacy anchor key (pre-R8 runtimes recorded only the tail here). Kept
#: current so older tooling that reads it still sees the committed tail.
LEDGER_ANCHOR_KEY = "ledger_anchor"


def verify_chain(events: list[dict[str, Any]]) -> tuple[bool, str]:
    """Structural verification of a list of events, wherever they came from."""
    previous = None
    for index, event in enumerate(events, start=1):
        if event.get("sequence") != index:
            return False, f"sequence mismatch at event {index}"
        if event.get("previous_digest") != previous:
            return False, f"previous digest mismatch at event {index}"
        claimed = event.get("digest")
        body = dict(event)
        body.pop("digest", None)
        if digest_object(body) != claimed:
            return False, f"digest mismatch at event {index}"
        previous = claimed
    return True, "PASS"


class EventLedger:
    def __init__(self, path: Path, anchor_store: Any | None = None):
        self.path = path
        self.anchor_store = anchor_store
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    # ------------------------------------------------------------- reading
    def file_events(self) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        if not self.path.exists():
            return values
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LedgerError(f"invalid JSON at ledger line {number}: {exc}") from exc
        return values

    def events(self) -> list[dict[str, Any]]:
        """The canonical chain: the database when there is one, else the file."""
        if self.anchor_store is not None and hasattr(self.anchor_store, "events"):
            return self.anchor_store.events()
        return self.file_events()

    # ------------------------------------------------------------ writing
    def append(self, event_type: str, actor: str, payload: dict[str, Any]) -> dict[str, Any]:
        db = self.anchor_store
        if db is None or not hasattr(db, "append_event"):
            # File-only ledger (no runtime store): the legacy behaviour.
            events = self.file_events()
            previous = events[-1]["digest"] if events else None
            event = {
                "sequence": len(events) + 1,
                "timestamp": utc_now(),
                "type": event_type,
                "actor": actor,
                "payload": payload,
                "previous_digest": previous,
            }
            event["digest"] = digest_object(event)
            self._write_line(event)
            return event
        event = db.append_event(event_type, actor, payload)
        db.set_meta(LEDGER_ANCHOR_KEY, {"sequence": event["sequence"], "digest": event["digest"]})
        # Projection only after the enclosing transaction commits (now, if none).
        db.on_commit(self.project_pending)
        return event

    def _write_line(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(event) + "\n")

    def project_pending(self) -> int:
        """Append every committed-but-unprojected event, in sequence order.

        Refuses (and leaves the rows pending) when the file does not end where
        the projected prefix says it should: a file that is ahead of, or
        diverges from, the chain is an integrity finding for `verify`, not
        something to append on top of.
        """
        db = self.anchor_store
        if db is None or not hasattr(db, "pending_events"):
            return 0
        # Under the single-writer lock: two Controllers finishing at once must
        # not both read the same pending set and both append it. The rows are
        # marked as each line lands, so an interruption mid-way leaves the file
        # exactly one line ahead of the mark, which verify() accepts and the
        # next projection completes.
        with db.controller_transaction():
            pending = db.pending_events()
            if not pending:
                return 0
            projected = db.projected_event_count()
            try:
                on_disk = self.file_events()
            except LedgerError:
                return 0
            if len(on_disk) < projected:
                return 0
            already = on_disk[projected:]
            written = 0
            for index, event in enumerate(pending):
                if index < len(already):
                    if already[index] != event:
                        return written
                else:
                    self._write_line(event)
                db.mark_event_projected(int(event["sequence"]))
                written += 1
            return written

    # ---------------------------------------------------------- verifying
    def verify(self) -> tuple[bool, str]:
        db = self.anchor_store
        if db is None or not hasattr(db, "events"):
            try:
                return verify_chain(self.file_events())
            except LedgerError as exc:
                return False, str(exc)
        chain = db.events()
        ok, message = verify_chain(chain)
        if not ok:
            return False, f"canonical event chain broken: {message}"
        try:
            on_disk = self.file_events()
        except LedgerError as exc:
            return False, str(exc)
        projected = db.projected_event_count()
        expected = chain[:projected]
        if len(on_disk) < projected:
            return False, (
                "ledger truncated or replaced: state anchors event "
                f"{projected} but the file ends at "
                f"{on_disk[-1].get('sequence') if on_disk else 0}"
            )
        for index, (recorded, line) in enumerate(zip(expected, on_disk, strict=False), start=1):
            if line != recorded:
                return False, f"ledger projection tampered at event {index}"
        if len(on_disk) > len(chain):
            return False, (
                f"ledger carries {len(on_disk) - len(chain)} event(s) with no canonical "
                f"record after sequence {len(chain)}"
            )
        # Lines beyond the projected prefix must be exactly the pending events
        # (a projection interrupted between the write and the mark).
        for index, (recorded, line) in enumerate(
            zip(chain[projected:], on_disk[projected:], strict=False), start=projected + 1
        ):
            if line != recorded:
                return False, f"ledger projection tampered at event {index}"
        return True, "PASS"
