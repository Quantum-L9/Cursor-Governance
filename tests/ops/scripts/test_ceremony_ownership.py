"""Ceremony ownership: one public verb, no taught extra gate after precommit."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

DUAL_CEREMONY = re.compile(r"make pr-check\s*&&\s*make pr")
POST_COMMIT_PRECOMMIT = re.compile(
    r"after every local commit,\s*run `make precommit-repo`",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"(?i)\b(do not|don't|never|not a|not the|must not|forbidden|teaching failure)\b"
)

# Live teachers only. AGENTS.md historical append-only blocks are skipped.
# Remediator pack files that already forbid make pr-check are skipped.
SCAN_FILES = (
    ROOT / "ops" / "autonomy" / "surface_profile.yaml",
    ROOT / "ops" / "scripts" / "open_pr_after_gate.sh",
    ROOT / "ops" / "scripts" / "run_pr_precommit.sh",
    ROOT / "ops" / "config" / "commit-verification-contract.json",
)
SCAN_GLOBS = (
    "rules/*.mdc",
    "commands/*.md",
)

SKIP_REMEDIATOR_IF_FORBIDS = "do not run make pr-check"


def _iter_scan_paths() -> list[Path]:
    paths = list(SCAN_FILES)
    for glob in SCAN_GLOBS:
        paths.extend(sorted(ROOT.glob(glob)))
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        out.append(path)
    return out


def _skip_remediator(path: Path, text: str) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if "l9-pr-remediation" not in rel:
        return False
    return SKIP_REMEDIATOR_IF_FORBIDS in text.lower()


def _unnegated_hits(text: str, pattern: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not pattern.search(line):
            continue
        if NEGATION.search(line):
            continue
        hits.append(f"{number}:{line.strip()}")
    return hits


def test_live_teachers_do_not_stack_pr_check_then_pr() -> None:
    failures: list[str] = []
    for path in _iter_scan_paths():
        text = path.read_text(encoding="utf-8")
        if _skip_remediator(path, text):
            continue
        hits = _unnegated_hits(text, DUAL_CEREMONY)
        if hits:
            rel = path.relative_to(ROOT).as_posix()
            failures.append(f"{rel}: {hits}")
    assert not failures, "unnegated make pr-check && make pr in live teachers:\n" + "\n".join(
        failures
    )


def test_live_teachers_do_not_teach_postcommit_precommit_repo() -> None:
    failures: list[str] = []
    for path in _iter_scan_paths():
        text = path.read_text(encoding="utf-8")
        if _skip_remediator(path, text):
            continue
        hits = _unnegated_hits(text, POST_COMMIT_PRECOMMIT)
        if hits:
            rel = path.relative_to(ROOT).as_posix()
            failures.append(f"{rel}: {hits}")
    assert not failures, (
        "unnegated post-commit make precommit-repo ritual in live teachers:\n" + "\n".join(failures)
    )


PLAN_TEACHERS = (
    ROOT / "skills" / "l9-plan" / "SKILL.md",
    ROOT / "skills" / "l9-plan-simple" / "SKILL.md",
    ROOT / "commands" / "l9-plan.md",
    ROOT / "commands" / "l9-plan-simple.md",
)

PLAN_CEREMONY_GATES = (
    re.compile(r"make pr-check"),
    re.compile(r"OPEN_PR=0"),
    re.compile(r"git commit"),
    re.compile(r"git push"),
    re.compile(r"(?<![\w-])make pr(?![\w-])"),
)


def test_plan_teachers_keep_only_precommit_catalog() -> None:
    failures: list[str] = []
    for path in PLAN_TEACHERS:
        assert path.is_file(), f"missing plan teacher: {path}"
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        for pattern in PLAN_CEREMONY_GATES:
            hits = _unnegated_hits(text, pattern)
            if hits:
                failures.append(f"{rel} {pattern.pattern}: {hits}")
    assert not failures, "unnegated commit/push/pr ceremony in plan teachers:\n" + "\n".join(
        failures
    )


def test_makefile_pr_graph_keeps_pr_check_leaf() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^pr:\s*pr-preflight\s+pr-check\s*$", makefile, re.MULTILINE), (
        "Makefile must keep pr: pr-preflight pr-check"
    )
    assert not re.search(r"^pr-check:\s*.*precommit-repo", makefile, re.MULTILINE), (
        "Do not re-add precommit-repo as a Make prereq of pr-check"
    )
    assert not re.search(r"^pr:\s*.*precommit-repo", makefile, re.MULTILINE), (
        "Do not re-add precommit-repo as a Make prereq of pr"
    )


CURSOR_FINISH_TEACHERS = (
    ROOT / "ops" / "autonomy" / "surface_profile.yaml",
    ROOT / "rules" / "88-l4-local-autonomy.mdc",
    ROOT / "rules" / "48-make-pr-remediation.mdc",
    ROOT / "rules" / "99-no-auto-commit.mdc",
    ROOT / "rules" / "42-no-abandoned-work.mdc",
    ROOT / "commands" / "gmp.md",
    ROOT / "skills" / "l9-gmp-protocol" / "SKILL.md",
    ROOT / "skills" / "l9-gmp-protocol" / "references" / "gmp-autonomy-bounds.md",
)

FINISH_THEN_MAKE_PR = re.compile(
    r"(Only then:.*make pr|"
    r"PR_REMEDIATE=[01] make pr|"
    r"Finalize runs L4 release.*make pr|"
    r"Happy path: finish → scoped-commit → `make pr`)"
)
SURFACE_PREDICATE = re.compile(r"(?i)claude-code|L9_GOVERNANCE_SURFACE")


def _preceding_or_same_has_predicate(lines: list[str], index: int) -> bool:
    if SURFACE_PREDICATE.search(lines[index]):
        return True
    if index == 0:
        return False
    return bool(SURFACE_PREDICATE.search(lines[index - 1]))


def test_cursor_finish_teachers_do_not_unnegated_make_pr() -> None:
    failures: list[str] = []
    for path in CURSOR_FINISH_TEACHERS:
        assert path.is_file(), f"missing finish teacher: {path}"
        lines = path.read_text(encoding="utf-8").splitlines()
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(lines, start=1):
            if not FINISH_THEN_MAKE_PR.search(line):
                continue
            if NEGATION.search(line):
                continue
            if _preceding_or_same_has_predicate(lines, number - 1):
                continue
            failures.append(f"{rel}:{number}:{line.strip()}")
    assert not failures, (
        "unnegated Cursor finish-then-make-pr without a claude-code predicate:\n"
        + "\n".join(failures)
    )


def test_cursor_finish_teachers_name_stop() -> None:
    missing: list[str] = []
    for path in CURSOR_FINISH_TEACHERS:
        text = path.read_text(encoding="utf-8")
        if "STOP" not in text and "stop" not in text:
            missing.append(path.relative_to(ROOT).as_posix())
    assert not missing, "finish teachers must name Cursor STOP:\n" + "\n".join(missing)
