"""
Intelligence Harvest DAG - donor-to-beneficiary semantic mining (Enforced)
=========================================================================

Canonical runtime for the ``l9-intelligence-harvest`` skill pack, declared by
that pack as ``workflows/dags/intelligence_harvest_dag.py`` with registry id
``intelligence-harvest-v1``.

This module is a PROJECTION, not a second definition. The typed logical graph is
owned by the pack IR at ``skills/l9-intelligence-harvest/meta/skill-ir.json``,
which states in as many words that the pack "must not invent a parallel
registry". Node ids, kinds, capability bindings, edges, and the entrypoint below
are transcribed from that file; ``tests/workflows/test_intelligence_harvest_dag.py``
fails if the two ever disagree, so the IR stays the single source of the graph
and this stays the registration adapter.

The pack ships deterministic scripts for the deterministic nodes
(``bind_request.py``, ``inventory_source.py``, ``qualify_nuggets.py``,
``rank_nuggets.py``, ``validate_harvest.py``, ``render_brief.py``). Bounded-LLM
nodes carry their contract reference in ``action``; each fails closed with
"emit UNKNOWN or terminal BLOCKED; never fabricate" rather than inventing.

Terminal states: PASS, PARTIAL, BLOCKED, FAIL.

Version: 1.0.0
Source of truth: skills/l9-intelligence-harvest/meta/skill-ir.json
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Intelligence Harvest Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-08-28T00:00:00Z",
    "updated_at": "2026-08-28T00:00:00Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "intelligence_harvest_dag",
    "type": "cli",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.__init__"],
    },
}
# ============================================================================

from workflows.session.interface import NodeType, SessionDAG, SessionEdge, SessionNode
from workflows.session.registry import register_session_dag

#: The IR file this graph is transcribed from. Named so the drift test and any
#: reader can find the authority without searching.
IR_SOURCE = "skills/l9-intelligence-harvest/meta/skill-ir.json"

INTELLIGENCE_HARVEST_NODES = [
    SessionNode(
        id="BIND_REQUEST",
        name="Bind Request",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability bind_request",
        action="skills/l9-intelligence-harvest/scripts/bind_request.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "bind_and_validate_inputs",
            "capabilities": ["bind_request"],
        },
    ),
    SessionNode(
        id="PROBE_CAPABILITIES",
        name="Probe Capabilities",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability probe_capabilities",
        action="skills/l9-intelligence-harvest/scripts/inventory_source.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "artifact_and_reference_resolution",
            "capabilities": ["probe_capabilities", "canonical_dag_registration"],
        },
    ),
    SessionNode(
        id="LOCK_SOURCE_IDENTITY",
        name="Lock Source Identity",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability source_identity",
        action="skills/l9-intelligence-harvest/scripts/inventory_source.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "artifact_and_reference_resolution",
            "capabilities": ["source_identity"],
        },
    ),
    SessionNode(
        id="INVENTORY_DONOR",
        name="Inventory Donor",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability inventory_source",
        action="skills/l9-intelligence-harvest/scripts/inventory_source.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "package_integrity",
            "capabilities": ["inventory_source"],
        },
    ),
    SessionNode(
        id="RECONSTRUCT_SYSTEM",
        name="Reconstruct System",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability system_reconstruction",
        action="references/system-reconstruction-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["system_reconstruction"],
        },
    ),
    SessionNode(
        id="TRACE_SURFACES",
        name="Trace Surfaces",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability semantic_surface_mapping",
        action="references/system-reconstruction-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["semantic_surface_mapping"],
        },
    ),
    SessionNode(
        id="DETECT_DUPLICATION_DRIFT",
        name="Detect Duplication Drift",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability canonicality_interpretation",
        action="references/system-reconstruction-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["canonicality_interpretation"],
        },
    ),
    SessionNode(
        id="EXTRACT_CONCEPT_CANDIDATES",
        name="Extract Concept Candidates",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability concept_extraction",
        action="references/concept-extraction-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["concept_extraction"],
        },
    ),
    SessionNode(
        id="QUALIFY_NUGGETS",
        name="Qualify Nuggets",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability qualify_nuggets",
        action="skills/l9-intelligence-harvest/scripts/qualify_nuggets.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "structural_and_static_validation",
            "capabilities": ["qualify_nuggets"],
        },
    ),
    SessionNode(
        id="COMPARE_BENEFICIARY",
        name="Compare Beneficiary",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability beneficiary_comparison",
        action="references/beneficiary-fit-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["beneficiary_comparison"],
        },
    ),
    SessionNode(
        id="DISPOSITION_CONCEPTS",
        name="Disposition Concepts",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability disposition_selection",
        action="references/beneficiary-fit-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["disposition_selection"],
        },
    ),
    SessionNode(
        id="DERIVE_ACCEPTANCE_TESTS",
        name="Derive Acceptance Tests",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability acceptance_test_derivation",
        action="references/beneficiary-fit-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["acceptance_test_derivation"],
        },
    ),
    SessionNode(
        id="RANK_NUGGETS",
        name="Rank Nuggets",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability rank_nuggets",
        action="skills/l9-intelligence-harvest/scripts/rank_nuggets.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "structural_and_static_validation",
            "capabilities": ["rank_nuggets"],
        },
    ),
    SessionNode(
        id="SAFETY_PORTABILITY_AUDIT",
        name="Safety Portability Audit",
        node_type=NodeType.ANALYZE,
        description="bounded_llm node; capability risk_identification",
        action="references/system-reconstruction-contract.md",
        metadata={
            "ir_kind": "bounded_llm",
            "impl": "source_intelligence_extraction",
            "capabilities": ["risk_identification"],
        },
    ),
    SessionNode(
        id="EVIDENCE_CLOSURE",
        name="Evidence Closure",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability evidence_closure",
        action="skills/l9-intelligence-harvest/scripts/validate_harvest.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "artifact_and_reference_resolution",
            "capabilities": ["evidence_closure"],
        },
    ),
    SessionNode(
        id="RENDER_OUTPUT",
        name="Render Output",
        node_type=NodeType.VALIDATE,
        description="deterministic node; capability render_output",
        action="skills/l9-intelligence-harvest/scripts/render_brief.py",
        metadata={
            "ir_kind": "deterministic",
            "impl": "deterministic_metadata_rendering",
            "capabilities": ["render_output"],
        },
    ),
    SessionNode(
        id="PASS",
        name="Pass",
        node_type=NodeType.END,
        description="terminal node; capability none",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal", "impl": None, "capabilities": []},
    ),
    SessionNode(
        id="PARTIAL",
        name="Partial",
        node_type=NodeType.END,
        description="terminal node; capability none",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal", "impl": None, "capabilities": []},
    ),
    SessionNode(
        id="BLOCKED",
        name="Blocked",
        node_type=NodeType.END,
        description="terminal node; capability none",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal", "impl": None, "capabilities": []},
    ),
    SessionNode(
        id="FAIL",
        name="Fail",
        node_type=NodeType.END,
        description="terminal node; capability none",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal", "impl": None, "capabilities": []},
    ),
]

INTELLIGENCE_HARVEST_EDGES = [
    SessionEdge(from_node="BIND_REQUEST", to_node="PROBE_CAPABILITIES"),
    SessionEdge(from_node="PROBE_CAPABILITIES", to_node="LOCK_SOURCE_IDENTITY"),
    SessionEdge(from_node="LOCK_SOURCE_IDENTITY", to_node="INVENTORY_DONOR"),
    SessionEdge(from_node="INVENTORY_DONOR", to_node="RECONSTRUCT_SYSTEM"),
    SessionEdge(from_node="RECONSTRUCT_SYSTEM", to_node="TRACE_SURFACES"),
    SessionEdge(from_node="TRACE_SURFACES", to_node="DETECT_DUPLICATION_DRIFT"),
    SessionEdge(from_node="DETECT_DUPLICATION_DRIFT", to_node="EXTRACT_CONCEPT_CANDIDATES"),
    SessionEdge(from_node="EXTRACT_CONCEPT_CANDIDATES", to_node="QUALIFY_NUGGETS"),
    SessionEdge(from_node="QUALIFY_NUGGETS", to_node="COMPARE_BENEFICIARY"),
    SessionEdge(from_node="COMPARE_BENEFICIARY", to_node="DISPOSITION_CONCEPTS"),
    SessionEdge(from_node="DISPOSITION_CONCEPTS", to_node="DERIVE_ACCEPTANCE_TESTS"),
    SessionEdge(from_node="DERIVE_ACCEPTANCE_TESTS", to_node="RANK_NUGGETS"),
    SessionEdge(from_node="RANK_NUGGETS", to_node="SAFETY_PORTABILITY_AUDIT"),
    SessionEdge(from_node="SAFETY_PORTABILITY_AUDIT", to_node="EVIDENCE_CLOSURE"),
    SessionEdge(from_node="EVIDENCE_CLOSURE", to_node="RENDER_OUTPUT"),
    SessionEdge(from_node="RENDER_OUTPUT", to_node="PASS"),
    SessionEdge(from_node="RENDER_OUTPUT", to_node="PARTIAL"),
    SessionEdge(from_node="RENDER_OUTPUT", to_node="BLOCKED"),
    SessionEdge(from_node="RENDER_OUTPUT", to_node="FAIL"),
]

INTELLIGENCE_HARVEST_V1 = SessionDAG(
    id="intelligence-harvest-v1",
    name="Intelligence Harvest Workflow",
    version="1.0.0",
    description=(
        "Mine reusable semantic intelligence from a donor, compare it against a "
        "beneficiary, classify transfer dispositions, derive acceptance tests, and "
        "emit canonical harvest.json. Never mutates donor or beneficiary."
    ),
    nodes=INTELLIGENCE_HARVEST_NODES,
    edges=INTELLIGENCE_HARVEST_EDGES,
    entry_node="BIND_REQUEST",
    tags=["l9", "intelligence-harvest", "donor-mining", "diagnostic"],
    metadata={"ir_source": IR_SOURCE, "skill": "l9-intelligence-harvest"},
)

_errors = INTELLIGENCE_HARVEST_V1.validate()
if _errors:
    raise ValueError(f"intelligence-harvest-v1 DAG validation failed: {_errors}")

register_session_dag(INTELLIGENCE_HARVEST_V1)


# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
