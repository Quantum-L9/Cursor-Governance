#!/usr/bin/env python3
"""Emit compiled packets from already-harvested invariants.

Harvest owner is skills/l9-intelligence-harvest (bind/inventory/qualify).
This script only extracts success-property rows and writes destination
packets. It does not call l9-harvest-pipeline.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from audit_plans import parse_frontmatter

GOLD_NUGGET = "kernels/Gold Nugget Extractor 🚀.md"
CODE_FENCE_RE = re.compile(r"```")
SP_ROW_RE = re.compile(r"(?m)^\|\s*(SP-\d+)\s*\|\s*([^|]+)\|")
TEMPLATE_PROPS = frozenset(
    {
        "replace",
        "property",
        "baseline still matches locked sha at start",
        "declared behavior/structure holds after mutation",
        "quality gate / pr gate pass on changed files",
    }
)
CONCERN_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^(pe_|make-program-execution)"), "pe-loop"),
    (re.compile(r"^(l4_publish|in-flight_pr|publish_)"), "publish"),
    (re.compile(r"^(toolchain_|core-identical)"), "toolchain"),
    (re.compile(r"^worktree_"), "isolation"),
    (re.compile(r"^claude_code_"), "session-contract"),
    (re.compile(r"^(ra_|root_docs|plan_template)"), "docs"),
    (re.compile(r"^infisical_"), "secrets"),
    (re.compile(r"^memory_outbox"), "memory"),
]


def concern_for(name: str) -> str:
    for pattern, concern in CONCERN_RULES:
        if pattern.search(name):
            return concern
    return "uncategorized"


def _clean_prop(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"`+", "", text)
    return " ".join(text.split())


def extract_invariants(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(text)
    invariants: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in SP_ROW_RE.finditer(body):
        prop = _clean_prop(match.group(2))
        if not prop or prop.lower() in TEMPLATE_PROPS:
            continue
        key = prop.lower()
        if key in seen:
            continue
        seen.add(key)
        invariants.append(
            {
                "id": match.group(1),
                "text": prop,
                "source": path.name,
            }
        )
    overview = str(fm.get("overview") or "").strip()
    if overview and not CODE_FENCE_RE.search(overview):
        invariants.append(
            {
                "id": "overview",
                "text": overview[:400],
                "source": path.name,
            }
        )
    return {
        "path": str(path),
        "name": str(fm.get("name") or path.stem),
        "concern": concern_for(path.name),
        "kind": str(fm.get("kind") or ""),
        "execute_via": str(fm.get("execute_via") or ""),
        "invariants": invariants,
    }


def compile_by_concern(extractions: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for item in extractions:
        concern = str(item.get("concern") or "uncategorized")
        for inv in item.get("invariants") or []:
            text = str(inv.get("text") or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen[concern]:
                continue
            seen[concern].add(key)
            grouped[concern].append(inv)
    return dict(grouped)


def reject_implementation(payload: dict[str, Any]) -> None:
    blob = json.dumps(payload, sort_keys=True)
    if CODE_FENCE_RE.search(blob):
        raise SystemExit("harvest receipt contains a code fence; refuse implementation payload")


def emit_compiled_plan(
    *,
    concern: str,
    invariants: list[dict[str, str]],
    donors: list[str],
    dest: Path,
) -> None:
    lines = [
        "---",
        f"name: Compiled {concern} invariants",
        "compiled: true",
        'overview: "Invariants harvested from mixed donors. Execute via /gmp."',
        "todos:",
    ]
    for idx, inv in enumerate(invariants, start=1):
        text = str(inv.get("text") or "").replace('"', "'")
        lines.append(f"  - id: inv-{idx:02d}")
        lines.append(f'    content: "{text[:300]}"')
        lines.append("    status: pending")
    lines.extend(
        [
            "isProject: false",
            "kind: simple",
            "execute_via: gmp",
            "---",
            "",
            f"# PLAN: Compiled {concern} invariants",
            "",
            "Harvested without implementation. Gold Nugget kernel cited by path.",
            "",
            "## Donors",
            "",
        ]
    )
    for donor in donors:
        lines.append(f"- `{donor}`")
    lines.extend(
        [
            "",
            "## Execute via GMP",
            "",
            "Run `/gmp` on this packet. Do not run `make campaign`.",
            "Do not admit a Program Lock. Donors stay on the shelf until they",
            "carry `compiled_into`; this file does not whole-file supersede them.",
            "",
        ]
    )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--emit-plan", default=None, type=Path)
    parser.add_argument("--concern", default=None)
    args = parser.parse_args(argv)

    extractions = [extract_invariants(path) for path in args.plans]
    grouped = compile_by_concern(extractions)
    if args.concern:
        grouped = {args.concern: grouped.get(args.concern, [])}
    payload = {
        "kernel": GOLD_NUGGET,
        "implementation": False,
        "donors": [path.name for path in args.plans],
        "concerns": grouped,
    }
    reject_implementation(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.emit_plan:
        concern = args.concern or next(iter(grouped), "compiled")
        emit_compiled_plan(
            concern=concern,
            invariants=grouped.get(concern, []),
            donors=[path.name for path in args.plans],
            dest=args.emit_plan,
        )
    print(f"wrote {args.out} concerns={list(grouped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
