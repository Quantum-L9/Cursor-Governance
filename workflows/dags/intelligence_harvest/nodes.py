from __future__ import annotations

from workflows.dags.intelligence_harvest.state import HarvestState


def node_bind_request(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/bind_request.py")
    state["ran"] = ran
    return state


def node_blocked(state: HarvestState) -> HarvestState:
    state["status"] = "BLOCKED"
    return state


def node_compare_beneficiary(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("COMPARE_BENEFICIARY")
    state["unknowns"] = unknowns
    return state


def node_derive_acceptance_tests(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("DERIVE_ACCEPTANCE_TESTS")
    state["unknowns"] = unknowns
    return state


def node_detect_duplication_drift(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("DETECT_DUPLICATION_DRIFT")
    state["unknowns"] = unknowns
    return state


def node_disposition_concepts(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("DISPOSITION_CONCEPTS")
    state["unknowns"] = unknowns
    return state


def node_evidence_closure(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/validate_harvest.py")
    state["ran"] = ran
    return state


def node_extract_concept_candidates(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("EXTRACT_CONCEPT_CANDIDATES")
    state["unknowns"] = unknowns
    return state


def node_fail(state: HarvestState) -> HarvestState:
    state["status"] = "FAIL"
    return state


def node_inventory_donor(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/inventory_source.py")
    state["ran"] = ran
    return state


def node_lock_source_identity(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/inventory_source.py")
    state["ran"] = ran
    return state


def node_partial(state: HarvestState) -> HarvestState:
    state["status"] = "PARTIAL"
    return state


def node_pass(state: HarvestState) -> HarvestState:
    state["status"] = "PASS"
    return state


def node_probe_capabilities(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/inventory_source.py")
    state["ran"] = ran
    return state


def node_qualify_nuggets(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/qualify_nuggets.py")
    state["ran"] = ran
    return state


def node_rank_nuggets(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/rank_nuggets.py")
    state["ran"] = ran
    return state


def node_reconstruct_system(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("RECONSTRUCT_SYSTEM")
    state["unknowns"] = unknowns
    return state


def node_render_output(state: HarvestState) -> HarvestState:
    ran = list(state.get("ran") or [])
    ran.append("skills/l9-intelligence-harvest/scripts/render_brief.py")
    state["ran"] = ran
    return state


def node_safety_portability_audit(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("SAFETY_PORTABILITY_AUDIT")
    state["unknowns"] = unknowns
    return state


def node_trace_surfaces(state: HarvestState) -> HarvestState:
    unknowns = list(state.get("unknowns") or [])
    unknowns.append("TRACE_SURFACES")
    state["unknowns"] = unknowns
    return state
