from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise RuntimeError("classifier.py requires the 'PyYAML' package") from exc
PRIMARY_CLASSES = {
    "repository_fact",
    "architecture_boundary",
    "ownership_finding",
    "dependency_finding",
    "implementation_surface",
    "execution_procedure",
    "validation_procedure",
    "failure_pattern",
    "rejected_approach",
    "context_requirement",
    "context_waste",
    "task_contract_gap",
    "policy_candidate",
    "invariant_candidate",
    "regression_candidate",
    "reusable_pattern_candidate",
    "artifact_lineage",
    "unresolved_unknown",
    "follow_on_opportunity",
    "evidence_only",
}
EPISTEMIC_STATUSES = {
    "observed",
    "derived",
    "hypothesized",
    "disproven",
    "contested",
    "unresolved",
}
HIGH_AUTHORITY_CLASSES = {
    "architecture_boundary",
    "ownership_finding",
    "policy_candidate",
    "invariant_candidate",
}
MEDIUM_AUTHORITY_CLASSES = {
    "task_contract_gap",
    "validation_procedure",
    "failure_pattern",
    "regression_candidate",
    "reusable_pattern_candidate",
}
DEFAULT_ROUTES = {
    "repository_fact": ["memory"],
    "architecture_boundary": ["architecture"],
    "ownership_finding": ["architecture"],
    "dependency_finding": ["architecture", "memory"],
    "implementation_surface": ["memory", "contracts"],
    "execution_procedure": ["patterns"],
    "validation_procedure": ["validation", "patterns"],
    "failure_pattern": ["validation", "patterns"],
    "rejected_approach": ["memory", "patterns"],
    "context_requirement": ["contracts", "memory"],
    "context_waste": ["contracts"],
    "task_contract_gap": ["contracts"],
    "policy_candidate": ["architecture"],
    "invariant_candidate": ["validation"],
    "regression_candidate": ["validation"],
    "reusable_pattern_candidate": ["patterns"],
    "artifact_lineage": ["memory"],
    "unresolved_unknown": ["opportunities"],
    "follow_on_opportunity": ["opportunities"],
    "evidence_only": ["evidence"],
}


class ClassificationFailure(ValueError):
    """Raised when a generated data unit cannot be classified safely."""


@dataclass(frozen=True)
class Classification:
    unit_id: str
    primary_class: str
    epistemic_status: str
    authority_sensitivity: str
    evidence_strength: str
    confidence_band: str
    reuse_horizon: str
    risk_of_incorrect_reuse: str
    normalized_routes: tuple[str, ...]
    classification_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "primary_class": self.primary_class,
            "epistemic_status": self.epistemic_status,
            "authority_sensitivity": self.authority_sensitivity,
            "evidence_strength": self.evidence_strength,
            "confidence_band": self.confidence_band,
            "reuse_horizon": self.reuse_horizon,
            "risk_of_incorrect_reuse": self.risk_of_incorrect_reuse,
            "normalized_routes": list(self.normalized_routes),
            "classification_hash": self.classification_hash,
        }


class GeneratedDataClassifier:
    """Deterministically enrich validated generated data units."""

    def classify(
        self,
        unit: Mapping[str, Any],
    ) -> Classification:
        unit_id = self._required_string(unit, "unit_id")
        primary_class = self._required_string(
            unit,
            "primary_class",
        )
        epistemic_status = self._required_string(
            unit,
            "epistemic_status",
        )
        if primary_class not in PRIMARY_CLASSES:
            raise ClassificationFailure(f"Unsupported primary_class: {primary_class!r}")
        if epistemic_status not in EPISTEMIC_STATUSES:
            raise ClassificationFailure(f"Unsupported epistemic_status: {epistemic_status!r}")
        authority_sensitivity = self._authority_sensitivity(primary_class)
        evidence_strength = self._evidence_strength(unit)
        confidence_band = self._confidence_band(unit)
        reuse_horizon = self._reuse_horizon(unit)
        risk = self._incorrect_reuse_risk(
            primary_class=primary_class,
            epistemic_status=epistemic_status,
            evidence_strength=evidence_strength,
            confidence_band=confidence_band,
        )
        proposed = unit.get("proposed_routes")
        if not isinstance(proposed, list) or not proposed:
            proposed = DEFAULT_ROUTES[primary_class]
        normalized_routes = tuple(
            sorted({str(route).strip() for route in proposed if str(route).strip()})
        )
        payload = {
            "unit_id": unit_id,
            "primary_class": primary_class,
            "epistemic_status": epistemic_status,
            "authority_sensitivity": authority_sensitivity,
            "evidence_strength": evidence_strength,
            "confidence_band": confidence_band,
            "reuse_horizon": reuse_horizon,
            "risk_of_incorrect_reuse": risk,
            "normalized_routes": normalized_routes,
        }
        return Classification(
            **payload,
            classification_hash=self._sha256(payload),
        )

    def classify_packet(
        self,
        packet: Mapping[str, Any],
    ) -> list[Classification]:
        units = packet.get("generated_data_units", [])
        if not isinstance(units, list):
            raise ClassificationFailure("generated_data_units must be a list")
        return [self.classify(unit) for unit in units if isinstance(unit, Mapping)]

    @staticmethod
    def _authority_sensitivity(
        primary_class: str,
    ) -> str:
        if primary_class in HIGH_AUTHORITY_CLASSES:
            return "high"
        if primary_class in MEDIUM_AUTHORITY_CLASSES:
            return "medium"
        return "low"

    @staticmethod
    def _evidence_strength(
        unit: Mapping[str, Any],
    ) -> str:
        evidence = unit.get("source_evidence", [])
        if not isinstance(evidence, list):
            return "none"
        count = len(evidence)
        if count == 0:
            return "none"
        independently_sourced = len(
            {
                str(item.get("source_id"))
                for item in evidence
                if isinstance(item, Mapping) and item.get("source_id")
            }
        )
        if count >= 3 and independently_sourced >= 2:
            return "strong"
        if count >= 1:
            return "moderate"
        return "none"

    @staticmethod
    def _confidence_band(
        unit: Mapping[str, Any],
    ) -> str:
        raw = unit.get("confidence", 0)
        try:
            confidence = float(raw)
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence >= 0.9:
            return "very_high"
        if confidence >= 0.75:
            return "high"
        if confidence >= 0.5:
            return "medium"
        if confidence >= 0.25:
            return "low"
        return "very_low"

    @staticmethod
    def _reuse_horizon(
        unit: Mapping[str, Any],
    ) -> str:
        expected = unit.get("expected_reuse")
        if isinstance(expected, Mapping):
            if expected.get("cross_repository"):
                return "cross_repository"
            if expected.get("cross_campaign"):
                return "cross_campaign"
            if expected.get("cross_task"):
                return "cross_task"
        return "task_local"

    @staticmethod
    def _incorrect_reuse_risk(
        *,
        primary_class: str,
        epistemic_status: str,
        evidence_strength: str,
        confidence_band: str,
    ) -> str:
        score = 0
        if primary_class in HIGH_AUTHORITY_CLASSES:
            score += 3
        elif primary_class in MEDIUM_AUTHORITY_CLASSES:
            score += 2
        else:
            score += 1
        if epistemic_status in {
            "hypothesized",
            "contested",
            "unresolved",
        }:
            score += 3
        elif epistemic_status == "derived":
            score += 1
        if evidence_strength == "none":
            score += 2
        elif evidence_strength == "moderate":
            score += 1
        if confidence_band in {"very_low", "low"}:
            score += 2
        elif confidence_band == "medium":
            score += 1
        if score >= 7:
            return "critical"
        if score >= 5:
            return "high"
        if score >= 3:
            return "medium"
        return "low"

    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise ClassificationFailure(f"{field_name!r} must be a non-empty string")
        return raw.strip()

    @staticmethod
    def _sha256(value: Mapping[str, Any]) -> str:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def load_data(path: str | Path) -> Any:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        if source.suffix.lower() == ".json":
            return json.load(handle)
        if source.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(handle)
    raise ValueError(f"Unsupported file type: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify generated data units deterministically.")
    parser.add_argument("packet")
    args = parser.parse_args()
    packet = load_data(args.packet)
    if not isinstance(packet, Mapping):
        raise SystemExit("Packet root must be an object")
    classifications = GeneratedDataClassifier().classify_packet(packet)
    print(
        json.dumps(
            [item.to_dict() for item in classifications],
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
