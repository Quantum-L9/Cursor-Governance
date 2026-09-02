"""Program Synthesizer: INTENT_RESOLUTION -> validator-clean Blueprint v2 (contract §9-§13)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from peer_execution.imports import load_module

from .mission_admission import validate_mission_context

MODULE_ROOT = Path(__file__).resolve().parent
PE_ROOT = MODULE_ROOT.parent
TEMPLATE_ROOT = PE_ROOT / "core" / "program-execution-blueprint-template"

from .prohibition_kind import entry as prohibition_entry

#: The official Blueprint template renderer (contract §17 reuse), bound by FILE
#: LOCATION under a name Program Execution owns. `instantiate` is not a name
#: this module may claim: the controller template ships its own
#: `scripts/instantiate.py` with the same basename and a different contract
#: (no `render_tree`), and both template `scripts/` directories get prepended
#: to the import path by different callers, so a bare `import instantiate`
#: bound whichever renderer happened to be imported first in the process.
BLUEPRINT_RENDERER_MODULE = "pe_blueprint_instantiate"
instantiate = load_module(TEMPLATE_ROOT / "scripts" / "instantiate.py", BLUEPRINT_RENDERER_MODULE)

#: Emitted only for a Mission-bound resolution. Not MISSION_BINDING.yaml: that
#: names blueprint_digest and may never live inside the Blueprint (ADR-0026).
MISSION_CONTEXT_FILENAME = "MISSION_CONTEXT.yaml"

AUTH_ACTIONS = (
    "inspect",
    "local_write",
    "commit",
    "push",
    "pull_request",
    "merge",
    "publish_or_release",
    "deploy_or_migrate",
    "destructive_change",
    "external_message",
)

RUNTIME_KEYS = {
    "attempts",
    "attempt_receipts",
    "verification_receipts",
    "gate_results",
    "lease",
    "leases",
    "recovery_state",
    "handoff_receipts",
    "runtime_status",
}


class RuntimeContaminationError(ValueError):
    """The synthesizer was asked to emit Controller runtime state (contract §3, §21)."""


def synthesize(resolution: dict[str, Any], output_root: Path, now: datetime | None = None) -> Path:
    """Render a complete Program Execution Blueprint v2 from a resolution artifact.

    Design-time definitions only. Any attempt to inject Controller runtime
    state (attempts, gate results, leases, receipts) is rejected.
    """
    now = now or datetime.now(UTC)
    _reject_runtime_state(resolution)
    output_root = output_root.resolve()
    if output_root.exists():
        raise SystemExit(f"target already exists: {output_root}")

    meta = resolution.get("_compiler_meta") or {}
    program = _program(resolution, meta, now)
    variables = {
        "PROGRAM_NAME": program["program"]["name"],
        "PROGRAM_ID": program["program"]["id"],
        "PROGRAM_VERSION": program["program"]["version"],
        "PROGRAM_OWNER": program["program"]["owner"],
        "DATE": program["program"]["snapshot_at"],
    }
    instantiate.render_tree(output_root, variables)

    artifacts = _artifacts(resolution, meta, program, now)
    for name, payload in artifacts.items():
        path = output_root / f"{name}.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False, width=110), encoding="utf-8")
    for name, text in _markdown_overrides(program).items():
        (output_root / f"{name}.md").write_text(text, encoding="utf-8")

    _write_mission_context(resolution, output_root)

    instantiate.write_manifest(output_root)
    return output_root


def _write_mission_context(resolution: dict[str, Any], output_root: Path) -> Path | None:
    """Emit the minimal Mission projection, before the manifest is finalized.

    Ordering is the point. ``write_manifest`` inventories every Blueprint file
    but its own, so a context written after it would be a Blueprint file the
    manifest does not cover — the official validator rejects that, and the
    Mission projection would sit outside the identity it is meant to be part of.

    Unbound synthesis emits nothing and behaves exactly as before.
    """
    context = resolution.get("mission_context")
    if context is None:
        return None
    # Re-validated here rather than trusted: the synthesizer writes into the
    # digest domain, so anything that reached this resolution by another path
    # must still be exactly the four-field projection.
    payload = validate_mission_context(dict(context))
    path = output_root / MISSION_CONTEXT_FILENAME
    path.write_text(yaml.safe_dump(payload, sort_keys=False, width=110), encoding="utf-8")
    return path


def _reject_runtime_state(resolution: dict[str, Any]) -> None:
    def walk(node: Any, trail: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in RUNTIME_KEYS:
                    raise RuntimeContaminationError(
                        "Controller runtime state is forbidden in compiler artifacts: "
                        f"{trail}.{key}"
                    )
                walk(value, f"{trail}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}[{index}]")

    walk(resolution, "resolution")


def _program(resolution: dict[str, Any], meta: dict[str, Any], now: datetime) -> dict[str, Any]:
    intent = resolution["intent"]
    program_id = "pe-" + intent["id"].replace("INTENT-", "").lower()
    owner = meta.get("owner") or "UNRESOLVED_PENDING_DECISION"
    snapshot = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema": "program-execution-blueprint.program.v2",
        "schema_version": "2.0.0",
        "program": {
            "id": program_id,
            "name": _program_name(intent["normalized_objective"]),
            "version": "1.0.0",
            "owner": owner,
            # A compiler produces a draft. Acceptance is `accept_blueprint`'s
            # decision, taken against bound evidence and recorded in an
            # ACCEPTANCE_RECEIPT; a compiler that stamped `accepted` here
            # accepted its own output with no evidence and no receipt.
            "definition_status": "draft",
            "snapshot_at": snapshot,
            "objective": intent["normalized_objective"],
            "problem_statement": (
                f"Minimal user goal requires authoritative compilation into a "
                f"validator-clean program: {intent['normalized_objective']}"
            ),
            "target_state": "Program synthesized, officially validated, and prepared for lock.",
            "scope": {
                "include": _scope_include(resolution),
                "exclude": [
                    "Controller runtime state",
                    "attempt or gate result mutation",
                    "authority widening beyond the active policy ceiling",
                ],
            },
            "contracts": {
                "blueprint": "program-execution-blueprint.v2",
                "controller_minimum": "program-execution-controller.v2",
                "pair": "program-execution-system.v2",
            },
            "authority_order": [
                "applicable_safety_legal_security_requirements",
                "latest_accepted_program_decision",
                "accepted_architecture_and_contracts",
                "verified_current_state_evidence",
                "approved_task_card",
                "implementation",
                "documentation",
                "historical_material",
                "UNKNOWN",
            ],
            "operating_rules": [
                "one_authority_per_responsibility",
                "controller_may_narrow_never_widen",
                "unknown_blocks_only_named_dependencies",
                "promotion_requires_evidence_backed_gates",
                "no_silent_scope_expansion",
                "no_irreversible_action_without_exact_authority",
                "worker_claim_is_not_verification",
            ],
            "terminal_verdicts": [
                "CONVERGED",
                "CONVERGED_WITH_NON_BLOCKING_RISKS",
                "NOT_CONVERGED",
                "INCONCLUSIVE",
            ],
        },
    }


def _program_name(objective: str) -> str:
    words = objective.split()[:8]
    return " ".join(words) + ("..." if len(objective.split()) > 8 else "")


def _scope_include(resolution: dict[str, Any]) -> list[str]:
    includes = []
    for req in resolution.get("derived_requirements") or []:
        includes.append(req["statement"])
    targets = resolution.get("targets") or []
    for target in targets:
        includes.append(f"Repository target: {target['repository_id']}")
    return includes


def _artifacts(
    resolution: dict[str, Any],
    meta: dict[str, Any],
    program: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    unknowns = resolution.get("unknowns") or []
    requires_human = resolution.get("decisions", {}).get("requires_human_authority") or []
    requirements = resolution.get("derived_requirements") or []
    profile = resolution["governing_authority"]["policy_profile"]
    snapshot = program["program"]["snapshot_at"]
    owner = program["program"]["owner"]
    ceiling = meta.get("ceiling") or {}
    test_command = meta.get("test_command")
    revision = meta.get("target_revision") or "UNKNOWN"

    req_task_ids = [f"TASK-{index + 2:03d}" for index in range(len(requirements))]
    validation_task_id = f"TASK-{len(requirements) + 2:03d}"
    verification_task_id = f"TASK-{len(requirements) + 3:03d}"
    w1_task_ids = req_task_ids + [validation_task_id]
    w2_task_ids = [verification_task_id]
    all_task_ids = ["TASK-001", *req_task_ids, validation_task_id, verification_task_id]

    tasks = [_task_001(owner)]
    for task_id, req in zip(req_task_ids, requirements):
        tasks.append(_implementation_task(task_id, req, ceiling, profile, test_command))
    if test_command:
        tasks.append(_validation_task(validation_task_id, test_command, ceiling, req_task_ids))
    tasks.append(_verification_task(verification_task_id, ceiling, w1_task_ids))

    decisions = _decisions(profile, requires_human, owner, all_task_ids)

    return {
        "PROGRAM": program,
        "EXECUTION_TARGETS": _targets(resolution, meta),
        "AUTHORITY_REGISTRY": _authority_registry(owner),
        "DECISION_REGISTER": decisions,
        "UNKNOWN_REGISTER": _unknowns(unknowns, all_task_ids),
        "RISK_REGISTER": _risks(all_task_ids),
        "WAIVER_REGISTER": _waivers(),
        "EVIDENCE_CATALOG": _evidence(revision, owner, snapshot),
        "DO_NOT_BUILD": _do_not_build(),
        "CURRENT_STATE_DELTA": _current_state_delta(revision, snapshot),
        "WORKSTREAMS": _workstreams(),
        "DEPENDENCY_GRAPH": _graph(req_task_ids, w1_task_ids, w2_task_ids),
        "EXECUTION_WAVES": _waves(w1_task_ids, w2_task_ids),
        "TASK_CARDS": {
            "schema": "program-execution-blueprint.task-cards.v2",
            "schema_version": "2.0.0",
            "tasks": tasks,
        },
        "CONVERGENCE_GATES": _gates(owner, w1_task_ids, w2_task_ids),
        "PHASE0_USER_CONFIG": _phase0(owner),
        "OBSERVABILITY_PLAN": _observability(owner),
        "CUTOVER_AND_ROLLBACK": _cutover_rollback(owner),
        "SOURCE_TRACEABILITY": _traceability(resolution, all_task_ids),
    }


def _task_001(owner: str) -> dict[str, Any]:
    return {
        "id": "TASK-001",
        "title": "Refresh and lock current state",
        "definition_status": "ready",
        "workstream_id": "WS-01",
        "wave_id": "W0",
        "target_id": "TARGET-001",
        "execution_kind": "program_control",
        "objective": "Produce current evidence and resolve the authority lock.",
        "authority_basis_ids": ["AUTH-001"],
        "required_decision_ids": [],
        "blocking_unknown_ids": [],
        "input_evidence_ids": ["EVID-001"],
        "actions": [
            "refresh_current_state",
            "resolve_blocking_decisions",
            "approve_authority_registry",
        ],
        "outputs": [
            {
                "id": "OUT-001",
                "type": "evidence",
                "location": "CURRENT_STATE_DELTA.yaml",
                "required": True,
            }
        ],
        "acceptance": [
            {
                "id": "AC-001",
                "statement": "Current-state evidence is fresh and authority conflicts are absent.",
                "required_evidence_types": ["inspection"],
            }
        ],
        "validation": [
            {
                "id": "VAL-001",
                "method": "inspection",
                "command_or_inspection": "Inspect registers and source revisions.",
                "environment": "planning",
                "expected_result": "PASS",
            }
        ],
        "negative_cases": ["stale evidence", "duplicate authority"],
        "rollback": {
            "strategy": "discard_unaccepted_planning_changes",
            "trigger": "authority_lock_failure",
            "validation": "Blueprint remains at prior accepted revision.",
        },
        "risk": {
            "tier": "T0",
            "reversibility": "fully_reversible",
            "blast_radius": "program_definition",
        },
        "authorization_ceiling": {action: False for action in AUTH_ACTIONS} | {"inspect": True},
        "completion_gate_ids": ["GATE-001"],
    }


def _implementation_task(
    task_id: str,
    req: dict[str, Any],
    ceiling: dict[str, bool],
    profile: str,
    test_command: str | None = None,
) -> dict[str, Any]:
    statement = req["statement"]
    # The validation is repository truth or an inspection; never an invented
    # shell command the repository cannot run.
    validation = (
        {
            "id": f"VAL-{task_id}",
            "method": "command",
            "command_or_inspection": test_command,
            "environment": "local",
            "expected_result": "PASS",
        }
        if test_command
        else {
            "id": f"VAL-{task_id}",
            "method": "inspection",
            "command_or_inspection": (
                f"No repository test command was resolved; inspect the durable output for "
                f"{req['id']} and its evidence by hand."
            ),
            "environment": "local",
            "expected_result": "PASS",
        }
    )
    return {
        "id": task_id,
        "title": statement[:80],
        "definition_status": "ready",
        "workstream_id": "WS-02",
        "wave_id": "W1",
        "target_id": "TARGET-001",
        "execution_kind": "repo_local",
        "objective": statement,
        "authority_basis_ids": ["AUTH-001"],
        "required_decision_ids": [],
        "blocking_unknown_ids": [],
        "input_evidence_ids": ["EVID-001"],
        "actions": [f"implement_{task_id.lower()}"],
        "outputs": [
            {
                "id": f"OUT-{task_id}",
                "type": "artifact",
                "location": f"durable output for {req['id']}",
                "required": True,
            }
        ],
        "acceptance": [
            {
                "id": f"AC-{task_id}",
                "statement": f"{req['id']} is satisfied with verifiable evidence.",
                "required_evidence_types": ["test_result"],
            }
        ],
        "validation": [validation],
        "negative_cases": ["validation fails", "evidence missing"],
        "rollback": {
            "strategy": "git restore of the scoped change",
            "trigger": "validation_failure_or_cutover_abort",
            "validation": "Working tree returns to the pre-task revision.",
        },
        "risk": {"tier": "T2", "reversibility": "reversible", "blast_radius": "single_target"},
        "authorization_ceiling": {
            action: bool(ceiling.get(action, False)) for action in AUTH_ACTIONS
        },
        "completion_gate_ids": ["GATE-002"],
    }


def _validation_task(
    task_id: str, test_command: str, ceiling: dict[str, bool], predecessors: list[str]
) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": "Run declared repository validation",
        "definition_status": "ready",
        "workstream_id": "WS-03",
        "wave_id": "W1",
        "target_id": "TARGET-001",
        "execution_kind": "repo_local",
        "objective": f"Execute the repository-declared validation command: {test_command}",
        "authority_basis_ids": ["AUTH-001"],
        "required_decision_ids": [],
        "blocking_unknown_ids": [],
        "input_evidence_ids": ["EVID-001"],
        "actions": ["run_declared_validation"],
        "outputs": [
            {
                "id": f"OUT-{task_id}",
                "type": "evidence",
                "location": "validation log",
                "required": True,
            }
        ],
        "acceptance": [
            {
                "id": f"AC-{task_id}",
                "statement": f"Command `{test_command}` exits zero.",
                "required_evidence_types": ["command_execution"],
            }
        ],
        "validation": [
            {
                "id": f"VAL-{task_id}",
                "method": "command",
                "command_or_inspection": test_command,
                "environment": "local",
                "expected_result": "PASS",
            }
        ],
        "negative_cases": ["command exits non-zero", "command unavailable"],
        "rollback": {
            "strategy": "no mutation performed by this validation task",
            "trigger": "validation_failure",
            "validation": "Tree unchanged by the validation task itself.",
        },
        "risk": {"tier": "T0", "reversibility": "fully_reversible", "blast_radius": "none"},
        "authorization_ceiling": {
            action: bool(ceiling.get(action, False)) for action in AUTH_ACTIONS
        },
        "completion_gate_ids": ["GATE-002"],
    }


def _verification_task(
    task_id: str, ceiling: dict[str, bool], predecessors: list[str]
) -> dict[str, Any]:
    return {
        "id": task_id,
        "title": "Independent verification and handoff preparation",
        "definition_status": "ready",
        "workstream_id": "WS-03",
        "wave_id": "W2",
        "target_id": "TARGET-001",
        "execution_kind": "repo_local",
        "objective": (
            "Verify the produced evidence independently of the producing tasks and prepare handoff."
        ),
        "authority_basis_ids": ["AUTH-001"],
        "required_decision_ids": [],
        "blocking_unknown_ids": [],
        "input_evidence_ids": ["EVID-001"],
        "actions": ["independent_verification", "prepare_handoff"],
        "outputs": [
            {
                "id": f"OUT-{task_id}",
                "type": "evidence",
                "location": "verification receipt",
                "required": True,
            }
        ],
        "acceptance": [
            {
                "id": f"AC-{task_id}",
                "statement": (
                    "Independent verification evidence exists and worker claims "
                    "were not treated as verification."
                ),
                "required_evidence_types": ["test_result", "contract_validation"],
            }
        ],
        "validation": [
            {
                "id": f"VAL-{task_id}",
                "method": "inspection",
                "command_or_inspection": (
                    "Inspect verification receipts independently of the generation path."
                ),
                "environment": "planning",
                "expected_result": "PASS",
            }
        ],
        "negative_cases": ["self-verification only", "missing receipt"],
        "rollback": {
            "strategy": "discard_unaccepted_planning_changes",
            "trigger": "verification_failure",
            "validation": "Program remains at prior accepted revision.",
        },
        "risk": {
            "tier": "T0",
            "reversibility": "fully_reversible",
            "blast_radius": "program_definition",
        },
        "authorization_ceiling": {
            action: bool(ceiling.get(action, False)) for action in AUTH_ACTIONS
        },
        "completion_gate_ids": ["GATE-003"],
    }


def _targets(resolution: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    # The resolver already resolved the target repository (from the intent or
    # the checkout's git remote, with evidence). Re-deriving it here from the
    # local filesystem path invented ids: a hard-coded "Quantum-L9/Cursor-
    # Governance" for any path containing "Quantum-L9", a bare absolute path
    # otherwise.
    targets = resolution.get("targets") or []
    repository_id = str((targets[0] if targets else {}).get("repository_id") or "").strip()
    if not repository_id:
        raise ValueError("resolution declares no target repository_id; cannot synthesize targets")
    return {
        "schema": "program-execution-blueprint.execution-targets.v2",
        "schema_version": "2.0.0",
        "targets": [
            {
                "id": "TARGET-001",
                "name": repository_id,
                "kind": "git_repository",
                "authority_owner": "program_owner",
                "execution_mode": "repo_local",
                "repository_id": repository_id,
                "source_of_truth": str(meta.get("target_root") or "repository"),
                "environments": ["local"],
                "mutability": "reversible",
                "expected_revision": meta.get("target_revision") or "UNKNOWN",
                "adapter": "git",
            }
        ],
    }


def _authority_registry(owner: str) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.authority-registry.v2",
        "schema_version": "2.0.0",
        "policy": {
            "one_owner_per_responsibility": True,
            "projection_does_not_transfer_authority": True,
            "unresolved_conflict_result": "BLOCKED",
        },
        "responsibilities": [
            {
                "id": "AUTH-001",
                "responsibility": (
                    "Program definition and authorization ceiling for this compiled program"
                ),
                "owner_target_id": "TARGET-001",
                "source_of_truth": "PROGRAM.yaml plus governing policy profile",
                "consumers": ["Program Execution Controller", "worker adapters"],
                "allowed_roles": ["authority", "proposal_source", "projection", "cache", "display"],
                "prohibited_owner_target_ids": [],
                "enforcement": [
                    "official Blueprint validation",
                    "authorization ceiling on every task card",
                ],
                "validation_gate_ids": ["GATE-001"],
                "definition_status": "active",
            }
        ],
    }


def _decisions(
    profile: str,
    requires_human: list[str],
    owner: str,
    task_ids: list[str],
) -> dict[str, Any]:
    decisions = [
        {
            "id": "DEC-001",
            "question": "Which policy profile and placement govern this program?",
            "status": "accepted",
            "owner": owner,
            "options": [
                {
                    "id": "A",
                    "description": f"Use profile {profile} as resolved from active policy.",
                    "benefits": ["provenance recorded", "no invented authority"],
                    "risks": ["profile must not widen over time"],
                },
                {
                    "id": "B",
                    "description": "Adopt a different profile requiring explicit owner authority.",
                    "benefits": ["owner control"],
                    "risks": ["stalls dependent work"],
                },
            ],
            "selected_option": "A",
            "rationale": "Policy-determined resolution with recorded provenance.",
            "evidence_ids": ["EVID-001"],
            "blocks": [],
            "required_by": "UNKNOWN",
            "supersedes": None,
        }
    ]
    for index, label in enumerate(requires_human):
        decisions.append(
            {
                "id": label,
                "question": f"Authority-bearing item {label} requires owner input.",
                "status": "pending",
                "owner": owner,
                "options": [
                    {
                        "id": "A",
                        "description": "Accept the proposed resolution.",
                        "benefits": [],
                        "risks": [],
                    },
                    {"id": "B", "description": "Reject and re-scope.", "benefits": [], "risks": []},
                ],
                "selected_option": None,
                "rationale": None,
                "evidence_ids": [],
                "blocks": [task_ids[1]] if len(task_ids) > 1 else [],
                "required_by": "UNKNOWN",
                "supersedes": None,
            }
        )
    return {
        "schema": "program-execution-blueprint.decision-register.v2",
        "schema_version": "2.0.0",
        "policy": "No blocked decision may be silently defaulted.",
        "decisions": decisions,
    }


def _unknowns(unknowns: list[dict[str, Any]], task_ids: list[str]) -> dict[str, Any]:
    mapped = []
    for unknown in unknowns:
        blocks = [b for b in unknown.get("blocks") or [] if b in task_ids]
        mapped.append(
            {
                "id": unknown["id"],
                "topic": unknown["topic"],
                "owner": "program_owner",
                "blocks": blocks,
                "safe_state": unknown.get("safe_state", "Do not execute dependent work."),
                "resolution_requirements": unknown.get("resolution_requirements") or [],
                "resolution_evidence_ids": [],
                "status": "open",
                "resolved_at": None,
            }
        )
    return {
        "schema": "program-execution-blueprint.unknown-register.v2",
        "schema_version": "2.0.0",
        "policy": "Unknowns remain explicit and block only named dependent work.",
        "unknowns": mapped,
    }


def _risks(task_ids: list[str]) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.risk-register.v2",
        "schema_version": "2.0.0",
        "risks": [
            {
                "id": "RISK-001",
                "risk": "Authority widening beyond the compiled ceiling",
                "severity": "high",
                "likelihood": "UNKNOWN",
                "owner": "program_owner",
                "trigger": "Task action requests an action above its authorization_ceiling",
                "preventive_controls": ["exact authorization ceiling on every task card"],
                "contingency": ["Block the task and escalate to the program owner"],
                "related_tasks": [task_ids[0]],
                "related_gates": ["GATE-001"],
                "acceptance_decision_id": None,
                "status": "open",
            },
            {
                "id": "RISK-002",
                "risk": "Worker self-verification treated as independent evidence",
                "severity": "medium",
                "likelihood": "UNKNOWN",
                "owner": "program_owner",
                "trigger": "A completion gate passes without independent verification evidence",
                "preventive_controls": ["independent verification required by the policy profile"],
                "contingency": ["Re-run verification outside the producing task"],
                "related_tasks": task_ids[-1:],
                "related_gates": ["GATE-003"],
                "acceptance_decision_id": None,
                "status": "open",
            },
        ],
    }


def _waivers() -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.waiver-register.v2",
        "schema_version": "2.0.0",
        "policy": {"implicit_waivers_forbidden": True, "expired_waiver_non_passing": True},
        "waivers": [],
    }


def _evidence(revision: str, owner: str, snapshot: str) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.evidence-catalog.v2",
        "schema_version": "2.0.0",
        "evidence": [
            {
                "id": "EVID-001",
                "type": "source_snapshot",
                "source": "TARGET-001 repository HEAD",
                "revision": revision,
                "digest": None,
                "method": "git rev-parse HEAD",
                "environment": "planning",
                "producer": owner,
                "produced_at": snapshot,
                "expires_at": None,
                "result": "INFORMATIONAL",
                "status": "planned",
                "supports": ["DELTA-001"],
                "contradicts": [],
                "notes": "Bound at synthesis time by the Intent Resolver.",
            },
            {
                "id": "EVID-002",
                "type": "inspection",
                "source": "PHASE0_USER_CONFIG.yaml",
                "revision": "UNKNOWN",
                "digest": None,
                "method": "inspection",
                "environment": "planning",
                "producer": owner,
                "produced_at": snapshot,
                "expires_at": None,
                "result": "INFORMATIONAL",
                "status": "planned",
                "supports": [],
                "contradicts": [],
                "notes": "Phase 0 completeness and operator acknowledgement.",
            },
        ],
    }


def _do_not_build() -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.do-not-build.v2",
        "schema_version": "2.0.0",
        # Both of these are architecture laws, not globs. They used to ship as
        # path_or_pattern, which the Controller then tried to match against
        # changed files - a sentence never appears inside a path, so the gate
        # passed having enforced neither. They now travel as semantic rules.
        "prohibited_primary_paths": [
            prohibition_entry(
                identifier="DNB-001",
                statement="a second Program Execution runtime or Controller",
                reason="The existing Controller is the sole runtime authority",
                detection="review plus conformance checks",
                exception_authority="NONE",
            ),
            prohibition_entry(
                identifier="DNB-002",
                statement="compiler-owned mutable runtime state",
                reason="The compiler emits definitions; runtime state belongs to the Controller",
                detection="review plus conformance checks",
                exception_authority="NONE",
            ),
        ],
        "allowed_experiments": [],
    }


def _current_state_delta(revision: str, snapshot: str) -> dict[str, Any]:
    # An unobserved revision is not IN_SYNC with anything; say so.
    observed = revision != "UNKNOWN"
    return {
        "schema": "program-execution-blueprint.current-state-delta.v2",
        "schema_version": "2.0.0",
        "snapshot_at": snapshot,
        "freshness_policy": {"maximum_age": "24h", "stale_result": "BLOCKED"},
        "sources": [
            {
                "source_id": "SRC-001",
                "evidence_id": "EVID-001",
                "revision": revision,
                "freshness": "UNKNOWN",
            }
        ],
        "deltas": [
            {
                "id": "DELTA-001",
                "target_id": "TARGET-001",
                "expected_state": f"repository HEAD {revision}",
                "observed_state": f"repository HEAD {revision}",
                "classification": "IN_SYNC" if observed else "UNKNOWN",
                "impact": (
                    "No drift; synthesis bound to the observed revision."
                    if observed
                    else "Repository revision could not be observed; synthesis is bound to "
                    "no revision."
                ),
                "required_action": (
                    "None until the Controller advances execution."
                    if observed
                    else "Resolve the target checkout's git HEAD before admission."
                ),
                "evidence_ids": ["EVID-001"],
            }
        ],
        "next_blocking_action": "Resolve authority and decision lock before implementation.",
    }


def _workstreams() -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.workstreams.v2",
        "schema_version": "2.0.0",
        "workstreams": [
            {
                "id": "WS-01",
                "name": "authority_and_current_state_lock",
                "objective": "Lock authority, decisions, and current-state evidence",
                "owner": "program_owner",
                "target_ids": ["TARGET-001"],
                "scope": {
                    "include": ["authority registry", "current state"],
                    "exclude": ["runtime state"],
                },
                "inputs": ["INTENT_RESOLUTION artifact"],
                "outputs": ["accepted authority registry", "fresh current-state evidence"],
                "entry_gate_ids": ["GATE-000"],
                "exit_gate_ids": ["GATE-001"],
                "rollback_boundary": "Discard planning artifacts; runtime mutation is forbidden.",
                "definition_status": "active",
            },
            {
                "id": "WS-02",
                "name": "implementation",
                "objective": "Execute scoped, verifiable implementation units",
                "owner": "program_owner",
                "target_ids": ["TARGET-001"],
                "scope": {
                    "include": ["derived requirement units"],
                    "exclude": ["authority changes"],
                },
                "inputs": ["accepted authority registry"],
                "outputs": ["verified implementation artifacts"],
                "entry_gate_ids": ["GATE-001"],
                "exit_gate_ids": ["GATE-002"],
                "rollback_boundary": "git restore per task card",
                "definition_status": "active",
            },
            {
                "id": "WS-03",
                "name": "independent_verification",
                "objective": "Verify evidence independently and prepare handoff",
                "owner": "program_owner",
                "target_ids": ["TARGET-001"],
                "scope": {"include": ["verification receipts"], "exclude": ["worker self-claims"]},
                "inputs": ["implementation evidence"],
                "outputs": ["independent verification receipt", "handoff"],
                "entry_gate_ids": ["GATE-002"],
                "exit_gate_ids": ["GATE-003"],
                "rollback_boundary": "Discard unaccepted planning changes",
                "definition_status": "active",
            },
        ],
    }


def _graph(
    req_task_ids: list[str], w1_task_ids: list[str], w2_task_ids: list[str]
) -> dict[str, Any]:
    nodes = [{"id": "TASK-001", "entity_type": "task", "owner": "program_owner"}]
    nodes += [
        {"id": task_id, "entity_type": "task", "owner": "program_owner"} for task_id in w1_task_ids
    ]
    nodes += [
        {"id": task_id, "entity_type": "task", "owner": "program_owner"} for task_id in w2_task_ids
    ]
    edges = []
    for index, task_id in enumerate(w1_task_ids, start=1):
        edges.append(
            {
                "id": f"EDGE-{index:03d}",
                "from": "TASK-001",
                "to": task_id,
                "relation": "requires",
                "blocking": True,
                "proof_gate_ids": ["GATE-001"],
            }
        )
    for index, task_id in enumerate(w2_task_ids, start=len(w1_task_ids) + 1):
        edges.append(
            {
                "id": f"EDGE-{index:03d}",
                "from": w1_task_ids[-1],
                "to": task_id,
                "relation": "requires",
                "blocking": True,
                "proof_gate_ids": ["GATE-002"],
            }
        )
    critical_path = ["TASK-001", w1_task_ids[-1], w2_task_ids[-1]] if w1_task_ids else ["TASK-001"]
    return {
        "schema": "program-execution-blueprint.dependency-graph.v2",
        "schema_version": "2.0.0",
        "direction": "predecessor_to_successor",
        "nodes": nodes,
        "edges": edges,
        "critical_path": critical_path,
        "parallelizable_groups": [w1_task_ids] if len(w1_task_ids) > 1 else [],
        "hard_rule": "No successor may bypass a predecessor by reproducing its output elsewhere.",
    }


def _waves(w1_task_ids: list[str], w2_task_ids: list[str]) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.execution-waves.v2",
        "schema_version": "2.0.0",
        "promotion_rule": "A wave starts only when prior waves and all blocking entry gates pass.",
        "waves": [
            {
                "id": "W0",
                "name": "authority_and_current_state_lock",
                "sequence": 0,
                "depends_on": [],
                "workstream_ids": ["WS-01"],
                "task_ids": ["TASK-001"],
                "entry_gate_ids": [],
                "exit_gate_ids": ["GATE-001"],
                "rollback_boundary": "Discard planning artifacts; runtime mutation is forbidden.",
                "definition_status": "active",
            },
            {
                "id": "W1",
                "name": "implementation",
                "sequence": 1,
                "depends_on": ["W0"],
                "workstream_ids": ["WS-02"],
                "task_ids": w1_task_ids,
                "entry_gate_ids": ["GATE-001"],
                "exit_gate_ids": ["GATE-002"],
                "rollback_boundary": "git restore of scoped changes",
                "definition_status": "active",
            },
            {
                "id": "W2",
                "name": "independent_verification",
                "sequence": 2,
                "depends_on": ["W1"],
                "workstream_ids": ["WS-03"],
                "task_ids": w2_task_ids,
                "entry_gate_ids": ["GATE-002"],
                "exit_gate_ids": ["GATE-003"],
                "rollback_boundary": "Discard unaccepted planning changes",
                "definition_status": "active",
            },
        ],
    }


def _gates(owner: str, w1_task_ids: list[str], w2_task_ids: list[str]) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.convergence-gates.v2",
        "schema_version": "2.0.0",
        "result_values": ["PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE_WITH_REASON"],
        "unknown_is_non_passing": True,
        "gates": [
            {
                "id": "GATE-000",
                "name": "phase0_user_config_complete",
                "definition_status": "active",
                "owner": owner,
                "class": "phase0",
                "blocking_class": "true_blocking",
                "scope": {"wave_ids": ["W0"], "task_ids": ["TASK-001"]},
                "method": {
                    "type": "inspection",
                    "steps": [
                        "Inspect PHASE0_USER_CONFIG.yaml completeness and operator acknowledgement."
                    ],
                },
                "pass_condition": (
                    "Phase 0 acknowledges the program scope and ceilings; "
                    "autonomous_merge is false."
                ),
                "fail_condition": "Unacknowledged Phase 0 or misaligned autonomy ceilings.",
                "blocking": True,
                "required_evidence_ids": ["EVID-002"],
                "waiver_allowed": False,
            },
            {
                "id": "GATE-001",
                "name": "authority_and_decision_lock",
                "definition_status": "active",
                "owner": owner,
                "class": "authority",
                "blocking_class": "true_blocking",
                "scope": {"wave_ids": ["W0"], "task_ids": ["TASK-001"]},
                "method": {
                    "type": "inspection",
                    "steps": [
                        (
                            "Inspect authority, decisions, Unknowns, targets, "
                            "and current-state evidence."
                        )
                    ],
                },
                "pass_condition": (
                    "Every material responsibility has one owner and no required "
                    "decision or Unknown blocks the scoped work."
                ),
                "fail_condition": (
                    "Duplicate authority, stale evidence, or unresolved scoped blocker remains."
                ),
                "blocking": True,
                "required_evidence_ids": ["EVID-001"],
                "waiver_allowed": False,
            },
            {
                "id": "GATE-002",
                "name": "implementation_and_validation_complete",
                "definition_status": "active",
                "owner": owner,
                "class": "execution",
                "blocking_class": "true_blocking",
                "scope": {"wave_ids": ["W1"], "task_ids": w1_task_ids},
                "method": {
                    "type": "command_and_inspection",
                    "steps": ["Run declared validation commands and inspect outputs."],
                },
                "pass_condition": (
                    "All W1 task acceptance criteria are evidenced; declared "
                    "validation commands exit zero."
                ),
                "fail_condition": "Any W1 validation command fails or evidence is missing.",
                "blocking": True,
                "required_evidence_ids": [],
                "waiver_allowed": False,
            },
            {
                "id": "GATE-003",
                "name": "independent_verification_complete",
                "definition_status": "active",
                "owner": owner,
                "class": "validation",
                "blocking_class": "true_blocking",
                "scope": {"wave_ids": ["W2"], "task_ids": w2_task_ids},
                "method": {
                    "type": "inspection",
                    "steps": [
                        "Inspect verification receipts independently of the producing tasks."
                    ],
                },
                "pass_condition": (
                    "Independent verification evidence exists; no worker "
                    "self-claim is treated as verification."
                ),
                "fail_condition": "Verification rests only on worker self-claims.",
                "blocking": True,
                "required_evidence_ids": [],
                "waiver_allowed": False,
            },
        ],
    }


def _phase0(owner: str) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.phase0-user-config.v2",
        "schema_version": "2.0.0",
        "phase": 0,
        "definition_status": "draft",
        "program_deploying": False,
        "autonomy": {
            "default": "maximum_within_ceiling",
            "profile": "bounded_local_execution",
            "authority": "A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE",
            "autonomous_merge": False,
            "max_parallel_workers": 1,
            "max_mutation_lanes": 1,
            "remediation_skill": "l9-pr-remediation",
        },
        "adapter_status": "absent",
        "blocking_inventory": {"true_blocking": [], "advisory_or_disabled": []},
        "stop_conditions_reviewed": False,
        "approvals_preauthorized": [],
        "open_business_decisions": [],
        "alignment": {
            "uv_lock_check": "pending",
            "toolchain_pin_lockstep": "pending",
            "make_pr_gate_required": True,
            "targets_inventoried": [],
        },
        "campaign_authorization_packet": {
            "packet_id": None,
            "declared_repos": [],
            "declared_prs": [],
            "declared_branches": [],
            "declared_ops": [],
        },
        "kill_switch": {
            "path": ".l9/autonomy/revoke",
            "operator_action": "touch_revoke_and_runtime_suspend",
            "auto_file_watch_enforced": False,
        },
        "resource_hygiene_ack": False,
        "operator_ack": {"name": owner, "acknowledged_at": None},
        "completeness": {"phase0_complete": False},
        "notes": (
            "Compiled by the Program Execution intent compiler; Phase 0 "
            "completion remains an operator action."
        ),
    }


def _observability(owner: str) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.observability-plan.v2",
        "schema_version": "2.0.0",
        "signals": [
            {
                "id": "OBS-001",
                "name": "validation_command_exit_status",
                "owner": owner,
                "source_target_id": "TARGET-001",
                "collection_method": "command exit code capture",
                "expected_range": "exit 0 for declared validation commands",
                "alert_condition": "any declared validation command exits non-zero",
                "retention": "program duration",
                "related_gate_ids": ["GATE-003"],
                "status": "planned",
            }
        ],
        "incident_routing": [
            {
                "condition": "blocking_signal_breach",
                "owner": owner,
                "action": "pause_affected_wave_and_preserve_evidence",
            }
        ],
    }


def _cutover_rollback(owner: str) -> dict[str, Any]:
    return {
        "schema": "program-execution-blueprint.cutover-and-rollback.v2",
        "schema_version": "2.0.0",
        "cutover": {
            "required_gate_ids": ["GATE-003"],
            "approval_action": "deploy_or_migrate",
            "steps": ["Owner accepts the verification receipt before any promotion."],
            "abort_conditions": ["gate failure", "observability breach"],
            "observation_window": "program-specific; bounded by gate scope",
        },
        "rollback": {
            "trigger_conditions": ["blocking_gate_failure", "material_observability_breach"],
            "steps": ["git restore the scoped change to the pre-task revision"],
            "data_reconciliation": "compare worktree against the bound revision",
            "validation": ["official Blueprint validation still passes on the restored tree"],
            "owner": owner,
        },
    }


def _traceability(resolution: dict[str, Any], task_ids: list[str]) -> dict[str, Any]:
    profile = resolution["governing_authority"]["policy_profile"]
    sources = [
        {
            "id": "SRC-001",
            "source": "User intent (program-execution.intent.v1)",
            "revision": "UNKNOWN",
            "authority_class": "governing",
            "evidence_id": "EVID-001",
            "claims": [resolution["intent"]["normalized_objective"]],
            "target_ids": ["TARGET-001"],
            "workstream_ids": ["WS-01"],
            "task_ids": ["TASK-001"],
            "gate_ids": ["GATE-001"],
            "status": "active",
        },
        {
            "id": "SRC-002",
            "source": f"Policy profile {profile}",
            "revision": "UNKNOWN",
            "authority_class": "governing",
            "evidence_id": "EVID-001",
            "claims": ["authorization ceiling and decision classes"],
            "target_ids": ["TARGET-001"],
            "workstream_ids": ["WS-02", "WS-03"],
            "task_ids": task_ids[1:],
            "gate_ids": ["GATE-001"],
            "status": "active",
        },
    ]
    return {
        "schema": "program-execution-blueprint.source-traceability.v2",
        "schema_version": "2.0.0",
        "authority_classes": [
            "governing",
            "supporting",
            "contradicting",
            "example",
            "historical",
            "inferred",
        ],
        "sources": sources,
    }


def _markdown_overrides(program: dict[str, Any]) -> dict[str, str]:
    title = program["program"]["name"]
    owner = program["program"]["owner"]
    program_id = program["program"]["id"]
    snapshot = program["program"]["snapshot_at"]
    return {
        "DEFINITION_OF_DONE": (
            "# Definition of Done\n\n"
            "Every task in this program is complete only when:\n\n"
            "- its acceptance criteria are satisfied with verifiable evidence;\n"
            "- its declared validation command exits zero or its inspection evidence is recorded;\n"
            "- its rollback strategy is executable without authority widening;\n"
            "- its completion gates are evaluated by the Controller, not by the worker itself.\n\n"
            f"Program: {program_id}\n"
        ),
        "EXECUTIVE_DECISION": (
            "# Executive Decision\n\n"
            f"Program `{program_id}` ({title}) is compiled from minimal user intent "
            f"under the governing autonomy policy recorded in AUTHORITY_REGISTRY.yaml.\n\n"
            "The compiler emitted design-time definitions only. Execution authority, "
            "mutable runtime state, gate results, and the terminal program verdict "
            "remain with the Program Execution Controller and the program owner.\n\n"
            f"Compiled at: {snapshot}\n"
        ),
        "HANDOFF": (
            "# Handoff\n\n"
            "This directory is a compiler-generated Program Execution Blueprint v2.\n\n"
            "- Definition state only: no Controller runtime state, attempts, or gate results.\n"
            "- Independent verification is required before any convergence claim.\n"
            "- The terminal verdict belongs to the program owner.\n\n"
            f"Program: {program_id}\nOwner: {owner}\n"
        ),
    }


__all__ = [
    "AUTH_ACTIONS",
    "RuntimeContaminationError",
    "synthesize",
]
