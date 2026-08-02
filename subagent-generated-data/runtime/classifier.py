"""Deterministic classification of generated data units (law §14, §18).

Given a unit's primary class this assigns candidate destination routes and a
promotion risk class. The mapping is deterministic; model-assisted refinement
(law §14) may override candidate routes downstream but must stay a proposal.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import GeneratedDataClass, GeneratedDataUnit, RiskClass, RouteName

# Primary class -> candidate destination routes (law §7, §15, §16).
CLASS_TO_ROUTES: dict[GeneratedDataClass, tuple[RouteName, ...]] = {
    GeneratedDataClass.REPOSITORY_FACT: (RouteName.MEMORY,),
    GeneratedDataClass.ARCHITECTURE_BOUNDARY: (RouteName.ARCHITECTURE,),
    GeneratedDataClass.OWNERSHIP_FINDING: (RouteName.ARCHITECTURE,),
    GeneratedDataClass.DEPENDENCY_FINDING: (RouteName.ARCHITECTURE, RouteName.MEMORY),
    GeneratedDataClass.IMPLEMENTATION_SURFACE: (RouteName.MEMORY,),
    GeneratedDataClass.EXECUTION_PROCEDURE: (RouteName.PATTERNS,),
    GeneratedDataClass.VALIDATION_PROCEDURE: (RouteName.VALIDATION, RouteName.PATTERNS),
    GeneratedDataClass.FAILURE_PATTERN: (RouteName.VALIDATION,),
    GeneratedDataClass.REJECTED_APPROACH: (RouteName.VALIDATION, RouteName.MEMORY),
    GeneratedDataClass.CONTEXT_REQUIREMENT: (RouteName.CONTRACTS,),
    GeneratedDataClass.CONTEXT_WASTE: (RouteName.CONTRACTS,),
    GeneratedDataClass.TASK_CONTRACT_GAP: (RouteName.CONTRACTS,),
    GeneratedDataClass.POLICY_CANDIDATE: (RouteName.UNKNOWNS,),
    GeneratedDataClass.INVARIANT_CANDIDATE: (RouteName.VALIDATION,),
    GeneratedDataClass.REGRESSION_CANDIDATE: (RouteName.VALIDATION,),
    GeneratedDataClass.REUSABLE_PATTERN_CANDIDATE: (RouteName.PATTERNS,),
    GeneratedDataClass.ARTIFACT_LINEAGE: (RouteName.EVIDENCE,),
    GeneratedDataClass.UNRESOLVED_UNKNOWN: (RouteName.UNKNOWNS,),
    GeneratedDataClass.FOLLOW_ON_OPPORTUNITY: (RouteName.OPPORTUNITIES,),
    GeneratedDataClass.EVIDENCE_ONLY: (RouteName.EVIDENCE,),
}

# High-risk classes touch architecture ownership, policy, or cross-repo canon
# and can never be promoted automatically (law §18: SGD-014).
HIGH_RISK_CLASSES: frozenset[GeneratedDataClass] = frozenset(
    {
        GeneratedDataClass.ARCHITECTURE_BOUNDARY,
        GeneratedDataClass.OWNERSHIP_FINDING,
        GeneratedDataClass.POLICY_CANDIDATE,
        GeneratedDataClass.INVARIANT_CANDIDATE,
    }
)

# Medium-risk classes require independent validation or recurrence (law §18).
MEDIUM_RISK_CLASSES: frozenset[GeneratedDataClass] = frozenset(
    {
        GeneratedDataClass.EXECUTION_PROCEDURE,
        GeneratedDataClass.VALIDATION_PROCEDURE,
        GeneratedDataClass.REUSABLE_PATTERN_CANDIDATE,
        GeneratedDataClass.REGRESSION_CANDIDATE,
        GeneratedDataClass.FAILURE_PATTERN,
        GeneratedDataClass.TASK_CONTRACT_GAP,
        GeneratedDataClass.CONTEXT_REQUIREMENT,
        GeneratedDataClass.DEPENDENCY_FINDING,
    }
)


@dataclass(frozen=True, slots=True)
class Classification:
    unit_id: str
    primary_class: GeneratedDataClass
    candidate_routes: tuple[RouteName, ...]
    risk_class: RiskClass
    authority_required: str | None


def risk_for_class(cls: GeneratedDataClass) -> RiskClass:
    if cls in HIGH_RISK_CLASSES:
        return RiskClass.HIGH
    if cls in MEDIUM_RISK_CLASSES:
        return RiskClass.MEDIUM
    return RiskClass.LOW


def _authority_for(risk: RiskClass) -> str | None:
    if risk is RiskClass.HIGH:
        return "designated_human_or_canonical_authority"
    if risk is RiskClass.MEDIUM:
        return "independent_validation_or_recurrence"
    return "runtime_validation"


def classify(unit: GeneratedDataUnit) -> Classification:
    candidate = CLASS_TO_ROUTES.get(unit.primary_class, (RouteName.EVIDENCE,))
    risk = risk_for_class(unit.primary_class)
    return Classification(
        unit_id=unit.unit_id,
        primary_class=unit.primary_class,
        candidate_routes=candidate,
        risk_class=risk,
        authority_required=_authority_for(risk),
    )
