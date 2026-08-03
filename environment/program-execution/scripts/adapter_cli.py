from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from adapters.common.errors import AdapterFailure
from adapters.common.models import ProbeContext

from scripts.provider_loader import instantiate, subsystem_root
from scripts.router import route_contract


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _read_object(path: str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    allowed = [subsystem_root().parents[1].resolve()]
    program_home = os.environ.get("L9_PROGRAM_HOME")
    if program_home:
        allowed.append(Path(program_home).expanduser().resolve())
    if not any(root == source or root in source.parents for root in allowed):
        raise ValueError(f"path is outside allowed roots: {source}")
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON document must be an object: {source}")
    return value


def _runtime(args: argparse.Namespace) -> Path:
    value = args.runtime or os.environ.get("L9_PROGRAM_ADAPTER_RUNTIME")
    if not value:
        raise ValueError("runtime path is required")
    return Path(value).expanduser().resolve()


def _program_digest(args: argparse.Namespace) -> str:
    value = args.program_lock_digest or os.environ.get("L9_PROGRAM_LOCK_DIGEST")
    if not value:
        raise ValueError("Program Lock digest is required")
    return value


def command_validate(args: argparse.Namespace) -> int:
    from scripts.validate_execution_adapters import validate

    report = validate(subsystem_root())
    _json(report)
    return 0 if report["status"] == "PASS" else 1


def command_probe(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    adapter = instantiate(args.adapter, runtime)
    context = ProbeContext(
        repository_root=str(subsystem_root().parents[1]),
        runtime_root=str(runtime),
        program_lock_digest=_program_digest(args),
        requested_capabilities=tuple(args.capability or []),
        metadata={
            "producer_identity": args.producer_identity,
            "repository": args.repository,
            "workflow": args.workflow,
            "checks_write_proven": args.checks_write_proven,
            "actions_write_proven": args.actions_write_proven,
            "deployments_write_proven": args.deployments_write_proven,
        },
    )
    receipt = adapter.probe(context)
    _json(receipt.to_dict())
    return 0 if receipt.status == "PASS" else 2


def command_route(args: argparse.Namespace) -> int:
    contract = _read_object(args.contract)
    capability_dir = _runtime(args) / "capabilities"
    receipts: dict[str, dict[str, Any]] = {}
    if capability_dir.is_dir():
        for path in capability_dir.glob("*.json"):
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and value.get("adapter_id"):
                receipts[str(value["adapter_id"])] = value
    result = route_contract(
        contract,
        subsystem_root=subsystem_root(),
        capability_receipts=receipts,
    )
    _json(result)
    return 0


def command_dispatch(args: argparse.Namespace) -> int:
    runtime = _runtime(args)
    adapter = instantiate(args.adapter, runtime)
    contract = _read_object(args.contract)
    prepared = adapter.prepare(contract)
    dispatched = adapter.dispatch(
        {"dispatch_id": prepared.dispatch_id},
    )
    _json(
        {
            "prepare": prepared.to_dict(),
            "dispatch": dispatched.to_dict(),
        }
    )
    return 0 if dispatched.status in {"PASS", "RUNNING"} else 1


def command_lifecycle(args: argparse.Namespace, operation: str) -> int:
    adapter_id = args.adapter
    if not adapter_id:
        record_path = _runtime(args) / "dispatches" / f"{args.dispatch_id}.json"
        value = json.loads(record_path.read_text(encoding="utf-8"))
        adapter_id = str(value["adapter_id"])
    adapter = instantiate(adapter_id, _runtime(args))
    method = getattr(adapter, operation)
    value = method(args.dispatch_id)
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    _json(value)
    if isinstance(value, dict) and value.get("status") in {"FAIL", "BLOCKED"}:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="program-execution-adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.set_defaults(func=command_validate)

    probe = sub.add_parser("probe")
    probe.add_argument("--adapter", required=True)
    probe.add_argument("--runtime")
    probe.add_argument("--program-lock-digest")
    probe.add_argument("--capability", action="append")
    probe.add_argument("--producer-identity")
    probe.add_argument("--repository")
    probe.add_argument("--workflow")
    probe.add_argument("--checks-write-proven", action="store_true")
    probe.add_argument("--actions-write-proven", action="store_true")
    probe.add_argument("--deployments-write-proven", action="store_true")
    probe.set_defaults(func=command_probe)

    route = sub.add_parser("route")
    route.add_argument("--contract", required=True)
    route.add_argument("--runtime")
    route.set_defaults(func=command_route)

    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--adapter", required=True)
    dispatch.add_argument("--contract", required=True)
    dispatch.add_argument("--runtime")
    dispatch.set_defaults(func=command_dispatch)

    for name in ("status", "collect", "cancel", "cleanup"):
        command = sub.add_parser(name)
        command.add_argument("--dispatch-id", required=True)
        command.add_argument("--adapter")
        command.add_argument("--runtime")
        command.set_defaults(func=lambda args, operation=name: command_lifecycle(args, operation))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except AdapterFailure as exc:
        print(json.dumps(exc.to_dict(), sort_keys=True), file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
