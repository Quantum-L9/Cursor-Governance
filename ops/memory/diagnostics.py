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
    R5 MCP_HANDSHAKE_VERIFIED memory-owned `client cursor verify` (default on;
                              spawns a server and completes a real handshake,
                              ~1.2s measured. Opt out with --no-verify-mcp.
                              NOTE it verifies the SERVER via generated argv
                              (argv_source=generated, config_path=null), so it
                              proves the package answers `initialize` and
                              carries its tools — it does NOT prove any client's
                              config expands. Claude's rendered .mcp.json is
                              emit_claude_readiness._claude_mcp_health.
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

from ops.memory import environment_heal
from ops.memory.control_plane_client import (
    FAULT_CANONICAL,
    FAULT_ENVIRONMENT,
    FAULT_NONE,
    MemoryControlPlaneClient,
    OutcomeStatus,
)
from ops.memory.namespace_context import resolve_namespace_context
from ops.memory.runtime_binding import (
    _REPO_ROOT,
    MODE_CALLER,
    RuntimeBinding,
    resolve_runtime_binding,
)

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
    verify_mcp: bool = True,
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
            record("R5", SKIPPED, "handshake opted out with --no-verify-mcp")
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
    overall = _overall(statuses)
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "workspace": workspace_path,
        "overall_status": overall,
        "fault_class": fault_class_for_overall(overall),
        "remediation": remediation_for(overall, binding),
        "binding": binding.as_dict(),
        "namespace_context": context.as_dict(),
        "levels": [asdict(results[key]) for key, _ in LEVELS],
    }


#: Overall statuses that mean the runtime never reached memory (ADR-0032).
_ENVIRONMENT_OVERALL = frozenset({"PACKAGE_UNBOUND"})
_READY_OVERALL = frozenset({"READY", "CANONICAL_READY_PROJECTION_DEGRADED"})


def fault_class_for_overall(overall: str) -> str:
    """``none`` / ``environment`` / ``canonical`` for an overall readiness status.

    ``PACKAGE_UNBOUND`` is an environment fault: R0/R1 failed, so no memory
    operation ran and nothing canonical was observed. Every other non-ready
    status was measured *through* the bound runtime and is canonical.
    """

    if overall in _READY_OVERALL:
        return FAULT_NONE
    if overall in _ENVIRONMENT_OVERALL:
        return FAULT_ENVIRONMENT
    return FAULT_CANONICAL


def remediation_for(overall: str, binding: RuntimeBinding) -> str | None:
    """One actionable line for an environment fault; ``None`` otherwise.

    Names what the one-shot heal already did so the operator is not told to
    repeat a repair that just ran, and points at the governance checkout the
    binding actually tried rather than a generic ``make venv``.
    """

    if fault_class_for_overall(overall) != FAULT_ENVIRONMENT:
        return None
    root = binding.governance_root or str(_REPO_ROOT)
    heal = binding.environment_heal
    if heal == environment_heal.HEAL_HEALED:
        return (
            f"ENVIRONMENT_FAULT: the locked sync of {root} succeeded but the runtime is still "
            "unbound — the lock itself no longer pins expected_package_version; "
            "reconcile pyproject.toml / uv.lock with ops/config/memory-binding.json"
        )
    if heal == environment_heal.HEAL_FAILED:
        return (
            f"ENVIRONMENT_FAULT: locked sync of {root} failed — run "
            f"`bash ops/scripts/ensure_uv_environment.sh {root} apply` and read its stderr"
        )
    if heal and heal.startswith(environment_heal.HEAL_SKIPPED_PREFIX):
        why = heal[len(environment_heal.HEAL_SKIPPED_PREFIX) :]
        return (
            f"ENVIRONMENT_FAULT: governance .venv at {root} is unbound; automatic heal skipped "
            f"({why}) — run `bash ops/scripts/ensure_uv_environment.sh {root} apply`"
        )
    if binding.runtime_mode == MODE_CALLER:
        return (
            "ENVIRONMENT_FAULT: no governance .venv was found (L9_GOVERNANCE_DIR, "
            "$HOME/.cursor-governance, this checkout) — run `make venv` in the governance "
            "checkout or export L9_GOVERNANCE_DIR"
        )
    return (
        f"ENVIRONMENT_FAULT: memory runtime unbound at {root} — run "
        f"`bash ops/scripts/ensure_uv_environment.sh {root} apply` "
        "(not a memory degradation: no canonical operation ran)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Layered memory readiness (R0..R9)")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--binding-only", action="store_true", help="print only the binding proof")
    parser.add_argument(
        "--verify-mcp",
        dest="verify_mcp",
        action="store_true",
        default=True,
        help="run the real MCP handshake (R5) — now the default; accepted for compatibility",
    )
    parser.add_argument(
        "--no-verify-mcp",
        dest="verify_mcp",
        action="store_false",
        help="skip the R5 handshake (it spawns a server for ~1.2s)",
    )
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
        sys.stdout.write(
            f"memory readiness: {result['overall_status']} (fault_class={result['fault_class']})\n"
        )
        if result.get("remediation"):
            sys.stdout.write(f"  {result['remediation']}\n")
        for level in result["levels"]:
            sys.stdout.write(
                f"  {level['level']} {level['name']:<24} {level['status']:<7} {level['detail']}\n"
            )
    return 0 if result["overall_status"] in {"READY", "CANONICAL_READY_PROJECTION_DEGRADED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
