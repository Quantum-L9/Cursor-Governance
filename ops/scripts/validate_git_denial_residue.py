#!/usr/bin/env python3
"""Fail if an active authority surface claims `git push` / `gh` is gate-denied.

PR #226 removed execution gating for `git` and `gh`; #235 replaced it with
effect-based guardrails (`ops/autonomy/git_guardrails.py`). The doctrine text did
not follow for three days, so every rung of the authority chain — CANONICAL_LAW
§6.2, the Autonomy Surface Profile, AGENTS.md, CLAUDE.md and rules 53/88/99 —
named a denial that `ops/autonomy/local_execution_gate.py` had stopped
performing. An agent reading any of them would have waited for an error that
never comes.

This gate keeps that from returning. It is deliberately narrow: it flags a
sentence that asserts a `git`/`gh` command IS denied, on a surface an agent
treats as law. Text that marks the claim as retired, or that states the current
model, is allowed — the point is truthfulness, not banning the words.

Historical evidence (docs/plans, reports, releases, WIP) is out of scope, same as
the sibling gate `validate_legacy_doctrine_residue.py`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Surfaces an agent reads as standing instruction. Files, then directories.
AUTHORITY_FILES = (
    "CANONICAL_LAW.md",
    "AGENTS.md",
    "CLAUDE.md",
    "ops/autonomy/surface_profile.yaml",
)
AUTHORITY_DIRS = (
    "rules",
    "environment/generated/llm-rules",
    "skills",
    "commands",
)

SKIP_DIR_PARTS = {"_archived", "archived", "reports", "WIP", "__pycache__", ".git"}

SKIP_NAMES = {
    "validate_git_denial_residue.py",
    "test_validate_git_denial_residue.py",
}

TEXT_SUFFIXES = {".md", ".mdc", ".yaml", ".yml", ".json", ".txt"}

#: An assertion that a git/gh command is refused. Needs the command AND a denial
#: verb on the same line. Requiring a copula ("is denied") was too narrow: the
#: text this gate exists to catch read "`git push` / `gh pr create` / `make pr`
#: denied until `authorize-release`" — a bare participle. A skill's own
#: discipline ("NEVER raw git push") carries no denial verb and stays clean.
#: Anchored at \A deliberately. This is a *containment* test — two zero-width
#: lookaheads that consume nothing — so if it matches anywhere it matches at
#: offset 0, and letting `search` retry it at every offset is pure waste: each
#: retry rescans the rest of the unit, which is O(n^2). Units are whole
#: paragraphs and a generated manifest is one 50k-character paragraph with no
#: blank line in it, so that quadratic term hung this gate for minutes on a file
#: it was only ever going to clear. `[\s\S]` rather than `.` because a unit
#: that ever carries a newline must still be scanned end to end.
DENIAL_CLAIM = re.compile(
    r"(?i)\A"
    r"(?=[\s\S]*\b(?:git\s+push|gh\s+pr\s+create|gh\s+pr\s+edit)\b)"
    r"(?=[\s\S]*\b(?:denied|blocked|refused|rejected|prohibited)\b)"
)

#: The claim is fine when the unit also says it is no longer true, states a
#: condition, or is quoting the historical position. A bare §6.2.4 citation
#: is not an exemption — that section is exactly where a false denial is
#: likely to hide.
ALLOW_LINE = re.compile(
    r"(?i)("
    # `not denied`, `is *not* denied`, `NOT gate-denied`, `not mechanically denied`
    r"\bnot\b[\s*_`]*(?:mechanically |automatically |gate[- ])?deni|"
    r"not denied|"
    r"is NOT denied|"
    r"no longer|"
    r"not blocked|"
    r"never arrives|"
    r"stopped|"
    r"used to|"
    r"formerly|"
    r"historical|"
    r"superseded|"
    r"retired|"
    r"was denied|"
    r"if .*denied|"
    r"where .*denied|"
    r"elsewhere|"
    r"off doctrine but"
    r")"
)


def _candidates() -> list[Path]:
    seen: list[Path] = []
    for name in AUTHORITY_FILES:
        path = ROOT / name
        if path.is_file():
            seen.append(path)
    for directory in AUTHORITY_DIRS:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            rel_parts = path.relative_to(ROOT).parts
            if any(part in SKIP_DIR_PARTS for part in rel_parts):
                continue
            if path.name in SKIP_NAMES:
                continue
            seen.append(path)
    return seen


def _paragraphs(text: str) -> list[tuple[int, str]]:
    """Blank-line-separated paragraphs with the first source line of each.

    Authority Markdown wraps mid-sentence. A denial split across two lines
    (command on one line, "denied at every phase" on the next) must still
    match. Location stays the paragraph start so the report is usable.
    """
    units: list[tuple[int, str]] = []
    start: int | None = None
    buf: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            if buf and start is not None:
                units.append((start, " ".join(buf)))
            buf = []
            start = None
            continue
        if start is None:
            start = number
        buf.append(line)
    if buf and start is not None:
        units.append((start, " ".join(buf)))
    return units


def scan(paths: list[Path]) -> list[str]:
    findings = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for number, unit in _paragraphs(text):
            if DENIAL_CLAIM.search(unit) and not ALLOW_LINE.search(unit):
                findings.append(f"{rel}:{number}: {unit.strip()[:160]}")
    return findings


def main(argv: list[str] | None = None) -> int:
    del argv
    findings = scan(_candidates())
    if findings:
        print("FAIL: active doctrine claims `git`/`gh` is denied by a gate")
        print(
            "local_execution_gate.py exempts git and gh (git_execution_exemption.py); "
            "denial is by effect via git_guardrails.py. See CANONICAL_LAW §6.2.4."
        )
        print("State the preference, or mark the claim retired — do not assert the block.")
        for hit in findings[:80]:
            print(f"  {hit}")
        if len(findings) > 80:
            print(f"  ... and {len(findings) - 80} more")
        return 1
    print("PASS: no active surface claims a git/gh gate denial")
    return 0


if __name__ == "__main__":
    sys.exit(main())
