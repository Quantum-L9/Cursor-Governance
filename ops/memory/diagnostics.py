"""Layered memory readiness (plan §26) and the binding proof (plan §7).

Replaces "Graphiti is up" with ten levels, projection last:

    R0 PACKAGE_BOUND          runtime binding is usable: the audited artifact
                              (exact), a compatible build whose artifact could
                              not be proved, or an explicit dev checkout. The
                              detail always names which — 'compatible' is a
                              weaker claim than 'exact' and must read as one.
    R1 CLI_EXECUTABLE         the bound l9-memory answered `capabilities`
    R2 CANONICAL_STORE_READY  memory.health reports the store healthy
    R3 MEMORY_SERVICE_READY   health status complete/partial on the expected contract
    R4 MCP_CONFIG_INSTALLED   memory-owned `client cursor status` is complete
    R5 MCP_HANDSHAKE_VERIFIED memory-owned `client cursor verify` (opt-in; spawns a server)
    R6 HYDRATION_READY        canonical hydrate answered (hits or a clean no-hit)
    R7 WRITE_READY            write admission dry run passed
    R8 CLOSE_READY            close admission dry run passed (nothing committed)
    R9 PROJECTION_READY       projection healthy, or none configured

A Graphiti hit can never turn R2 green, and a Graphiti outage can never turn
R2 red (INV-04, INV-05).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ops.memory.control_plane_client import MemoryControlPlaneClient, OutcomeStatus
from ops.memory.namespace_context import resolve_namespace_context
from ops.memory.runtime_binding import RuntimeBinding, resolve_runtime_binding

PASS = "pass"
FAIL = "fail"
SKIPPED = "skipped"

LEVELS: tuple[tuple[str, str], ...] = (
    ("R0", "PACKAGE_BOUND"),
    ("R1", "CLI_EXECUTABLE"),
    ("R2", "CANONICAL_STORE_READY"),
    ("R3", "MEMORY_SERVICE_READY"),
    ("R4", "MCP_CONFIG_INSTALLED"),
    ("R5", "MCP_HANDSHAKE_VERIFIED"),
    ("R6", "HYDRATION_READY"),
    ("R7", "WRITE_READY"),
    ("R8", "CLOSE_READY"),
    ("R9", "PROJECTION_READY"),
)


@dataclass(frozen=True)
class Level:
    level: str
    name: str
    status: str
    detail: str


def _overall(levels: dict[str, str]) -> str:
    if levels["R0"] != PASS or levels["R1"] != PASS:
        return "PACKAGE_UNBOUND"
    if levels["R2"] != PASS or levels["R3"] != PASS:
        return "MEMORY_UNAVAILABLE"
    core = all(levels[key] == PASS for key in ("R6", "R7", "R8"))
    surface = levels["R4"] == PASS and levels["R5"] in (PASS, SKIPPED)
    if not core:
        return "MEMORY_DEGRADED"
    if not surface:
        return "PARTIAL_SURFACE_READY"
    if levels["R9"] == FAIL:
        return "CANONICAL_READY_PROJECTION_DEGRADED"
    return "READY"


def readiness_report(
    *,
    workspace: str | Path,
    binding: RuntimeBinding | None = None,
    client: MemoryControlPlaneClient | None = None,
    verify_mcp: bool = False,
    mcp_config_path: str | None = None,
) -> dict[str, Any]:
    workspace_path = str(Path(workspace).expanduser().resolve())
    binding = binding or resolve_runtime_binding()
    client = client or MemoryControlPlaneClient(binding)
    context = resolve_namespace_context(workspace_path)
    results: dict[str, Level] = {}

    def record(level: str, status: str, detail: str) -> None:
        name = dict(LEVELS)[level]
        results[level] = Level(level=level, name=name, status=status, detail=detail[:400])

    record(
        "R0",
        PASS if binding.ok else FAIL,
        f"{binding.status}: " + ("; ".join(binding.reasons) or "artifact proved"),
    )
    record(
        "R1",
        PASS if (binding.ok and binding.capabilities is not None) else FAIL,
        binding.memory_cli or "no bound executable",
    )

    health = client.health() if binding.ok else None
    receipt = health.receipt if health is not None else None
    if receipt is None:
        detail = health.error if health is not None else "binding failed"
        record("R2", FAIL, detail or "no health receipt")
        record("R3", FAIL, detail or "no health receipt")
    else:
        record(
            "R2", PASS if receipt.store_healthy else FAIL, f"store healthy={receipt.store_healthy}"
        )
        contract_ok = receipt.contract_version == binding.expected_contract_version
        record(
            "R3",
            PASS if (receipt.canonical_ready and contract_ok) else FAIL,
            f"status={receipt.status} contract={receipt.contract_version}",
        )

    if binding.ok:
        status_outcome = client.cursor_client_status(config_path=mcp_config_path)
        record(
            "R4",
            PASS if status_outcome.ok else FAIL,
            status_outcome.error or "managed entry current",
        )
        if verify_mcp:
            verify_outcome = client.cursor_client_verify(config_path=mcp_config_path)
            record(
                "R5",
                PASS if verify_outcome.ok else FAIL,
                verify_outcome.error or "handshake complete",
            )
        else:
            record("R5", SKIPPED, "pass --verify-mcp to run the real MCP handshake")
    else:
        record("R4", FAIL, "binding failed")
        record("R5", SKIPPED, "binding failed")

    namespace = context.write_namespace_hint
    if binding.ok and results["R2"].status == PASS and context.read_namespace_hints:
        hydrate = client.hydrate(
            "readiness probe",
            workspace=workspace_path,
            write_namespace_hint=namespace,
            read_namespace_hints=context.read_namespace_hints,
            token_budget=256,
            max_records=5,
        )
        detail = f"{hydrate.status.value}: {hydrate.error or 'hydrate answered'}"
        if (
            hydrate.status is OutcomeStatus.UNAUTHORIZED_NAMESPACE
            and namespace
            and len(context.read_namespace_hints) > 1
        ):
            # A denied read fan-in is memory's verdict on a *hint* (INV-07).
            # Readiness then asks the narrower canonical question — the one
            # write namespace alone — and reports the denial beside it. This
            # is a smaller request to the same authority, never a fallback.
            primary = client.hydrate(
                "readiness probe",
                workspace=workspace_path,
                write_namespace_hint=namespace,
                read_namespace_hints=(namespace,),
                token_budget=256,
                max_records=5,
            )
            detail = (
                f"fan-in denied ({hydrate.error}); primary namespace {namespace!r} "
                f"{primary.status.value}"
            )
            hydrate = primary
        record(
            "R6",
            PASS if hydrate.status in (OutcomeStatus.OK, OutcomeStatus.NO_HITS) else FAIL,
            detail,
        )
    else:
        record("R6", FAIL, "no namespace hint or store not ready")

    if binding.ok and namespace and results["R2"].status == PASS:
        write_probe = client.write_probe(workspace=workspace_path, namespace=namespace)
        record(
            "R7",
            PASS if write_probe.ok else FAIL,
            write_probe.error or "write admission dry run ok",
        )
        close_probe = client.close(
            workspace=workspace_path,
            namespace=namespace,
            summary="readiness probe: close admission dry run",
            dry_run=True,
        )
        close_ok = close_probe.status is OutcomeStatus.NOT_COMMITTED
        record(
            "R8",
            PASS if close_ok else FAIL,
            "close admission dry run ok (nothing committed)"
            if close_ok
            else f"{close_probe.status.value}: {close_probe.error or 'no receipt'}",
        )
    else:
        record("R7", FAIL, "no write namespace hint or store not ready")
        record("R8", FAIL, "no write namespace hint or store not ready")

    if receipt is None:
        record("R9", FAIL, "no health receipt")
    elif receipt.projection_name in (None, "none"):
        record("R9", SKIPPED, "projection backend is none")
    else:
        record(
            "R9",
            PASS if receipt.projection_healthy else FAIL,
            f"projection={receipt.projection_name} healthy={receipt.projection_healthy}",
        )

    statuses = {key: results[key].status for key, _ in LEVELS}
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "workspace": workspace_path,
        "overall_status": _overall(statuses),
        "binding": binding.as_dict(),
        "namespace_context": context.as_dict(),
        "levels": [asdict(results[key]) for key, _ in LEVELS],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Layered memory readiness (R0..R9)")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--binding-only", action="store_true", help="print only the binding proof")
    parser.add_argument("--verify-mcp", action="store_true", help="run the real MCP handshake (R5)")
    parser.add_argument("--mcp-config-path", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    binding = resolve_runtime_binding()
    if args.binding_only:
        sys.stdout.write(json.dumps(binding.as_dict(), indent=2, sort_keys=True) + "\n")
        return 0 if binding.ok else 1
    result = readiness_report(
        workspace=args.workspace,
        binding=binding,
        verify_mcp=args.verify_mcp,
        mcp_config_path=args.mcp_config_path,
    )
    if args.json:
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"memory readiness: {result['overall_status']}\n")
        for level in result["levels"]:
            sys.stdout.write(
                f"  {level['level']} {level['name']:<24} {level['status']:<7} {level['detail']}\n"
            )
    return 0 if result["overall_status"] in {"READY", "CANONICAL_READY_PROJECTION_DEGRADED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
