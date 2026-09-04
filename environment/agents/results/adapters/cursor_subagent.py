from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_BRIDGE = Path(__file__).resolve().parents[2] / "cursor-subagents" / "result_bridge.py"


def _load_bridge():
    spec = importlib.util.spec_from_file_location("cursor_result_bridge", _BRIDGE)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {_BRIDGE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cursor_result_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod


result_bridge = _load_bridge()


def normalize(
    surface_result: dict[str, Any],
    *,
    assignment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and digest-bind one Cursor result document.

    The former adapter probed for APIs that the canonical bridge never exposed
    and then fell back to changing only the schema string. This function calls
    the actual bridge contract. Assignment correlation remains optional because
    older lifecycle receipts may not carry every exact result-role field; the
    result gateway independently correlates all identities it does have.
    """

    if not isinstance(surface_result, dict):
        raise ValueError("cursor subagent result must be a JSON object")
    normalized = result_bridge.with_artifact_digest(surface_result)
    if assignment is None:
        return normalized

    # Use the stronger bridge correlation only when the lifecycle assignment
    # contains the exact fields its contract requires.
    document_assignment = normalized["assignment"]
    required = {
        "campaign_id",
        "graph_id",
        "action_id",
        "agent_id",
        "lease_id",
        "base_sha",
    }
    if required.issubset(assignment) and all(assignment.get(key) for key in required):
        exact = {key: assignment[key] for key in required}
        # Scope and subject come from the rendered assignment only. A document
        # that names its own writable paths or its own review subject is
        # self-attesting the very authority the gateway exists to check.
        exact.update(
            {
                "role": result_bridge.canonical_cursor_role(
                    assignment.get("result_role")
                    or assignment.get("subagent_role")
                    or document_assignment["role"]
                ),
                "allowed_paths": list(assignment.get("allowed_paths") or []),
                "action_allowed_paths": list(assignment.get("action_allowed_paths") or []),
                "forbidden_paths": list(assignment.get("forbidden_paths") or []),
            }
        )
        if exact["role"] == "verifier_reviewer":
            exact["subject_agent_id"] = assignment.get("subject_agent_id")
        return result_bridge.validate_result_against_assignment(normalized, exact)
    return normalized
