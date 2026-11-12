#!/usr/bin/env python3
"""Host default projection binding — what every session of a host reads without opting in.

Contract: governance/host-bindings/<host>.yaml (`l9.cursor-governance.host-binding/v1`), one
per host (`cursor`, `claude-code`). Both hosts' SessionStart hooks call this module, so every
bootstrapped session is bound automatically: no skill, command or opt-in is involved, and a
contract that does not declare `session_start.autobind: true` with
`depends_on_skill: false` is rejected.

The default binding is the admitted operating plane
(`l9.projection/cursor-governance-operating-plane@2`), verified by its own consumer adapter in
admitted mode. It is BOUND only when that adapter reports CURRENT; the session then reads its
source classes through the adapter, which releases a class only after re-verifying it. Any
other adapter status leaves the session NOT_BOUND with the exact reason, and nothing from the
operating plane may be cited.

On top of the base a contract may list domain projections (the Cursor contract mirrors
Quantum-L9/.github `l9.domain-consumer-binding/cursor@1`), each verified by the verifier its
binding declares. `always` domains are loaded in every session; a conditional domain
(`hosted_skill_requirement`, `explicit_task_requirement`) is loaded only when that activation
is named, and is otherwise neither verified nor loaded.

The overall status is BOUND when the base is CURRENT and every activated domain is
ADMITTED_AND_CURRENT, otherwise BLOCKED with each exact reason. It changes what a session
reads, never what it may do. Other projections are bound only by the manual modes
(`/coding-agent`, `/lcto`, `/architect`).

Usage:
  host_binding.py [--host cursor|claude-code] [--activate ACTIVATION ...] [--workspace DIR]
                  [--authority-root DIR] [--domains-only] [--format json|markdown|line]

json exits 0 BOUND, 3 BLOCKED, 1 REJECTED; markdown and line are SessionStart renderings and
exit 0.
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
    start = doc.get("session_start")
    if (
        not isinstance(start, dict)
        or start.get("autobind") is not True
        or start.get("depends_on_skill") is not False
    ):
        # The default binding is made by SessionStart itself; a skill never gates it.
        raise ContractError("SESSION_START_AUTOBIND_REQUIRED")
    base = doc.get("base")
    if not isinstance(base, dict) or base.get("required") is not True:
        raise ContractError("BASE_MUST_BE_REQUIRED")
    if not isinstance(base.get("ref"), str) or not base["ref"]:
        raise ContractError("BASE_REF_UNRESOLVED")
    for key in ("binding", "adapter"):
        if not isinstance(base.get(key), str) or not (REPO / base[key]).is_file():
            raise ContractError(f"BASE_{key.upper()}_UNRESOLVED")
    domains = doc.get("domains")
    if not isinstance(domains, list):
        # An empty list is valid: the host binds the operating plane alone.
        raise ContractError("DOMAINS_MALFORMED")
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


def default_binding(
    base: dict[str, Any],
    result: dict[str, Any],
    workspace: Path | None,
    authority: Path | None,
) -> dict[str, Any]:
    """The session's default binding: the base, BOUND only on its adapter's CURRENT."""
    if result.get("status") != BASE_CURRENT:
        return {
            "ref": base["ref"],
            "status": "NOT_BOUND",
            "reason": f"{result.get('status')}: {result.get('reason')}",
        }
    read = [sys.executable, str(REPO / base["adapter"]), "--mode", "admitted"]
    if workspace is not None:
        read += ["--workspace", str(workspace)]
    if authority is not None:
        # The checkout the binding was verified against, so a read cannot resolve another.
        read += ["--authority-root", str(authority)]
    return {
        "ref": base["ref"],
        "status": "BOUND",
        "automatic": True,
        "authority_main": result.get("authority_main"),
        "source_classes": result.get("source_classes") or [],
        # Releases one class (or one invariant/contract record) after re-verifying it.
        "read": [*read, "--source-class", "<class>"],
    }


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
        report["default"] = {"ref": base["ref"], "status": "NOT_EVALUATED"}
    else:
        result = verify_base(base, workspace, authority)
        report["base"] = {
            "ref": base["ref"],
            "status": result["status"],
            "reason": result.get("reason"),
        }
        report["default"] = default_binding(base, result, workspace, authority)
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


MANUAL = "/coding-agent, /lcto, /architect"


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg else arg


def _items(report: dict[str, Any]) -> list[str]:
    """The binding as plain items; markdown prefixes them, line indents them."""
    if report["status"] == "REJECTED":
        return [f"REJECTED: {report['reason']}"]
    items: list[str] = []
    default = report.get("default") or {}
    if default.get("status") == "BOUND":
        main = str(default.get("authority_main") or "")[:12]
        items += [
            f"BOUND (automatic at session start): {default['ref']} at authority main {main}",
            "source classes: " + ", ".join(default["source_classes"]),
            "read a class before deciding a question it governs, and cite the profile and "
            "authority main: `" + " ".join(_quote(a) for a in default["read"]) + "`",
        ]
    elif default.get("status") == "NOT_BOUND":
        items.append(
            f"NOT BOUND: {default['ref']} {default['reason']}. Cite no operating-plane "
            "semantics this session."
        )
    if report["domains"]:
        items.append(f"domains ({report.get('canonical_binding_ref')}): {report['status']}")
        for item in report["domains"]:
            detail = (
                item["status"] if item["status"] != "NOT_ACTIVATED" else f"on {item['activation']}"
            )
            items.append(f"  {item['ref']} [{item['activation']}]: {detail}")
    items.append(f"manual bindings: {MANUAL}")
    return items


def markdown(report: dict[str, Any]) -> str:
    """Cursor SessionStart rendering."""
    lines = [f"### default projection binding ({report['host']})"]
    for item in _items(report):
        nested = item.startswith("  ")
        lines.append(f"  - {item.strip()}" if nested else f"- {item}")
    return "\n".join(lines)


def line(report: dict[str, Any]) -> str:
    """Claude Code SessionStart rendering: one heading line, then indented items."""
    items = _items(report)
    head, rest = items[0], items[1:]
    out = [f"default projection binding ({report['host']}): {head}"]
    out += [f"  {item}" for item in rest]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="cursor", choices=("cursor", "claude-code"))
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
    parser.add_argument("--format", choices=("json", "markdown", "line"), default="json")
    args = parser.parse_args(argv)
    report = evaluate(
        args.host,
        activations=frozenset(args.activate),
        workspace=args.workspace.resolve(),
        authority_root=args.authority_root,
        domains_only=args.domains_only,
    )
    if args.format in ("markdown", "line"):
        print(markdown(report) if args.format == "markdown" else line(report))
        return 0
    print(json.dumps(report, indent=2, sort_keys=True))
    return EXIT[report["status"]]


if __name__ == "__main__":
    sys.exit(main())
