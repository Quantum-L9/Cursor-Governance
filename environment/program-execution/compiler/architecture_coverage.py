"""Coverage: the deterministic proof that nothing material fell out.

A Blueprint that validates against its schema proves the artifact is well
formed. It proves nothing at all about whether the architecture the operator
wrote survived the trip. This module is that second proof, and it is mechanical
on purpose: dispositions per source unit, provenance per semantic item, and a
campaign mapping per material executable item, counted and compared.

The loop around it is a repair loop, not a gate. Ordinary incompleteness in a
first extraction pass — a missed unit, an ungrounded restatement, a
misclassification — is normal and gets another bounded round aimed only at what
is actually missing.

Compilation fails only for the conditions `audit()` records as failures, and
that set is exactly these five:

1. A source unit carrying normative signals has no disposition at all.
2. A normative unit has a disposition outside `GOVERNED_DISPOSITIONS`.
3. A semantic item cites no source unit (`source_refs` is empty).
4. A material *executable* item has no campaign mapping — checked only once
   `mappings` is supplied, which happens after lowering, so a pre-lowering
   audit cannot fail on this one.
5. Fewer source chunks were extracted than were sent.

Everything else the audit reports is a count, not a verdict. Two failures
live outside `audit()` and are named here so the boundary is complete:
`ask()` propagates `ExtractorError` when a response is still malformed after
its bounded retry, and `compile_architecture_intent` raises
`ArchitectureCompileError` when the repair rounds end with `status != "PASS"`.
Both leave nothing executed.

`CoverageError` is exported from this module but is raised nowhere; the
non-convergence path is the `ArchitectureCompileError` above. It is named
here rather than left to be inferred, because an exception in `__all__` reads
like part of the contract.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .architecture_extractor import (
    ArchitectureExtractor,
    ArchitectureExtractorRequest,
    ArchitectureExtractorResponse,
    ExtractorError,
    chunk_units,
    ensure_valid,
    new_request_id,
)
from .architecture_intent import ArchitectureIntent, SourceUnit
from .architecture_ir import (
    Contradiction,
    RejectedItem,
    SemanticItem,
    admit,
    contradictions,
    dedupe,
)

DISPOSITION_BY_KIND = {
    "requirement": "mapped_requirement",
    "objective": "mapped_requirement",
    "constraint": "mapped_requirement",
    "implementation_seam": "mapped_requirement",
    "prohibition": "mapped_prohibition",
    "negative_case": "mapped_prohibition",
    "decision": "mapped_decision",
    "assumption": "mapped_decision",
    "acceptance": "mapped_acceptance",
    "validation": "mapped_validation",
    "risk": "mapped_risk",
    "unknown": "mapped_risk",
    "deferral": "mapped_deferral",
    "scope_include": "mapped_scope",
    "scope_exclude": "mapped_scope",
    "evidence_requirement": "mapped_evidence_requirement",
    "file_seam": "mapped_requirement",
    "dependency": "mapped_requirement",
    "ordering": "mapped_requirement",
    "informational": "mapped_context",
}

#: A unit carrying these signals must end up with a governed disposition; a
#: `mapped_context` reading of a MUST is a coverage failure, not a disposition.
GOVERNED_DISPOSITIONS = frozenset(
    {
        "mapped_requirement",
        "mapped_prohibition",
        "mapped_decision",
        "mapped_acceptance",
        "mapped_validation",
        "mapped_risk",
        "mapped_deferral",
        "mapped_scope",
        "mapped_evidence_requirement",
        "explicitly_non_normative_with_reason",
    }
)

DEFAULT_REPAIR_ROUNDS = 3


class CoverageError(RuntimeError):
    """Semantic coverage cannot converge. Nothing has been executed."""


@dataclass
class UnitDisposition:
    unit: SourceUnit
    disposition: str
    semantic_ids: list[str] = field(default_factory=list)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = self.unit.to_dict(include_text=False)
        data["disposition"] = self.disposition
        data["semantic_ids"] = list(self.semantic_ids)
        if self.reason:
            data["reason"] = self.reason
        return data


@dataclass
class CoverageReport:
    dispositions: list[UnitDisposition]
    failures: list[str]
    unmapped_material_units: list[str]
    material_units: int
    mapped_material_units: int
    material_items: int
    mapped_material_items: int
    chunks_expected: int = 1
    chunks_extracted: int = 1
    unmapped_material_items: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "PASS" if not self.failures else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_units": len(self.dispositions),
            "classified_units": sum(1 for item in self.dispositions if item.disposition),
            "material_units": self.material_units,
            "mapped_material_units": self.mapped_material_units,
            "unmapped_material_units": len(self.unmapped_material_units),
            "material_semantic_items": self.material_items,
            "mapped_material_semantic_items": self.mapped_material_items,
            "chunks_expected": self.chunks_expected,
            "chunks_extracted": self.chunks_extracted,
            "status": self.status,
            "failures": list(self.failures),
        }


def ask(
    extractor: ArchitectureExtractor,
    request: ArchitectureExtractorRequest,
    *,
    retries: int = 1,
) -> ArchitectureExtractorResponse:
    """One request, with a bounded retry on a malformed or failed response.

    A model that returns prose where JSON was asked for is a normal, recoverable
    event; a model that does it twice is a broken capability. Neither one is
    allowed to become a partially authoritative extraction, so the retry either
    produces a schema-valid response or the error propagates and compilation
    fails with nothing executed.
    """
    last: ExtractorError | None = None
    for attempt in range(retries + 1):
        try:
            return ensure_valid(extractor.extract(request))
        except ExtractorError as exc:
            last = exc
            if attempt >= retries:
                break
    raise last if last is not None else ExtractorError("extractor produced no response")


def dispositions_for(
    units: Sequence[SourceUnit], items: Sequence[SemanticItem]
) -> list[UnitDisposition]:
    """Assign every unit exactly one disposition, strongest reading wins."""
    by_unit: dict[str, list[SemanticItem]] = {unit.id: [] for unit in units}
    for item in items:
        for ref in item.source_refs:
            if ref in by_unit:
                by_unit[ref].append(item)
    order = [
        "mapped_prohibition",
        "mapped_requirement",
        "mapped_decision",
        "mapped_acceptance",
        "mapped_validation",
        "mapped_evidence_requirement",
        "mapped_deferral",
        "mapped_scope",
        "mapped_risk",
        "mapped_context",
    ]
    rank = {name: index for index, name in enumerate(order)}
    result: list[UnitDisposition] = []
    for unit in units:
        mapped = by_unit[unit.id]
        material = [item for item in mapped if item.material]
        pool = material or mapped
        if not pool:
            if unit.normative:
                result.append(
                    UnitDisposition(
                        unit=unit,
                        disposition="",
                        reason="normative signals present but no semantic item cites this unit",
                    )
                )
            else:
                result.append(
                    UnitDisposition(
                        unit=unit,
                        disposition="explicitly_non_normative_with_reason",
                        reason="no normative signal and no semantic item cites this unit",
                    )
                )
            continue
        best = min(
            (DISPOSITION_BY_KIND.get(item.kind, "mapped_context") for item in pool),
            key=lambda name: rank.get(name, len(order)),
        )
        if unit.normative and best == "mapped_context":
            result.append(
                UnitDisposition(
                    unit=unit,
                    disposition="",
                    semantic_ids=[item.id for item in pool],
                    reason=(
                        f"unit carries normative signals {list(unit.signals)} but was read only "
                        "as context"
                    ),
                )
            )
            continue
        result.append(
            UnitDisposition(
                unit=unit,
                disposition=best,
                semantic_ids=[item.id for item in pool],
            )
        )
    return result


def audit(
    intent: ArchitectureIntent,
    items: Sequence[SemanticItem],
    *,
    mappings: dict[str, list[dict[str, Any]]] | None = None,
    chunks_expected: int = 1,
    chunks_extracted: int = 1,
) -> CoverageReport:
    """Count coverage. `mappings` is supplied only after campaign lowering."""
    dispositions = dispositions_for(intent.units, items)
    failures: list[str] = []
    unmapped_units = [entry.unit.id for entry in dispositions if not entry.disposition]
    if unmapped_units:
        failures.append(
            "source units with normative signals have no governed disposition: "
            + ", ".join(unmapped_units[:12])
        )
    for entry in dispositions:
        if (
            entry.disposition
            and entry.unit.normative
            and entry.disposition not in GOVERNED_DISPOSITIONS
        ):
            failures.append(
                f"{entry.unit.id} carries {list(entry.unit.signals)} but its disposition "
                f"{entry.disposition} is not governed"
            )
    for item in items:
        if not item.source_refs:
            failures.append(f"{item.id} has no source provenance")
    material_items = [item for item in items if item.material]
    executable = [item for item in material_items if item.executable]
    mapped_items = 0
    unmapped_items: list[str] = []
    if mappings is not None:
        for item in executable:
            if mappings.get(item.id):
                mapped_items += 1
            else:
                unmapped_items.append(item.id)
        if unmapped_items:
            failures.append(
                "material executable semantic items with no campaign mapping: "
                + ", ".join(unmapped_items[:12])
            )
    if chunks_extracted < chunks_expected:
        failures.append(
            f"only {chunks_extracted} of {chunks_expected} source chunks were extracted; "
            "no chunk may be silently omitted"
        )
    material_units = [unit for unit in intent.units if unit.normative]
    mapped_material = [
        entry
        for entry in dispositions
        if entry.unit.normative and entry.disposition in GOVERNED_DISPOSITIONS
    ]
    return CoverageReport(
        dispositions=dispositions,
        failures=failures,
        unmapped_material_units=unmapped_units,
        material_units=len(material_units),
        mapped_material_units=len(mapped_material),
        material_items=len(material_items),
        mapped_material_items=mapped_items if mappings is not None else len(executable),
        unmapped_material_items=unmapped_items,
        chunks_expected=chunks_expected,
        chunks_extracted=chunks_extracted,
    )


@dataclass
class ExtractionResult:
    items: list[SemanticItem]
    rejected: list[RejectedItem]
    contradictions: list[Contradiction]
    coverage: CoverageReport
    chunks: int
    repair_rounds: int
    critic_rounds: int
    extractor_id: str = ""
    notes: list[str] = field(default_factory=list)

    def unresolved_contradictions(self) -> list[Contradiction]:
        alive = {item.id for item in self.items}
        return [
            entry
            for entry in self.contradictions
            if entry.left_id in alive and entry.right_id in alive
        ]


def extract_semantics(
    intent: ArchitectureIntent,
    extractor: ArchitectureExtractor,
    *,
    max_chunk_chars: int | None = None,
    repair_rounds: int = DEFAULT_REPAIR_ROUNDS,
    critic: bool = True,
) -> ExtractionResult:
    """segment → extract → admit → dedupe → audit → critic → bounded repair.

    Every round narrows: a repair request carries only the units and items that
    are actually unresolved, never the whole document again.
    """
    chunks = (
        chunk_units(intent.units, max_chars=max_chunk_chars)
        if max_chunk_chars
        else chunk_units(intent.units)
    )
    unit_texts = {unit.id: unit.text for unit in intent.units}
    unit_order = {unit.id: index for index, unit in enumerate(intent.units)}
    raw_items: list[dict[str, Any]] = []
    rejected: list[RejectedItem] = []
    notes: list[str] = []
    chunks_extracted = 0
    seen_units: set[str] = set()
    for index, chunk in enumerate(chunks):
        request = ArchitectureExtractorRequest(
            request_id=new_request_id(),
            mode="extract",
            source_sha256=intent.sha256,
            units=chunk,
            target=intent.target,
            chunk_index=index,
            chunk_total=len(chunks),
        )
        response = ask(extractor, request)
        chunks_extracted += 1
        seen_units.update(unit.id for unit in chunk)
        raw_items.extend(response.items)
        notes.extend(response.notes)

    missing_chunks = [unit.id for unit in intent.units if unit.id not in seen_units]
    if missing_chunks:
        notes.append(f"source units never sent for extraction: {missing_chunks[:8]}")

    accepted, chunk_rejected = admit(raw_items, unit_texts=unit_texts)
    rejected.extend(chunk_rejected)
    items = dedupe(accepted, unit_order)
    report = audit(intent, items, chunks_expected=len(chunks), chunks_extracted=chunks_extracted)
    if missing_chunks:
        report.failures.append(
            "source units were never sent to the extractor: " + ", ".join(missing_chunks[:12])
        )

    critic_rounds = 0
    if critic:
        try:
            critique = ask(
                extractor,
                ArchitectureExtractorRequest(
                    request_id=new_request_id(),
                    mode="critic",
                    source_sha256=intent.sha256,
                    units=tuple(intent.material_units or intent.units),
                    target=intent.target,
                    existing_items=tuple(item.to_dict() for item in items),
                    reasons=(
                        "identify material obligations that are absent, weakened, reversed, "
                        "or misclassified",
                    ),
                ),
            )
            critic_rounds = 1
            critic_items, critic_rejected = admit(critique.items, unit_texts=unit_texts)
            rejected.extend(critic_rejected)
            if critic_items:
                items = dedupe(list(items) + critic_items, unit_order)
                report = audit(
                    intent,
                    items,
                    chunks_expected=len(chunks),
                    chunks_extracted=chunks_extracted,
                )
                if missing_chunks:
                    report.failures.append(
                        "source units were never sent to the extractor: "
                        + ", ".join(missing_chunks[:12])
                    )
        except ExtractorError as exc:
            # The critic strengthens coverage; it does not own it. A failed
            # critic round is recorded and the deterministic audit still rules.
            notes.append(f"critic round unavailable: {exc}")

    rounds = 0
    while report.failures and rounds < repair_rounds:
        focus = _repair_focus(intent, report, rejected)
        if not focus:
            break
        rounds += 1
        response = ask(
            extractor,
            ArchitectureExtractorRequest(
                request_id=new_request_id(),
                mode="repair",
                source_sha256=intent.sha256,
                units=focus,
                target=intent.target,
                focus=tuple(unit.id for unit in focus),
                reasons=tuple(report.failures[:8]),
                existing_items=tuple(item.to_dict() for item in items),
            ),
        )
        repaired, repair_rejected = admit(response.items, unit_texts=unit_texts)
        rejected.extend(repair_rejected)
        if not repaired:
            break
        items = dedupe(list(items) + repaired, unit_order)
        report = audit(
            intent, items, chunks_expected=len(chunks), chunks_extracted=chunks_extracted
        )
        if missing_chunks:
            report.failures.append(
                "source units were never sent to the extractor: " + ", ".join(missing_chunks[:12])
            )

    return ExtractionResult(
        extractor_id=str(getattr(extractor, "id", "") or extractor.__class__.__name__),
        items=list(items),
        rejected=rejected,
        contradictions=contradictions(items),
        coverage=report,
        chunks=len(chunks),
        repair_rounds=rounds,
        critic_rounds=critic_rounds,
        notes=notes,
    )


def _repair_focus(
    intent: ArchitectureIntent, report: CoverageReport, rejected: Iterable[RejectedItem]
) -> tuple[SourceUnit, ...]:
    """Only the units that are actually unresolved, plus their neighbours.

    Context matters for a list item whose obligation is stated in the paragraph
    above it, so one neighbour on each side travels with the focus. Resending
    the whole architecture every round is what makes long documents uncompilable.
    """
    wanted = {entry.unit.id for entry in report.dispositions if not entry.disposition}
    for item in rejected:
        wanted.update(item.source_refs)
    if not wanted:
        return ()
    order = list(intent.units)
    positions = {unit.id: index for index, unit in enumerate(order)}
    selected: set[int] = set()
    for unit_id in wanted:
        index = positions.get(unit_id)
        if index is None:
            continue
        for neighbour in (index - 1, index, index + 1):
            if 0 <= neighbour < len(order):
                selected.add(neighbour)
    return tuple(order[index] for index in sorted(selected))


__all__ = [
    "CoverageError",
    "CoverageReport",
    "DEFAULT_REPAIR_ROUNDS",
    "DISPOSITION_BY_KIND",
    "ExtractionResult",
    "GOVERNED_DISPOSITIONS",
    "UnitDisposition",
    "ask",
    "audit",
    "dispositions_for",
    "extract_semantics",
]
