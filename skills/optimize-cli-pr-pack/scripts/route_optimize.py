#!/usr/bin/env python3
"""Deterministically route an optimize CLI revision to proportional proof obligations.

Path contract (Sonar S8707 / LLM+CLI path-escape):
  * ``--root`` is the only trusted directory root.
  * positional ``input`` and optional ``--output`` MUST be relative paths with no
    ``..`` segments; they are resolved via ``os.path.join`` + ``realpath`` +
    ``commonpath`` under ``--root`` before any filesystem access.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

THROUGHPUT_GAPS = {
    "artificial_delay",
    "unnecessary_serialization",
    "low_local_cap",
    "blocking_io",
    "repeated_startup",
    "duplicate_work",
    "buffering",
    "local_retry_backoff",
    "lock_contention",
}
CAPABILITY_GAPS = {
    "inactive_component",
    "miswired_file",
    "dormant_capability",
    "unused_signal",
    "orphaned_config_schema",
    "broken_partial_wiring",
    "latent_capability_wiring",
}
BOUNDARY_GAPS = {"other_repository_owned", "external_limit", "unknown"}
VALID_UTILIZATION_GAPS = THROUGHPUT_GAPS | CAPABILITY_GAPS | BOUNDARY_GAPS
VALID_OWNERSHIP = {"repository_owned", "external", "unknown"}
VALID_EVIDENCE = {"sufficient", "partial", "conflicting", "absent"}
VALID_RISK = {"reversible", "guarded", "irreversible"}
VALID_DIVERGENCE = {"none", "non_blocking", "release_blocking", "unknown"}
VALID_MODES = {"pack_only", "write_authorized"}


def under_root(root: Path, rel: str, *, label: str) -> Path:
    """Join ``rel`` under ``root`` and reject escapes / absolute paths."""
    if not rel or rel.startswith(("/", "\\")) or ".." in Path(rel).parts:
        raise ValueError(f"{label} must be a relative path without '..': {rel!r}")
    base = os.path.realpath(root)
    target = os.path.realpath(os.path.join(base, rel))
    try:
        if os.path.commonpath([base, target]) != base:
            raise ValueError(f"{label} escapes --root: {rel!r}")
    except ValueError as exc:
        if "escapes" in str(exc):
            raise
        raise ValueError(f"{label} escapes --root: {rel!r}") from exc
    return Path(target)


def _require(data: dict[str, Any], key: str, allowed: set[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{key} must be one of {sorted(allowed)}")
    return value


def route(data: dict[str, Any]) -> dict[str, Any]:
    gap = _require(data, "utilization_gap_class", VALID_UTILIZATION_GAPS)
    is_capability = gap in CAPABILITY_GAPS
    target_reachable = data.get("target_reachable", True)
    if not isinstance(target_reachable, bool):
        raise ValueError("target_reachable must be boolean")
    ownership = _require(data, "ownership", VALID_OWNERSHIP)
    evidence = _require(data, "evidence_state", VALID_EVIDENCE)
    risk = _require(data, "risk_class", VALID_RISK)
    divergence = _require(data, "docs_code_divergence", VALID_DIVERGENCE)
    mode = _require(data, "output_mode", VALID_MODES)
    latent = data.get("latent_capability")
    if not isinstance(latent, bool):
        raise ValueError("latent_capability must be boolean")

    obligations: list[dict[str, str]] = [
        {
            "id": "PO-OWNERSHIP",
            "description": "Prove repository ownership or classify the external/unknown blocker.",
            "source": "core",
        },
        {
            "id": "PO-CORRECTNESS",
            "description": "Preserve behavior, ordering, cancellation, signals, and exit codes.",
            "source": "core",
        },
        {
            "id": "PO-RESOURCE-ENVELOPE",
            "description": "Prove bounded resource use under the candidate path.",
            "source": "core",
        },
        {
            "id": "PO-LEVERAGE-SELECTION",
            "description": "Close the finding-target-option graph and select threshold-valid options.",
            "source": "leverage",
        },
        {
            "id": "PO-HANDOFF",
            "description": "Preserve exact resumable state and next action.",
            "source": "handoff",
        },
    ]
    adapters = ["revision_synthesis_leverage", "ecosystem_native_cli"]
    methods = ["deductive", "comparative"]

    if ownership == "repository_owned":
        obligations.append(
            {
                "id": "PO-UTILIZATION-PROOF",
                "description": "Show comparable before/after evidence: a throughput baseline-vs-candidate measurement, or a capability-activation functional proof that the capability is now reachable and exercised by a real entrypoint.",
                "source": "performance",
            }
        )
    if evidence != "sufficient":
        obligations.append(
            {
                "id": "PO-BASELINE",
                "description": "Resolve the exact evidence gap with a bounded probe.",
                "source": "evidence",
            }
        )
        methods.insert(0, "abductive")
    if latent or is_capability:
        obligations.append(
            {
                "id": "PO-REACHABILITY",
                "description": "Prove bidirectional reachability and rollout intent.",
                "source": "latent_capability",
            }
        )
        adapters.append("latent_capability_reachability")
    if divergence != "none":
        obligations.append(
            {
                "id": "PO-DIVERGENCE",
                "description": "Reconcile or disclose documentation-code divergence.",
                "source": "docs_code",
            }
        )
        adapters.append("docs_code_divergence")
    if risk in {"guarded", "irreversible"}:
        obligations.append(
            {
                "id": "PO-DEPLOY-ROLLBACK",
                "description": "Prove staged deployment, abort thresholds, and rollback.",
                "source": "risk",
            }
        )

    if ownership == "external":
        action = "blocked_pack"
    elif ownership == "repository_owned" and not target_reachable:
        action = "blocked_pack"
    elif (
        ownership == "unknown"
        or evidence in {"absent", "partial", "conflicting"}
        or divergence == "unknown"
    ):
        action = "bounded_probe"
    elif risk == "irreversible" or divergence == "release_blocking":
        action = "proceed_with_validation"
    else:
        action = "proceed"

    depth = (
        "deep"
        if risk == "irreversible" or evidence == "conflicting" or latent or is_capability
        else "standard"
    )
    if (
        risk == "reversible"
        and evidence == "sufficient"
        and not latent
        and not is_capability
        and divergence == "none"
    ):
        depth = "rapid"

    return {
        "route_version": "1.0.0",
        "task_kind": "optimize_cli_revision",
        "reasoning_depth": depth,
        "epistemic_methods": list(dict.fromkeys(methods)),
        "evidence_state": evidence,
        "risk_class": risk,
        "initial_action": action,
        "required_adapters": list(dict.fromkeys(adapters)),
        "proof_obligations": obligations,
        "max_cycles": 3,
        "stop_condition": "Stop when all active proof obligations are satisfied or cycle three packages a blocker.",
        "write_action_allowed": mode == "write_authorized",
        "utilization_gap_class": gap,
        "ownership": ownership,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Trusted directory root for input/output path resolution",
    )
    parser.add_argument("input", help="Input JSON path relative to --root")
    parser.add_argument("--output", help="Optional output JSON path relative to --root")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        input_path = under_root(root, args.input, label="input")
        with open(input_path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("input root must be an object")
        result = route(data)
        text = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            output_path = under_root(root, args.output, label="--output")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write(text)
        else:
            print(text, end="")
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
