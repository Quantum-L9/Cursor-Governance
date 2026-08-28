#!/usr/bin/env python3
"""Contract tests for l9-ynp 2.1.0. Stdlib only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
WORKFLOW = (ROOT / "references" / "ynp-workflow.md").read_text(encoding="utf-8")
CMD = Path(__file__).resolve().parents[3] / "commands" / "ynp.md"
CMD_TEXT = CMD.read_text(encoding="utf-8") if CMD.is_file() else ""


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _need(text: str, needle: str, where: str) -> None:
    if needle not in text:
        _fail(f"{where} missing required string: {needle!r}")


def _forbid(text: str, needle: str, where: str) -> None:
    if needle in text:
        _fail(f"{where} contains forbidden string: {needle!r}")


def test_action_enum() -> None:
    for text, where in ((SKILL, "SKILL.md"), (WORKFLOW, "ynp-workflow.md"), (CMD_TEXT, "commands/ynp.md")):
        if not text:
            _fail(f"{where} missing")
        _need(text, "action:", where)
        _need(text, "proceed_with_validation", where)
        _need(text, "bounded_probe", where)
        _need(text, "evidence_quality", where)
        _need(text, "decision_risk", where)


def test_no_auto_execute_or_percent_template() -> None:
    pack = "\n".join([SKILL, WORKFLOW, CMD_TEXT])
    _forbid(pack, "AUTO-" + "EXECUTE", "l9-ynp pack + commands/ynp.md")
    _forbid(pack, "Confidence: {score}%", "l9-ynp pack + commands/ynp.md")
    _forbid(SKILL, "Confidence MUST be stated", "SKILL.md")
    _need(SKILL, "action: MUST be stated", "SKILL.md")
    _need(SKILL, "uncalibrated", "SKILL.md")
    _need(SKILL, "do not auto-execute unless the user explicitly asks", "SKILL.md")


def test_version() -> None:
    _need(SKILL, "version: 2.1.0", "SKILL.md")
    _need(CMD_TEXT, 'version: "8.2.0"', "commands/ynp.md")


def main() -> int:
    test_version()
    test_action_enum()
    test_no_auto_execute_or_percent_template()
    print("PASS: l9-ynp self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
