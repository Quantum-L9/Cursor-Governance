"""PEC-P2-001 / PEC-P3-001: one public Peer Execution front door, fencing-aware failover."""

from __future__ import annotations

import json
import re
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any

from peer_execution.errors import AdapterFailure, CanonicalErrorCode
from peer_execution.front_door import (
    AMBIGUOUS_SIDE_EFFECT,
    KNOWN_TERMINAL,
    PROVIDER_FAILOVER_UNSAFE,
    SAFE_BEFORE_DISPATCH,
    FailoverPolicy,
    PeerExecutionRequest,
    ProviderHealth,
    execute,
)

PE_ROOT = Path(__file__).resolve().parents[2]

POLICY = FailoverPolicy(
    maximum_automatic_retries=2,
    retryable=frozenset({"HOST_TRANSIENT", "NETWORK_TRANSIENT", "RATE_LIMITED"}),
    non_retryable=frozenset(
        {"AUTHORIZATION_INFLATION", "SCOPE_VIOLATION", "CAPABILITY_UNSUPPORTED"}
    ),
)


class _Binding:
    def __init__(self, provider_ref: str) -> None:
        self.provider_ref = provider_ref
        self.execution_profile_ref = "worker-default"
        self.agent_ref = "agent"
        self.surface = "surface"

    def to_dict(self) -> dict[str, str]:
        return {"provider_ref": self.provider_ref}


class _Probe:
    def __init__(self, status: str = "PASS", blocked_reason: str | None = None) -> None:
        self.status = status
        self.blocked_reason = blocked_reason

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "blocked_reason": self.blocked_reason}


class _Outcome:
    def __init__(self, status: str, *, timed_out: bool = False, termination: str | None = None):
        self.status = status
        self.timed_out = timed_out
        self.termination = termination

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "timed_out": self.timed_out, "termination": self.termination}


class _Lifecycle:
    """Scriptable lifecycle: per-provider behaviour for each stage."""

    def __init__(self, script: dict[str, dict[str, Any]], *, max_attempts: int = 1) -> None:
        self.script = script
        self.calls: list[tuple[str, str | None]] = []
        self.max_attempts = max_attempts
        self.dispatches = 0

    def resolve_provider(self, *, provider_ref: str | None, **_: Any) -> tuple[Any, Any, Path]:
        self.calls.append(("resolve", provider_ref))
        name = provider_ref or "default"
        plan = self.script.get(name)
        if plan is None or plan.get("resolve") == "fail":
            raise ValueError(f"no binding for {name}")
        adapter = types.SimpleNamespace(
            execution_profile={"retry_policy": {"max_attempts": self.max_attempts}}
        )
        return _Binding(name), adapter, Path("/tmp/runtime")

    def probe_provider(self, *, binding: Any, **_: Any) -> Any:
        self.calls.append(("probe", binding.provider_ref))
        plan = self.script[binding.provider_ref]
        blocked = plan.get("probe_blocked")
        return _Probe("BLOCKED", blocked) if blocked else _Probe()

    def dispatch_provider(self, *, adapter: Any, **_: Any) -> tuple[str, dict, dict]:
        self.dispatches += 1
        name = next(name for stage, name in reversed(self.calls) if stage == "probe")
        self.calls.append(("dispatch", name))
        plan = self.script[name]
        failure = plan.get("dispatch_raises")
        if failure is not None:
            raise failure
        dispatch_id = f"{name}-d{self.dispatches}"
        return dispatch_id, {"dispatch_id": dispatch_id}, {"status": "DISPATCHED"}

    def await_provider(self, *, dispatch_id: str, **_: Any) -> Any:
        name = dispatch_id.rsplit("-d", 1)[0]
        self.calls.append(("await", name))
        plan = self.script[name]
        if plan.get("await_raises"):
            raise ConnectionError("lost the host")
        return plan.get("outcome") or _Outcome("PASS")

    def collect_provider(self, *, dispatch_id: str, **_: Any) -> dict[str, Any]:
        return {"changed_files": ["docs/result.txt"], "dispatch_id": dispatch_id}


def _request(tmp: Path, *, mutating: bool = True, **kwargs: Any) -> PeerExecutionRequest:
    return PeerExecutionRequest(
        workspace=tmp,
        contract={
            "task_id": "TASK-001",
            "contract_digest": "c" * 64,
            "program_digest": "p" * 64,
            "base_sha": "b" * 40,
            "requested_actions": ["inspect", "local_write"] if mutating else ["inspect"],
        },
        agent_ref="agent",
        surface="surface",
        attempt_id="attempt-0001",
        lease_id="lease-0001",
        **kwargs,
    )


def _run(lifecycle: _Lifecycle, request: PeerExecutionRequest) -> dict[str, Any]:
    return execute(request, lifecycle=lifecycle, policy=POLICY, health=ProviderHealth())


class FailoverTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_provider_unavailable_before_dispatch_fails_over_immediately(self) -> None:
        lifecycle = _Lifecycle({"primary": {"resolve": "fail"}, "alternate": {}})
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["provider_ref"], "alternate")
        self.assertEqual(
            [a["failure_class"] for a in result["attempts"]], [SAFE_BEFORE_DISPATCH, None]
        )
        self.assertEqual(result["attempts"][0]["stage"], "resolve")

    def test_unsupported_capability_does_not_fail_over(self) -> None:
        lifecycle = _Lifecycle(
            {"primary": {"probe_blocked": "CAPABILITY_UNSUPPORTED"}, "alternate": {}}
        )
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        # Non-retryable on this provider; policy still allows the alternate
        # candidate, which is a different provider, and it serves.
        self.assertEqual(result["provider_ref"], "alternate")
        self.assertEqual(result["attempts"][0]["retryable"], False)

    def test_transient_probe_block_retries_within_budget_then_moves_on(self) -> None:
        lifecycle = _Lifecycle(
            {"primary": {"probe_blocked": "HOST_TRANSIENT"}, "alternate": {}}, max_attempts=2
        )
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        probes = [name for stage, name in lifecycle.calls if stage == "probe"]
        self.assertEqual(probes[:2], ["primary", "primary"])
        self.assertEqual(result["provider_ref"], "alternate")

    def test_timeout_before_the_provider_accepts_work_is_safe_to_fail_over(self) -> None:
        lifecycle = _Lifecycle(
            {
                "primary": {
                    "dispatch_raises": AdapterFailure(
                        CanonicalErrorCode.CREDENTIAL_UNAVAILABLE,
                        "host never answered",
                        transient=True,
                    )
                },
                "alternate": {},
            }
        )
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["attempts"][0]["stage"], "dispatch")
        self.assertEqual(result["attempts"][0]["failure_class"], SAFE_BEFORE_DISPATCH)

    def test_timeout_after_execution_started_is_never_failed_over(self) -> None:
        lifecycle = _Lifecycle(
            {
                "primary": {"outcome": _Outcome("FAIL", timed_out=True, termination="unconfirmed")},
                "alternate": {},
            }
        )
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["failure_class"], AMBIGUOUS_SIDE_EFFECT)
        self.assertTrue(result["failover_unsafe"])
        self.assertIn(PROVIDER_FAILOVER_UNSAFE, result["reason"])
        self.assertNotIn(("resolve", "alternate"), lifecycle.calls)
        self.assertEqual(lifecycle.dispatches, 1)

    def test_connection_loss_while_the_worker_may_run_is_ambiguous(self) -> None:
        lifecycle = _Lifecycle({"primary": {"await_raises": True}, "alternate": {}})
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(result["failure_class"], AMBIGUOUS_SIDE_EFFECT)
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(lifecycle.dispatches, 1)

    def test_known_terminal_failure_of_a_mutating_task_needs_fencing_before_retry(self) -> None:
        script = {
            "primary": {"outcome": _Outcome("FAIL", timed_out=True, termination="confirmed")},
            "alternate": {},
        }
        without = _run(
            _Lifecycle(script),
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(without["failure_class"], KNOWN_TERMINAL)
        self.assertTrue(without["failover_unsafe"])
        self.assertEqual(len(without["attempts"]), 1)

        fenced: list[dict[str, Any]] = []
        with_fence = _run(
            _Lifecycle(script),
            _request(
                self.tmp,
                provider_ref="primary",
                provider_candidates=("alternate",),
                fence_prior_attempt=lambda entry: fenced.append(entry) or True,
            ),
        )
        self.assertEqual(with_fence["status"], "PASS")
        self.assertEqual(with_fence["provider_ref"], "alternate")
        self.assertEqual(len(fenced), 1)
        self.assertTrue(with_fence["attempts"][0]["fenced"])

        refused = _run(
            _Lifecycle(script),
            _request(
                self.tmp,
                provider_ref="primary",
                provider_candidates=("alternate",),
                fence_prior_attempt=lambda entry: False,
            ),
        )
        self.assertTrue(refused["failover_unsafe"])
        self.assertFalse(refused["attempts"][0]["fenced"])

    def test_no_two_providers_ever_hold_the_same_scope_at_once(self) -> None:
        script = {
            "primary": {"outcome": _Outcome("FAIL", timed_out=True, termination="confirmed")},
            "alternate": {},
        }
        lifecycle = _Lifecycle(script)
        order: list[str] = []

        def fence(entry: dict[str, Any]) -> bool:
            order.append("fence")
            return True

        original = lifecycle.dispatch_provider

        def dispatch(**kwargs: Any) -> Any:
            order.append("dispatch")
            return original(**kwargs)

        lifecycle.dispatch_provider = dispatch  # type: ignore[method-assign]
        _run(
            lifecycle,
            _request(
                self.tmp,
                provider_ref="primary",
                provider_candidates=("alternate",),
                fence_prior_attempt=fence,
            ),
        )
        self.assertEqual(order, ["dispatch", "fence", "dispatch"])

    def test_retry_limit_reached_is_terminal(self) -> None:
        lifecycle = _Lifecycle(
            {"a": {"resolve": "fail"}, "b": {"resolve": "fail"}, "c": {"resolve": "fail"}, "d": {}}
        )
        result = _run(
            lifecycle, _request(self.tmp, provider_ref="a", provider_candidates=("b", "c", "d"))
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("PROVIDER_RETRY_EXHAUSTED", result["reason"])
        self.assertEqual(len(result["attempts"]), 1 + POLICY.maximum_automatic_retries)
        self.assertNotIn(("resolve", "d"), lifecycle.calls)

    def test_provider_pass_is_a_claim_not_a_verdict(self) -> None:
        result = _run(_Lifecycle({"default": {}}), _request(self.tmp))
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("verdict", result)
        self.assertNotIn("kernel_verdict", result)
        self.assertEqual(result["receipt"]["changed_files"], ["docs/result.txt"])

    def test_retry_preserves_contract_lease_and_attempt_identity(self) -> None:
        lifecycle = _Lifecycle({"primary": {"resolve": "fail"}, "alternate": {}})
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        for entry in result["attempts"]:
            self.assertEqual(entry["contract_digest"], "c" * 64)
            self.assertEqual(entry["lease_id"], "lease-0001")
            self.assertEqual(entry["attempt_id"], "attempt-0001")
            self.assertEqual(entry["base_sha"], "b" * 40)
        self.assertEqual(result["attempts"][0]["provider_attempt"], 1)
        self.assertEqual(result["attempts"][1]["provider_attempt"], 2)

    def test_retry_never_widens_capabilities(self) -> None:
        seen: list[tuple[str, ...]] = []

        class Capturing(_Lifecycle):
            def probe_provider(self, *, requested_capabilities=(), **kwargs: Any) -> Any:
                seen.append(tuple(requested_capabilities))
                return super().probe_provider(**kwargs)

        lifecycle = Capturing({"primary": {"resolve": "fail"}, "alternate": {}})
        _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(seen, [("inspect", "local_write")])

    def test_authority_refusal_never_retries(self) -> None:
        lifecycle = _Lifecycle(
            {
                "primary": {
                    "dispatch_raises": ValueError("MUTATING_DISPATCH_WITHOUT_ROOT_AUTHORITY")
                },
                "alternate": {},
            }
        )
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["attempts"]), 1)
        self.assertNotIn(("resolve", "alternate"), lifecycle.calls)

    def test_retry_receipt_records_the_history(self) -> None:
        lifecycle = _Lifecycle({"primary": {"resolve": "fail"}, "alternate": {}})
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        receipt = json.loads(Path(result["retry_receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema"], "l9.peer-execution.retry-receipt.v1")
        self.assertEqual(len(receipt["attempts"]), 2)
        self.assertEqual(receipt["attempt_id"], "attempt-0001")

    def test_an_unwritable_retry_receipt_fails_closed(self) -> None:
        """Audit R5: "every try is recorded" — a try that cannot be recorded is not returned."""
        from peer_execution.front_door import RetryReceiptUnrecorded

        blocker = self.tmp / "runtime"
        blocker.write_text("not a directory\n", encoding="utf-8")  # mkdir -p will fail here
        lifecycle = _Lifecycle({"primary": {}})
        with self.assertRaises(RetryReceiptUnrecorded) as ctx:
            _run(lifecycle, _request(self.tmp, provider_ref="primary"))
        self.assertIn("RETRY_RECEIPT_UNRECORDED", str(ctx.exception))
        # The claim is diagnostics on the exception, never a returned success.
        self.assertEqual(ctx.exception.result["status"], "PASS")
        self.assertEqual(ctx.exception.result["retry_receipt"], "")

    def test_collect_failure_after_pass_is_classified_not_raised(self) -> None:
        """Audit R4: a collect() exception is a KNOWN_TERMINAL collect-stage failure.

        The provider confirmed its window ended, so the scope may hold its work;
        the claim is unknown. It is recorded, never retried or failed over, and
        unsafe for a mutating contract until the Controller fences the attempt.
        """

        class _CollectFails(_Lifecycle):
            def collect_provider(self, *, dispatch_id: str, **_: Any) -> dict[str, Any]:
                raise OSError("receipt directory vanished")

        lifecycle = _CollectFails({"primary": {}, "alternate": {}})
        result = _run(
            lifecycle,
            _request(self.tmp, provider_ref="primary", provider_candidates=("alternate",)),
        )
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["failure_class"], KNOWN_TERMINAL)
        self.assertTrue(result["failover_unsafe"])
        self.assertIn(PROVIDER_FAILOVER_UNSAFE, result["reason"])
        self.assertIn("provider_collect_failed", result["reason"])
        self.assertEqual(result["attempts"][-1]["stage"], "collect")
        self.assertEqual(result["attempts"][-1]["status"], "UNKNOWN")
        self.assertFalse(result["attempts"][-1]["retryable"])
        self.assertEqual(lifecycle.dispatches, 1)
        self.assertNotIn(("resolve", "alternate"), lifecycle.calls)
        receipt = json.loads(Path(result["retry_receipt"]).read_text(encoding="utf-8"))
        self.assertEqual(receipt["attempts"][-1]["stage"], "collect")

    def test_collect_failure_of_an_inspection_task_is_terminal_but_not_unsafe(self) -> None:
        class _CollectFails(_Lifecycle):
            def collect_provider(self, *, dispatch_id: str, **_: Any) -> dict[str, Any]:
                raise RuntimeError("collector crashed")

        lifecycle = _CollectFails({"primary": {}})
        result = _run(lifecycle, _request(self.tmp, mutating=False, provider_ref="primary"))
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["failure_class"], KNOWN_TERMINAL)
        self.assertFalse(result["failover_unsafe"])
        self.assertNotIn(PROVIDER_FAILOVER_UNSAFE, result["reason"])


class ProviderHealthTests(unittest.TestCase):
    def test_stale_unhealthy_is_deprioritized_never_removed(self) -> None:
        health = ProviderHealth({"primary": "UNHEALTHY", "alternate": "UNKNOWN"})
        self.assertEqual(health.order(["primary", "alternate"]), ["alternate", "primary"])

    def test_healthy_record_never_bypasses_the_live_probe(self) -> None:
        lifecycle = _Lifecycle({"primary": {"probe_blocked": "HOST_TRANSIENT"}, "alternate": {}})
        result = execute(
            _request(
                Path(tempfile.mkdtemp()), provider_ref="primary", provider_candidates=("alternate",)
            ),
            lifecycle=lifecycle,
            policy=POLICY,
            health=ProviderHealth({"primary": "HEALTHY"}),
        )
        self.assertIn(("probe", "primary"), lifecycle.calls)
        self.assertEqual(result["provider_ref"], "alternate")

    def test_policy_loads_from_the_registry(self) -> None:
        policy = FailoverPolicy.load()
        self.assertEqual(policy.maximum_automatic_retries, 2)
        self.assertIn("HOST_TRANSIENT", policy.retryable)
        self.assertIn("CAPABILITY_UNSUPPORTED", policy.non_retryable)


class LiveCampaignUsesFrontDoorTests(unittest.TestCase):
    def test_run_campaign_composes_no_private_pipeline_helpers(self) -> None:
        text = (PE_ROOT / "scripts" / "run_campaign.py").read_text(encoding="utf-8")
        for private in ("_resolve_provider", "_probe_provider", "_execute_provider"):
            self.assertNotIn(f"pipeline.{private}", text)
            self.assertNotIn(f"._{private.lstrip('_')}(", text.replace("front_door", ""))
        self.assertIn("front_door.execute(request)", text)
        self.assertIn("PeerExecutionRequest(", text)

    def test_pipeline_facade_delegates_to_the_front_door(self) -> None:
        text = (PE_ROOT / "scripts" / "run_peer_task_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("front_door.dispatch_provider", text)
        self.assertIn("front_door.await_provider", text)
        self.assertNotIn("run_to_terminal(", text)
        self.assertIsNone(re.search(r"^def _resolve_provider\(", text, re.M))


if __name__ == "__main__":
    unittest.main()
