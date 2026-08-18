"""Saturation-seeking, claim-aware scheduler for the autonomy control plane.

Invariant enforced here:

    MAXIMIZE LEGAL PARALLELISM.

    No independent READY action may remain idle while compatible execution
    capacity exists. Read-only work is bounded by available capacity. Mutation
    work is bounded by actual claim conflict, not by artificial global
    serialization. Concurrency never expands authority.

Admission order matches the campaign concurrency contract: dependency
readiness, campaign authority, role and resource-class ceilings, claim
compatibility, then global provider capacity accounting. Nothing in this module
grants capability, widens scope, or bypasses the lease/claim registry — the
registry stays authoritative and re-checks every claim transactionally when the
lease is issued.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from autonomy.runtime.claims import claims_collide
from autonomy.runtime.store import RuntimeStore
from autonomy.runtime.timeutil import utc_now_text
from autonomy.runtime.types import ScheduledAction, SchedulingCycle

TERMINAL_SUCCESS = {"COMPLETED", "SKIPPED"}
ACTIVE_STATUSES = {"LEASED", "RUNNING"}
UNREADY_STATUSES = {"PENDING", "BLOCKED", "INVALIDATED"}
SATURATE = "saturate"

BUDGET_KEYS = {
    "mutation": "max_mutation_agents",
    "poll": "max_poll_agents",
    "read": "max_read_agents",
}


class Scheduler:
    def __init__(
        self,
        store: RuntimeStore,
        resource_policy: Mapping[str, Any],
    ) -> None:
        self.store = store
        self.resource_policy = resource_policy
        self._role_ceilings: dict[str, dict[str, int]] = {}
        self._provider_ceiling = self._resolve_provider_ceiling()
        self._effective_ceiling = self._provider_ceiling

    # ------------------------------------------------------------------
    # policy accessors
    # ------------------------------------------------------------------

    @property
    def global_policy(self) -> Mapping[str, Any]:
        block = self.resource_policy.get("global", {})
        return block if isinstance(block, Mapping) else {}

    @property
    def resource_classes(self) -> Mapping[str, Any]:
        classes = self.resource_policy.get("classes", {})
        return classes if isinstance(classes, Mapping) else {}

    @property
    def fill_policy(self) -> str:
        return str(self.global_policy.get("fill_policy", SATURATE))

    @property
    def reserved_control_slots(self) -> int:
        return max(0, int(self.global_policy.get("reserved_control_slots", 0)))

    @property
    def provider_concurrency_ceiling(self) -> int:
        """Absolute upstream ceiling, before control-slot reservation."""

        return self._provider_ceiling

    @property
    def worker_concurrency_ceiling(self) -> int:
        """Slots available to workers after control-plane reservation."""

        return max(0, self._effective_ceiling - self.reserved_control_slots)

    def _resolve_provider_ceiling(self) -> int:
        declared = self.global_policy.get("provider_concurrency_ceiling")
        if isinstance(declared, int) and declared > 0:
            return declared
        # No declared provider ceiling: derive one from class capacities so the
        # global accounting is never tighter than the per-class policy already
        # allows. This keeps pre-2.0.0 resource policies working unchanged.
        derived = sum(
            int(config.get("capacity", 0))
            for config in self.resource_classes.values()
            if isinstance(config, Mapping)
        )
        return max(1, derived)

    # ------------------------------------------------------------------
    # adaptive backpressure (provider-driven, never authority-changing)
    # ------------------------------------------------------------------

    @property
    def _backpressure(self) -> Mapping[str, Any]:
        block = self.global_policy.get("adaptive_backpressure", {})
        return block if isinstance(block, Mapping) else {}

    @property
    def backpressure_enabled(self) -> bool:
        return bool(self._backpressure.get("enabled", False))

    def record_provider_throttle(self) -> int:
        """Multiplicative decrease after provider throttling (HTTP 429).

        Returns the effective provider ceiling after the decrease. Callers that
        observe provider throttling report it here instead of shrinking their
        own batch sizes, so the reduction is visible in cycle telemetry.
        """

        if not self.backpressure_enabled:
            return self._effective_ceiling
        factor = float(self._backpressure.get("decrease_factor", 0.75))
        factor = min(max(factor, 0.05), 1.0)
        floor = self.reserved_control_slots + 1
        self._effective_ceiling = max(
            min(floor, self._provider_ceiling),
            math.floor(self._effective_ceiling * factor),
        )
        return self._effective_ceiling

    def record_provider_recovery(self) -> int:
        """Additive increase back toward the declared provider ceiling."""

        if not self.backpressure_enabled:
            return self._effective_ceiling
        step = max(1, self._provider_ceiling // 50)
        self._effective_ceiling = min(
            self._provider_ceiling,
            self._effective_ceiling + step,
        )
        return self._effective_ceiling

    # ------------------------------------------------------------------
    # role authorization ceilings (from the deployment manifest)
    # ------------------------------------------------------------------

    def set_role_ceilings(
        self,
        campaign_id: str,
        ceilings: Mapping[str, int],
    ) -> None:
        """Register deployment role maxima as concurrent-worker ceilings.

        Role cardinality is an authorization ceiling, not a spawn target: an
        unregistered campaign is simply unconstrained by role, and workers are
        only ever admitted when a corresponding READY action exists.
        """

        self._role_ceilings[campaign_id] = {
            str(role): int(maximum) for role, maximum in ceilings.items()
        }

    def role_ceilings(self, campaign_id: str) -> Mapping[str, int]:
        return self._role_ceilings.get(campaign_id, {})

    # ------------------------------------------------------------------
    # readiness
    # ------------------------------------------------------------------

    def refresh_readiness(self, campaign_id: str) -> list[str]:
        campaign = self.store.get_campaign(campaign_id)
        graph = json.loads(campaign["graph_json"])
        action_rows = {row["action_id"]: row for row in self.store.list_actions(campaign_id)}
        became_ready: list[str] = []
        now = utc_now_text()
        with self.store.transaction() as connection:
            for action in graph["actions"]:
                row = action_rows[action["id"]]
                if row["status"] not in UNREADY_STATUSES:
                    continue
                dependencies = action.get("depends_on", [])
                dependencies_complete = all(
                    action_rows[dependency]["status"] in TERMINAL_SUCCESS
                    for dependency in dependencies
                )
                if not dependencies_complete:
                    continue
                if not self._condition_satisfied(
                    action=action,
                    action_rows=action_rows,
                ):
                    continue
                connection.execute(
                    """
                    UPDATE actions
                    SET
                        status = 'READY',
                        failure_reason = NULL,
                        updated_at = ?
                    WHERE campaign_id = ? AND action_id = ?
                    """,
                    (now, campaign_id, action["id"]),
                )
                became_ready.append(action["id"])
        return became_ready

    # ------------------------------------------------------------------
    # admission
    # ------------------------------------------------------------------

    def next_actions(
        self,
        campaign_id: str,
        *,
        limit: int | None = None,
        hard_limit: int | None = None,
    ) -> list[ScheduledAction]:
        """Admit as many legal READY actions as capacity allows.

        `limit` is a legacy caller batch size. Under `fill_policy: saturate` it
        is recorded in telemetry and ignored, so a timid upstream batch request
        cannot serialize otherwise-legal independent work. `hard_limit` is a
        deliberate safety ceiling and always truncates.
        """

        return list(
            self.next_cycle(
                campaign_id,
                limit=limit,
                hard_limit=hard_limit,
            ).selected
        )

    def next_cycle(
        self,
        campaign_id: str,
        *,
        limit: int | None = None,
        hard_limit: int | None = None,
    ) -> SchedulingCycle:
        self.refresh_readiness(campaign_id)
        action_rows = self.store.list_actions(campaign_id)
        budgets = self._campaign_budgets(campaign_id)
        role_ceilings = self.role_ceilings(campaign_id)

        active_rows = [row for row in action_rows if row["status"] in ACTIVE_STATUSES]
        active_by_class = Counter(row["resource_class"] for row in active_rows)
        active_by_role = Counter(row["role"] for row in active_rows)
        active_by_bucket = Counter(self._budget_bucket_row(row) for row in active_rows)
        blocked_dependency = sum(1 for row in action_rows if row["status"] in UNREADY_STATUSES)

        available_global = max(0, self.worker_concurrency_ceiling - len(active_rows))
        global_remaining = available_global

        held_claims = self._active_claims(campaign_id)
        counters: Counter[str] = Counter()
        selected: list[ScheduledAction] = []
        ready_count = 0

        for row, action in self._prioritized_ready(action_rows):
            ready_count += 1
            if action.get("kind") == "human_gate":
                counters["blocked_human_gate"] += 1
                continue
            resource_class = row["resource_class"]
            config = self.resource_classes.get(resource_class)
            if not isinstance(config, Mapping):
                # Never drop an action silently: an undeclared resource class is
                # a policy defect, and it is reported as its own blocking reason.
                counters["blocked_unknown_resource_class"] += 1
                continue
            if global_remaining <= 0:
                counters["blocked_global_capacity"] += 1
                continue
            capacity = int(config.get("capacity", 0))
            if active_by_class[resource_class] >= capacity:
                counters["blocked_resource_capacity"] += 1
                continue
            bucket = self._budget_bucket(
                mutation=bool(row["mutation"]),
                kind=str(row["kind"]),
            )
            budget = budgets.get(bucket)
            if budget is not None and active_by_bucket[bucket] >= budget:
                counters["blocked_campaign_budget"] += 1
                continue
            role = row["role"]
            role_ceiling = role_ceilings.get(role)
            if role_ceiling is not None and active_by_role[role] >= role_ceiling:
                counters["blocked_role_cardinality"] += 1
                continue
            claims = action.get("claims", [])
            if self._claims_conflict(claims, held_claims):
                counters["blocked_claim"] += 1
                continue

            selected.append(
                ScheduledAction(
                    action_id=row["action_id"],
                    role=role,
                    resource_class=resource_class,
                    score=self._score(row, action),
                    mutation=bool(row["mutation"]),
                )
            )
            active_by_class[resource_class] += 1
            active_by_role[role] += 1
            active_by_bucket[bucket] += 1
            global_remaining -= 1
            self._hold_claims(claims, held_claims)

        caller_limit_applied = False
        if self.fill_policy != SATURATE and limit is not None:
            caller_limit_applied = len(selected) > limit
            selected = selected[:limit]
        if hard_limit is not None and len(selected) > hard_limit:
            caller_limit_applied = True
            selected = selected[:hard_limit]

        return SchedulingCycle(
            selected=tuple(selected),
            ready=ready_count,
            running=len(active_rows),
            available_global_slots=available_global,
            blocked_dependency=blocked_dependency,
            blocked_claim=counters["blocked_claim"],
            blocked_resource_capacity=counters["blocked_resource_capacity"],
            blocked_campaign_budget=counters["blocked_campaign_budget"],
            blocked_role_cardinality=counters["blocked_role_cardinality"],
            blocked_global_capacity=counters["blocked_global_capacity"],
            blocked_unknown_resource_class=counters["blocked_unknown_resource_class"],
            blocked_human_gate=counters["blocked_human_gate"],
            caller_limit=limit if limit is not None else hard_limit,
            caller_limit_applied=caller_limit_applied,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _prioritized_ready(
        self,
        action_rows: Sequence[Any],
    ) -> list[tuple[Any, dict[str, Any]]]:
        ready: list[tuple[Any, dict[str, Any]]] = []
        for row in action_rows:
            if row["status"] != "READY":
                continue
            ready.append((row, json.loads(row["action_json"])))
        ready.sort(
            key=lambda item: (
                -self._score(item[0], item[1]),
                item[0]["action_id"],
            )
        )
        return ready

    @staticmethod
    def _score(row: Any, action: Mapping[str, Any]) -> float:
        score = float(row["priority_weight"]) * float(row["critical_depth"])
        if action.get("mutation"):
            score *= 1.15
        return score

    def _campaign_budgets(self, campaign_id: str) -> dict[str, int | None]:
        campaign = json.loads(self.store.get_campaign(campaign_id)["campaign_json"])
        declared = campaign.get("budgets", {})
        if not isinstance(declared, Mapping):
            declared = {}
        budgets: dict[str, int | None] = {}
        for bucket, key in BUDGET_KEYS.items():
            value = declared.get(key)
            budgets[bucket] = int(value) if isinstance(value, int) else None
        return budgets

    @staticmethod
    def _budget_bucket(*, mutation: bool, kind: str) -> str:
        if mutation:
            return "mutation"
        if kind == "poll":
            return "poll"
        return "read"

    def _budget_bucket_row(self, row: Any) -> str:
        return self._budget_bucket(
            mutation=bool(row["mutation"]),
            kind=str(row["kind"]),
        )

    def _active_claims(self, campaign_id: str) -> dict[str, list[tuple[str, bool]]]:
        held: dict[str, list[tuple[str, bool]]] = {}
        with self.store.connect() as connection:
            rows = connection.execute(
                """
                SELECT resource_key, mode, exclusive
                FROM claims
                WHERE campaign_id = ? AND status = 'ACTIVE'
                """,
                (campaign_id,),
            )
            for row in rows:
                held.setdefault(row["resource_key"], []).append(
                    (str(row["mode"]), bool(row["exclusive"]))
                )
        return held

    @staticmethod
    def _claim_shape(claim: Mapping[str, Any]) -> tuple[str, str, bool]:
        key = str(claim["key"])
        mode = str(claim["mode"])
        exclusive = bool(claim.get("exclusive", mode == "write"))
        return key, mode, exclusive

    def _claims_conflict(
        self,
        claims: Sequence[Mapping[str, Any]],
        held: Mapping[str, list[tuple[str, bool]]],
    ) -> bool:
        """Pre-filter admission with the registry's own compatibility rule.

        Claim keys are opaque identifiers: two actions collide when they name
        the same key and `claims_collide` says so. The registry re-checks this
        transactionally at lease time and remains authoritative.
        """

        for claim in claims:
            key, mode, exclusive = self._claim_shape(claim)
            for existing_mode, existing_exclusive in held.get(key, ()):
                if claims_collide(
                    mode=mode,
                    exclusive=exclusive,
                    other_mode=existing_mode,
                    other_exclusive=existing_exclusive,
                ):
                    return True
        return False

    def _hold_claims(
        self,
        claims: Sequence[Mapping[str, Any]],
        held: dict[str, list[tuple[str, bool]]],
    ) -> None:
        for claim in claims:
            key, mode, exclusive = self._claim_shape(claim)
            held.setdefault(key, []).append((mode, exclusive))

    def _condition_satisfied(
        self,
        *,
        action: Mapping[str, Any],
        action_rows: Mapping[str, Any],
    ) -> bool:
        conditional_on = action.get("conditional_on")
        if not conditional_on:
            return True
        condition_row = action_rows.get(conditional_on)
        return condition_row is not None and condition_row["status"] in TERMINAL_SUCCESS
