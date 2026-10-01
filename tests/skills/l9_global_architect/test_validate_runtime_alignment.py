"""GAR v0.8.2 pack alignment and single-authority discovery contract.

Runs the pack-shipped runtime-alignment validator against the installed pack,
proves it fails closed on a mutated copy, and proves the repository registry
resolves exactly one GAR to the installed SKILL.md.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "skills" / "l9-global-architect"
VALIDATOR = PACK / "scripts" / "validate_runtime_alignment.py"
REGISTRY = REPO / "ops" / "generated" / "skill-registry.json"
PACK_VERSION = "0.8.2"


def _run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    # The pack validator treats __pycache__ as forbidden residue, so the
    # validator process must not write bytecode into the pack it inspects.
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(root / "scripts" / VALIDATOR.name), str(root)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def _frontmatter(skill_md: Path) -> dict:
    return yaml.safe_load(skill_md.read_text(encoding="utf-8").split("---")[1])


def test_installed_pack_passes_runtime_alignment() -> None:
    proc = _run_validator(PACK)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "GAR_RUNTIME_ALIGNMENT: PASS" in proc.stdout
    assert f"version: {PACK_VERSION}" in proc.stdout


def _bump_skill_version(root: Path) -> None:
    skill = root / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    skill.write_text(text.replace(f"version: {PACK_VERSION}", "version: 0.5.0"), encoding="utf-8")


def _drop_profile(root: Path) -> None:
    (root / "contracts" / "L9_ARCHITECTURE_PROFILE.yaml").unlink()


def _drop_signal_kernel(root: Path) -> None:
    (root / "references" / "reasoning-foursome" / "04_SIGNAL_LEVERAGE_KERNEL.md").unlink()


def _restore_stale_propagation_owner(root: Path) -> None:
    kernel = root / "references" / "reasoning-foursome" / "01_FIRST_ORDER_THINKING_KERNEL.md"
    text = kernel.read_text(encoding="utf-8")
    fixed = "propagate through the mesh? -> Signal Leverage\n"
    assert fixed in text
    kernel.write_text(
        text.replace(fixed, "propagate through the mesh? -> Leverage\n"), encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("mutate", "needle"),
    [
        pytest.param(_bump_skill_version, "SKILL.md release version", id="version-mismatch"),
        pytest.param(_drop_profile, "L9_ARCHITECTURE_PROFILE.yaml", id="missing-profile"),
        pytest.param(_drop_signal_kernel, "04_SIGNAL_LEVERAGE_KERNEL.md", id="missing-signal"),
        pytest.param(
            _restore_stale_propagation_owner,
            "propagation hand-off must resolve to Signal Leverage",
            id="stale-propagation-owner",
        ),
    ],
)
def test_validator_fails_closed_on_mutated_pack(tmp_path: Path, mutate, needle: str) -> None:
    copy = tmp_path / "l9-global-architect"
    shutil.copytree(PACK, copy, ignore=shutil.ignore_patterns("__pycache__"))
    mutate(copy)
    proc = _run_validator(copy)
    assert proc.returncode != 0, proc.stdout
    assert "FAIL:" in proc.stdout
    assert needle in proc.stdout


def test_skill_and_manifest_declare_same_release() -> None:
    meta = _frontmatter(PACK / "SKILL.md")
    manifest = yaml.safe_load((PACK / "runtime" / "MANIFEST.yaml").read_text(encoding="utf-8"))
    assert meta["name"] == "l9-global-architect"
    assert meta["disable-model-invocation"] is True
    assert str(meta["metadata"]["version"]) == PACK_VERSION
    assert manifest["manifest"]["name"] == "l9-global-architect"
    assert str(manifest["manifest"]["version"]) == PACK_VERSION
    bootloader = (PACK / "runtime" / manifest["manifest"]["human_bootloader"]).resolve()
    assert bootloader == (PACK / "SKILL.md").resolve()
    for ref in manifest["load_order"]:
        assert (PACK / ref).is_file(), ref


def test_registry_resolves_single_active_gar() -> None:
    from ops.skill_routing.materialize import resolve_skill_resource

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = [item for item in registry["skills"] if item["name"] == "l9-global-architect"]
    assert len(records) == 1
    record = records[0]
    assert record["invocation"] == "explicit_only"
    resolved = resolve_skill_resource("l9-global-architect", record, REPO, verify_digest=True)
    assert Path(resolved["skill_md"]) == (PACK / "SKILL.md").resolve()
    # No other registered skill may resolve into the GAR pack.
    others = [
        item["name"]
        for item in registry["skills"]
        if item["name"] != "l9-global-architect"
        and str(item.get("skill_md", "")).startswith("skills/l9-global-architect/")
    ]
    assert others == []
