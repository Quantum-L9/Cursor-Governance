"""
L9 Workflows — Graph Orchestration
==================================

`workflows/` is the single runtime root for L9 workflow graphs. It hosts two
distinct first-class graph kinds. They are not two generations of one thing, and
neither supersedes the other.

1. **SESSION_GUIDANCE** — `SessionDAG` (workflows.session)
   - Guides an agent through a workflow; not an executable runtime
   - Registered with `register_session_dag()`, resolved with `get_session_dag()`
   - Discovered by importing `workflows.dags`
   - Permits revision loops, because a guided workflow may legitimately
     return to an earlier step (see `SessionDAG.validate`)
   - Renders to Mermaid and Markdown for human review

2. **LANGGRAPH_RUNTIME** — `StateGraph` (langgraph.graph)
   - Executable state machine with async execution and state persistence
   - Never registered in the SessionDAG registry; reached through its own
     module or a domain-owned runtime entrypoint
   - Exemplars: `workflows/dags/gmp/`, `workflows/dags/inspect_dag.py`,
     `workflows/harvest_deploy.py`

Graph kind is a property of the graph, not a quality judgement. Classification
and lifecycle mechanics are owned by the `l9-dag-authoring` Skill; this package
owns implementation and execution.

Structure:
    workflows/
    ├── session/              # SESSION_GUIDANCE contract
    │   ├── interface.py      # SessionDAG, SessionNode, SessionEdge
    │   └── registry.py       # SessionDAG registry
    ├── dags/                 # Graph definitions of both kinds
    │   ├── __init__.py       # Discovery boundary (import to auto-register)
    │   ├── refactoring_dag.py        # SESSION_GUIDANCE
    │   ├── harvest_deploy_dag.py     # SESSION_GUIDANCE
    │   ├── inspect_dag.py            # LANGGRAPH_RUNTIME
    │   └── gmp/                      # LANGGRAPH_RUNTIME (graph/state/routing/nodes)
    ├── state.py              # LangGraph state schemas
    ├── nodes/                # LangGraph reusable nodes
    ├── harvest_deploy.py     # LANGGRAPH_RUNTIME
    ├── runner.py             # YAML-based CLI runner
    └── defs/                 # Simple YAML definitions

Usage:
    # SESSION_GUIDANCE (agent guidance)
    from workflows.session import get_session_dag
    dag = get_session_dag("harvest-deploy-v1")
    print(dag.to_mermaid())  # noqa: ADR-0019

    # LANGGRAPH_RUNTIME (execution)
    from workflows.harvest_deploy import run_harvest_deploy
    result = await run_harvest_deploy(source_document="...", ...)

    # YAML Runner (CLI)
    python -m workflows.runner run workflow.yaml

Author: L9 Team
"""

# ============================================================================

# === LangGraph State & Types ===
# These work with or without LangGraph installed
import importlib.util

from workflows.state import (
    ExtractionPattern,
    FileMapping,
    StepResult,
    StepStatus,
    ValidationCheck,
    WorkflowState,
    create_initial_state,
)

# LangGraph execution is available when langgraph is installed.
# find_spec("langgraph.graph") must import the parent "langgraph" package to
# resolve the submodule, so it raises ModuleNotFoundError (not None) when
# langgraph isn't installed at all — guard explicitly to keep this optional.
try:
    _LANGGRAPH_AVAILABLE = importlib.util.find_spec("langgraph.graph") is not None
except ModuleNotFoundError:
    _LANGGRAPH_AVAILABLE = False

# === Session DAG System ===
# Trigger DAG auto-registration (side-effect import — `as dags` signals intentional
# re-export). Must stay below _LANGGRAPH_AVAILABLE: registration order depends on
# the availability check running first.
from workflows import dags as dags  # noqa: E402
from workflows.session import (  # noqa: E402
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
    SessionState,
    get_session_dag,
    list_session_dags,
    register_session_dag,
    session_dag_registry,
)

__all__ = [
    "ExtractionPattern",
    "FileMapping",
    "GateType",
    "NodeType",
    # Session DAG
    "SessionDAG",
    "SessionEdge",
    "SessionNode",
    "SessionState",
    "StepResult",
    "StepStatus",
    "ValidationCheck",
    # LangGraph State
    "WorkflowState",
    "create_initial_state",
    "get_session_dag",
    "list_session_dags",
    "register_session_dag",
    "session_dag_registry",
]
