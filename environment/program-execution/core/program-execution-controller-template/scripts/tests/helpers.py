from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

CONTROLLER_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = CONTROLLER_ROOT / "scripts"
REPO = Path(__file__).resolve().parents[6]

READINESS_SHA = "a" * 40
READINESS_SESSION = "controller-test-session"


def session_workspace(temp: Path) -> Path:
    """The workspace the session's readiness receipt and memory state hang off."""
    return temp / "session-workspace"


def establish_runtime_readiness(
    temp: Path,
    *,
    session_id: str = READINESS_SESSION,
    governance_revision: str = READINESS_SHA,
    runtime_script_revision: str = READINESS_SHA,
    degraded_count: int = 0,
) -> dict[str, Any]:
    """Give this test the READY session receipt mutating commands require.

    Mutating ``pec`` commands are admitted only against an
    ``l9.agents.runtime-readiness.v1`` receipt (see ``pec/admission.py``), so the
    suite establishes one the way a real session does rather than bypassing the
    gate. The session workspace is deliberately *not* the fixture git repo: the
    receipt admission resolves belongs to the session (``CLAUDE_PROJECT_DIR``),
    while ``preflight --receipt-workspace`` stays an independent argument that
    tests still exercise against the repo. ``L9_RUNTIME_ROOT`` keeps everything
    out of the developer's real ``~/.l9``, and ``.l9/memory`` is created because
    the receipt reports NOT_READY until the memory state root resolves.
    """
    sys.path.insert(0, str(REPO / "ops" / "scripts"))
    from write_runtime_readiness_receipt import main as write_receipt
    from write_runtime_readiness_receipt import receipt_path

    workspace = session_workspace(temp)
    (workspace / ".l9" / "memory").mkdir(parents=True, exist_ok=True)
    (temp / "home").mkdir(parents=True, exist_ok=True)
    # HOME is redirected so the Graphiti session-state file and the runtime root
    # this fixture creates land under the temp dir, never the developer's real
    # ~/.cursor or ~/.l9.
    os.environ["HOME"] = str(temp / "home")
    os.environ["L9_RUNTIME_ROOT"] = str(temp / "l9")
    os.environ["L9_PE_RECEIPT_WORKSPACE"] = str(workspace)
    os.environ["CLAUDE_PROJECT_DIR"] = str(workspace)
    os.environ["CURSOR_PROJECT_DIR"] = str(workspace)
    rc = write_receipt(
        [
            "--surface",
            surface(),
            "--workspace",
            str(workspace),
            "--governance",
            str(REPO),
            "--governance-revision",
            governance_revision,
            "--runtime-script-revision",
            runtime_script_revision,
            "--session-id",
            session_id,
            "--degraded-count",
            str(degraded_count),
        ]
    )
    if rc != 0:
        raise AssertionError(f"readiness receipt writer exit {rc}")
    receipt = json.loads(
        receipt_path(surface=surface(), workspace=workspace).read_text(encoding="utf-8")
    )
    expected = "READY" if degraded_count == 0 else "DEGRADED"
    if receipt["overall_status"] != expected:
        raise AssertionError(f"fixture runtime is {receipt['overall_status']}, want {expected}")
    return receipt


def surface() -> str:
    return os.environ.get("L9_GOVERNANCE_SURFACE", "").strip() or "cursor"


def establish_phase_lock(
    *,
    session_id: str = READINESS_SESSION,
    granted: bool = True,
    graphiti_satisfied: bool = True,
) -> dict[str, Any]:
    """Put the canonical phase-lock state in place for every declared namespace.

    Governed mutation requires a Graphiti-granted phase lock, so preflight
    verifies two artifacts that ``memory_lock.py acquire`` produces together: the
    local lock file (written through ``memory_state``, the same module the CLI
    and the PreToolUse gate use) and the Cursor Graphiti session state recording
    the served grant. Both are written here through the canonical helpers rather
    than by hand, so the fixture cannot drift from the real acquire path.

    ``granted`` / ``graphiti_satisfied`` exist so negative cases can withhold
    exactly one of the two and assert the specific blocker.
    """
    mem = REPO / "environment" / "agents" / "adapters" / "claude-code" / "memory"
    sys.path.insert(0, str(mem))
    import memory_state as st

    contract = st.load_contract()
    written: list[str] = []
    for namespace in st.resolve_namespaces(contract):
        st.write_receipt(contract, session_id, {"namespaces": [namespace]})
        path = st.write_lock(contract, namespace, session_id, st.task_signature(namespace))
        body = json.loads(path.read_text(encoding="utf-8"))
        body["transport"] = "cursor-graphiti-phase-lock"
        body["granted"] = granted
        path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(namespace)

    state = st.graphiti_state_path(session_id)
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(
        json.dumps({"memory_satisfied_for": ["gmp:phase_lock"] if graphiti_satisfied else []}),
        encoding="utf-8",
    )
    return {"namespaces": written, "graphiti_state_file": str(state), "session_id": session_id}


def write_yaml(path: Path, value: Any) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def run_cli(*args: str, expect: int = 0) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / "pec.py"), *args],
        cwd=CONTROLLER_ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=45,
    )
    if completed.returncode != expect:
        raise AssertionError(
            f"command exit {completed.returncode}, expected {expect}: {args}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return json.loads(completed.stdout)


def make_blueprint(
    root: Path,
    *,
    two_tasks: bool = False,
    risk_tier: str = "T2",
    with_decision_unknown: bool = False,
    open_risk: bool = False,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    required = [
        "PROGRAM.yaml",
        "EXECUTION_TARGETS.yaml",
        "AUTHORITY_REGISTRY.yaml",
        "DECISION_REGISTER.yaml",
        "UNKNOWN_REGISTER.yaml",
        "RISK_REGISTER.yaml",
        "WAIVER_REGISTER.yaml",
        "EVIDENCE_CATALOG.yaml",
        "DO_NOT_BUILD.yaml",
        "CURRENT_STATE_DELTA.yaml",
        "WORKSTREAMS.yaml",
        "DEPENDENCY_GRAPH.yaml",
        "EXECUTION_WAVES.yaml",
        "TASK_CARDS.yaml",
        "CONVERGENCE_GATES.yaml",
        "OBSERVABILITY_PLAN.yaml",
        "CUTOVER_AND_ROLLBACK.yaml",
        "SOURCE_TRACEABILITY.yaml",
    ]
    write_yaml(
        root / "EXECUTION_INDEX.yaml",
        {
            "schema": "program-execution-blueprint.index.v2",
            "schema_version": "2.0.0",
            "blueprint_contract": "program-execution-blueprint.v2",
            "required_sources": required,
            "canonical_owners": {"task_dependencies": "DEPENDENCY_GRAPH.yaml"},
            "controller_import": {
                "immutable": True,
                "digest_algorithm": "sha256",
                "unknown_contract": "reject",
                "source_change": "mark_runtime_stale",
            },
        },
    )
    write_yaml(
        root / "PROGRAM.yaml",
        {
            "schema": "program-execution-blueprint.program.v2",
            "schema_version": "2.0.0",
            "program": {
                "id": "test-program",
                "name": "Test Program",
                "version": "2.0.0",
                "owner": "operator",
                "definition_status": "accepted",
                "snapshot_at": "2026-08-01T13:00:00-04:00",
                "objective": "Exercise the Controller",
                "problem_statement": "Execution requires governed proof",
                "target_state": "The bounded change is independently verified",
                "scope": {"include": ["repo-a"], "exclude": ["remote mutation"]},
                "contracts": {
                    "blueprint": "program-execution-blueprint.v2",
                    "controller_minimum": "program-execution-controller.v2",
                    "pair": "program-execution-system.v2",
                },
                "authority_order": [
                    "operator",
                    "accepted_blueprint",
                    "verified_evidence",
                    "UNKNOWN",
                ],
                "operating_rules": ["controller_may_narrow_never_widen"],
                "terminal_verdicts": [
                    "CONVERGED",
                    "CONVERGED_WITH_NON_BLOCKING_RISKS",
                    "NOT_CONVERGED",
                    "INCONCLUSIVE",
                ],
            },
        },
    )
    write_yaml(
        root / "EXECUTION_TARGETS.yaml",
        {
            "schema": "program-execution-blueprint.execution-targets.v2",
            "schema_version": "2.0.0",
            "targets": [
                {
                    "id": "TARGET-001",
                    "name": "Repository A",
                    "kind": "git_repository",
                    "authority_owner": "operator",
                    "execution_mode": "repo_local",
                    "repository_id": "repo-a",
                    "source_of_truth": "git",
                    "environments": ["local"],
                    "mutability": "reversible",
                    "expected_revision": "UNKNOWN",
                    "adapter": "git",
                }
            ],
        },
    )
    write_yaml(
        root / "AUTHORITY_REGISTRY.yaml",
        {
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
                    "responsibility": "repository implementation",
                    "owner_target_id": "TARGET-001",
                    "source_of_truth": "repo-a",
                    "consumers": ["controller"],
                    "allowed_roles": ["authority"],
                    "prohibited_owner_target_ids": [],
                    "enforcement": ["source contract"],
                    "validation_gate_ids": ["GATE-001"],
                    "definition_status": "active",
                }
            ],
        },
    )
    decisions = []
    unknowns = []
    if with_decision_unknown:
        decisions = [
            {
                "id": "DEC-001",
                "question": "Proceed?",
                "status": "pending",
                "owner": "operator",
                "options": [
                    {"id": "A", "description": "Proceed", "benefits": ["test"], "risks": ["test"]}
                ],
                "selected_option": None,
                "rationale": None,
                "evidence_ids": [],
                "blocks": ["TASK-001"],
                "required_by": "TASK-001",
                "supersedes": None,
            }
        ]
        unknowns = [
            {
                "id": "UNK-001",
                "topic": "Input certainty",
                "owner": "operator",
                "blocks": ["TASK-001"],
                "safe_state": "Do not execute",
                "resolution_requirements": ["inspect evidence"],
                "resolution_evidence_ids": [],
                "status": "open",
                "resolved_at": None,
            }
        ]
    write_yaml(
        root / "DECISION_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.decision-register.v2",
            "schema_version": "2.0.0",
            "policy": "No silent defaults",
            "decisions": decisions,
        },
    )
    write_yaml(
        root / "UNKNOWN_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.unknown-register.v2",
            "schema_version": "2.0.0",
            "policy": "Scoped blocking",
            "unknowns": unknowns,
        },
    )
    risks = []
    if open_risk:
        risks = [
            {
                "id": "RISK-001",
                "risk": "Residual risk",
                "severity": "low",
                "likelihood": "possible",
                "owner": "operator",
                "trigger": "observed",
                "preventive_controls": ["verify"],
                "contingency": ["rollback"],
                "related_tasks": ["TASK-001"],
                "related_gates": ["GATE-001"],
                "acceptance_decision_id": None,
                "status": "open",
            }
        ]
    write_yaml(
        root / "RISK_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.risk-register.v2",
            "schema_version": "2.0.0",
            "risks": risks,
        },
    )
    write_yaml(
        root / "WAIVER_REGISTER.yaml",
        {
            "schema": "program-execution-blueprint.waiver-register.v2",
            "schema_version": "2.0.0",
            "policy": {"implicit_waivers_forbidden": True, "expired_waiver_non_passing": True},
            "waivers": [],
        },
    )
    write_yaml(
        root / "EVIDENCE_CATALOG.yaml",
        {
            "schema": "program-execution-blueprint.evidence-catalog.v2",
            "schema_version": "2.0.0",
            "evidence": [
                {
                    "id": "EVID-PLAN",
                    "type": "source_snapshot",
                    "source": "test fixture",
                    "revision": "fixture-v2",
                    "digest": None,
                    "method": "fixture inspection",
                    "environment": "planning",
                    "producer": "test",
                    "produced_at": "2026-08-01T13:00:00-04:00",
                    "expires_at": None,
                    "result": "PASS",
                    "status": "available",
                    "supports": ["TASK-001"],
                    "contradicts": [],
                    "notes": None,
                }
            ],
        },
    )
    write_yaml(
        root / "DO_NOT_BUILD.yaml",
        {
            "schema": "program-execution-blueprint.do-not-build.v2",
            "schema_version": "2.0.0",
            "prohibited_primary_paths": [],
            "allowed_experiments": [],
        },
    )
    write_yaml(
        root / "CURRENT_STATE_DELTA.yaml",
        {
            "schema": "program-execution-blueprint.current-state-delta.v2",
            "schema_version": "2.0.0",
            "snapshot_at": "2026-08-01T13:00:00-04:00",
            "freshness_policy": {"maximum_age": "30d", "stale_result": "BLOCKED"},
            "sources": [
                {
                    "source_id": "SRC-001",
                    "evidence_id": "EVID-PLAN",
                    "revision": "fixture-v2",
                    "freshness": "fresh",
                }
            ],
            "deltas": [
                {
                    "id": "DELTA-001",
                    "target_id": "TARGET-001",
                    "expected_state": "result exists",
                    "observed_state": "result absent",
                    "classification": "gap",
                    "impact": "task required",
                    "required_action": "execute task",
                    "evidence_ids": ["EVID-PLAN"],
                }
            ],
            "next_blocking_action": "Execute TASK-001",
        },
    )
    write_yaml(
        root / "WORKSTREAMS.yaml",
        {
            "schema": "program-execution-blueprint.workstreams.v2",
            "schema_version": "2.0.0",
            "workstreams": [
                {
                    "id": "WS-01",
                    "name": "Implementation",
                    "objective": "Create result",
                    "owner": "operator",
                    "target_ids": ["TARGET-001"],
                    "scope": {"include": ["docs/result.txt"], "exclude": ["remote"]},
                    "inputs": ["EVID-PLAN"],
                    "outputs": ["docs/result.txt"],
                    "entry_gate_ids": [],
                    "exit_gate_ids": ["GATE-001"],
                    "rollback_boundary": "delete result",
                    "definition_status": "active",
                }
            ],
        },
    )
    task_ids = ["TASK-001"] + (["TASK-002"] if two_tasks else [])
    edges = []
    write_yaml(
        root / "DEPENDENCY_GRAPH.yaml",
        {
            "schema": "program-execution-blueprint.dependency-graph.v2",
            "schema_version": "2.0.0",
            "direction": "predecessor_to_successor",
            "nodes": [
                {"id": task_id, "entity_type": "task", "owner": "operator"} for task_id in task_ids
            ],
            "edges": edges,
            "critical_path": ["TASK-001"],
            "parallelizable_groups": [task_ids] if two_tasks else [],
            "hard_rule": "No bypass",
        },
    )
    write_yaml(
        root / "EXECUTION_WAVES.yaml",
        {
            "schema": "program-execution-blueprint.execution-waves.v2",
            "schema_version": "2.0.0",
            "promotion_rule": "Blocking gates pass",
            "waves": [
                {
                    "id": "W0",
                    "name": "local execution",
                    "sequence": 0,
                    "depends_on": [],
                    "workstream_ids": ["WS-01"],
                    "task_ids": task_ids,
                    "entry_gate_ids": [],
                    "exit_gate_ids": ["GATE-001"],
                    "rollback_boundary": "delete result",
                    "definition_status": "active",
                }
            ],
        },
    )
    ceiling = {
        action: False
        for action in [
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
        ]
    }
    ceiling.update({"inspect": True, "local_write": True})

    def task(task_id: str, output: str) -> dict[str, Any]:
        return {
            "id": task_id,
            "title": f"Write {output}",
            "definition_status": "ready",
            "workstream_id": "WS-01",
            "wave_id": "W0",
            "target_id": "TARGET-001",
            "execution_kind": "repo_local",
            "objective": f"Write {output}",
            "authority_basis_ids": ["AUTH-001"],
            "required_decision_ids": ["DEC-001"]
            if with_decision_unknown and task_id == "TASK-001"
            else [],
            "blocking_unknown_ids": ["UNK-001"]
            if with_decision_unknown and task_id == "TASK-001"
            else [],
            "input_evidence_ids": ["EVID-PLAN"],
            "actions": ["write_file"],
            "outputs": [
                {
                    "id": f"OUT-{task_id[-3:]}",
                    "type": "artifact",
                    "location": output,
                    "required": True,
                }
            ],
            "acceptance": [
                {
                    "id": f"AC-{task_id[-3:]}",
                    "statement": f"{output} contains ok",
                    "required_evidence_types": ["test_result"],
                }
            ],
            "validation": [
                {
                    "id": f"VAL-{task_id[-3:]}",
                    "method": "command",
                    "command_or_inspection": f"python3 -c \"from pathlib import Path; assert Path('{output}').read_text() == 'ok\\n'\"",  # noqa: E501
                    "environment": "local",
                    "expected_result": "PASS",
                }
            ],
            "negative_cases": ["wrong content"],
            "rollback": {
                "strategy": f"delete {output}",
                "trigger": "validation_failure",
                "validation": "file absent",
            },
            "risk": {
                "tier": risk_tier if task_id == "TASK-001" else "T2",
                "reversibility": "reversible",
                "blast_radius": "single_target",
            },
            "authorization_ceiling": dict(ceiling),
            "completion_gate_ids": ["GATE-001"],
        }

    tasks = [task("TASK-001", "docs/result.txt")]
    if two_tasks:
        tasks.append(task("TASK-002", "docs/second.txt"))
    write_yaml(
        root / "TASK_CARDS.yaml",
        {
            "schema": "program-execution-blueprint.task-cards.v2",
            "schema_version": "2.0.0",
            "tasks": tasks,
        },
    )
    write_yaml(
        root / "CONVERGENCE_GATES.yaml",
        {
            "schema": "program-execution-blueprint.convergence-gates.v2",
            "schema_version": "2.0.0",
            "result_values": ["PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE_WITH_REASON"],
            "unknown_is_non_passing": True,
            "gates": [
                {
                    "id": "GATE-001",
                    "name": "local verification",
                    "definition_status": "active",
                    "owner": "operator",
                    "class": "execution",
                    "scope": {"wave_ids": ["W0"], "task_ids": task_ids},
                    "method": {"type": "command_and_inspection", "steps": ["verify result"]},
                    "pass_condition": "Controller verification passes",
                    "fail_condition": "Verification fails",
                    "blocking": True,
                    "required_evidence_ids": [],
                    "waiver_allowed": False,
                }
            ],
        },
    )
    write_yaml(
        root / "OBSERVABILITY_PLAN.yaml",
        {
            "schema": "program-execution-blueprint.observability-plan.v2",
            "schema_version": "2.0.0",
            "signals": [],
            "incident_routing": [],
        },
    )
    write_yaml(
        root / "CUTOVER_AND_ROLLBACK.yaml",
        {
            "schema": "program-execution-blueprint.cutover-and-rollback.v2",
            "schema_version": "2.0.0",
            "cutover": {
                "required_gate_ids": ["GATE-001"],
                "approval_action": "deploy_or_migrate",
                "steps": ["not applicable locally"],
                "abort_conditions": ["gate failure"],
                "observation_window": "immediate",
            },
            "rollback": {
                "trigger_conditions": ["gate failure"],
                "steps": ["delete result"],
                "data_reconciliation": "none",
                "validation": ["working tree clean"],
                "owner": "operator",
            },
        },
    )
    write_yaml(
        root / "SOURCE_TRACEABILITY.yaml",
        {
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
            "sources": [
                {
                    "id": "SRC-001",
                    "source": "fixture",
                    "revision": "v2",
                    "authority_class": "governing",
                    "evidence_id": "EVID-PLAN",
                    "claims": ["test"],
                    "target_ids": ["TARGET-001"],
                    "workstream_ids": ["WS-01"],
                    "task_ids": task_ids,
                    "gate_ids": ["GATE-001"],
                    "status": "active",
                }
            ],
        },
    )
    return root


def make_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Controller Test"], check=True)
    (root / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-m", "init"], check=True, capture_output=True
    )
    return root


def source_contract(
    task_id: str = "TASK-001",
    output: str = "docs/result.txt",
    *,
    actions: list[str] | None = None,
    risk_tier: str = "T2",
) -> dict[str, Any]:
    return {
        "schema": "program-execution-controller.source-contract.v2",
        "task_id": task_id,
        "target_id": "TARGET-001",
        "repository_id": "repo-a",
        "objective": f"Write {output}",
        "requested_actions": actions or ["inspect", "local_write"],
        "acceptance_obligation_ids": [f"AC-{task_id[-3:]}"],
        "writable_paths": [output],
        "validation_commands": [
            f"python3 -c \"from pathlib import Path; assert Path('{output}').read_text() == 'ok\\n'\""  # noqa: E501
        ],
        "required_gate_ids": ["GATE-001"],
        "required_evidence_ids": ["EVID-PLAN"],
        "risk_tier": risk_tier,
        "remote_mutation": "denied",
        "stop_conditions": ["program, contract, authority, scope, lease, or base-state drift"],
        "rollback": f"delete {output}",
    }


def write_json(path: Path, value: Any) -> Path:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def bootstrap_repo(temp: Path, **blueprint_options: Any) -> tuple[Path, Path, Path]:
    establish_runtime_readiness(temp)
    blueprint = make_blueprint(temp / "blueprint", **blueprint_options)
    repo = make_repo(temp / "repo")
    workspace = temp / "runtime"
    run_cli("bootstrap", "--workspace", str(workspace), "--blueprint", str(blueprint))
    run_cli("reconcile", "--workspace", str(workspace), "--repository", f"repo-a={repo}")
    return blueprint, repo, workspace


def register_contract(
    temp: Path,
    workspace: Path,
    *,
    task_id: str = "TASK-001",
    output: str = "docs/result.txt",
    actions: list[str] | None = None,
    risk_tier: str = "T2",
) -> Path:
    path = write_json(
        temp / f"{task_id}.source.json",
        source_contract(task_id, output, actions=actions, risk_tier=risk_tier),
    )
    run_cli(
        "register-contract",
        task_id,
        "--workspace",
        str(workspace),
        "--file",
        str(path),
        "--actor",
        "operator",
    )
    return path


def prepare_attempt(
    temp: Path,
    workspace: Path,
    *,
    task_id: str = "TASK-001",
    output: str = "docs/result.txt",
    declared_changed: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    run_cli("claim", task_id, "--workspace", str(workspace), "--holder", "worker")
    prepared = run_cli("prepare", task_id, "--workspace", str(workspace))
    rendered = run_cli("render-contract", task_id, "--workspace", str(workspace))
    run_cli("start", task_id, "--workspace", str(workspace), "--actor", "worker")
    worktree = Path(prepared["worktree"])
    target = worktree / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("ok\n", encoding="utf-8")
    contract = json.loads(Path(rendered["contract"]).read_text(encoding="utf-8"))
    receipt = {
        "schema": "program-execution-controller.attempt-receipt.v2",
        "task_id": task_id,
        "contract_digest": contract["contract_digest"],
        "program_digest": contract["program_digest"],
        "base_sha": contract["base_sha"],
        "candidate_sha": None,
        "changed_files": declared_changed if declared_changed is not None else [output],
        "validation_results": [
            {"command": command, "status": "PASS", "exit_code": 0, "evidence": "worker output"}
            for command in contract["validation_commands"]
        ],
        "produced_evidence": [],
        "residual_unknowns": [],
        "claimed_status": "completed",
    }
    receipt_path = write_json(temp / f"{task_id}.attempt.json", receipt)
    run_cli(
        "record-attempt", task_id, "--workspace", str(workspace), "--receipt", str(receipt_path)
    )
    return contract, prepared


def cleanup_worktree(repo: Path, workspace: Path, task_id: str = "TASK-001") -> None:
    worktree = workspace / "worktrees" / task_id
    if worktree.exists():
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
            check=False,
            capture_output=True,
            timeout=15,
        )
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "prune"], check=False, capture_output=True, timeout=15
    )
