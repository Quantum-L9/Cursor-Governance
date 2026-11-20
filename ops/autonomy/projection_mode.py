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
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - interpreter without PyYAML
    print(json.dumps({"mode": "BLOCKED", "reason": "INTERPRETER_UNRESOLVED"}))
    sys.exit(3)

REPO = Path(__file__).resolve().parents[2]


def _organization_policy(role: str) -> dict[str, Any]:
    """Same .github pin for every mode. A failure here does not change mode admission."""
    try:
        try:
            from org_policy_binding import bind
        except ImportError:
            from ops.autonomy.org_policy_binding import bind
        return bind(role)
    except (OSError, ValueError, ImportError) as exc:
        return {"status": "MISSING", "role": role, "reason": str(exc)}


def _policy_denials(role: str) -> list[dict[str, Any]]:
    """Authority claims this mode must not grant. Mode ON/OFF stays independent."""
    try:
        try:
            from org_policy_binding import AUTHORITY_CLAIMS, govern
        except ImportError:
            from ops.autonomy.org_policy_binding import AUTHORITY_CLAIMS, govern
        return [govern(action, role) for action in AUTHORITY_CLAIMS]
    except (OSError, ValueError, ImportError) as exc:
        return [{"action": "author_organization_policy", "allowed": False, "reason": str(exc)}]


# Host session identity, in order. The first names are the ones hooks document.
# Cursor agent shells set CURSOR_CONVERSATION_ID and not CURSOR_SESSION_ID;
# Claude cloud sets CLAUDE_CODE_REMOTE_SESSION_ID when the local id is absent.
# Those two are how `on` binds without a hand-passed --session-id. An earlier
# name still wins. "default" is not an identity. An unresolvable session never
# activates a mode.
SESSION_ENVS = (
    "CURSOR_SESSION_ID",
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "CURSOR_CONVERSATION_ID",
    "CLAUDE_CODE_REMOTE_SESSION_ID",
)
EXIT = {"ACTIVE": 0, "OFF": 0, "BLOCKED": 3, "REJECTED": 1, "STALE": 1}
ADMITTED = "ADMITTED_AND_CURRENT"
# The coding-agent execution projection keeps its own binding
# (governance/authority-bindings/coding-agent-execution.yaml) and status reader; a mode binds
# it through those instead of a second binding for the same projection.
CODING_BINDING_SCHEMA = "l9.cursor-governance.coding-projection-binding/v3"
CODING_BOUND = ("CURRENT", "BOUND")

Verify = Callable[[Path, Path | None], dict[str, Any]]


def binding_profile(doc: dict[str, Any]) -> tuple[str | None, str | None]:
    """(profile ref, verifier path) a binding declares, whichever binding shape it is."""
    if doc.get("schema") == CODING_BINDING_SCHEMA:
        return (doc.get("upstream") or {}).get("profile_ref"), (doc.get("verification") or {}).get(
            "status_reader"
        )
    pins = doc.get("input") or {}
    return (pins.get("authority") or {}).get("projection_profile_ref"), pins.get("verifier")


def binding_views(doc: dict[str, Any]) -> list[Path]:
    """The files a session reads once the binding verified."""
    if doc.get("schema") == CODING_BINDING_SCHEMA:
        return sorted((REPO / doc["bundle"]["path"] / "projections").glob("*.projection.json"))
    bundle = doc["input"]["bundle"]
    return [REPO / bundle["path"] / bundle["composed_view"]]


class ContractError(Exception):
    """The mode contract or a binding is malformed: fail closed."""


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def check_operating_protocol(protocol: Any) -> None:
    """Fail closed on a malformed operating protocol, or one that claims authority.

    A mode contract may carry behavioral defaults for the session that activates it. They
    are emitted with the mode status; they must declare that they grant no permission, and
    every invariant must be a non-empty statement.
    """
    if not isinstance(protocol, dict):
        raise ContractError("OPERATING_PROTOCOL_MALFORMED")
    if protocol.get("grants_permission") is not False:
        raise ContractError("OPERATING_PROTOCOL_MUST_GRANT_NO_PERMISSION")
    invariants = protocol.get("invariants")
    if not isinstance(invariants, dict) or not invariants:
        raise ContractError("OPERATING_PROTOCOL_INVARIANTS_EMPTY")
    for name, statement in invariants.items():
        if not isinstance(name, str) or not isinstance(statement, str) or not statement.strip():
            raise ContractError(f"OPERATING_PROTOCOL_INVARIANT_MALFORMED: {name}")
    check_protocol_sections(protocol)
    if "child_system_prompt" in protocol:
        check_child_system_prompt(protocol["child_system_prompt"])


# Every section /lcto tells the CTO to adopt. A protocol is consumed whole, so a missing
# or mistyped section fails closed instead of silently dropping a coordination rule.
PROTOCOL_LIST_SECTIONS = (
    "pre_launch",
    "child_brief_must_include",
    "child_launch_rules",
    "check_in",
    "handoff",
)
PROTOCOL_MAP_SECTIONS = ("roles",)
# Each declared host transport must say how the CTO reaches a child and how the child
# reaches the CTO, and how a child that stopped on a question is continued.
TRANSPORT_KEYS = ("cto_to_swarm", "swarm_to_cto", "continuation")


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def check_protocol_sections(protocol: dict[str, Any]) -> None:
    for name in PROTOCOL_LIST_SECTIONS:
        items = protocol.get(name)
        if not isinstance(items, list) or not items or not all(map(_nonempty_str, items)):
            raise ContractError(f"OPERATING_PROTOCOL_SECTION_MALFORMED: {name}")
    for name in PROTOCOL_MAP_SECTIONS:
        entries = protocol.get(name)
        if (
            not isinstance(entries, dict)
            or not entries
            or not all(_nonempty_str(k) and _nonempty_str(v) for k, v in entries.items())
        ):
            raise ContractError(f"OPERATING_PROTOCOL_SECTION_MALFORMED: {name}")
    transport = protocol.get("transport")
    if not isinstance(transport, dict) or not transport:
        raise ContractError("OPERATING_PROTOCOL_SECTION_MALFORMED: transport")
    for host, spec in transport.items():
        if not isinstance(spec, dict) or not all(
            _nonempty_str(spec.get(k)) for k in TRANSPORT_KEYS
        ):
            raise ContractError(f"OPERATING_PROTOCOL_TRANSPORT_INCOMPLETE: {host}")


CTO_SESSION_PLACEHOLDER = "{cto_session}"
# A child launch prompt must carry the transcript reporting route and must never name a
# cross-session send tool: a later message cannot override a launch system prompt.
CHILD_PROMPT_REQUIRED = (
    "CTO-STATUS:",
    "CTO-QUESTION:",
    "CTO-BLOCKER:",
    CTO_SESSION_PLACEHOLDER,
    # Every swarm agent is deployed with the coding-agent projections enabled.
    'coding_agent_mode.py" on',
    "ACTIVE",
    # Projections and modes govern the swarm; a skill is never a substitute.
    "Never invoke the l9-coding-agent skill",
    # The publishing agent owns its PR until it is ready to merge, then returns to the
    # pool idle; the CTO owns integration and never remediates (protocol v2, 2026-11-16).
    "CTO-STATUS: ready-to-merge",
    "CTO-STATUS: idle",
    "CTO ASSIGN",
    # Quantum-L9/.github is the session source (add_repo refuses dot names); the primary
    # repository and Cursor-Governance are attached before role registration (2026-11-17).
    "never call add_repo for it",
    "Attach your primary repository (access push) and Quantum-L9/Cursor-Governance",
    # A pool outlives its CTO: coordinator transfer is explicit and re-registers the role,
    # and a published PR stays repairable by its owner after the owner takes another lane.
    "CTO TRANSFER <new session id>",
    "You own every PR you published until it merges",
    # The child registers its role so hooks enforce it (ops/autonomy/session_role.py),
    # and publishes without spawning remediation or PR watching.
    'session_role.py" register-child --cto-session {cto_session}',
    "PR_REMEDIATE=0",
)
CHILD_PROMPT_FORBIDDEN = ("send_message", "SendMessage")


def check_child_system_prompt(template: Any) -> None:
    if not isinstance(template, str) or not template.strip():
        raise ContractError("CHILD_SYSTEM_PROMPT_MALFORMED")
    missing = [token for token in CHILD_PROMPT_REQUIRED if token not in template]
    if missing:
        raise ContractError(f"CHILD_SYSTEM_PROMPT_INCOMPLETE: {', '.join(missing)}")
    named = [token for token in CHILD_PROMPT_FORBIDDEN if token in template]
    if named:
        raise ContractError(f"CHILD_SYSTEM_PROMPT_NAMES_SEND_TOOL: {', '.join(named)}")


def render_child_prompt(contract: dict[str, Any], cto_session: str) -> str:
    """The canonical child launch system prompt, with the CTO session filled in."""
    template = (contract.get("operating_protocol") or {}).get("child_system_prompt")
    if template is None:
        raise ContractError("CHILD_SYSTEM_PROMPT_UNDECLARED")
    if not cto_session.strip():
        raise ContractError("CTO_SESSION_UNRESOLVED")
    return str(template).replace(CTO_SESSION_PLACEHOLDER, cto_session.strip())


LAUNCH_SPEC_SCHEMA = "l9.cto-child-launch-spec/v1"
LAUNCH_HOST = "claude-code"
_CHILD_SESSION_KEYS = ("source_url", "permission_mode", "governance_repository")


def _repo_coordinate(value: str) -> tuple[str, str]:
    parts = value.strip().split("/")
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ContractError(f"LANE_REPO_MALFORMED: {value}")
    return parts[0].strip(), parts[1].strip()


def _declared_child_session(contract: dict[str, Any]) -> dict[str, Any]:
    transport = ((contract.get("operating_protocol") or {}).get("transport") or {}).get(
        LAUNCH_HOST
    ) or {}
    child = transport.get("child_session")
    if not isinstance(child, dict) or not all(
        _nonempty_str(child.get(key)) for key in _CHILD_SESSION_KEYS
    ):
        raise ContractError("CHILD_SESSION_UNDECLARED")
    return child


def _source_repo(source_url: str) -> str:
    return "/".join(source_url.rstrip("/").removesuffix(".git").split("/")[-2:]).lower()


def _attachment_list(
    source_url: str, governance: str, lane_repos: list[str]
) -> list[dict[str, str]]:
    """Push attachments for lane repos, plus governance read when it is not a lane."""
    if not lane_repos:
        raise ContractError("LANE_REPO_REQUIRED")
    source_repo = _source_repo(source_url)
    attach: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in lane_repos:
        owner, repo = _repo_coordinate(value)
        key = f"{owner}/{repo}".lower()
        # The source repository is read-only to every child, and add_repo refuses it.
        if key == source_repo:
            raise ContractError(f"LANE_REPO_IS_SESSION_SOURCE: {value}")
        if key not in seen:
            seen.add(key)
            attach.append({"owner": owner, "repo": repo, "access": "push"})
    if governance.lower() not in seen:
        owner, repo = governance.split("/")
        attach.append({"owner": owner, "repo": repo, "access": "read"})
    return attach


def _session_tags(cto_session: str, tags: list[str] | None) -> list[str]:
    session_tags = [f"cto:{cto_session.strip()}"]
    for tag in tags or []:
        if _nonempty_str(tag) and tag.strip() not in session_tags:
            session_tags.append(tag.strip())
    return session_tags


def _create_session_args(
    child: dict[str, Any],
    prompt: str,
    cto_session: str,
    *,
    title: str | None,
    tags: list[str] | None,
) -> dict[str, Any]:
    create: dict[str, Any] = {
        "source_url": str(child["source_url"]).strip(),
        "append_system_prompt": prompt,
        "permission_mode": str(child["permission_mode"]).strip(),
        "tags": _session_tags(cto_session, tags),
    }
    if _nonempty_str(title):
        create["title"] = str(title).strip()
    return create


def build_launch_spec(
    contract: dict[str, Any],
    cto_session: str,
    lane_repos: list[str],
    *,
    title: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """The create_session arguments and the add_repo list for one swarm child.

    Every value comes from the mode contract or the arguments; nothing is inferred. It
    grants nothing: the CTO still makes the call, and the child still attaches.
    """
    child = _declared_child_session(contract)
    prompt = render_child_prompt(contract, cto_session)
    source = str(child["source_url"]).strip()
    governance = "/".join(_repo_coordinate(str(child["governance_repository"])))
    return {
        "schema": LAUNCH_SPEC_SCHEMA,
        "grants_permission": False,
        "host": LAUNCH_HOST,
        "create_session": _create_session_args(child, prompt, cto_session, title=title, tags=tags),
        "add_repo": _attachment_list(source, governance, lane_repos),
    }


def resolve_session_id(explicit: str | None = None) -> str | None:
    """The host session this command runs in, or None when it cannot be proven."""
    for candidate in (explicit, *(os.environ.get(name) for name in SESSION_ENVS)):
        if isinstance(candidate, str) and candidate.strip() and candidate.strip() != "default":
            return candidate.strip()
    return None


@contextmanager
def authority_main_checkout(root: Path | None) -> Iterator[Path | None]:
    """Yield a checkout whose HEAD is ``refs/remotes/origin/main``.

    Domain verifiers refuse a checkout whose HEAD is not that pin, so every
    consumer repository goes STALE (``AUTHORITY_REVISION_MISMATCH``) when the
    shared Quantum-L9/.github clone sits on another branch. The operating plane
    already detaches a shared checkout at the pin (``pinned_checkout``) and
    leaves the operator's branch alone. Domain verification uses that same
    snapshot. No ``origin/main`` yields *root* unchanged, and the verifier
    reports that absence itself.
    """
    if root is None:
        yield None
        return
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools.authority.verify_coding_projection import Unobserved, pinned_checkout, resolve

    main = resolve(root, "refs/remotes/origin/main")
    if main is None:
        yield root
        return
    try:
        holder = pinned_checkout(root, main)
    except Unobserved:
        yield root
        return
    with holder as checkout:
        yield Path(checkout) / "authority"


def run_verifier(binding: Path, authority_root: Path | None) -> dict[str, Any]:
    """The binding's own verifier, admitted mode. No second verification lives here."""
    doc = yaml.safe_load(binding.read_text(encoding="utf-8"))
    coding = doc.get("schema") == CODING_BINDING_SCHEMA
    _ref, verifier = binding_profile(doc)
    with authority_main_checkout(authority_root) as pinned:
        cmd = [sys.executable, str(REPO / str(verifier))]
        if coding:
            # The shared coding-projection classifier: the same verdict SessionStart reports.
            cmd += ["--format", "json"]
        else:
            cmd += ["--binding", str(binding), "--mode", "admitted"]
        if pinned is not None:
            cmd += ["--authority-root", str(pinned)]
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
    return coding_verdict(report) if coding else report


def coding_verdict(report: dict[str, Any]) -> dict[str, Any]:
    """Map the coding classifier onto the verifier verdict a mode judges.

    ADMITTED_AND_CURRENT only when the bundle verifies at main (CURRENT, or BOUND against the
    checkout's origin/main) AND its admission decision admits the exact profile digest.
    """
    status, detail = report["status"], report.get("detail")
    admission = (report.get("admission") or {}).get("status")
    if status in CODING_BOUND and admission == ADMITTED:
        return {"status": ADMITTED, "reason": f"{status}: {detail}"}
    if status in CODING_BOUND:
        return {"status": "BLOCKED", "reason": f"ADMISSION_NOT_PROVED: {admission}"}
    return {"status": status, "reason": detail}


def resolve_authority(explicit: Path | None, workspace: Path | None) -> Path | None:
    """The Quantum-L9/.github checkout, resolved like every other projection consumer here.

    One order for all of them (ops/scripts/coding_projection_status.py `_authority`): an
    explicit path, then L9_AUTHORITY_ROOT, then the managed ``~/.l9/authority/.github``
    checkout, then `.github` inside or beside the workspace. Each is accepted only if
    it is a verified authority checkout. None when none is. Callers that verify pass
    the result through ``authority_main_checkout`` so the clone's own branch is not
    the pin.
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
            ref, verifier = binding_profile(
                yaml.safe_load(binding.read_text(encoding="utf-8")) or {}
            )
            if ref != entry["ref"]:
                raise ContractError(f"BINDING_REF_MISMATCH: {entry['binding']}")
            if not isinstance(verifier, str) or not (REPO / verifier).is_file():
                raise ContractError(f"BINDING_VERIFIER_UNDECLARED: {entry['binding']}")
        if "operating_protocol" in doc:
            check_operating_protocol(doc["operating_protocol"])
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
            "organization_policy": _organization_policy(self.name),
            "organization_policy_denials": _policy_denials(self.name),
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
                views = [str(path) for path in binding_views(binding)]
                item: dict[str, Any] = {
                    "ref": entry["ref"],
                    "views": views,
                    "provenance": result.get("architecture_intelligence"),
                }
                if binding.get("schema") != CODING_BINDING_SCHEMA:
                    item["composed_view"] = views[0]
                load.append(item)
            elif entry["required"]:
                blockers.append(record)
        mode = "ACTIVE" if not blockers else "BLOCKED"
        result_report = {
            **report,
            "mode": mode,
            "requested_at": state.get("requested_at"),
            "selection_status": contract["selection"].get("status"),
            "projections": projections,
            "blockers": blockers,
            "load": load if mode == "ACTIVE" else [],
        }
        if "operating_protocol" in contract:
            # Behavior, not projection semantics: it applies whether or not every
            # projection is admitted, because the persona still runs when BLOCKED.
            result_report["operating_protocol"] = contract["operating_protocol"]
        return result_report

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

    def record_outcome(
        self, workspace: Path, report: dict[str, Any], session_id: str | None = None
    ) -> None:
        """Stamp the last evaluated mode on this session's own request.

        Gates read it cheaply (``last_mode`` + ``last_contract_digest``) instead of re-running
        the verifiers on every tool call; the stamp is only written onto a request made by
        the same session, so it never vouches for another session. Best-effort.
        """
        path = self.state_path(workspace)
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        current = resolve_session_id(session_id)
        if not isinstance(state, dict) or state.get("session_id") != current:
            return
        state["last_mode"] = report.get("mode")
        state["last_evaluated_at"] = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        state["last_contract_digest"] = state.get("contract_digest")
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            tmp.replace(path)
        except OSError:
            return

    def release(self, workspace: Path) -> bool:
        path = self.state_path(workspace)
        if path.is_file():
            path.unlink()
            return True
        return False

    def _parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description=f"{self.name} mode: opt-in, session-bound projection binding"
        )
        commands = ["on", "off", "status", "child-prompt"]
        # Launching swarm children is the CTO's alone; other modes keep their commands.
        if self.name == "cto":
            commands.append("launch-spec")
        parser.add_argument("command", choices=commands)
        parser.add_argument(
            "--cto-session",
            help=(
                "child-prompt: the CTO session id (default: this host session's "
                "cross-session id, session_<suffix>, else its local id)"
            ),
        )
        if self.name == "cto":
            parser.add_argument(
                "--lane-repo",
                action="append",
                default=[],
                help="launch-spec: owner/name of a lane repository the child attaches (push)",
            )
            parser.add_argument("--title", help="launch-spec: the child session title")
            parser.add_argument(
                "--tag", action="append", default=[], help="launch-spec: an extra session tag"
            )
        parser.add_argument("--workspace", type=Path, default=Path.cwd())
        parser.add_argument(
            "--authority-root",
            type=Path,
            help=(
                "Quantum-L9/.github checkout (default: $L9_AUTHORITY_ROOT, "
                "then ~/.l9/authority/.github, then .github in or beside the workspace). "
                "Verification reads origin/main; the checkout's branch is not the pin."
            ),
        )
        parser.add_argument(
            "--session-id", help=f"host session id (default: first of {', '.join(SESSION_ENVS)})"
        )
        return parser

    def _print_child_prompt(self, args: argparse.Namespace) -> int:
        """Plain text on stdout: the child's launch system prompt, verbatim."""
        try:
            # Default to the id cross-session tools address (session_<suffix>), not the
            # local host id: children must recognize the CTO's messages by it.
            from session_role import remote_session_id  # noqa: PLC0415

            session = (
                args.cto_session or remote_session_id() or resolve_session_id(args.session_id)
            ) or ""
            print(render_child_prompt(self.load_contract(), session))
        except ContractError as exc:
            print(json.dumps({"mode": "REJECTED", "reason": str(exc)}, sort_keys=True))
            return EXIT["REJECTED"]
        return 0

    def _print_launch_spec(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
        """JSON on stdout: the create_session arguments and the child's add_repo list."""
        if not args.cto_session or not args.cto_session.strip():
            parser.error("launch-spec requires --cto-session")
        if not args.lane_repo:
            parser.error("launch-spec requires at least one --lane-repo")
        try:
            spec = build_launch_spec(
                self.load_contract(),
                args.cto_session,
                args.lane_repo,
                title=args.title,
                tags=args.tag,
            )
        except ContractError as exc:
            print(json.dumps({"mode": "REJECTED", "reason": str(exc)}, sort_keys=True))
            return EXIT["REJECTED"]
        print(json.dumps(spec, indent=2, sort_keys=True))
        return 0

    def _request_on(self, workspace: Path, args: argparse.Namespace) -> int | None:
        try:
            self.request(workspace, session_id=args.session_id)
        except ContractError as exc:
            print(json.dumps({"mode": "REJECTED", "reason": str(exc)}, sort_keys=True))
            return EXIT["REJECTED"]
        return None

    def cite_operator_view(self, receipt: Path) -> str:
        """Opt-in citation. Mode evaluation does not call this."""
        from ops.autonomy.operator_alignment import opt_in_operator_view

        return opt_in_operator_view(receipt)

    def main(self, argv: list[str] | None = None) -> int:
        parser = self._parser()
        args = parser.parse_args(argv)
        workspace = args.workspace.resolve()
        if args.command == "child-prompt":
            return self._print_child_prompt(args)
        if args.command == "launch-spec":
            return self._print_launch_spec(parser, args)
        if args.command == "off":
            removed = self.release(workspace)
            print(json.dumps({"mode": "OFF", "state_removed": removed}, sort_keys=True))
            return 0
        if args.command == "on":
            rejected = self._request_on(workspace, args)
            if rejected is not None:
                return rejected
        report = self.evaluate(
            workspace, authority_root=args.authority_root, session_id=args.session_id
        )
        if args.command in ("on", "status"):
            self.record_outcome(workspace, report, session_id=args.session_id)
        print(json.dumps(report, indent=2, sort_keys=True))
        return EXIT[report["mode"]]
