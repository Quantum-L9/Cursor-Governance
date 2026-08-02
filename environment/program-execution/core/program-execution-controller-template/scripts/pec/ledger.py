from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import canonical_json, digest_object, utc_now


class LedgerError(RuntimeError):
    pass


class EventLedger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

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
        return event

    def verify(self) -> tuple[bool, str]:
        previous = None
        try:
            events = self.events()
        except LedgerError as exc:
            return False, str(exc)
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
