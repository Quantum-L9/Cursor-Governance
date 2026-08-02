from __future__ import annotations

import argparse
import json
from typing import Any

from autonomy.cli_fs import load_json_cli as load_json
from autonomy.runtime.engine import AutonomyRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="L9 Wave-2 autonomy runtime.")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root.",
    )
    parser.add_argument(
        "--database",
        help="Runtime SQLite database path.",
    )
    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("--campaign", required=True)
    bootstrap.add_argument("--deployment", required=True)
    bootstrap.add_argument("--graph", required=True)
    status = commands.add_parser("status")
    status.add_argument("--campaign-id", required=True)
    ready = commands.add_parser("ready")
    ready.add_argument("--campaign-id", required=True)
    ready.add_argument("--limit", type=int)
    lease = commands.add_parser("lease")
    lease.add_argument("--campaign-id", required=True)
    lease.add_argument("--action-id", required=True)
    lease.add_argument("--agent-id", required=True)
    lease.add_argument("--ttl-seconds", type=int)
    acknowledge = commands.add_parser("ack")
    acknowledge.add_argument("--lease-id", required=True)
    acknowledge.add_argument("--agent-id", required=True)
    acknowledge.add_argument(
        "--capability",
        action="append",
        default=[],
    )
    heartbeat = commands.add_parser("heartbeat")
    heartbeat.add_argument("--lease-id", required=True)
    heartbeat.add_argument("--agent-id", required=True)
    heartbeat.add_argument("--base-sha", required=True)
    heartbeat.add_argument(
        "--status",
        default="running",
    )
    heartbeat.add_argument(
        "--progress-json",
        default="{}",
    )
    authorize = commands.add_parser("authorize")
    authorize.add_argument("--lease-id", required=True)
    authorize.add_argument("--agent-id", required=True)
    authorize.add_argument("--capability", required=True)
    authorize.add_argument("--resource")
    submit = commands.add_parser("submit")
    submit.add_argument("--lease-id", required=True)
    submit.add_argument("--agent-id", required=True)
    submit.add_argument("--artifact", required=True)
    commands.add_parser("sweep")
    verify = commands.add_parser("verify-receipts")
    verify.add_argument("--campaign-id", required=True)
    suspend = commands.add_parser("suspend")
    suspend.add_argument("--campaign-id", required=True)
    suspend.add_argument("--reason", required=True)
    suspend.add_argument("--actor", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime = AutonomyRuntime.from_repository(
        repository_root=args.root,
        database_path=args.database,
    )
    if args.command == "bootstrap":
        runtime.bootstrap(
            campaign_payload=load_json(args.campaign),
            deployment_payload=load_json(args.deployment),
            graph_payload=load_json(args.graph),
        )
        print("campaign bootstrapped")
        return 0
    if args.command == "status":
        print_json(runtime.status(args.campaign_id))
        return 0
    if args.command == "ready":
        actions = runtime.scheduler.next_actions(
            args.campaign_id,
            limit=args.limit,
        )
        print_json(
            [
                {
                    "action_id": action.action_id,
                    "role": action.role,
                    "resource_class": action.resource_class,
                    "score": action.score,
                    "mutation": action.mutation,
                }
                for action in actions
            ]
        )
        return 0
    if args.command == "lease":
        lease = runtime.leases.issue(
            campaign_id=args.campaign_id,
            action_id=args.action_id,
            agent_id=args.agent_id,
            ttl_seconds=args.ttl_seconds,
        )
        print_json(
            {
                "lease_id": lease.lease_id,
                "campaign_id": lease.campaign_id,
                "graph_id": lease.graph_id,
                "action_id": lease.action_id,
                "agent_id": lease.agent_id,
                "role": lease.role,
                "capability_id": lease.capability_id,
                "base_sha": lease.base_sha,
                "issued_at": lease.issued_at,
                "expires_at": lease.expires_at,
            }
        )
        return 0
    if args.command == "ack":
        runtime.leases.acknowledge(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            accepted_capabilities=args.capability,
        )
        print("lease acknowledged")
        return 0
    if args.command == "heartbeat":
        progress = json.loads(args.progress_json)
        runtime.leases.heartbeat(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            observed_base_sha=args.base_sha,
            status=args.status,
            progress=progress,
        )
        print("heartbeat accepted")
        return 0
    if args.command == "authorize":
        decision = runtime.gateway.authorize(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            capability=args.capability,
            resource=args.resource,
        )
        print_json(
            {
                "allowed": decision.allowed,
                "code": decision.code,
                "message": decision.message,
                "lease_id": decision.lease_id,
                "capability": decision.capability,
                "resource": decision.resource,
            }
        )
        return 0 if decision.allowed else 1
    if args.command == "submit":
        artifact_id = runtime.artifacts.submit(
            lease_id=args.lease_id,
            agent_id=args.agent_id,
            artifact=load_json(args.artifact),
        )
        print_json({"artifact_id": artifact_id})
        return 0
    if args.command == "sweep":
        print_json(runtime.leases.sweep())
        return 0
    if args.command == "verify-receipts":
        errors = runtime.verify_receipts(args.campaign_id)
        print_json({"valid": not errors, "errors": errors})
        return 0 if not errors else 1
    if args.command == "suspend":
        runtime.suspend(
            campaign_id=args.campaign_id,
            reason=args.reason,
            actor=args.actor,
        )
        print("campaign suspended")
        return 0
    parser.error(f"Unsupported command: {args.command}")
    return 2


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
