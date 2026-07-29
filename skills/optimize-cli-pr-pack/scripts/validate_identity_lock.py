#!/usr/bin/env python3
"""Reject identity drift from capability optimization into throttling, capability manufacture, audit-only, or quota bypass work."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    "SKILL.md",
    "references/optimize-cli-product-contract.md",
    "references/pr-commit-pack-contract.md",
    "references/latent-capability-activation.md",
    "references/adaptive-optimize-router.yaml",
    "references/evidence-decision-ledger-contract.yaml",
    "references/adaptive-convergence.md",
    "references/deploy-playbook-contract.md",
    "references/agent-handoff-contract.md",
    "schemas/pack-spec.schema.json",
    "schemas/pack-manifest.schema.json",
    "scripts/build_commit_pack.py",
    "scripts/validate_commit_pack.py",
    "scripts/self_test.py",
    "scripts/validate_latent_capability_integration.py",
    "scripts/route_optimize.py",
    "scripts/validate_decision_ledger.py",
    "scripts/validate_adaptive_reasoning.py",
    "scripts/validate_exemplary_skill.py",
}
BANNED = {
    "legacy skill identity": re.compile(r"\b(?:un)?throttle-cli-pr-pack\b", re.IGNORECASE),
    "legacy product reference": re.compile(r"references/throttle-cli-product-contract\.md", re.IGNORECASE),
    "throttle implementation objective": re.compile(r"\b(?:build|add|implement|create)\s+(?:a\s+)?(?:deployable\s+)?throttle\b", re.IGNORECASE),
    "rate limiter objective": re.compile(r"\b(?:add|build|implement|create)\s+(?:a\s+)?(?:deterministic\s+)?rate limit(?:er|ing)\b", re.IGNORECASE),
    "legacy model selector": re.compile(r"select_throttle_model|deployable_throttle_cli", re.IGNORECASE),
    "audit-only terminal output": re.compile(r"terminal_artifact:\s*audit", re.IGNORECASE),
}


def main() -> int:
    errors: list[str] = []
    present = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}
    for missing in sorted(REQUIRED_FILES - present):
        errors.append(f"missing required file: {missing}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    required_snippets = [
        "name: optimize-cli-pr-pack",
        "Produce a deployable code change that enables an underutilized, verified repository-owned capability",
        "Never implement a new throttle",
        "Do not use for audit-only output",
        "Adaptive Execution Router",
        "Evidence and Decision Ledger",
        "Run at most three",
        "A fourth cycle is prohibited",
        "EXECUTION_ROUTE.json",
        "DECISION_LEDGER.json",
        "OPTIMIZATION_PLAN.json",
        "PERFORMANCE.md",
        "bidirectional evidence",
    ]
    # M3: one distinctive phrase per numbered Identity Lock invariant (1..12), so
    # deleting any invariant fails the gate (previously only ~3 were covered).
    invariant_phrases = [
        "Enable a proven, underutilized repository-owned capability",   # 1
        "Preserve correctness, compatibility, safety",                  # 2
        "Never implement a new throttle",                               # 3
        "Produce a deployable PR commit pack, not an audit-only report",# 4
        "Synthesize all material findings before selecting",            # 5
        "Apply leverage after synthesis",                               # 6
        "Treat unproven reachability",                                  # 7
        "Preserve unresolved out-of-scope documentation-code divergence",  # 8
        "Route only the proof obligations required",                    # 9
        "Run at most three implementation-validation cycles",           # 10
        "Require comparable performance proof before claiming improvement",  # 11
        "Require explicit current-turn authorization before commit",    # 12
    ]
    for index, phrase in enumerate(invariant_phrases, start=1):
        if phrase not in skill:
            errors.append(f"SKILL.md missing Identity Lock invariant #{index}: {phrase}")
    for snippet in required_snippets:
        if snippet not in skill:
            errors.append(f"SKILL.md missing identity-lock text: {snippet}")

    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            errors.append(f"generated cache is forbidden: {path.relative_to(ROOT).as_posix()}")
            continue
        if path.suffix in {".zip", ".gz"}:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in BANNED.items():
            if pattern.search(text):
                errors.append(f"{label} in {path.relative_to(ROOT).as_posix()}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("PASS: optimize identity is locked and no legacy throttle objective remains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
