from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class SchemaRegistry:
    def __init__(self, subsystem_root: str | Path) -> None:
        self.root = Path(subsystem_root).resolve()
        self.conformance = self.root / "conformance" / "schemas"
        self.core = self.root / "core" / "program-execution-controller-template" / "schemas"

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"schema must be an object: {path}")
        return value

    def validate(self, schema_path: Path, value: Mapping[str, Any]) -> list[str]:
        schema = self._load(schema_path)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(dict(value)),
            key=lambda item: list(item.path),
        )
        return [
            f"{'.'.join(str(part) for part in item.path) or '<root>'}: {item.message}"
            for item in errors
        ]

    def validate_adapter_spec(self, value: Mapping[str, Any]) -> list[str]:
        return self.validate(
            self.conformance / "execution-adapter-spec.schema.json",
            value,
        )

    def validate_capability(self, value: Mapping[str, Any]) -> list[str]:
        return self.validate(
            self.conformance / "capability-receipt.schema.json",
            value,
        )

    def validate_lifecycle(self, value: Mapping[str, Any]) -> list[str]:
        return self.validate(
            self.conformance / "lifecycle-receipt.schema.json",
            value,
        )

    def validate_core_receipt(
        self,
        kind: str,
        value: Mapping[str, Any],
    ) -> list[str]:
        mapping = {
            "attempt": "attempt-receipt.schema.json",
            "verification": "verification-receipt.schema.json",
            "handoff": "handoff-receipt.schema.json",
        }
        try:
            name = mapping[kind]
        except KeyError as exc:
            raise ValueError(f"unsupported core receipt kind: {kind}") from exc
        return self.validate(self.core / name, value)

    def validate_terminal_receipt(
        self,
        value: Mapping[str, Any],
    ) -> list[str]:
        schema_id = value.get("schema")
        mapping = {
            "program-execution-controller.attempt-receipt.v2": (
                self.core / "attempt-receipt.schema.json"
            ),
            "program-execution-controller.verification-receipt.v2": (
                self.core / "verification-receipt.schema.json"
            ),
            "program-execution-adapter.remote-action-receipt.v1": (
                self.conformance / "remote-action-receipt.schema.json"
            ),
            "program-execution-adapter.deployment-receipt.v1": (
                self.conformance / "deployment-receipt.schema.json"
            ),
        }
        path = mapping.get(str(schema_id))
        if path is None:
            return [f"unsupported terminal receipt schema: {schema_id}"]
        return self.validate(path, value)
