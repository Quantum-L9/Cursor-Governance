#!/usr/bin/env python3
"""Contract tests for l9-pr-remediation 4.0.0. Stdlib only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
REFS = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "references").glob("*.md")}


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        _fail(f"{where} missing required string: {needle!r}")


def _forbid(text: str, needle: str, where: str) -> None:
    if needle in text:
        _fail(f"{where} contains forbidden string: {needle!r}")


def test_version_and_map() -> None:
    _need(SKILL, "version: 4.0.0", "SKILL.md")
    _need(SKILL, "references/run-contract.md", "SKILL.md")
    _need(SKILL, "scripts/self_test.py", "SKILL.md")
    if "run-contract.md" not in REFS:
        _fail("references/run-contract.md missing")


def test_merge_train() -> None:
    _need(SKILL, "FIRST_MERGE_GATE", "SKILL.md")
    _need(SKILL, "MERGE_TRAIN", "SKILL.md")
    _need(SKILL, "REMEDIATE_ALL", "SKILL.md")
    _need(SKILL, "oldest_created_at_default: false", "SKILL.md")
    for label, text in (("SKILL.md", SKILL), ("merge-advise.md", REFS["merge-advise.md"])):
        _forbid(text, "oldest first", label)
        _forbid(text, "older-to-newer", label)
    _need(REFS["run-contract.md"], "FIRST_MERGE_GATE", "run-contract.md")
    _need(REFS["convergence-loop.md"], "FIRST_MERGE_GATE", "convergence-loop.md")


def test_command_surface() -> None:
    _need(SKILL, "PR_REMEDIATE=0 make pr", "SKILL.md")
    _need(REFS["run-contract.md"], "PR_REMEDIATE=0 make pr", "run-contract.md")
    _need(REFS["fix-engine.md"], "sanctioned publish", "fix-engine.md")
    _need(REFS["remediation-plan.md"], "sanctioned publish", "remediation-plan.md")
    for label, text in (
        ("fix-engine.md", REFS["fix-engine.md"]),
        ("remediation-plan.md", REFS["remediation-plan.md"]),
        ("merge-advise.md", REFS["merge-advise.md"]),
    ):
        if "git push" not in text:
            continue
        if "PR_REMEDIATE=0" in text or "sanctioned" in text.lower():
            continue
        if "Never raw `git push`" in text or "never raw `git push`" in text:
            continue
        idx = text.find("git push")
        prefix = text[max(0, idx - 80) : idx]
        if any(tok in prefix.lower() for tok in ("do not", "forbidden", "never", "not")):
            continue
    if "\ngit push\n" in REFS["remediation-plan.md"]:
        _fail("remediation-plan.md still has a bare git push success path")
    if "git push (ONE push)" in REFS["fix-engine.md"]:
        _fail("fix-engine.md still instructs git push (ONE push)")
    if "git push origin main" in REFS["merge-advise.md"]:
        _fail("merge-advise.md still instructs git push origin main")
    _need(REFS["run-contract.md"], "git add -u", "run-contract.md")  # listed as forbidden


def test_venv() -> None:
    rc = REFS["run-contract.md"]
    _need(rc, "UV_PYTHON", "run-contract.md")
    _need(rc, "ENVIRONMENT", "run-contract.md")
    _need(SKILL, "ENVIRONMENT", "SKILL.md")
    _need(REFS["ownership-boundary.md"], "## ENVIRONMENT", "ownership-boundary.md")
    _need(REFS["finding-classifier.md"], "ENVIRONMENT", "finding-classifier.md")
    _forbid(rc, "pip install cryptography==", "run-contract.md")
    _need(rc, "symlink a failing SSOT venv", "run-contract.md")
    _need(rc, ".cursor-commands/.venv", "run-contract.md")


def test_conversations() -> None:
    _need(SKILL, "isResolved: false", "SKILL.md")
    _need(SKILL, "any author", "SKILL.md")
    _forbid(SKILL, "leave true human-decision threads open", "SKILL.md")
    _forbid(REFS["ownership-boundary.md"], "leave the thread open", "ownership-boundary.md")
    _forbid(REFS["review-replies.md"], "except open HUMAN decisions", "review-replies.md")
    _forbid(REFS["validation-gates.md"], "except open HUMAN decisions", "validation-gates.md")
    _need(REFS["code-review-agents.md"], "isResolved", "code-review-agents.md")


def test_fast_path() -> None:
    _need(SKILL, "Min preflight", "SKILL.md")
    _need(SKILL, "require_precommit_all_files: false", "SKILL.md")
    _forbid(SKILL, "pre-commit run --all-files", "SKILL.md")
    _forbid(REFS["remediation-plan.md"], "pre-commit run --all-files", "remediation-plan.md")
    _need(REFS["validation-gates.md"], "cited", "validation-gates.md")
    _need(REFS["signal-ingestion.md"], "$PWD", "signal-ingestion.md")


def test_ci_and_poll() -> None:
    _need(SKILL, "Poll workers never merge", "SKILL.md")
    _need(REFS["run-contract.md"], "merge_eligible", "run-contract.md")
    _need(REFS["remediation-plan.md"], "companion", "remediation-plan.md")


def test_counters() -> None:
    for key in (
        "time_to_first_useful_action",
        "blocked_command_attempts",
        "environment_repair_count",
        "ci_run_count",
        "merge_conflict_count",
        "repeated_command_count",
    ):
        _need(SKILL, key, "SKILL.md")


def main() -> None:
    test_version_and_map()
    test_merge_train()
    test_command_surface()
    test_venv()
    test_conversations()
    test_fast_path()
    test_ci_and_poll()
    test_counters()
    print("l9-pr-remediation self_test: PASS")


if __name__ == "__main__":
    main()
