"""Cursor skill-projection invariants (VSP phases 9, 11, 12).

Inventory invariants:
  * canonical skill names == registry skill names
  * Cursor-visible skill count == 1 (the gateway)
  * gateway not in the registry or manifest
  * adding canonical skills increments the registry only
  * adding 1000 synthetic skills keeps the native count at 1
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[3]
VALIDATOR = ADAPTER / "validate_skill_projection.py"
BUILDER = ROOT / "ops" / "scripts" / "build_claude_skill_registry.py"
PROJECTION = ADAPTER / "skills"
GATEWAY = "l9-skill-gateway"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = _load(VALIDATOR, "l9_cursor_projection_validator")
builder = _load(BUILDER, "l9_registry_builder_for_projection")


def copy_root(tmp_path: Path) -> Path:
    """A minimal governance root copy: skills, manifest, plugin, hooks, projection."""
    root = tmp_path / "gov"
    for rel in (
        "skills",
        ".cursor-plugin",
        "ops/hooks/hooks.json.template",
        "ops/generated/skill-registry.json",
        "environment/agents/adapters/cursor/skills",
    ):
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)
    return root


def regenerate(root: Path) -> None:
    text = builder.serialized(builder.build_registry(root))
    (root / "ops" / "generated" / "skill-registry.json").write_text(text, encoding="utf-8")


def add_synthetic_skills(root: Path, count: int) -> list[str]:
    manifest_path = root / "skills" / "AUTONOMY_MANIFEST.yaml"
    names = [f"l9-synthetic-{i:05d}" for i in range(count)]
    lines = []
    for name in names:
        skill_dir = root / "skills" / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: synthetic capability number {name} for scale proof. "
            "use when validating that canonical cardinality never changes native cardinality, "
            "or when measuring registry scale.\n---\n# synthetic\n",
            encoding="utf-8",
        )
        lines.append(f"  - skill: {name}\n    use_when: synthetic scale proof for {name}\n")
    text = manifest_path.read_text(encoding="utf-8")
    marker = "  auto_invoke:\n"
    assert marker in text
    text = text.replace(marker, marker + "".join(lines), 1)
    manifest_path.write_text(text, encoding="utf-8")
    return names


def native_count(root: Path) -> int:
    projection = root / "environment" / "agents" / "adapters" / "cursor" / "skills"
    return sum(1 for entry in projection.iterdir() if entry.is_dir())


# --- live repository -----------------------------------------------------------


def test_live_projection_passes_strict():
    result = validator.validate(ROOT)
    assert result["ok"], result["errors"]
    facts = result["facts"]
    assert facts["native_skills"] == [GATEWAY]
    assert facts["native_skill_count"] == 1
    assert facts["registry_skill_count"] == facts["canonical_skill_count"]
    assert facts["plugin_skills"] == validator.PLUGIN_SKILLS_VALUE


def test_validator_cli_exit_codes():
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(ROOT), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert json.loads(proc.stdout)["ok"] is True


def test_gateway_not_in_registry_or_manifest():
    registry = json.loads((ROOT / "ops" / "generated" / "skill-registry.json").read_text())
    assert GATEWAY not in {item["name"] for item in registry["skills"]}
    manifest = (ROOT / "skills" / "AUTONOMY_MANIFEST.yaml").read_text(encoding="utf-8")
    # Named only as the cursor_discovery gateway, never as a tier entry or route.
    assert f"skill: {GATEWAY}" not in manifest
    assert f"primary: {GATEWAY}" not in manifest
    assert not (ROOT / "skills" / GATEWAY).exists()


def test_gateway_does_not_enumerate_corpus():
    body = (PROJECTION / GATEWAY / "SKILL.md").read_text(encoding="utf-8")
    registry = json.loads((ROOT / "ops" / "generated" / "skill-registry.json").read_text())
    leaked = [item["name"] for item in registry["skills"] if item["name"] in body]
    assert leaked == []
    assert "skill-route.json" not in body


# --- synthetic roots -----------------------------------------------------------


def test_mirrored_canonical_skill_fails(tmp_path: Path):
    root = copy_root(tmp_path)
    shutil.copytree(
        root / "skills" / "l9-ynp",
        root / "environment" / "agents" / "adapters" / "cursor" / "skills" / "l9-ynp",
    )
    result = validator.validate(root)
    assert not result["ok"]
    assert any("mirrored" in err or "exactly" in err for err in result["errors"])


def test_symlink_escape_into_corpus_fails(tmp_path: Path):
    root = copy_root(tmp_path)
    projection = root / "environment" / "agents" / "adapters" / "cursor" / "skills"
    os.symlink(root / "skills" / "l9-ynp", projection / "l9-linked")
    result = validator.validate(root)
    assert not result["ok"]
    assert any("symlink" in err for err in result["errors"])


def test_gateway_in_registry_fails(tmp_path: Path):
    root = copy_root(tmp_path)
    registry_path = root / "ops" / "generated" / "skill-registry.json"
    data = json.loads(registry_path.read_text())
    data["skills"].append(dict(data["skills"][0], name=GATEWAY))
    registry_path.write_text(json.dumps(data), encoding="utf-8")
    result = validator.validate(root)
    assert any(GATEWAY in err for err in result["errors"])


def test_legacy_plugin_manifest_fails_strict(tmp_path: Path):
    root = copy_root(tmp_path)
    plugin_path = root / ".cursor-plugin" / "plugin.json"
    plugin = json.loads(plugin_path.read_text())
    plugin["skills"] = "skills"
    plugin_path.write_text(json.dumps(plugin), encoding="utf-8")
    strict = validator.validate(root)
    assert any("plugin.skills" in err for err in strict["errors"])
    legacy = validator.validate(root, allow_legacy_manifest=True)
    assert not any("plugin.skills" in err for err in legacy["errors"])


def test_manifest_without_virtual_gateway_fails(tmp_path: Path):
    root = copy_root(tmp_path)
    manifest = root / "skills" / "AUTONOMY_MANIFEST.yaml"
    manifest.write_text(
        manifest.read_text().replace("mode: virtual_gateway", "mode: mirror"), encoding="utf-8"
    )
    result = validator.validate(root)
    assert any("virtual_gateway" in err for err in result["errors"])


def test_adding_canonical_skill_increments_registry_only(tmp_path: Path):
    root = copy_root(tmp_path)
    before = validator.validate(root)["facts"]
    add_synthetic_skills(root, 1)
    regenerate(root)
    after = validator.validate(root)
    assert after["ok"], after["errors"]
    assert after["facts"]["registry_skill_count"] == before["registry_skill_count"] + 1
    assert after["facts"]["canonical_skill_count"] == before["canonical_skill_count"] + 1
    assert after["facts"]["native_skill_count"] == before["native_skill_count"] == 1


@pytest.mark.parametrize("count", [1000])
def test_thousand_synthetic_skills_keep_native_count_one(tmp_path: Path, count: int):
    root = copy_root(tmp_path)
    names = add_synthetic_skills(root, count)
    regenerate(root)
    result = validator.validate(root)
    assert result["ok"], result["errors"][:5]
    assert result["facts"]["native_skill_count"] == 1
    assert result["facts"]["registry_skill_count"] >= count
    assert native_count(root) == 1
    registry = json.loads((root / "ops" / "generated" / "skill-registry.json").read_text())
    assert set(names) <= {item["name"] for item in registry["skills"]}
