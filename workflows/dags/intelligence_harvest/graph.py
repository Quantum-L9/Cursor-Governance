from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from workflows.dags.intelligence_harvest.nodes import (
    node_bind_request,
    node_blocked,
    node_compare_beneficiary,
    node_derive_acceptance_tests,
    node_detect_duplication_drift,
    node_disposition_concepts,
    node_evidence_closure,
    node_extract_concept_candidates,
    node_fail,
    node_inventory_donor,
    node_lock_source_identity,
    node_partial,
    node_pass,
    node_probe_capabilities,
    node_qualify_nuggets,
    node_rank_nuggets,
    node_reconstruct_system,
    node_render_output,
    node_safety_portability_audit,
    node_trace_surfaces,
)
from workflows.dags.intelligence_harvest.routing import (
    route_after_render_output,
)
from workflows.dags.intelligence_harvest.state import HarvestState


def build_intelligence_harvest_graph() -> StateGraph:
    graph = StateGraph(HarvestState)
    graph.add_node("BIND_REQUEST", node_bind_request)
    graph.add_node("BLOCKED", node_blocked)
    graph.add_node("COMPARE_BENEFICIARY", node_compare_beneficiary)
    graph.add_node("DERIVE_ACCEPTANCE_TESTS", node_derive_acceptance_tests)
    graph.add_node("DETECT_DUPLICATION_DRIFT", node_detect_duplication_drift)
    graph.add_node("DISPOSITION_CONCEPTS", node_disposition_concepts)
    graph.add_node("EVIDENCE_CLOSURE", node_evidence_closure)
    graph.add_node("EXTRACT_CONCEPT_CANDIDATES", node_extract_concept_candidates)
    graph.add_node("FAIL", node_fail)
    graph.add_node("INVENTORY_DONOR", node_inventory_donor)
    graph.add_node("LOCK_SOURCE_IDENTITY", node_lock_source_identity)
    graph.add_node("PARTIAL", node_partial)
    graph.add_node("PASS", node_pass)
    graph.add_node("PROBE_CAPABILITIES", node_probe_capabilities)
    graph.add_node("QUALIFY_NUGGETS", node_qualify_nuggets)
    graph.add_node("RANK_NUGGETS", node_rank_nuggets)
    graph.add_node("RECONSTRUCT_SYSTEM", node_reconstruct_system)
    graph.add_node("RENDER_OUTPUT", node_render_output)
    graph.add_node("SAFETY_PORTABILITY_AUDIT", node_safety_portability_audit)
    graph.add_node("TRACE_SURFACES", node_trace_surfaces)
    graph.add_edge(START, "BIND_REQUEST")
    graph.add_edge("BIND_REQUEST", "PROBE_CAPABILITIES")
    graph.add_edge("BLOCKED", END)
    graph.add_edge("COMPARE_BENEFICIARY", "DISPOSITION_CONCEPTS")
    graph.add_edge("DERIVE_ACCEPTANCE_TESTS", "RANK_NUGGETS")
    graph.add_edge("DETECT_DUPLICATION_DRIFT", "EXTRACT_CONCEPT_CANDIDATES")
    graph.add_edge("DISPOSITION_CONCEPTS", "DERIVE_ACCEPTANCE_TESTS")
    graph.add_edge("EVIDENCE_CLOSURE", "RENDER_OUTPUT")
    graph.add_edge("EXTRACT_CONCEPT_CANDIDATES", "QUALIFY_NUGGETS")
    graph.add_edge("FAIL", END)
    graph.add_edge("INVENTORY_DONOR", "RECONSTRUCT_SYSTEM")
    graph.add_edge("LOCK_SOURCE_IDENTITY", "INVENTORY_DONOR")
    graph.add_edge("PARTIAL", END)
    graph.add_edge("PASS", END)
    graph.add_edge("PROBE_CAPABILITIES", "LOCK_SOURCE_IDENTITY")
    graph.add_edge("QUALIFY_NUGGETS", "COMPARE_BENEFICIARY")
    graph.add_edge("RANK_NUGGETS", "SAFETY_PORTABILITY_AUDIT")
    graph.add_edge("RECONSTRUCT_SYSTEM", "TRACE_SURFACES")
    graph.add_conditional_edges(
        "RENDER_OUTPUT",
        route_after_render_output,
        {"PASS": "PASS", "PARTIAL": "PARTIAL", "BLOCKED": "BLOCKED", "FAIL": "FAIL"},
    )
    graph.add_edge("SAFETY_PORTABILITY_AUDIT", "EVIDENCE_CLOSURE")
    graph.add_edge("TRACE_SURFACES", "DETECT_DUPLICATION_DRIFT")
    return graph
