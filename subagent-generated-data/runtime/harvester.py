from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise RuntimeError("harvester.py requires the 'PyYAML' package") from exc
RUNTIME_DIR = Path(__file__).resolve().parent
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))
from classifier import GeneratedDataClassifier
from packet_validator import PacketValidator


class HarvestFailure(ValueError):
    """Raised when harvesting cannot proceed safely."""


@dataclass(frozen=True)
class HarvestedUnit:
    unit_id: str
    source_packet_id: str
    source_action_id: str
    source_agent_id: str
    source_role: str
    repository: str
    base_sha: str
    statement_hash: str
    normalized_statement: str
    classification: Mapping[str, Any]
    original_unit: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "source_packet_id": self.source_packet_id,
            "source_action_id": self.source_action_id,
            "source_agent_id": self.source_agent_id,
            "source_role": self.source_role,
            "repository": self.repository,
            "base_sha": self.base_sha,
            "statement_hash": self.statement_hash,
            "normalized_statement": self.normalized_statement,
            "classification": dict(self.classification),
            "original_unit": dict(self.original_unit),
        }


@dataclass(frozen=True)
class HarvestResult:
    packet_id: str
    packet_hash: str
    valid: bool
    harvested_units: tuple[HarvestedUnit, ...]
    duplicate_unit_ids: tuple[str, ...]
    rejected_units: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "valid": self.valid,
            "harvested_units": [unit.to_dict() for unit in self.harvested_units],
            "duplicate_unit_ids": list(self.duplicate_unit_ids),
            "rejected_units": [dict(item) for item in self.rejected_units],
        }


class SubagentDataHarvester:
    """Extract reusable generated-data units from a validated packet."""

    def __init__(
        self,
        *,
        validator: PacketValidator | None = None,
        classifier: GeneratedDataClassifier | None = None,
    ) -> None:
        self.validator = validator or PacketValidator()
        self.classifier = classifier or GeneratedDataClassifier()

    def harvest(
        self,
        packet: Mapping[str, Any],
    ) -> HarvestResult:
        validation = self.validator.validate(
            packet,
            raise_on_error=True,
        )
        packet_id = self._required_string(
            packet,
            "packet_id",
        )
        identity = self._required_mapping(
            packet,
            "identity",
        )
        source_action_id = self._required_string(
            identity,
            "action_id",
        )
        source_agent_id = self._required_string(
            identity,
            "agent_id",
        )
        source_role = self._required_string(
            identity,
            "role",
        )
        repository = self._required_string(
            identity,
            "repository",
        )
        base_sha = self._required_string(
            identity,
            "base_sha",
        )
        harvested: list[HarvestedUnit] = []
        rejected: list[Mapping[str, Any]] = []
        duplicates: list[str] = []
        seen_unit_ids: set[str] = set()
        seen_semantic_keys: set[str] = set()
        units = packet.get("generated_data_units", [])
        if not isinstance(units, list):
            raise HarvestFailure("generated_data_units must be a list")
        for unit in units:
            if not isinstance(unit, Mapping):
                rejected.append(
                    {
                        "reason": "unit_not_object",
                        "unit": unit,
                    }
                )
                continue
            unit_id = self._required_string(
                unit,
                "unit_id",
            )
            statement = self._required_string(
                unit,
                "statement",
            )
            if unit_id in seen_unit_ids:
                duplicates.append(unit_id)
                continue
            seen_unit_ids.add(unit_id)
            normalized = self._normalize_statement(statement)
            semantic_key = self._semantic_key(
                primary_class=str(unit.get("primary_class", "")),
                normalized_statement=normalized,
                repository=repository,
                scope=unit.get("scope"),
            )
            if semantic_key in seen_semantic_keys:
                duplicates.append(unit_id)
                continue
            seen_semantic_keys.add(semantic_key)
            classification = self.classifier.classify(unit).to_dict()
            harvested.append(
                HarvestedUnit(
                    unit_id=unit_id,
                    source_packet_id=packet_id,
                    source_action_id=source_action_id,
                    source_agent_id=source_agent_id,
                    source_role=source_role,
                    repository=repository,
                    base_sha=base_sha,
                    statement_hash=self._sha256_text(normalized),
                    normalized_statement=normalized,
                    classification=classification,
                    original_unit=dict(unit),
                )
            )
        return HarvestResult(
            packet_id=packet_id,
            packet_hash=validation.packet_hash or "",
            valid=True,
            harvested_units=tuple(harvested),
            duplicate_unit_ids=tuple(sorted(duplicates)),
            rejected_units=tuple(rejected),
        )

    @staticmethod
    def _normalize_statement(value: str) -> str:
        return " ".join(value.strip().split())

    @staticmethod
    def _semantic_key(
        *,
        primary_class: str,
        normalized_statement: str,
        repository: str,
        scope: Any,
    ) -> str:
        payload = {
            "primary_class": primary_class,
            "normalized_statement": normalized_statement.lower(),
            "repository": repository,
            "scope": scope,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _sha256_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise HarvestFailure(f"{field_name!r} must be a non-empty string")
        return raw.strip()

    @staticmethod
    def _required_mapping(
        value: Mapping[str, Any],
        field_name: str,
    ) -> Mapping[str, Any]:
        raw = value.get(field_name)
        if not isinstance(raw, Mapping):
            raise HarvestFailure(f"{field_name!r} must be an object")
        return raw


def load_data(path: str | Path) -> Any:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        if source.suffix.lower() == ".json":
            return json.load(handle)
        if source.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(handle)
    raise ValueError(f"Unsupported file type: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest validated subagent-generated data.")
    parser.add_argument("packet")
    parser.add_argument("--output")
    args = parser.parse_args()
    packet = load_data(args.packet)
    if not isinstance(packet, Mapping):
        raise SystemExit("Packet root must be an object")
    result = SubagentDataHarvester().harvest(packet).to_dict()
    rendered = json.dumps(
        result,
        indent=2,
        sort_keys=True,
    )
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            rendered + "\n",
            encoding="utf-8",
        )
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
