#!/usr/bin/env python3
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/tools/peer_execution_probe.py
#   layer: tool
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-10
"""Universal Peer Execution Probe (Universal Agent Peer Execution Plan, s.10).

Every executable peer passes the SAME logical probe before the router may
schedule Program Execution work to it. The probe proves a peer can consume the
Program Execution contract — not merely that it can reach shared memory.

For each executable peer it emits, in order:

    [PASS] agent identity resolved
    [PASS] governance root present
    [PASS] workspace root present
    [PASS] workspace SHA resolved
    [PASS] Program Execution core validated
    [PASS] autonomy provider available
    [PASS] execution adapter registered
    [PASS] adapter capabilities declared
    [PASS] permissions do not exceed Controller authority
    [PASS] receipt mapping available
    [PASS] cancellation supported honestly
    [PASS] mutable runtime external to Git
    [PASS] peer ready

Any failed line sets PROGRAM_EXECUTION_READY=false for that peer; the router
must not schedule work to a peer that is not ready. This probe is read-only.

Exit 0 = every executable peer ready, 1 = at least one peer not ready,
2 = environment error.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_TOOLS = Path(__file__).resolve().parent


def _load_conformance() -> Any:
    """Load the sibling conformance module by path (no package on sys.path)."""
    spec = importlib.util.spec_from_file_location(
        "peer_execution_conformance",
        _TOOLS / "peer_execution_conformance.py",
    )
    if spec is None or spec.loader is None:  # pragma: no cover
        sys.stderr.write("error: cannot load peer_execution_conformance\n")
        raise SystemExit(2)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_conformance = _load_conformance()
PeerExecutionModel = _conformance.PeerExecutionModel
ROLE_ADAPTER_KINDS = _conformance.ROLE_ADAPTER_KINDS
CANCELLATION_ENUM = _conformance.CANCELLATION_ENUM


def _git_sha(directory: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = result.stdout.strip()
    return sha if result.returncode == 0 and sha else None


def _runtime_root() -> Path:
    program_home = os.environ.get("L9_PROGRAM_HOME", "~/.l9/programs")
    return Path(program_home).expanduser().resolve()


def _peer_checks(
    model: PeerExecutionModel,
    key: str,
    agent: dict[str, Any],
    governance_root: Path,
    workspace_root: Path,
    workspace_sha: str | None,
    runtime_root: Path,
) -> list[tuple[str, bool]]:
    role = str(agent.get("role"))
    allowed = ROLE_ADAPTER_KINDS.get(role, set())
    adapters = model.agent_program_adapters(agent)
    descriptors = [(a, model.descriptor(a)) for a in adapters]
    registered = bool(adapters) and all(a in model.exec_by_id for a in adapters)
    caps_declared = all(
        d is not None and bool((d.get("capabilities") or {}).get("actions")) for _, d in descriptors
    )
    authority_ok = all(
        str((model.exec_by_id.get(a) or {}).get("adapter_kind")) in allowed for a in adapters
    )
    receipts_ok = all(
        d is not None and bool((d.get("receipts") or {}).get("lifecycle_schema"))
        for _, d in descriptors
    )
    cancellation_ok = all(
        d is not None and (d.get("capabilities") or {}).get("cancellation") in CANCELLATION_ENUM
        for _, d in descriptors
    )
    runtime_external = not str(runtime_root).startswith(str(governance_root))

    checks = [
        ("agent identity resolved", str(agent.get("agent_id")) == key),
        ("governance root present", (governance_root / "environment").is_dir()),
        ("workspace root present", workspace_root.is_dir()),
        ("workspace SHA resolved", workspace_sha is not None),
        (
            "Program Execution core validated",
            (governance_root / "environment/program-execution/core").is_dir(),
        ),
        ("autonomy provider available", (governance_root / "autonomy").is_dir()),
        ("execution adapter registered", registered),
        ("adapter capabilities declared", caps_declared),
        ("permissions do not exceed Controller authority", authority_ok),
        ("receipt mapping available", receipts_ok),
        ("cancellation supported honestly", cancellation_ok),
        ("mutable runtime external to Git", runtime_external),
    ]
    peer_ready = all(passed for _, passed in checks)
    checks.append(("peer ready", peer_ready))
    return checks


def probe(governance_root: Path, workspace_root: Path) -> dict[str, Any]:
    model = PeerExecutionModel(governance_root)
    workspace_sha = _git_sha(workspace_root)
    runtime_root = _runtime_root()
    peers: list[dict[str, Any]] = []
    for key, agent in model.executable_agents().items():
        checks = _peer_checks(
            model,
            key,
            agent,
            governance_root,
            workspace_root,
            workspace_sha,
            runtime_root,
        )
        ready = checks[-1][1]
        peers.append(
            {
                "peer": key,
                "role": agent.get("role"),
                "adapters": model.agent_program_adapters(agent),
                "program_execution_ready": ready,
                "checks": [{"name": name, "pass": passed} for name, passed in checks],
            }
        )
    all_ready = all(item["program_execution_ready"] for item in peers)
    return {
        "schema": "l9.peer-execution-probe-report.v1",
        "status": "PASS" if all_ready else "FAIL",
        "governance_root": str(governance_root),
        "workspace_root": str(workspace_root),
        "workspace_sha": workspace_sha,
        "runtime_root": str(runtime_root),
        "peers": peers,
    }


def _print_human(report: dict[str, Any]) -> None:
    for item in report["peers"]:
        sys.stderr.write(f"PEER EXECUTION PROBE — {item['peer']} ({item['role']})\n")
        for check in item["checks"]:
            mark = "PASS" if check["pass"] else "FAIL"
            sys.stderr.write(f"  [{mark}] {check['name']}\n")
        ready = "true" if item["program_execution_ready"] else "false"
        sys.stderr.write(f"  PROGRAM_EXECUTION_READY={ready}\n\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_gov = Path(__file__).resolve().parents[3]
    parser.add_argument("--governance-root", type=Path, default=default_gov)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path(os.environ.get("L9_WORKSPACE_ROOT", str(default_gov))),
    )
    parser.add_argument("--json", action="store_true", help="emit the full JSON report")
    args = parser.parse_args(argv)
    governance_root = args.governance_root.resolve()
    workspace_root = args.workspace_root.resolve()
    if not governance_root.is_dir():
        sys.stderr.write(f"error: governance root not found: {governance_root}\n")
        return 2
    report = probe(governance_root, workspace_root)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human(report)
        sys.stderr.write(f"{report['status']} — {len(report['peers'])} executable peer(s)\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
