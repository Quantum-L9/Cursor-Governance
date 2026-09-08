"""Validate memory receipts against the *bound release's own* contract.

Audit CG-P1-02. Cursor used to accept a receipt as authoritative on the
strength of a reduced local parse: each ``receipts.py`` view checked that the
handful of fields it reads were present, and a successful-looking status did
the rest. ``validate_against_contract`` existed beside that path and was never
called by it — a helper is not a gate.

The gap is structural rather than an oversight. In pinned mode the memory
runtime is a *different interpreter*, so ``import l9_graphite_memory.contracts``
cannot succeed in this process however carefully it is written, and a helper
that returns ``False`` when the import fails degrades to structural acceptance
exactly where the binding is strongest.

So the schemas come across the boundary instead: ``runtime_binding`` exports
each canonical receipt model from the bound release as JSON Schema (one probe,
at binding time), and this module validates raw receipts against those. The
authority stays with memory; Cursor's dataclasses are projections of a payload
that has already satisfied memory's own contract.

Layering, in order:

    bound release  ->  canonical schema  ->  canonical validation
                   ->  structural view (receipts.py)  ->  Cursor projection

Cursor may narrow what it requires. It may not weaken it, and it may not
silently proceed when canonical validation is required and unavailable — that
is :class:`ValidationUnavailable`, a non-success condition, never a fallback.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ops.memory.receipts import InvalidReceiptError

#: Turns canonical validation from "run it when the bound release exports
#: schemas" into "refuse the operation when it cannot run". Set by the
#: cross-repo proof and by any caller that needs exactness rather than
#: best effort.
ENV_REQUIRE_VALIDATION = "L9_MEMORY_REQUIRE_CANONICAL_VALIDATION"

VALIDATION_CANONICAL = "canonical"
VALIDATION_UNAVAILABLE = "unavailable"

_TRUE = frozenset({"1", "true", "yes", "on"})


class ValidationUnavailable(RuntimeError):
    """Canonical validation was required and could not be performed.

    Distinct from :class:`InvalidReceiptError` on purpose: the receipt was not
    proved wrong, it was not proved *right*. Collapsing the two would report a
    healthy runtime as emitting bad receipts, and — worse in the other
    direction — invite a fallback that treats "cannot check" as "checked".
    """


def _major(version: str) -> int:
    """Leading integer of a dotted version; unparseable sorts as -1."""

    head = str(version).strip().split(".", 1)[0]
    try:
        return int(head)
    except ValueError:
        return -1


def require_canonical_validation(env: Mapping[str, str] | None = None) -> bool:
    environment = os.environ if env is None else env
    return str(environment.get(ENV_REQUIRE_VALIDATION, "")).strip().lower() in _TRUE


@dataclass(frozen=True)
class CanonicalValidator:
    """Validates raw receipts against schemas exported by the bound release."""

    schemas: Mapping[str, Any] | None
    schema_digest: str | None = None
    schema_source: str | None = None
    required: bool = False
    #: What the bound release declared in its own capabilities receipt. A
    #: receipt that names a different contract lineage is not from the release
    #: this client is bound to, whatever else it satisfies.
    expected_schema_version: str | None = None
    expected_package_version: str | None = None

    @classmethod
    def for_binding(
        cls, binding: Any, *, env: Mapping[str, str] | None = None
    ) -> CanonicalValidator:
        capabilities = getattr(binding, "capabilities", None)
        return cls(
            schemas=getattr(binding, "contract_schemas", None),
            schema_digest=getattr(binding, "schema_digest", None),
            schema_source=getattr(binding, "schema_source", None),
            required=require_canonical_validation(env),
            expected_schema_version=getattr(capabilities, "schema_version", None) or None,
            expected_package_version=getattr(binding, "memory_version", None),
        )

    @property
    def available(self) -> bool:
        return bool(self.schemas)

    def schema_for(self, model_name: str) -> Any | None:
        if not self.schemas:
            return None
        return self.schemas.get(model_name)

    def validate(self, raw: Any, model_name: str) -> str:
        """Validate ``raw`` against the canonical schema for ``model_name``.

        Returns the validation mode actually achieved: ``canonical`` when the
        bound release's schema was applied, ``unavailable`` when it could not
        be and validation was not required.

        Raises :class:`InvalidReceiptError` when the payload violates the
        canonical contract, and :class:`ValidationUnavailable` when validation
        was required but no schema or validator was reachable.
        """

        schema = self.schema_for(model_name)
        if schema is None:
            return self._unavailable(
                f"the bound memory release exports no canonical schema for {model_name}"
            )
        if not isinstance(raw, dict):
            raise InvalidReceiptError(f"{model_name} is not a JSON object")
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - jsonschema is a declared dependency
            return self._unavailable(
                "jsonschema is not importable, so the canonical schema cannot be applied"
            )
        try:
            jsonschema.validate(instance=raw, schema=schema)
        except jsonschema.ValidationError as exc:
            location = "/".join(str(part) for part in exc.absolute_path) or "<root>"
            raise InvalidReceiptError(
                f"{model_name} violates the canonical contract at {location}: {exc.message}"
            ) from exc
        except jsonschema.SchemaError as exc:
            return self._unavailable(f"canonical schema for {model_name} is not usable: {exc}")
        self._check_provenance(raw, model_name)
        return VALIDATION_CANONICAL

    def _check_provenance(self, raw: Mapping[str, Any], model_name: str) -> None:
        """Reject a receipt that is well-formed but from the wrong release.

        Schema conformance proves shape, not origin. Where the receipt itself
        carries provenance — the contract lineage it was written against, the
        package that wrote it — it must agree with the release this client is
        bound to, or the binding proved nothing about the receipt in hand.
        """

        declared = raw.get("schema_version")
        if declared is not None and self.expected_schema_version:
            if str(declared) != self.expected_schema_version:
                expected_major = _major(self.expected_schema_version)
                actual_major = _major(str(declared))
                detail = (
                    "a later major than the bound release declares"
                    if actual_major > expected_major
                    else "an incompatible schema lineage"
                )
                raise InvalidReceiptError(
                    f"{model_name} declares schema_version {declared}, {detail}; the bound "
                    f"release declares {self.expected_schema_version}"
                )
        package = raw.get("package_version")
        if package is not None and self.expected_package_version:
            if str(package) != self.expected_package_version:
                raise InvalidReceiptError(
                    f"{model_name} was written by package {package}, not the bound "
                    f"{self.expected_package_version}"
                )

    def _unavailable(self, detail: str) -> str:
        if self.required:
            raise ValidationUnavailable(detail)
        return VALIDATION_UNAVAILABLE


__all__ = [
    "ENV_REQUIRE_VALIDATION",
    "VALIDATION_CANONICAL",
    "VALIDATION_UNAVAILABLE",
    "CanonicalValidator",
    "ValidationUnavailable",
    "require_canonical_validation",
]
