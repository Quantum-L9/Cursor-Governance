#!/usr/bin/env python3
"""Compile a long-form architecture document into campaign-source.v2.

Live entrypoint for the `architecture -> campaign_source -> blueprint -> PEC`
route. Everything here runs BEFORE any campaign side effect: artifacts land
only under the primed compiler cache (`$L9_ROOT/primed/architecture/<id>/`).
If compilation fails, no worktree is created, no PEC workspace is bootstrapped,
no task is claimed, and no repository is mutated.

The operator hands over unchanged assistant/audit Markdown (Mode A, forced via
`make campaign-architecture`) or a self-describing document with
`schema: l9.program-execution.architecture-intent.v1` frontmatter (Mode B).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

PE_ROOT = Path(__file__).resolve().parents[1]
if str(PE_ROOT) not in sys.path:
    sys.path.insert(0, str(PE_ROOT))

from compiler.architecture_extractor import (  # noqa: E402
    ArchitectureExtractor,
    ExtractorError,
    run_extraction,
    select_extractor,
)
from compiler.architecture_intent import (  # noqa: E402
    ArchitectureIntentError,
    load_source,
    parse_frontmatter,
)
from compiler.architecture_to_campaign import (  # noqa: E402
    LoweringError,
    lower_to_campaign_source,
)

RESOLUTION_SCHEMA = "l9.program-execution.architecture-resolution.v1"


class ArchitectureCompileError(RuntimeError):
    """Terminal architecture compilation failure. Nothing has executed."""

    def __init__(self, message: str, *, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": "PE_ARCHITECTURE_COMPILE_FAILED",
            "reason": str(self),
            "nothing_executed": True,
            "workspace_created": False,
            "tasks_started": 0,
        }


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def existing_campaign_ids(host_root: Path | None, l9_root: Path | None = None) -> set[str]:
    """Campaign ids that already exist, derived from real state only.

    These sources answer "does this id already exist?" — collision detection —
    never "is this new id permitted to exist?". There is no preregistration
    list on this path.
    """
    ids: set[str] = set()
    if host_root is not None:
        campaigns = Path(host_root) / "environment/program-execution/campaigns"
        if campaigns.is_dir():
            for path in campaigns.iterdir():
                if path.is_dir() and (path / "CAMPAIGN_SOURCE.yaml").is_file():
                    ids.add(path.name)
            status = campaigns / "CAMPAIGN_STATUS.yaml"
            if status.is_file() and yaml is not None:
                try:
                    raw = yaml.safe_load(status.read_text(encoding="utf-8")) or {}
                except Exception:
                    raw = {}
                for item in raw.get("campaigns") or []:
                    if isinstance(item, dict) and item.get("id"):
                        ids.add(str(item["id"]))
            completed = campaigns / "COMPLETED"
            if completed.is_dir():
                for path in completed.iterdir():
                    if path.is_dir() and path.name not in {"stale"}:
                        ids.add(path.name)
    if l9_root is not None:
        programs = Path(l9_root) / "programs"
        if programs.is_dir():
            for path in programs.iterdir():
                if path.is_dir():
                    ids.add(path.name)
    return ids


def _same_source_ids(primed_root: Path, source_sha: str) -> set[str]:
    """Ids whose primed resolution already binds this exact source digest.

    Re-running the same architecture source must reuse its campaign id rather
    than suffixing a new one; a different source keeps collision-safe suffixes.
    """
    matches: set[str] = set()
    architecture_root = primed_root / "architecture"
    if not architecture_root.is_dir():
        return matches
    for path in architecture_root.iterdir():
        receipt = path / "architecture-resolution.json"
        if not receipt.is_file():
            continue
        try:
            recorded = json.loads(receipt.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if str((recorded.get("source") or {}).get("sha256") or "") == source_sha:
            matches.add(path.name)
    return matches


def compile_architecture(
    source_path: Path,
    *,
    target: str = "",
    owner: str = "Igor Beylin",
    primed_dir: Path,
    existing_ids: set[str] | None = None,
    repo_path: Path | None = None,
    extractor: ArchitectureExtractor | None = None,
    max_repair_rounds: int = 2,
    stamp: str | None = None,
) -> dict[str, Any]:
    """Full pre-side-effect pipeline: segment → extract → audit → lower → emit.

    Returns a result whose ``campaign_source`` is the generated
    campaign-source.v2 document and whose ``campaign_source_path`` is its
    primed-cache location. Raises :class:`ArchitectureCompileError` on any
    unrecoverable condition — before campaign side effects, never as a
    Blueprint full of blocked tasks.
    """
    if yaml is None:
        raise ArchitectureCompileError("PyYAML required for architecture compilation")
    now = stamp or utc_now()
    try:
        document = load_source(Path(source_path))
    except ArchitectureIntentError as exc:
        raise ArchitectureCompileError(str(exc)) from exc
    frontmatter = parse_frontmatter(document.text) or {}
    effective_target = str(frontmatter.get("target") or target or "").strip()
    if not effective_target or "/" not in effective_target:
        raise ArchitectureCompileError(
            "target repository cannot be identified: pass TARGET=owner/repo to "
            "campaign-architecture or declare `target:` in the frontmatter"
        )
    title = str(frontmatter.get("title") or "").strip()
    chosen_extractor = extractor or select_extractor()
    try:
        outcome = run_extraction(
            chosen_extractor,
            document,
            target=effective_target,
            title=title,
            max_repair_rounds=max_repair_rounds,
        )
    except ExtractorError as exc:
        raise ArchitectureCompileError(f"semantic extraction failed: {exc}") from exc
    if not outcome.coverage.passed:
        details = "; ".join(str(problem.get("detail")) for problem in outcome.coverage.problems[:6])
        raise ArchitectureCompileError(
            "semantic coverage cannot converge after bounded repair "
            f"({outcome.repair_rounds} rounds): {details}"
        )

    primed_root = Path(primed_dir)
    known = set(existing_ids or set()) - _same_source_ids(primed_root, document.sha256)
    try:
        lowered = lower_to_campaign_source(
            document,
            outcome,
            target_repo=effective_target,
            owner=owner,
            existing_ids=known,
            repo_path=repo_path,
            stamp=now,
        )
    except LoweringError as exc:
        raise ArchitectureCompileError(str(exc)) from exc

    out_dir = primed_root / "architecture" / lowered.campaign_id
    out_dir.mkdir(parents=True, exist_ok=True)
    campaign_source_path = out_dir / "CAMPAIGN_SOURCE.yaml"
    campaign_source_path.write_text(
        yaml.safe_dump(lowered.source, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )
    resolution = {
        "schema": RESOLUTION_SCHEMA,
        "campaign_id": lowered.campaign_id,
        "target": effective_target,
        "compiled_at": now,
        "source": {
            "sha256": document.sha256,
            "media_type": document.media_type,
            "path": str(source_path),
        },
        "source_units": [unit.to_dict() for unit in document.units],
        "semantic_items": [item.to_dict() for item in outcome.items],
        "rejected_items": outcome.rejected,
        "coverage": lowered.coverage.to_dict(),
        "extractor": {
            "identity": outcome.extractor_identity,
            "protocol": "l9.program-execution.architecture-extractor-request.v1",
        },
        "repair_rounds": outcome.repair_rounds,
        "chunk_count": outcome.chunk_count,
        "critic_ran": outcome.critic_ran,
        "repository_evidence": lowered.repository_evidence,
    }
    resolution_path = out_dir / "architecture-resolution.json"
    resolution_path.write_text(json.dumps(resolution, indent=2) + "\n", encoding="utf-8")

    tasks = lowered.source.get("tasks") or []
    return {
        "campaign_id": lowered.campaign_id,
        "target": effective_target,
        "campaign_source": lowered.source,
        "campaign_source_path": str(campaign_source_path),
        "resolution_path": str(resolution_path),
        "coverage": lowered.source["intent_provenance"]["coverage"],
        "task_count": len(tasks),
        "ready_task_count": sum(1 for task in tasks if task.get("definition_status") == "ready"),
        "blocked_task_count": sum(
            1 for task in tasks if task.get("definition_status") == "blocked"
        ),
        "prohibition_count": len(lowered.source.get("prohibited_paths") or []),
        "validation_count": sum(len(task.get("validation") or []) for task in tasks),
        "repair_rounds": outcome.repair_rounds,
        "chunk_count": outcome.chunk_count,
        "extractor": outcome.extractor_identity,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="compile_architecture_intent", description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", default="", help="owner/repo the architecture applies to")
    parser.add_argument("--owner", default="Igor Beylin")
    parser.add_argument(
        "--primed-dir",
        type=Path,
        default=Path.home() / ".l9/primed",
        help="compiler cache root; artifacts land under <primed>/architecture/<id>/",
    )
    parser.add_argument(
        "--host-root",
        type=Path,
        default=None,
        help="governance checkout used only for campaign-id collision detection",
    )
    parser.add_argument("--repo-path", type=Path, default=None)
    parser.add_argument("--extractor", default=None)
    parser.add_argument("--max-repair-rounds", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        chosen = select_extractor(args.extractor) if args.extractor else None
        result = compile_architecture(
            args.source.resolve(),
            target=args.target,
            owner=args.owner,
            primed_dir=args.primed_dir,
            existing_ids=existing_campaign_ids(args.host_root),
            repo_path=args.repo_path,
            extractor=chosen,
            max_repair_rounds=args.max_repair_rounds,
        )
    except (ArchitectureCompileError, ExtractorError) as exc:
        payload = (
            exc.to_dict()
            if isinstance(exc, ArchitectureCompileError)
            else ArchitectureCompileError(str(exc)).to_dict()
        )
        print(json.dumps(payload, indent=2) if args.json else f"FAIL: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 2)
    summary = {key: value for key, value in result.items() if key != "campaign_source"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
