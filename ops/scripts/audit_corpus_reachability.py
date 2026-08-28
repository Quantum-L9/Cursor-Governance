#!/usr/bin/env python3
"""Advisory corpus reachability audit (harvest C5).

Classifies tracked governance artifacts as reachable or unreachable from a
*declared* entrypoint set. Name-loaded skills/commands/rules count as
reachable. Unreachable is evidence, never delete authorization. Always exit 0.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ENTRYPOINTS = (
    "skills/AUTONOMY_MANIFEST.yaml",
    "commands/COMMANDS_MANIFEST.yaml",
    "rules/RULES-MANIFEST.yaml",
    "ops/generated/skill-registry.json",
    ".pre-commit-config.yaml",
    "Makefile",
    "ops/hooks/hooks.json.template",
    "environment/agents/adapters/claude-code/plugins.desired.json",
    "environment/agents/adapters/claude-code/settings.template.json",
)

POPULATION_PREFIXES = (
    "skills/",
    "commands/",
    "rules/",
    "ops/scripts/",
    "ops/hooks/",
    "environment/agents/",
    "workflows/",
)

SKIP_PARTS = {
    "_archived",
    "WIP",
    "__pycache__",
    "generated",
    ".git",
    "node_modules",
}

# Basename-only hits would mark every SKILL.md reachable because manifests
# mention the filename. Require a full path, or a non-generic basename token.
GENERIC_BASENAMES = {
    "skill.md",
    "readme.md",
    "__init__.py",
    "hooks.json",
    "config.yaml",
    "config.yml",
    "settings.json",
    "makefile",
    "index.md",
    "plugin.json",
}

IMPORT_RE = re.compile(
    r"^(?:from|import)\s+([A-Za-z0-9_.]+)",
    re.MULTILINE,
)


def _posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _skip(rel: str) -> bool:
    parts = set(rel.split("/"))
    return bool(parts & SKIP_PARTS)


def list_population(root: Path) -> list[str]:
    rows: list[str] = []
    git_dir = root / ".git"
    if git_dir.exists():
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=False,
            capture_output=True,
        )
        if proc.returncode == 0:
            names = [n.decode("utf-8") for n in proc.stdout.split(b"\0") if n]
            for rel in names:
                if any(rel.startswith(prefix) for prefix in POPULATION_PREFIXES) and not _skip(rel):
                    rows.append(rel)
            return sorted(rows)
    for prefix in POPULATION_PREFIXES:
        base = root / prefix.rstrip("/")
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = _posix(path, root)
            if _skip(rel):
                continue
            rows.append(rel)
    return sorted(rows)


def _read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def registered_names(root: Path) -> dict[str, set[str]]:
    """Names that load by identity, not import."""
    names: dict[str, set[str]] = {
        "skill": set(),
        "command": set(),
        "rule": set(),
    }
    autonomy = _read(root, "skills/AUTONOMY_MANIFEST.yaml")
    for match in re.finditer(r"^\s+- skill:\s+(\S+)", autonomy, re.MULTILINE):
        names["skill"].add(match.group(1).strip().strip("\"'"))
    commands = _read(root, "commands/COMMANDS_MANIFEST.yaml")
    for match in re.finditer(r"^\s+file:\s+(\S+)", commands, re.MULTILINE):
        names["command"].add(match.group(1).strip().strip("\"'"))
    for match in re.finditer(r"^\s+slash:\s+(\S+)", commands, re.MULTILINE):
        names["command"].add(match.group(1).strip().lstrip("/"))
    rules = _read(root, "rules/RULES-MANIFEST.yaml")
    for match in re.finditer(r"^\s+file:\s+(\S+)", rules, re.MULTILINE):
        names["rule"].add(match.group(1).strip().strip("\"'"))
    registry = _read(root, "ops/generated/skill-registry.json")
    for match in re.finditer(r'"l9-[a-z0-9-]+"', registry):
        names["skill"].add(match.group(0).strip('"'))
    return names


def name_reachable(rel: str, names: dict[str, set[str]]) -> bool:
    parts = rel.split("/")
    if rel.startswith("skills/") and len(parts) >= 2:
        if parts[1] in names["skill"]:
            return True
    if rel.startswith("commands/") and rel in names["command"]:
        return True
    if rel.startswith("commands/") and Path(rel).stem in names["command"]:
        return True
    if rel.startswith("rules/") and len(parts) >= 2:
        if parts[-1] in names["rule"] or rel in names["rule"]:
            return True
    return False


def entrypoint_hits(root: Path, population: list[str]) -> set[str]:
    blobs = []
    for rel in ENTRYPOINTS:
        blobs.append(_read(root, rel))
    joined = "\n".join(blobs)
    hits: set[str] = set()
    for rel in ENTRYPOINTS:
        if rel in population:
            hits.add(rel)
    for rel in population:
        if rel in joined:
            hits.add(rel)
            continue
        name = Path(rel).name
        if name.lower() in GENERIC_BASENAMES:
            continue
        pattern = r'(?:^|[\s"\'`/=])' + re.escape(name) + r'(?:$|[\s"\'`.])'
        if re.search(pattern, joined):
            hits.add(rel)
    return hits


def import_one_hop(root: Path, seeds: set[str], population: list[str]) -> set[str]:
    """Mark population files imported by already-reachable Python modules."""
    by_module: dict[str, str] = {}
    for rel in population:
        if not rel.endswith(".py"):
            continue
        stem = Path(rel).stem
        by_module[stem] = rel
        dotted = rel[:-3].replace("/", ".")
        by_module[dotted] = rel
    extra: set[str] = set()
    pop_set = set(population)
    for rel in list(seeds):
        if not rel.endswith(".py"):
            continue
        text = _read(root, rel)
        if not text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            for match in IMPORT_RE.finditer(text):
                name = match.group(1).split(".")[-1]
                target = by_module.get(name)
                if target and target in pop_set:
                    extra.add(target)
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = by_module.get(alias.name) or by_module.get(alias.name.split(".")[-1])
                    if target and target in pop_set:
                        extra.add(target)
            elif isinstance(node, ast.ImportFrom) and node.module:
                target = by_module.get(node.module) or by_module.get(node.module.split(".")[-1])
                if target and target in pop_set:
                    extra.add(target)
    return extra


def category_of(rel: str) -> str:
    return rel.split("/", 1)[0]


def audit(root: Path) -> dict:
    population = list_population(root)
    names = registered_names(root)
    reachable: set[str] = set()
    for rel in population:
        if name_reachable(rel, names):
            reachable.add(rel)
    reachable.update(entrypoint_hits(root, population))
    reachable.update(import_one_hop(root, reachable, population))
    unreachable = [rel for rel in population if rel not in reachable]
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "reachable": 0})
    for rel in population:
        cat = category_of(rel)
        by_cat[cat]["total"] += 1
        if rel in reachable:
            by_cat[cat]["reachable"] += 1
    total = len(population)
    reached = len(reachable)
    ratio = round((reached / total * 100), 1) if total else 100.0
    return {
        "schema": "l9.corpus-reachability/v1",
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "advisory": True,
        "delete_authorization": False,
        "entrypoints": list(ENTRYPOINTS),
        "population_prefixes": list(POPULATION_PREFIXES),
        "summary": {
            "total": total,
            "reachable": reached,
            "unreachable": len(unreachable),
            "utilization_pct": ratio,
            "by_category": dict(by_cat),
        },
        "unreachable": unreachable,
        "note": (
            "Unreachable is leftover evidence, not authorization to delete. "
            "Reachability is defined only by the declared entrypoint set."
        ),
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Corpus reachability (advisory)",
        "",
        f"Utilization: {summary['utilization_pct']}% "
        f"({summary['reachable']}/{summary['total']} reachable). "
        "This report does not authorize deletion.",
        "",
        "## Entrypoint set",
    ]
    for item in report["entrypoints"]:
        lines.append(f"- `{item}`")
    lines += ["", "## Unreachable"]
    unreachable = report["unreachable"]
    if not unreachable:
        lines.append("_None._")
    else:
        for rel in unreachable[:200]:
            lines.append(f"- `{rel}`")
        extra = len(unreachable) - 200
        if extra > 0:
            lines.append(f"- … and {extra} more")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="JSON report path (default: <root>/reports/corpus-reachability.json)",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Markdown report path (default: <root>/reports/corpus-reachability.md)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = audit(root)
    json_out = args.json_out or (root / "reports" / "corpus-reachability.json")
    md_out = args.md_out or (root / "reports" / "corpus-reachability.md")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    print(
        f"OK: corpus reachability {report['summary']['utilization_pct']}% "
        f"({report['summary']['reachable']}/{report['summary']['total']}) "
        f"advisory={report['advisory']} delete_authorization={report['delete_authorization']}"
    )
    print(f"wrote {json_out}")
    print(f"wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
