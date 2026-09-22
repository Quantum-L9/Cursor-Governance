"""Ceremony ownership: one public verb, no taught extra gate after precommit."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

REMOVED_GATE = re.compile(r"(?<![\w-])(?:make\s+)?pr[-]check(?![\w-])")
POST_COMMIT_PRECOMMIT = re.compile(
    r"after every local commit,\s*run `make precommit-repo`",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"(?i)\b(do not|don't|never|not a|not the|must not|forbidden|teaching failure)\b"
)

# Live teachers only. AGENTS.md historical append-only blocks are skipped.
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
CURRENT_PUBLICATION_DOCTRINE = (
    ROOT / "AGENTS.md",
    ROOT / "CANONICAL_LAW.md",
)


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


def _unnegated_hits(text: str, pattern: re.Pattern[str]) -> list[str]:
    hits: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not pattern.search(line):
            continue
        if NEGATION.search(line):
            continue
        hits.append(f"{number}:{line.strip()}")
    return hits


def test_live_teachers_do_not_teach_removed_pr_check_target() -> None:
    failures: list[str] = []
    for path in _iter_scan_paths():
        text = path.read_text(encoding="utf-8")
        hits = _unnegated_hits(text, REMOVED_GATE)
        if hits:
            rel = path.relative_to(ROOT).as_posix()
            failures.append(f"{rel}: {hits}")
    assert not failures, "removed gate alias taught in live teachers:\n" + "\n".join(failures)


def test_current_publication_doctrine_names_one_gate_only() -> None:
    """AGENTS and canonical law must retire the old public gate together."""
    for path in CURRENT_PUBLICATION_DOCTRINE:
        text = path.read_text(encoding="utf-8")
        assert "OPEN_PR=0 make pr" in text, f"{path.name} lacks the gate-only command"
        if path.name == "AGENTS.md":
            assert re.search(r"Do\s+not invoke `make pr-check`", text)
        else:
            assert "PR_CHECK_TARGET_REMOVED_V2" in text
            assert "`pr-check` as an invocable Make target" in text


def test_active_agents_publication_section_has_no_retired_gate() -> None:
    """The live publication section cannot rely on a later amendment to be correct."""
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    current_section = agents.split("## 4. Publish path (capability graph)", 1)[1].split(
        "<!-- AGENTS_PR_CHECK_TARGET_REMOVED_V2 -->", 1
    )[0]
    assert not REMOVED_GATE.search(current_section), (
        "active AGENTS publication doctrine still names the removed pr-check command"
    )


def test_live_teachers_do_not_teach_postcommit_precommit_repo() -> None:
    failures: list[str] = []
    for path in _iter_scan_paths():
        text = path.read_text(encoding="utf-8")
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
)

PLAN_CEREMONY_GATES = (
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


def test_makefile_pr_graph_uses_direct_gate() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    publish = (ROOT / "ops" / "make" / "publish.mk").read_text(encoding="utf-8")
    assert "ops/make/publish.mk" in makefile
    assert re.search(r"^pr:\s*pr-preflight\s*$", publish, re.MULTILINE), (
        "publish fragment must invoke the gate directly after pr-preflight"
    )
    assert "run_pr_gate.sh" in publish
    assert "pr-check:" not in makefile
    assert "pr-check:" not in publish
    assert "precommit-repo" not in re.search(
        r"^pr:\s*pr-preflight.*?(?=^\S|\Z)", publish, re.MULTILINE | re.DOTALL
    ).group(0)


FINISH_TEACHERS = (
    ROOT / "ops" / "autonomy" / "surface_profile.yaml",
    ROOT / "rules" / "88-l4-local-autonomy.mdc",
    ROOT / "rules" / "48-make-pr-remediation.mdc",
    ROOT / "rules" / "99-no-auto-commit.mdc",
    ROOT / "commands" / "gmp.md",
    ROOT / "skills" / "l9-gmp-protocol" / "SKILL.md",
    ROOT / "skills" / "l9-gmp-protocol" / "references" / "gmp-autonomy-bounds.md",
)

SPLIT_FINISH = (
    "catalog + commit + **STOP**",
    "catalog + commit + stop",
    "Cursor has no standing publish",
    "Cursor does not take this step",
    "Cursor stops after catalog",
    "after `make precommit-repo` and a scoped local commit, **STOP**",
    "After `make precommit-repo` and that commit, **STOP**",
)


def test_finish_teachers_teach_one_make_pr() -> None:
    missing: list[str] = []
    for path in FINISH_TEACHERS:
        assert path.is_file(), f"missing finish teacher: {path}"
        text = path.read_text(encoding="utf-8")
        if "PR_REMEDIATE=0 make pr" not in text and "l9 pr" not in text:
            missing.append(path.relative_to(ROOT).as_posix())
    assert not missing, "finish teachers must name PR_REMEDIATE=0 make pr or l9 pr:\n" + "\n".join(
        missing
    )


def test_finish_teachers_do_not_split_cursor_stop() -> None:
    failures: list[str] = []
    for path in FINISH_TEACHERS:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        lower = text.lower()
        for needle in SPLIT_FINISH:
            if needle.lower() in lower:
                failures.append(f"{rel}: {needle}")
    assert not failures, "split Cursor-STOP teaching still live:\n" + "\n".join(failures)
