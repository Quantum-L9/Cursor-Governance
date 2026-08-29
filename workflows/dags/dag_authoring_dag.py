"""
DAG Authoring Graph — the graph lifecycle, encoded
===================================================

Runtime projection of the `l9-dag-authoring` Skill. The Skill owns the graph
lifecycle contract; this graph is how an agent walks it.

`workflows/` hosts two distinct first-class graph kinds, and the first
substantive step here is deciding which one is being authored:

- SESSION_GUIDANCE — a `SessionDAG` that guides an agent through a workflow.
  Registered with `register_session_dag()`, resolved with `get_session_dag()`,
  discovered by importing `workflows.dags`. Not an executable runtime.
- LANGGRAPH_RUNTIME — an executable `StateGraph`. Reached through its own module
  or a domain-owned runtime entrypoint, never through the SessionDAG registry.

Neither is a legacy generation of the other. Coercing one into the other's
contract is the failure this graph exists to prevent.

CRITICAL INSIGHT (unchanged):
- Graph nodes carry ALL detailed instructions in their `action` field
- Slash commands are MINIMAL TRIGGERS
- NEVER duplicate instructions between command file and graph

Phases:
0. CLASSIFY — resolve graph kind before authoring anything
1. ANALYZE — understand the workflow to encode
2. STRUCTURE — design the graph
3. WRITE — nodes and edges, or runtime modules
4. VALIDATE — kind-specific structural validation
5. BIND — registration/discovery, or runtime entrypoint proof
6. COMMAND — optional thin trigger

Version: 2.1.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Dag Authoring Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-31T20:27:26Z",
    "updated_at": "2026-01-31T22:27:11Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "dag_authoring_dag",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.__init__"],
    },
}
# ============================================================================

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

# =============================================================================
# DAG AUTHORING GRAPH DEFINITION
# =============================================================================

DAG_AUTHORING_DAG = SessionDAG(
    id="dag-authoring-v1",
    name="DAG Authoring Workflow",
    version="2.1.0",
    description="""
Author or update an L9 workflow graph the proper way.

CRITICAL RULES:
1. Classify the graph kind BEFORE authoring, validating, or registering
2. Graph nodes contain ALL detailed instructions in `action` field
3. The slash command file is a MINIMAL TRIGGER only
4. NEVER duplicate instructions between command and graph
5. NEVER register a LANGGRAPH_RUNTIME graph in the SessionDAG registry

GRAPH KINDS:
- SESSION_GUIDANCE — `SessionDAG` guidance workflow. Registered through
  register_session_dag(), resolved through get_session_dag(), discovered by
  importing workflows.dags. Permits revision loops. Not executable.
- LANGGRAPH_RUNTIME — executable `StateGraph`. No registry. Reached through its
  own module or a domain-owned runtime entrypoint.
- UNKNOWN — conflicting or absent evidence. Blocks mutation.

NODE TYPES (SESSION_GUIDANCE authoring):
- START/END — Entry/exit points
- ANALYZE — Information gathering, no state change
- TRANSFORM — State-changing operations
- VALIDATE — Verification checks
- GATE — Conditional branching (CONDITIONAL or USER_CONFIRM)

PROPER PATTERN:
```python
SessionNode(
    id="unique_id",
    name="Human Name",
    node_type=NodeType.TRANSFORM,
    description="One-line summary",
    action='''Detailed multi-line instructions here.

Include:
- Exact commands to run
- Expected outputs
- Pre-reading files
- Success criteria
''',
    outputs=["state_key_1", "state_key_2"],
)
```

KEY FILES:
- Graphs: workflows/dags/*.py
- SessionDAG interface: workflows/session/interface.py
- SessionDAG registry: workflows/session/registry.py
- Discovery boundary: workflows/dags/__init__.py
- Commands: commands/*.md
- Skill: skills/l9-dag-authoring/
""",
    tags=["meta", "dag", "authoring", "workflow", "creation", "langgraph"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin graph authoring workflow. Identify what workflow to encode.",
        ),
        # === PHASE 0: CLASSIFY ===
        SessionNode(
            id="classify_graph_kind",
            name="Classify Graph Kind",
            node_type=NodeType.ANALYZE,
            description="Resolve SESSION_GUIDANCE vs LANGGRAPH_RUNTIME before authoring",
            action="""Resolve the graph kind. Nothing else may proceed until this is settled.

The two kinds are distinct contracts, not old and new generations of one thing.
Coercing one into the other is the failure this step prevents.

| | SESSION_GUIDANCE | LANGGRAPH_RUNTIME |
|---|---|---|
| Type | SessionDAG | StateGraph |
| Registry | register_session_dag() | none |
| Lookup | get_session_dag() | domain runtime entrypoint |
| Discovery | workflows/dags/__init__.py | module import |
| Executable | no | yes |

1. **If a source file already exists, classify it:**
```bash
python3 skills/l9-dag-authoring/scripts/classify_graph_kind.py workflows/dags/<file>.py
```
Classification reads the AST. A construction call outranks an import, so a
SessionDAG module that documents runtime validation in a node action string
stays SESSION_GUIDANCE.

2. **If authoring from scratch, decide from the requirement:**
   - Does an agent read the steps and carry them out? → SESSION_GUIDANCE
   - Does code execute the steps with state and routing? → LANGGRAPH_RUNTIME

3. **If evidence conflicts or is absent → UNKNOWN.** Stop. Do not guess a kind
   to keep moving. Report the smallest unresolved fact.

4. **Record in state:**
```python
state["graph_kind"] = "SESSION_GUIDANCE"  # or LANGGRAPH_RUNTIME / UNKNOWN
state["graph_path"] = "workflows/dags/<file>.py"
```

Pre-reading: skills/l9-dag-authoring/policies/graph-kinds.yaml""",
            outputs=["graph_kind", "graph_path"],
        ),
        SessionNode(
            id="gate_graph_kind",
            name="Which Graph Kind?",
            node_type=NodeType.GATE,
            description="Route to the SessionDAG branch or the LangGraph runtime branch",
            action="""Route on the resolved graph kind.

- SESSION_GUIDANCE → SessionDAG authoring branch
- LANGGRAPH_RUNTIME → runtime authoring branch
- UNKNOWN → blocked; resolve ownership or evidence first""",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('graph_kind') in {'SESSION_GUIDANCE', 'LANGGRAPH_RUNTIME'}",
        ),
        SessionNode(
            id="blocked_unknown_kind",
            name="Blocked — Unknown Graph Kind",
            node_type=NodeType.END,
            description="Terminal: graph kind unresolved, mutation refused",
            action="""Terminal state BLOCKED.

Graph kind could not be resolved. Do not author, validate, or register anything.

Report:
- what evidence was found (constructions, imports, or neither)
- which domain owner must decide
- the smallest fact that would unblock

Never default to SESSION_GUIDANCE because it is the more common kind here.""",
        ),
        # === PHASE 1: ANALYZE (shared) ===
        SessionNode(
            id="analyze_workflow",
            name="Analyze Workflow",
            node_type=NodeType.ANALYZE,
            description="Understand the workflow to encode",
            action="""Analyze the workflow that needs to be encoded.

1. **Identify the workflow source:**
   - Existing chat transcript with steps?
   - Manual process to automate?
   - New workflow design?

2. **Confirm the domain owner.** This graph owns lifecycle mechanics only.
   If the request is really "design the domain behavior", route to the domain
   Skill first, then come back and encode the result.

3. **Extract key elements:**
   - What are the PHASES? (numbered steps)
   - What are the GATES? (decision points, user confirms)
   - What are the OUTPUTS? (state values produced)
   - What files need to be read/modified?

4. **Document in state:**
   ```python
   state["workflow_name"] = "readme-pipeline"
   state["phases"] = ["gap_analysis", "enrich", "generate", "validate"]
   state["gates"] = ["gaps_found?", "template_update?", "validation_passed?"]
   state["key_files"] = ["config.yaml", "generator.py"]
   ```

5. **Check for an existing graph of the same kind:**
   ```bash
   ls workflows/dags/*.py
   ```
   A duplicate graph id fails closed unless this is an explicit update by the
   same owner.

Pre-reading: workflows/dags/*.py (pick one of the matching kind as reference)""",
            outputs=["workflow_name", "phases", "gates", "key_files", "reference_graph"],
        ),
        # === PHASE 2: STRUCTURE (SESSION_GUIDANCE) ===
        SessionNode(
            id="design_structure",
            name="Design Node Structure",
            node_type=NodeType.ANALYZE,
            description="Design the SessionDAG node graph",
            action="""Design the SessionDAG node graph.

1. **Create node list:**
   - start (START)
   - One node per phase (ANALYZE/TRANSFORM/VALIDATE)
   - One gate per decision point (GATE)
   - end (END)

2. **Map node types:**
   | Phase | Node ID | Node Type | Gate Type |
   |-------|---------|-----------|-----------|
   | Entry | start | START | - |
   | Analysis | analyze_X | ANALYZE | - |
   | Decision | gate_X | GATE | CONDITIONAL/USER_CONFIRM |
   | Transform | do_X | TRANSFORM | - |
   | Validate | validate_X | VALIDATE | - |
   | Exit | end | END | - |

3. **Design edge flow:**
   ```
   start -> phase1 -> gate1 -> [branch_a, branch_b] -> phase2 -> validate ->
   gate2 -> [success, retry] -> end
   ```

4. **Identify loop-backs.** Revision loops are legal here: SessionDAG.validate()
   deliberately permits cycles because a guided workflow may return to an
   earlier step. Do not remove a loop to make the graph acyclic.

5. **Document state flow:**
   What outputs from each node feed into later nodes?

Pre-reading: workflows/session/interface.py (for NodeType, GateType enums)""",
            outputs=["node_list", "edge_flow", "loop_backs"],
        ),
        # === PHASE 3: WRITE NODES (SESSION_GUIDANCE) ===
        SessionNode(
            id="write_nodes",
            name="Write Node Definitions",
            node_type=NodeType.TRANSFORM,
            description="Write each node with detailed action instructions",
            action="""Write each SessionNode with DETAILED action instructions.

CRITICAL: Each node's `action` field contains ALL instructions.
   This is where the actual work is documented — NOT in the command file!

FOR EACH NODE:

```python
SessionNode(
    id="lowercase_snake_case",           # Unique identifier
    name="Human Readable Name",          # Display name
    node_type=NodeType.TRANSFORM,        # Type (see below)
    description="One-line what it does", # Brief summary
    action='''DETAILED instructions here.

## What to Do
1. Specific step one
2. Specific step two

## Commands to Run
    actual_command --with-flags

## Expected Output
- Description of success state
- What files change

## Pre-reading
- path/to/file.py

## State Updates
    state["key"] = value
''',
    outputs=["state_keys_produced"],     # Optional: state keys this node sets
    gate_type=GateType.CONDITIONAL,      # Only for GATE nodes
    validation="state.get('x', False)",  # Only for GATE/VALIDATE nodes
)
```

NODE TYPE GUIDE:
- START/END — Entry/exit (minimal action)
- ANALYZE — Read, compare, discover (no mutations)
- TRANSFORM — Create, modify, delete (mutations)
- VALIDATE — Check, verify, test (assertions)
- GATE — Decision point (needs gate_type)

GATE TYPE GUIDE:
- CONDITIONAL — Auto-evaluated (validation expression)
- USER_CONFIRM — Requires user approval

DO: Include exact commands, file paths, expected outputs
DON'T: Leave vague instructions like "do the thing"

Pre-reading: workflows/dags/readme_pipeline_dag.py (good example)""",
            outputs=["nodes_written"],
        ),
        # === PHASE 4: WRITE EDGES (SESSION_GUIDANCE) ===
        SessionNode(
            id="write_edges",
            name="Write Edge Definitions",
            node_type=NodeType.TRANSFORM,
            description="Define flow between nodes",
            action="""Write SessionEdge definitions for all transitions.

EDGE STRUCTURE:
```python
SessionEdge(
    from_node="node_id",        # Source node
    to_node="target_id",        # Destination node
    condition="condition_key",  # Optional: for conditional branches
    label="Display Label",      # Optional: edge label for visualization
)
```

PATTERNS:

1. **Linear flow:**
```python
SessionEdge(from_node="start", to_node="phase1"),
SessionEdge(from_node="phase1", to_node="phase2"),
```

2. **Conditional branch (from gate):**
```python
SessionEdge(from_node="gate_x", to_node="path_a", condition="yes", label="Approved"),
SessionEdge(from_node="gate_x", to_node="path_b", condition="no", label="Rejected"),
```

3. **Loop-back (validation retry):**
```python
SessionEdge(from_node="gate_valid", to_node="fix_step", condition="failed", label="Fix issues"),
SessionEdge(from_node="gate_valid", to_node="next_step", condition="passed", label="Continue"),
```

4. **Merge (multiple paths join):**
```python
SessionEdge(from_node="path_a", to_node="merged_step"),
SessionEdge(from_node="path_b", to_node="merged_step"),
```

COMPLETENESS CHECK:
- Every node except END has at least one outgoing edge
- Every node except START has at least one incoming edge
- All gate nodes have edges for each possible outcome""",
            outputs=["edges_written"],
        ),
        # === PHASE 5: VALIDATE (SESSION_GUIDANCE) ===
        SessionNode(
            id="validate_session_dag",
            name="Validate SessionDAG",
            node_type=NodeType.VALIDATE,
            description="Structural validation of the SessionDAG source",
            action="""Validate the SessionDAG is syntactically correct and registerable.

1. **Syntax check:**
```bash
python -m py_compile workflows/dags/new_dag.py
```

2. **Structural check (AST, no import needed):**
```bash
python3 skills/l9-dag-authoring/scripts/validate_session_dag_source.py \\
    workflows/dags/new_dag.py
```
This proves exactly one canonical SessionDAG assignment, that
register_session_dag is imported from workflows.session.registry, that the
canonical symbol is actually registered, and that no static edge endpoint
dangles.

3. **Import test:**
```bash
python -c "from workflows.dags.new_dag import NEW_DAG; print(NEW_DAG.id)"
```

4. **Interface validation:**
```bash
python -c "
from workflows.dags.new_dag import NEW_DAG
errors = NEW_DAG.validate()
assert not errors, errors
print('nodes', len(NEW_DAG.nodes), 'edges', len(NEW_DAG.edges))
"
```
Cycles are NOT errors here. SessionDAG.validate() permits them by contract.

SUCCESS CRITERIA:
- py_compile passes
- validate_session_dag_source.py returns PASS
- Import succeeds
- SessionDAG.validate() returns no errors""",
            outputs=["validation_passed"],
        ),
        SessionNode(
            id="gate_session_validation",
            name="SessionDAG Validation Passed?",
            node_type=NodeType.GATE,
            description="Check if SessionDAG validation succeeded",
            action="If validation passed, register and prove discovery. Otherwise fix the nodes.",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('validation_passed', False)",
        ),
        # === PHASE 5b: REGISTER + DISCOVER (SESSION_GUIDANCE only) ===
        SessionNode(
            id="register_and_discover",
            name="Register and Prove Discovery",
            node_type=NodeType.VALIDATE,
            description="Bind the SessionDAG to the registry and the discovery boundary",
            action="""Register the SessionDAG and prove it is reachable. This step is
SESSION_GUIDANCE only — never run it for a LANGGRAPH_RUNTIME graph.

1. **Register on import** (in the graph module itself):
```python
from workflows.session.registry import register_session_dag

def register():
    register_session_dag(NEW_DAG)

register()
```
Never invent ACTIVE_DAGS, a dict-only registry, or a second registration layer.

2. **Add to the discovery boundary** — workflows/dags/__init__.py:
```python
from workflows.dags.new_dag import NEW_DAG
```
and add "NEW_DAG" to __all__ under the SESSION_GUIDANCE group.

3. **Probe registration and discovery.** Registration is a separate proof
   obligation from constructing the object — claiming either without a probe is
   forbidden:
```bash
python3 skills/l9-dag-authoring/scripts/probe_registration.py "$PWD" new-dag-id
```

Equivalent by hand:
```bash
python -c "
import workflows.dags
from workflows.session.registry import get_session_dag
d = get_session_dag('new-dag-id')
assert d is not None
print('registered:', d.id)
"
```

The lookup function is get_session_dag(). There is no get_dag() in
workflows/session/registry.py — calling it raises ImportError.

SUCCESS CRITERIA:
- probe exits 0 and prints the graph id
- importing workflows.dags does not raise""",
            outputs=["registration_passed", "discovery_passed"],
        ),
        # === LANGGRAPH_RUNTIME BRANCH ===
        SessionNode(
            id="design_runtime",
            name="Design LangGraph Runtime",
            node_type=NodeType.TRANSFORM,
            description="Author the executable graph, state, routing, and nodes",
            action="""Author the LANGGRAPH_RUNTIME graph. This is executable code, not
guidance text.

1. **Separate concerns once complexity warrants it** — the current exemplar is
   workflows/dags/gmp/:
   - graph.py — builds the StateGraph, adds nodes and edges
   - state.py — the typed state schema
   - routing.py — conditional edge functions
   - nodes/ — node implementations
   - executor.py — the public runtime entrypoint

   A small runtime may stay in one module (see workflows/dags/inspect_dag.py).

2. **Build the graph:**
```python
from langgraph.graph import END, START, StateGraph

def build_graph():
    graph = StateGraph(MyState)
    graph.add_node("step", step_fn)
    graph.add_edge(START, "step")
    graph.add_conditional_edges("step", route_fn, {"done": END})
    return graph
```

3. **Domain ownership.** This graph owns mechanics: construction, binding,
   routing resolution, compilation. The domain owner owns node semantics, state
   semantics, side effects, permissions, and terminal meaning. Do not invent
   domain behavior here.

4. **Do NOT import or call register_session_dag, and do NOT construct a
   SessionDAG.** A runtime graph is not registry-backed. There is no adapter.

Pre-reading: workflows/dags/gmp/graph.py, workflows/dags/inspect_dag.py""",
            outputs=["runtime_written"],
        ),
        SessionNode(
            id="validate_langgraph",
            name="Validate LangGraph Runtime",
            node_type=NodeType.VALIDATE,
            description="Prove the runtime graph shape before any runtime claim",
            action="""Validate the runtime graph. No runtime claim before this passes.

1. **Syntax check:**
```bash
python -m py_compile workflows/dags/<package>/graph.py
```

2. **Shape check (AST, graph.py only):**
```bash
python3 skills/l9-dag-authoring/scripts/validate_langgraph_source.py \\
    workflows/dags/<package>/graph.py
```
This proves the module imports langgraph, actually constructs the graph, and
carries no session-registry contamination. Contamination is detected from the
AST — an import of or call to the registry symbols — so a docstring that names
them to say they must not be used is documenting the boundary, not crossing it.

3. **Package durability check:**
```bash
python3 skills/l9-dag-authoring/scripts/validate_langgraph_source.py \\
    workflows/dags/<package>
```
PASS requires persistence_class=durable: executor compile(checkpointer=...)
with a non-MemorySaver and thread_id. graph.py must not call compile().
MemorySaver / missing saver is FAIL, not PARTIAL.

4. **Compile when the runtime is available:**
```bash
python -c "
from workflows.dags.<package>.executor import compile_graph
compile_graph()
print('compiled')
"
```
If langgraph is not installed, record PARTIAL — a non-local probe that cannot
execute is not a pass.

5. **Confirm every referenced node is bound and every conditional route target
   resolves.**

SUCCESS CRITERIA:
- py_compile passes
- structural validate(graph.py) returns PASS
- validate_package(dir) returns PASS with persistence_class=durable
- executor compiles with a durable checkpointer, or PARTIAL is recorded because
  langgraph is not installed""",
            outputs=["validation_passed"],
        ),
        SessionNode(
            id="gate_runtime_validation",
            name="Runtime Validation Passed?",
            node_type=NodeType.GATE,
            description="Check if LangGraph validation succeeded",
            action="If validation passed, prove the entrypoint. Otherwise fix the runtime.",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('validation_passed', False)",
        ),
        SessionNode(
            id="prove_runtime_entrypoint",
            name="Prove Runtime Entrypoint",
            node_type=NodeType.VALIDATE,
            description="Bind the runtime by proving builder and entrypoint are the same graph",
            action="""Bind a LANGGRAPH_RUNTIME graph by proof, not by registration.

For this kind, "binding" means: the canonical builder and the public
executor/runner entrypoint resolve to the same graph implementation.

1. **Identify the public entrypoint** — the function a caller actually invokes
   (for example run_inspect, or the domain executor in gmp/executor.py).

2. **Prove it reaches the canonical builder:**
```bash
python -c "
from workflows.dags.<runtime> import build_graph, run_<name>
import inspect
assert 'build_graph' in inspect.getsource(run_<name>)
print('entrypoint reaches canonical builder')
"
```
Read the source if the call is indirect. Do not assert linkage you did not see.

3. **Confirm no SessionDAG registration was created as a side effect:**
```bash
python -c "
import workflows.dags
from workflows.session.registry import get_session_dag
assert get_session_dag('<runtime-id>') is None
print('correctly absent from SessionDAG registry')
"
```

Absence from the SessionDAG registry is the correct state for this kind. Do not
"fix" it by registering.

SUCCESS CRITERIA:
- entrypoint and builder resolve to one graph
- graph is absent from the SessionDAG registry""",
            outputs=["runtime_bound"],
        ),
        # === PHASE 6: OPTIONAL COMMAND BIND (shared) ===
        SessionNode(
            id="gate_command_binding",
            name="Bind a Command?",
            node_type=NodeType.GATE,
            description="Command binding is optional",
            action="""Decide whether a slash command trigger is part of this deliverable.

Bind a command only when it was requested, or when the command already exists
and belongs to this workflow's owned public surface. Do not create one
speculatively.

A command-binding failure does not invalidate an otherwise valid graph unless
the command was the required deliverable.""",
            gate_type=GateType.USER_CONFIRM,
            validation="state.get('command_requested', False)",
        ),
        SessionNode(
            id="create_command_trigger",
            name="Create Thin Command Trigger",
            node_type=NodeType.TRANSFORM,
            description="Create or reduce the command to a trigger",
            action="""Create the slash command file as a MINIMAL TRIGGER.

CRITICAL: the command file is a trigger. NO detailed instructions.
   All instructions live in this graph's node action fields, or in the runtime
   code for a LANGGRAPH_RUNTIME graph.

TEMPLATE (commands/{command}.md):

```markdown
---
name: {command}
version: "1.0.0"
description: "One-line description"
auto_chain: ynp
dag: {graph-id}
dag_file: workflows/dags/{graph_file}.py
---

# /{command} — {Human Title}

Delegates to skill **`l9-dag-authoring`** / the owning domain skill.

## Usage

    /{command}                    # Default usage
    /{command} --option value     # With options

## EXECUTION

1. Read and follow the graph at `workflows/dags/{graph_file}.py`.
2. Follow each node's `action` field in sequence.

## Key Files

- **Graph**: `workflows/dags/{graph_file}.py`
```

RULES:
- `dag_file` points at `workflows/dags/*.py` — never `.cursor-commands/...`
- roughly 80 lines is the ceiling
- no phase-by-phase restatement of the workflow
- no second implementation of validation or registration behavior

VALIDATE the result:
```bash
python3 skills/l9-dag-authoring/scripts/validate_command_trigger.py \\
    commands/{command}.md {graph-id}
```

REGISTER the command in the manifest that is actually read:
- `commands/COMMANDS_MANIFEST.yaml` — the enabled slash -> file map, and the
  source of truth for what is active
- `commands/commands-index.md` — human quick reference

There is no `.cursor/rules/` directory in this repository; the projected rule
`rules/02-slash-commands.mdc` is regenerated from the manifest, not hand-edited.

Pre-reading: commands/dag-authoring.md (current thin-trigger example)""",
            outputs=["command_created", "command_registered"],
        ),
        # === END ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Graph authoring complete",
            action="""Graph authoring complete.

Emit a receipt:
```bash
python3 skills/l9-dag-authoring/scripts/render_receipt.py \\
    --operation CREATE --status PASS --dag-id <graph-id> \\
    --check structure --check registration --check discovery
```

Terminal state is PASS, PARTIAL, BLOCKED, or FAIL. Report PARTIAL rather than
PASS when a probe could not execute.""",
        ),
    ],
    edges=[
        # Classification comes first
        SessionEdge(from_node="start", to_node="classify_graph_kind"),
        SessionEdge(from_node="classify_graph_kind", to_node="gate_graph_kind"),
        SessionEdge(
            from_node="gate_graph_kind",
            to_node="blocked_unknown_kind",
            condition="unknown",
            label="UNKNOWN — blocked",
        ),
        SessionEdge(
            from_node="gate_graph_kind",
            to_node="analyze_workflow",
            condition="resolved",
            label="Kind resolved",
        ),
        # Shared analysis, then split by kind
        SessionEdge(
            from_node="analyze_workflow",
            to_node="design_structure",
            condition="session_guidance",
            label="SESSION_GUIDANCE",
        ),
        SessionEdge(
            from_node="analyze_workflow",
            to_node="design_runtime",
            condition="langgraph_runtime",
            label="LANGGRAPH_RUNTIME",
        ),
        # SESSION_GUIDANCE branch
        SessionEdge(from_node="design_structure", to_node="write_nodes"),
        SessionEdge(from_node="write_nodes", to_node="write_edges"),
        SessionEdge(from_node="write_edges", to_node="validate_session_dag"),
        SessionEdge(from_node="validate_session_dag", to_node="gate_session_validation"),
        SessionEdge(
            from_node="gate_session_validation",
            to_node="register_and_discover",
            condition="passed",
            label="Validation passed",
        ),
        SessionEdge(
            from_node="gate_session_validation",
            to_node="write_nodes",
            condition="failed",
            label="Fix issues",
        ),
        SessionEdge(from_node="register_and_discover", to_node="gate_command_binding"),
        # LANGGRAPH_RUNTIME branch
        SessionEdge(from_node="design_runtime", to_node="validate_langgraph"),
        SessionEdge(from_node="validate_langgraph", to_node="gate_runtime_validation"),
        SessionEdge(
            from_node="gate_runtime_validation",
            to_node="prove_runtime_entrypoint",
            condition="passed",
            label="Validation passed",
        ),
        SessionEdge(
            from_node="gate_runtime_validation",
            to_node="design_runtime",
            condition="failed",
            label="Fix runtime",
        ),
        SessionEdge(from_node="prove_runtime_entrypoint", to_node="gate_command_binding"),
        # Optional command binding, then exit
        SessionEdge(
            from_node="gate_command_binding",
            to_node="create_command_trigger",
            condition="yes",
            label="Command requested",
        ),
        SessionEdge(
            from_node="gate_command_binding",
            to_node="end",
            condition="no",
            label="No command",
        ),
        SessionEdge(from_node="create_command_trigger", to_node="end"),
    ],
)


# =============================================================================
# REGISTRATION
# =============================================================================


def register():
    """Register the DAG authoring graph (SESSION_GUIDANCE)."""
    register_session_dag(DAG_AUTHORING_DAG)


# Auto-register on import
register()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-026",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["operations", "testing", "utility", "workflows"],
    "keywords": [
        "action",
        "authoring",
        "between",
        "command",
        "create",
        "dag",
        "dags",
        "detailed",
    ],
    "business_value": (
        "This DAG enforces the proper pattern for creating and updating DAGs. DAGs "
        "contain ALL detailed instructions in node `action` fields Slash commands "
        "are MINIMAL TRIGGERS (~30 lines) NEVER duplicate inst"
    ),
    "last_modified": "2026-01-31T22:27:11Z",
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
