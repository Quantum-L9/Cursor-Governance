"""The one public Peer Execution front door (PEC-P2-001, PEC-P3-001).

Live campaign execution enters Peer Execution here and nowhere else. The
front door owns binding resolution, capability probe, dispatch, provider retry
and failover classification, and normalization of the provider's terminal
result. It returns a provider CLAIM -- never a Controller verdict.

Failure taxonomy (remediation §13.1):

* SAFE_BEFORE_DISPATCH  -- the provider never received work (resolution,
  probe, prepare/dispatch failed before a dispatch id existed). An alternate
  provider may be tried immediately, within policy.
* KNOWN_TERMINAL        -- the provider confirmed its execution ended. A retry
  is possible only after the Controller has fenced the prior attempt, because
  the window may have mutated the writable scope.
* AMBIGUOUS_SIDE_EFFECT -- timeout after dispatch, connection lost while the
  worker may still run, termination unconfirmed or unsupported. Never retried
  or failed over here: PROVIDER_FAILOVER_UNSAFE.

Identity is preserved across a failover: Program, lock, task, contract, lease
and worktree never change; the provider ref, its execution id and the front
door's own attempt counter do. The Controller's execution attempt id is
carried through so every history entry names the attempt it served.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .bindings import resolve_peer_binding
from .errors import AdapterFailure, CanonicalErrorCode, canonical_code_for
from .imports import pe_script
from .models import ProbeContext
from .runner import run_to_terminal

PE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PE_ROOT.parents[1]
FAILOVER_POLICY_PATH = PE_ROOT / "registry" / "EXECUTION_FAILOVER_POLICY.yaml"
HEALTH_PATH = PE_ROOT / "registry" / "EXECUTION_ADAPTER_HEALTH.yaml"
RETRY_RECEIPT_SCHEMA = "l9.peer-execution.retry-receipt.v1"

SAFE_BEFORE_DISPATCH = "SAFE_BEFORE_DISPATCH"
KNOWN_TERMINAL = "KNOWN_TERMINAL"
AMBIGUOUS_SIDE_EFFECT = "AMBIGUOUS_SIDE_EFFECT"

PROVIDER_FAILOVER_UNSAFE = "PROVIDER_FAILOVER_UNSAFE"
PROVIDER_RETRY_EXHAUSTED = "PROVIDER_RETRY_EXHAUSTED"
PROVIDER_RESOLUTION_FAILED = "PROVIDER_RESOLUTION_FAILED"

#: Contract actions whose execution mutates the task worktree.
MUTATING_ACTIONS = frozenset({"local_write", "destructive_change", "commit"})


@dataclass(frozen=True)
class PeerExecutionRequest:
    """Everything the front door needs, bound to exact Program identities."""

    workspace: Path
    contract: Mapping[str, Any]
    agent_ref: str
    surface: str
    provider_ref: str | None = None
    autonomy_authority: Mapping[str, Any] | None = None
    attempt_id: str | None = None
    lease_id: str | None = None
    #: Ordered alternate providers for failover, each a provider_ref declared
    #: for this agent/surface in PEER_RUNTIME_BINDINGS.yaml.
    provider_candidates: tuple[str, ...] = ()
    #: Proof that the prior attempt has been fenced by the Controller. Without
    #: it a retry after any dispatch is refused for a mutating contract.
    fence_prior_attempt: Callable[[dict[str, Any]], bool] | None = None
    repository_root: Path | None = None

    @property
    def task_id(self) -> str:
        return str(self.contract.get("task_id") or "")

    @property
    def mutating(self) -> bool:
        requested = {str(item) for item in (self.contract.get("requested_actions") or [])}
        return bool(requested & MUTATING_ACTIONS)


@dataclass
class FailoverPolicy:
    maximum_automatic_retries: int = 0
    retryable: frozenset[str] = frozenset()
    non_retryable: frozenset[str] = frozenset()
    rules: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path = FAILOVER_POLICY_PATH) -> FailoverPolicy:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            maximum_automatic_retries=int(value.get("maximum_automatic_retries") or 0),
            retryable=frozenset(str(item) for item in value.get("retryable") or []),
            non_retryable=frozenset(str(item) for item in value.get("non_retryable") or []),
            rules=tuple(str(item) for item in value.get("rules") or []),
        )


@dataclass
class ProviderHealth:
    """Advisory ordering only. Never bypasses a live probe, never blacklists."""

    entries: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = HEALTH_PATH) -> ProviderHealth:
        if not path.is_file():
            return cls()
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            {
                str(item.get("adapter_id")): str(item.get("status") or "UNKNOWN")
                for item in value.get("entries") or []
                if isinstance(item, dict) and item.get("adapter_id")
            }
        )

    def order(self, candidates: list[str | None]) -> list[str | None]:
        """Known-unhealthy candidates last, everything else in declared order."""
        healthy = [c for c in candidates if self.entries.get(str(c), "UNKNOWN") != "UNHEALTHY"]
        unhealthy = [c for c in candidates if c not in healthy]
        return healthy + unhealthy


# ------------------------------------------------------------------ lifecycle
def resolve_provider(
    *,
    workspace: Path,
    agent_ref: str,
    surface: str,
    provider_ref: str | None,
    repository_root: Path | None = None,
) -> tuple[Any, Any, Path]:
    binding = resolve_peer_binding(repository_root or REPO_ROOT, agent_ref, surface, provider_ref)
    runtime = workspace / "runtime" / "peer-execution"
    adapter = pe_script("provider_loader").instantiate(
        binding.provider_ref,
        runtime,
        execution_profile_ref=binding.execution_profile_ref,
        binding_context=binding.to_dict(),
    )
    return binding, adapter, runtime


def probe_provider(
    *,
    binding: Any,
    adapter: Any,
    runtime: Path,
    program_digest: str,
    requested_capabilities: tuple[str, ...] = (),
    repository_root: Path | None = None,
) -> Any:
    return adapter.probe(
        ProbeContext(
            repository_root=str(repository_root or REPO_ROOT),
            runtime_root=str(runtime),
            program_lock_digest=program_digest,
            requested_capabilities=requested_capabilities,
            metadata=binding.to_dict(),
        )
    )


def bind_root_authority(
    *, adapter: Any, contract: Mapping[str, Any], autonomy_authority: Mapping[str, Any] | None
) -> None:
    """Attach this task's root authority to the adapter, or fail closed."""
    binder = getattr(adapter, "bind_autonomy_authority", None)
    requested = {str(item) for item in (contract.get("requested_actions") or [])}
    if autonomy_authority is None:
        if requested & MUTATING_ACTIONS:
            raise ValueError(
                "MUTATING_DISPATCH_WITHOUT_ROOT_AUTHORITY: "
                f"{contract.get('task_id')!r} requests mutation with no root autonomy authority"
            )
        if callable(binder):
            binder(None)
        return
    if not callable(binder):
        raise ValueError(
            "ADAPTER_CANNOT_CARRY_ROOT_AUTHORITY: "
            f"{type(adapter).__name__} has no autonomy authority carrier"
        )
    binder(dict(autonomy_authority))


def dispatch_provider(
    *,
    contract: Mapping[str, Any],
    adapter: Any,
    autonomy_authority: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """prepare + dispatch. Returns (dispatch_id, prepared, dispatched)."""
    bind_root_authority(adapter=adapter, contract=contract, autonomy_authority=autonomy_authority)
    prepared = adapter.prepare(dict(contract))
    dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
    return str(prepared.dispatch_id), prepared.to_dict(), dispatched.to_dict()


def await_provider(*, adapter: Any, dispatch_id: str, initial_status: str) -> Any:
    """Poll to a terminal status under the profile's timeout policy."""
    return run_to_terminal(adapter, dispatch_id, initial_status)


def collect_provider(*, adapter: Any, dispatch_id: str) -> dict[str, Any]:
    return dict(adapter.collect(dispatch_id))


def root_authority_evidence(
    autonomy_authority: Mapping[str, Any] | None, result: Any
) -> dict[str, Any] | None:
    """Correlation only: which lease/session this dispatch ran under."""
    if autonomy_authority is None:
        return None
    changed = result.get("changed_files") if isinstance(result, dict) else None
    return {
        "task_id": autonomy_authority.get("task_id"),
        "lease_id": autonomy_authority.get("lease_id"),
        "adapter_session_id": autonomy_authority.get("adapter_session_id"),
        "agent_id": autonomy_authority.get("agent_id"),
        "authority_digest": autonomy_authority.get("authority_digest"),
        "runtime_database": autonomy_authority.get("runtime_database"),
        "provider_reported_changed_files": sorted(
            {str(item) for item in changed} if isinstance(changed, list) else set()
        ),
    }


class _DefaultLifecycle:
    resolve_provider = staticmethod(resolve_provider)
    probe_provider = staticmethod(probe_provider)
    dispatch_provider = staticmethod(dispatch_provider)
    await_provider = staticmethod(await_provider)
    collect_provider = staticmethod(collect_provider)


# ------------------------------------------------------------ classification
def _canonical_code(value: Any, policy: FailoverPolicy | None = None) -> str | None:
    """The failure code the failover policy reasons about.

    EXECUTION_FAILOVER_POLICY.yaml names transport-level codes (HOST_TRANSIENT,
    NETWORK_TRANSIENT, RATE_LIMITED) that the adapter error enum does not
    define; the policy's own vocabulary is authoritative for retry decisions,
    so a reason that names one of its codes -- bare or as a prefix -- is kept
    verbatim before any enum or registry mapping is consulted.
    """
    if value is None:
        return None
    text = str(value)
    if policy is not None:
        vocabulary = policy.retryable | policy.non_retryable
        head = text.split(":", 1)[0].strip()
        if head in vocabulary:
            return head
    try:
        return CanonicalErrorCode(text).value
    except ValueError:
        mapped = canonical_code_for(text)
        return mapped.value if mapped else None


def _retryable(policy: FailoverPolicy, code: str | None, *, transient: bool = False) -> bool:
    if code in policy.non_retryable:
        return False
    if code in policy.retryable:
        return True
    return transient


def classify_outcome(outcome: Any) -> tuple[str, str]:
    """(failure_class, reason) for a ProviderRunOutcome that is not PASS."""
    status = str(getattr(outcome, "status", "UNKNOWN"))
    if getattr(outcome, "timed_out", False):
        termination = str(getattr(outcome, "termination", None) or "unknown")
        if termination == "confirmed":
            return KNOWN_TERMINAL, "peer_execution_timeout"
        return AMBIGUOUS_SIDE_EFFECT, f"peer_execution_timeout:termination_{termination}"
    if status in {"FAIL", "BLOCKED", "CANCELLED", "UNSUPPORTED"}:
        return KNOWN_TERMINAL, f"provider_status_{status.lower()}"
    return AMBIGUOUS_SIDE_EFFECT, f"provider_status_{status.lower()}"


# ---------------------------------------------------------------- execution
class RetryReceiptUnrecorded(RuntimeError):
    """The retry receipt could not be persisted, so the try is NOT recorded.

    "Every try is recorded in ``runtime/peer-execution/retry-receipts/``" is the
    front door's contract (README). A receipt write that failed used to be
    swallowed into ``retry_receipt=""`` while the claim was still returned as
    if recorded (audit R5) — the Controller then had a provider claim with no
    durable record of the attempts behind it. The claim travels on the
    exception (``result``) for diagnostics; it is never returned as a success.
    """

    def __init__(self, target: Path, cause: OSError, result: dict[str, Any]) -> None:
        super().__init__(f"RETRY_RECEIPT_UNRECORDED: cannot write {target}: {cause}")
        self.target = target
        self.cause = cause
        self.result = result


def _write_retry_receipt(request: PeerExecutionRequest, payload: dict[str, Any]) -> Path:
    """Persist the retry receipt atomically. Raises OSError; never returns None."""
    root = request.workspace / "runtime" / "peer-execution" / "retry-receipts"
    root.mkdir(parents=True, exist_ok=True)
    name = f"{request.task_id or 'task'}-{request.attempt_id or 'attempt'}.json"
    target = root / name
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=root, delete=False) as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        temp = handle.name
    os.replace(temp, target)
    return target


def retry_receipt_target(request: PeerExecutionRequest) -> Path:
    root = request.workspace / "runtime" / "peer-execution" / "retry-receipts"
    return root / f"{request.task_id or 'task'}-{request.attempt_id or 'attempt'}.json"


def execute(
    request: PeerExecutionRequest,
    *,
    lifecycle: Any | None = None,
    policy: FailoverPolicy | None = None,
    health: ProviderHealth | None = None,
) -> dict[str, Any]:
    """Run one rendered contract through Peer Execution. Returns a provider claim.

    The result never carries a Controller verdict. `status` is the provider's
    terminal status; `receipt` is its terminal result; `failure_class` and
    `attempts` say what the front door did about failures and why.
    """
    lifecycle = lifecycle or _DefaultLifecycle()
    policy = policy or FailoverPolicy.load()
    health = health or ProviderHealth.load()
    contract = dict(request.contract)
    program_digest = str(
        contract.get("program_digest") or contract.get("program_lock_digest") or ""
    )
    requested = tuple(str(item) for item in (contract.get("requested_actions") or []))
    candidates: list[str | None] = [request.provider_ref]
    for item in request.provider_candidates:
        if item not in candidates:
            candidates.append(item)
    candidates = health.order(candidates)
    budget = 1 + max(0, policy.maximum_automatic_retries)
    history: list[dict[str, Any]] = []
    identity = {
        "task_id": request.task_id,
        "attempt_id": request.attempt_id,
        "lease_id": request.lease_id,
        "contract_digest": str(contract.get("contract_digest") or ""),
        "program_digest": program_digest,
        "base_sha": str(contract.get("base_sha") or ""),
        "agent_ref": request.agent_ref,
        "surface": request.surface,
    }
    last_failure: dict[str, Any] | None = None
    unsafe = False

    def record(entry: dict[str, Any]) -> None:
        history.append({**identity, "provider_attempt": len(history) + 1, **entry})

    def finish(result: dict[str, Any]) -> dict[str, Any]:
        result.update(identity)
        result["attempts"] = history
        result["failover_unsafe"] = unsafe
        payload = {
            "schema": RETRY_RECEIPT_SCHEMA,
            **identity,
            "status": result.get("status"),
            "failure_class": result.get("failure_class"),
            "reason": result.get("reason"),
            "failover_unsafe": unsafe,
            "attempts": history,
        }
        try:
            result["retry_receipt"] = str(_write_retry_receipt(request, payload))
        except OSError as exc:
            # Fail closed: an unrecorded try is a contract violation, not a
            # blank field. The claim rides the exception for diagnostics.
            result["retry_receipt"] = ""
            raise RetryReceiptUnrecorded(retry_receipt_target(request), exc, result) from exc
        return result

    for candidate in candidates:
        if len(history) >= budget:
            break
        provider_ref = candidate
        # --- resolution (SAFE_BEFORE_DISPATCH on failure) --------------------
        try:
            binding, adapter, runtime = lifecycle.resolve_provider(
                workspace=request.workspace,
                agent_ref=request.agent_ref,
                surface=request.surface,
                provider_ref=provider_ref,
                repository_root=request.repository_root,
            )
        except (ValueError, AdapterFailure) as exc:
            record(
                {
                    "provider_ref": provider_ref,
                    "stage": "resolve",
                    "status": "FAIL",
                    "failure_class": SAFE_BEFORE_DISPATCH,
                    "reason": f"{PROVIDER_RESOLUTION_FAILED}: {exc}",
                }
            )
            last_failure = history[-1]
            continue
        provider_ref = binding.provider_ref
        try:
            profile_retries = int(
                (getattr(adapter, "execution_profile", {}) or {})
                .get("retry_policy", {})
                .get("max_attempts")
                or 1
            )
        except (TypeError, ValueError, AttributeError):
            profile_retries = 1
        for _ in range(max(1, profile_retries)):
            if len(history) >= budget:
                break
            # --- probe (SAFE_BEFORE_DISPATCH on BLOCKED) -----------------------
            probe = lifecycle.probe_provider(
                binding=binding,
                adapter=adapter,
                runtime=runtime,
                program_digest=program_digest,
                requested_capabilities=requested,
                repository_root=request.repository_root,
            )
            if str(getattr(probe, "status", "")) != "PASS":
                reason = str(getattr(probe, "blocked_reason", None) or "UNKNOWN")
                code = _canonical_code(reason, policy)
                record(
                    {
                        "provider_ref": provider_ref,
                        "stage": "probe",
                        "status": "BLOCKED",
                        "failure_class": SAFE_BEFORE_DISPATCH,
                        "reason": reason,
                        "canonical_error_code": code,
                        "retryable": _retryable(policy, code),
                    }
                )
                last_failure = history[-1]
                if not _retryable(policy, code):
                    break  # this provider cannot serve; next candidate, not next try
                continue
            # --- dispatch (SAFE_BEFORE_DISPATCH until a dispatch id exists) ---
            try:
                dispatch_id, prepared, dispatched = lifecycle.dispatch_provider(
                    contract=contract,
                    adapter=adapter,
                    autonomy_authority=request.autonomy_authority,
                )
            except AdapterFailure as exc:
                code = exc.code.value
                record(
                    {
                        "provider_ref": provider_ref,
                        "stage": "dispatch",
                        "status": "FAIL",
                        "failure_class": SAFE_BEFORE_DISPATCH,
                        "reason": str(exc),
                        "canonical_error_code": code,
                        "retryable": _retryable(policy, code, transient=exc.transient),
                    }
                )
                last_failure = history[-1]
                if not _retryable(policy, code, transient=exc.transient):
                    break
                continue
            except ValueError as exc:
                # Authority / contract refusal: never retryable, never failover.
                record(
                    {
                        "provider_ref": provider_ref,
                        "stage": "dispatch",
                        "status": "FAIL",
                        "failure_class": SAFE_BEFORE_DISPATCH,
                        "reason": str(exc),
                        "retryable": False,
                    }
                )
                return finish(
                    {
                        "status": "FAIL",
                        "reason": str(exc),
                        "failure_class": SAFE_BEFORE_DISPATCH,
                        "receipt": {},
                        "dispatch_id": "",
                        "provider_ref": provider_ref,
                        "execution_profile_ref": binding.execution_profile_ref,
                    }
                )
            # --- await (post-dispatch: KNOWN_TERMINAL or AMBIGUOUS) ----------
            try:
                outcome = lifecycle.await_provider(
                    adapter=adapter,
                    dispatch_id=dispatch_id,
                    initial_status=str(dispatched.get("status") or "DISPATCHED"),
                )
            except Exception as exc:  # noqa: BLE001 - after dispatch every failure is ambiguous
                record(
                    {
                        "provider_ref": provider_ref,
                        "stage": "await",
                        "status": "UNKNOWN",
                        "failure_class": AMBIGUOUS_SIDE_EFFECT,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "dispatch_id": dispatch_id,
                        "retryable": False,
                    }
                )
                unsafe = True
                return finish(
                    {
                        "status": "UNKNOWN",
                        "reason": PROVIDER_FAILOVER_UNSAFE,
                        "failure_class": AMBIGUOUS_SIDE_EFFECT,
                        "receipt": {},
                        "dispatch_id": dispatch_id,
                        "provider_ref": provider_ref,
                        "execution_profile_ref": binding.execution_profile_ref,
                        "prepare": prepared,
                        "dispatch": dispatched,
                    }
                )
            if str(outcome.status) == "PASS":
                # --- collect (post-dispatch, window confirmed ended) -------
                # The provider said PASS, so its window is KNOWN_TERMINAL and
                # the writable scope may hold its work; a collection failure
                # means the CLAIM is unknown, not that the worker may still
                # run. It used to escape this function as a raw exception,
                # bypassing the failure classifier and the retry receipt
                # (audit R4). Never retried or failed over here: the scope
                # may already be mutated, and the Controller must fence the
                # attempt before anything runs again.
                try:
                    result = lifecycle.collect_provider(adapter=adapter, dispatch_id=dispatch_id)
                except Exception as exc:  # noqa: BLE001 - classify, never escape
                    reason = f"provider_collect_failed: {type(exc).__name__}: {exc}"
                    record(
                        {
                            "provider_ref": provider_ref,
                            "stage": "collect",
                            "status": "UNKNOWN",
                            "failure_class": KNOWN_TERMINAL,
                            "reason": reason,
                            "dispatch_id": dispatch_id,
                            "retryable": False,
                        }
                    )
                    if request.mutating:
                        unsafe = True
                        reason = f"{PROVIDER_FAILOVER_UNSAFE}: {reason}"
                    return finish(
                        {
                            "status": "UNKNOWN",
                            "reason": reason,
                            "failure_class": KNOWN_TERMINAL,
                            "receipt": {},
                            "dispatch_id": dispatch_id,
                            "provider_ref": provider_ref,
                            "execution_profile_ref": binding.execution_profile_ref,
                            "prepare": prepared,
                            "dispatch": dispatched,
                            "run": outcome.to_dict() if hasattr(outcome, "to_dict") else {},
                        }
                    )
                record(
                    {
                        "provider_ref": provider_ref,
                        "stage": "terminal",
                        "status": "PASS",
                        "failure_class": None,
                        "reason": None,
                        "dispatch_id": dispatch_id,
                    }
                )
                return finish(
                    {
                        "status": "PASS",
                        "reason": "",
                        "failure_class": None,
                        "receipt": result,
                        "dispatch_id": dispatch_id,
                        "provider_ref": provider_ref,
                        "execution_profile_ref": binding.execution_profile_ref,
                        "prepare": prepared,
                        "dispatch": dispatched,
                        "probe": probe.to_dict() if hasattr(probe, "to_dict") else {},
                        "binding": binding.to_dict() if hasattr(binding, "to_dict") else {},
                        "run": outcome.to_dict() if hasattr(outcome, "to_dict") else {},
                        "root_authority": root_authority_evidence(
                            request.autonomy_authority, result
                        ),
                    }
                )
            failure_class, reason = classify_outcome(outcome)
            code = _canonical_code(
                (outcome.to_dict().get("cancel_receipt") or {}).get("canonical_error_code")
                if hasattr(outcome, "to_dict")
                else None,
                policy,
            )
            record(
                {
                    "provider_ref": provider_ref,
                    "stage": "terminal",
                    "status": str(outcome.status),
                    "failure_class": failure_class,
                    "reason": reason,
                    "dispatch_id": dispatch_id,
                    "canonical_error_code": code,
                }
            )
            last_failure = history[-1]
            terminal = {
                "status": str(outcome.status),
                "reason": reason,
                "failure_class": failure_class,
                "receipt": {},
                "dispatch_id": dispatch_id,
                "provider_ref": provider_ref,
                "execution_profile_ref": binding.execution_profile_ref,
                "prepare": prepared,
                "dispatch": dispatched,
                "run": outcome.to_dict() if hasattr(outcome, "to_dict") else {},
            }
            if failure_class == AMBIGUOUS_SIDE_EFFECT:
                unsafe = True
                terminal["reason"] = f"{PROVIDER_FAILOVER_UNSAFE}: {reason}"
                return finish(terminal)
            # KNOWN_TERMINAL after a dispatch: the window may have mutated the
            # scope. A further try -- same provider or another -- needs the
            # prior attempt fenced by the Controller; otherwise stop here.
            if request.mutating:
                fence = request.fence_prior_attempt
                fenced = bool(fence(history[-1])) if fence is not None else False
                history[-1]["fenced"] = fenced
                if not fenced:
                    unsafe = True
                    terminal["reason"] = f"{PROVIDER_FAILOVER_UNSAFE}: {reason}"
                    return finish(terminal)
            if not _retryable(policy, code, transient=False) and code is not None:
                return finish(terminal)
            # retryable (or unclassified) known-terminal failure: next try/candidate
            continue
    failure = last_failure or {}
    return finish(
        {
            "status": str(failure.get("status") or "FAIL"),
            "reason": (
                f"{PROVIDER_RETRY_EXHAUSTED}: {failure.get('reason')}"
                if len(history) >= budget
                else str(failure.get("reason") or PROVIDER_RESOLUTION_FAILED)
            ),
            "failure_class": failure.get("failure_class") or SAFE_BEFORE_DISPATCH,
            "receipt": {},
            "dispatch_id": str(failure.get("dispatch_id") or ""),
            "provider_ref": failure.get("provider_ref"),
            "execution_profile_ref": None,
        }
    )
