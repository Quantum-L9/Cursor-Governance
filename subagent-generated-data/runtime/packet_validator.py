from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, RefResolver
    from jsonschema.exceptions import SchemaError
except ImportError as exc:
    raise RuntimeError("packet_validator.py requires the 'jsonschema' package") from exc
try:
    import yaml
except ImportError as exc:
    raise RuntimeError("packet_validator.py requires the 'PyYAML' package") from exc
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
        self.packet_schema = self._load_json(self.schemas_dir / "subagent-data-packet.schema.json")
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
        valid = not any(finding.severity == "error" for finding in findings)
        report = ValidationReport(
            valid=valid,
            packet_id=self._optional_string(packet.get("packet_id")),
            packet_hash=(self._sha256_json(packet) if isinstance(packet, Mapping) else None),
            schema_version=self._optional_string(packet.get("schema_version")),
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
            raise PacketValidationFailure(f"Packet root must be an object: {path}")
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
        # Build a fresh resolver-backed validator per call: the deprecated
        # RefResolver mutates resolution scope while following cross-file $refs
        # and does not restore it across successive validations, so a reused
        # instance fails to resolve local pointers (e.g. "#/$defs/role") on the
        # second packet. A per-call validator keeps resolution deterministic.
        validator = self._build_validator(self.packet_schema)
        for error in sorted(
            validator.iter_errors(packet),
            key=lambda item: list(item.absolute_path),
        ):
            location = "$"
            if error.absolute_path:
                location += "." + ".".join(str(part) for part in error.absolute_path)
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
                        message=("identity.base_sha and provenance.base_sha must match"),
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
                                location=(f"$.generated_data_units[{index}].unit_id"),
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
                            message=(f"{status!r} units require source evidence"),
                            location=(f"$.generated_data_units[{index}].source_evidence"),
                        )
                    )
                proposed_routes = unit.get("proposed_routes", [])
                if isinstance(proposed_routes, list) and not proposed_routes:
                    findings.append(
                        ValidationFinding(
                            code="SGD-ROUTE-REQUIRED",
                            severity="error",
                            message=(
                                "Every generated data unit requires at least one proposed route"
                            ),
                            location=(f"$.generated_data_units[{index}].proposed_routes"),
                        )
                    )
                invalidation = unit.get(
                    "invalidation_conditions",
                    [],
                )
                if unit.get("expected_reuse") and not invalidation:
                    findings.append(
                        ValidationFinding(
                            code="SGD-INVALIDATION-REQUIRED",
                            severity="error",
                            message=("Reusable units require invalidation conditions"),
                            location=(f"$.generated_data_units[{index}].invalidation_conditions"),
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
                                message=(f"Unresolved unknown is missing {field_name!r}"),
                                location=(f"$.unresolved_unknowns[{index}].{field_name}"),
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
        required_classes = set(profile.get("required_generated_data_classes", []))
        units = packet.get("generated_data_units", [])
        present_classes = {
            str(unit.get("primary_class")) for unit in units if isinstance(unit, Mapping)
        }
        missing_classes = sorted(required_classes - present_classes)
        allows_empty = bool(profile.get("allows_empty_generated_data", True))
        if missing_classes and units and not allows_empty:
            findings.append(
                ValidationFinding(
                    code="SGD-ROLE-CLASS-MISSING",
                    severity="error",
                    message=(
                        "Role packet does not include required generated "
                        "data classes: " + ", ".join(missing_classes)
                    ),
                    location="$.generated_data_units",
                )
            )
        forbidden_promotions = set(profile.get("forbidden_self_promotion_targets", []))
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
                        message=("Producing role cannot self-promote to: " + ", ".join(prohibited)),
                        location=(f"$.generated_data_units[{index}]"),
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
        raise ValueError(f"Unsupported packet file type: {source}")

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
        return PacketValidator._optional_string(identity.get("role"))

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
    parser = argparse.ArgumentParser(description="Validate an L9 subagent-generated data packet.")
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
            "valid": not any(item.severity == "error" for item in findings),
            "findings": [item.to_dict() for item in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["valid"] else 1
    if not args.packet:
        parser.error("packet is required unless --validate-contracts is used")
    report = validator.validate_file(args.packet)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
