"""Layered readiness: a Graphiti hit never turns the store green, nor an outage red."""

from __future__ import annotations

from pathlib import Path

from memory_boundary_fixtures import (
    EXPECTED_VERSION,
    FakeMemoryCli,
    close_payload,
    health_payload,
    hydration_payload,
)

from ops.memory import diagnostics
from ops.memory.control_plane_client import MemoryControlPlaneClient
from ops.memory.receipts import CapabilitiesReceipt
from ops.memory.runtime_binding import STATUS_UNBOUND, RuntimeBinding

ROOT = Path(__file__).resolve().parents[3]


def _levels(report: dict) -> dict[str, str]:
    return {level["level"]: level["status"] for level in report["levels"]}


def _with_capabilities(bound: RuntimeBinding) -> RuntimeBinding:
    caps = CapabilitiesReceipt.parse(
        {
            "package": "l9-graphite-memory",
            "package_version": EXPECTED_VERSION,
            "contract_version": "memory-control-plane/v1",
            "transports": [{"transport": "cli", "operations": {"close": "close"}}],
        }
    )
    return RuntimeBinding(**{**bound.__dict__, "capabilities": caps})


def _healthy_cli(cli: FakeMemoryCli, **health_kwargs) -> FakeMemoryCli:
    cli.reply("health", 0, health_payload(**health_kwargs))
    cli.reply("client cursor status", 0, {"status": "complete"})
    cli.reply("hydrate", 0, hydration_payload())
    cli.reply("write", 0, {"status": "admitted", "record_id": None})
    cli.reply("close", 3, close_payload(status="partial", record_id=None))
    return cli


def test_all_green_with_projection_none_is_ready(bound, fake_cli) -> None:
    client = MemoryControlPlaneClient(bound, runner=_healthy_cli(fake_cli).run)
    report = diagnostics.readiness_report(
        workspace=ROOT, binding=_with_capabilities(bound), client=client
    )
    levels = _levels(report)
    assert report["overall_status"] == "READY"
    assert levels["R0"] == levels["R2"] == levels["R6"] == levels["R7"] == levels["R8"] == "pass"
    assert levels["R5"] == "skipped" and levels["R9"] == "skipped"
    # Nothing was committed by the probes: close ran as a dry run.
    assert "--dry-run" in fake_cli.last("close")
    assert "--dry-run" in fake_cli.last("write")


def test_canonical_healthy_projection_down_is_canonical_ready_projection_degraded(
    bound, fake_cli
) -> None:
    cli = _healthy_cli(fake_cli, projection="http", projection_healthy=False)
    cli.reply("health", 1, health_payload(projection="http", projection_healthy=False))
    client = MemoryControlPlaneClient(bound, runner=cli.run)
    report = diagnostics.readiness_report(
        workspace=ROOT, binding=_with_capabilities(bound), client=client
    )
    assert report["overall_status"] == "CANONICAL_READY_PROJECTION_DEGRADED"
    assert _levels(report)["R2"] == "pass" and _levels(report)["R9"] == "fail"


def test_projection_healthy_store_down_is_memory_unavailable(bound, fake_cli) -> None:
    cli = _healthy_cli(fake_cli)
    cli.reply(
        "health", 1, health_payload(store_healthy=False, projection="http", projection_healthy=True)
    )
    client = MemoryControlPlaneClient(bound, runner=cli.run)
    report = diagnostics.readiness_report(
        workspace=ROOT, binding=_with_capabilities(bound), client=client
    )
    assert report["overall_status"] == "MEMORY_UNAVAILABLE"
    assert _levels(report)["R2"] == "fail"
    # No hydrate/write probe runs against an unavailable store.
    assert all(call[0][1] not in {"hydrate", "write", "close"} for call in cli.calls)


def test_mcp_missing_with_healthy_cli_is_partial_surface_ready(bound, fake_cli) -> None:
    cli = _healthy_cli(fake_cli)
    cli.reply("client cursor status", 1, {"status": "unchanged", "reasons": ["not installed"]})
    client = MemoryControlPlaneClient(bound, runner=cli.run)
    report = diagnostics.readiness_report(
        workspace=ROOT, binding=_with_capabilities(bound), client=client
    )
    assert report["overall_status"] == "PARTIAL_SURFACE_READY"
    assert _levels(report)["R4"] == "fail" and _levels(report)["R6"] == "pass"


def test_unbound_package_is_package_unbound_and_spawns_nothing(fake_cli) -> None:
    unbound = RuntimeBinding(
        status=STATUS_UNBOUND,
        runtime_mode="pinned_environment",
        memory_package="l9-graphite-memory",
        expected_version=EXPECTED_VERSION,
        expected_contract_version="memory-control-plane/v1",
        manifest_path="m",
        reasons=("l9-graphite-memory is not importable",),
    )
    client = MemoryControlPlaneClient(unbound, runner=fake_cli.run)
    report = diagnostics.readiness_report(workspace=ROOT, binding=unbound, client=client)
    assert report["overall_status"] == "PACKAGE_UNBOUND"
    assert fake_cli.calls == []
    assert report["binding"]["binding_status"] == "unbound"


def test_denied_fan_in_narrows_to_the_primary_namespace(bound, fake_cli) -> None:
    """INV-07: a denied read hint is memory's verdict; readiness asks the narrower question."""

    from memory_boundary_fixtures import error_stderr

    calls: list[list[str]] = []

    def hydrate(argv: list[str], _stdin: str | None) -> tuple[int, object, str]:
        calls.append(argv)
        if argv.count("--namespace") > 1:
            return 1, None, error_stderr("AuthorizationError", "not authorized to read 'other'")
        return 0, hydration_payload(), ""

    cli = _healthy_cli(fake_cli).on("hydrate", hydrate)
    client = MemoryControlPlaneClient(bound, runner=cli.run)
    report = diagnostics.readiness_report(
        workspace=ROOT, binding=_with_capabilities(bound), client=client
    )
    level = next(item for item in report["levels"] if item["level"] == "R6")
    assert level["status"] == "pass"
    assert "fan-in denied" in level["detail"]
    assert len(calls) == 2 and calls[1].count("--namespace") == 1
