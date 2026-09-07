#!/usr/bin/env python3
"""Snapshot the Claude Code skill-projection surface from repository state.

The snapshot is the machine-readable form of "what Claude Code sees": which
canonical L9 skills exist, what invocation tier each one carries, which
`skillOverrides` the Claude adapter templates project, and which skill each
shared route names as primary for the Claude `UserPromptSubmit` router.

Two properties make this usable as a preservation gate:

* **Repository-pure.** Every field is read from a tracked file. No `HOME`, no
  Cursor receipt, no Cursor gateway, no network, no clock. Running it with
  Cursor absent produces byte-identical output (validation V-CC-002).
* **Deterministic.** Mappings are emitted sorted, so a diff against the
  attested baseline names exactly which skill or route moved.

A change to Claude Code behavior is therefore never silent: it shows up as a
baseline diff that a human has to accept on purpose.

Usage:
    claude_projection_snapshot.py                  # print snapshot JSON
    claude_projection_snapshot.py --check          # compare against baseline
    claude_projection_snapshot.py --write-baseline # re-attest the baseline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

SCHEMA = "l9.claude-projection-snapshot.v1"

REGISTRY_REL = Path("ops/generated/skill-registry.json")
MANIFEST_REL = Path("skills/AUTONOMY_MANIFEST.yaml")
SETTINGS_TEMPLATE_REL = Path("environment/agents/adapters/claude-code/settings.template.json")
WORKSPACE_SETTINGS_REL = Path(".claude/settings.json")
BASELINE_REL = Path(
    "environment/agents/adapters/claude-code/baseline/claude-projection-baseline.json"
)


def repo_root(start: Path) -> Path:
    for parent in [start, *start.parents]:
        if (parent / "CANONICAL_LAW.md").is_file():
            return parent
    raise RuntimeError(f"governance repo root not found from {start}")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot(root: Path) -> dict[str, Any]:
    """Build the Claude Code projection snapshot for the tree at ``root``."""
    registry = _load_json(root / REGISTRY_REL)
    manifest = yaml.safe_load((root / MANIFEST_REL).read_text(encoding="utf-8"))
    template = _load_json(root / SETTINGS_TEMPLATE_REL)

    skills = registry.get("skills", [])
    canonical = sorted(str(s["name"]) for s in skills)

    # Invocation tier is the registry's own field; it is what
    # reconcile_claude_settings projects into skillOverrides.
    invocation = {str(s["name"]): str(s.get("invocation", "")) for s in skills}

    routing = manifest.get("claude_routing", {}) or {}
    routes = {
        str(r["id"]): str(r.get("primary", ""))
        for r in routing.get("routes", []) or []
        if r.get("id")
    }

    workspace_settings_path = root / WORKSPACE_SETTINGS_REL
    workspace_overrides: dict[str, str] | None = None
    if workspace_settings_path.is_file():
        workspace_overrides = dict(
            _load_json(workspace_settings_path).get("skillOverrides", {}) or {}
        )

    data: dict[str, Any] = {
        "schema": SCHEMA,
        "canonical_skills": canonical,
        "canonical_skill_count": len(canonical),
        "invocation": dict(sorted(invocation.items())),
        "settings_template_skill_overrides": dict(
            sorted((template.get("skillOverrides", {}) or {}).items())
        ),
        "routing_primary_skills": sorted(routing.get("primary_skills", []) or []),
        "routing_supporting_skills": sorted(routing.get("supporting_skills", []) or []),
        "routes": dict(sorted(routes.items())),
    }
    if workspace_overrides is not None:
        data["workspace_skill_overrides"] = dict(sorted(workspace_overrides.items()))
    return data


def _render(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _diff(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Human-readable field-level differences, most specific first."""
    findings: list[str] = []
    for key in sorted(set(baseline) | set(current)):
        was, now = baseline.get(key), current.get(key)
        if was == now:
            continue
        if isinstance(was, dict) and isinstance(now, dict):
            for name in sorted(set(was) | set(now)):
                if was.get(name) != now.get(name):
                    findings.append(f"{key}[{name}]: {was.get(name)!r} -> {now.get(name)!r}")
        elif isinstance(was, list) and isinstance(now, list):
            removed = sorted(set(was) - set(now))
            added = sorted(set(now) - set(was))
            if removed:
                findings.append(f"{key}: removed {removed}")
            if added:
                findings.append(f"{key}: added {added}")
        else:
            findings.append(f"{key}: {was!r} -> {now!r}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare the live snapshot against the attested baseline",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="re-attest the baseline from the live tree (deliberate act)",
    )
    args = parser.parse_args(argv)

    root = (args.root or repo_root(Path(__file__).resolve().parent)).resolve()
    current = snapshot(root)
    baseline_path = root / BASELINE_REL

    if args.write_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(_render(current), encoding="utf-8")
        print(f"WROTE: {BASELINE_REL}")
        return 0

    if not args.check:
        sys.stdout.write(_render(current))
        return 0

    if not baseline_path.is_file():
        print(f"FAIL: baseline missing: {BASELINE_REL}", file=sys.stderr)
        return 1

    findings = _diff(_load_json(baseline_path), current)
    if not findings:
        print(
            "PASS: Claude Code projection matches baseline "
            f"({current['canonical_skill_count']} canonical skills, "
            f"{len(current['routes'])} routes)"
        )
        return 0

    print("FAIL: Claude Code projection drifted from the attested baseline", file=sys.stderr)
    for line in findings:
        print(f"  {line}", file=sys.stderr)
    print(
        "\nClaude Code behavior is preserved by contract "
        "(docs/CLAUDE_CODE_PRESERVATION_CONTRACT.md, CC-001/CC-006).\n"
        "A drift here is either an unintended cross-agent regression — fix the "
        "change — or a deliberate, independently justified Claude Code change, "
        "which is re-attested with:\n"
        f"  python3 {REGISTRY_REL.parts[0]}/scripts/{Path(__file__).name} --write-baseline",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
