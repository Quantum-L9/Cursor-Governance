"""
Workflow Graphs — Discovery Boundary
====================================

Importing this module registers every `SESSION_GUIDANCE` graph in the package.

Two distinct graph kinds live here. Both are first-class; neither is a legacy
generation of the other, and neither is "fake".

SESSION_GUIDANCE (`SessionDAG`, workflows.session.interface):
    Guides an agent through a workflow. Registered with `register_session_dag()`
    at import time and resolved with `get_session_dag()`. Not an executable
    runtime, and not intended to be one.

LANGGRAPH_RUNTIME (`StateGraph`, langgraph.graph):
    Executable state machine. Reached through its own module or a domain-owned
    runtime entrypoint, never through the SessionDAG registry.

See `workflows/__init__.py` for the package-level taxonomy and the
`l9-dag-authoring` Skill for graph-kind classification and lifecycle rules.
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Auto-Discovery",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-25T14:33:03Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "__init__",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": [],
    },
}
# ============================================================================

# SESSION_GUIDANCE graphs — registered on import
from workflows.dags.dag_authoring_dag import DAG_AUTHORING_DAG
from workflows.dags.gmp_execution_dag import GMP_EXECUTION_DAG
from workflows.dags.harvest_deploy_dag import HARVEST_DEPLOY_DAG

# LANGGRAPH_RUNTIME graphs — executable, not registry-backed
from workflows.dags.inspect_dag import (
    INSPECT_DAG,
    InspectState,
    build_inspect_graph,
    run_inspect,
)
from workflows.dags.pr_train_dag import (
    PR_TRAIN_DAG,
    PrTrainState,
    build_pr_train_graph,
    run_pr_train,
)
from workflows.dags.intelligence_harvest_dag import INTELLIGENCE_HARVEST_V1
from workflows.dags.readme_pipeline_dag import README_PIPELINE_DAG
from workflows.dags.refactoring_dag import REFACTORING_DAG
from workflows.dags.slash_command_update_dag import SLASH_COMMAND_UPDATE_DAG
from workflows.dags.test_pipeline_dag import TEST_PIPELINE_DAG
from workflows.dags.wire_dag import WIRE_DAG

__all__ = [
    # LANGGRAPH_RUNTIME
    "INSPECT_DAG",
    "InspectState",
    "build_inspect_graph",
    "run_inspect",
    "PR_TRAIN_DAG",
    "PrTrainState",
    "build_pr_train_graph",
    "run_pr_train",
    # SESSION_GUIDANCE
    "DAG_AUTHORING_DAG",
    "GMP_EXECUTION_DAG",
    "HARVEST_DEPLOY_DAG",
    "INTELLIGENCE_HARVEST_V1",
    "README_PIPELINE_DAG",
    "REFACTORING_DAG",
    "SLASH_COMMAND_UPDATE_DAG",
    "TEST_PIPELINE_DAG",
    "WIRE_DAG",
]
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-031",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "testing", "utility", "workflows"],
    "keywords": [
        "analysis",
        "auto",
        "dags",
        "dataclass",
        "discovery",
        "documentation",
        "executable",
        "langgraph",
    ],
    "business_value": "Utility module for   init  ",
    "last_modified": "2026-01-31T22:21:54Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
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
