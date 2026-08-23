#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one anchor, found {count}: {old[:120]!r}')
    write(path, text.replace(old, new, 1))


def regex_once(path: str, pattern: str, replacement: str, *, flags: int = 0) -> None:
    text = read(path)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one regex anchor, found {count}: {pattern[:120]!r}')
    write(path, updated)


# ---------------------------------------------------------------------------
# PE-AUTH-001: make campaign is permanently local-only.
# ---------------------------------------------------------------------------
RUN = 'environment/program-execution/scripts/run_campaign.py'
replace_once(
    RUN,
    'Sealed stages: isolate → emit → blueprint → collect → accept →\n'
    'pec bootstrap (no draft) → pec reconcile → contract/claim TASK-001 →\n'
    'execute every task → stacked task PRs → pec+host close → COMPLETED/.\n',
    'Sealed stages: isolate → emit → blueprint → collect → accept →\n'
    'pec bootstrap (no draft) → pec reconcile → contract/claim →\n'
    'Peer Execution → Controller verify → local commits → STOP.\n',
)
replace_once(
    RUN,
    '''UNTIL_STAGES = (\n    "activate",\n    "blueprint",\n    "admit",\n    "bootstrap",\n    "arm",\n    "execute",\n    "pr",\n    "close",\n)\nUNTIL_ALIASES = {"merge": "close", "bootstrap": "arm"}\nSTAGE_INDEX = {name: index for index, name in enumerate(UNTIL_STAGES)}\n''',
    '''UNTIL_STAGES = (\n    "activate",\n    "blueprint",\n    "admit",\n    "bootstrap",\n    "arm",\n    "execute",\n)\nUNTIL_ALIASES = {"bootstrap": "arm"}\n# Kept only so unreachable compatibility helpers can compare their historical\n# stages without becoming public runner stages again.\nLEGACY_PUBLICATION_STAGES = ("pr", "close", "merge")\nSTAGE_INDEX = {\n    name: index for index, name in enumerate(UNTIL_STAGES + ("pr", "close"))\n}\n''',
)
replace_once(
    RUN,
    '''# Autonomous Program Execution is local-commit-only. It prepares, executes,\n# validates, verifies, and commits — then stops. Pushing a branch, opening or\n# updating a pull request, and merging are release actions, not campaign\n# stages, and only run under an explicit governed release transition.\nPE_RELEASE_ENV = "L9_PE_RELEASE_AUTHORIZED"\nAUTONOMOUS_LAST_STAGE = "execute"\nPUBLICATION_STAGES = ("pr", "close")\n''',
    '''# Program Execution is permanently local-commit-only. The historical\n# release variable is retained as a diagnostic compatibility name only; it can\n# never widen runner authority. Publication belongs to root `make pr`; merge\n# belongs to /l9-pr-remediation.\nPE_RELEASE_ENV = "L9_PE_RELEASE_AUTHORIZED"\nAUTONOMOUS_LAST_STAGE = "execute"\nPUBLICATION_STAGES = ("pr", "close")\n''',
)
regex_once(
    RUN,
    r'def release_authorized\(\) -> bool:\n.*?\n\ndef refuse_publication\(action: str\) -> None:\n.*?\n\n\n_PUBLICATION_GIT_SUBCOMMANDS',
    '''def release_authorized() -> bool:\n    """Compatibility probe: Program Execution never owns release authority."""\n    return False\n\n\ndef refuse_publication(action: str) -> None:\n    """Fail closed on every remote publication attempt from Program Execution."""\n    raise CampaignError(\n        f"Program Execution is permanently local-commit-only; refusing to {action}. "\n        f"Campaign execution ends at '{AUTONOMOUS_LAST_STAGE}' with verified local commits. "\n        "Publish separately with `PR_REMEDIATE=0 make pr`; merge only through "\n        "/l9-pr-remediation. L9_PE_RELEASE_AUTHORIZED cannot widen PE authority."\n    )\n\n\n_PUBLICATION_GIT_SUBCOMMANDS''',
    flags=re.S,
)
replace_once(
    RUN,
    '''def normalize_until(until: str) -> str:\n    mapped = UNTIL_ALIASES.get(until, until)\n    if mapped not in STAGE_INDEX:\n        raise CampaignError(\n            "until must be one of " + ", ".join(UNTIL_STAGES + tuple(UNTIL_ALIASES))\n        )\n    return mapped\n''',
    '''def normalize_until(until: str) -> str:\n    mapped = UNTIL_ALIASES.get(until, until)\n    if until in LEGACY_PUBLICATION_STAGES or mapped in PUBLICATION_STAGES:\n        refuse_publication(f"run campaign stage {until!r}")\n    if mapped not in UNTIL_STAGES:\n        raise CampaignError(\n            "until must be one of " + ", ".join(UNTIL_STAGES + tuple(UNTIL_ALIASES))\n        )\n    return mapped\n''',
)
# Direct unit calls must classify historical merge as publication too.
replace_once(
    RUN,
    'if resolved in PUBLICATION_STAGES:\n',
    'if until in LEGACY_PUBLICATION_STAGES or resolved in PUBLICATION_STAGES:\n',
)

# ---------------------------------------------------------------------------
# PE-EXEC-001: route production execution through Peer Core + bounded scheduler.
# Preserve the historical hook path only for deterministic embedding/unit tests.
# ---------------------------------------------------------------------------
PEER_HELPERS = r'''

def _peer_identity() -> tuple[str, str, str | None]:
    """Resolve the live agent/surface identity without inventing a provider."""
    agent_ref = os.environ.get("L9_PE_AGENT_REF", "").strip()
    surface = os.environ.get("L9_PE_SURFACE", "").strip()
    provider_ref = os.environ.get("L9_PE_PROVIDER_REF", "").strip() or None
    if agent_ref and surface:
        return agent_ref, surface, provider_ref
    governance_surface = os.environ.get("L9_GOVERNANCE_SURFACE", "").strip().lower()
    aliases = {
        "claude-code": ("claude-code", "claude-cli"),
        "claude-cli": ("claude-code", "claude-cli"),
        "claude-web": ("claude-code", "claude-web"),
        "claude-mobile": ("claude-code", "claude-mobile"),
        "cursor": ("cursor", "cursor-ide"),
        "cursor-ide": ("cursor", "cursor-ide"),
        "codex": ("codex", "codex-cli"),
        "gemini": ("gemini", "gemini-cli"),
        "manus": ("manus", "manus-web"),
    }
    identity = aliases.get(governance_surface)
    if identity is None:
        raise CampaignError(
            "Peer Execution requires a canonical runtime binding. Set L9_PE_AGENT_REF and "
            "L9_PE_SURFACE, or run from a recognized L9_GOVERNANCE_SURFACE."
        )
    return identity[0], identity[1], provider_ref


def _peer_imports():
    if str(PE_ROOT) not in sys.path:
        sys.path.insert(0, str(PE_ROOT))
    from peer_execution.autonomy.models import (  # noqa: PLC0415
        ActionRuntime,
        ActionSpec,
        ActionStatus,
        CampaignState,
        ConcurrencyBudget,
        ResourceLock,
    )
    from peer_execution.autonomy.scheduler import plan_ready_set  # noqa: PLC0415
    from peer_execution.bindings import resolve_peer_binding  # noqa: PLC0415
    from peer_execution.models import ProbeContext  # noqa: PLC0415
    from peer_execution.runner import run_to_terminal  # noqa: PLC0415
    import provider_loader  # noqa: PLC0415

    return {
        "ActionRuntime": ActionRuntime,
        "ActionSpec": ActionSpec,
        "ActionStatus": ActionStatus,
        "CampaignState": CampaignState,
        "ConcurrencyBudget": ConcurrencyBudget,
        "ResourceLock": ResourceLock,
        "plan_ready_set": plan_ready_set,
        "resolve_peer_binding": resolve_peer_binding,
        "ProbeContext": ProbeContext,
        "run_to_terminal": run_to_terminal,
        "provider_loader": provider_loader,
    }


def _peer_concurrency_budget():
    modules = _peer_imports()
    policy = load_yaml(PE_ROOT / "registry/EXECUTION_CONCURRENCY_POLICY.yaml")
    limits = dict((policy or {}).get("limits") or {})
    return modules["ConcurrencyBudget"](
        total_lanes=int(limits.get("max_active_dispatches") or 1),
        mutation_lanes=int(limits.get("max_mutating_dispatches") or 1),
    )


def _task_target_lineage(task: dict[str, Any]) -> tuple[str, ...]:
    candidates = task.get("target_ids") or task.get("target_id") or task.get("target") or ()
    if isinstance(candidates, str):
        values = [candidates]
    elif isinstance(candidates, (list, tuple)):
        values = [str(item) for item in candidates if item]
    else:
        values = []
    return tuple(values or ["TARGET-001"])


def _plan_peer_task_batch(
    campaign_id: str,
    tasks: list[dict[str, Any]],
    task_states: dict[str, str],
) -> list[str]:
    """Use the canonical scheduler to choose the next non-conflicting ready set."""
    modules = _peer_imports()
    specs: dict[str, Any] = {}
    runtime: dict[str, Any] = {}
    for index, task in enumerate(tasks):
        task_id = str(task["id"])
        resources = [
            modules["ResourceLock"](key=f"target-lineage:{target}", mode="write")
            for target in _task_target_lineage(task)
        ]
        resources.extend(
            modules["ResourceLock"](key=f"path:{path}", mode="write")
            for path in task_output_locations(task)
        )
        specs[task_id] = modules["ActionSpec"](
            action_id=task_id,
            objective=str(task.get("title") or task.get("objective") or task_id),
            depends_on=tuple(
                str(item)
                for item in (task.get("dependencies") or task.get("depends_on") or [])
            ),
            resources=tuple(resources),
            mutation=True,
            authority_granted=True,
            preconditions_satisfied=task_states.get(task_id) not in {"STALE", "CANCELLED"},
            priority=max(0, len(tasks) - index),
        )
        status = task_states.get(task_id)
        runtime[task_id] = modules["ActionRuntime"](
            status=(
                modules["ActionStatus"].COMPLETED
                if status == "COMPLETED"
                else modules["ActionStatus"].PENDING
            )
        )
    state = modules["CampaignState"](
        campaign_id=campaign_id,
        objective=f"Execute {campaign_id} through Peer Execution Core",
        action_specs=specs,
        action_runtime=runtime,
    )
    plan = modules["plan_ready_set"](state, _peer_concurrency_budget())
    return list(plan.selected)


def _run_peer_execution(
    workspace: Path,
    contract: dict[str, Any],
) -> dict[str, Any]:
    """Execute one rendered contract through binding → profile → probe → provider."""
    modules = _peer_imports()
    agent_ref, surface, provider_override = _peer_identity()
    binding = modules["resolve_peer_binding"](
        GOV_ROOT,
        agent_ref=agent_ref,
        surface=surface,
        provider_ref=provider_override,
    )
    runtime_root = workspace / "runtime" / "peer-execution"
    adapter = modules["provider_loader"].instantiate(
        binding.provider_ref,
        runtime_root,
        execution_profile_ref=binding.execution_profile_ref,
        binding_context=binding.to_dict(),
    )
    requested = tuple(str(item) for item in (contract.get("requested_actions") or []))
    probe = adapter.probe(
        modules["ProbeContext"](
            repository_root=str(GOV_ROOT),
            runtime_root=str(runtime_root),
            program_lock_digest=str(contract["program_digest"]),
            requested_capabilities=requested,
            metadata=binding.to_dict(),
        )
    )
    if probe.status != "PASS":
        raise CampaignError(
            f"Peer Execution capability probe blocked {contract.get('task_id')}: "
            f"{probe.blocked_reason or 'UNKNOWN'}"
        )
    prepared = adapter.prepare(contract)
    dispatched = adapter.dispatch(prepared.to_dict())
    dispatch_id = str(dispatched.dispatch_id or prepared.dispatch_id or "")
    terminal = modules["run_to_terminal"](adapter, dispatch_id, dispatched.status)
    if terminal.status != "PASS":
        raise CampaignError(
            f"Peer Execution provider failed {contract.get('task_id')}: {terminal.status}"
        )
    receipt = dict(adapter.collect(dispatch_id))
    adapter.cleanup(dispatch_id)
    return {
        "receipt": receipt,
        "dispatch_id": dispatch_id,
        "provider_ref": binding.provider_ref,
        "execution_profile_ref": binding.execution_profile_ref,
        "agent_ref": binding.agent_ref,
        "surface": binding.surface,
    }


def _dispatch_peer_batch(
    workspace: Path,
    units: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Run provider windows concurrently and harvest every child before returning."""
    from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: PLC0415

    if not units:
        return {}
    outcomes: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(units), thread_name_prefix="pe-peer") as pool:
        futures = {
            pool.submit(_run_peer_execution, workspace, unit["contract"]): str(unit["task_id"])
            for unit in units
        }
        for future in as_completed(futures):
            task_id = futures[future]
            try:
                outcomes[task_id] = future.result()
            except Exception as exc:  # harvest all child outcomes before failing the batch
                failures[task_id] = f"{type(exc).__name__}: {exc}"
    if failures:
        raise CampaignError("Peer Execution batch failed: " + json.dumps(failures, sort_keys=True))
    return outcomes


def _prepare_peer_unit(
    workspace: Path,
    task: dict[str, Any],
    *,
    trace: pe_trace.ExecutionTrace | None,
) -> dict[str, Any]:
    task_id = str(task["id"])
    states = {str(item["id"]): item for item in pec_status_tasks(workspace)}
    state = str((states.get(task_id) or {}).get("runtime_state") or "")
    if state in {"STALE", "CANCELLED", "FAILED"}:
        raise CampaignError(f"{task_id} is {state}; Peer Core does not blind-retry failed attempts")
    contract_path = workspace / "contracts" / "rendered" / f"{task_id}.json"
    worktree = workspace / "worktrees" / task_id
    already_submitted = state in {"SUBMITTED", "VERIFYING"}
    if already_submitted:
        if not contract_path.is_file():
            raise CampaignError(f"{task_id} is {state} without a Rendered Contract")
        rendered = {"contract": str(contract_path)}
    else:
        if state not in {"LEASED", "PREPARED", "CONTRACTED", "EXECUTING"}:
            with traced(trace, "task_prepare", "materialize_contract", task_id=task_id):
                ensure_task_contract(workspace, task_id)
            with traced(trace, "task_prepare", "pec_claim", task_id=task_id):
                pec_cmd(
                    workspace,
                    "claim",
                    task_id,
                    "--holder",
                    "make-campaign",
                    "--ttl-minutes",
                    str(TASK_BUDGET_MINUTES),
                )
            state = "LEASED"
        emit(trace, "TASK_SELECTED", "task", "task_selected", task_id=task_id)
        if state == "LEASED":
            with traced(trace, "task_prepare", "task_worktree_create", task_id=task_id):
                prepared = pec_cmd(workspace, "prepare", task_id)
            worktree = Path(str(prepared.get("worktree") or worktree))
        if state in {"LEASED", "PREPARED"} or not contract_path.is_file():
            with traced(trace, "task_prepare", "render_contract", task_id=task_id):
                rendered = pec_cmd(workspace, "render-contract", task_id)
        else:
            rendered = {"contract": str(contract_path)}
        if state in {"LEASED", "PREPARED", "CONTRACTED"}:
            pec_cmd(workspace, "start", task_id, "--actor", "make-campaign")
    ensure_workspace_wired(worktree)
    emit(
        trace,
        "TASK_WORKTREE_READY",
        "task",
        "task_worktree_ready",
        task_id=task_id,
        metadata={"worktree": str(worktree)},
    )
    contract = json.loads(Path(str(rendered["contract"])).read_text(encoding="utf-8"))
    contract = fill_inferred_validation(Path(str(rendered["contract"])), contract, worktree)
    writable = [str(path) for path in (contract.get("writable_paths") or []) if path]
    if not writable:
        writable = task_output_locations(task)
    return {
        "task": task,
        "task_id": task_id,
        "worktree": worktree,
        "contract": contract,
        "writable": writable,
        "rel": writable[0],
        "title": str(task.get("title") or task_id),
        "already_submitted": already_submitted,
    }


def _finish_peer_unit(
    workspace: Path,
    unit: dict[str, Any],
    outcome: dict[str, Any] | None,
    *,
    trace: pe_trace.ExecutionTrace | None,
    timer: Any,
) -> None:
    task = unit["task"]
    task_id = unit["task_id"]
    worktree = unit["worktree"]
    contract = unit["contract"]
    writable = unit["writable"]
    attempt_number: int | None = None
    if not unit["already_submitted"]:
        if outcome is None:
            raise CampaignError(f"missing Peer Execution outcome for {task_id}")
        receipt = dict(outcome["receipt"])
        changed = [str(path) for path in (receipt.get("changed_files") or [])]
        observed = observe_first_write(worktree, changed)
        if observed:
            emit(
                trace,
                "TASK_FIRST_WRITE",
                "filesystem_write",
                "task_first_write",
                task_id=task_id,
                metadata={"path": observed[0], "changed_paths": observed[:50]},
            )
        validations = [dict(item) for item in (receipt.get("validation_results") or [])]
        emit(
            trace,
            "TASK_VALIDATION_FINISHED",
            "validation",
            "task_validation_finished",
            task_id=task_id,
            metadata={
                "failed": sum(1 for item in validations if item.get("status") != "PASS"),
                "total": len(validations),
                "provider_ref": outcome["provider_ref"],
                "execution_profile_ref": outcome["execution_profile_ref"],
            },
        )
        receipt_path = Path(str(contract["attempt_receipt_path"]))
        if not receipt_path.is_file():
            raise CampaignError(f"Peer Core did not persist attempt receipt for {task_id}")
        with traced(trace, "commit", "record_attempt", task_id=task_id):
            recorded = pec_cmd(workspace, "record-attempt", task_id, "--receipt", str(receipt_path))
        if isinstance(recorded.get("attempt"), int):
            attempt_number = int(recorded["attempt"])

    with timer.stage("task_verify", task_id=task_id):
        verification = traced_verify(
            workspace, task_id, trace=trace, attempt_number=attempt_number
        )
    decision = dispatch_kernel_change(verification)
    if decision["action"] != "pass":
        raise CampaignError(
            f"Diagnose First: Peer Core attempt for {task_id} did not verify cleanly; "
            f"action={decision['action']} reason={decision['reason']}"
        )
    if verification.get("verdict") != "PASSED_LOCAL":
        raise CampaignError(
            f"pec verify {task_id} did not PASS: {verification.get('verdict')}; "
            f"failed gates={json.dumps(failed_gates(verification), sort_keys=True)}"
        )
    # Commit only the exact work the Controller just verified. Provider execution
    # owns mutation; PE retains the local commit boundary.
    candidate = write_and_commit_output(
        worktree,
        unit["rel"],
        unit["title"],
        writable=writable,
    )
    emit(
        trace,
        "TASK_LOCAL_COMMIT",
        "commit",
        "task_local_commit",
        task_id=task_id,
        metadata={"candidate_sha": candidate},
    )
    evidence_id = str(verification["evidence_id"])
    for gate_id in task.get("completion_gates") or task.get("completion_gate_ids") or []:
        pec_cmd(
            workspace,
            "evaluate-gate",
            str(gate_id),
            "PASS",
            "--evidence-id",
            evidence_id,
            "--method",
            "inspection",
            "--actor",
            "make-campaign",
        )
    pec_cmd(
        workspace,
        "complete",
        task_id,
        "--actor",
        "make-campaign",
        "--evidence-id",
        evidence_id,
    )
    emit(
        trace,
        "TASK_COMPLETED",
        "task",
        "task_completed",
        task_id=task_id,
        attempt_number=attempt_number,
        metadata={"evidence_id": evidence_id},
    )


def _default_execute_peer(
    workspace: Path,
    campaign_id: str,
    *,
    hooks: Hooks,
    live_prs: bool,
    trace: pe_trace.ExecutionTrace | None = None,
    timer: Any | None = None,
) -> dict[str, Any]:
    if live_prs:
        refuse_publication("open task pull requests from the live PE runner")
    timing = _load_script("pe_timing", PE_ROOT / "scripts/pe_timing.py")
    timer = timer if timer is not None else timing.StageTimer(workspace)
    tasks = locked_tasks(workspace)
    completed: list[str] = []
    while len(completed) < len(tasks):
        status_rows = pec_status_tasks(workspace)
        task_states = {str(item["id"]): str(item.get("runtime_state") or "") for item in status_rows}
        completed = [task_id for task_id, state in task_states.items() if state == "COMPLETED"]
        if len(completed) == len(tasks):
            break
        selected = _plan_peer_task_batch(campaign_id, tasks, task_states)
        # A resumed SUBMITTED/VERIFYING task needs verification before any new dispatch.
        resumable = [
            str(task["id"])
            for task in tasks
            if task_states.get(str(task["id"])) in {"SUBMITTED", "VERIFYING"}
        ]
        if resumable:
            selected = [resumable[0]]
        if not selected:
            raise CampaignError(
                "Peer scheduler found no runnable task while the program is incomplete: "
                + json.dumps(task_states, sort_keys=True)
            )
        by_id = {str(task["id"]): task for task in tasks}
        units = [_prepare_peer_unit(workspace, by_id[task_id], trace=trace) for task_id in selected]
        dispatch_units = [unit for unit in units if not unit["already_submitted"]]
        for unit in dispatch_units:
            emit(
                trace,
                "TASK_WORKER_STARTED",
                "worker",
                "peer_execution_started",
                task_id=unit["task_id"],
            )
        with timer.stage("task_worker"):
            outcomes = _dispatch_peer_batch(workspace, dispatch_units)
        for unit in units:
            _finish_peer_unit(
                workspace,
                unit,
                outcomes.get(unit["task_id"]),
                trace=trace,
                timer=timer,
            )
    return {"completed": sorted(completed)}
'''

# Keep the current direct-worker loop only as a deterministic hook compatibility
# implementation. Production uses the wrapper inserted below.
replace_once(RUN, 'def default_execute(\n', 'def _default_execute_legacy(\n')
insert_anchor = '\n\ndef run_worker_handoff(\n'
replace_once(RUN, insert_anchor, PEER_HELPERS + insert_anchor)
NEW_WRAPPER = r'''

def default_execute(
    workspace: Path,
    campaign_id: str,
    *,
    hooks: Hooks,
    live_prs: bool,
    trace: pe_trace.ExecutionTrace | None = None,
    timer: Any | None = None,
) -> dict[str, Any]:
    """Execute through Peer Core; hook-owned writes retain the legacy test seam only."""
    if hooks.write_task_output is not None:
        return _default_execute_legacy(
            workspace,
            campaign_id,
            hooks=hooks,
            live_prs=live_prs,
            trace=trace,
            timer=timer,
        )
    return _default_execute_peer(
        workspace,
        campaign_id,
        hooks=hooks,
        live_prs=live_prs,
        trace=trace,
        timer=timer,
    )
'''
replace_once(RUN, '\n\ndef commit_host_emit(', NEW_WRAPPER + '\n\ndef commit_host_emit(')

# Compatibility worker: explicit non-canonical status.
WORKER = 'environment/program-execution/scripts/pe_worker.py'
replace_once(
    WORKER,
    '"""Provider-neutral worker handoff for Program Execution tasks.\n',
    '"""Legacy direct-worker compatibility shim.\n\nThe live `make campaign` path executes through Peer Execution Core. This module\nis retained only for deterministic embedding/tests that intentionally own the\nwrite seam; it is not a canonical production dispatcher.\n\n',
)

# Peer Core canonical receipt chain must serialize digest linking across threads.
BASE = 'environment/program-execution/peer_execution/base.py'
replace_once(BASE, 'import uuid\n', 'import threading\nimport uuid\n')
replace_once(
    BASE,
    'from .schema_registry import SchemaRegistry\n\n\nclass BaseExecutionAdapter:',
    'from .schema_registry import SchemaRegistry\n\n\n_RECEIPT_CHAIN_LOCK = threading.RLock()\n\n\nclass BaseExecutionAdapter:',
)
regex_once(
    BASE,
    r'    def _append\(\n        self,\n        \*,\n        phase: str,\n        binding: ContractBinding \| None,\n        status: str,\n        dispatch_id: str \| None = None,\n        evidence: list\[dict\[str, Any\]\] \| None = None,\n        canonical_error_code: str \| None = None,\n        adapter_error_code: str \| None = None,\n        program_lock_digest: str \| None = None,\n    \) -> LifecycleReceipt:\n.*?        return receipt\n',
    '''    def _append(\n        self,\n        *,\n        phase: str,\n        binding: ContractBinding | None,\n        status: str,\n        dispatch_id: str | None = None,\n        evidence: list[dict[str, Any]] | None = None,\n        canonical_error_code: str | None = None,\n        adapter_error_code: str | None = None,\n        program_lock_digest: str | None = None,\n    ) -> LifecycleReceipt:\n        # Lifecycle receipts form one hash-linked chain per runtime root. The\n        # scheduler may execute provider lanes concurrently, so predecessor read\n        # + receipt construction + append must be one critical section.\n        with _RECEIPT_CHAIN_LOCK:\n            lock_digest = program_lock_digest\n            if binding is not None:\n                lock_digest = binding.program_lock_digest\n            if lock_digest is None:\n                raise ValueError("Program Lock digest is required")\n            receipt = LifecycleReceipt.create(\n                adapter_id=self.adapter_id,\n                adapter_version=self.adapter_version,\n                phase=phase,\n                program_lock_digest=lock_digest,\n                rendered_contract_digest=(binding.rendered_contract_digest if binding else None),\n                task_id=binding.task_id if binding else None,\n                dispatch_id=dispatch_id,\n                status=status,\n                canonical_error_code=canonical_error_code,\n                adapter_error_code=adapter_error_code,\n                evidence=evidence,\n                previous_receipt_digest=self.chain.last_digest(),\n            )\n            errors = self.schemas.validate_lifecycle(receipt.to_dict())\n            if errors:\n                raise ValueError(f"lifecycle receipt schema errors: {errors}")\n            self.chain.append(receipt)\n            return receipt\n''',
    flags=re.S,
)

# ---------------------------------------------------------------------------
# PE-GEN-001: advisory top-level PE manifest cannot block campaign promotion.
# ---------------------------------------------------------------------------
PROMO = 'environment/program-execution/scripts/validate_campaign_promotion.py'
text = read(PROMO)
text = text.replace('import hashlib\n', '')
text = re.sub(r'\nPE_MANIFEST_ROOT = .*?\n', '\n', text, count=1)
text = re.sub(
    r'\n\ndef check_generated_projections\(root: Path\) -> list\[str\]:\n.*?(?=\n\ndef )',
    '',
    text,
    count=1,
    flags=re.S,
)
text = text.replace('    6. Generated projections current: top-level PE MANIFEST digest matches repo\n', '')
text = text.replace('    projection_errors = check_generated_projections(root)\n', '')
text = text.replace('    errors.extend(projection_errors)\n', '')
text = text.replace('        "GENERATED_ARTIFACTS_CURRENT": not projection_errors,\n', '')
write(PROMO, text)

# ---------------------------------------------------------------------------
# Authority doctrine convergence.
# ---------------------------------------------------------------------------
AUTH_SCRIPT = 'skills/l9-pe-campaign-activate/scripts/authorize_campaign_merge.py'
write(
    AUTH_SCRIPT,
    '''#!/usr/bin/env python3\n"""Fail-closed compatibility shim: Program Execution owns no merge authority."""\n\nfrom __future__ import annotations\n\nimport sys\n\n\ndef main() -> int:\n    print(\n        "DENIED: Program Execution owns no merge authority. "\n        "Publish separately with `PR_REMEDIATE=0 make pr`; merge only through "\n        "/l9-pr-remediation.",\n        file=sys.stderr,\n    )\n    return 2\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n''',
)
write(
    'skills/l9-pe-campaign-activate/references/merge-authority.md',
    '''# Merge authority boundary\n\nProgram Execution owns **no** push, pull-request, or merge authority.\n\n`make campaign INTENT=...` terminates after Controller verification and local\ncommits. `L9_PE_RELEASE_AUTHORIZED` is not an authority source and cannot reopen\nremote actions. The compatibility script `authorize_campaign_merge.py` therefore\nfails closed and never writes a merge grant.\n\nAfter PE handoff:\n\n1. Publish through the root L4 surface: `PR_REMEDIATE=0 make pr`.\n2. Converge and merge only through `/l9-pr-remediation`, under the exact approval\n   model owned by `core/shared/AUTHORIZATION_MODEL.yaml`.\n\nCapability never implies authorization. A PE lease or campaign invocation cannot\nmanufacture a remote-action approval.\n''',
)

SKILL = 'skills/l9-pe-campaign-activate/SKILL.md'
skill = read(SKILL)
# Replace the whole human body after metadata with one converged, compact contract.
if not skill.startswith('---'):
    raise SystemExit('unexpected PE activation skill frontmatter')
parts = skill.split('---', 2)
front = '---' + parts[1] + '---\n'
write(
    SKILL,
    front
    + '''\n# PE Campaign Activation\n\n## Purpose\n\nRun the single live Program Execution front door from operator intent through\nBlueprint, Program Lock, bounded Peer Execution, Controller verification, and\n**local commits only**.\n\n```bash\nmake -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>\n```\n\n## Authority law\n\n- Program Execution owns design projection, readiness, leases, worktrees,\n  provider-neutral execution, independent verification, evidence, and local commits.\n- Program Execution **never** pushes, opens/updates a PR, writes merge authority,\n  or merges. `L9_PE_RELEASE_AUTHORIZED` cannot widen this boundary.\n- Publication is a later root operation: `PR_REMEDIATE=0 make pr`.\n- Merge belongs only to `/l9-pr-remediation` under exact approval. Invoking this\n  skill is **not** merge authorization.\n\n## Live path\n\n```text\noperator intent\n  → make campaign\n  → Blueprint / Program Lock / Controller\n  → PE runtime binding + execution profile\n  → fresh capability probe\n  → canonical context manifest\n  → Peer Execution Core → thin provider\n  → typed attempt receipt\n  → Controller verify\n  → local commit\n  → STOP / handoff\n```\n\nThe Controller remains the Program state owner. Peer Execution owns the\nprovider-neutral execution lifecycle only. The bounded scheduler may overlap only\nnon-conflicting ready provider lanes and must harvest every child result; same\ntarget lineage mutation remains serialized by the canonical concurrency policy.\n\n## Stop conditions\n\nStop and report on Program Lock drift, blocked capability probe, missing runtime\nbinding, provider failure, verification failure, scheduler dead-end, lease expiry,\nor any attempted remote publication from PE. Never bypass the tunnel with direct\nPEC mutation commands.\n\n## After PE\n\nA successful PE run hands off verified local commits. Remote publication and merge\nare separate operations with separate authority:\n\n```text\nPE local handoff → PR_REMEDIATE=0 make pr → /l9-pr-remediation\n```\n\nSee `references/pipeline.md` and `references/merge-authority.md`.\n''',
)

PIPE = 'skills/l9-pe-campaign-activate/references/pipeline.md'
pipe = read(PIPE)
pipe = re.sub(
    r'\| execute \|.*?\n\| pr \|.*?\n\| close \|.*?\n',
    '| execute | pec prepares isolated task worktrees; Peer Core resolves binding/profile, probes, compiles context, dispatches thin providers; Controller verifies; runner commits locally; **STOP** |\n',
    pipe,
    count=1,
)
pipe = re.sub(
    r'It never pushes a branch, opens or updates a PR, or merges\. The `pr` and\n`close` stages are a separate governed release transition, entered only with\n`L9_PE_RELEASE_AUTHORIZED=<reason>`; merge authority remains\n`/l9-pr-remediation`\'s alone\.',
    'It never pushes a branch, opens or updates a PR, writes merge authority, or merges. '
    '`L9_PE_RELEASE_AUTHORIZED` cannot widen PE authority. After the PE handoff, root '
    '`PR_REMEDIATE=0 make pr` owns publication and `/l9-pr-remediation` owns merge.',
    pipe,
    count=1,
)
pipe = pipe.replace(
    '`CAMPAIGN_UNTIL` other than `execute` is refused unless\n`L9_CAMPAIGN_UNTIL_DEBUG=1` (runner unit tests only) or the release\ntransition is open.\n',
    '`CAMPAIGN_UNTIL` other than `execute` is refused on the live path; `L9_CAMPAIGN_UNTIL_DEBUG=1` exists only for early-stage runner tests. Publication stages are not PE stages.\n',
)
pipe = pipe.replace(
    '- Stacked PR red → remediate that STACK.json PR only; do not leave the tunnel\n',
    '- Provider or Controller verification failure → stop and report; do not publish from PE\n',
)
write(PIPE, pipe)

SURFACE = 'ops/autonomy/surface_profile.yaml'
surface = read(SURFACE)
surface = surface.replace(
    'Campaigns and `make pr` publish remote PRs',
    'Program Execution campaigns never publish; root `make pr` publishes remote PRs',
)
surface = surface.replace(
    'L9_PE_RELEASE_AUTHORIZED',
    'L9_PE_RELEASE_AUTHORIZED (diagnostic compatibility only; never authority)',
)
write(SURFACE, surface)

README = 'environment/program-execution/campaigns/README.md'
readme = read(README)
if 'PR_REMEDIATE=0 make pr' not in readme:
    readme += '''\n\n## Runtime authority boundary\n\n`make campaign` ends at verified local commits. It never pushes, opens or updates\na PR, writes merge authority, or merges, even when `L9_PE_RELEASE_AUTHORIZED` is\nset. Publish afterward through `PR_REMEDIATE=0 make pr`; merge only through\n`/l9-pr-remediation`.\n'''
write(README, readme)

# ---------------------------------------------------------------------------
# Tests: promotion semantics, permanent local-only authority, live Peer Core.
# ---------------------------------------------------------------------------
PROMO_TEST = 'environment/program-execution/scripts/tests/test_validate_campaign_promotion.py'
t = read(PROMO_TEST)
t = t.replace('import hashlib\n', '')
t = re.sub(r'\n    def regenerate_manifest\(.*?(?=\n    def |\n\nclass )', '\n', t, count=1, flags=re.S)
t = re.sub(r'^\s*self\.regenerate_manifest\([^\n]+\)\n', '', t, flags=re.M)
t = t.replace('"GENERATED_ARTIFACTS_CURRENT": True,\n', '')
# Replace stale/missing blocking tests by advisory proofs without depending on exact method names.
t = re.sub(
    r'    def test_.*?manifest.*?\n(?:(?:        ).*\n)+?(?=    def |\n\nif __name__)',
    '',
    t,
    flags=re.I,
)
insert = '''\n    def test_stale_top_level_pe_manifest_is_advisory(self) -> None:\n        with tempfile.TemporaryDirectory() as raw:\n            root = self.build_repo(Path(raw))\n            manifest = root / "environment/program-execution/MANIFEST.json"\n            manifest.parent.mkdir(parents=True, exist_ok=True)\n            manifest.write_text('{"generated": "stale"}\\n', encoding="utf-8")\n            result = self.mod.validate(root)\n            self.assertEqual(result["errors"], [])\n            self.assertTrue(result["summary"]["all_passed"])\n\n    def test_missing_top_level_pe_manifest_is_advisory(self) -> None:\n        with tempfile.TemporaryDirectory() as raw:\n            root = self.build_repo(Path(raw))\n            manifest = root / "environment/program-execution/MANIFEST.json"\n            if manifest.exists():\n                manifest.unlink()\n            result = self.mod.validate(root)\n            self.assertEqual(result["errors"], [])\n            self.assertTrue(result["summary"]["all_passed"])\n'''
marker = '\n\nif __name__ == "__main__":'
if marker not in t:
    raise SystemExit('promotion test marker missing')
t = t.replace(marker, insert + marker, 1)
write(PROMO_TEST, t)

LOCAL = 'environment/program-execution/scripts/tests/test_pe_local_commit_only.py'
local = read(LOCAL)
local = local.replace('    _worker_command,\n', '    _peer_test_env,\n')
local = local.replace(
    '"L9_PE_WORKER_CMD": _worker_command(tmp),\n                "L9_TEST_SUBPROCESS_LOG": str(log),\n                "PATH": f"{bin_dir}{os.pathsep}{os.environ.get(\'PATH\', \'\')}",',
    '**_peer_test_env(tmp),\n                "L9_TEST_SUBPROCESS_LOG": str(log),\n                "PATH": f"{bin_dir}{os.pathsep}{_peer_test_env(tmp)[\'PATH\']}",',
)
regex_once(
    LOCAL,
    r'    # ---- the release transition still works \(authority preserved\) -----------\n\n    def test_release_transition_reopens_publication\(self\) -> None:\n.*?            self\.assertFalse\(self\.mod\.release_authorized\(\)\)\n',
    '''    # ---- legacy release env cannot widen PE authority -------------------------\n\n    def test_release_environment_never_reopens_publication(self) -> None:\n        with unittest.mock.patch.dict(\n            "os.environ", {"L9_PE_RELEASE_AUTHORIZED": "operator release"}\n        ):\n            self.assertFalse(self.mod.release_authorized())\n            for call in (\n                lambda: self.mod.refuse_publication("push a branch"),\n                lambda: self.mod.refuse_live_until_shortcut("pr"),\n                lambda: self.mod.refuse_live_until_shortcut("close"),\n                lambda: self.mod.refuse_live_until_shortcut("merge"),\n            ):\n                with self.assertRaises(self.mod.CampaignError) as ctx:\n                    call()\n                self.assertIn("permanently local-commit-only", str(ctx.exception))\n''',
    flags=re.S,
)
write(LOCAL, local)

SMOKE = 'environment/program-execution/scripts/tests/test_pe_smoke_campaign.py'
smoke = read(SMOKE)
# Replace direct worker fixture with a deterministic fake Claude CLI that still goes through the real provider.
smoke = re.sub(
    r'# A worker is any command.*?def _worker_command\(tmp: Path\) -> str:\n.*?    return f"\{sys\.executable\} \{script\}"\n',
    r'''# Deterministic fake Claude CLI. The live runner still traverses the real\n# runtime binding, execution profile, capability probe, context manifest,\n# PeerExecutionAdapter, thin claude-code provider, and typed attempt receipt.\nFAKE_CLAUDE = r"""#!/usr/bin/env python3\nimport json, pathlib, subprocess, sys\nprompt = sys.argv[sys.argv.index("-p") + 1]\ncontract = json.loads(prompt.strip().splitlines()[-1])\nworktree = pathlib.Path.cwd()\nchanged = []\nfor rel in contract.get("writable_paths") or []:\n    target = worktree / rel\n    target.parent.mkdir(parents=True, exist_ok=True)\n    target.write_text(\n        f"{contract['task_id']} implemented through Peer Core.\\n" + ("verified " * 8) + "\\n",\n        encoding="utf-8",\n    )\n    changed.append(rel)\nvalidations = []\nfor command in contract.get("validation_commands") or []:\n    completed = subprocess.run(command, cwd=worktree, shell=True, text=True, capture_output=True)\n    validations.append({\n        "command": command,\n        "status": "PASS" if completed.returncode == 0 else "FAIL",\n        "exit_code": completed.returncode,\n        "evidence": (completed.stdout + completed.stderr)[-4000:] or None,\n    })\npayload = {\n    "candidate_sha": None,\n    "changed_files": changed,\n    "validation_results": validations,\n    "residual_unknowns": [],\n    "claimed_status": "completed",\n}\nprint(json.dumps({\n    "is_error": False,\n    "session_id": "smoke-peer-session",\n    "num_turns": 1,\n    "usage": {},\n    "result": payload,\n}))\n"""\n\n\ndef _peer_test_env(tmp: Path) -> dict[str, str]:\n    bin_dir = tmp / "peer-bin"\n    bin_dir.mkdir(parents=True, exist_ok=True)\n    claude = bin_dir / "claude"\n    claude.write_text(FAKE_CLAUDE, encoding="utf-8")\n    claude.chmod(0o755)\n    return {\n        "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",\n        "L9_GOVERNANCE_SURFACE": "claude-code",\n        "L9_PE_AGENT_REF": "claude-code",\n        "L9_PE_SURFACE": "claude-cli",\n    }\n''',
    smoke,
    count=1,
    flags=re.S,
)
smoke = smoke.replace(
    'with unittest.mock.patch.dict("os.environ", {"L9_PE_WORKER_CMD": _worker_command(tmp)}):',
    'with unittest.mock.patch.dict("os.environ", _peer_test_env(tmp)):',
)
smoke = smoke.replace(
    '{"L9_PE_WORKER_CMD": _worker_command(tmp), "L9_CAMPAIGN_UNTIL_DEBUG": "1"},',
    '{**_peer_test_env(tmp), "L9_CAMPAIGN_UNTIL_DEBUG": "1"},',
)
# Worker brief assertions become canonical context/receipt assertions.
smoke = re.sub(
    r'            for task_id in \("TASK-001", "TASK-002"\):\n                brief = workspace / "runtime/worker" / f"\{task_id\}\.BRIEF\.md"\n                self\.assertTrue\(brief\.is_file\(\), msg=f"\{task_id\} never reached a worker"\)\n',
    '''            contexts = list((workspace / "runtime/peer-execution/contexts").glob("*.json"))\n            self.assertGreaterEqual(len(contexts), 2)\n            for context in contexts:\n                payload = json.loads(context.read_text(encoding="utf-8"))\n                self.assertEqual(payload["schema"], "l9.peer-execution.context-manifest.v1")\n''',
    smoke,
    count=1,
)
smoke = re.sub(
    r'                brief = workspace / "runtime/worker" / f"\{task_id\}\.BRIEF\.md"\n                self\.assertTrue\(brief\.is_file\(\), msg=f"no worker brief rendered for \{task_id\}"\)\n',
    '''                attempts = list((workspace / "attempts").rglob(f"*{task_id}*.json"))\n                self.assertTrue(attempts, msg=f"no typed Peer Core attempt receipt for {task_id}")\n''',
    smoke,
    count=1,
)
# Missing direct worker is now a blocked canonical capability probe.
smoke = re.sub(
    r'    def test_implementation_task_without_a_worker_fails_before_verification\(self\) -> None:\n.*?            self\.assertIn\("L9_PE_WORKER_CMD", message\)\n',
    '''    def test_missing_bound_provider_fails_before_verification(self) -> None:\n        with tempfile.TemporaryDirectory() as raw:\n            tmp = Path(raw)\n            env = {\n                key: value\n                for key, value in os.environ.items()\n                if key not in {"L9_PE_AGENT_REF", "L9_PE_SURFACE", "L9_PE_PROVIDER_REF"}\n            }\n            env["L9_GOVERNANCE_SURFACE"] = "claude-code"\n            # Hide any real claude executable from the test.\n            env["PATH"] = os.pathsep.join(\n                part for part in env.get("PATH", "").split(os.pathsep) if "claude" not in part.lower()\n            )\n            with unittest.mock.patch.dict("os.environ", env, clear=True):\n                with self.assertRaises(self.mod.CampaignError) as ctx:\n                    self._run_smoke(tmp)\n            self.assertIn("capability probe blocked", str(ctx.exception))\n\n    def test_scheduler_serializes_same_lineage_and_selects_distinct_lineages(self) -> None:\n        tasks = [\n            {"id": "TASK-001", "title": "A", "target_ids": ["TARGET-A"], "source": {"outputs": [{"location": "a.txt"}]}},\n            {"id": "TASK-002", "title": "B", "target_ids": ["TARGET-A"], "source": {"outputs": [{"location": "b.txt"}]}},\n            {"id": "TASK-003", "title": "C", "target_ids": ["TARGET-B"], "source": {"outputs": [{"location": "c.txt"}]}},\n        ]\n        selected = self.mod._plan_peer_task_batch(\n            "scheduler-smoke", tasks, {task["id"]: "ELIGIBLE" for task in tasks}\n        )\n        self.assertIn("TASK-001", selected)\n        self.assertIn("TASK-003", selected)\n        self.assertNotIn("TASK-002", selected)\n\n    def test_peer_batch_harvests_every_parallel_child(self) -> None:\n        import time as time_module\n        units = [\n            {"task_id": "TASK-A", "contract": {"task_id": "TASK-A"}},\n            {"task_id": "TASK-B", "contract": {"task_id": "TASK-B"}},\n        ]\n\n        def fake_peer(_workspace, contract):\n            time_module.sleep(0.2)\n            return {"receipt": {"task_id": contract["task_id"]}}\n\n        started = time_module.monotonic()\n        with unittest.mock.patch.object(self.mod, "_run_peer_execution", side_effect=fake_peer):\n            outcomes = self.mod._dispatch_peer_batch(Path("."), units)\n        elapsed = time_module.monotonic() - started\n        self.assertEqual(set(outcomes), {"TASK-A", "TASK-B"})\n        self.assertLess(elapsed, 0.35, msg=f"provider windows did not overlap: {elapsed}")\n''',
    smoke,
    count=1,
    flags=re.S,
)
write(SMOKE, smoke)

# Current generic runner tests that deliberately drove the old release transition
# must certify the new permanent boundary instead.
RUN_TEST = 'environment/program-execution/scripts/tests/test_run_campaign.py'
rt = read(RUN_TEST)
rt = rt.replace('until="close"', 'until="execute"')
rt = rt.replace('self.assertEqual(opened, ["demo-activate-v1"])', 'self.assertEqual(opened, [])')
rt = rt.replace('            self.assertIn("close", report.stages_completed)\n', '            self.assertNotIn("close", report.stages_completed)\n')
rt = rt.replace('                "close",\n', '')
write(RUN_TEST, rt)

# Permanent-release env regression can live in the airtight front-door test too.
TUNNEL = 'environment/program-execution/scripts/tests/test_campaign_tunnel_airtight.py'
tunnel = read(TUNNEL)
marker = '\n\nif __name__ == "__main__":'
if marker in tunnel and 'test_release_env_cannot_reopen_remote_stages' not in tunnel:
    addition = '''\n    def test_release_env_cannot_reopen_remote_stages(self) -> None:\n        with unittest.mock.patch.dict(\n            "os.environ", {"L9_PE_RELEASE_AUTHORIZED": "operator release"}\n        ):\n            for stage in ("pr", "close", "merge"):\n                with self.assertRaises(self.mod.CampaignError):\n                    self.mod.normalize_until(stage)\n'''
    tunnel = tunnel.replace(marker, addition + marker, 1)
write(TUNNEL, tunnel)

# Note the resolved policy contradiction without touching unresolved campaign order/state.
TODO = 'TODO.md'
todo = read(TODO)
note = '- [x] PE top-level `environment/program-execution/MANIFEST.json` is advisory/manual; campaign promotion no longer blocks on its freshness. Standalone manifest validation remains strict.\n'
if note not in todo:
    todo += '\n' + note
write(TODO, todo)

print('PE remediation source patch applied')
