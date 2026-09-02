#!/usr/bin/env python3
"""Compile long-form architecture prose into an executable campaign-source.v2.

    architecture prose
        → semantic architecture compilation
        → coverage + provenance repair
        → campaign-source.v2
        → Blueprint v2 → PEC → execute

Everything this script does happens *before* the campaign has side effects. It
writes only into the compiler cache under `$L9_ROOT/primed/<id>/`, which is a
compiler artifact area and not an executing PEC workspace. If compilation fails
— unreadable source, an unresolvable target, coverage that will not converge, a
material contradiction the source itself cannot settle — it fails here, with no
worktree, no Blueprint, no controller state, and no task claimed.

The failure mode this replaces is worse than a failure: a Blueprint full of
BLOCKED tasks that looks like a program and can never run. A program that can be
compiled should execute; a program that cannot should never have been minted.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

PE_ROOT = Path(__file__).resolve().parents[1]
# APPEND, never insert(0): Program Execution needs its own PE-exclusive
# packages here, but `scripts` is a top-level name it SHARES with the
# repository root. Prepending would hand PE's `scripts/` that name for the
# whole process. See peer_execution.imports.pe_script.
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))

from compiler.architecture_coverage import (  # noqa: E402
    DEFAULT_REPAIR_ROUNDS,
    ExtractionResult,
    extract_semantics,
)
from compiler.architecture_extractor import (  # noqa: E402
    ExtractorError,
    ExtractorUnavailable,
    resolve_extractor,
)
from compiler.architecture_intent import (  # noqa: E402
    ArchitectureIntent,
    ArchitectureIntentError,
    architecture_campaign_id,
    load_architecture_intent,
)
from compiler.architecture_to_campaign import (  # noqa: E402
    LoweredCampaign,
    LoweringError,
    inspect_repository,
    lower,
)

FAILURE_CODE = "PE_ARCHITECTURE_COMPILE_FAILED"


class ArchitectureCompileError(RuntimeError):
    """Terminal, self-explaining. Nothing has executed when this raises."""

    exit_code = 2

    def __init__(self, reason: str, *, fix: str = "", detail: dict[str, Any] | None = None) -> None:
        self.reason = reason.strip()
        self.fix = fix.strip()
        self.detail = detail or {}
        super().__init__(self.render())

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": FAILURE_CODE,
            "reason": self.reason,
            "fix": self.fix,
            "nothing_executed": True,
            "workspace_created": False,
            "tasks_started": 0,
            **self.detail,
        }

    def render(self) -> str:
        lines = [FAILURE_CODE, "", "reason:", f"  {self.reason}", ""]
        for key, value in self.detail.items():
            lines.append(f"{key}: {json.dumps(value) if not isinstance(value, str) else value}")
        if self.detail:
            lines.append("")
        lines.extend(
            [
                "nothing_executed: true",
                "workspace_created: false",
                "tasks_started: 0",
            ]
        )
        if self.fix:
            lines.extend(["", "fix:", f"  {self.fix}"])
        return "\n".join(lines) + "\n"


def default_cache_root() -> Path:
    return Path(os.environ.get("L9_ROOT", str(Path.home() / ".l9"))).resolve() / "primed"


def existing_campaign_ids(repo_root: Path | None) -> set[str]:
    """Ids that already exist — a collision check, never an admission list.

    Derived from real state (campaign directories, the status ledger, completed
    campaigns). It answers "does this id already exist", and deliberately not
    "is this id permitted to exist": no campaign needs preregistration to
    compile.
    """
    ids: set[str] = set()
    if repo_root is None:
        return ids
    campaigns = Path(repo_root) / "environment/program-execution/campaigns"
    if campaigns.is_dir():
        for path in campaigns.iterdir():
            if path.is_dir() and path.name not in {"COMPLETED", "scripts", "stale"}:
                ids.add(path.name)
        completed = campaigns / "COMPLETED"
        if completed.is_dir():
            for path in completed.iterdir():
                if path.is_dir() and path.name != "stale":
                    ids.add(path.name)
        status = campaigns / "CAMPAIGN_STATUS.yaml"
        if status.is_file():
            import yaml

            try:
                raw = yaml.safe_load(status.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError as exc:
                # An unreadable ledger hid every id it records, so a collision
                # check that "passed" proved nothing.
                raise ArchitectureCompileError(
                    f"campaign status ledger is unreadable: {status}: {exc}"
                ) from exc
            for entry in raw.get("campaigns") or []:
                if isinstance(entry, dict) and entry.get("id"):
                    ids.add(str(entry["id"]))
    return ids


def compile_architecture_intent(
    path: Path,
    *,
    target: str | None = None,
    forced: bool = True,
    repo_root: Path | None = None,
    target_checkout: Path | None = None,
    campaign_id: str | None = None,
    cache_root: Path | None = None,
    extractor_name: str = "",
    extractor: Any | None = None,
    repair_rounds: int = DEFAULT_REPAIR_ROUNDS,
    critic: bool = True,
    max_chunk_chars: int | None = None,
    owner: str | None = None,
    stamp: str | None = None,
) -> dict[str, Any]:
    """Run the whole architecture route and return a receipt.

    The receipt names the emitted campaign source; the caller (the runner) then
    enters the *same* direct campaign-source placement path an operator-supplied
    source uses, so nothing about the richer representation is rebuilt from a
    weaker one on the way in.
    """
    intent = _load(path, target=target, forced=forced)
    extraction = _extract(
        intent,
        extractor=extractor,
        extractor_name=extractor_name,
        repair_rounds=repair_rounds,
        critic=critic,
        max_chunk_chars=max_chunk_chars,
    )
    _refuse_unresolved_contradictions(intent, extraction)
    resolved_id = campaign_id or architecture_campaign_id(intent, existing_campaign_ids(repo_root))
    facts = inspect_repository(target_checkout, intent.target)
    try:
        lowered: LoweredCampaign = lower(
            intent,
            extraction,
            campaign_id=resolved_id,
            owner=owner or "Igor Beylin",
            repository=facts,
            stamp=stamp,
        )
    except LoweringError as exc:
        raise ArchitectureCompileError(
            str(exc),
            fix="Extend the architecture source with the missing obligation, or compile a "
            "document that states executable work.",
        ) from exc
    if lowered.coverage.status != "PASS":
        raise ArchitectureCompileError(
            "semantic coverage did not converge after bounded repair",
            fix="Resolve the listed source units in the architecture document, or state them "
            "in the conventional MUST / MUST NOT / OUT OF SCOPE vocabulary so they can be "
            "read as obligations.",
            detail={
                "coverage": lowered.coverage.to_dict(),
                "unmapped_material_units": lowered.coverage.unmapped_material_units[:20],
            },
        )
    cache = (cache_root or default_cache_root()) / resolved_id
    source_path = cache / "CAMPAIGN_SOURCE.yaml"
    _refuse_foreign_cache(source_path, lowered.source, resolved_id)
    cache.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(source_path, _yaml_text(lowered.source))
    resolution_path = cache / "ARCHITECTURE_RESOLUTION.json"
    _write_text_atomic(
        resolution_path,
        json.dumps(lowered.source["intent_provenance"], indent=2, sort_keys=True) + "\n",
    )
    archived = cache / f"architecture-source{intent.path.suffix or '.md'}"
    _write_text_atomic(archived, intent.text)
    return {
        "schema": "l9.program-execution.architecture-compile-receipt.v1",
        "campaign_id": resolved_id,
        "target": intent.target,
        "source": {
            "path": str(intent.path),
            "sha256": intent.sha256,
            "archived": str(archived),
        },
        "campaign_source": str(source_path),
        "resolution": str(resolution_path),
        "extractor": extraction.extractor_id,
        "chunks": extraction.chunks,
        "repair_rounds": extraction.repair_rounds,
        "critic_rounds": extraction.critic_rounds,
        "coverage": lowered.coverage.to_dict(),
        "task_count": lowered.task_count,
        "prohibition_count": lowered.prohibition_count,
        "validation_count": lowered.validation_count,
        "rejected_items": len(extraction.rejected),
        "blocked_task_count": sum(
            1 for task in lowered.source["tasks"] if task["definition_status"] == "blocked"
        ),
    }


def _load(path: Path, *, target: str | None, forced: bool) -> ArchitectureIntent:
    try:
        return load_architecture_intent(path, target=target, forced=forced)
    except ArchitectureIntentError as exc:
        raise ArchitectureCompileError(
            str(exc),
            fix="Pass TARGET=<owner/repo> to `make campaign-architecture`, or add "
            "`schema: l9.program-execution.architecture-intent.v1` and `target:` frontmatter.",
        ) from exc


def _extract(
    intent: ArchitectureIntent,
    *,
    extractor: Any | None,
    extractor_name: str,
    repair_rounds: int,
    critic: bool,
    max_chunk_chars: int | None,
) -> ExtractionResult:
    try:
        engine = extractor or resolve_extractor(extractor_name)
    except ExtractorUnavailable as exc:
        raise ArchitectureCompileError(
            f"no semantic extraction capability is available: {exc}",
            fix="Install the Claude Code CLI, or set "
            "L9_ARCHITECTURE_EXTRACTOR=deterministic to use the lexical reader.",
        ) from exc
    try:
        return extract_semantics(
            intent,
            engine,
            repair_rounds=repair_rounds,
            critic=critic,
            max_chunk_chars=max_chunk_chars,
        )
    except ExtractorError as exc:
        raise ArchitectureCompileError(
            f"semantic extraction failed: {exc}",
            fix="Re-run the compile. If the extractor keeps failing, select another with "
            "L9_ARCHITECTURE_EXTRACTOR=.",
        ) from exc


def _refuse_unresolved_contradictions(
    intent: ArchitectureIntent, extraction: ExtractionResult
) -> None:
    """A contradiction the source itself cannot settle is a real impossibility.

    Not a BLOCKED task: a program whose own requirements disagree has no valid
    execution, so it must never be minted. Everything else — a model that
    contradicted itself, an ungrounded restatement — was already discarded by
    admission and repair before this point.
    """
    unresolved = extraction.unresolved_contradictions()
    if not unresolved:
        return
    lines = []
    by_id = {item.id: item for item in extraction.items}
    for entry in unresolved:
        left, right = by_id.get(entry.left_id), by_id.get(entry.right_id)
        lines.append(
            {
                "left": {
                    "id": entry.left_id,
                    "kind": getattr(left, "kind", ""),
                    "statement": getattr(left, "statement", ""),
                    "source_refs": list(getattr(left, "source_refs", ())),
                },
                "right": {
                    "id": entry.right_id,
                    "kind": getattr(right, "kind", ""),
                    "statement": getattr(right, "statement", ""),
                    "source_refs": list(getattr(right, "source_refs", ())),
                },
                "reason": entry.reason,
            }
        )
    raise ArchitectureCompileError(
        "the architecture source states contradictory obligations of equal authority; "
        "compilation cannot pick a winner without inventing authority",
        fix="Resolve the contradiction in the architecture document (state which obligation "
        "wins, or scope them so they do not overlap) and re-run.",
        detail={"contradictions": lines},
    )


def _yaml_text(value: Any) -> str:
    import yaml

    return yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=100)


def _dump_yaml(path: Path, value: Any) -> None:
    _write_text_atomic(path, _yaml_text(value))


def _write_text_atomic(path: Path, text: str) -> None:
    """Compiler cache entries are read by later stages: never leave a torn file."""
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    handle, staged = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
    finally:
        if os.path.exists(staged):
            os.unlink(staged)


def _source_sha256(source: dict[str, Any]) -> str:
    provenance = source.get("intent_provenance") or {}
    origin = provenance.get("source") if isinstance(provenance, dict) else None
    return str((origin or {}).get("sha256") or "") if isinstance(origin, dict) else ""


def _refuse_foreign_cache(source_path: Path, source: dict[str, Any], campaign_id: str) -> None:
    """Refuse to overwrite a cached campaign compiled from a DIFFERENT document.

    The campaign id is derived from the document title, so two different
    documents with one H1 resolved to one cache directory and the second
    silently replaced the first, stack proof included. Recompiling the same
    document (same source digest) stays idempotent.
    """
    if not source_path.is_file():
        return
    import yaml

    try:
        existing = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ArchitectureCompileError(
            f"cached campaign source for {campaign_id} is unreadable: {source_path}: {exc}"
        ) from exc
    previous = _source_sha256(existing) if isinstance(existing, dict) else ""
    current = _source_sha256(source)
    if previous and current and previous != current:
        raise ArchitectureCompileError(
            f"campaign id {campaign_id} is already compiled from a different source "
            f"(sha256 {previous[:12]} != {current[:12]}) at {source_path.parent}; "
            "pass --campaign-id for a distinct id or remove the stale cache deliberately"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="compile_architecture_intent", description=__doc__)
    parser.add_argument("--intent", required=True, type=Path)
    parser.add_argument("--target", default=None, help="owner/repo the architecture applies to")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--repo-root", type=Path, default=None, help="governance checkout")
    parser.add_argument(
        "--target-checkout", type=Path, default=None, help="local clone of the target repository"
    )
    parser.add_argument("--cache-root", type=Path, default=None)
    parser.add_argument("--extractor", default="", help="deterministic | claude-code")
    parser.add_argument("--repair-rounds", type=int, default=DEFAULT_REPAIR_ROUNDS)
    parser.add_argument("--no-critic", action="store_true")
    parser.add_argument("--max-chunk-chars", type=int, default=None)
    parser.add_argument("--owner", default=None)
    parser.add_argument(
        "--declared-only",
        action="store_true",
        help="require the document to declare the architecture-intent schema itself",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        receipt = compile_architecture_intent(
            args.intent,
            target=args.target,
            forced=not args.declared_only,
            repo_root=args.repo_root,
            target_checkout=args.target_checkout,
            campaign_id=args.campaign_id,
            cache_root=args.cache_root,
            extractor_name=args.extractor,
            repair_rounds=args.repair_rounds,
            critic=not args.no_critic,
            max_chunk_chars=args.max_chunk_chars,
            owner=args.owner,
        )
    except ArchitectureCompileError as exc:
        print(exc.render(), file=sys.stderr)
        return exc.exit_code
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
