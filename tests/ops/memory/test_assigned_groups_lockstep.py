#!/usr/bin/env python3
"""``assigned_groups`` must name real namespaces.

``environment/agents/tools/render_principals.py`` turns each agent's
``assigned_groups`` straight into that principal's write grants, and its own
comment says the list "must stay in lockstep with ops/graphiti/group_registry
.yaml" -- but nothing enforced it. A typo, or a repository that was never
registered, renders a grant for a namespace memory will never resolve, and the
failure surfaces much later as an opaque "namespace did not match any write
grant" at the moment an agent tries to record something.

That is the same silent-drift shape as two disagreeing kind tables: two files
that must agree, with no assertion that they do. This closes it.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / "environment" / "agents" / "agent_registry.yaml"
GROUPS = REPO / "ops" / "graphiti" / "group_registry.yaml"

# ``*`` is the orchestrator wildcard, not a namespace name.
WILDCARD = "*"


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):  # pragma: no cover - corrupt checkout
        raise AssertionError(f"{path} did not parse to a mapping")
    return data


class AssignedGroupsLockstepTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agents = _load(REGISTRY).get("agents") or {}
        registry = _load(GROUPS)
        # A namespace is resolvable if it is a registered repository, a shared
        # read fan-in namespace, or the workspace group itself.
        self.known = set(registry.get("repos") or {})
        self.known.update(registry.get("shared_read_namespaces") or [])
        workspace_group = registry.get("workspace_group")
        if workspace_group:
            self.known.add(str(workspace_group))
        self.assertTrue(self.known, f"no namespaces parsed from {GROUPS}")
        self.forbidden = set(registry.get("forbidden_groups") or [])

    def test_every_assigned_group_is_a_registered_namespace(self) -> None:
        for agent_id, agent in sorted(self.agents.items()):
            for group in agent.get("assigned_groups") or []:
                if group == WILDCARD:
                    continue
                with self.subTest(agent=agent_id, group=group):
                    self.assertIn(
                        group,
                        self.known,
                        f"agent {agent_id} is assigned {group!r}, which is not a "
                        f"group in {GROUPS.relative_to(REPO)}. render_principals "
                        f"would grant a namespace memory cannot resolve.",
                    )

    def test_no_agent_is_assigned_a_forbidden_group(self) -> None:
        """``main`` / ``default`` / ``test`` are never write targets."""
        for agent_id, agent in sorted(self.agents.items()):
            for group in agent.get("assigned_groups") or []:
                with self.subTest(agent=agent_id, group=group):
                    self.assertNotIn(
                        group,
                        self.forbidden,
                        f"agent {agent_id} is assigned forbidden group {group!r}",
                    )

    def test_a_writing_agent_has_at_least_one_grant(self) -> None:
        """An implementer with no grants cannot record anything, silently."""
        writing = {"implementer", "researcher-builder", "orchestrator"}
        for agent_id, agent in sorted(self.agents.items()):
            if agent.get("status") != "active" or agent.get("role") not in writing:
                continue
            with self.subTest(agent=agent_id):
                self.assertTrue(
                    agent.get("assigned_groups"),
                    f"active writing agent {agent_id} has no assigned_groups",
                )


if __name__ == "__main__":
    unittest.main()
