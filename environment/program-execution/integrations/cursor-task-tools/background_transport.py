from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from peer_execution.runtime_store import write_json_atomic


class BackgroundTransport:
    def __init__(self, runtime_root: str | Path) -> None:
        self.root = Path(runtime_root).resolve() / "cursor-tasks" / "background"
        self.root.mkdir(parents=True, exist_ok=True)

    def dispatch(self, dispatch_id: str, task: dict[str, Any]) -> Path:
        path = self.root / f"{dispatch_id}.request.json"
        # The host polls this file from another process: write-then-rename.
        write_json_atomic(path, task)
        return path

    def status(self, dispatch_id: str) -> str:
        # Cancellation is the host's termination acknowledgement and outranks
        # any result file: a result that lands after the host cancelled the
        # task is not a pass.
        if (self.root / f"{dispatch_id}.cancelled.json").is_file():
            return "CANCELLED"
        result_path = self.root / f"{dispatch_id}.result.json"
        if not result_path.is_file():
            return "RUNNING"
        if self.binding_error(dispatch_id) is not None:
            return "BLOCKED"
        return "PASS"

    def binding_error(self, dispatch_id: str) -> str | None:
        """Why the result file is not bound to this dispatch, or None.

        A result file is only evidence for a dispatch when it echoes the
        dispatch id and, when the request carried one, the rendered contract
        digest. An unbound file (wrong id, stale contract, no request on
        record) is never treated as a pass.
        """
        result_path = self.root / f"{dispatch_id}.result.json"
        if not result_path.is_file():
            return None
        try:
            value = json.loads(result_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            return f"result is not valid JSON: {exc}"
        if not isinstance(value, dict):
            return "result is not an object"
        request_path = self.root / f"{dispatch_id}.request.json"
        if not request_path.is_file():
            return "no dispatch request on record for this result"
        request = json.loads(request_path.read_text(encoding="utf-8"))
        echoed = value.get("dispatch_id")
        if echoed != dispatch_id:
            return f"result dispatch_id {echoed!r} does not echo {dispatch_id!r}"
        expected_digest = _rendered_contract_digest(request)
        if expected_digest is not None:
            observed = value.get("rendered_contract_digest")
            if observed != expected_digest:
                return (
                    f"result rendered_contract_digest {observed!r} does not echo "
                    f"{expected_digest!r}"
                )
        return None

    def cancel(self, dispatch_id: str) -> bool:
        handle = self.root / f"{dispatch_id}.handle.json"
        if not handle.is_file():
            return False
        marker = self.root / f"{dispatch_id}.cancel.request.json"
        marker.write_text(
            json.dumps({"dispatch_id": dispatch_id, "cancel": True}) + "\n",
            encoding="utf-8",
        )
        return True

    def collect(self, dispatch_id: str) -> dict[str, Any] | None:
        path = self.root / f"{dispatch_id}.result.json"
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Cursor result must be an object")
        if (self.root / f"{dispatch_id}.cancelled.json").is_file():
            return {
                "status": "BLOCKED",
                "dispatch_id": dispatch_id,
                "reason": "host cancelled the task; a later result file is not a pass",
                "evidence": {"type": "cursor_task_cancelled", "dispatch_id": dispatch_id},
                "unbound_result": value,
            }
        problem = self.binding_error(dispatch_id)
        if problem is not None:
            return {
                "status": "BLOCKED",
                "dispatch_id": dispatch_id,
                "reason": problem,
                "evidence": {"type": "cursor_task_result_unbound", "dispatch_id": dispatch_id},
                "unbound_result": value,
            }
        return value


def _rendered_contract_digest(request: Any) -> str | None:
    """The contract digest a dispatch request carries, if any."""
    if not isinstance(request, dict):
        return None
    direct = request.get("rendered_contract_digest")
    if direct:
        return str(direct)
    canonical = request.get("canonical_execution_request")
    if isinstance(canonical, dict) and canonical.get("rendered_contract_digest"):
        return str(canonical["rendered_contract_digest"])
    return None
