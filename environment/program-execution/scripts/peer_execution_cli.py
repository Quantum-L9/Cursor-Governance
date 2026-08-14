from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from peer_execution.bindings import resolve_peer_binding
from peer_execution.models import ProbeContext
from peer_execution.runtime_store import RuntimeStore

from scripts.provider_loader import instantiate, repository_root


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _read_object(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("contract must be a JSON object")
    return value


def _program_digest(contract: dict[str, Any]) -> str:
    value = contract.get("program_lock_digest") or contract.get("program_digest")
    if not isinstance(value, str) or not value:
        raise ValueError("Program Lock digest is required")
    return value


def _runtime(value: str | None) -> Path:
    raw = value or os.environ.get("L9_PROGRAM_ADAPTER_RUNTIME")
    if not raw:
        raise ValueError("runtime path is required")
    return Path(raw).expanduser().resolve()


def _binding(args: argparse.Namespace):
    return resolve_peer_binding(
        repository_root(),
        args.agent_ref,
        args.surface,
        args.provider_ref,
    )


def command_dispatch(args: argparse.Namespace) -> int:
    runtime = _runtime(args.runtime)
    contract = _read_object(args.contract)
    binding = _binding(args)
    adapter = instantiate(
        binding.provider_ref,
        runtime,
        execution_profile_ref=binding.execution_profile_ref,
        binding_context=binding.to_dict(),
    )
    probe = adapter.probe(
        ProbeContext(
            repository_root=str(repository_root()),
            runtime_root=str(runtime),
            program_lock_digest=_program_digest(contract),
            requested_capabilities=tuple(contract.get("requested_actions") or []),
            metadata=binding.to_dict(),
        )
    )
    if probe.status != "PASS":
        _json({"binding": binding.to_dict(), "probe": probe.to_dict()})
        return 2
    prepared = adapter.prepare(contract)
    dispatched = adapter.dispatch({"dispatch_id": prepared.dispatch_id})
    _json(
        {
            "binding": binding.to_dict(),
            "probe": probe.to_dict(),
            "prepare": prepared.to_dict(),
            "dispatch": dispatched.to_dict(),
        }
    )
    return 0 if dispatched.status in {"PASS", "RUNNING"} else 1


def _adapter_from_dispatch(runtime: Path, dispatch_id: str):
    record = RuntimeStore(runtime).load(dispatch_id)
    provider_ref = str(record["adapter_id"])
    profile_ref = record.get("execution_profile_ref")
    binding_context = record.get("binding_context") or {}
    return instantiate(
        provider_ref,
        runtime,
        execution_profile_ref=str(profile_ref) if profile_ref else None,
        binding_context=binding_context,
    )


def command_lifecycle(args: argparse.Namespace, operation: str) -> int:
    runtime = _runtime(args.runtime)
    adapter = _adapter_from_dispatch(runtime, args.dispatch_id)
    value = getattr(adapter, operation)(args.dispatch_id)
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    _json(value)
    return 1 if isinstance(value, dict) and value.get("status") in {"FAIL", "BLOCKED"} else 0


def command_probe(args: argparse.Namespace) -> int:
    runtime = _runtime(args.runtime)
    binding = _binding(args)
    digest = args.program_lock_digest or hashlib.sha256(b"peer-execution-probe").hexdigest()
    adapter = instantiate(
        binding.provider_ref,
        runtime,
        execution_profile_ref=binding.execution_profile_ref,
        binding_context=binding.to_dict(),
    )
    receipt = adapter.probe(
        ProbeContext(
            repository_root=str(repository_root()),
            runtime_root=str(runtime),
            program_lock_digest=digest,
            metadata=binding.to_dict(),
        )
    )
    _json({"binding": binding.to_dict(), "probe": receipt.to_dict()})
    return 0 if receipt.status == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="peer-execution")
    sub = value.add_subparsers(dest="command", required=True)
    for name in ("probe", "dispatch"):
        command = sub.add_parser(name)
        command.add_argument("--agent-ref", required=True)
        command.add_argument("--surface", required=True)
        command.add_argument("--provider-ref")
        command.add_argument("--runtime")
        if name == "probe":
            command.add_argument("--program-lock-digest")
            command.set_defaults(func=command_probe)
        else:
            command.add_argument("--contract", required=True)
            command.set_defaults(func=command_dispatch)
    for name in ("status", "collect", "cancel", "cleanup"):
        command = sub.add_parser(name)
        command.add_argument("--dispatch-id", required=True)
        command.add_argument("--runtime")
        command.set_defaults(func=lambda args, operation=name: command_lifecycle(args, operation))
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(
            json.dumps(
                {"status": "FAIL", "error_type": type(exc).__name__, "message": str(exc)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
