"""
Plan-Simple → Improve → Validate & Repair → Build/GMP
=====================================================

SESSION_GUIDANCE composition graph. Domain owners stay with their packs:

- planning: skill ``l9-plan-simple`` (``/l9-plan-simple``)
- improve: ``kernels/Improve.md``
- repair: ``kernels/Validate & Repair.md``
- execute: ``kernels/Build.md`` wrapped by slash ``/gmp``
  (``workflows/gmp_executor.py``)

This module does not own those semantics. Node ``action`` values are repo
paths the agent must Read/run — not a restatement of kernel or GMP phases.

Registry id: ``plan-simple-build-v1``
"""

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

PLAN_SIMPLE_BUILD_NODES = [
    SessionNode(
        id="start",
        name="Start",
        node_type=NodeType.START,
        description="Entry: bind the user objective as the authorized target",
        action="commands/l9-plan-build.md",
        metadata={"ir_kind": "terminal", "domain_owner": "l9-dag-authoring"},
    ),
    SessionNode(
        id="plan_simple",
        name="Plan via l9-plan-simple",
        node_type=NodeType.ANALYZE,
        description="Produce PLAN_DOCUMENT JSON and a kind:simple .plan.md",
        action="skills/l9-plan-simple/SKILL.md",
        outputs=["plan_json", "plan_md"],
        metadata={
            "ir_kind": "bounded_llm",
            "domain_owner": "l9-plan-simple",
            "also_read": [
                "skills/l9-plan-simple/references/plan-workflow-simple.md",
                "skills/l9-plan/scripts/validate_plan_document.py",
                "skills/l9-plan/scripts/render_plan_pe_autonomy.py",
            ],
        },
    ),
    SessionNode(
        id="validate_plan",
        name="Validate PLAN_DOCUMENT",
        node_type=NodeType.VALIDATE,
        description="Fail-closed schema/depth gate on the plan JSON",
        action="skills/l9-plan/scripts/validate_plan_document.py",
        validation="PLAN_DOCUMENT validator exits 0",
        outputs=["plan_valid"],
        metadata={"ir_kind": "deterministic", "domain_owner": "l9-plan"},
    ),
    SessionNode(
        id="gate_plan",
        name="Plan ready?",
        node_type=NodeType.GATE,
        description="PASS only when JSON validates and the .plan.md is kind:simple",
        action="skills/l9-plan/scripts/validate_plan_document.py",
        gate_type=GateType.CONDITIONAL,
        validation="state.get('plan_valid') is True",
        metadata={"ir_kind": "deterministic", "domain_owner": "l9-plan"},
    ),
    SessionNode(
        id="improve",
        name="Improve kernel",
        node_type=NodeType.TRANSFORM,
        description="Apply Improve to the bound .plan.md; stamp kernel_pass.improve",
        action="kernels/Improve.md",
        outputs=["improve_deltas"],
        metadata={"ir_kind": "bounded_llm", "domain_owner": "kernels/Improve.md"},
    ),
    SessionNode(
        id="validate_repair",
        name="Validate & Repair kernel",
        node_type=NodeType.TRANSFORM,
        description="Apply V&R independently after Improve; stamp kernel_pass.validate_repair",
        action="kernels/Validate & Repair.md",
        outputs=["repair_deltas"],
        metadata={
            "ir_kind": "bounded_llm",
            "domain_owner": "kernels/Validate & Repair.md",
        },
    ),
    SessionNode(
        id="kernel_receipt",
        name="Kernel receipt",
        node_type=NodeType.VALIDATE,
        description="Hashed Improve-then-V&R receipt must PASS on the bound plan",
        action="skills/l9-plan/scripts/validate_plan_kernel_receipt.py",
        validation="validate_plan_kernel_receipt.py exits 0",
        outputs=["kernel_pass"],
        metadata={"ir_kind": "deterministic", "domain_owner": "l9-plan"},
    ),
    SessionNode(
        id="gate_kernel",
        name="Kernel receipt PASS?",
        node_type=NodeType.GATE,
        description="Refuse Build/GMP until the plan kernel receipt PASSes",
        action="skills/l9-plan/scripts/validate_plan_kernel_receipt.py",
        gate_type=GateType.CONDITIONAL,
        validation="state.get('kernel_pass') is True",
        metadata={"ir_kind": "deterministic", "domain_owner": "l9-plan"},
    ),
    SessionNode(
        id="gmp_start",
        name="GMP start",
        node_type=NodeType.TRANSFORM,
        description="Authorize and start GMP against the bound plan (slash semantics)",
        action="workflows/gmp_executor.py",
        outputs=["gmp_started"],
        metadata={
            "ir_kind": "deterministic",
            "domain_owner": "l9-gmp-protocol",
            "argv": [
                "--authorized-by",
                "slash-gmp",
                "--mode",
                "start",
                "--plan",
                "<resolved.plan.md>",
                "<task>",
            ],
            "also_read": ["commands/gmp.md", "skills/l9-gmp-protocol/SKILL.md"],
        },
    ),
    SessionNode(
        id="build",
        name="Build the plan",
        node_type=NodeType.TRANSFORM,
        description="Execute the bound plan in this turn (Cursor Build; no PE campaign)",
        action="skills/l9-plan-simple/references/plan-workflow-simple.md",
        outputs=["build_artifacts"],
        metadata={
            "ir_kind": "bounded_llm",
            "domain_owner": "l9-plan-simple",
            "execute_via": "cursor-build",
            "intended_kernel": "kernels/Build.md",
        },
    ),
    SessionNode(
        id="gmp_finalize",
        name="GMP finalize",
        node_type=NodeType.TRANSFORM,
        description="Finalize the GMP run after Build (commit-when-done is surface-split)",
        action="workflows/gmp_executor.py",
        outputs=["gmp_finalized"],
        metadata={
            "ir_kind": "deterministic",
            "domain_owner": "l9-gmp-protocol",
            "argv": ["--resume", "--mode", "finalize", "--commit-when-done"],
        },
    ),
    SessionNode(
        id="gate_execute",
        name="Execute complete?",
        node_type=NodeType.GATE,
        description="PASS only when Build and GMP finalize both report success",
        action="skills/l9-gmp-protocol/SKILL.md",
        gate_type=GateType.CONDITIONAL,
        validation="state.get('gmp_finalized') is True",
        metadata={"ir_kind": "deterministic", "domain_owner": "l9-gmp-protocol"},
    ),
    SessionNode(
        id="PASS",
        name="Pass",
        node_type=NodeType.END,
        description="Plan hardened and executed via Build/GMP",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal"},
    ),
    SessionNode(
        id="BLOCKED",
        name="Blocked",
        node_type=NodeType.END,
        description="Missing inputs or an unresolved gate; do not fabricate",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal"},
    ),
    SessionNode(
        id="FAIL",
        name="Fail",
        node_type=NodeType.END,
        description="Execute failed after kernels; do not claim success",
        action="terminal state; no action",
        metadata={"ir_kind": "terminal"},
    ),
]

PLAN_SIMPLE_BUILD_EDGES = [
    SessionEdge(from_node="start", to_node="plan_simple"),
    SessionEdge(from_node="plan_simple", to_node="validate_plan"),
    SessionEdge(from_node="validate_plan", to_node="gate_plan"),
    SessionEdge(
        from_node="gate_plan",
        to_node="improve",
        condition="passed",
        label="Plan valid",
    ),
    SessionEdge(
        from_node="gate_plan",
        to_node="plan_simple",
        condition="failed",
        label="Fix plan",
    ),
    SessionEdge(
        from_node="gate_plan",
        to_node="BLOCKED",
        condition="blocked",
        label="Cannot plan",
    ),
    SessionEdge(from_node="improve", to_node="validate_repair"),
    SessionEdge(from_node="validate_repair", to_node="kernel_receipt"),
    SessionEdge(from_node="kernel_receipt", to_node="gate_kernel"),
    SessionEdge(
        from_node="gate_kernel",
        to_node="gmp_start",
        condition="passed",
        label="Kernel receipt PASS",
    ),
    SessionEdge(
        from_node="gate_kernel",
        to_node="improve",
        condition="failed",
        label="Re-run kernels",
    ),
    SessionEdge(
        from_node="gate_kernel",
        to_node="BLOCKED",
        condition="blocked",
        label="Cannot stamp receipt",
    ),
    SessionEdge(from_node="gmp_start", to_node="build"),
    SessionEdge(from_node="build", to_node="gmp_finalize"),
    SessionEdge(from_node="gmp_finalize", to_node="gate_execute"),
    SessionEdge(
        from_node="gate_execute",
        to_node="PASS",
        condition="passed",
        label="Build/GMP complete",
    ),
    SessionEdge(
        from_node="gate_execute",
        to_node="validate_repair",
        condition="failed",
        label="Repair then retry",
    ),
    SessionEdge(
        from_node="gate_execute",
        to_node="FAIL",
        condition="abort",
        label="Abort execute",
    ),
]

PLAN_SIMPLE_BUILD_DAG = SessionDAG(
    id="plan-simple-build-v1",
    name="Plan-Simple Build/GMP Workflow",
    version="1.0.0",
    description=(
        "Compose /l9-plan-simple, kernels/Improve.md, then kernels/Validate & "
        "Repair.md, and execute the hardened plan via Cursor Build under /gmp. "
        "Domain packs own semantics; this graph owns ordering only."
    ),
    nodes=PLAN_SIMPLE_BUILD_NODES,
    edges=PLAN_SIMPLE_BUILD_EDGES,
    entry_node="start",
    tags=["l9", "plan-simple", "improve", "validate-repair", "build", "gmp"],
    metadata={
        "skill": "l9-dag-authoring",
        "command": "/l9-plan-build",
        "execute_via": "cursor-build-gmp",
        "domain_owners": [
            "l9-plan-simple",
            "kernels/Improve.md",
            "kernels/Validate & Repair.md",
            "l9-gmp-protocol",
        ],
    },
)

_errors = PLAN_SIMPLE_BUILD_DAG.validate()
if _errors:
    raise ValueError(f"plan-simple-build-v1 DAG validation failed: {_errors}")

register_session_dag(PLAN_SIMPLE_BUILD_DAG)
