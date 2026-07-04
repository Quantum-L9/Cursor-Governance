#!/usr/bin/env python3
"""Transform learning/ flat files into Graphiti-ingestible episode JSON.

Reads the existing learning corpus (repeated-mistakes.md, audit_log.jsonl,
violations.jsonl, formal_lessons_pending.json, quick-fixes.md, solutions/*.md)
and produces structured episode files ready for batch ingestion via graphiti_sink.

Output: learning/graphiti-episodes/*.json

Usage:
    python3 ops/scripts/transform_learning_to_episodes.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LEARNING = REPO_ROOT / "learning"
EPISODES_DIR = LEARNING / "graphiti-episodes"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _episode(body: str, source: str, group_ids: list[str],
             semantic_score: float = 0.8, trust_level: str = "L2") -> dict:
    return {
        "body": body,
        "source_agent_id": "learning-corpus-transformer",
        "session_id": f"batch-transform-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "group_ids": group_ids,
        "semantic_score": semantic_score,
        "trust_level": trust_level,
        "source_file": source,
        "transformed_at": _now_iso(),
    }


def transform_repeated_mistakes() -> list[dict]:
    """Parse repeated-mistakes.md into individual lesson episodes."""
    path = LEARNING / "failures" / "repeated-mistakes.md"
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    episodes = []

    # Split by lesson headers (## Lesson NN or ### pattern)
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section or len(section) < 50:
            continue
        # Extract lesson ID if present
        match = re.match(r"## (Lesson[- ]?\d+.*?)$", section, re.MULTILINE)
        lesson_id = match.group(1) if match else "unknown"
        episodes.append(_episode(
            body=section[:2000],  # Cap at 2000 chars per episode
            source="learning/failures/repeated-mistakes.md",
            group_ids=["corpus:repeated-mistakes", f"lesson:{lesson_id}"],
            semantic_score=0.9,
        ))
    return episodes


def transform_violations() -> list[dict]:
    """Parse violations.jsonl into episodes."""
    path = LEARNING / "failures" / "violations.jsonl"
    if not path.exists():
        return []

    episodes = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        try:
            v = json.loads(line)
        except json.JSONDecodeError:
            continue
        body = (
            f"Violation: {v.get('lesson_id', 'unknown')}\n"
            f"Severity: {v.get('severity', 'unknown')}\n"
            f"Description: {v.get('description', '')}\n"
            f"Source: {v.get('source', '')}\n"
            f"Context: {v.get('context', '')}"
        )
        episodes.append(_episode(
            body=body,
            source="learning/failures/violations.jsonl",
            group_ids=["corpus:violations", f"lesson:{v.get('lesson_id', 'unknown')}"],
            semantic_score=0.85,
        ))
    return episodes


def transform_audit_log() -> list[dict]:
    """Parse audit_log.jsonl into episodes."""
    path = LEARNING / "failures" / "audit_log.jsonl"
    if not path.exists():
        return []

    episodes = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        body = (
            f"Audit: {entry.get('lesson_id', 'unknown')}\n"
            f"Quality Score: {entry.get('quality_score', 'N/A')}\n"
            f"Mistake: {entry.get('lesson_content', {}).get('mistake', '')}\n"
            f"Impact: {entry.get('lesson_content', {}).get('impact', '')}\n"
            f"Prevention: {entry.get('lesson_content', {}).get('prevention', '')}"
        )
        episodes.append(_episode(
            body=body,
            source="learning/failures/audit_log.jsonl",
            group_ids=["corpus:audit-log", f"lesson:{entry.get('lesson_id', 'unknown')}"],
            semantic_score=float(entry.get("quality_score", 0.7)),
        ))
    return episodes


def transform_quick_fixes() -> list[dict]:
    """Parse quick-fixes.md into episodes."""
    path = LEARNING / "patterns" / "quick-fixes.md"
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8")
    episodes = []

    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    for section in sections:
        section = section.strip()
        if not section or len(section) < 30:
            continue
        match = re.match(r"## (.+?)$", section, re.MULTILINE)
        fix_name = match.group(1) if match else "unknown-fix"
        episodes.append(_episode(
            body=section[:2000],
            source="learning/patterns/quick-fixes.md",
            group_ids=["corpus:quick-fixes", f"pattern:{fix_name}"],
            semantic_score=0.8,
        ))
    return episodes


def transform_solutions() -> list[dict]:
    """Parse solutions/*.md into episodes."""
    solutions_dir = LEARNING / "solutions"
    if not solutions_dir.exists():
        return []

    episodes = []
    for md_file in solutions_dir.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        # Strip YAML header if present
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                content = content[end + 3:].strip()

        if len(content) < 30:
            continue

        episodes.append(_episode(
            body=content[:2000],
            source=f"learning/solutions/{md_file.name}",
            group_ids=["corpus:solutions", f"solution:{md_file.stem}"],
            semantic_score=0.85,
        ))
    return episodes


def main() -> None:
    EPISODES_DIR.mkdir(parents=True, exist_ok=True)

    all_episodes: dict[str, list[dict]] = {
        "repeated-mistakes": transform_repeated_mistakes(),
        "violations": transform_violations(),
        "audit-log": transform_audit_log(),
        "quick-fixes": transform_quick_fixes(),
        "solutions": transform_solutions(),
    }

    total = 0
    for name, episodes in all_episodes.items():
        if not episodes:
            continue
        out_path = EPISODES_DIR / f"{name}.episodes.json"
        out_path.write_text(json.dumps(episodes, indent=2), encoding="utf-8")
        total += len(episodes)
        print(f"  [{name}] {len(episodes)} episodes -> {out_path.name}")

    # Write manifest
    manifest = {
        "generated_at": _now_iso(),
        "total_episodes": total,
        "sources": {k: len(v) for k, v in all_episodes.items()},
        "ingestion_target": "graphiti_sink.emit_session()",
        "batch_command": "python3 -m l9_ops_mcp.cli batch-ingest learning/graphiti-episodes/",
    }
    manifest_path = EPISODES_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nTotal: {total} episodes ready for Graphiti ingestion.")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
