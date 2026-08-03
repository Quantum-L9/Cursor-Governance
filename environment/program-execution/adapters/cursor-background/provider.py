from __future__ import annotations

from pathlib import Path
from typing import Any

from adapters.common.base import BaseExecutionAdapter
from adapters.common.errors import CanonicalErrorCode
from adapters.common.imports import load_module


class CursorBackgroundAdapter(BaseExecutionAdapter):
    adapter_id = "cursor-background"
    capabilities = ("inspect", "local_write", "artifact_production")
    cancellation = "conditional"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        super().__init__(runtime_root)
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/integrations/cursor-task-tools"
            / "background_transport.py",
            "pes_cursor_background_transport",
        )
        self.transport = module.BackgroundTransport(runtime_root)

    def _probe_status(self, context):
        required = [
            self.repository_root / "autonomy/adapters/cursor/adapter.py",
            self.repository_root / "autonomy/adapters/conformance.py",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        return (
            "PASS" if not missing else "BLOCKED",
            None if not missing else "root-autonomy Cursor provider is unavailable",
            [{"type": "path_probe", "missing": missing}],
        )

    def _dispatch_record(self, record: dict[str, Any]):
        request = {
            "schema": "program-execution-adapter.cursor-task.v1",
            "mode": "background",
            "dispatch_id": record["dispatch_id"],
            "contract": record["contract"],
            "run_in_background": True,
        }
        path = self.transport.dispatch(record["dispatch_id"], request)
        return "RUNNING", [{"type": "cursor_task_request", "path": str(path)}]

    def status(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        host_status = self.transport.status(dispatch_id)
        result = self.transport.collect(dispatch_id)
        if result is not None:
            mapper = load_module(
                Path(__file__).with_name("receipt_mapper.py"),
                "pes_cursor_background_receipt_mapper",
            )
            record["result"] = mapper.map_result(record["contract"], result)
            host_status = "PASS"
        record["status"] = host_status
        self.runtime.save(dispatch_id, record)
        return super().status(dispatch_id)

    def cancel(self, dispatch_id: str):
        record = self.runtime.load(dispatch_id)
        from adapters.common.contracts import validate_contract

        binding = validate_contract(record["contract"])
        if not self.transport.cancel(dispatch_id):
            return self._append(
                phase="cancel",
                binding=binding,
                status="UNSUPPORTED",
                dispatch_id=dispatch_id,
                canonical_error_code=CanonicalErrorCode.CANCELLATION_UNSUPPORTED.value,
                adapter_error_code="CURSOR_TASK_HANDLE_UNAVAILABLE",
            )
        record["status"] = "CANCELLED"
        self.runtime.save(dispatch_id, record)
        return self._append(
            phase="cancel",
            binding=binding,
            status="CANCELLED",
            dispatch_id=dispatch_id,
            evidence=[{"type": "cursor_cancel_request", "accepted": True}],
        )
