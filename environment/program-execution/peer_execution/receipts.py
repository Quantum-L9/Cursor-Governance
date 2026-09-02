from __future__ import annotations

import contextlib
import fcntl
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .digests import verify_embedded_digest
from .models import LifecycleReceipt


class ReceiptChainError(ValueError):
    """The on-disk chain cannot be trusted as a chain."""


class ReceiptChain:
    """Append-only lifecycle receipt chain, safe across processes.

    `append` used to read the last digest and then open the file for append as
    two unrelated steps. Two controller CLI processes on the same runtime root
    (a dispatch and a status poll) could both read digest N and both append a
    receipt chained to it, and a crash between the write and the flush left a
    partial last line that `last_digest` then failed to parse. The chain is now
    extended under an exclusive file lock, the line is written and fsynced as
    one unit, and a partial tail is refused rather than parsed around.
    """

    def __init__(self, root: str | Path) -> None:
        self.path = Path(root).expanduser().resolve() / "lifecycle-receipts.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.path.with_name(self.path.name + ".lock")

    @contextlib.contextmanager
    def _locked(self) -> Iterator[None]:
        with self._lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def append(self, receipt: LifecycleReceipt) -> None:
        with self._locked():
            previous = self._last_digest_unlocked()
            if receipt.previous_receipt_digest != previous:
                raise ValueError("lifecycle receipt previous digest mismatch")
            if not receipt.is_valid():
                raise ValueError("invalid lifecycle receipt digest")
            line = json.dumps(receipt.to_dict(), sort_keys=True) + "\n"
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())

    def last_digest(self) -> str | None:
        with self._locked():
            return self._last_digest_unlocked()

    def _last_digest_unlocked(self) -> str | None:
        if not self.path.exists():
            return None
        text = self.path.read_text(encoding="utf-8")
        if not text.strip():
            return None
        if not text.endswith("\n"):
            raise ReceiptChainError(
                f"lifecycle receipt chain {self.path} ends in a partial line; "
                "a previous append did not complete -- repair or quarantine the chain"
            )
        last = text.rstrip("\n").splitlines()[-1]
        try:
            record = json.loads(last)
        except json.JSONDecodeError as exc:
            raise ReceiptChainError(
                f"lifecycle receipt chain {self.path} tail is not a JSON object: {exc}"
            ) from exc
        digest = record.get("receipt_digest") if isinstance(record, dict) else None
        if not isinstance(digest, str) or not digest:
            raise ReceiptChainError(f"lifecycle receipt chain {self.path} tail has no digest")
        return digest

    def verify(self) -> list[str]:
        if not self.path.exists():
            return []
        errors: list[str] = []
        previous = None
        text = self.path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if text and not text.endswith("\n"):
            errors.append(f"line {len(lines)}: partial line (append did not complete)")
        for index, line in enumerate(lines, 1):
            if not line.strip():
                errors.append(f"line {index}: empty line inside the chain")
                continue
            try:
                raw: dict[str, Any] = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"line {index}: not JSON ({exc.msg})")
                continue
            if not isinstance(raw, dict):
                errors.append(f"line {index}: not a receipt object")
                continue
            if raw.get("previous_receipt_digest") != previous:
                errors.append(f"line {index}: previous digest mismatch")
            if not verify_embedded_digest(raw, "receipt_digest"):
                errors.append(f"line {index}: receipt digest mismatch")
            previous = raw.get("receipt_digest")
        return errors
