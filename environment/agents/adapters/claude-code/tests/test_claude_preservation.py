"""Claude Code Preservation Contract — V-CC-001..005.

Claude Code sits deliberately outside the Cursor virtualization boundary. Each
clause below is a named test, and each is paired with a negative fixture that
drives the same check red: a check that cannot fail is not evidence
(rules/95).

The V-CC-001 and V-CC-004 negatives are the exact shape PR #513 carried before
the sever — l9-plan-simple promoted out of explicit_only, its
`user-invocable-only` override gone from the Claude projection.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[3]
VALIDATOR = ADAPTER / "validate_claude_preservation.py"
BUILDER = ROOT / "ops" / "scripts" / "build_claude_skill_registry.py"
CURSOR_ADAPTER = ROOT / "environment" / "agents" / "adapters" / "cursor"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = _load(VALIDATOR, "l9_claude_preservation_validator")
builder = _load(BUILDER, "l9_registry_builder_for_preservation")


def _clause(result: dict, clause: str) -> list[str]:
    """Errors attributed to one clause, so a test asserts its own clause."""
    return [err for err in result["errors"] if err.startswith(f"{clause}:")]


# --------------------------------------------------------------------------
# tmp-corpus fixture: a governance root the validator can be pointed at
# --------------------------------------------------------------------------


def build_root(tmp_path: Path) -> Path:
    """A minimal governance root: canonical skills plus the Claude projection.

    The projection is *generated* from the corpus exactly as the real pipeline
    generates it (build_claude_skill_registry for the registry mirror, the
    explicit_only tier for skillOverrides — see sync_generated_artifacts), so a
    fixture cannot drift from production semantics.
    """
    root = tmp_path / "gov"
    (root / "skills").parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "skills", root / "skills", symlinks=True)
    project(root)
    write_baseline_from(root)
    return root


def project(root: Path) -> None:
    """Regenerate the Claude projection from the corpus."""
    registry = builder.build_registry(root)
    mirror = root / "environment/agents/adapters/claude-code/generated/skill-registry.json"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_text(builder.serialized(registry), encoding="utf-8")

    overrides = {
        record["name"]: "user-invocable-only"
        for record in sorted(registry["skills"], key=lambda item: item["name"])
        if record["invocation"] == "explicit_only"
    }
    settings = root / ".claude/settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps({"skillOverrides": overrides}, indent=2) + "\n", encoding="utf-8"
    )


def write_baseline_from(root: Path) -> None:
    tier_map, errors = validator.projected_tier_map(root)
    assert not errors, errors
    baseline = {
        "schema": "l9.claude-preservation-baseline.v1",
        "generated_from_commit": "fixture",
        "skill_count": len(tier_map),
        "skill_names": sorted(tier_map),
        "tier_map": dict(sorted(tier_map.items())),
    }
    path = root / validator.BASELINE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def an_explicit_only_skill(root: Path) -> str:
    """A skill the fixture projects as explicit_only.

    Chosen from the projection rather than hardcoded, so the negative fixtures
    below measure the clause and not the corpus they happen to start from —
    they must be able to fail on the pre-sever tree too, where l9-plan-simple
    is already promoted.
    """
    current, errors = validator.projected_tier_map(root)
    assert not errors, errors
    explicit = sorted(n for n, t in current.items() if t["invocation"] == "explicit_only")
    assert explicit, "fixture has no explicit_only skill to exercise"
    return "l9-plan-simple" if "l9-plan-simple" in explicit else explicit[0]


def promote_to_auto_invoke(root: Path, name: str) -> None:
    """Reproduce the pre-sever #513 state for one skill.

    Drops `disable-model-invocation: true` from the SKILL.md frontmatter and
    moves the manifest tier entry explicit_only -> auto_invoke, then
    regenerates. This is the change the sever removed, applied to a fixture.
    """
    skill_md = root / "skills" / name / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    skill_md.write_text(text.replace("disable-model-invocation: true\n", "", 1), encoding="utf-8")

    manifest = root / "skills" / "AUTONOMY_MANIFEST.yaml"
    lines = manifest.read_text(encoding="utf-8").splitlines(keepends=True)
    kept, removed = [], False
    index = 0
    while index < len(lines):
        if lines[index].strip() == f"- skill: {name}" and not removed:
            index += 1
            while index < len(lines) and lines[index].startswith("    "):
                index += 1
            removed = True
            continue
        kept.append(lines[index])
        index += 1
    assert removed, f"{name} not found in a manifest tier"
    text = "".join(kept)
    marker = "  auto_invoke:\n"
    assert marker in text
    entry = f"  - skill: {name}\n    use_when: promoted by the fixture under test\n"
    manifest.write_text(text.replace(marker, marker + entry, 1), encoding="utf-8")
    project(root)


# --------------------------------------------------------------------------
# V-CC-001 — projected skill set + tier map == baseline
# --------------------------------------------------------------------------


def test_v_cc_001_projection_matches_baseline_in_repo() -> None:
    result = validator.validate(ROOT)
    assert _clause(result, "V-CC-001") == []
    assert result["facts"]["tier_drift_count"] == 0
    assert result["facts"]["baseline_skill_count"] == result["facts"]["projected_skill_count"]


def test_v_cc_001_allowlist_is_empty_without_a_reasoned_entry() -> None:
    """An ALLOWLIST entry is a recorded exception, never a default."""
    assert validator.ALLOWLIST == {}, "every allowlist entry needs a reason and an owning PR"


def test_v_cc_001_fails_when_a_tier_moves(tmp_path: Path) -> None:
    """The exact shape of the hunk #513 carried: explicit_only -> model_allowed."""
    root = build_root(tmp_path)
    assert _clause(validator.validate(root), "V-CC-001") == []
    subject = an_explicit_only_skill(root)

    promote_to_auto_invoke(root, subject)

    errors = _clause(validator.validate(root), "V-CC-001")
    assert errors, "a Claude tier move must fail V-CC-001"
    assert subject in errors[0]
    assert "explicit_only" in errors[0] and "model_allowed" in errors[0]


def test_v_cc_001_fails_when_a_skill_leaves_the_projection(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    mirror = root / validator.CLAUDE_REGISTRY_REL
    registry = json.loads(mirror.read_text(encoding="utf-8"))
    registry["skills"] = [s for s in registry["skills"] if s["name"] != "l9-ynp"]
    mirror.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    errors = _clause(validator.validate(root), "V-CC-001")
    assert any("dropped from the Claude projection" in err and "l9-ynp" in err for err in errors)


# --------------------------------------------------------------------------
# V-CC-002 — Cursor-independent: no Cursor import, no ~/.cursor read
# --------------------------------------------------------------------------


def test_v_cc_002_validator_imports_no_cursor_module() -> None:
    result = validator.validate(ROOT)
    assert _clause(result, "V-CC-002") == []
    assert not [name for name in result["facts"]["validator_imports"] if "cursor" in name.lower()]


def test_v_cc_002_passes_with_the_cursor_adapter_tree_absent(tmp_path: Path) -> None:
    """CC-007: Claude Code runs correctly with Cursor entirely absent."""
    root = build_root(tmp_path)
    assert not (root / validator.CURSOR_ADAPTER_REL).exists()

    result = validator.validate(root)

    assert result["ok"], result["errors"]
    assert result["facts"]["cursor_tree_present"] is False
    assert result["facts"]["cursor_adapter_present"] is False


def test_v_cc_002_passes_with_no_cursor_home_and_no_cursor_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every L9_CURSOR_* var unset and HOME pointed at a tree with no ~/.cursor."""
    root = build_root(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    for key in [k for k in os.environ if k.startswith(("L9_CURSOR", "CURSOR"))]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(home))

    result = validator.validate(root)

    assert result["ok"], result["errors"]
    assert not (home / ".cursor").exists()


def test_v_cc_002_fails_when_the_validator_reads_cursor_state(tmp_path: Path) -> None:
    """The self-check fires on a copy that reaches into ~/.cursor."""
    tainted = tmp_path / "tainted_validator.py"
    source = VALIDATOR.read_text(encoding="utf-8")
    marker = "    errors: list[str] = []\n    source_path = Path(__file__).resolve()\n"
    assert marker in source
    tainted.write_text(
        source.replace(marker, marker + '    _route = "~/.cursor/l9/routes/current.json"\n', 1),
        encoding="utf-8",
    )
    module = _load(tainted, "l9_claude_preservation_tainted")

    errors = [e for e in module.validate(ROOT)["errors"] if e.startswith("V-CC-002:")]

    assert any("Cursor runtime state" in err for err in errors)


# --------------------------------------------------------------------------
# V-CC-003 — a new canonical skill propagates to the Claude projection
# --------------------------------------------------------------------------


def test_v_cc_003_repo_corpus_is_fully_projected() -> None:
    result = validator.validate(ROOT)
    assert _clause(result, "V-CC-003") == []
    assert result["facts"]["canonical_skill_count"] == result["facts"]["propagated"]


def test_v_cc_003_new_canonical_skill_reaches_claude(tmp_path: Path) -> None:
    """Adding a skill under skills/ must appear in the Claude projection."""
    root = build_root(tmp_path)
    name = "l9-synthetic-preservation"
    skill_dir = root / "skills" / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: synthetic capability proving that a new canonical "
        "skill propagates into the Claude Code projection. use when validating the "
        "preservation contract's propagation clause.\n---\n# synthetic\n",
        encoding="utf-8",
    )
    manifest = root / "skills" / "AUTONOMY_MANIFEST.yaml"
    text = manifest.read_text(encoding="utf-8")
    marker = "  auto_invoke:\n"
    manifest.write_text(
        text.replace(
            marker, marker + f"  - skill: {name}\n    use_when: synthetic propagation\n", 1
        ),
        encoding="utf-8",
    )
    project(root)

    current, errors = validator.projected_tier_map(root)

    assert not errors, errors
    assert name in current, "a new canonical skill did not reach the Claude projection"
    assert _clause(validator.validate(root), "V-CC-003") == []


def test_v_cc_003_fails_when_a_canonical_skill_is_not_projected(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    mirror = root / validator.CLAUDE_REGISTRY_REL
    registry = json.loads(mirror.read_text(encoding="utf-8"))
    registry["skills"] = [s for s in registry["skills"] if s["name"] != "l9-ynp"]
    mirror.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    errors = _clause(validator.validate(root), "V-CC-003")

    assert any("absent from the Claude projection" in err and "l9-ynp" in err for err in errors)


def test_v_cc_003_fails_when_an_explicit_skill_loses_its_override(tmp_path: Path) -> None:
    """The exact regression the sever fixed, seen from the settings side."""
    root = build_root(tmp_path)
    subject = an_explicit_only_skill(root)
    settings = root / validator.SETTINGS_REL
    data = json.loads(settings.read_text(encoding="utf-8"))
    del data["skillOverrides"][subject]
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    errors = _clause(validator.validate(root), "V-CC-003")

    assert any("without a Claude settings override" in err and subject in err for err in errors)


# --------------------------------------------------------------------------
# V-CC-004 — nothing reachable before is unreachable now
# --------------------------------------------------------------------------


def test_v_cc_004_every_baseline_skill_is_still_reachable() -> None:
    result = validator.validate(ROOT)
    assert _clause(result, "V-CC-004") == []
    assert result["facts"]["baseline_reachable_checked"] == result["facts"]["baseline_skill_count"]


def test_v_cc_004_fails_when_a_baseline_skill_loses_its_resource(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    mirror = root / validator.CLAUDE_REGISTRY_REL
    registry = json.loads(mirror.read_text(encoding="utf-8"))
    for record in registry["skills"]:
        if record["name"] == "l9-ynp":
            record["skill_md"] = "skills/l9-ynp/MOVED.md"
    mirror.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    errors = _clause(validator.validate(root), "V-CC-004")

    assert any("no longer reachable" in err and "l9-ynp" in err for err in errors)


def test_v_cc_004_fails_when_a_baseline_skill_is_no_longer_user_invocable(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    subject = an_explicit_only_skill(root)
    mirror = root / validator.CLAUDE_REGISTRY_REL
    registry = json.loads(mirror.read_text(encoding="utf-8"))
    for record in registry["skills"]:
        if record["name"] == subject:
            record["user_invocable"] = False
    mirror.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    errors = _clause(validator.validate(root), "V-CC-004")

    assert any("user_invocable is false" in err for err in errors)


# --------------------------------------------------------------------------
# V-CC-005 — the Cursor adapter tree never writes a Claude-owned path
# --------------------------------------------------------------------------


def test_v_cc_005_cursor_adapter_writes_no_claude_path() -> None:
    result = validator.validate(ROOT)
    assert _clause(result, "V-CC-005") == []
    assert result["facts"]["cursor_files_scanned"] > 0, "the scan must actually read files"


def test_v_cc_005_fails_on_a_cursor_installer_that_writes_claude_settings(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    cursor = root / validator.CURSOR_ADAPTER_REL
    cursor.mkdir(parents=True)
    (cursor / "install.sh").write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\nprintf "{}" > "$ROOT/.claude/settings.json"\n',
        encoding="utf-8",
    )

    errors = _clause(validator.validate(root), "V-CC-005")

    assert any("writes a Claude-owned path" in err and "install.sh" in err for err in errors)


def test_v_cc_005_fails_on_a_cursor_hook_that_writes_the_claude_adapter(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    cursor = root / validator.CURSOR_ADAPTER_REL
    cursor.mkdir(parents=True)
    (cursor / "hook.py").write_text(
        "from pathlib import Path\n"
        'Path("environment/agents/adapters/claude-code/settings.template.json")'
        '.write_text("{}", encoding="utf-8")\n',
        encoding="utf-8",
    )

    errors = _clause(validator.validate(root), "V-CC-005")

    assert any("writes a Claude-owned path" in err and "hook.py" in err for err in errors)


def test_v_cc_005_allows_a_cursor_file_that_only_names_a_claude_path(tmp_path: Path) -> None:
    """Naming is not writing — the real Cursor README documents the boundary."""
    root = build_root(tmp_path)
    cursor = root / validator.CURSOR_ADAPTER_REL
    cursor.mkdir(parents=True)
    (cursor / "README.md").write_text(
        "The Cursor adapter never touches `.claude/settings.json`; that plane is "
        "owned by environment/agents/adapters/claude-code.\n",
        encoding="utf-8",
    )

    assert _clause(validator.validate(root), "V-CC-005") == []


# --------------------------------------------------------------------------
# whole-contract
# --------------------------------------------------------------------------


def test_contract_passes_on_the_repository() -> None:
    result = validator.validate(ROOT)
    assert result["ok"], result["errors"]
    assert set(result["checks"]) == {
        "V-CC-001",
        "V-CC-002",
        "V-CC-003",
        "V-CC-004",
        "V-CC-005",
    }
    assert all(status == "PASS" for status in result["checks"].values())


def test_cli_exits_nonzero_on_a_violating_tree(tmp_path: Path) -> None:
    root = build_root(tmp_path)
    promote_to_auto_invoke(root, an_explicit_only_skill(root))

    assert validator.main(["--root", str(root)]) == 1
    assert validator.main(["--root", str(ROOT)]) == 0
