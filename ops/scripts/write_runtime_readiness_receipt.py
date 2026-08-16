#!/usr/bin/env python3
"""Write l9.agents.runtime-readiness.v1 — UNKNOWN never omitted."""

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


def classify_status(
    *,
    governance_revision: str,
    runtime_script_revision: str,
    bound_sha: str,
    degraded_count: int,
) -> tuple[str, str]:
    known = _known_shas(governance_revision, runtime_script_revision, bound_sha)
    if len(set(known)) > 1:
        return NOT_READY, REVISION_MISMATCH
    if UNKNOWN in {governance_revision, runtime_script_revision}:
        return DEGRADED, ""
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
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    gov_dir = Path(args.governance).expanduser().resolve() if args.governance else workspace
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
    receipt = build_receipt(
        surface=args.surface,
        workspace=workspace,
        governance_revision=gov_rev,
        runtime_script_revision=runtime_rev,
        session_id=session_id,
        memory_state_root=memory_root,
        graphiti_state_file=graphiti,
        components=[],
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
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
