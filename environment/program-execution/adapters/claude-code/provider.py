from __future__ import annotations

import os
import shutil
from pathlib import Path

from peer_execution.imports import load_module
from peer_execution.provider import (
    CanonicalExecutionRequest,
    CanonicalProviderResult,
    ProviderInvocation,
    ProviderProbe,
)
from peer_execution.subprocess_runner import run_argv

#: The live enforcement surface a Claude worker window runs behind. Without
#: both of these the PreToolUse wrapper has nothing to authorize through, so a
#: window would write with root authority nobody checked.
HOOK_SURFACE_PATHS = (
    "environment/agents/adapters/claude-code/hooks/local_execution_gate_wrap.py",
    "environment/program-execution/integrations/autonomy-control-plane/program_authority.py",
    "autonomy/adapters/tool_hook.py",
)

#: Authority fields the live hook needs, and nothing else. The sidecar carries
#: more (campaign/graph/action ids, capabilities, the peer binding); exporting
#: those into a worker's environment would widen what a compromised worker can
#: read without widening anything it can do.
_AUTHORITY_ENVIRONMENT = {
    "L9_ADAPTER_SESSION_ID": "adapter_session_id",
    "L9_LEASE_ID": "lease_id",
    "L9_AGENT_ID": "agent_id",
    "L9_AUTONOMY_DATABASE": "runtime_database",
    "L9_AUTONOMY_ROOT": "repository_root",
    "L9_PROGRAM_WORKSPACE": "workspace",
    "L9_PROGRAM_TASK_ID": "task_id",
    "L9_AUTONOMY_AUTHORITY_DIGEST": "authority_digest",
}


class ClaudeCodeProvider:
    provider_id = "claude-code-direct"

    def __init__(self, runtime_root: str | Path, repository_root: str | Path) -> None:
        self.runtime_root = Path(runtime_root).resolve()
        self.repository_root = Path(repository_root).resolve()

    def probe(self, context) -> ProviderProbe:
        executable = shutil.which("claude")
        required = [
            self.repository_root / "autonomy/adapters/claude_code/adapter.py",
            self.repository_root / "autonomy/adapters/conformance.py",
            *(self.repository_root / relative for relative in HOOK_SURFACE_PATHS),
        ]
        missing = [str(path) for path in required if not path.is_file()]
        metadata = self._provider_metadata()
        if executable is None:
            return ProviderProbe(
                status="BLOCKED",
                blocked_reason="claude executable is absent",
                evidence=(
                    {"type": "executable", "path": None},
                    {"type": "path_probe", "missing": missing},
                    {"type": "provider_metadata", **metadata},
                ),
                observed_capabilities=("inspect", "local_write", "artifact_production"),
            )
        return ProviderProbe(
            status="PASS" if not missing else "BLOCKED",
            blocked_reason=(
                None if not missing else "root-autonomy Claude Code provider is unavailable"
            ),
            evidence=(
                {"type": "executable", "path": executable},
                {"type": "path_probe", "missing": missing},
                {"type": "provider_metadata", **metadata},
            ),
            observed_capabilities=("inspect", "local_write", "artifact_production"),
        )

    @staticmethod
    def _provider_metadata() -> dict[str, object]:
        model = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("CLAUDE_MODEL")
        return {
            "provider_surface": "claude-code-cli",
            "backend_mode": (
                "custom_anthropic_compatible"
                if os.environ.get("ANTHROPIC_BASE_URL")
                else "anthropic_default"
            ),
            "model_hint": model,
        }

    def _authority_environment(self, request: CanonicalExecutionRequest) -> dict[str, str]:
        """Task-scoped root authority for the worker window, or fail closed.

        A window that requests mutation without carrying root authority has no
        way to authorize its own effects, and the campaign would only discover
        that after the writes existed.
        """
        authority = request.autonomy_authority
        mutating = bool(set(request.requested_capabilities) & {"local_write", "destructive_change"})
        if authority is None:
            if mutating:
                raise ValueError(
                    "MUTATING_WINDOW_WITHOUT_ROOT_AUTHORITY: "
                    f"{request.task_id} carries no autonomy authority"
                )
            return {}
        environment: dict[str, str] = {}
        for name, field in _AUTHORITY_ENVIRONMENT.items():
            value = authority.get(field)
            if value is None or not str(value).strip():
                if field == "authority_digest":
                    continue
                raise ValueError(f"ROOT_AUTHORITY_INCOMPLETE: missing {field!r}")
            environment[name] = str(value)
        parent = authority.get("program_parent") or {}
        for name, field in (
            ("L9_PROGRAM_LEASE_ID", "lease_id"),
            ("L9_PROGRAM_WORKTREE", "worktree"),
        ):
            value = parent.get(field)
            if value is not None and str(value).strip():
                environment[name] = str(value)
        return environment

    def invoke(self, request: CanonicalExecutionRequest) -> ProviderInvocation:
        permission_profile = dict(request.permission_profile)
        renderer = load_module(
            Path(__file__).with_name("permission_renderer.py"),
            "pes_claude_permission_renderer",
        )
        permissions = renderer.render_permissions(
            permission_profile,
            request.rendered_contract,
        )
        argv = [
            "claude",
            "-p",
            request.worker_instruction,
            "--output-format",
            "json",
            "--max-turns",
            str(int(request.inference_budget.get("max_turns") or 12)),
            "--allowedTools",
            ",".join(permissions["allowed"]),
            "--disallowedTools",
            ",".join(permissions["denied"]),
        ]
        result = run_argv(
            argv,
            cwd=Path(request.worktree_ref).resolve(),
            timeout_seconds=int(request.timeout_budget.get("dispatch_seconds") or 1800),
            environment={
                "L9_AUTONOMY_REQUIRED": "1",
                "L9_PROGRAM_LOCK_DIGEST": request.program_lock_digest,
                **self._authority_environment(request),
            },
        )
        excerpts = load_module(
            Path(__file__).with_name("excerpts.py"),
            "pes_claude_excerpts",
        )
        parser = load_module(
            Path(__file__).with_name("stream_parser.py"),
            "pes_claude_stream_parser",
        )
        parse_error: str | None = None
        try:
            host = parser.parse_claude_json(result.stdout)
        except (TypeError, ValueError) as exc:
            host = {"is_error": True}
            parse_error = type(exc).__name__
        payload = host.get("result_payload")
        if not isinstance(payload, dict):
            payload = {}
        status = "PASS" if result.exit_code == 0 and not host.get("is_error") else "FAIL"
        usage = host.get("usage") if isinstance(host.get("usage"), dict) else {}
        denials = host.get("permission_denials")
        denial_tools = (
            [
                item.get("tool_name")
                for item in denials
                if isinstance(item, dict) and item.get("tool_name")
            ]
            if isinstance(denials, list)
            else []
        )
        host_errors = host.get("errors") if isinstance(host.get("errors"), list) else None
        stdout_text = excerpts.redacted_excerpt(result.stdout)
        stderr_text = excerpts.redacted_excerpt(result.stderr)
        diagnostics = {
            "type": "claude_code_execution",
            "stdout_digest": result.stdout_digest,
            "stderr_digest": result.stderr_digest,
            "num_turns": host.get("num_turns"),
            "is_error": host.get("is_error"),
            "subtype": host.get("subtype"),
            "stop_reason": host.get("stop_reason"),
            "terminal_reason": host.get("terminal_reason"),
            "host_errors": host_errors,
            "permission_denial_tools": denial_tools,
            "result_type": type(host.get("result")).__name__,
            "payload_keys": sorted(payload.keys()),
            "changed_files_type": type(payload.get("changed_files")).__name__,
            "stdout_excerpt": stdout_text,
            "stderr_excerpt": stderr_text,
        }
        transport_evidence = dict(result.to_evidence())
        fail_error: dict[str, object] = {
            "type": "claude_code_error",
            "exit_code": result.exit_code,
            "stderr_digest": result.stderr_digest,
            "stdout_digest": result.stdout_digest,
            "parse_error": parse_error,
            "subtype": host.get("subtype"),
            "host_errors": host_errors,
            "stdout_excerpt": stdout_text,
            "stderr_excerpt": stderr_text,
        }
        if status == "FAIL":
            # Bounded redacted text on FAIL so a digest-only receipt is not the
            # only diagnostic. Digests stay; secrets stay redacted.
            diagnostics["stdout_text"] = stdout_text
            diagnostics["stderr_text"] = stderr_text
            fail_error["stdout_text"] = stdout_text
            fail_error["stderr_text"] = stderr_text
            transport_evidence["stdout_text"] = stdout_text
            transport_evidence["stderr_text"] = stderr_text
        provider_result = CanonicalProviderResult(
            execution_id=request.execution_id,
            status=status,
            structured_payload=payload,
            raw_output_digest=result.stdout_digest,
            provider_metadata=self._provider_metadata(),
            usage=usage,
            session_or_run_id=(
                str(host.get("session_id")) if host.get("session_id") is not None else None
            ),
            observed_capabilities=("inspect", "local_write", "artifact_production"),
            errors=() if status == "PASS" else (fail_error,),
            transport_evidence_refs=(transport_evidence,),
        )
        return ProviderInvocation(
            status=status,
            evidence=(diagnostics,),
            result=provider_result,
        )

    def poll(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(
            status="BLOCKED",
            state=state,
            evidence=({"type": "poll_not_applicable", "execution_id": request.execution_id},),
        )

    def cancel(self, request, state) -> ProviderInvocation:
        return ProviderInvocation(
            status="UNSUPPORTED",
            state=state,
            evidence=({"type": "cancellation_unsupported", "execution_id": request.execution_id},),
        )


PROVIDER_CLASS = ClaudeCodeProvider
