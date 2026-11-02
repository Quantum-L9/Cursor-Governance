"""Registry v2 loading / validation (VSP phase 1-2)."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.skill_routing import registry as reg  # noqa: E402

LIVE = ROOT / "ops" / "generated" / "skill-registry.json"
BUILDER = ROOT / "ops" / "scripts" / "build_claude_skill_registry.py"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_root(tmp_path: Path, names: list[str]) -> Path:
    root = tmp_path / "gov"
    (root / "ops" / "generated").mkdir(parents=True)
    records = []
    for name in names:
        skill_dir = root / "skills" / name
        skill_dir.mkdir(parents=True)
        body = f"---\nname: {name}\ndescription: {name} use when testing\n---\n# {name}\n"
        (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
        records.append(
            {
                "name": name,
                "path": f"skills/{name}",
                "skill_md": f"skills/{name}/SKILL.md",
                "skill_sha256": _sha(body.encode("utf-8")),
                "invocation": "model_allowed",
                "description": f"{name} use when testing",
                "when_to_use": "",
                "reason": "",
                "composition_role": "general",
                "disable_model_invocation": False,
                "user_invocable": True,
            }
        )
    data = {
        "schema_version": 2,
        "generation_id": "1" * 64,
        "source": "skills/AUTONOMY_MANIFEST.yaml",
        "source_manifest_sha256": "2" * 64,
        "source_skill_corpus_sha256": "3" * 64,
        "routing": {"routes": [], "force_threshold": 8, "advisory_threshold": 6},
        "skills": records,
    }
    (root / reg.REGISTRY_REL).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return root


def write(root: Path, data: dict) -> None:
    (root / reg.REGISTRY_REL).write_text(json.dumps(data), encoding="utf-8")


def test_live_registry_is_valid_v2():
    loaded = reg.load_registry(ROOT, check_files=True)
    assert loaded.data["schema_version"] == 2
    assert len(loaded.index) == len(loaded.skills)
    assert loaded.generation_id == _sha(
        f"{loaded.source_manifest_sha256}:{loaded.source_skill_corpus_sha256}".encode()
    )
    for record in loaded.skills:
        assert record["skill_md"] == f"skills/{record['name']}/SKILL.md"
        assert _sha((ROOT / record["skill_md"]).read_bytes()) == record["skill_sha256"]


def test_live_registry_names_equal_canonical_corpus():
    loaded = reg.load_registry(ROOT)
    on_disk = sorted(
        path.name
        for path in (ROOT / "skills").iterdir()
        if path.is_dir() and not path.name.startswith("_") and (path / "SKILL.md").is_file()
    )
    assert sorted(loaded.index) == on_disk


def test_load_and_index(tmp_path: Path):
    root = make_root(tmp_path, ["l9-one", "l9-two"])
    loaded = reg.load_registry(root)
    assert set(loaded.index) == {"l9-one", "l9-two"}
    assert loaded.resolve_skill_record("l9-two")["skill_md"] == "skills/l9-two/SKILL.md"
    assert loaded.identity()["generation_id"] == "1" * 64
    with pytest.raises(reg.RegistryError):
        loaded.resolve_skill_record("l9-missing")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.__setitem__("schema_version", 1),
        lambda d: d.pop("generation_id"),
        lambda d: d.__setitem__("generation_id", "not-hex"),
        lambda d: d.__setitem__("skills", []),
        lambda d: d["skills"].append(copy.deepcopy(d["skills"][0])),
        lambda d: d["skills"][0].__setitem__("path", "skills/other"),
        lambda d: d["skills"][0].__setitem__("skill_md", "/etc/passwd"),
        lambda d: d["skills"][0].__setitem__("skill_md", "skills/l9-one/../SKILL.md"),
        lambda d: d["skills"][0].__setitem__("skill_sha256", "zz"),
        lambda d: d["skills"][0].__setitem__("invocation", "always"),
        lambda d: d["skills"][0].__setitem__("name", "not-l9"),
        lambda d: d["routing"]["routes"].append({"id": "x", "primary": "l9-ghost"}),
    ],
)
def test_invalid_registry_rejected(tmp_path: Path, mutate):
    root = make_root(tmp_path, ["l9-one", "l9-two"])
    data = json.loads((root / reg.REGISTRY_REL).read_text())
    mutate(data)
    write(root, data)
    with pytest.raises(reg.RegistryError):
        reg.load_registry(root)


def test_corrupt_and_missing_registry_rejected(tmp_path: Path):
    root = make_root(tmp_path, ["l9-one"])
    (root / reg.REGISTRY_REL).write_text("{not json", encoding="utf-8")
    with pytest.raises(reg.RegistryError):
        reg.load_registry(root)
    (root / reg.REGISTRY_REL).unlink()
    with pytest.raises(reg.RegistryError):
        reg.load_registry(root)


def test_check_files_rejects_deleted_skill(tmp_path: Path):
    root = make_root(tmp_path, ["l9-one"])
    (root / "skills" / "l9-one" / "SKILL.md").unlink()
    reg.load_registry(root)  # shape-only load stays cheap
    with pytest.raises(reg.RegistryError):
        reg.load_registry(root, check_files=True)


def test_resolve_root_prefers_env(tmp_path: Path, monkeypatch):
    root = make_root(tmp_path, ["l9-one"])
    monkeypatch.setenv("L9_GOVERNANCE_DIR", str(root))
    assert reg.resolve_governance_root() == root
    # Order is env → ~/.cursor-governance → ancestors of the start file. Point
    # HOME at an empty dir so a governed machine's home clone cannot satisfy
    # the lookup and the ancestor walk is what gets exercised.
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("L9_GOVERNANCE_DIR", str(tmp_path / "nope"))
    assert reg.resolve_governance_root(ROOT / "ops" / "skill_routing" / "registry.py") == ROOT


def test_generation_is_byte_deterministic():
    spec = importlib.util.spec_from_file_location("l9_build_registry_test", BUILDER)
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    first = builder.serialized(builder.build_registry(ROOT))
    second = builder.serialized(builder.build_registry(ROOT))
    assert first == second
    assert first.encode("utf-8") == LIVE.read_bytes()
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--root", str(ROOT), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
