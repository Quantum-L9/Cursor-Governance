from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .digests import canonical_json, digest_object, normalize_digest, sha256_bytes

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


PROJECTION_CONTEXT_SCHEMA = "l9.peer-execution.projection-context.v1"


def projection_context(binding: Mapping[str, Any], repository_root: str | Path) -> dict[str, Any]:
    """The bound projection's views, re-verified and ready to hand to a worker.

    `binding` is the record Program Execution made when it bound the program to
    a projection: profile, bundle revision, and each view's repository-relative
    path and digest. Every view is read again and must still carry the digest
    that was bound; a view that moved, escaped the repository or is a symlink
    is refused. The worker is handed exactly the bytes that were verified.
    """
    profile_ref = _require_string("profile_ref", binding.get("profile_ref"))
    revision = _require_string("bundle_revision", binding.get("bundle_revision"))
    declared = binding.get("views")
    if not isinstance(declared, list) or not declared:
        raise ValueError("PROJECTION_VIEWS_ABSENT: the projection binding names no views")
    root = Path(repository_root).expanduser().resolve()
    views: list[dict[str, Any]] = []
    for item in declared:
        if not isinstance(item, Mapping):
            raise ValueError("PROJECTION_VIEW_MALFORMED: a view entry is not an object")
        relative = _require_string("view path", item.get("path"))
        expected = normalize_digest(_require_string("view digest", item.get("digest")))
        candidate = root / relative
        if candidate.is_symlink() or root not in candidate.resolve().parents:
            raise ValueError(f"PROJECTION_VIEW_ESCAPES: {relative} is not a file in {root}")
        try:
            raw = candidate.read_bytes()
        except OSError as exc:
            raise ValueError(f"PROJECTION_VIEW_UNREADABLE: {relative}: {exc}") from exc
        actual = sha256_bytes(raw)
        if actual != expected:
            raise ValueError(
                f"PROJECTION_VIEW_DRIFT: {relative} is {actual}, bound as {expected}; "
                "the projection changed after the program was bound to it"
            )
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"PROJECTION_VIEW_MALFORMED: {relative} is not JSON") from exc
        payload = document.get("payload") if isinstance(document, Mapping) else None
        if not isinstance(payload, Mapping) or not payload:
            raise ValueError(f"PROJECTION_VIEW_MALFORMED: {relative} carries no payload")
        views.append(
            {
                "path": relative,
                "digest": actual,
                "source_ref": _require_string("source_ref", document.get("source_ref")),
                "projection_digest": _require_string(
                    "projection_digest", document.get("projection_digest")
                ),
                "payload": dict(payload),
            }
        )
    views.sort(key=lambda view: view["path"])
    return {
        "schema": PROJECTION_CONTEXT_SCHEMA,
        "profile_ref": profile_ref,
        "bundle_revision": revision,
        "views": views,
    }


def _projection_instruction(projection: Mapping[str, Any]) -> list[str]:
    """The lines that hand a worker its bound projection, payloads included."""
    if projection.get("schema") != PROJECTION_CONTEXT_SCHEMA:
        raise ValueError("projection context has an unsupported schema")
    profile_ref = _require_string("profile_ref", projection.get("profile_ref"))
    revision = _require_string("bundle_revision", projection.get("bundle_revision"))
    views = projection.get("views")
    if not isinstance(views, list) or not views:
        raise ValueError("projection context carries no views")
    lines = [
        (
            f"This program is bound to the execution projection {profile_ref} at bundle "
            f"revision {revision}. Its views follow, one per line: the execution "
            "invariants, contracts and authority model for bounded code changes. Ground "
            "every implementation decision in them. They narrow how you carry out this "
            "contract and grant no authority beyond it. If they forbid what this contract "
            "asks, change nothing and report the conflict in residual_unknowns."
        )
    ]
    for view in views:
        if not isinstance(view, Mapping) or not isinstance(view.get("payload"), Mapping):
            raise ValueError("projection view carries no payload")
        lines.append(
            f"PROJECTION VIEW {_require_string('source_ref', view.get('source_ref'))} "
            f"{_require_string('digest', view.get('digest'))}: " + canonical_json(view["payload"])
        )
    return lines


def _projection_record(projection: Mapping[str, Any]) -> dict[str, Any]:
    """What the manifest records about the handed projection; payloads are in the
    instruction, which the manifest digest already covers."""
    return {
        "schema": projection["schema"],
        "profile_ref": projection["profile_ref"],
        "bundle_revision": projection["bundle_revision"],
        "views": [
            {key: view[key] for key in ("path", "digest", "source_ref", "projection_digest")}
            for view in projection["views"]
        ],
    }


def _safe_execution_id(value: str) -> str:
    execution_id = _require_string("execution_id", value)
    if execution_id in {".", ".."} or any(char in execution_id for char in ("/", "\\", "\x00")):
        raise ValueError("execution_id is not safe for a runtime filename")
    return execution_id


def build_context_manifest(
    contract: Mapping[str, Any],
    projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
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
            "Return only JSON. changed_files MUST be a JSON array of repo-relative paths.",
            "candidate_sha MUST be JSON null — do not git add or git commit; PE commits later.",
            "Also include validation_results (array) and residual_unknowns (array of strings).",
            (
                "validation_results MUST hold exactly one entry per command in the contract's "
                "validation_commands, in that order, and no other entry: the Controller refuses "
                "an attempt whose claimed commands differ from the contract's. Anything else "
                "you ran or observed belongs in that entry's evidence text."
            ),
            (
                "Each validation_results entry MUST be an object with exactly these four keys: "
                'command (string), status ("PASS", "FAIL", "BLOCKED" or "UNKNOWN"), '
                "exit_code (integer or null), evidence (string or null)."
            ),
            'claimed_status MUST be "completed" when the contract was executed.',
            (
                "residual_unknowns is a blocking field: every entry stops the Controller from "
                "accepting this attempt. List only a fact you could not establish that leaves "
                "the contract objective unmet; use [] when there is none."
            ),
            (
                "Not residual unknowns: gate and acceptance-criteria evaluation (the "
                "Controller's), pre-existing untracked worktree wiring (.cursor-commands, "
                ".cursor/, .l9/), and anything outside writable_paths, which is refused and is "
                "not yours to do."
            ),
            "Do not claim independent verification or program convergence.",
            *(_projection_instruction(projection) if projection is not None else ()),
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
    if projection is not None:
        body["projection"] = _projection_record(projection)
    body["manifest_digest"] = digest_object(body)
    return body


def write_context_manifest(
    runtime_root: str | Path,
    execution_id: str,
    contract: Mapping[str, Any],
    projection: Mapping[str, Any] | None = None,
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
    manifest = build_context_manifest(contract, projection)
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
