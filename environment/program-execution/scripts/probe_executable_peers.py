from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from peer_execution.bindings import load_peer_bindings
from peer_execution.imports import load_module, pe_script
from peer_execution.models import ProbeContext

instantiate = pe_script("provider_loader").instantiate

_STRUCTURAL_CHECKS = (
    "canonical_binding",
    "provider_conformance",
    "execution_profile",
    "provider_routable",
    "provider_probe_integrity",
    "autonomy_provider",
    "autonomy_conformance",
    "execution_gateway",
)


def _subsystem_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repo_root() -> Path:
    return _subsystem_root().parents[1]


def _resolve_runtime_root() -> Path:
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    try:
        from environment.agents.runtime_paths import peer_readiness_root

        return peer_readiness_root()
    except Exception:  # noqa: BLE001
        return (Path.home() / ".l9" / "programs" / "_peer-readiness").resolve()


def _readiness_builder():
    module = load_module(
        _subsystem_root() / "integrations/bootstrap/peer_readiness.py",
        "pes_probe_peer_readiness",
    )
    return module.build_readiness


def _required_peers(repo_root: Path) -> dict[str, Any]:
    doc = load_peer_bindings(repo_root)
    return {
        key: peer
        for key, peer in (doc.get("peers") or {}).items()
        if (peer.get("execution") or {}).get("required") is True
    }


def _binding_outcome(receipt: dict[str, Any]) -> str:
    """Classify one readiness receipt for the inventory gate.

    READY is live. Honest BLOCKED (missing host / file-drop) is inventory.
    FAIL is a structural or probe defect and fails the gate.
    """
    if receipt.get("status") == "READY":
        return "READY"
    checks = receipt.get("checks") or {}
    if any(checks.get(name) == "FAIL" for name in _STRUCTURAL_CHECKS):
        return "FAIL"
    probe_status = str(checks.get("provider_probe") or "")
    if probe_status == "FAIL":
        return "FAIL"
    if receipt.get("status") == "BLOCKED" or probe_status == "BLOCKED":
        return "BLOCKED"
    return "FAIL"


def probe(subsystem_root: Path, repo_root: Path, runtime_root: Path) -> dict[str, Any]:
    build_readiness = _readiness_builder()
    runtime_root.mkdir(parents=True, exist_ok=True)
    peers_out: list[dict[str, Any]] = []
    gate_ok = True
    status_counts: dict[str, int] = {"READY": 0, "BLOCKED": 0, "FAIL": 0}
    try:
        required = _required_peers(repo_root)
    except (OSError, ValueError, FileNotFoundError) as exc:
        return {
            "schema": "l9.executable-peer-probe-report.v2",
            "status": "FAIL",
            "runtime_root": str(runtime_root),
            "status_counts": {"READY": 0, "BLOCKED": 0, "FAIL": 0},
            "peers": [],
            "errors": [str(exc)],
        }
    for agent_id, peer in required.items():
        bindings = (peer.get("execution") or {}).get("bindings") or []
        receipts = []
        outcomes: list[str] = []
        for binding in bindings:
            surface = binding["surface"]
            provider_ref = binding["provider_ref"]
            profile_ref = binding["execution_profile_ref"]
            probe_runtime = runtime_root / "provider-probes" / agent_id / provider_ref
            probe_digest = (
                "sha256:"
                + hashlib.sha256(
                    f"peer-readiness:{agent_id}:{surface}:{provider_ref}".encode()
                ).hexdigest()
            )
            try:
                adapter = instantiate(
                    provider_ref,
                    probe_runtime,
                    execution_profile_ref=profile_ref,
                    binding_context={
                        "agent_ref": agent_id,
                        "surface": surface,
                        "provider_ref": provider_ref,
                        "execution_profile_ref": profile_ref,
                    },
                )
                provider_probe = adapter.probe(
                    ProbeContext(
                        repository_root=str(repo_root),
                        runtime_root=str(probe_runtime),
                        program_lock_digest=probe_digest,
                        metadata={"agent_ref": agent_id, "surface": surface},
                    )
                ).to_dict()
            except Exception as exc:  # noqa: BLE001
                provider_probe = {
                    "status": "BLOCKED",
                    "blocked_reason": "provider_probe_exception",
                    "error_type": type(exc).__name__,
                }
            receipt = build_readiness(
                subsystem_root,
                repo_root,
                agent_id,
                surface,
                provider_ref,
                profile_ref,
                provider_probe=provider_probe,
            )
            out_dir = runtime_root / agent_id
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{provider_ref}.json").write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            receipts.append(receipt)
            outcome = _binding_outcome(receipt)
            outcomes.append(outcome)
            status_counts[outcome] = status_counts.get(outcome, 0) + 1
        agent_ready = "READY" in outcomes
        agent_gate_ok = any(item in {"READY", "BLOCKED"} for item in outcomes)
        if not agent_gate_ok:
            gate_ok = False
        peers_out.append(
            {
                "agent_id": agent_id,
                "agent_ref": peer.get("agent_ref", agent_id),
                "ready": agent_ready,
                "gate": "ok" if agent_gate_ok else "fail",
                "bindings": [
                    {
                        "surface": r["surface"],
                        "provider_ref": r["provider_ref"],
                        "execution_profile_ref": r["execution_profile_ref"],
                        "status": r["status"],
                        "receipt_digest": r["receipt_digest"],
                    }
                    for r in receipts
                ],
            }
        )
    return {
        "schema": "l9.executable-peer-probe-report.v2",
        "status": "PASS" if gate_ok else "FAIL",
        "runtime_root": str(runtime_root),
        "status_counts": status_counts,
        "peers": peers_out,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    runtime = (
        args.runtime.expanduser().resolve() if args.runtime is not None else _resolve_runtime_root()
    )
    report = probe(_subsystem_root(), _repo_root(), runtime)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for peer in report["peers"]:
            mark = "READY" if peer["ready"] else "BLOCKED"
            bindings = ", ".join(f"{b['provider_ref']}={b['status']}" for b in peer["bindings"])
            print(f"[{mark}] {peer['agent_id']}: {bindings}")
        print(f"{report['status']} — {len(report['peers'])} execution.required peer(s)")
        for err in report.get("errors") or []:
            print(f"error: {err}", file=sys.stderr)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
