from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from adapters.common.imports import load_module


def _subsystem_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return _subsystem_root().parents[1]


def _resolve_runtime_root() -> Path:
    """Canonical agents/readiness via runtime_paths; legacy fallback if import fails."""
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    try:
        from environment.agents.runtime_paths import peer_readiness_root

        return peer_readiness_root()
    except Exception:  # noqa: BLE001 — probe must still run in thin PYTHONPATH setups
        return (Path.home() / ".l9" / "programs" / "_peer-readiness").resolve()


def _readiness_builder():
    module = load_module(
        _subsystem_root() / "integrations/bootstrap/peer_readiness.py",
        "pes_probe_peer_readiness",
    )
    return module.build_readiness


def _required_peers(repo_root: Path) -> dict[str, Any]:
    bindings_path = repo_root / "environment/agents/PEER_RUNTIME_BINDINGS.yaml"
    if not bindings_path.is_file():
        raise FileNotFoundError(
            f"PEER_RUNTIME_BINDINGS.yaml missing at {bindings_path} "
            "(probe refuses vacuous PASS)"
        )
    doc = yaml.safe_load(bindings_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("PEER_RUNTIME_BINDINGS.yaml must be an object")
    peers = doc.get("peers") or {}
    return {
        key: peer
        for key, peer in peers.items()
        if isinstance(peer, dict) and (peer.get("execution") or {}).get("required") is True
    }


def probe(subsystem_root: Path, repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    build_readiness = _readiness_builder()
    runtime_root.mkdir(parents=True, exist_ok=True)
    peers_out: list[dict[str, Any]] = []
    all_ready = True
    try:
        required = _required_peers(repo_root)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return {
            "schema": "l9.executable-peer-probe-report.v1",
            "status": "FAIL",
            "runtime_root": str(runtime_root),
            "peers": [],
            "errors": [str(exc)],
        }
    for agent_id, peer in required.items():
        bindings = (peer.get("execution") or {}).get("bindings") or []
        receipts = []
        agent_ready = False
        for binding in bindings:
            surface = str(binding.get("surface"))
            adapter_id = str(binding.get("adapter_id"))
            # Readiness remains binding-level: (agent_ref, surface, adapter_id)
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
        peers_out.append(
            {
                "agent_id": agent_id,
                "agent_ref": peer.get("agent_ref", agent_id),
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
        "peers": peers_out,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    runtime = (
        args.runtime.expanduser().resolve()
        if args.runtime is not None
        else _resolve_runtime_root()
    )
    report = probe(_subsystem_root(), _repo_root(), runtime)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for peer in report["peers"]:
            mark = "READY" if peer["ready"] else "BLOCKED"
            bindings = ", ".join(f"{b['adapter_id']}={b['status']}" for b in peer["bindings"])
            print(f"[{mark}] {peer['agent_id']}: {bindings}")
        print(f"{report['status']} — {len(report['peers'])} execution.required peer(s)")
        for err in report.get("errors") or []:
            print(f"error: {err}", file=sys.stderr)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
