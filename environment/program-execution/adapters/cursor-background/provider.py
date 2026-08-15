from __future__ import annotations

from pathlib import Path

from peer_execution.imports import load_module
from peer_execution.provider import (
    CanonicalExecutionRequest,
    CanonicalProviderResult,
    ProviderInvocation,
    ProviderProbe,
)


class CursorBackgroundProvider:
    provider_id = "cursor-background"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()
        module = load_module(
            self.repository_root
            / "environment/program-execution/integrations/cursor-task-tools"
            / "background_transport.py",
            "pes_cursor_background_transport",
        )
        self.transport = module.BackgroundTransport(runtime_root)

    def probe(self, context) -> ProviderProbe:
        required = [
            self.repository_root / "autonomy/adapters/cursor/adapter.py",
            self.repository_root / "autonomy/adapters/conformance.py",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        return ProviderProbe(
            status="BLOCKED",
            blocked_reason="cursor file-drop transport is not a live probe",
            evidence=(
                {
                    "type": "path_probe",
                    "missing": missing,
                    "transport": "file-drop",
                },
            ),
            observed_capabilities=("inspect", "local_write", "artifact_production"),
        )

    def invoke(self, request: CanonicalExecutionRequest) -> ProviderInvocation:
        host_request = {
            "schema": "program-execution-adapter.cursor-task.v1",
            "mode": "background",
            "dispatch_id": request.execution_id,
            "contract": dict(request.rendered_contract),
            "canonical_execution_request": request.to_dict(),
            "run_in_background": True,
        }
        path = self.transport.dispatch(request.execution_id, host_request)
        return ProviderInvocation(
            status="RUNNING",
            state={"request_path": str(path)},
            evidence=({"type": "cursor_task_request", "path": str(path)},),
        )

    def poll(self, request, state) -> ProviderInvocation:
        host_status = self.transport.status(request.execution_id)
        result = self.transport.collect(request.execution_id)
        if result is None:
            return ProviderInvocation(status=str(host_status), state=state)
        raw = result.get("status")
        status = raw if raw == "PASS" else (raw if raw in {"FAIL", "BLOCKED"} else "BLOCKED")
        provider_result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status=status,
            structured_payload=dict(result),
            provider_metadata={"provider_surface": "cursor-background"},
            session_or_run_id=request.execution_id,
            observed_capabilities=("inspect", "local_write", "artifact_production"),
        )
        return ProviderInvocation(
            status=status,
            state=state,
            evidence=({"type": "cursor_task_result", "received": True},),
            result=provider_result,
        )

    def cancel(self, request, state) -> ProviderInvocation:
        accepted = bool(self.transport.cancel(request.execution_id))
        return ProviderInvocation(
            status="CANCELLED" if accepted else "UNSUPPORTED",
            state=state,
            evidence=(
                {
                    "type": "cursor_cancel_request",
                    "execution_id": request.execution_id,
                    "accepted": accepted,
                },
            ),
        )


PROVIDER_CLASS = CursorBackgroundProvider
