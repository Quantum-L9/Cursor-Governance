"""Executable declaration and session-registry binding for l9-skill-compiler v2.

The compiler owns its typed stage graph. Generic session discovery is owned by
Cursor-Governance's ``workflows.session`` registry and ``workflows.dags``
auto-discovery package. The logical graph remains machine-readable in
``NODES``/``SKILL_COMPILER_V2`` for compiler validation, while
``SKILL_COMPILER_SESSION_DAG`` binds the same graph into the repo's canonical
SessionDAG registry without inventing a parallel ACTIVE_DAGS mechanism.
"""

from __future__ import annotations

from workflows.session.interface import NodeType, SessionDAG, SessionEdge, SessionNode
from workflows.session.registry import register_session_dag

SCRIPTS = "skills/l9-skill-compiler/scripts"

NODES = [
    {
        "id": "COMPILE_REQUEST",
        "kind": "deterministic",
        "impl": "bind_and_validate_inputs",
        "exec": None,
        "next": ["BIND_INPUTS"],
    },
    {
        "id": "BIND_INPUTS",
        "kind": "deterministic",
        "impl": "bind_and_validate_inputs",
        "exec": SCRIPTS + "/bind_inputs.py",
        "args": ["request"],
        "writes": False,
        "next": ["SCAN_SKILL_TOPOLOGY"],
    },
    {
        "id": "SCAN_SKILL_TOPOLOGY",
        "kind": "deterministic",
        "impl": "enumerate_live_skill_topology",
        "exec": SCRIPTS + "/scan_skill_topology.py",
        "args": ["request", "skills_dir"],
        "writes": False,
        "next": ["TOPOLOGY_OWNERSHIP_JUDGMENT", "CLASSIFY_SKILL_PROFILE"],
    },
    {
        "id": "TOPOLOGY_OWNERSHIP_JUDGMENT",
        "kind": "bounded_llm",
        "impl": "ambiguous_topology_ownership_decision",
        "contract": "references/runtime-design-contract.md",
        "guard": "entered only when scan emits ESCALATE_TO_BOUNDED_LLM",
        "guard_when": {
            "stage": "SCAN_SKILL_TOPOLOGY",
            "field": "decision",
            "equals": "ESCALATE_TO_BOUNDED_LLM",
        },
        "next": ["CLASSIFY_SKILL_PROFILE"],
    },
    {
        "id": "CLASSIFY_SKILL_PROFILE",
        "kind": "deterministic",
        "impl": "deterministic_profile_rules",
        "exec": SCRIPTS + "/classify_skill_profile.py",
        "args": ["request"],
        "writes": False,
        "next": ["PROFILE_JUDGMENT", "EXTRACT_SOURCE_INTELLIGENCE"],
    },
    {
        "id": "PROFILE_JUDGMENT",
        "kind": "bounded_llm",
        "impl": "ambiguous_skill_profile_classification",
        "contract": "references/runtime-design-contract.md",
        "guard": "entered only when classification escalates",
        "guard_when": {
            "stage": "CLASSIFY_SKILL_PROFILE",
            "field": "status",
            "equals": "ESCALATE_TO_BOUNDED_LLM",
        },
        "next": ["EXTRACT_SOURCE_INTELLIGENCE"],
    },
    {
        "id": "EXTRACT_SOURCE_INTELLIGENCE",
        "kind": "bounded_llm",
        "impl": "source_intelligence_extraction",
        "contract": "references/source-intelligence-contract.md",
        "satisfied_by": "ir",
        "next": ["NORMALIZE_SKILL_IR"],
    },
    {
        "id": "NORMALIZE_SKILL_IR",
        "kind": "deterministic",
        "impl": "normalize_and_schema_validate_IR",
        "exec": SCRIPTS + "/normalize_skill_ir.py",
        "args": ["ir", "ir_out"],
        "writes": True,
        "next": ["DESIGN_RUNTIME"],
    },
    {
        "id": "DESIGN_RUNTIME",
        "kind": "bounded_llm",
        "impl": "semantic_runtime_design",
        "contract": "references/runtime-design-contract.md",
        "satisfied_by": "ir",
        "next": ["RENDER_TARGET_PROFILE"],
    },
    {
        "id": "RENDER_TARGET_PROFILE",
        "kind": "deterministic",
        "impl": "render_target_profiles",
        "exec": SCRIPTS + "/render_target_profile.py",
        "args": ["ir", "profile", "render_outdir"],
        "fan_out": "profile",
        "writes": True,
        "next": ["STATIC_VALIDATE"],
    },
    {
        "id": "STATIC_VALIDATE",
        "kind": "deterministic",
        "impl": "structural_and_static_validation",
        "exec": SCRIPTS + "/static_validate.py",
        "args": ["ir", "pack"],
        "writes": False,
        "next": ["CAPABILITY_CLOSURE"],
    },
    {
        "id": "CAPABILITY_CLOSURE",
        "kind": "deterministic",
        "impl": "capability_graph_resolution",
        "exec": SCRIPTS + "/check_capability_closure.py",
        "args": ["ir", "repo_root"],
        "writes": False,
        "next": ["ACTIVATION_EVAL"],
    },
    {
        "id": "ACTIVATION_EVAL",
        "kind": "deterministic",
        "impl": "activation_fixture_execution",
        "exec": SCRIPTS + "/evaluate_activation.py",
        "args": ["ir"],
        "writes": False,
        "next": ["BEHAVIOR_EVAL"],
    },
    {
        "id": "BEHAVIOR_EVAL",
        "kind": "bounded_llm",
        "impl": "family_specific_behavior_judgment_when_not_deterministically_testable",
        "contract": "references/evaluation-contract.md",
        "next": ["PACKAGE"],
    },
    {
        "id": "PACKAGE",
        "kind": "deterministic",
        "impl": "package_integrity",
        "exec": SCRIPTS + "/package_skill.py",
        "args": ["pack"],
        "writes": False,
        "next": ["HANDOFF_TO_WIRING"],
    },
    {
        "id": "HANDOFF_TO_WIRING",
        "kind": "deterministic",
        "impl": "build_receipt_generation",
        "exec": None,
        "delegates_to": ["l9-wire-skill-into-repo", "l9-dag-authoring"],
        "next": ["PASS_BLOCKED_FAIL"],
    },
    {
        "id": "PASS_BLOCKED_FAIL",
        "kind": "terminal",
        "impl": None,
        "next": [],
    },
]

# Symbolic stage-input tokens. A runner resolves each token from its own run
# context; the DAG owns which tokens a stage consumes so no runner has to carry
# per-stage invocation knowledge of its own.
ARG_TOKENS = {
    "request",
    "skills_dir",
    "ir",
    "ir_out",
    "profile",
    "render_outdir",
    "pack",
    "repo_root",
}

# Terminal-state mapping. The DAG is authoritative for terminal state, so every
# runner and operator surface resolves an outcome through this table instead of
# inventing its own success vocabulary. ``build_succeeded`` is deliberately
# false for DRY_RUN: a non-mutating plan is never a build.
TERMINAL_STATES = {
    "PASS": {"status": "PASS", "build_succeeded": True},
    "BLOCKED": {"status": "BLOCKED", "build_succeeded": False},
    "FAIL": {"status": "FAIL", "build_succeeded": False},
    "BOUNDED_LLM_REQUIRED": {"status": "BLOCKED", "build_succeeded": False},
    "DRY_RUN": {"status": "PASS", "build_succeeded": False},
}

SKILL_COMPILER_V2 = {
    "id": "skill-compiler-v2",
    "version": "2.0.0",
    "owner_skill": "l9-skill-compiler",
    "entrypoint": "COMPILE_REQUEST",
    "terminal": ["PASS_BLOCKED_FAIL"],
    "nodes": NODES,
}


def graph():
    return {node["id"]: node.get("next", []) for node in NODES}


def validate_graph():
    ids = {node["id"] for node in NODES}
    errors = []
    if SKILL_COMPILER_V2["entrypoint"] not in ids:
        errors.append("entrypoint does not resolve to a node")
    for node in NODES:
        for target in node.get("next", []):
            if target not in ids:
                errors.append(f"dangling edge {node['id']} -> {target}")
        if node["kind"] == "bounded_llm" and not node.get("contract"):
            errors.append(f"bounded_llm node {node['id']} has no contract")
        if node.get("exec"):
            if "args" not in node:
                errors.append(f"executable node {node['id']} declares no args")
            if "writes" not in node:
                errors.append(f"executable node {node['id']} does not declare writes")
        satisfied_by = node.get("satisfied_by")
        if satisfied_by is not None:
            if node["kind"] != "bounded_llm":
                errors.append(f"{node['id']}: satisfied_by is only valid on a bounded_llm node")
            if satisfied_by not in ARG_TOKENS:
                errors.append(f"{node['id']}: unknown satisfied_by token {satisfied_by}")
        if node.get("exec"):
            for token in node.get("args", []):
                if token not in ARG_TOKENS:
                    errors.append(f"{node['id']}: unknown arg token {token}")
            fan_out = node.get("fan_out")
            if fan_out is not None and fan_out not in node.get("args", []):
                errors.append(f"{node['id']}: fan_out {fan_out} is not one of its args")
        if node.get("guard") and not node.get("guard_when"):
            errors.append(f"guarded node {node['id']} has no machine-evaluable guard_when")
    for node in NODES:
        guard_when = node.get("guard_when")
        if guard_when and guard_when.get("stage") not in ids:
            errors.append(f"{node['id']}: guard_when stage does not resolve to a node")
    if not any(node["kind"] == "terminal" for node in NODES):
        errors.append("no terminal node")
    return errors


def _session_node_type(node):
    if node["id"] == SKILL_COMPILER_V2["entrypoint"]:
        return NodeType.START
    if node["kind"] == "terminal":
        return NodeType.END
    validation_nodes = {
        "STATIC_VALIDATE",
        "CAPABILITY_CLOSURE",
        "ACTIVATION_EVAL",
        "BEHAVIOR_EVAL",
    }
    if node["id"] in validation_nodes:
        return NodeType.VALIDATE
    if node["kind"] == "bounded_llm":
        return NodeType.ANALYZE
    return NodeType.TRANSFORM


def _session_action(node):
    if node.get("exec"):
        return (
            "Execute this stage deterministically via `python "
            + node["exec"]
            + "` using the bound stage inputs. Do not substitute prose execution "
            "for the executable."
        )
    if node.get("contract"):
        return (
            "Execute only the bounded semantic operation `"
            + node["impl"]
            + "` under `skills/l9-skill-compiler/"
            + node["contract"]
            + "`. Emit only contract-conforming output."
        )
    if node.get("delegates_to"):
        return (
            "Emit the typed build/wiring handoff receipt, then delegate registry/discovery "
            "work to "
            + ", ".join(node["delegates_to"])
            + ". This node does not invent or mutate foreign registries directly."
        )
    if node["kind"] == "terminal":
        return (
            "Resolve the run to PASS, BLOCKED, or FAIL from machine receipts; material "
            "UNKNOWN blocks success."
        )
    return "Bind and validate the compile request against the compiler contracts before advancing."


SESSION_NODES = [
    SessionNode(
        id=node["id"],
        name=node["id"].replace("_", " ").title(),
        node_type=_session_node_type(node),
        description=node.get("impl") or "terminal compiler state",
        action=_session_action(node),
        metadata={
            "kind": node["kind"],
            "exec": node.get("exec"),
            "contract": node.get("contract"),
            "guard": node.get("guard"),
            "guard_when": node.get("guard_when"),
            "satisfied_by": node.get("satisfied_by"),
            "args": node.get("args"),
            "fan_out": node.get("fan_out"),
            "writes": node.get("writes"),
            "delegates_to": node.get("delegates_to", []),
        },
    )
    for node in NODES
]

SESSION_EDGES = [
    SessionEdge(from_node=node["id"], to_node=target)
    for node in NODES
    for target in node.get("next", [])
]

SKILL_COMPILER_SESSION_DAG = SessionDAG(
    id="skill-compiler-v2",
    name="L9 Skill Compiler v2",
    version="2.0.0",
    description=(
        "Repository-bound session discovery adapter for the l9-skill-compiler v2 typed graph. "
        "The compiler's NODES graph remains canonical; this adapter makes the same graph "
        "discoverable through Cursor-Governance's existing SessionDAG registry."
    ),
    nodes=SESSION_NODES,
    edges=SESSION_EDGES,
    entry_node="COMPILE_REQUEST",
    tags=["skill", "compiler", "capability-closure", "dag"],
    metadata={"owner_skill": "l9-skill-compiler", "graph_constant": "SKILL_COMPILER_V2"},
)


def register():
    """Register the compiler in Cursor-Governance's canonical session registry."""
    errors = validate_graph() + SKILL_COMPILER_SESSION_DAG.validate()
    if errors:
        raise ValueError(f"skill-compiler-v2 DAG validation failed: {errors}")
    register_session_dag(SKILL_COMPILER_SESSION_DAG)


register()
