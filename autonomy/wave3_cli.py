from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from autonomy.adapters.claude_code.adapter import build_claude_task
from autonomy.adapters.cursor.adapter import build_cursor_task
from autonomy.adapters.orchestrator import AdapterOrchestrator
from autonomy.io import load_json, write_json
from autonomy.runtime.engine import AutonomyRuntime
from autonomy.validation.simulator import PipelineSimulator


def main() -> int:
    parser = argparse.ArgumentParser(
        description="L9 Wave-3 IDE orchestration CLI."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--database")
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser("register-adapter")
    register.add_argument("--config", required=True)

    deploy = commands.add_parser("deploy")
    deploy.add_argument("--session-id", required=True)
    deploy.add_argument("--campaign-id", required=True)
    deploy.add_argument("--agent-id", required=True)
    deploy.add_argument("--action-id")
    deploy.add_argument("--role")
    deploy.add_argument("--ttl-seconds", type=int)
    deploy.add_argument(
        "--render",
        choices=("raw", "cursor", "claude-code"),
        default="raw",
    )
    deploy.add_argument("--output")

    acknowledge = commands.add_parser("ack")
    acknowledge.add_argument("--session-id", required=True)
    acknowledge.add_argument("--lease-id", required=True)
    acknowledge.add_argument("--agent-id", required=True)
    acknowledge.add_argument("--capability", action="append", default=[])

    authorize = commands.add_parser("authorize")
    authorize.add_argument("--session-id", required=True)
    authorize.add_argument("--lease-id", required=True)
    authorize.add_argument("--agent-id", required=True)
    authorize.add_argument("--capability", required=True)
    authorize.add_argument("--resource")

    heartbeat = commands.add_parser("heartbeat")
    heartbeat.add_argument("--session-id", required=True)
    heartbeat.add_argument("--lease-id", required=True)
    heartbeat.add_argument("--agent-id", required=True)
    heartbeat.add_argument("--base-sha", required=True)
    heartbeat.add_argument("--status", default="running")
    heartbeat.add_argument("--progress-json", default="{}")

    submit = commands.add_parser("submit")
    submit.add_argument("--session-id", required=True)
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--agent-id", required=True)
    submit.add_argument("--artifact", required=True)

    status = commands.add_parser("status")
    status.add_argument("--session-id", required=True)
    status.add_argument("--campaign-id", required=True)

    simulate = commands.add_parser("simulate")
    simulate.add_argument("--graph", required=True)
    simulate.add_argument("--output")

    args = parser.parse_args()
    root = Path(args.root)
    runtime = AutonomyRuntime.from_repository(
        repository_root=root,
        database_path=args.database,
    )
    orchestrator = AdapterOrchestrator(runtime, repository_root=root)

    if args.command == "register-adapter":
        return output(orchestrator.register(load_json(args.config)))
    if args.command == "deploy":
        deployment = orchestrator.request_agent(
            session_id=args.session_id,
            campaign_id=args.campaign_id,
            agent_id=args.agent_id,
            action_id=args.action_id,
            requested_role=args.role,
            ttl_seconds=args.ttl_seconds,
        )
        rendered: Any = deployment
        if args.render == "cursor":
            rendered = build_cursor_task(deployment)
            rendered["environment"]["L9_ADAPTER_SESSION_ID"] = args.session_id
        elif args.render == "claude-code":
            rendered = build_claude_task(deployment)
            rendered["environment"]["L9_ADAPTER_SESSION_ID"] = args.session_id
        if args.output:
            write_json(args.output, rendered)
            return output(
                {
                    "written": args.output,
                    "lease_id": deployment["lease"]["lease_id"],
                }
            )
        return output(rendered)
    if args.command == "ack":
        return output(
            orchestrator.acknowledge_agent(
                session_id=args.session_id,
                lease_id=args.lease_id,
                agent_id=args.agent_id,
                accepted_capabilities=args.capability,
            )
        )
    if args.command == "authorize":
        result = orchestrator.authorize_tool(
            session_id=args.session_id,
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            capability=args.capability,
            resource=args.resource,
        )
        output(result)
        return 0 if result["allowed"] else 1
    if args.command == "heartbeat":
        return output(
            orchestrator.heartbeat(
                session_id=args.session_id,
                lease_id=args.lease_id,
                agent_id=args.agent_id,
                base_sha=args.base_sha,
                status=args.status,
                progress=json.loads(args.progress_json),
            )
        )
    if args.command == "submit":
        return output(
            orchestrator.submit_artifact(
                session_id=args.session_id,
                lease_id=args.lease_id,
                agent_id=args.agent_id,
                artifact=load_json(args.artifact),
            )
        )
    if args.command == "status":
        return output(
            orchestrator.status(
                session_id=args.session_id,
                campaign_id=args.campaign_id,
            )
        )
    if args.command == "simulate":
        result = PipelineSimulator(
            load_json(args.graph),
            load_json(root / "autonomy/policies/resource-classes.json"),
        ).simulate()
        if args.output:
            write_json(args.output, result)
            return output({"written": args.output})
        output(result)
        return 0 if result["valid"] else 1
    parser.error(f"Unsupported command: {args.command}")
    return 2


def output(value: Any) -> int:
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
