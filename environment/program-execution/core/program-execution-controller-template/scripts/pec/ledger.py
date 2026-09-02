from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import canonical_json, digest_object, utc_now


class LedgerError(RuntimeError):
    pass


#: State key holding the tail of the chain as last appended. The ledger file
#: alone can prove that nothing was inserted or edited, but not that nothing
#: was cut off the end or that the file is the one that was written: a missing
#: file was silently recreated empty and an empty chain verifies trivially.
LEDGER_ANCHOR_KEY = "ledger_anchor"


class EventLedger:
    def __init__(self, path: Path, anchor_store: Any | None = None):
        self.path = path
        self.anchor_store = anchor_store
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _anchor(self) -> dict[str, Any] | None:
        if self.anchor_store is None:
            return None
        value = self.anchor_store.get_meta(LEDGER_ANCHOR_KEY)
        return value if isinstance(value, dict) else None

    def events(self) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LedgerError(f"invalid JSON at ledger line {number}: {exc}") from exc
        return values

    def append(self, event_type: str, actor: str, payload: dict[str, Any]) -> dict[str, Any]:
        events = self.events()
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
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(event) + "\n")
        if self.anchor_store is not None:
            self.anchor_store.set_meta(
                LEDGER_ANCHOR_KEY, {"sequence": event["sequence"], "digest": event["digest"]}
            )
        return event

    def verify(self) -> tuple[bool, str]:
        previous = None
        try:
            events = self.events()
        except LedgerError as exc:
            return False, str(exc)
        anchor = self._anchor()
        if anchor is not None:
            tail = events[-1] if events else None
            if (
                tail is None
                or tail.get("sequence") != anchor.get("sequence")
                or tail.get("digest") != anchor.get("digest")
            ):
                return False, (
                    "ledger truncated or replaced: state anchors event "
                    f"{anchor.get('sequence')} but the file ends at "
                    f"{tail.get('sequence') if tail else 0}"
                )
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
