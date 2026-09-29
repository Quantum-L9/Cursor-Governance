"""Structural reachability tests for the modular Cursor-Governance Makefile.

The root Makefile owns only composition, the capability registry, dispatcher
classification, and introspection. Domain recipes live under ``ops/make``.
These assertions keep the root-to-fragment-to-consumer graph closed: adding a
fragment, a capability, or a consumer-safe target cannot silently bypass the
single registry.
"""

from __future__ import annotations

import collections
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAKEFILE = ROOT / "Makefile"
MAKE_DIR = ROOT / "ops" / "make"

ROOT_TARGETS = {
    "help",
    "targets",
    "consumer-targets",
    "l9-consumer-safe-list",
}
TARGET_RULE = re.compile(r"^(?P<targets>[A-Za-z0-9_. -]+):(?P<tail>.*)$")


def _assignment_targets(path: Path) -> list[str]:
    """Return every target registered in the file's ``L9_TARGETS`` clauses."""
    values: list[str] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^L9_TARGETS\s*(?::=|\+=)\s*(?:\\)?$", line):
            index += 1
            continue
        while True:
            index += 1
            assert index < len(lines), f"unterminated L9_TARGETS assignment in {path}"
            line = lines[index].strip()
            continued = line.endswith("\\")
            values.extend(line.removesuffix("\\").rstrip().split())
            if not continued:
                break
        index += 1
    return values


def _rule_owners(path: Path) -> dict[str, list[Path]]:
    """Map recipe/prerequisite-bearing targets to their owning Makefile.

    A target-specific export (for example ``pr: export PR_EARLY_OVERLAP = 1``)
    refines the same target but does not make a second recipe owner.
    """
    owned: dict[str, list[Path]] = collections.defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(("#", "\t", ".")):
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*(?::=|\+=|\?=)", line):
            continue
        match = TARGET_RULE.match(line)
        if match is None:
            continue
        tail = match.group("tail").strip()
        if tail.startswith("export ") or tail.startswith("private "):
            continue
        for target in match.group("targets").split():
            owned[target].append(path)
    return owned


def _make_fragments() -> list[str]:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        r"^MAKE_FRAGMENTS\s*:=\s*\\\n(?P<body>(?:.*\\\n)+?\s*ops/make/internal\.mk)$",
        text,
        re.MULTILINE,
    )
    assert match is not None, "root Makefile must declare the fragment composition list"
    return [line.strip().removesuffix("\\").strip() for line in match.group("body").splitlines()]


def _consumer_safe_targets() -> list[str]:
    text = MAKEFILE.read_text(encoding="utf-8")
    match = re.search(
        r"^L9_CONSUMER_SAFE_TARGETS\s*:=\s*\\\n(?P<body>(?:.*\\\n)+?\s*workspace-clean)$",
        text,
        re.MULTILINE,
    )
    assert match is not None, "root Makefile must own the consumer-safe target list"
    return [line.strip().removesuffix("\\").strip() for line in match.group("body").splitlines()]


def test_root_composes_every_live_make_fragment_once() -> None:
    fragments = _make_fragments()
    live = sorted(path.relative_to(ROOT).as_posix() for path in MAKE_DIR.glob("*.mk"))
    assert len(fragments) == len(set(fragments)), "fragment composition contains duplicates"
    assert sorted(fragments) == live

    root = MAKEFILE.read_text(encoding="utf-8")
    assert "include $(MAKE_FRAGMENTS)" in root
    assert "_MISSING_MAKE_FRAGMENTS" in root
    assert "missing required Make fragments" in root


def test_every_registered_capability_has_one_live_recipe_owner() -> None:
    fragments = [ROOT / path for path in _make_fragments()]
    registered = _assignment_targets(MAKEFILE)
    for fragment in fragments:
        registered.extend(_assignment_targets(fragment))

    counts = collections.Counter(registered)
    duplicates = sorted(target for target, count in counts.items() if count != 1)
    assert not duplicates, f"each capability must be registered exactly once: {duplicates}"

    owners: dict[str, list[Path]] = collections.defaultdict(list)
    for path in [MAKEFILE, *fragments]:
        for target, target_owners in _rule_owners(path).items():
            owners[target].extend(target_owners)

    missing = sorted(target for target in registered if target not in owners)
    assert not missing, f"registered capabilities need a recipe/prerequisite owner: {missing}"

    duplicate_owners = {
        target: sorted({owner.relative_to(ROOT).as_posix() for owner in paths})
        for target, paths in owners.items()
        if target in registered and len(set(paths)) != 1
    }
    assert not duplicate_owners, f"capabilities have competing fragment owners: {duplicate_owners}"


def test_root_stays_a_composition_and_introspection_surface() -> None:
    root_owned = set(_rule_owners(MAKEFILE))
    assert root_owned == ROOT_TARGETS
    text = MAKEFILE.read_text(encoding="utf-8")
    assert ".DEFAULT_GOAL := help" in text
    assert "L9_TARGETS :=" in text
    assert "L9_CONSUMER_SAFE_TARGETS :=" in text


def test_consumer_safe_targets_are_registered_and_exposed_by_make() -> None:
    registered = set(_assignment_targets(MAKEFILE))
    for fragment in (ROOT / path for path in _make_fragments()):
        registered.update(_assignment_targets(fragment))
    safe = _consumer_safe_targets()
    assert len(safe) == len(set(safe)), "consumer-safe registry contains duplicates"
    assert set(safe) <= registered

    result = subprocess.run(
        ["make", "--no-print-directory", "-n", "l9-consumer-safe-list"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "@echo" not in result.stdout
    assert "echo " + " ".join(safe) in result.stdout


def test_registered_targets_have_parseable_make_database_entries() -> None:
    targets = _assignment_targets(MAKEFILE)
    for fragment in (ROOT / path for path in _make_fragments()):
        targets.extend(_assignment_targets(fragment))
    result = subprocess.run(
        ["make", "--no-print-directory", "-rRpn"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for target in targets:
        assert re.search(rf"(?m)^{re.escape(target)}:", result.stdout), target


# ---------------------------------------------------------------------------
# Boundary: the local WIP subsystem was evicted (reports/wip-eviction/).
# These assertions protect the architectural property, not a lifecycle.
# ---------------------------------------------------------------------------

_WIP_ENGINE_PATHS = (
    "ops/scripts/wip_corpus.py",
    "ops/config/wip-corpus.yaml",
    "ops/config/wip-inventory.schema.yaml",
    "ops/config/wip-prune-receipt.schema.yaml",
    "ops/scripts/tests/test_wip_corpus.py",
)
_WIP_MAKE_TARGETS = {"wip-hygiene", "wip-inventory"}
_FF_CORPUS_KEEP_FILES = (
    "ops/scripts/lib/ssot_machine_local_keep.sh",
    "skills/l9-repo-sync/scripts/ff.sh",
    "skills/l9-repo-sync/scripts/ff_shelf.py",
)
_SCANNER_CONFIGS = (
    ".pre-commit-config.yaml",
    "pyproject.toml",
    ".ruffignore",
    "biome.json",
    ".biomeignore",
    ".semgrepignore",
    ".gitleaks.toml",
    "sonar-project.properties",
    ".sonarcloud.properties",
    ".cursorignore",
    ".github/codeql/codeql-config.yml",
    "ops/scripts/resolve_changed_files.sh",
    "ops/scripts/run_pr_security.sh",
)
_WIP_PATH_TOKEN = re.compile(r"(?<![A-Za-z0-9_./-])WIP(?:/|\b)")
_WIP_CI_TOKEN = re.compile(r"WIP/\*\*|\^WIP/|:!\*\*/WIP")
_WIP_POLICY_TOKENS = (
    "make wip-hygiene",
    "wip_corpus.py",
    "WIP/INVENTORY.yaml",
    "WIP/_receipts",
    "ssot_ff_corpus_skip_rel",
)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _frontmatter_globs(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    head = text[3:end] if end != -1 else ""
    match = re.search(r"^globs:\s*(.*)$", head, re.MULTILINE)
    return match.group(1) if match else ""


def test_cursor_governance_has_no_local_wip_subsystem() -> None:
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--", "WIP"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert tracked == "", "WIP/ must not exist as a tracked top-level directory"

    present = [rel for rel in _WIP_ENGINE_PATHS if (ROOT / rel).exists()]
    assert not present, f"retired WIP engine files reappeared: {present}"

    registered: set[str] = set()
    for fragment in sorted(MAKE_DIR.glob("*.mk")):
        registered.update(_assignment_targets(fragment))
        registered.update(_rule_owners(fragment))
    registered.update(_assignment_targets(MAKEFILE))
    assert not (registered & _WIP_MAKE_TARGETS), "WIP Make targets must stay absent"

    for rel in _FF_CORPUS_KEEP_FILES:
        assert not _WIP_PATH_TOKEN.search(_read(rel)), f"{rel}: /ff must not special-case WIP"

    for rel in _SCANNER_CONFIGS:
        assert not _WIP_PATH_TOKEN.search(_read(rel)), f"{rel}: WIP scanner exemption reappeared"

    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        assert not _WIP_CI_TOKEN.search(workflow.read_text(encoding="utf-8")), (
            f"{workflow.relative_to(ROOT)}: WIP CI paths-ignore reappeared"
        )

    for rule in sorted((ROOT / "rules").glob("*.mdc")):
        text = rule.read_text(encoding="utf-8")
        assert "WIP" not in _frontmatter_globs(text), f"{rule.name}: rule scoped to WIP/"
        hits = [token for token in _WIP_POLICY_TOKENS if token in text]
        assert not hits, f"{rule.name} prescribes retired WIP lifecycle: {hits}"

    assert "<!-- WIP_SUBSYSTEM_RETIRED_V1 -->" in _read("AGENTS.md"), (
        "AGENTS.md must carry the WIP retirement amendment"
    )
    assert "| `WIP/` |" not in _read("ARCHITECTURE.md"), "ARCHITECTURE.md lists WIP/ as a surface"
    assert (ROOT / "reports" / "wip-eviction" / "eviction-receipt.json").is_file()
