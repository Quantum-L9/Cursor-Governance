"""Write Graphiti lesson/outcome labels for six declared (action, feedback) pairs.

Never import intelligence/_archived. Never write a registry or threshold file.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

_MAP_PATH = Path(__file__).resolve().parent / "outcome_label_map.yaml"
_WRITE_KIND = "lesson"

WriteFn = Callable[[dict[str, Any]], Any]


def load_outcome_map(path: Path | None = None) -> dict[tuple[str, str], str]:
    import yaml

    raw = yaml.safe_load((path or _MAP_PATH).read_text(encoding="utf-8")) or {}
    out: dict[tuple[str, str], str] = {}
    for row in raw.get("pairs") or []:
        action = str(row.get("action") or "").strip()
        feedback = str(row.get("feedback") or "").strip()
        label = str(row.get("label") or "").strip()
        if action and feedback and label:
            out[(action, feedback)] = label
    return out


def label_for(
    action: str, feedback: str, mapping: dict[tuple[str, str], str] | None = None
) -> str | None:
    table = mapping if mapping is not None else load_outcome_map()
    return table.get((str(action).strip(), str(feedback).strip()))


def write_outcome_label(
    *,
    decision_episode_id: str,
    action: str,
    feedback: str,
    agent_id: str,
    write_fn: WriteFn | None = None,
    mapping: dict[tuple[str, str], str] | None = None,
) -> dict[str, Any] | None:
    """Write a lesson episode for a declared pair. Unknown pairs are no-ops.

    Requires a non-empty decision episode id and agent_id. Unit tests must pass
    write_fn (mock). Live path uses graphiti_memory_client.call_tool.
    """
    episode_id = str(decision_episode_id or "").strip()
    if not episode_id:
        msg = "decision_episode_id is required"
        raise ValueError(msg)
    stamp = str(agent_id or "").strip()
    if not stamp:
        msg = "agent_id is required"
        raise ValueError(msg)
    label = label_for(action, feedback, mapping)
    if label is None:
        return None
    body = (
        f"OUTCOME|decision={episode_id}|action={action}|feedback={feedback}|"
        f"label={label}|agent={stamp}"
    )
    payload = {
        "name": f"outcome-{episode_id}",
        "episode_body": body,
        "source": "text",
        "source_description": f"agent={stamp};kind={_WRITE_KIND}",
        "kind": _WRITE_KIND,
        "agent_id": stamp,
        "decision_episode_id": episode_id,
        "label": label,
    }
    if write_fn is None:

        def _live_write(p: dict[str, Any]) -> Any:
            import graphiti_memory_client as gmc

            return gmc.call_tool("add_memory", p)

        write_fn = _live_write
    result = write_fn(payload)
    return {"wrote": True, "label": label, "kind": _WRITE_KIND, "result": result}
