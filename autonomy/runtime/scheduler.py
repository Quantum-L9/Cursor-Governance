from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from typing import Any

from autonomy.runtime.store import RuntimeStore
from autonomy.runtime.timeutil import utc_now_text
from autonomy.runtime.types import ScheduledAction

TERMINAL_SUCCESS = {"COMPLETED", "SKIPPED"}
ACTIVE_STATUSES = {"LEASED", "RUNNING"}


class Scheduler:
    def __init__(
        self,
        store: RuntimeStore,
        resource_policy: Mapping[str, Any],
    ) -> None:
        self.store = store
        self.resource_policy = resource_policy

    def refresh_readiness(self, campaign_id: str) -> list[str]:
        campaign = self.store.get_campaign(campaign_id)
        graph = json.loads(campaign["graph_json"])
        action_rows = {row["action_id"]: row for row in self.store.list_actions(campaign_id)}
        became_ready: list[str] = []
        now = utc_now_text()
        with self.store.transaction() as connection:
            for action in graph["actions"]:
                row = action_rows[action["id"]]
                if row["status"] not in {
                    "PENDING",
                    "BLOCKED",
                    "INVALIDATED",
                }:
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

    def next_actions(
        self,
        campaign_id: str,
        *,
        limit: int | None = None,
    ) -> list[ScheduledAction]:
        self.refresh_readiness(campaign_id)
        action_rows = self.store.list_actions(campaign_id)
        active_by_resource = Counter(
            row["resource_class"] for row in action_rows if row["status"] in ACTIVE_STATUSES
        )
        resource_classes = self.resource_policy.get(
            "classes",
            {},
        )
        candidates: list[ScheduledAction] = []
        for row in action_rows:
            if row["status"] != "READY":
                continue
            resource_class = row["resource_class"]
            config = resource_classes.get(resource_class)
            if not isinstance(config, Mapping):
                continue
            capacity = int(config.get("capacity", 0))
            if active_by_resource[resource_class] >= capacity:
                continue
            action = json.loads(row["action_json"])
            if action["kind"] == "human_gate":
                continue
            score = float(row["priority_weight"]) * float(row["critical_depth"])
            if action.get("mutation"):
                score *= 1.15
            candidates.append(
                ScheduledAction(
                    action_id=row["action_id"],
                    role=row["role"],
                    resource_class=resource_class,
                    score=score,
                    mutation=bool(row["mutation"]),
                )
            )
        candidates.sort(
            key=lambda item: (
                -item.score,
                item.action_id,
            )
        )
        if limit is not None:
            return candidates[:limit]
        return candidates

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
