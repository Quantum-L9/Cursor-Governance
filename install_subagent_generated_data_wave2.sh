#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
BASE="$ROOT/subagent-generated-data"
RUNTIME="$BASE/runtime"
ROUTES="$BASE/routes"
if [[ ! -f "$BASE/law/SUBAGENT_GENERATED_DATA_LAW.md" ]]; then
  echo "ERROR: Wave 1 law is missing: $BASE/law/SUBAGENT_GENERATED_DATA_LAW.md" >&2
  exit 1
fi
if [[ ! -d "$BASE/schemas" ]]; then
  echo "ERROR: Wave 1 schemas directory is missing: $BASE/schemas" >&2
  exit 1
fi
if [[ ! -d "$BASE/roles" ]]; then
  echo "ERROR: Wave 1 roles directory is missing: $BASE/roles" >&2
  exit 1
fi
mkdir -p "$RUNTIME" "$ROUTES"
cat > "$RUNTIME/__init__.py" <<'PY'
"""
L9 Subagent-Generated Data runtime.
Wave 2 provides:
- packet validation
- generated-data harvesting
- deterministic classification
- route selection
- promotion gating
- campaign learning-closure evaluation
The runtime is governance infrastructure. It does not own destination systems
such as Graphiti memory, task contracts, validation implementations,
architecture authority, or opportunity planning.
"""
__version__ = "1.0.0"
PY
cat > "$RUNTIME/packet_validator.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
try:
    from jsonschema import Draft202012Validator, RefResolver
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError as exc:
    raise RuntimeError(
        "packet_validator.py requires the 'jsonschema' package"
    ) from exc
try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "packet_validator.py requires the 'PyYAML' package"
    ) from exc
RUNTIME_DIR = Path(__file__).resolve().parent
BASE_DIR = RUNTIME_DIR.parent
SCHEMAS_DIR = BASE_DIR / "schemas"
ROLES_DIR = BASE_DIR / "roles"
PACKET_SCHEMA = SCHEMAS_DIR / "subagent-data-packet.schema.json"
UNIT_SCHEMA = SCHEMAS_DIR / "generated-data-unit.schema.json"
PROVENANCE_SCHEMA = SCHEMAS_DIR / "provenance.schema.json"
ROUTING_SCHEMA = SCHEMAS_DIR / "routing-decision.schema.json"
CLOSURE_SCHEMA = SCHEMAS_DIR / "learning-closure.schema.json"
class PacketValidationFailure(ValueError):
    """Raised when a subagent data packet violates a required contract."""
@dataclass(frozen=True)
class ValidationFinding:
    code: str
    severity: str
    message: str
    location: str
    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
        }
@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    packet_id: str | None
    packet_hash: str | None
    schema_version: str | None
    role: str | None
    findings: tuple[ValidationFinding, ...]
    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "packet_id": self.packet_id,
            "packet_hash": self.packet_hash,
            "schema_version": self.schema_version,
            "role": self.role,
            "findings": [finding.to_dict() for finding in self.findings],
        }
class PacketValidator:
    """Validate packets against Wave 1 schemas and role obligations."""
    def __init__(
        self,
        *,
        schemas_dir: str | Path = SCHEMAS_DIR,
        roles_dir: str | Path = ROLES_DIR,
    ) -> None:
        self.schemas_dir = Path(schemas_dir)
        self.roles_dir = Path(roles_dir)
        self.packet_schema = self._load_json(
            self.schemas_dir / "subagent-data-packet.schema.json"
        )
        self.schema_store = self._load_schema_store(self.schemas_dir)
        self.validator = self._build_validator(self.packet_schema)
        Draft202012Validator.check_schema(self.packet_schema)
    def validate(
        self,
        packet: Mapping[str, Any],
        *,
        raise_on_error: bool = False,
    ) -> ValidationReport:
        findings: list[ValidationFinding] = []
        findings.extend(self._schema_findings(packet))
        findings.extend(self._semantic_findings(packet))
        findings.extend(self._role_findings(packet))
        valid = not any(
            finding.severity == "error" for finding in findings
        )
        report = ValidationReport(
            valid=valid,
            packet_id=self._optional_string(packet.get("packet_id")),
            packet_hash=(
                self._sha256_json(packet)
                if isinstance(packet, Mapping)
                else None
            ),
            schema_version=self._optional_string(
                packet.get("schema_version")
            ),
            role=self._packet_role(packet),
            findings=tuple(findings),
        )
        if raise_on_error and not valid:
            rendered = "\n".join(
                f"{item.code} {item.location}: {item.message}"
                for item in report.findings
                if item.severity == "error"
            )
            raise PacketValidationFailure(rendered)
        return report
    def validate_file(
        self,
        path: str | Path,
        *,
        raise_on_error: bool = False,
    ) -> ValidationReport:
        packet = self._load_data(path)
        if not isinstance(packet, Mapping):
            raise PacketValidationFailure(
                f"Packet root must be an object: {path}"
            )
        return self.validate(
            packet,
            raise_on_error=raise_on_error,
        )
    def validate_schema_set(self) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        required = (
            "subagent-data-packet.schema.json",
            "generated-data-unit.schema.json",
            "provenance.schema.json",
            "routing-decision.schema.json",
            "learning-closure.schema.json",
        )
        for filename in required:
            path = self.schemas_dir / filename
            if not path.is_file():
                findings.append(
                    ValidationFinding(
                        code="SGD-SCHEMA-MISSING",
                        severity="error",
                        message=f"Required schema is missing: {filename}",
                        location=str(path),
                    )
                )
                continue
            try:
                schema = self._load_json(path)
                Draft202012Validator.check_schema(schema)
            except (ValueError, SchemaError) as exc:
                findings.append(
                    ValidationFinding(
                        code="SGD-SCHEMA-INVALID",
                        severity="error",
                        message=str(exc),
                        location=str(path),
                    )
                )
        return findings
    def _schema_findings(
        self,
        packet: Mapping[str, Any],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for error in sorted(
            self.validator.iter_errors(packet),
            key=lambda item: list(item.absolute_path),
        ):
            location = "$"
            if error.absolute_path:
                location += "." + ".".join(
                    str(part) for part in error.absolute_path
                )
            findings.append(
                ValidationFinding(
                    code="SGD-PACKET-SCHEMA",
                    severity="error",
                    message=error.message,
                    location=location,
                )
            )
        return findings
    def _semantic_findings(
        self,
        packet: Mapping[str, Any],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        identity = packet.get("identity")
        if not isinstance(identity, Mapping):
            return findings
        base_sha = identity.get("base_sha")
        provenance = packet.get("provenance")
        if isinstance(provenance, Mapping):
            provenance_sha = provenance.get("base_sha")
            if (
                isinstance(base_sha, str)
                and isinstance(provenance_sha, str)
                and base_sha != provenance_sha
            ):
                findings.append(
                    ValidationFinding(
                        code="SGD-BASE-SHA-MISMATCH",
                        severity="error",
                        message=(
                            "identity.base_sha and provenance.base_sha "
                            "must match"
                        ),
                        location="$.provenance.base_sha",
                    )
                )
        units = packet.get("generated_data_units", [])
        if isinstance(units, list):
            unit_ids: set[str] = set()
            for index, unit in enumerate(units):
                if not isinstance(unit, Mapping):
                    continue
                unit_id = unit.get("unit_id")
                if isinstance(unit_id, str):
                    if unit_id in unit_ids:
                        findings.append(
                            ValidationFinding(
                                code="SGD-DUPLICATE-UNIT-ID",
                                severity="error",
                                message=f"Duplicate unit_id: {unit_id}",
                                location=(
                                    f"$.generated_data_units[{index}].unit_id"
                                ),
                            )
                        )
                    unit_ids.add(unit_id)
                status = unit.get("epistemic_status")
                evidence = unit.get("source_evidence", [])
                if status in {"observed", "derived"} and not evidence:
                    findings.append(
                        ValidationFinding(
                            code="SGD-EVIDENCE-REQUIRED",
                            severity="error",
                            message=(
                                f"{status!r} units require source evidence"
                            ),
                            location=(
                                f"$.generated_data_units[{index}]"
                                ".source_evidence"
                            ),
                        )
                    )
                proposed_routes = unit.get("proposed_routes", [])
                if (
                    isinstance(proposed_routes, list)
                    and not proposed_routes
                ):
                    findings.append(
                        ValidationFinding(
                            code="SGD-ROUTE-REQUIRED",
                            severity="error",
                            message=(
                                "Every generated data unit requires at "
                                "least one proposed route"
                            ),
                            location=(
                                f"$.generated_data_units[{index}]"
                                ".proposed_routes"
                            ),
                        )
                    )
                invalidation = unit.get(
                    "invalidation_conditions",
                    [],
                )
                if (
                    unit.get("expected_reuse")
                    and not invalidation
                ):
                    findings.append(
                        ValidationFinding(
                            code="SGD-INVALIDATION-REQUIRED",
                            severity="error",
                            message=(
                                "Reusable units require invalidation "
                                "conditions"
                            ),
                            location=(
                                f"$.generated_data_units[{index}]"
                                ".invalidation_conditions"
                            ),
                        )
                    )
        unknowns = packet.get("unresolved_unknowns", [])
        if isinstance(unknowns, list):
            for index, unknown in enumerate(unknowns):
                if not isinstance(unknown, Mapping):
                    continue
                for field_name in (
                    "unknown_id",
                    "description",
                    "class",
                    "blocking_status",
                    "owner",
                    "next_action",
                    "evidence_needed",
                ):
                    if not unknown.get(field_name):
                        findings.append(
                            ValidationFinding(
                                code="SGD-UNKNOWN-INCOMPLETE",
                                severity="error",
                                message=(
                                    "Unresolved unknown is missing "
                                    f"{field_name!r}"
                                ),
                                location=(
                                    f"$.unresolved_unknowns[{index}]"
                                    f".{field_name}"
                                ),
                            )
                        )
        return findings
    def _role_findings(
        self,
        packet: Mapping[str, Any],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        role = self._packet_role(packet)
        if not role:
            return findings
        profile_path = self.roles_dir / f"{role}.yaml"
        if not profile_path.is_file():
            findings.append(
                ValidationFinding(
                    code="SGD-ROLE-PROFILE-MISSING",
                    severity="error",
                    message=f"No role profile exists for {role!r}",
                    location="$.identity.role",
                )
            )
            return findings
        profile = self._load_yaml(profile_path)
        if not isinstance(profile, Mapping):
            findings.append(
                ValidationFinding(
                    code="SGD-ROLE-PROFILE-INVALID",
                    severity="error",
                    message="Role profile root must be an object",
                    location=str(profile_path),
                )
            )
            return findings
        required_classes = set(
            profile.get("required_generated_data_classes", [])
        )
        units = packet.get("generated_data_units", [])
        present_classes = {
            str(unit.get("primary_class"))
            for unit in units
            if isinstance(unit, Mapping)
        }
        missing_classes = sorted(
            required_classes - present_classes
        )
        allows_empty = bool(
            profile.get("allows_empty_generated_data", True)
        )
        if (
            missing_classes
            and units
            and not allows_empty
        ):
            findings.append(
                ValidationFinding(
                    code="SGD-ROLE-CLASS-MISSING",
                    severity="error",
                    message=(
                        "Role packet does not include required generated "
                        "data classes: "
                        + ", ".join(missing_classes)
                    ),
                    location="$.generated_data_units",
                )
            )
        forbidden_promotions = set(
            profile.get("forbidden_self_promotion_targets", [])
        )
        for index, unit in enumerate(units):
            if not isinstance(unit, Mapping):
                continue
            routes = set(unit.get("proposed_routes", []))
            prohibited = sorted(routes & forbidden_promotions)
            if prohibited and unit.get("self_promoted") is True:
                findings.append(
                    ValidationFinding(
                        code="SGD-SELF-PROMOTION-FORBIDDEN",
                        severity="error",
                        message=(
                            "Producing role cannot self-promote to: "
                            + ", ".join(prohibited)
                        ),
                        location=(
                            f"$.generated_data_units[{index}]"
                        ),
                    )
                )
        return findings
    def _build_validator(
        self,
        schema: Mapping[str, Any],
    ) -> Draft202012Validator:
        resolver = RefResolver.from_schema(
            schema,
            store=self.schema_store,
        )
        return Draft202012Validator(
            schema,
            resolver=resolver,
        )
    @staticmethod
    def _load_schema_store(
        schemas_dir: Path,
    ) -> dict[str, Mapping[str, Any]]:
        store: dict[str, Mapping[str, Any]] = {}
        for path in schemas_dir.glob("*.json"):
            schema = PacketValidator._load_json(path)
            store[path.name] = schema
            store[path.as_uri()] = schema
            schema_id = schema.get("$id")
            if isinstance(schema_id, str):
                store[schema_id] = schema
        return store
    @staticmethod
    def _load_data(path: str | Path) -> Any:
        source = Path(path)
        suffix = source.suffix.lower()
        with source.open("r", encoding="utf-8") as handle:
            if suffix == ".json":
                return json.load(handle)
            if suffix in {".yaml", ".yml"}:
                return yaml.safe_load(handle)
        raise ValueError(
            f"Unsupported packet file type: {source}"
        )
    @staticmethod
    def _load_json(path: str | Path) -> Any:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    @staticmethod
    def _load_yaml(path: str | Path) -> Any:
        with Path(path).open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    @staticmethod
    def _packet_role(
        packet: Mapping[str, Any],
    ) -> str | None:
        identity = packet.get("identity")
        if not isinstance(identity, Mapping):
            return None
        return PacketValidator._optional_string(
            identity.get("role")
        )
    @staticmethod
    def _optional_string(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None
    @staticmethod
    def _sha256_json(value: Mapping[str, Any]) -> str:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate an L9 subagent-generated data packet."
    )
    parser.add_argument(
        "packet",
        nargs="?",
        help="JSON or YAML packet to validate.",
    )
    parser.add_argument(
        "--schemas-dir",
        default=str(SCHEMAS_DIR),
    )
    parser.add_argument(
        "--roles-dir",
        default=str(ROLES_DIR),
    )
    parser.add_argument(
        "--validate-contracts",
        action="store_true",
        help="Validate the full Wave 1 schema set.",
    )
    args = parser.parse_args()
    validator = PacketValidator(
        schemas_dir=args.schemas_dir,
        roles_dir=args.roles_dir,
    )
    if args.validate_contracts:
        findings = validator.validate_schema_set()
        payload = {
            "valid": not any(
                item.severity == "error"
                for item in findings
            ),
            "findings": [
                item.to_dict() for item in findings
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["valid"] else 1
    if not args.packet:
        parser.error(
            "packet is required unless --validate-contracts is used"
        )
    report = validator.validate_file(args.packet)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.valid else 1
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$RUNTIME/classifier.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "classifier.py requires the 'PyYAML' package"
    ) from exc
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
            raise ClassificationFailure(
                f"Unsupported primary_class: {primary_class!r}"
            )
        if epistemic_status not in EPISTEMIC_STATUSES:
            raise ClassificationFailure(
                f"Unsupported epistemic_status: "
                f"{epistemic_status!r}"
            )
        authority_sensitivity = self._authority_sensitivity(
            primary_class
        )
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
            sorted(
                {
                    str(route).strip()
                    for route in proposed
                    if str(route).strip()
                }
            )
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
            raise ClassificationFailure(
                "generated_data_units must be a list"
            )
        return [
            self.classify(unit)
            for unit in units
            if isinstance(unit, Mapping)
        ]
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
                if isinstance(item, Mapping)
                and item.get("source_id")
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
            raise ClassificationFailure(
                f"{field_name!r} must be a non-empty string"
            )
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
    parser = argparse.ArgumentParser(
        description="Classify generated data units deterministically."
    )
    parser.add_argument("packet")
    args = parser.parse_args()
    packet = load_data(args.packet)
    if not isinstance(packet, Mapping):
        raise SystemExit("Packet root must be an object")
    classifications = GeneratedDataClassifier().classify_packet(
        packet
    )
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
PY
cat > "$RUNTIME/harvester.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "harvester.py requires the 'PyYAML' package"
    ) from exc
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
            "harvested_units": [
                unit.to_dict() for unit in self.harvested_units
            ],
            "duplicate_unit_ids": list(
                self.duplicate_unit_ids
            ),
            "rejected_units": [
                dict(item) for item in self.rejected_units
            ],
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
        self.classifier = (
            classifier or GeneratedDataClassifier()
        )
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
            raise HarvestFailure(
                "generated_data_units must be a list"
            )
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
                primary_class=str(
                    unit.get("primary_class", "")
                ),
                normalized_statement=normalized,
                repository=repository,
                scope=unit.get("scope"),
            )
            if semantic_key in seen_semantic_keys:
                duplicates.append(unit_id)
                continue
            seen_semantic_keys.add(semantic_key)
            classification = self.classifier.classify(
                unit
            ).to_dict()
            harvested.append(
                HarvestedUnit(
                    unit_id=unit_id,
                    source_packet_id=packet_id,
                    source_action_id=source_action_id,
                    source_agent_id=source_agent_id,
                    source_role=source_role,
                    repository=repository,
                    base_sha=base_sha,
                    statement_hash=self._sha256_text(
                        normalized
                    ),
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
        return hashlib.sha256(
            value.encode("utf-8")
        ).hexdigest()
    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise HarvestFailure(
                f"{field_name!r} must be a non-empty string"
            )
        return raw.strip()
    @staticmethod
    def _required_mapping(
        value: Mapping[str, Any],
        field_name: str,
    ) -> Mapping[str, Any]:
        raw = value.get(field_name)
        if not isinstance(raw, Mapping):
            raise HarvestFailure(
                f"{field_name!r} must be an object"
            )
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
    parser = argparse.ArgumentParser(
        description="Harvest validated subagent-generated data."
    )
    parser.add_argument("packet")
    parser.add_argument("--output")
    args = parser.parse_args()
    packet = load_data(args.packet)
    if not isinstance(packet, Mapping):
        raise SystemExit("Packet root must be an object")
    result = SubagentDataHarvester().harvest(
        packet
    ).to_dict()
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
PY
cat > "$RUNTIME/routing_engine.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
try:
    import yaml
except ImportError as exc:
    raise RuntimeError(
        "routing_engine.py requires the 'PyYAML' package"
    ) from exc
RUNTIME_DIR = Path(__file__).resolve().parent
BASE_DIR = RUNTIME_DIR.parent
ROUTES_DIR = BASE_DIR / "routes"
class RoutingFailure(ValueError):
    """Raised when no safe routing decision can be produced."""
@dataclass(frozen=True)
class RoutingDecision:
    decision_id: str
    unit_id: str
    route: str
    destination: str
    status: str
    reason_codes: tuple[str, ...]
    required_authority: str
    requires_independent_validation: bool
    decision_hash: str
    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "unit_id": self.unit_id,
            "route": self.route,
            "destination": self.destination,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "required_authority": self.required_authority,
            "requires_independent_validation": (
                self.requires_independent_validation
            ),
            "decision_hash": self.decision_hash,
        }
class RoutingEngine:
    """Route harvested generated-data units using declarative route files."""
    def __init__(
        self,
        *,
        routes_dir: str | Path = ROUTES_DIR,
    ) -> None:
        self.routes_dir = Path(routes_dir)
        self.routes = self._load_routes(self.routes_dir)
    def route(
        self,
        harvested_unit: Mapping[str, Any],
    ) -> list[RoutingDecision]:
        original = harvested_unit.get("original_unit")
        classification = harvested_unit.get("classification")
        if not isinstance(original, Mapping):
            raise RoutingFailure(
                "harvested_unit.original_unit must be an object"
            )
        if not isinstance(classification, Mapping):
            raise RoutingFailure(
                "harvested_unit.classification must be an object"
            )
        unit_id = self._required_string(
            harvested_unit,
            "unit_id",
        )
        primary_class = self._required_string(
            classification,
            "primary_class",
        )
        epistemic_status = self._required_string(
            classification,
            "epistemic_status",
        )
        risk = self._required_string(
            classification,
            "risk_of_incorrect_reuse",
        )
        requested_routes = classification.get(
            "normalized_routes",
            [],
        )
        if not isinstance(requested_routes, list):
            requested_routes = list(requested_routes)
        decisions: list[RoutingDecision] = []
        for route_name in requested_routes:
            route_name = str(route_name)
            route = self.routes.get(route_name)
            if route is None:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination="none",
                        status="rejected",
                        reason_codes=(
                            "route_not_registered",
                        ),
                        required_authority="none",
                        requires_independent_validation=False,
                    )
                )
                continue
            accepted_classes = set(
                route.get(
                    "accepted_primary_classes",
                    [],
                )
            )
            if primary_class not in accepted_classes:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(
                            route["destination"]
                        ),
                        status="rejected",
                        reason_codes=(
                            "class_not_accepted_by_route",
                        ),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=bool(
                            route.get(
                                "independent_validation_required",
                                False,
                            )
                        ),
                    )
                )
                continue
            forbidden_statuses = set(
                route.get(
                    "forbidden_epistemic_statuses",
                    [],
                )
            )
            if epistemic_status in forbidden_statuses:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(
                            route["destination"]
                        ),
                        status="deferred",
                        reason_codes=(
                            "epistemic_status_not_promotable",
                        ),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=True,
                    )
                )
                continue
            allowed_risks = set(
                route.get(
                    "allowed_risk_levels",
                    ["low", "medium"],
                )
            )
            if risk not in allowed_risks:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(
                            route["destination"]
                        ),
                        status="deferred",
                        reason_codes=(
                            "risk_exceeds_route_threshold",
                        ),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=True,
                    )
                )
                continue
            required_fields = route.get(
                "required_unit_fields",
                [],
            )
            missing = [
                field_name
                for field_name in required_fields
                if not original.get(field_name)
            ]
            if missing:
                decisions.append(
                    self._decision(
                        unit_id=unit_id,
                        route=route_name,
                        destination=str(
                            route["destination"]
                        ),
                        status="deferred",
                        reason_codes=tuple(
                            f"missing_{field_name}"
                            for field_name in missing
                        ),
                        required_authority=str(
                            route.get(
                                "promotion_authority",
                                "runtime",
                            )
                        ),
                        requires_independent_validation=bool(
                            route.get(
                                "independent_validation_required",
                                False,
                            )
                        ),
                    )
                )
                continue
            decisions.append(
                self._decision(
                    unit_id=unit_id,
                    route=route_name,
                    destination=str(
                        route["destination"]
                    ),
                    status="eligible",
                    reason_codes=(
                        "class_accepted",
                        "epistemic_status_accepted",
                        "risk_accepted",
                        "required_fields_present",
                    ),
                    required_authority=str(
                        route.get(
                            "promotion_authority",
                            "runtime",
                        )
                    ),
                    requires_independent_validation=bool(
                        route.get(
                            "independent_validation_required",
                            False,
                        )
                    ),
                )
            )
        if not decisions:
            decisions.append(
                self._decision(
                    unit_id=unit_id,
                    route="reject",
                    destination="evidence_archive",
                    status="rejected",
                    reason_codes=(
                        "no_route_requested",
                    ),
                    required_authority="runtime",
                    requires_independent_validation=False,
                )
            )
        return decisions
    def route_many(
        self,
        harvested_units: Iterable[Mapping[str, Any]],
    ) -> list[RoutingDecision]:
        decisions: list[RoutingDecision] = []
        for unit in harvested_units:
            decisions.extend(self.route(unit))
        return decisions
    def validate_routes(self) -> list[str]:
        errors: list[str] = []
        required_fields = {
            "route_id",
            "schema_version",
            "destination",
            "accepted_primary_classes",
            "forbidden_epistemic_statuses",
            "allowed_risk_levels",
            "required_unit_fields",
            "promotion_authority",
            "independent_validation_required",
        }
        for route_name, route in self.routes.items():
            missing = sorted(
                required_fields - set(route)
            )
            if missing:
                errors.append(
                    f"{route_name}: missing fields "
                    + ", ".join(missing)
                )
            if route.get("route_id") != route_name:
                errors.append(
                    f"{route_name}: route_id must equal filename stem"
                )
        return errors
    @staticmethod
    def _decision(
        *,
        unit_id: str,
        route: str,
        destination: str,
        status: str,
        reason_codes: tuple[str, ...],
        required_authority: str,
        requires_independent_validation: bool,
    ) -> RoutingDecision:
        payload = {
            "unit_id": unit_id,
            "route": route,
            "destination": destination,
            "status": status,
            "reason_codes": list(reason_codes),
            "required_authority": required_authority,
            "requires_independent_validation": (
                requires_independent_validation
            ),
        }
        decision_hash = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return RoutingDecision(
            decision_id=f"route-{decision_hash[:20]}",
            unit_id=unit_id,
            route=route,
            destination=destination,
            status=status,
            reason_codes=reason_codes,
            required_authority=required_authority,
            requires_independent_validation=(
                requires_independent_validation
            ),
            decision_hash=decision_hash,
        )
    @staticmethod
    def _load_routes(
        routes_dir: Path,
    ) -> dict[str, Mapping[str, Any]]:
        routes: dict[str, Mapping[str, Any]] = {}
        for path in sorted(routes_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle)
            if not isinstance(payload, Mapping):
                raise RoutingFailure(
                    f"Route file must contain an object: {path}"
                )
            routes[path.stem] = payload
        return routes
    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise RoutingFailure(
                f"{field_name!r} must be a non-empty string"
            )
        return raw.strip()
def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Route harvested generated-data units."
    )
    parser.add_argument("harvest_result", nargs="?")
    parser.add_argument(
        "--routes-dir",
        default=str(ROUTES_DIR),
    )
    parser.add_argument(
        "--validate-routes",
        action="store_true",
    )
    args = parser.parse_args()
    engine = RoutingEngine(
        routes_dir=args.routes_dir,
    )
    if args.validate_routes:
        errors = engine.validate_routes()
        print(
            json.dumps(
                {
                    "valid": not errors,
                    "errors": errors,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if not errors else 1
    if not args.harvest_result:
        parser.error(
            "harvest_result is required unless "
            "--validate-routes is used"
        )
    payload = load_json(args.harvest_result)
    units = payload.get("harvested_units", [])
    decisions = engine.route_many(units)
    print(
        json.dumps(
            [decision.to_dict() for decision in decisions],
            indent=2,
            sort_keys=True,
        )
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$RUNTIME/promotion_gate.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
class PromotionFailure(ValueError):
    """Raised when a promotion result cannot be determined safely."""
@dataclass(frozen=True)
class PromotionResult:
    promotion_id: str
    unit_id: str
    route: str
    decision: str
    risk_class: str
    authority_required: str
    reasons: tuple[str, ...]
    conditions: tuple[str, ...]
    promotion_hash: str
    def to_dict(self) -> dict[str, Any]:
        return {
            "promotion_id": self.promotion_id,
            "unit_id": self.unit_id,
            "route": self.route,
            "decision": self.decision,
            "risk_class": self.risk_class,
            "authority_required": self.authority_required,
            "reasons": list(self.reasons),
            "conditions": list(self.conditions),
            "promotion_hash": self.promotion_hash,
        }
class PromotionGate:
    """Apply L9 promotion-risk rules to routing decisions."""
    HIGH_RISK_ROUTES = {
        "architecture",
    }
    MEDIUM_RISK_ROUTES = {
        "contracts",
        "validation",
        "patterns",
        "memory",
    }
    LOW_RISK_ROUTES = {
        "opportunities",
        "evidence",
    }
    def evaluate(
        self,
        *,
        harvested_unit: Mapping[str, Any],
        routing_decision: Mapping[str, Any],
        independent_validation_present: bool = False,
        designated_authority_approval: bool = False,
        recurrence_count: int = 1,
    ) -> PromotionResult:
        unit_id = self._required_string(
            harvested_unit,
            "unit_id",
        )
        route = self._required_string(
            routing_decision,
            "route",
        )
        route_status = self._required_string(
            routing_decision,
            "status",
        )
        classification = harvested_unit.get(
            "classification",
        )
        original = harvested_unit.get("original_unit")
        if not isinstance(classification, Mapping):
            raise PromotionFailure(
                "classification must be an object"
            )
        if not isinstance(original, Mapping):
            raise PromotionFailure(
                "original_unit must be an object"
            )
        confidence = self._confidence(original)
        epistemic_status = str(
            classification.get(
                "epistemic_status",
                "",
            )
        )
        reuse_risk = str(
            classification.get(
                "risk_of_incorrect_reuse",
                "critical",
            )
        )
        authority_sensitivity = str(
            classification.get(
                "authority_sensitivity",
                "high",
            )
        )
        risk_class = self._risk_class(
            route=route,
            authority_sensitivity=authority_sensitivity,
            reuse_risk=reuse_risk,
        )
        reasons: list[str] = []
        conditions: list[str] = []
        if route_status == "rejected":
            return self._result(
                unit_id=unit_id,
                route=route,
                decision="reject",
                risk_class=risk_class,
                authority_required="none",
                reasons=("routing_rejected",),
                conditions=(),
            )
        if route_status == "deferred":
            return self._result(
                unit_id=unit_id,
                route=route,
                decision="defer",
                risk_class=risk_class,
                authority_required=str(
                    routing_decision.get(
                        "required_authority",
                        "runtime",
                    )
                ),
                reasons=("routing_deferred",),
                conditions=tuple(
                    routing_decision.get(
                        "reason_codes",
                        [],
                    )
                ),
            )
        if epistemic_status in {
            "hypothesized",
            "contested",
            "unresolved",
        }:
            reasons.append(
                "epistemic_status_not_promotable"
            )
            conditions.append(
                "resolve_or_reclassify_epistemic_status"
            )
        if confidence < 0.5:
            reasons.append("confidence_below_minimum")
            conditions.append("collect_stronger_evidence")
        if risk_class == "high":
            if not independent_validation_present:
                conditions.append(
                    "independent_validation_required"
                )
            if not designated_authority_approval:
                conditions.append(
                    "designated_authority_approval_required"
                )
            if conditions:
                reasons.append(
                    "high_risk_promotion_controls_missing"
                )
                return self._result(
                    unit_id=unit_id,
                    route=route,
                    decision="defer",
                    risk_class=risk_class,
                    authority_required="designated_authority",
                    reasons=tuple(sorted(set(reasons))),
                    conditions=tuple(
                        sorted(set(conditions))
                    ),
                )
        if risk_class == "medium":
            if (
                not independent_validation_present
                and recurrence_count < 2
            ):
                return self._result(
                    unit_id=unit_id,
                    route=route,
                    decision="defer",
                    risk_class=risk_class,
                    authority_required=(
                        "independent_validator_or_recurrence"
                    ),
                    reasons=(
                        "medium_risk_requires_validation_or_recurrence",
                    ),
                    conditions=(
                        "provide_independent_validation",
                        "or_observe_second_confirming_occurrence",
                    ),
                )
        if confidence < 0.75 and route != "evidence":
            return self._result(
                unit_id=unit_id,
                route=route,
                decision="retain",
                risk_class=risk_class,
                authority_required="runtime",
                reasons=("confidence_supports_evidence_only",),
                conditions=("reassess_after_additional_evidence",),
            )
        return self._result(
            unit_id=unit_id,
            route=route,
            decision="promote",
            risk_class=risk_class,
            authority_required=str(
                routing_decision.get(
                    "required_authority",
                    "runtime",
                )
            ),
            reasons=(
                "routing_eligible",
                "promotion_controls_satisfied",
            ),
            conditions=(),
        )
    def evaluate_many(
        self,
        *,
        harvested_units: list[Mapping[str, Any]],
        routing_decisions: list[Mapping[str, Any]],
        independent_validation_present: bool = False,
        designated_authority_approval: bool = False,
        recurrence_counts: Mapping[str, int] | None = None,
    ) -> list[PromotionResult]:
        by_unit = {
            str(unit["unit_id"]): unit
            for unit in harvested_units
        }
        recurrence_counts = recurrence_counts or {}
        results: list[PromotionResult] = []
        for decision in routing_decisions:
            unit_id = str(decision["unit_id"])
            unit = by_unit.get(unit_id)
            if unit is None:
                raise PromotionFailure(
                    f"Routing decision references unknown unit "
                    f"{unit_id!r}"
                )
            results.append(
                self.evaluate(
                    harvested_unit=unit,
                    routing_decision=decision,
                    independent_validation_present=(
                        independent_validation_present
                    ),
                    designated_authority_approval=(
                        designated_authority_approval
                    ),
                    recurrence_count=int(
                        recurrence_counts.get(
                            unit_id,
                            1,
                        )
                    ),
                )
            )
        return results
    def _risk_class(
        self,
        *,
        route: str,
        authority_sensitivity: str,
        reuse_risk: str,
    ) -> str:
        if (
            route in self.HIGH_RISK_ROUTES
            or authority_sensitivity == "high"
            or reuse_risk in {"high", "critical"}
        ):
            return "high"
        if (
            route in self.MEDIUM_RISK_ROUTES
            or authority_sensitivity == "medium"
            or reuse_risk == "medium"
        ):
            return "medium"
        return "low"
    @staticmethod
    def _confidence(
        original: Mapping[str, Any],
    ) -> float:
        try:
            value = float(original.get("confidence", 0))
        except (TypeError, ValueError):
            value = 0.0
        return max(0.0, min(1.0, value))
    @staticmethod
    def _result(
        *,
        unit_id: str,
        route: str,
        decision: str,
        risk_class: str,
        authority_required: str,
        reasons: tuple[str, ...],
        conditions: tuple[str, ...],
    ) -> PromotionResult:
        payload = {
            "unit_id": unit_id,
            "route": route,
            "decision": decision,
            "risk_class": risk_class,
            "authority_required": authority_required,
            "reasons": list(reasons),
            "conditions": list(conditions),
        }
        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return PromotionResult(
            promotion_id=f"promotion-{digest[:20]}",
            unit_id=unit_id,
            route=route,
            decision=decision,
            risk_class=risk_class,
            authority_required=authority_required,
            reasons=reasons,
            conditions=conditions,
            promotion_hash=digest,
        )
    @staticmethod
    def _required_string(
        value: Mapping[str, Any],
        field_name: str,
    ) -> str:
        raw = value.get(field_name)
        if not isinstance(raw, str) or not raw.strip():
            raise PromotionFailure(
                f"{field_name!r} must be a non-empty string"
            )
        return raw.strip()
def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply promotion gates to routing decisions."
    )
    parser.add_argument("--harvest", required=True)
    parser.add_argument("--routes", required=True)
    parser.add_argument(
        "--independent-validation",
        action="store_true",
    )
    parser.add_argument(
        "--authority-approved",
        action="store_true",
    )
    args = parser.parse_args()
    harvest = load_json(args.harvest)
    routes = load_json(args.routes)
    results = PromotionGate().evaluate_many(
        harvested_units=harvest.get(
            "harvested_units",
            [],
        ),
        routing_decisions=routes,
        independent_validation_present=(
            args.independent_validation
        ),
        designated_authority_approval=(
            args.authority_approved
        ),
    )
    print(
        json.dumps(
            [result.to_dict() for result in results],
            indent=2,
            sort_keys=True,
        )
    )
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$RUNTIME/learning_closure.py" <<'PY'
from __future__ import annotations
import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
class LearningClosureFailure(ValueError):
    """Raised when a closure report cannot be computed."""
@dataclass(frozen=True)
class ClosureCheck:
    check_id: str
    passed: bool
    blocking: bool
    message: str
    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "passed": self.passed,
            "blocking": self.blocking,
            "message": self.message,
        }
@dataclass(frozen=True)
class LearningClosureResult:
    closure_id: str
    campaign_id: str
    status: str
    checks: tuple[ClosureCheck, ...]
    unresolved_high_value_units: tuple[str, ...]
    unresolved_unknown_ids: tuple[str, ...]
    closure_hash: str
    def to_dict(self) -> dict[str, Any]:
        return {
            "closure_id": self.closure_id,
            "campaign_id": self.campaign_id,
            "status": self.status,
            "checks": [
                check.to_dict() for check in self.checks
            ],
            "unresolved_high_value_units": list(
                self.unresolved_high_value_units
            ),
            "unresolved_unknown_ids": list(
                self.unresolved_unknown_ids
            ),
            "closure_hash": self.closure_hash,
        }
class LearningClosureEvaluator:
    """Determine whether a campaign may seal its learning lifecycle."""
    def evaluate(
        self,
        *,
        campaign_id: str,
        expected_action_ids: Iterable[str],
        packets: Iterable[Mapping[str, Any]],
        validation_reports: Iterable[Mapping[str, Any]],
        harvest_results: Iterable[Mapping[str, Any]],
        routing_decisions: Iterable[Mapping[str, Any]],
        promotion_results: Iterable[Mapping[str, Any]],
        evidence_archive_complete: bool,
    ) -> LearningClosureResult:
        expected_actions = set(expected_action_ids)
        packet_list = list(packets)
        validation_list = list(validation_reports)
        harvest_list = list(harvest_results)
        route_list = list(routing_decisions)
        promotion_list = list(promotion_results)
        packet_actions = {
            str(packet.get("identity", {}).get("action_id"))
            for packet in packet_list
            if isinstance(packet.get("identity"), Mapping)
        }
        missing_actions = sorted(
            expected_actions - packet_actions
        )
        packet_ids = {
            str(packet.get("packet_id"))
            for packet in packet_list
            if packet.get("packet_id")
        }
        valid_packet_ids = {
            str(report.get("packet_id"))
            for report in validation_list
            if report.get("valid") is True
        }
        invalid_or_unvalidated = sorted(
            packet_ids - valid_packet_ids
        )
        harvested_unit_ids: set[str] = set()
        rejected_units_have_reasons = True
        for result in harvest_list:
            for unit in result.get(
                "harvested_units",
                [],
            ):
                if isinstance(unit, Mapping) and unit.get(
                    "unit_id"
                ):
                    harvested_unit_ids.add(
                        str(unit["unit_id"])
                    )
            for rejected in result.get(
                "rejected_units",
                [],
            ):
                if not isinstance(rejected, Mapping):
                    rejected_units_have_reasons = False
                elif not rejected.get("reason"):
                    rejected_units_have_reasons = False
        routed_unit_ids = {
            str(decision.get("unit_id"))
            for decision in route_list
            if decision.get("unit_id")
        }
        unrouted_units = sorted(
            harvested_unit_ids - routed_unit_ids
        )
        promoted_unit_ids = {
            str(result.get("unit_id"))
            for result in promotion_list
            if result.get("unit_id")
        }
        units_without_promotion_decision = sorted(
            routed_unit_ids - promoted_unit_ids
        )
        high_value_unresolved: set[str] = set()
        for result in promotion_list:
            if not isinstance(result, Mapping):
                continue
            if (
                result.get("risk_class")
                in {"medium", "high"}
                and result.get("decision") == "defer"
            ):
                high_value_unresolved.add(
                    str(result.get("unit_id"))
                )
        unresolved_unknown_ids: set[str] = set()
        for packet in packet_list:
            unknowns = packet.get(
                "unresolved_unknowns",
                [],
            )
            if not isinstance(unknowns, list):
                continue
            for unknown in unknowns:
                if not isinstance(unknown, Mapping):
                    continue
                if not unknown.get("owner") or not unknown.get(
                    "next_action"
                ):
                    unresolved_unknown_ids.add(
                        str(
                            unknown.get(
                                "unknown_id",
                                "unknown",
                            )
                        )
                    )
        checks = (
            ClosureCheck(
                check_id="SGD-CLOSE-001",
                passed=not missing_actions,
                blocking=True,
                message=(
                    "All required subagent packets received"
                    if not missing_actions
                    else (
                        "Missing packets for actions: "
                        + ", ".join(missing_actions)
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-002",
                passed=not invalid_or_unvalidated,
                blocking=True,
                message=(
                    "All packets validated"
                    if not invalid_or_unvalidated
                    else (
                        "Invalid or unvalidated packets: "
                        + ", ".join(invalid_or_unvalidated)
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-003",
                passed=not unrouted_units,
                blocking=True,
                message=(
                    "All harvested units routed"
                    if not unrouted_units
                    else (
                        "Unrouted units: "
                        + ", ".join(unrouted_units)
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-004",
                passed=not units_without_promotion_decision,
                blocking=True,
                message=(
                    "All routed units have promotion decisions"
                    if not units_without_promotion_decision
                    else (
                        "Units missing promotion decisions: "
                        + ", ".join(
                            units_without_promotion_decision
                        )
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-005",
                passed=not unresolved_unknown_ids,
                blocking=True,
                message=(
                    "All unresolved unknowns have owners and next actions"
                    if not unresolved_unknown_ids
                    else (
                        "Unowned unresolved unknowns: "
                        + ", ".join(
                            sorted(unresolved_unknown_ids)
                        )
                    )
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-006",
                passed=rejected_units_have_reasons,
                blocking=True,
                message=(
                    "All rejected units have reasons"
                    if rejected_units_have_reasons
                    else "One or more rejected units lack a reason"
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-007",
                passed=evidence_archive_complete,
                blocking=True,
                message=(
                    "Evidence archive is complete"
                    if evidence_archive_complete
                    else "Evidence archive is incomplete"
                ),
            ),
            ClosureCheck(
                check_id="SGD-CLOSE-008",
                passed=not high_value_unresolved,
                blocking=True,
                message=(
                    "No high-value promotion decision remains unresolved"
                    if not high_value_unresolved
                    else (
                        "Deferred high-value units require resolution: "
                        + ", ".join(
                            sorted(high_value_unresolved)
                        )
                    )
                ),
            ),
        )
        status = (
            "closed"
            if all(
                check.passed or not check.blocking
                for check in checks
            )
            else "blocked"
        )
        payload = {
            "campaign_id": campaign_id,
            "status": status,
            "checks": [
                check.to_dict() for check in checks
            ],
            "unresolved_high_value_units": sorted(
                high_value_unresolved
            ),
            "unresolved_unknown_ids": sorted(
                unresolved_unknown_ids
            ),
        }
        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        return LearningClosureResult(
            closure_id=f"closure-{digest[:20]}",
            campaign_id=campaign_id,
            status=status,
            checks=checks,
            unresolved_high_value_units=tuple(
                sorted(high_value_unresolved)
            ),
            unresolved_unknown_ids=tuple(
                sorted(unresolved_unknown_ids)
            ),
            closure_hash=digest,
        )
def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate campaign learning closure."
    )
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--expected-actions", required=True)
    parser.add_argument("--packets", required=True)
    parser.add_argument("--validation-reports", required=True)
    parser.add_argument("--harvest-results", required=True)
    parser.add_argument("--routing-decisions", required=True)
    parser.add_argument("--promotion-results", required=True)
    parser.add_argument(
        "--evidence-archive-complete",
        action="store_true",
    )
    args = parser.parse_args()
    result = LearningClosureEvaluator().evaluate(
        campaign_id=args.campaign_id,
        expected_action_ids=load_json(
            args.expected_actions
        ),
        packets=load_json(args.packets),
        validation_reports=load_json(
            args.validation_reports
        ),
        harvest_results=load_json(
            args.harvest_results
        ),
        routing_decisions=load_json(
            args.routing_decisions
        ),
        promotion_results=load_json(
            args.promotion_results
        ),
        evidence_archive_complete=(
            args.evidence_archive_complete
        ),
    )
    print(
        json.dumps(
            result.to_dict(),
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.status == "closed" else 1
if __name__ == "__main__":
    raise SystemExit(main())
PY
cat > "$ROUTES/memory.yaml" <<'YAML'
route_id: memory
schema_version: "1.0.0"
description: >
  Route validated, advisory, reusable knowledge to the governed memory
  candidate interface. Memory remains subordinate to current repository state,
  canonical law, active policy, and current task contracts.
destination: graphiti_memory_candidate_queue
accepted_primary_classes:
  - repository_fact
  - dependency_finding
  - implementation_surface
  - rejected_approach
  - context_requirement
  - artifact_lineage
forbidden_epistemic_statuses:
  - hypothesized
  - contested
  - unresolved
allowed_risk_levels:
  - low
  - medium
required_unit_fields:
  - unit_id
  - statement
  - source_evidence
  - scope
  - confidence
  - freshness
  - invalidation_conditions
promotion_authority: memory_admission_runtime
independent_validation_required: false
self_promotion_allowed: false
default_visibility: repository_local
output_contract:
  kind: MemoryCandidate
  authority_class: advisory
  preserve_provenance: true
  preserve_epistemic_status: true
  preserve_invalidation_conditions: true
reject_when:
  - current_repository_state_contradicts_unit
  - canonical_authority_conflicts
  - scope_is_undefined
  - provenance_is_missing
  - unit_is_duplicate_without_new_evidence
YAML
cat > "$ROUTES/contracts.yaml" <<'YAML'
route_id: contracts
schema_version: "1.0.0"
description: >
  Route generated data that can improve future task inputs, outputs,
  boundaries, stop conditions, context requirements, or evidence obligations.
destination: task_contract_delta_queue
accepted_primary_classes:
  - implementation_surface
  - context_requirement
  - context_waste
  - task_contract_gap
forbidden_epistemic_statuses:
  - contested
  - unresolved
allowed_risk_levels:
  - low
  - medium
required_unit_fields:
  - unit_id
  - statement
  - source_evidence
  - scope
  - confidence
  - expected_reuse
  - invalidation_conditions
promotion_authority: task_contract_compiler
independent_validation_required: true
self_promotion_allowed: false
default_visibility: constellation_internal
output_contract:
  kind: TaskContractDeltaCandidate
  preserve_source_contract: true
  require_behavioral_change: true
  require_rollback_or_rejection_path: true
reject_when:
  - proposed_delta_only_rephrases_existing_contract
  - no_future_behavior_change_is_identified
  - destination_contract_owner_is_unknown
  - unit_conflicts_with_higher_authority
YAML
cat > "$ROUTES/validation.yaml" <<'YAML'
route_id: validation
schema_version: "1.0.0"
description: >
  Route findings that can become tests, invariants, CI checks, evidence
  requirements, regression guards, or validation procedures.
destination: validation_candidate_queue
accepted_primary_classes:
  - validation_procedure
  - failure_pattern
  - invariant_candidate
  - regression_candidate
forbidden_epistemic_statuses:
  - hypothesized
  - unresolved
allowed_risk_levels:
  - low
  - medium
  - high
required_unit_fields:
  - unit_id
  - statement
  - source_evidence
  - scope
  - confidence
  - expected_reuse
  - invalidation_conditions
promotion_authority: validation_compiler
independent_validation_required: true
self_promotion_allowed: false
default_visibility: repository_local
output_contract:
  kind: ValidationCandidate
  require_reproduction_path: true
  require_expected_failure_or_pass_condition: true
  require_evidence_binding: true
reject_when:
  - validation_method_is_known_false_green
  - reproduction_path_is_missing
  - claim_cannot_be_measured
  - test_would_only_assert_implementation_details_without_contract_value
YAML
cat > "$ROUTES/patterns.yaml" <<'YAML'
route_id: patterns
schema_version: "1.0.0"
description: >
  Route repeatable execution, inspection, validation, remediation, and
  decomposition procedures into the reusable pattern candidate registry.
destination: reusable_pattern_candidate_queue
accepted_primary_classes:
  - execution_procedure
  - validation_procedure
  - failure_pattern
  - rejected_approach
  - reusable_pattern_candidate
forbidden_epistemic_statuses:
  - hypothesized
  - contested
  - unresolved
allowed_risk_levels:
  - low
  - medium
required_unit_fields:
  - unit_id
  - statement
  - source_evidence
  - scope
  - confidence
  - expected_reuse
  - invalidation_conditions
promotion_authority: pattern_compiler
independent_validation_required: true
self_promotion_allowed: false
default_visibility: constellation_internal
output_contract:
  kind: ReusablePatternCandidate
  require_trigger_conditions: true
  require_ordered_procedure: true
  require_validation_method: true
  require_failure_and_stop_conditions: true
reject_when:
  - procedure_is_task_specific_without_reuse
  - repeated_execution_has_no_measured_delta
  - procedure_duplicates_an_active_pattern
  - procedure_bypasses_policy_or_assurance
YAML
cat > "$ROUTES/architecture.yaml" <<'YAML'
route_id: architecture
schema_version: "1.0.0"
description: >
  Route ownership, responsibility, dependency, and must-not-own findings to
  architecture review. This route never grants canonical architecture authority
  automatically.
destination: architecture_candidate_queue
accepted_primary_classes:
  - architecture_boundary
  - ownership_finding
  - dependency_finding
  - policy_candidate
forbidden_epistemic_statuses:
  - hypothesized
  - contested
  - unresolved
allowed_risk_levels:
  - low
  - medium
  - high
  - critical
required_unit_fields:
  - unit_id
  - statement
  - source_evidence
  - scope
  - confidence
  - expected_reuse
  - invalidation_conditions
promotion_authority: designated_architecture_authority
independent_validation_required: true
self_promotion_allowed: false
default_visibility: constellation_internal
output_contract:
  kind: ArchitectureCandidate
  canonical_on_submission: false
  require_owner_of_truth_check: true
  require_conflict_search: true
  require_human_or_designated_authority_approval: true
reject_when:
  - claim_blurs_existing_authority
  - canonical_owner_cannot_be_named
  - proposed_boundary_increases_coupling_without_leverage
  - evidence_is_only_naming_or_directory_proximity
YAML
cat > "$ROUTES/opportunities.yaml" <<'YAML'
route_id: opportunities
schema_version: "1.0.0"
description: >
  Route unresolved unknowns and bounded follow-on opportunities into next-action
  planning without treating them as approved work or canonical truth.
destination: opportunity_and_unknown_registry
accepted_primary_classes:
  - unresolved_unknown
  - follow_on_opportunity
forbidden_epistemic_statuses: []
allowed_risk_levels:
  - low
  - medium
  - high
  - critical
required_unit_fields:
  - unit_id
  - statement
  - scope
  - confidence
  - expected_reuse
  - invalidation_conditions
promotion_authority: opportunity_planner
independent_validation_required: false
self_promotion_allowed: false
default_visibility: repository_local
output_contract:
  kind: OpportunityOrUnknownRecord
  authorize_execution: false
  require_owner: true
  require_next_action: true
  require_evidence_path: true
  require_priority_and_risk_scoring_before_execution: true
reject_when:
  - opportunity_is_unbounded
  - no_named_capability_gain_exists
  - no_owner_or_next_action_can_be_defined
  - work_duplicates_an_existing_open_action
YAML
python - <<'PY'
from __future__ import annotations
import ast
import hashlib
import json
import sys
from pathlib import Path
try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "ERROR: PyYAML is required to validate Wave 2"
    ) from exc
try:
    import jsonschema
except ImportError as exc:
    raise SystemExit(
        "ERROR: jsonschema is required to validate Wave 2"
    ) from exc
base = Path("subagent-generated-data")
runtime = base / "runtime"
routes = base / "routes"
python_files = sorted(runtime.glob("*.py"))
yaml_files = sorted(routes.glob("*.yaml"))
errors: list[str] = []
for path in python_files:
    try:
        ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        errors.append(f"{path}: Python syntax error: {exc}")
for path in yaml_files:
    try:
        value = yaml.safe_load(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        errors.append(f"{path}: YAML parse error: {exc}")
        continue
    if not isinstance(value, dict):
        errors.append(f"{path}: root must be a mapping")
expected_routes = {
    "memory",
    "contracts",
    "validation",
    "patterns",
    "architecture",
    "opportunities",
}
observed_routes = {path.stem for path in yaml_files}
missing_routes = sorted(expected_routes - observed_routes)
if missing_routes:
    errors.append(
        "Missing route files: " + ", ".join(missing_routes)
    )
sys.path.insert(0, str(runtime.resolve()))
try:
    from packet_validator import PacketValidator
    from routing_engine import RoutingEngine
    schema_findings = PacketValidator().validate_schema_set()
    errors.extend(
        f"{item.location}: {item.message}"
        for item in schema_findings
        if item.severity == "error"
    )
    route_errors = RoutingEngine().validate_routes()
    errors.extend(route_errors)
except Exception as exc:
    errors.append(f"Runtime import or validation failed: {exc}")
if errors:
    print("WAVE 2 VALIDATION FAILED")
    for error in errors:
        print(f"- {error}")
    raise SystemExit(1)
print("WAVE 2 VALIDATION PASSED")
print()
print("FINAL TREE")
for path in sorted(
    [
        *python_files,
        *yaml_files,
    ]
):
    print(path)
print()
print("SHA-256")
for path in sorted(
    [
        *python_files,
        *yaml_files,
    ]
):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{digest}  {path}")
PY
echo
echo "Wave 2 installation complete."
echo
echo "Created runtime:"
echo "  $RUNTIME/packet_validator.py"
echo "  $RUNTIME/harvester.py"
echo "  $RUNTIME/classifier.py"
echo "  $RUNTIME/routing_engine.py"
echo "  $RUNTIME/promotion_gate.py"
echo "  $RUNTIME/learning_closure.py"
echo
echo "Created routes:"
echo "  $ROUTES/memory.yaml"
echo "  $ROUTES/contracts.yaml"
echo "  $ROUTES/validation.yaml"
echo "  $ROUTES/patterns.yaml"
echo "  $ROUTES/architecture.yaml"
echo "  $ROUTES/opportunities.yaml"
