#!/usr/bin/env python3
"""Write l9.agents.runtime-readiness.v1 — UNKNOWN never omitted.

The receipt is the only thing Program Execution consults before admitting a
governed mutation, so it must describe the runtime that is actually installed —
governance SSOT, locked interpreter, generated environment, this surface's
adapter, the skill plane, the workspace checkout, and the session/memory
identity — rather than asserting a status over an unexamined environment.

A component marked ``REQUIRED`` answers "who is executing" and "where does
governed state live". When one of those is unresolved the receipt is NOT_READY:
an unattributable session is not a session PE may mutate from. ``ADVISORY``
components are described for diagnosis only — the shared bootstrap remains the
single authority on what counts as degraded, via ``--degraded-count``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from environment.agents.runtime_paths import runtime_readiness_root  # noqa: E402

SCHEMA = "l9.agents.runtime-readiness.v1"
UNKNOWN = "UNKNOWN"
READY = "READY"
DEGRADED = "DEGRADED"
NOT_READY = "NOT_READY"
REVISION_MISMATCH = "REVISION_MISMATCH"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
RUNTIME_COMPONENT_MISSING = "RUNTIME_COMPONENT_MISSING"

PRESENT = "PRESENT"
MISSING = "MISSING"

# A component the receipt only describes; its absence degrades the session but a
# session can still legitimately run without it (a workspace that is not a git
# checkout, a surface with no adapter directory of its own).
ADVISORY = "advisory"
# A component whose unresolved state makes the receipt unable to say WHO is
# executing or WHERE governed state lives. Program Execution cannot admit a
# mutation it cannot attribute, so these prevent READY rather than annotate it.
REQUIRED = "required"


def _unknown(value: str | None) -> str:
    text = (value or "").strip()
    return text if text else UNKNOWN


def _git_sha(cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return UNKNOWN
    sha = (proc.stdout or "").strip()
    return sha if proc.returncode == 0 and sha else UNKNOWN


def workspace_id_for(workspace: Path) -> str:
    resolved = str(workspace.expanduser().resolve())
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()


def receipt_path(*, surface: str, workspace: Path) -> Path:
    return (runtime_readiness_root() / surface / f"{workspace_id_for(workspace)}.json").resolve()


def compute_receipt_digest(receipt: dict[str, Any]) -> str:
    payload = dict(receipt)
    payload.pop("receipt_digest", None)
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _known_shas(*values: str) -> list[str]:
    return [value for value in values if value and value != UNKNOWN]


# --- component enumeration --------------------------------------------------
def _component(
    component_id: str,
    kind: str,
    status: str,
    *,
    requirement: str = ADVISORY,
    detail: str = "",
    digest: str = UNKNOWN,
) -> dict[str, str]:
    return {
        "id": component_id,
        "kind": kind,
        "status": status,
        "requirement": requirement,
        "detail": detail,
        "digest": digest,
    }


def _manifest_digest(root: Path, pattern: str = "*") -> tuple[str, int]:
    """Digest the sorted relative-path manifest under ``root``.

    Content is already pinned by ``governance_revision`` (the checkout SHA); what
    that SHA cannot express is a *partially generated* tree, where a projection
    or installer wrote some of its outputs and not the rest. Hashing the path
    manifest — not file bodies — detects exactly that, cheaply and stably.
    """
    try:
        names = sorted(
            str(path.relative_to(root))
            for path in root.rglob(pattern)
            if path.is_file() and not path.name.startswith(".")
        )
    except OSError:
        return UNKNOWN, 0
    if not names:
        return UNKNOWN, 0
    raw = "\n".join(names).encode("utf-8")
    return hashlib.sha256(raw).hexdigest(), len(names)


def _tree_component(
    component_id: str,
    kind: str,
    root: Path,
    *,
    requirement: str = ADVISORY,
    pattern: str = "*",
) -> dict[str, str]:
    if not root.is_dir():
        return _component(
            component_id, kind, MISSING, requirement=requirement, detail=f"absent: {root}"
        )
    digest, count = _manifest_digest(root, pattern)
    if not count:
        return _component(
            component_id, kind, MISSING, requirement=requirement, detail=f"empty: {root}"
        )
    return _component(
        component_id,
        kind,
        PRESENT,
        requirement=requirement,
        detail=f"{count} file(s)",
        digest=digest,
    )


def collect_components(
    *,
    surface: str,
    workspace: Path,
    governance: Path,
    session_id: str,
    memory_state_root: str,
    graphiti_state_file: str,
) -> list[dict[str, str]]:
    """Describe the runtime components actually installed for this session.

    The receipt is only useful to Program Execution if it names what is really in
    use — the governance SSOT, the locked interpreter, the generated environment,
    this surface's adapter, the skill plane, the workspace checkout, and the
    session/memory identity. Everything here is observed, never assumed.
    """
    components: list[dict[str, str]] = []

    law = governance / "CANONICAL_LAW.md"
    components.append(
        _component(
            "governance.ssot",
            "governance",
            PRESENT if law.is_file() else MISSING,
            requirement=REQUIRED,
            detail=str(governance),
        )
    )

    interpreter = governance / ".venv" / "bin" / "python3"
    components.append(
        _component(
            "governance.locked_interpreter",
            "toolchain",
            PRESENT if os.access(interpreter, os.X_OK) else MISSING,
            detail=str(interpreter),
        )
    )

    components.append(
        _tree_component(
            "environment.generated_llm_rules",
            "generated",
            governance / "environment" / "generated" / "llm-rules",
            pattern="*.md",
        )
    )

    registry = governance / "ops" / "generated" / "skill-registry.json"
    components.append(
        _component(
            "environment.skill_registry",
            "generated",
            PRESENT if registry.is_file() else MISSING,
            detail=str(registry),
        )
    )

    components.append(
        _tree_component("environment.skills", "skills", governance / "skills", pattern="SKILL.md")
    )

    adapter = governance / "environment" / "agents" / "adapters" / surface
    components.append(
        _tree_component(f"adapter.{surface}", "adapter", adapter)
        if adapter.is_dir()
        else _component(
            f"adapter.{surface}",
            "adapter",
            MISSING,
            detail=f"no adapter directory for surface {surface!r}",
        )
    )

    workspace_sha = _git_sha(workspace)
    components.append(
        _component(
            "workspace.checkout",
            "workspace",
            PRESENT if workspace_sha != UNKNOWN else MISSING,
            detail=str(workspace),
            digest=workspace_sha,
        )
    )

    components.append(
        _component(
            "session.identity",
            "identity",
            PRESENT if session_id != UNKNOWN else MISSING,
            requirement=REQUIRED,
            detail="session id resolved" if session_id != UNKNOWN else "no session id in surface",
        )
    )

    components.append(
        _component(
            "memory.state_root",
            "identity",
            PRESENT
            if memory_state_root != UNKNOWN and Path(memory_state_root).is_dir()
            else MISSING,
            requirement=REQUIRED,
            detail=memory_state_root,
        )
    )

    components.append(
        _component(
            "memory.graphiti_state",
            "identity",
            PRESENT
            if graphiti_state_file != UNKNOWN and Path(graphiti_state_file).is_file()
            else MISSING,
            detail=graphiti_state_file,
        )
    )
    return components


def unresolved(components: list[dict[str, str]], requirement: str) -> list[str]:
    return [
        str(item.get("id"))
        for item in components
        if item.get("requirement") == requirement and item.get("status") != PRESENT
    ]


def classify_status(
    *,
    governance_revision: str,
    runtime_script_revision: str,
    bound_sha: str,
    degraded_count: int,
    components: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    rows = components or []
    known = _known_shas(governance_revision, runtime_script_revision, bound_sha)
    if len(set(known)) > 1:
        return NOT_READY, REVISION_MISMATCH
    missing_required = unresolved(rows, REQUIRED)
    if missing_required:
        code = (
            IDENTITY_UNRESOLVED
            if any(row.startswith(("session.", "memory.")) for row in missing_required)
            else RUNTIME_COMPONENT_MISSING
        )
        return NOT_READY, code
    if UNKNOWN in {governance_revision, runtime_script_revision}:
        return DEGRADED, ""
    # ADVISORY components are described, never re-judged here: the shared
    # bootstrap already owns what counts as a degraded component and passes its
    # tally as degraded_count. Deriving a second verdict from the same facts
    # would put two authorities on one question.
    if degraded_count > 0:
        return DEGRADED, ""
    return READY, ""


def build_receipt(
    *,
    surface: str,
    workspace: Path,
    governance_revision: str,
    runtime_script_revision: str,
    session_id: str,
    memory_state_root: str,
    graphiti_state_file: str,
    components: list[dict[str, str]],
    degraded_count: int,
    bound_sha: str = UNKNOWN,
) -> dict[str, Any]:
    gov = _unknown(governance_revision)
    runtime = _unknown(runtime_script_revision)
    bound = _unknown(bound_sha)
    status, failure = classify_status(
        governance_revision=gov,
        runtime_script_revision=runtime,
        bound_sha=bound,
        degraded_count=degraded_count,
        components=components,
    )
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "surface": _unknown(surface),
        "workspace": {
            "id": workspace_id_for(workspace),
            "path": str(workspace.expanduser().resolve()),
        },
        "governance_revision": gov,
        "runtime_script_revision": runtime,
        "bound_workspace_sha": bound,
        "session_id": _unknown(session_id),
        "memory_state_root": _unknown(memory_state_root),
        "graphiti_state_file": _unknown(graphiti_state_file),
        "components": components,
        "degraded_count": int(degraded_count),
        "unresolved_required": unresolved(components, REQUIRED),
        "overall_status": status,
        "failure_code": failure,
        "observed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    body["receipt_digest"] = compute_receipt_digest(body)
    return body


def write_receipt(receipt: dict[str, Any], *, surface: str, workspace: Path) -> Path:
    path = receipt_path(surface=surface, workspace=workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _default_session_id() -> str:
    return (
        os.environ.get("CURSOR_CONVERSATION_ID")
        or os.environ.get("CURSOR_SESSION_ID")
        or os.environ.get("CLAUDE_SESSION_ID")
        or UNKNOWN
    )


def _default_memory_root(workspace: Path) -> str:
    root = workspace / ".l9" / "memory"
    return str(root.resolve()) if root.is_dir() else UNKNOWN


def _default_graphiti_state(session_id: str) -> str:
    conv = session_id if session_id != UNKNOWN else "default"
    return str(Path.home() / ".cursor" / "graphiti-state" / f"{conv}.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a runtime readiness receipt")
    parser.add_argument("--surface", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--governance", default="")
    parser.add_argument("--governance-revision", default="")
    parser.add_argument("--runtime-script-revision", default="")
    parser.add_argument("--bound-sha", default="")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--memory-state-root", default="")
    parser.add_argument("--graphiti-state-file", default="")
    parser.add_argument("--degraded-count", type=int, default=0)
    parser.add_argument("--omit-governance-revision", action="store_true")
    parser.add_argument("--omit-runtime-script-revision", action="store_true")
    parser.add_argument(
        "--restamp-session",
        action="store_true",
        help=(
            "stamp session identity onto the existing receipt, reusing its recorded "
            "revisions and degraded count instead of re-observing them"
        ),
    )
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    gov_dir = Path(args.governance).expanduser().resolve() if args.governance else workspace

    # A surface learns its session id only after the bootstrap has run — the
    # SessionStart hook has it, the bootstrap does not. Restamping records that
    # identity without re-deriving readiness: the degraded tally the bootstrap
    # observed is carried over verbatim, so this can resolve an identity but can
    # never upgrade a degraded runtime into a READY one.
    if args.restamp_session:
        prior_path = receipt_path(surface=args.surface, workspace=workspace)
        if prior_path.is_file():
            try:
                prior = json.loads(prior_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prior = {}
            if isinstance(prior, dict) and prior:
                args.governance_revision = args.governance_revision or prior.get(
                    "governance_revision", ""
                )
                args.runtime_script_revision = args.runtime_script_revision or prior.get(
                    "runtime_script_revision", ""
                )
                args.bound_sha = args.bound_sha or prior.get("bound_workspace_sha", "")
                # A receipt written before degraded_count was recorded must not
                # be read as "zero degraded components" — that would let a
                # restamp launder DEGRADED into READY. Fall back to the prior
                # verdict, which is the conservative reading.
                if "degraded_count" in prior:
                    args.degraded_count = int(prior.get("degraded_count") or 0)
                elif str(prior.get("overall_status") or "") == DEGRADED:
                    args.degraded_count = max(1, args.degraded_count)
                for field in ("governance_revision", "runtime_script_revision", "bound_sha"):
                    if getattr(args, field) == UNKNOWN:
                        setattr(args, field, "")
    gov_rev = (
        UNKNOWN
        if args.omit_governance_revision
        else (args.governance_revision or _git_sha(gov_dir))
    )
    runtime_rev = (
        UNKNOWN
        if args.omit_runtime_script_revision
        else (args.runtime_script_revision or _git_sha(gov_dir))
    )
    session_id = _unknown(args.session_id or _default_session_id())
    memory_root = args.memory_state_root or _default_memory_root(workspace)
    graphiti = args.graphiti_state_file or _default_graphiti_state(session_id)
    components = collect_components(
        surface=args.surface,
        workspace=workspace,
        governance=gov_dir,
        session_id=session_id,
        memory_state_root=memory_root,
        graphiti_state_file=graphiti,
    )
    receipt = build_receipt(
        surface=args.surface,
        workspace=workspace,
        governance_revision=gov_rev,
        runtime_script_revision=runtime_rev,
        session_id=session_id,
        memory_state_root=memory_root,
        graphiti_state_file=graphiti,
        components=components,
        degraded_count=args.degraded_count,
        bound_sha=args.bound_sha,
    )
    path = write_receipt(receipt, surface=args.surface, workspace=workspace)
    print(
        json.dumps(
            {
                "status": "WRITTEN",
                "path": str(path),
                "overall_status": receipt["overall_status"],
                "failure_code": receipt["failure_code"],
                "unresolved_required": receipt["unresolved_required"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
