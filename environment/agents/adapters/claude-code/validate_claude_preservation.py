#!/usr/bin/env python3
"""Claude Code preservation validator (repository-pure).

Encodes the Claude Code Preservation Contract's five verification clauses.
Claude Code sits deliberately OUTSIDE the Cursor virtualization boundary: the
Cursor plane may add a gateway, a registry schema, receipts and routing, and
none of that may move a skill's Claude-visible invocation tier, remove a skill
from the Claude projection, or write into the Claude adapter tree.

  V-CC-001  the projected Claude skill set and per-skill tier map equal the
            recorded baseline, except entries in ALLOWLIST (empty today)
  V-CC-002  this validator imports nothing under the Cursor adapter tree and
            reads no path under ~/.cursor/** — it runs with both absent
  V-CC-003  every live canonical skill under skills/ propagates to the Claude
            projection (registry record + settings override when explicit-only)
  V-CC-004  no canonical skill reachable in the baseline is unreachable now
  V-CC-005  no file in the Cursor adapter tree writes any path under
            .claude/** or environment/agents/adapters/claude-code/**

Reads only repository content: no network, no ~/.cursor, no Cursor import.
Exit 0 on PASS, 1 on any failure. ``--json`` prints the findings.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

SETTINGS_REL = Path(".claude/settings.json")
TEMPLATE_REL = Path("environment/agents/adapters/claude-code/settings.template.json")
CLAUDE_REGISTRY_REL = Path("environment/agents/adapters/claude-code/generated/skill-registry.json")
BASELINE_REL = Path("environment/agents/adapters/claude-code/claude_preservation_baseline.json")
CURSOR_ADAPTER_REL = Path("environment/agents/adapters/cursor")
CLAUDE_ADAPTER_REL = Path("environment/agents/adapters/claude-code")
CANONICAL_REL = Path("skills")

#: Skills whose Claude-visible tier is allowed to differ from the baseline.
#: Every entry needs a reason and an owning change set. A tier move belongs in
#: its own PR with its own ADR (contract CC-006); this list is not a shortcut
#: past that, it is the record that the separation happened.
ALLOWLIST: dict[str, str] = {}

#: Path prefixes the Cursor adapter tree may never write (V-CC-005).
CLAUDE_OWNED_PREFIXES = (".claude/", "environment/agents/adapters/claude-code")

#: Writes are matched syntactically, never as bare English fragments — "never
#: touches .claude/settings.json" in a README is documentation, not a write.
#: Only executable file types are scanned; prose may name a Claude path freely.
PY_WRITE_RE = re.compile(
    r"""
      \.(?:write_text|write_bytes|writelines|mkdir|makedirs|symlink_to
         |hardlink_to|unlink|touch|chmod|rename|replace)\s*\(
    | \b(?:os\.(?:replace|rename|remove|unlink|mkdir|makedirs|symlink|chmod|truncate)
         |shutil\.(?:copy|copy2|copyfile|copytree|move|rmtree))\s*\(
    | \bopen\s*\([^)]*["'][wax]
    """,
    re.VERBOSE,
)
SH_WRITE_VERB_RE = re.compile(
    r"(?:^|[;&|]|\$\(|\bthen\b|\bdo\b)\s*"
    r"(?:sudo\s+)?(?:cp|mv|rm|ln|install|tee|rsync|mkdir|touch|chmod|truncate|sed)\b"
)
#: A redirection writes what follows it; a markdown blockquote at line start
#: does not, so `>` must be preceded by something on the line.
SH_REDIRECT_RE = re.compile(r"\S\s*>>?\s*")

EXECUTABLE_SUFFIXES = {".py", ".sh", ".bash", ".zsh"}

#: Literals that would mean this validator reached into the Cursor plane.
CURSOR_STATE_LITERALS = ("~/.cursor", ".cursor/l9", "CURSOR_HOME", "cursor_discovery")


def line_writes_claude_path(line: str, suffix: str) -> bool:
    """True when this line both names a Claude-owned path and writes it."""
    hit = next((p for p in CLAUDE_OWNED_PREFIXES if p in line), None)
    if hit is None:
        return False
    if suffix == ".py":
        return bool(PY_WRITE_RE.search(line))
    if SH_WRITE_VERB_RE.search(line):
        return True
    # A redirection only writes what comes *after* it.
    match = SH_REDIRECT_RE.search(line)
    return bool(match) and line.find(hit) >= match.end() - 1


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def live_canonical_names(root: Path) -> list[str]:
    """Canonical corpus by filesystem truth — the same rule the generator uses."""
    skills = root / CANONICAL_REL
    if not skills.is_dir():
        return []
    return sorted(
        path.name
        for path in skills.iterdir()
        if path.is_dir() and not path.name.startswith("_") and (path / "SKILL.md").is_file()
    )


def projected_tier_map(root: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """The Claude-visible projection: registry invocation + settings override."""
    errors: list[str] = []
    overrides: dict[str, Any] = {}
    try:
        overrides = _read_json(root / SETTINGS_REL).get("skillOverrides", {}) or {}
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"claude settings unreadable: {exc}")

    records: list[dict[str, Any]] = []
    try:
        records = _read_json(root / CLAUDE_REGISTRY_REL).get("skills", []) or []
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"claude registry mirror unreadable: {exc}")

    tier_map: dict[str, dict[str, Any]] = {}
    for record in records:
        name = str(record.get("name", ""))
        if not name:
            errors.append("claude registry mirror has a record without a name")
            continue
        tier_map[name] = {
            "invocation": record.get("invocation"),
            "disable_model_invocation": bool(record.get("disable_model_invocation")),
            "settings_override": overrides.get(name),
        }
    return tier_map, errors


def check_cc001(root: Path, current: dict[str, dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """Projected skill set and tier map equal the recorded baseline."""
    errors: list[str] = []
    facts: dict[str, Any] = {}
    try:
        baseline = _read_json(root / BASELINE_REL)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"baseline fixture unreadable: {exc}"], facts

    if baseline.get("schema") != "l9.claude-preservation-baseline.v1":
        errors.append("baseline schema is not l9.claude-preservation-baseline.v1")
    base_map = baseline.get("tier_map", {}) or {}
    facts["baseline_commit"] = baseline.get("generated_from_commit")
    facts["baseline_skill_count"] = len(base_map)
    facts["projected_skill_count"] = len(current)

    dropped = sorted(set(base_map) - set(current) - set(ALLOWLIST))
    if dropped:
        errors.append(f"skills dropped from the Claude projection: {dropped}")
    added = sorted(set(current) - set(base_map) - set(ALLOWLIST))
    if added:
        facts["skills_added_since_baseline"] = added

    drifted: list[str] = []
    for name in sorted(set(base_map) & set(current)):
        if name in ALLOWLIST:
            continue
        if base_map[name] != current[name]:
            drifted.append(f"{name}: baseline={base_map[name]} projected={current[name]}")
    if drifted:
        errors.append(
            "Claude invocation tier changed without a separate change set: " + "; ".join(drifted)
        )
    facts["tier_drift_count"] = len(drifted)
    facts["allowlisted"] = sorted(ALLOWLIST)
    return errors, facts


def check_cc002(root: Path) -> tuple[list[str], dict[str, Any]]:
    """This validator is Cursor-independent: no Cursor import, no ~/.cursor read."""
    errors: list[str] = []
    source_path = Path(__file__).resolve()
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"validator source unreadable: {exc}"], {}

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:  # pragma: no cover - the file would not import
        return [f"validator source unparseable: {exc}"], {}

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    offending = sorted(name for name in imported if "cursor" in name.lower())
    if offending:
        errors.append(f"validator imports Cursor modules: {offending}")

    # The Cursor adapter path may be *named* — V-CC-005 scans that tree — but no
    # ~/.cursor runtime state may be read. Compare string constants via the AST
    # so the deny-list's own declaration is not mistaken for a use of it.
    exempt: set[int] = set()
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if any(isinstance(t, ast.Name) and t.id == "CURSOR_STATE_LITERALS" for t in targets):
            exempt.update(id(child) for child in ast.walk(node))
    # Docstrings describe the contract; they are prose, not a path read.
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            body = getattr(node, "body", [])
            first = body[0] if body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                exempt.add(id(first.value))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in exempt:
            continue
        hit = next((lit for lit in CURSOR_STATE_LITERALS if lit in node.value), None)
        if hit:
            errors.append(
                f"validator reads Cursor runtime state {hit!r} at line {getattr(node, 'lineno', 0)}"
            )

    facts = {
        "validator_imports": sorted(set(imported)),
        "cursor_adapter_present": (root / CURSOR_ADAPTER_REL).is_dir(),
    }
    return errors, facts


def check_cc003(root: Path, current: dict[str, dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """Every live canonical skill propagates into the Claude projection."""
    errors: list[str] = []
    canonical = live_canonical_names(root)
    missing = sorted(set(canonical) - set(current))
    if missing:
        errors.append(f"canonical skills absent from the Claude projection: {missing}")
    extra = sorted(set(current) - set(canonical))
    if extra:
        errors.append(f"Claude projection names skills with no canonical folder: {extra}")

    # An explicit-only skill must carry its settings override, or Claude Code
    # would model-invoke a skill the corpus marks user-invocable-only.
    unguarded = sorted(
        name
        for name, tier in current.items()
        if tier.get("invocation") == "explicit_only"
        and tier.get("settings_override") != "user-invocable-only"
    )
    if unguarded:
        errors.append(f"explicit-only skills without a Claude settings override: {unguarded}")

    facts = {"canonical_skill_count": len(canonical), "propagated": len(canonical) - len(missing)}
    return errors, facts


def check_cc004(root: Path, current: dict[str, dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    """No baseline-reachable skill became unreachable."""
    errors: list[str] = []
    try:
        baseline = _read_json(root / BASELINE_REL)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"baseline fixture unreadable: {exc}"], {}

    try:
        records = {
            str(item.get("name")): item
            for item in _read_json(root / CLAUDE_REGISTRY_REL).get("skills", []) or []
        }
    except (OSError, json.JSONDecodeError) as exc:
        return [f"claude registry mirror unreadable: {exc}"], {}

    unreachable: list[str] = []
    for name in baseline.get("skill_names", []) or []:
        if name in ALLOWLIST:
            continue
        record = records.get(name)
        if record is None:
            unreachable.append(f"{name}: absent from the Claude registry")
            continue
        skill_md = record.get("skill_md") or f"skills/{name}/SKILL.md"
        if not (root / skill_md).is_file():
            unreachable.append(f"{name}: {skill_md} does not exist")
        elif not bool(record.get("user_invocable", True)):
            unreachable.append(f"{name}: user_invocable is false")
    if unreachable:
        errors.append("baseline skills no longer reachable: " + "; ".join(unreachable))

    facts = {
        "baseline_reachable_checked": len(baseline.get("skill_names", []) or []) - len(ALLOWLIST)
    }
    return errors, facts


def check_cc005(root: Path) -> tuple[list[str], dict[str, Any]]:
    """No file in the Cursor adapter tree writes a Claude-owned path."""
    errors: list[str] = []
    cursor_tree = root / CURSOR_ADAPTER_REL
    scanned = 0
    if not cursor_tree.is_dir():
        # Claude Code must validate with Cursor entirely absent (CC-007). An
        # absent Cursor tree cannot write anything, so this clause is vacuous.
        return errors, {"cursor_files_scanned": 0, "cursor_tree_present": False}

    for path in sorted(cursor_tree.rglob("*")):
        if not path.is_file() or path.suffix not in EXECUTABLE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scanned += 1
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(text.splitlines(), 1):
            if line_writes_claude_path(line, path.suffix):
                where = f"{rel}:{lineno}"
                errors.append(
                    f"Cursor adapter writes a Claude-owned path: {where}: {line.strip()[:120]}"
                )

    return errors, {"cursor_files_scanned": scanned, "cursor_tree_present": True}


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    facts: dict[str, Any] = {}
    checks: dict[str, list[str]] = {}

    current, projection_errors = projected_tier_map(root)
    if projection_errors:
        checks["V-CC-000"] = projection_errors

    for clause, (errs, clause_facts) in {
        "V-CC-001": check_cc001(root, current),
        "V-CC-002": check_cc002(root),
        "V-CC-003": check_cc003(root, current),
        "V-CC-004": check_cc004(root, current),
        "V-CC-005": check_cc005(root),
    }.items():
        checks[clause] = errs
        facts.update(clause_facts)

    errors = [f"{clause}: {msg}" for clause, msgs in sorted(checks.items()) for msg in msgs]
    return {
        "ok": not errors,
        "errors": errors,
        "checks": {
            clause: ("PASS" if not msgs else "FAIL") for clause, msgs in sorted(checks.items())
        },
        "facts": facts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = validate(args.root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        facts = result["facts"]
        print(
            "claude preservation: baseline="
            f"{facts.get('baseline_skill_count')} projected={facts.get('projected_skill_count')} "
            f"canonical={facts.get('canonical_skill_count')} drift={facts.get('tier_drift_count')} "
            f"cursor_tree={'present' if facts.get('cursor_tree_present') else 'absent'}"
        )
        for clause, status in result["checks"].items():
            print(f"  {clause}: {status}")
        for err in result["errors"]:
            print(f"  - {err}")
        print("PASS" if result["ok"] else f"FAIL ({len(result['errors'])})")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
