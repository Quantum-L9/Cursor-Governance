#!/usr/bin/env python3
"""Fail-closed scan for stale references to retired/renamed Cursor rules."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "environment/generated/llm-rules",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "WIP",
}

# Historical stems retired or renamed by rules-corpus-cleanup-v1
DEFAULT_STALE = [
    "01-git-push-prohibition",
    "96-git-push-approval",
    "03-mcp-memory",
    "99-graphiti-temporal",
    "93-perplexity-research-protocol",
    "01-vps-rules",
    "05-recursive-execution-kernel",
    "87-cursor-subagent-orchestration",
    "87-l4-local-autonomy",
    "87-wire-workflow-guard",
    "88-bounded-session-autonomy",
    "88-perplexity-run-harness",
    "88-shared-worktree-isolation",
    "95-agent-pattern-activation",
    "96-env-no-hardcode",
    "96-output-discipline",
    "97-governance-ssot-paths",
    "97-graph-engine-architecture",
    "97-ide-profile-exceptions",
    "98-make-pr-remediation",
    "99-execute-as-instructed",
    "99-incident-report",
]

ALLOW_PATH_SUBSTR = (
    "reports/rules-cleanup-rename-map.yaml",
    "ops/scripts/audit_rule_references.py",
    "docs/rules-frontmatter-archive.yaml",
    "learning/failures/learned-lessons-corpus.md",
    "learning/failures/incidents/incident-report-corpus.md",
    "learning/patterns/anti-patterns.md",
    "ops/scripts/capture_rules_cleanup_preflight.py",
    "ops/scripts/_tmp_rules_cleanup_finish.py",
    "reports/rules-cleanup-rename-map.yaml",
)


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    if any(rel == a or rel.startswith(a.rstrip("/") + "/") for a in ALLOW_PATH_SUBSTR):
        return True
    parts = set(path.parts)
    if parts & SKIP_DIR_NAMES:
        return True
    if "environment/generated/llm-rules" in rel:
        return True
    if rel.startswith("rules/") and path.suffix == ".mdc":
        # Live rules may mention peers; still flag retired stems inside live bodies
        return False
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--freeze", type=Path, help="Optional JSON list of stale stems")
    args = parser.parse_args()
    root = args.root.resolve()

    stale = list(DEFAULT_STALE)
    if args.freeze and args.freeze.is_file():
        data = json.loads(args.freeze.read_text(encoding="utf-8"))
        if isinstance(data, list):
            stale = [str(x) for x in data]
        elif isinstance(data, dict) and "stale_stems" in data:
            stale = [str(x) for x in data["stale_stems"]]

    # Current stems are allowed
    current = {p.stem for p in (root / "rules").glob("*.mdc")}
    stale = [s for s in stale if s not in current]

    hits: list[str] = []
    patterns = {
        stem: re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(stem)}(?![A-Za-z0-9_-])") for stem in stale
    }

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {
            ".md",
            ".mdc",
            ".py",
            ".sh",
            ".yaml",
            ".yml",
            ".json",
            ".txt",
        }:
            continue
        if should_skip(path, root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        for stem, pat in patterns.items():
            if pat.search(text):
                hits.append(f"{rel}: stale reference to {stem}")

    if hits:
        for hit in hits:
            print(f"FAIL: {hit}", file=sys.stderr)
        print(f"RESULT: FAIL ({len(hits)} stale references)", file=sys.stderr)
        return 1
    print("RESULT: PASS - no stale rule stem references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
