from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.imports import load_module


class CursorForegroundAdapter(BaseExecutionAdapter):
    adapter_id = "cursor-foreground"
    capabilities = ("inspect", "local_write", "artifact_production")
    cancellation = "unsupported"

    def __init__(
        self,
        runtime_root: str | Path,
        repository_root: str | Path,
    ) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        transport_module = load_module(
            self.repository_root
            / "environment/program-execution/integrations/cursor-task-tools"
            / "foreground_transport.py",
            "pes_cursor_foreground_transport",
        )
        self.transport = transport_module.ForegroundTransport(runtime_root)

    def _probe_status(self, context):
        required = [
            self.repository_root / "autonomy/adapters/cursor/adapter.py",
            self.repository_root / "autonomy/adapters/conformance.py",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        status = "PASS" if not missing else "BLOCKED"
        reason = None if not missing else "root-autonomy Cursor provider is unavailable"
        return status, reason, [{"type": "path_probe", "missing": missing}]

    def _dispatch_record(self, record: dict[str, Any]):
        request = {
            "schema": "program-execution-adapter.cursor-task.v1",
            "mode": "foreground",
            "dispatch_id": record["dispatch_id"],
            "contract": record["contract"],
            "run_in_background": False,
        }
        path = self.transport.dispatch(record["dispatch_id"], request)
        return "RUNNING", [{"type": "cursor_task_request", "path": str(path)}]

    def status(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        result = self.transport.collect(dispatch_id)
        if result is not None:
            mapper = load_module(
                Path(__file__).with_name("receipt_mapper.py"),
                "pes_cursor_foreground_receipt_mapper",
            )
            record["result"] = mapper.map_result(record["contract"], result)
            record["status"] = "PASS"
            self.runtime.save(dispatch_id, record)
        return super().status(dispatch_id)
