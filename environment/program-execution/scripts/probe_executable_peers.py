from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml
from adapters.common.imports import load_module


def _subsystem_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return _subsystem_root().parents[1]


def _default_runtime() -> Path:
    program_home = Path(os.environ.get("L9_PROGRAM_HOME", "~/.l9/programs")).expanduser()
    return (program_home / "_peer-readiness").resolve()


def _readiness_builder():
    module = load_module(
        _subsystem_root() / "integrations/bootstrap/peer_readiness.py",
        "pes_probe_peer_readiness",
    )
    return module.build_readiness


def _enabled_agents(repo_root: Path) -> dict[str, Any]:
    registry = yaml.safe_load(
        (repo_root / "environment/agents/agent_registry.yaml").read_text(encoding="utf-8")
    )
    agents = registry.get("agents") or {}
    return {
        key: agent
        for key, agent in agents.items()
        if isinstance(agent, dict) and (agent.get("execution") or {}).get("enabled") is True
    }


def probe(subsystem_root: Path, repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    build_readiness = _readiness_builder()
    runtime_root.mkdir(parents=True, exist_ok=True)
    peers: list[dict[str, Any]] = []
    all_ready = True
    for agent_id, agent in _enabled_agents(repo_root).items():
        bindings = (agent.get("execution") or {}).get("bindings") or []
        receipts = []
        agent_ready = False
        for binding in bindings:
            surface = str(binding.get("surface"))
            adapter_id = str(binding.get("adapter_id"))
            receipt = build_readiness(subsystem_root, repo_root, agent_id, surface, adapter_id)
            out_dir = runtime_root / agent_id
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{adapter_id}.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            receipts.append(receipt)
            agent_ready = agent_ready or receipt["status"] == "READY"
        if not agent_ready:
            all_ready = False
        peers.append(
            {
                "agent_id": agent_id,
                "ready": agent_ready,
                "bindings": [
                    {
                        "surface": r["surface"],
                        "adapter_id": r["adapter_id"],
                        "status": r["status"],
                        "receipt_digest": r["receipt_digest"],
                    }
                    for r in receipts
                ],
            }
        )
    return {
        "schema": "l9.executable-peer-probe-report.v1",
        "status": "PASS" if all_ready else "FAIL",
        "runtime_root": str(runtime_root),
        "peers": peers,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=_default_runtime())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = probe(_subsystem_root(), _repo_root(), args.runtime.expanduser().resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for peer in report["peers"]:
            mark = "READY" if peer["ready"] else "BLOCKED"
            bindings = ", ".join(f"{b['adapter_id']}={b['status']}" for b in peer["bindings"])
            print(f"[{mark}] {peer['agent_id']}: {bindings}")
        print(f"{report['status']} — {len(report['peers'])} enabled peer(s)")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
