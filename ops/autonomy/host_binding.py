#!/usr/bin/env python3
"""Host default projection binding — what every session of a host reads without opting in.

Contract: governance/host-bindings/<host>.yaml (`l9.cursor-governance.host-binding/v1`).
The Cursor contract mirrors Quantum-L9/.github `l9.domain-consumer-binding/cursor@1`: the
admitted operating plane (`l9.projection/cursor-governance-operating-plane@2`) is the base,
verified by its own adapter; each domain projection is verified by the verifier its binding
declares. `always` domains are loaded in every session; a conditional domain
(`hosted_skill_requirement`, `explicit_task_requirement`) is loaded only when that activation
is named. A domain that is not activated is not verified and not loaded.

The binding is BOUND when the base is CURRENT and every activated domain is
ADMITTED_AND_CURRENT, otherwise BLOCKED with each exact reason; nothing is loaded from a
projection that did not verify. It changes what a session reads, never what it may do.

Usage:
  host_binding.py [--host cursor] [--activate ACTIVATION ...] [--workspace DIR]
                  [--authority-root DIR] [--domains-only] [--format json|markdown]

json exits 0 BOUND, 3 BLOCKED, 1 REJECTED; markdown is a SessionStart report and exits 0.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from projection_mode import (  # noqa: E402
    ADMITTED,
    REPO,
    ContractError,
    resolve_authority,
    run_verifier,
)

try:
    import yaml
except ImportError:  # pragma: no cover - interpreter without PyYAML
    print(json.dumps({"status": "BLOCKED", "reason": "INTERPRETER_UNRESOLVED"}))
    sys.exit(3)

SCHEMA = "l9.cursor-governance.host-binding/v1"
ACTIVATIONS = ("always", "hosted_skill_requirement", "explicit_task_requirement")
EXIT = {"BOUND": 0, "BLOCKED": 3, "REJECTED": 1}
BASE_CURRENT = "CURRENT"

Verify = Callable[[Path, Path | None], dict[str, Any]]
VerifyBase = Callable[[dict[str, Any], Path | None, Path | None], dict[str, Any]]


def contract_path(host: str) -> Path:
    return REPO / "governance" / "host-bindings" / f"{host}.yaml"


def load_contract(path: Path) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ContractError(f"HOST_BINDING_UNREADABLE: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ContractError("HOST_BINDING_SCHEMA_MISMATCH")
    base = doc.get("base")
    if not isinstance(base, dict) or base.get("required") is not True:
        raise ContractError("BASE_MUST_BE_REQUIRED")
    if not isinstance(base.get("ref"), str) or not base["ref"]:
        raise ContractError("BASE_REF_UNRESOLVED")
    for key in ("binding", "adapter"):
        if not isinstance(base.get(key), str) or not (REPO / base[key]).is_file():
            raise ContractError(f"BASE_{key.upper()}_UNRESOLVED")
    domains = doc.get("domains")
    if not isinstance(domains, list) or not domains:
        raise ContractError("DOMAINS_EMPTY")
    seen: set[str] = set()
    for entry in domains:
        if not isinstance(entry, dict) or not all(
            isinstance(entry.get(k), str) and entry[k] for k in ("ref", "binding", "activation")
        ):
            raise ContractError("DOMAIN_ENTRY_MALFORMED")
        if entry["activation"] not in ACTIVATIONS:
            raise ContractError(f"ACTIVATION_UNKNOWN: {entry['ref']} {entry['activation']}")
        if entry["ref"] in seen or entry["ref"] == base["ref"]:
            raise ContractError(f"DOMAIN_DUPLICATE: {entry['ref']}")
        seen.add(entry["ref"])
        binding = REPO / entry["binding"]
        if not binding.is_file():
            raise ContractError(f"BINDING_ABSENT: {entry['binding']}")
        pins = (yaml.safe_load(binding.read_text(encoding="utf-8")) or {}).get("input", {})
        if (pins.get("authority") or {}).get("projection_profile_ref") != entry["ref"]:
            raise ContractError(f"BINDING_REF_MISMATCH: {entry['binding']}")
    return doc


def run_base(
    base: dict[str, Any], workspace: Path | None, authority: Path | None
) -> dict[str, Any]:
    """The base's own consumer adapter, admitted mode. No second verification lives here."""
    cmd = [sys.executable, str(REPO / base["adapter"]), "--mode", "admitted", "--format", "json"]
    if workspace is not None:
        cmd += ["--workspace", str(workspace)]
    if authority is not None:
        cmd += ["--authority-root", str(authority)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, dict) or not isinstance(report.get("status"), str):
        return {"status": "BLOCKED", "reason": "ADAPTER_OUTPUT_UNREADABLE", "exit": proc.returncode}
    return report


def evaluate(
    host: str = "cursor",
    *,
    activations: frozenset[str] = frozenset(),
    workspace: Path | None = None,
    authority_root: Path | None = None,
    domains_only: bool = False,
    path: Path | None = None,
    verify: Verify = run_verifier,
    verify_base: VerifyBase = run_base,
) -> dict[str, Any]:
    report: dict[str, Any] = {"schema": "l9.host-binding-status/v1", "host": host}
    unknown = sorted(activations - set(ACTIVATIONS) - {"always"})
    if unknown:
        return {**report, "status": "REJECTED", "reason": f"ACTIVATION_UNKNOWN: {unknown}"}
    try:
        contract = load_contract(path or contract_path(host))
    except ContractError as exc:
        return {**report, "status": "REJECTED", "reason": str(exc)}
    authority = resolve_authority(authority_root, workspace)
    active = {"always", *activations}
    blockers: list[dict[str, Any]] = []
    load: list[dict[str, Any]] = []
    base = contract["base"]
    if domains_only:
        report["base"] = {"ref": base["ref"], "status": "NOT_EVALUATED", "reason": "DOMAINS_ONLY"}
    else:
        result = verify_base(base, workspace, authority)
        report["base"] = {
            "ref": base["ref"],
            "status": result["status"],
            "reason": result.get("reason"),
        }
        if result["status"] != BASE_CURRENT:
            blockers.append(report["base"])
    domains = []
    for entry in contract["domains"]:
        record: dict[str, Any] = {"ref": entry["ref"], "activation": entry["activation"]}
        if entry["activation"] not in active:
            domains.append({**record, "status": "NOT_ACTIVATED"})
            continue
        result = verify(REPO / entry["binding"], authority)
        record.update(status=result.get("status"), reason=result.get("reason"))
        domains.append(record)
        if result.get("status") == ADMITTED:
            bundle = yaml.safe_load((REPO / entry["binding"]).read_text("utf-8"))["input"]["bundle"]
            load.append(
                {
                    "ref": entry["ref"],
                    "composed_view": str(REPO / bundle["path"] / bundle["composed_view"]),
                }
            )
        else:
            blockers.append(record)
    status = "BOUND" if not blockers else "BLOCKED"
    return {
        **report,
        "status": status,
        "canonical_binding_ref": contract.get("canonical_binding_ref"),
        "activations": sorted(active),
        "authority_root": str(authority) if authority else None,
        "domains": domains,
        "blockers": blockers,
        "load": load if status == "BOUND" else [],
    }


def markdown(report: dict[str, Any]) -> str:
    lines = [f"### {report['host']} host binding (report-only)"]
    if report["status"] == "REJECTED":
        return "\n".join([*lines, f"- REJECTED: {report['reason']}"])
    base = report["base"]
    lines.append(f"- status: {report['status']} ({report.get('canonical_binding_ref')})")
    if base["status"] != "NOT_EVALUATED":
        lines.append(f"- base {base['ref']}: {base['status']}")
    for item in report["domains"]:
        detail = item["status"] if item["status"] != "NOT_ACTIVATED" else f"on {item['activation']}"
        lines.append(f"- {item['ref']} [{item['activation']}]: {detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="cursor")
    parser.add_argument(
        "--activate",
        action="append",
        default=[],
        choices=[a for a in ACTIVATIONS if a != "always"],
        help="load the conditional domains with this activation as well",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--authority-root", type=Path)
    parser.add_argument(
        "--domains-only",
        action="store_true",
        help="skip the base (SessionStart reports it through its own adapter block)",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    report = evaluate(
        args.host,
        activations=frozenset(args.activate),
        workspace=args.workspace.resolve(),
        authority_root=args.authority_root,
        domains_only=args.domains_only,
    )
    if args.format == "markdown":
        print(markdown(report))
        return 0
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
