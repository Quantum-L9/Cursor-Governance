#!/usr/bin/env python3
"""Opt-in, session-bound modes that bind selected L9 projections.

One implementation for every projection mode (CTO mode, architect mode). A mode is
configured by a contract (`governance/<name>-mode/MODE.yaml`) that names the projections
it binds, each through a binding verified by the verifier that binding declares. The
mode modules (`cto_mode.py`, `architect_mode.py`) only name their contract.

State lives in <workspace>/.l9/<name>-mode/session.json, bound to the host session that
requested it. Another session, or one whose id cannot be resolved, sees the mode as OFF.
While requested, every selected projection is checked in admitted mode; the mode is
ACTIVE only when every required projection is ADMITTED_AND_CURRENT, and otherwise
BLOCKED with each exact reason and nothing loaded from that projection. A mode changes
what a session reads, never what it may do.

Exit codes: 0 ACTIVE or OFF, 3 BLOCKED, 1 REJECTED or STALE, 2 usage.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - interpreter without PyYAML
    print(json.dumps({"mode": "BLOCKED", "reason": "INTERPRETER_UNRESOLVED"}))
    sys.exit(3)

REPO = Path(__file__).resolve().parents[2]
# Host session identity, in order. An unresolvable session never activates a mode.
SESSION_ENVS = ("CURSOR_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")
EXIT = {"ACTIVE": 0, "OFF": 0, "BLOCKED": 3, "REJECTED": 1, "STALE": 1}
ADMITTED = "ADMITTED_AND_CURRENT"

Verify = Callable[[Path, Path | None], dict[str, Any]]


class ContractError(Exception):
    """The mode contract or a binding is malformed: fail closed."""


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_session_id(explicit: str | None = None) -> str | None:
    """The host session this command runs in, or None when it cannot be proven."""
    for candidate in (explicit, *(os.environ.get(name) for name in SESSION_ENVS)):
        if isinstance(candidate, str) and candidate.strip() and candidate.strip() != "default":
            return candidate.strip()
    return None


def run_verifier(binding: Path, authority_root: Path | None) -> dict[str, Any]:
    """The binding's own verifier, admitted mode. No second verification lives here."""
    pins = yaml.safe_load(binding.read_text(encoding="utf-8"))["input"]
    cmd = [
        sys.executable,
        str(REPO / pins["verifier"]),
        "--binding",
        str(binding),
        "--mode",
        "admitted",
    ]
    if authority_root is not None:
        cmd += ["--authority-root", str(authority_root)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, dict) or not isinstance(report.get("status"), str):
        return {
            "status": "BLOCKED",
            "reason": "VERIFIER_OUTPUT_UNREADABLE",
            "exit": proc.returncode,
        }
    return report


def resolve_authority(explicit: Path | None, workspace: Path | None) -> Path | None:
    """The Quantum-L9/.github checkout, resolved like every other projection consumer here.

    One order for all of them (ops/scripts/coding_projection_status.py `_authority`): an
    explicit path, then L9_AUTHORITY_ROOT, then `.github` inside or beside the workspace,
    each accepted only if it is a verified authority checkout. None when none is.
    """
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from ops.scripts.coding_projection_status import _authority

    root, _rejected = _authority(workspace, explicit)
    return root


@dataclass(frozen=True)
class ProjectionMode:
    """One opt-in projection mode, identified by *name* (`cto`, `architect`)."""

    name: str

    @property
    def contract(self) -> Path:
        return REPO / f"governance/{self.name}-mode/MODE.yaml"

    @property
    def contract_schema(self) -> str:
        return f"l9.cursor-governance.{self.name}-mode/v1"

    @property
    def state_schema(self) -> str:
        return f"l9.{self.name}-mode-session/v1"

    @property
    def state_rel(self) -> Path:
        return Path(f".l9/{self.name}-mode/session.json")

    def state_path(self, workspace: Path) -> Path:
        return workspace / self.state_rel

    def load_contract(self, path: Path | None = None) -> dict[str, Any]:
        path = path or self.contract
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ContractError(f"MODE_CONTRACT_UNREADABLE: {exc}") from exc
        if not isinstance(doc, dict) or doc.get("schema") != self.contract_schema:
            raise ContractError("MODE_CONTRACT_SCHEMA_MISMATCH")
        activation = doc.get("activation") or {}
        if activation.get("default") is not False or activation.get("always_enabled") is not False:
            raise ContractError("MODE_MUST_BE_OPT_IN")
        projections = (doc.get("selection") or {}).get("projections")
        if not isinstance(projections, list) or not projections:
            raise ContractError("SELECTION_EMPTY")
        refs = set()
        for entry in projections:
            if not isinstance(entry, dict) or not all(
                isinstance(entry.get(k), str) and entry[k] for k in ("ref", "binding")
            ):
                raise ContractError("SELECTION_ENTRY_MALFORMED")
            if not isinstance(entry.get("required"), bool):
                raise ContractError(f"SELECTION_REQUIRED_UNDECLARED: {entry['ref']}")
            if entry["ref"] in refs:
                raise ContractError(f"SELECTION_DUPLICATE: {entry['ref']}")
            refs.add(entry["ref"])
            binding = REPO / entry["binding"]
            if not binding.is_file():
                raise ContractError(f"BINDING_ABSENT: {entry['binding']}")
            pins = (yaml.safe_load(binding.read_text(encoding="utf-8")) or {}).get("input", {})
            if (pins.get("authority") or {}).get("projection_profile_ref") != entry["ref"]:
                raise ContractError(f"BINDING_REF_MISMATCH: {entry['binding']}")
            if not isinstance(pins.get("verifier"), str):
                raise ContractError(f"BINDING_VERIFIER_UNDECLARED: {entry['binding']}")
        return doc

    def evaluate(
        self,
        workspace: Path,
        *,
        authority_root: Path | None = None,
        contract_path: Path | None = None,
        verify: Verify = run_verifier,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Mode status for *workspace* in the current session. Reads state; never writes it."""
        contract_path = contract_path or self.contract
        report: dict[str, Any] = {
            "schema": f"l9.{self.name}-mode-status/v1",
            "workspace": str(workspace),
        }
        try:
            contract = self.load_contract(contract_path)
        except ContractError as exc:
            return {**report, "mode": "REJECTED", "reason": str(exc)}
        state_file = self.state_path(workspace)
        if not state_file.is_file():
            return {**report, "mode": "OFF", "reason": "NOT_REQUESTED_IN_THIS_WORKSPACE"}
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {**report, "mode": "REJECTED", "reason": "STATE_UNREADABLE"}
        if not isinstance(state, dict) or state.get("schema") != self.state_schema:
            return {**report, "mode": "REJECTED", "reason": "STATE_SCHEMA_MISMATCH"}
        current = resolve_session_id(session_id)
        if current is None:
            return {**report, "mode": "OFF", "reason": "SESSION_UNRESOLVED"}
        if state.get("session_id") != current:
            # A request belongs to the session that made it; it never carries over.
            return {**report, "mode": "OFF", "reason": "REQUESTED_IN_ANOTHER_SESSION"}
        if state.get("contract_digest") != _digest(contract_path):
            # The selection changed since the operator asked; ask again rather than widen.
            return {**report, "mode": "STALE", "reason": "MODE_CONTRACT_CHANGED_SINCE_REQUEST"}
        root = resolve_authority(authority_root, workspace)
        projections, blockers, load = [], [], []
        for entry in contract["selection"]["projections"]:
            result = verify(REPO / entry["binding"], root)
            status = result.get("status")
            record = {
                "ref": entry["ref"],
                "required": entry["required"],
                "status": status,
                "reason": result.get("reason"),
            }
            projections.append(record)
            if status == ADMITTED:
                binding = yaml.safe_load((REPO / entry["binding"]).read_text("utf-8"))
                bundle = binding["input"]["bundle"]
                load.append(
                    {
                        "ref": entry["ref"],
                        "composed_view": str(REPO / bundle["path"] / bundle["composed_view"]),
                        "provenance": result.get("architecture_intelligence"),
                    }
                )
            elif entry["required"]:
                blockers.append(record)
        mode = "ACTIVE" if not blockers else "BLOCKED"
        return {
            **report,
            "mode": mode,
            "requested_at": state.get("requested_at"),
            "selection_status": contract["selection"].get("status"),
            "projections": projections,
            "blockers": blockers,
            "load": load if mode == "ACTIVE" else [],
        }

    def request(
        self,
        workspace: Path,
        contract_path: Path | None = None,
        session_id: str | None = None,
    ) -> Path:
        contract_path = contract_path or self.contract
        self.load_contract(contract_path)
        current = resolve_session_id(session_id)
        if current is None:
            raise ContractError(
                "SESSION_UNRESOLVED: pass --session-id or run inside a host session"
            )
        path = self.state_path(workspace)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "schema": self.state_schema,
            "requested_at": _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session_id": current,
            "contract": str(contract_path),
            "contract_digest": _digest(contract_path),
        }
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
        return path

    def release(self, workspace: Path) -> bool:
        path = self.state_path(workspace)
        if path.is_file():
            path.unlink()
            return True
        return False

    def main(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(
            description=f"{self.name} mode: opt-in, session-bound projection binding"
        )
        parser.add_argument("command", choices=("on", "off", "status"))
        parser.add_argument("--workspace", type=Path, default=Path.cwd())
        parser.add_argument(
            "--authority-root",
            type=Path,
            help=(
                "Quantum-L9/.github checkout (default: $L9_AUTHORITY_ROOT, "
                "then .github in or beside the workspace)"
            ),
        )
        parser.add_argument(
            "--session-id", help=f"host session id (default: first of {', '.join(SESSION_ENVS)})"
        )
        args = parser.parse_args(argv)
        workspace = args.workspace.resolve()
        if args.command == "off":
            removed = self.release(workspace)
            print(json.dumps({"mode": "OFF", "state_removed": removed}, sort_keys=True))
            return 0
        if args.command == "on":
            try:
                self.request(workspace, session_id=args.session_id)
            except ContractError as exc:
                print(json.dumps({"mode": "REJECTED", "reason": str(exc)}, sort_keys=True))
                return EXIT["REJECTED"]
        report = self.evaluate(
            workspace, authority_root=args.authority_root, session_id=args.session_id
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT[report["mode"]]
