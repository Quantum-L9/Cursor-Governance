from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .digests import digest_object, normalize_digest

if TYPE_CHECKING:
    from .provider import CanonicalExecutionRequest


def _require_string(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _string_list(name: str, value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    result: list[str] = []
    for item in value:
        result.append(_require_string(name, item))
    if len(set(result)) != len(result):
        raise ValueError(f"{name} must contain unique values")
    return result


def _safe_execution_id(value: str) -> str:
    execution_id = _require_string("execution_id", value)
    if execution_id in {".", ".."} or any(char in execution_id for char in ("/", "\\", "\x00")):
        raise ValueError("execution_id is not safe for a runtime filename")
    return execution_id


def build_context_manifest(contract: Mapping[str, Any]) -> dict[str, Any]:
    rendered = dict(contract)
    task_id = _require_string("task_id", rendered.get("task_id") or rendered.get("id"))
    program_digest = normalize_digest(
        _require_string(
            "program_lock_digest",
            rendered.get("program_lock_digest") or rendered.get("program_digest"),
        )
    )
    contract_digest = normalize_digest(
        _require_string(
            "rendered_contract_digest",
            rendered.get("rendered_contract_digest") or rendered.get("contract_digest"),
        )
    )
    worktree = _require_string("worktree", rendered.get("worktree"))
    base_sha = _require_string("base_sha", rendered.get("base_sha"))
    writable_paths = _string_list("writable_paths", rendered.get("writable_paths"))
    validation_commands = _string_list(
        "validation_commands",
        rendered.get("validation_commands"),
    )
    required_evidence_ids = _string_list(
        "required_evidence_ids",
        rendered.get("required_evidence_ids"),
    )
    compact_contract = json.dumps(
        rendered,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    instruction = "\n".join(
        [
            "Execute this exact Program Execution Rendered Contract.",
            "Stay inside its worktree, requested actions, writable paths, and stop conditions.",
            "Return only JSON containing candidate_sha, changed_files, validation_results,",
            "and residual_unknowns. Do not claim independent verification or program convergence.",
            compact_contract,
        ]
    )
    body = {
        "schema": "l9.peer-execution.context-manifest.v1",
        "task_id": task_id,
        "program_lock_digest": program_digest,
        "rendered_contract_digest": contract_digest,
        "base_sha": base_sha,
        "worktree": worktree,
        "writable_paths": writable_paths,
        "validation_commands": validation_commands,
        "required_evidence_ids": required_evidence_ids,
        "rendered_contract": rendered,
        "worker_instruction": instruction,
    }
    body["manifest_digest"] = digest_object(body)
    return body


def write_context_manifest(
    runtime_root: str | Path,
    execution_id: str,
    contract: Mapping[str, Any],
) -> Path:
    safe_id = _safe_execution_id(execution_id)
    runtime = Path(runtime_root).expanduser().resolve()
    root = runtime / "contexts"
    if root.is_symlink():
        raise ValueError(f"refusing symlinked context directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    if root.resolve() != root or runtime not in root.resolve().parents:
        raise ValueError("context directory escapes runtime root")
    path = root / f"{safe_id}.json"
    if path.is_symlink():
        raise ValueError(f"refusing symlinked context manifest: {path}")
    manifest = build_context_manifest(contract)
    if path.is_file():
        existing = load_context_manifest(path)
        if existing.get("manifest_digest") != manifest["manifest_digest"]:
            raise ValueError("existing context manifest does not match execution contract")
        return path
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=root,
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path


def load_context_manifest(path: str | Path) -> dict[str, Any]:
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError(f"refusing symlinked context manifest: {target}")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("context manifest must be an object")
    if value.get("schema") != "l9.peer-execution.context-manifest.v1":
        raise ValueError("unsupported context manifest schema")
    digest = value.get("manifest_digest")
    if not isinstance(digest, str):
        raise ValueError("context manifest digest is missing")
    body = dict(value)
    body.pop("manifest_digest", None)
    if digest_object(body) != normalize_digest(digest):
        raise ValueError("context manifest digest mismatch")
    return value


def load_execution_context(request: CanonicalExecutionRequest) -> dict[str, Any]:
    """Load a digest-valid context and bind it back to the canonical request."""

    value = load_context_manifest(request.context_manifest_ref)
    expected = {
        "task_id": request.task_id,
        "program_lock_digest": request.program_lock_digest,
        "rendered_contract_digest": request.rendered_contract_digest,
        "worktree": request.worktree_ref,
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            raise ValueError(f"context manifest {key} does not match execution request")
    return value
