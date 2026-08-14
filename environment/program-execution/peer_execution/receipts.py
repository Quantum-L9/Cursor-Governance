from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import LifecycleReceipt


class ReceiptChain:
    def __init__(self, root: str | Path) -> None:
        self.path = Path(root).expanduser().resolve() / "lifecycle-receipts.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, receipt: LifecycleReceipt) -> None:
        previous = self.last_digest()
        if receipt.previous_receipt_digest != previous:
            raise ValueError("lifecycle receipt previous digest mismatch")
        if not receipt.is_valid():
            raise ValueError("invalid lifecycle receipt digest")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt.to_dict(), sort_keys=True) + "\n")

    def last_digest(self) -> str | None:
        if not self.path.exists():
            return None
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line]
        if not lines:
            return None
        return json.loads(lines[-1])["receipt_digest"]

    def verify(self) -> list[str]:
        if not self.path.exists():
            return []
        errors: list[str] = []
        previous = None
        lines = self.path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, 1):
            raw: dict[str, Any] = json.loads(line)
            if raw.get("previous_receipt_digest") != previous:
                errors.append(f"line {index}: previous digest mismatch")
            from .digests import verify_embedded_digest

            if not verify_embedded_digest(raw, "receipt_digest"):
                errors.append(f"line {index}: receipt digest mismatch")
            previous = raw.get("receipt_digest")
        return errors
