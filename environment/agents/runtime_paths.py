# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/Cursor-Governance
#   path: environment/agents/runtime_paths.py
#   layer: library
#   owner: governance-control-plane
#   status: active
#   version: 1.0.0
#   updated: 2026-08-12
"""Canonical L9 runtime path resolver (discover-legacy; never migrates DBs).

Canonical root is ``L9_RUNTIME_ROOT`` (default ``~/.l9``). ``L9_ROOT`` is the
operator-facing spelling the campaign Makefile targets use for the same root;
either name resolves it, and setting both to different roots is refused rather
than silently picked between. New subsystems MUST use the canonical helpers.
Existing locations remain discoverable via the ``discover_*`` helpers — Patch A
does not move databases.
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_RUNTIME_ROOT = "~/.l9"
RUNTIME_ROOT_ENV = "L9_RUNTIME_ROOT"
RUNTIME_ROOT_ALIAS_ENV = "L9_ROOT"


def runtime_root() -> Path:
    canonical = os.environ.get(RUNTIME_ROOT_ENV, "").strip()
    alias = os.environ.get(RUNTIME_ROOT_ALIAS_ENV, "").strip()
    if canonical and alias:
        resolved_canonical = Path(canonical).expanduser().resolve()
        resolved_alias = Path(alias).expanduser().resolve()
        if resolved_canonical != resolved_alias:
            raise RuntimeError(
                f"{RUNTIME_ROOT_ENV}={canonical!r} and {RUNTIME_ROOT_ALIAS_ENV}={alias!r} name "
                "different roots; they are two spellings of one root -- unset one"
            )
    value = canonical or alias or _DEFAULT_RUNTIME_ROOT
    return Path(value).expanduser().resolve()


def program_runtime_root() -> Path:
    override = os.environ.get("L9_PROGRAM_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (runtime_root() / "programs").resolve()


def program_worktree_root() -> Path:
    return (runtime_root() / "program-worktrees").resolve()


def agent_runtime_root() -> Path:
    return (runtime_root() / "agents").resolve()


def deployment_receipt_root() -> Path:
    return (agent_runtime_root() / "deployments").resolve()


def assignment_root() -> Path:
    return (agent_runtime_root() / "assignments").resolve()


def subagent_receipt_root() -> Path:
    return (agent_runtime_root() / "subagent-receipts").resolve()


def peer_readiness_root() -> Path:
    """Canonical peer-readiness receipt root.

    Legacy probe default was ``$L9_PROGRAM_HOME/_peer-readiness`` (often
    ``~/.l9/programs/_peer-readiness``). Canonical layout is
    ``$L9_RUNTIME_ROOT/agents/readiness``.
    """
    return (agent_runtime_root() / "readiness").resolve()


def runtime_readiness_root() -> Path:
    """Session/runtime bootstrap receipt root (sibling of peer readiness)."""
    return (peer_readiness_root() / "runtime").resolve()


def generated_data_root() -> Path:
    return (runtime_root() / "generated-data").resolve()


def canonical_generated_data_database() -> Path:
    return (generated_data_root() / "pipeline.sqlite3").resolve()


def generated_data_database() -> Path:
    """Preferred DB path for new writers: canonical under L9_RUNTIME_ROOT."""
    return canonical_generated_data_database()


def generated_data_evidence_root() -> Path:
    return (generated_data_root() / "evidence").resolve()


def generated_data_receipt_root() -> Path:
    return (generated_data_root() / "receipts").resolve()


def generated_data_quarantine_root() -> Path:
    return (generated_data_root() / "quarantine").resolve()


def generated_data_outbox_root() -> Path:
    return (generated_data_root() / "outbox").resolve()


def memory_outbox_root() -> Path:
    """Canonical memory-route candidate outbox (FileOutboxTransport + drain)."""
    return (generated_data_outbox_root() / "memory").resolve()


def discover_existing_generated_data_database(
    *,
    repo_root: Path | None = None,
) -> Path | None:
    """Return the first existing legacy/canonical generated-data DB, or None.

    Discovery order (first hit wins). Never creates or moves files.
    """
    candidates: list[Path] = [
        canonical_generated_data_database(),
        (program_runtime_root() / "generated-data" / "pipeline.sqlite3").resolve(),
    ]
    if repo_root is not None:
        root = Path(repo_root).expanduser().resolve()
        candidates.extend(
            [
                (root / ".l9" / "subagent-generated-data" / "pipeline.sqlite3").resolve(),
                (root / ".l9" / "generated-data" / "pipeline.sqlite3").resolve(),
            ]
        )
    home = Path.home()
    candidates.append((home / ".l9" / "subagent-generated-data" / "pipeline.sqlite3").resolve())

    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.is_file():
            return path
    return None


def discover_legacy_peer_readiness_root() -> Path:
    """Legacy readiness root used by probe_executable_peers before Patch A."""
    return (program_runtime_root() / "_peer-readiness").resolve()


def discover_autonomy_runtime_state() -> Path | None:
    """Locate an existing root-autonomy runtime sqlite if present."""
    candidates = [
        (Path.cwd() / ".l9" / "autonomy" / "runtime.sqlite3").resolve(),
        (runtime_root() / "autonomy" / "runtime.sqlite3").resolve(),
        (Path.home() / ".l9" / "autonomy" / "runtime.sqlite3").resolve(),
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None
