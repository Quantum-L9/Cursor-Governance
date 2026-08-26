"""Deterministic coverage audit for architecture semantic compilation.

Coverage is the machine-verifiable fidelity contract between the architecture
source and the generated campaign. `PASS` requires, all at once:

- every source unit has a disposition;
- every deterministic normative-signal unit has a governed disposition;
- every material semantic item has valid source provenance;
- every material executable semantic item has a campaign mapping;
- every reported contradiction has been reconciled;
- no source unit was omitted from extraction requests.

The audit never invents semantics. It only measures whether the extractor's
candidate interpretation, after reconciliation and lowering, accounts for the
whole source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .architecture_intent import SourceDocument
from .architecture_ir import (
    EXECUTABLE_KINDS,
    SUPPORTING_KINDS,
    SemanticItem,
)

DISPOSITION_BY_KIND: dict[str, str] = {
    "objective": "mapped_requirement",
    "requirement": "mapped_requirement",
    "constraint": "mapped_requirement",
    "prohibition": "mapped_prohibition",
    "decision": "mapped_decision",
    "acceptance": "mapped_acceptance",
    "validation": "mapped_validation",
    "negative_case": "mapped_validation",
    "risk": "mapped_risk",
    "assumption": "mapped_risk",
    "unknown": "mapped_evidence_requirement",
    "evidence_requirement": "mapped_evidence_requirement",
    "deferral": "mapped_deferral",
    "scope_include": "mapped_scope",
    "scope_exclude": "mapped_scope",
    "dependency": "mapped_requirement",
    "ordering": "mapped_requirement",
    "implementation_seam": "mapped_requirement",
    "file_seam": "mapped_requirement",
    "informational": "explicitly_non_normative_with_reason",
}


@dataclass
class CoverageResult:
    total_units: int
    classified_units: int
    material_units: int
    mapped_material_units: int
    unmapped_material_units: int
    status: str
    problems: list[dict[str, Any]] = field(default_factory=list)
    unit_dispositions: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def unmapped_unit_ids(self) -> list[str]:
        ids: list[str] = []
        for problem in self.problems:
            for unit_id in problem.get("unit_ids") or []:
                if unit_id not in ids:
                    ids.append(unit_id)
        return ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_units": self.total_units,
            "classified_units": self.classified_units,
            "material_units": self.material_units,
            "mapped_material_units": self.mapped_material_units,
            "unmapped_material_units": self.unmapped_material_units,
            "status": self.status,
            "problems": list(self.problems),
            "unit_dispositions": dict(self.unit_dispositions),
        }


def is_material_item(item: SemanticItem) -> bool:
    return item.materiality == "material" and item.kind != "informational"


def requires_campaign_mapping(item: SemanticItem) -> bool:
    if not is_material_item(item):
        return False
    if item.kind in SUPPORTING_KINDS:
        return False
    return item.kind in EXECUTABLE_KINDS


def audit_coverage(
    document: SourceDocument,
    items: list[SemanticItem],
    *,
    mappings: dict[str, list[dict[str, Any]]] | None = None,
    requested_unit_ids: set[str] | None = None,
) -> CoverageResult:
    """Audit unit dispositions, provenance, contradictions, and mappings.

    ``mappings`` maps semantic item id -> campaign mappings produced by the
    lowerer; pass ``None`` for the pre-lowering audit (mapping checks are then
    skipped, everything else still applies). ``requested_unit_ids`` is the set
    of unit ids actually sent to the extractor across all chunks: any unit
    outside it was silently omitted and fails coverage outright.
    """
    problems: list[dict[str, Any]] = []
    unit_ids = [unit.id for unit in document.units]
    unit_set = set(unit_ids)

    if requested_unit_ids is not None:
        omitted = sorted(unit_set - set(requested_unit_ids))
        if omitted:
            problems.append(
                {
                    "code": "source_chunk_omitted",
                    "detail": "source units never reached the extractor",
                    "unit_ids": omitted,
                }
            )

    items_by_unit: dict[str, list[SemanticItem]] = {unit_id: [] for unit_id in unit_ids}
    for item in items:
        for ref in item.source_refs:
            if ref in items_by_unit:
                items_by_unit[ref].append(item)
        if is_material_item(item) and not item.source_refs:
            problems.append(
                {
                    "code": "material_item_without_provenance",
                    "detail": f"{item.id} ({item.kind}) has no source provenance",
                    "semantic_ids": [item.id],
                }
            )

    dispositions: dict[str, str] = {}
    material_units = 0
    mapped_material_units = 0
    for unit in document.units:
        cited = items_by_unit[unit.id]
        if unit.kind == "frontmatter":
            dispositions[unit.id] = "routing_metadata"
            continue
        if not cited:
            dispositions[unit.id] = "unclassified"
            problems.append(
                {
                    "code": "unit_unclassified",
                    "detail": f"{unit.id} received no semantic disposition",
                    "unit_ids": [unit.id],
                }
            )
            continue
        material_cited = [item for item in cited if is_material_item(item)]
        if material_cited:
            # The strongest disposition wins for reporting; all are recorded
            # through the items themselves.
            dispositions[unit.id] = DISPOSITION_BY_KIND.get(
                material_cited[0].kind, "mapped_requirement"
            )
            material_units += 1
            if mappings is None:
                mapped_material_units += 1
            else:
                needing = [item for item in material_cited if requires_campaign_mapping(item)]
                if all(mappings.get(item.id) for item in needing):
                    mapped_material_units += 1
                else:
                    missing = [item.id for item in needing if not mappings.get(item.id)]
                    problems.append(
                        {
                            "code": "material_unit_unmapped",
                            "detail": (
                                f"{unit.id}: material semantic items {missing} carry no "
                                "campaign mapping"
                            ),
                            "unit_ids": [unit.id],
                            "semantic_ids": missing,
                        }
                    )
            continue
        # Only informational citations. A normative-signal unit needs an
        # explicit non-normative classification with a reason.
        if unit.signals:
            reasons = [item for item in cited if item.kind == "informational" and item.statement]
            if reasons:
                dispositions[unit.id] = "explicitly_non_normative_with_reason"
            else:
                dispositions[unit.id] = "unclassified"
                problems.append(
                    {
                        "code": "signal_unit_without_governed_disposition",
                        "detail": (
                            f"{unit.id} carries normative signals {list(unit.signals)} but has "
                            "no mapped or explicitly non-normative disposition"
                        ),
                        "unit_ids": [unit.id],
                    }
                )
        else:
            dispositions[unit.id] = "informational"

    if mappings is not None:
        known_ids = {item.id for item in items}
        for item in items:
            if requires_campaign_mapping(item) and not mappings.get(item.id):
                problems.append(
                    {
                        "code": "material_item_unmapped",
                        "detail": f"{item.id} ({item.kind}) has no campaign mapping",
                        "semantic_ids": [item.id],
                        "unit_ids": list(item.source_refs),
                    }
                )
        for item_id in mappings:
            if item_id not in known_ids:
                problems.append(
                    {
                        "code": "mapping_without_semantic_item",
                        "detail": f"campaign mapping references unknown semantic item {item_id}",
                        "semantic_ids": [item_id],
                    }
                )

    for item in items:
        for other_id in item.conflicts_with:
            problems.append(
                {
                    "code": "unreconciled_contradiction",
                    "detail": f"{item.id} still conflicts with {other_id}",
                    "semantic_ids": [item.id, other_id],
                    "unit_ids": list(item.source_refs),
                }
            )

    classified = sum(1 for value in dispositions.values() if value != "unclassified")
    # Deduplicate the mapped-unit problem double count: a unit is unmapped when
    # flagged; material minus flagged is the mapped figure already computed.
    unmapped_material = material_units - mapped_material_units
    status = "PASS" if not problems else "FAIL"
    return CoverageResult(
        total_units=len(unit_ids),
        classified_units=classified,
        material_units=material_units,
        mapped_material_units=mapped_material_units,
        unmapped_material_units=unmapped_material,
        status=status,
        problems=problems,
        unit_dispositions=dispositions,
    )
