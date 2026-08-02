"""Evidence archive (law §13, §26 Tier 1): raw output retained as evidence.

Capture-before-distillation. The archive persists the raw packet mapping so a
promoted unit can always be traced to its source. Tier-1 evidence is never loaded
wholesale into future context (SGD-011); retrieval is by id only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArchiveRecord:
    packet_id: str
    campaign_id: str
    path: Path


class EvidenceArchive:
    """Filesystem-backed Tier-1 archive, one JSON file per packet."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    def _campaign_dir(self, campaign_id: str) -> Path:
        return self._root / campaign_id

    def persist(self, raw_packet: dict[str, object]) -> ArchiveRecord:
        packet_id = str(raw_packet.get("packet_id", "")).strip()
        identity = raw_packet.get("identity")
        campaign_id = ""
        if isinstance(identity, dict):
            campaign_id = str(identity.get("campaign_id", "")).strip()
        if not packet_id or not campaign_id:
            raise ValueError("cannot archive packet without packet_id and identity.campaign_id")
        target_dir = self._campaign_dir(campaign_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{packet_id}.json"
        path.write_text(json.dumps(raw_packet, indent=2, sort_keys=True), encoding="utf-8")
        return ArchiveRecord(packet_id=packet_id, campaign_id=campaign_id, path=path)

    def load(self, campaign_id: str, packet_id: str) -> dict[str, object]:
        path = self._campaign_dir(campaign_id) / f"{packet_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def packet_ids(self, campaign_id: str) -> list[str]:
        target_dir = self._campaign_dir(campaign_id)
        if not target_dir.exists():
            return []
        return sorted(p.stem for p in target_dir.glob("*.json"))
