from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Mapping
from typing import Any

from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.runtime.engine import AutonomyRuntime


class JsonLineBridge:
    """
    JSON-line stdin bridge into AdapterOrchestrator.

    Each line is a JSON object:
      {"command": "<name>", "arguments": {...}}
    Response lines:
      {"ok": true, "result": {...}}
      {"ok": false, "error": "..."}
    """

    def __init__(self, orchestrator: AdapterOrchestrator) -> None:
        self.orchestrator = orchestrator
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "register": self._register,
            "request_agent": self._request_agent,
            "acknowledge_agent": self._acknowledge_agent,
            "authorize_tool": self._authorize_tool,
            "heartbeat": self._heartbeat,
            "submit_artifact": self._submit_artifact,
            "status": self._status,
            "sweep": self._sweep,
        }

    def handle(
        self,
        command: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Any:
        handler = self._handlers.get(command)
        if handler is None:
            raise ValueError(f"Unknown bridge command: {command!r}")
        return handler(dict(arguments or {}))

    def _register(self, arguments: dict[str, Any]) -> Any:
        config = arguments.get("config")
        if not isinstance(config, dict):
            raise ValueError("register requires arguments.config object")
        return self.orchestrator.register(config)

    def _request_agent(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.request_agent(
            session_id=str(arguments["session_id"]),
            campaign_id=str(arguments["campaign_id"]),
            agent_id=str(arguments["agent_id"]),
            action_id=arguments.get("action_id"),
            requested_role=arguments.get("requested_role"),
            ttl_seconds=arguments.get("ttl_seconds"),
            required_surface_capabilities=list(arguments.get("required_surface_capabilities") or []),
        )

    def _acknowledge_agent(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.acknowledge_agent(
            session_id=str(arguments["session_id"]),
            lease_id=str(arguments["lease_id"]),
            agent_id=str(arguments["agent_id"]),
            accepted_capabilities=list(
                arguments.get("accepted_capabilities") or arguments.get("capabilities") or []
            ),
        )

    def _authorize_tool(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.authorize_tool(
            session_id=str(arguments["session_id"]),
            lease_id=str(arguments["lease_id"]),
            agent_id=str(arguments["agent_id"]),
            capability=str(arguments["capability"]),
            resource=arguments.get("resource"),
            metadata=arguments.get("metadata"),
        )

    def _heartbeat(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.heartbeat(
            session_id=str(arguments["session_id"]),
            lease_id=str(arguments["lease_id"]),
            agent_id=str(arguments["agent_id"]),
            base_sha=str(arguments.get("base_sha") or arguments.get("observed_base_sha")),
            status=str(arguments.get("status", "running")),
            progress=arguments.get("progress"),
        )

    def _submit_artifact(self, arguments: dict[str, Any]) -> Any:
        payload = dict(arguments)
        artifact = payload.pop("artifact", None)
        payload.pop("artifact_path", None)  # path loading removed (Sonar S8707)
        if not isinstance(artifact, dict):
            raise ValueError("submit_artifact requires an in-memory artifact object")
        return self.orchestrator.submit_artifact(artifact=artifact, **payload)

    def _status(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.status(
            session_id=str(arguments["session_id"]),
            campaign_id=str(arguments["campaign_id"]),
        )

    def _sweep(self, arguments: dict[str, Any]) -> Any:
        return self.orchestrator.runtime.leases.sweep()

    def serve(
        self,
        input_stream=None,
        output_stream=None,
    ) -> int:
        stdin = input_stream if input_stream is not None else sys.stdin
        stdout = output_stream if output_stream is not None else sys.stdout
        for raw_line in stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                command = str(message["command"])
                arguments = message.get("arguments") or {}
                result = self.handle(command, arguments)
                response = {"ok": True, "result": result}
            except Exception as exc:
                response = {"ok": False, "error": str(exc)}
            stdout.write(json.dumps(response, sort_keys=True) + "\n")
            stdout.flush()
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="L9 autonomy JSON-line adapter bridge.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--database", help="Runtime SQLite database path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    runtime = AutonomyRuntime.from_repository(
        repository_root=args.root,
        database_path=args.database,
    )
    orchestrator = AdapterOrchestrator(
        runtime,
        repository_root=args.root,
    )
    return JsonLineBridge(orchestrator).serve()


if __name__ == "__main__":
    raise SystemExit(main())
