"""Materialization + filesystem security (VSP phase 4)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from ops.skill_routing import materialize as mat  # noqa: E402
from ops.skill_routing import registry as reg  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_root(tmp_path: Path, names: list[str]) -> Path:
    root = tmp_path / "gov"
    (root / "ops" / "generated").mkdir(parents=True)
    records = []
    for name in names:
        skill_dir = root / "skills" / name
        skill_dir.mkdir(parents=True)
        body = f"---\nname: {name}\n---\n# {name}\n"
        (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
        records.append(
            {
                "name": name,
                "path": f"skills/{name}",
                "skill_md": f"skills/{name}/SKILL.md",
                "skill_sha256": _sha(body.encode("utf-8")),
                "invocation": "model_allowed" if name != "l9-locked" else "explicit_only",
            }
        )
    data = {
        "schema_version": 2,
        "generation_id": "1" * 64,
        "source_manifest_sha256": "2" * 64,
        "source_skill_corpus_sha256": "3" * 64,
        "routing": {"routes": []},
        "skills": records,
    }
    (root / reg.REGISTRY_REL).write_text(json.dumps(data), encoding="utf-8")
    return root


def decision(primary: str, *supporting: str) -> dict:
    return {"route_id": "r", "primary": primary, "supporting": list(supporting), "score": 8}


def test_good_path(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a", "l9-b", "l9-c"])
    loaded = reg.load_registry(root)
    out = mat.materialize_route(decision("l9-a", "l9-b", "l9-c"), loaded)
    assert out["primary"]["name"] == "l9-a"
    assert Path(out["primary"]["skill_md"]).is_file()
    assert Path(out["primary"]["skill_md"]).name == "SKILL.md"
    assert out["primary"]["invocation"] == "model_allowed"
    assert out["primary"]["sha256"] == loaded.index["l9-a"]["skill_sha256"]
    assert [item["name"] for item in out["supporting"]] == ["l9-b", "l9-c"]


def test_live_registry_materializes_every_skill():
    loaded = reg.load_registry(ROOT)
    for name in loaded.index:
        out = mat.materialize_route(decision(name), loaded)
        assert Path(out["primary"]["skill_md"]).is_relative_to(loaded.skills_root)


def test_missing_skill_md_fails_closed(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a"])
    loaded = reg.load_registry(root)
    (root / "skills" / "l9-a" / "SKILL.md").unlink()
    with pytest.raises(mat.MaterializationError, match="missing"):
        mat.materialize_route(decision("l9-a"), loaded)


def test_corrupt_skill_md_fails_closed(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a"])
    loaded = reg.load_registry(root)
    (root / "skills" / "l9-a" / "SKILL.md").write_text("tampered", encoding="utf-8")
    with pytest.raises(mat.MaterializationError, match="digest"):
        mat.materialize_route(decision("l9-a"), loaded)
    out = mat.materialize_route(decision("l9-a"), loaded, verify_digest=False)
    assert out["primary"]["name"] == "l9-a"


def test_unknown_primary_and_support(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a"])
    loaded = reg.load_registry(root)
    with pytest.raises(mat.MaterializationError, match="unknown skill"):
        mat.materialize_route(decision("l9-ghost"), loaded)
    with pytest.raises(mat.MaterializationError, match="unknown skill"):
        mat.materialize_route(decision("l9-a", "l9-ghost"), loaded)


def test_support_cap_and_overlap(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a", "l9-b", "l9-c", "l9-d"])
    loaded = reg.load_registry(root)
    with pytest.raises(mat.MaterializationError, match="supports"):
        mat.materialize_route(decision("l9-a", "l9-b", "l9-c", "l9-d"), loaded)
    with pytest.raises(mat.MaterializationError, match="overlap"):
        mat.materialize_route(decision("l9-a", "l9-a"), loaded)


@pytest.mark.parametrize(
    "bad_path",
    ["/etc/passwd", "skills/l9-a/../../SKILL.md", "skills/l9-a/README.md", "skills/l9-b/SKILL.md"],
)
def test_bad_record_paths_rejected(tmp_path: Path, bad_path: str):
    root = make_root(tmp_path, ["l9-a", "l9-b"])
    record = dict(reg.load_registry(root).index["l9-a"])
    record["skill_md"] = bad_path
    with pytest.raises(mat.MaterializationError):
        mat.resolve_skill_resource("l9-a", record, root)


def test_symlink_escape_rejected(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a"])
    outside = tmp_path / "outside"
    outside.mkdir()
    foreign = outside / "SKILL.md"
    foreign.write_text("---\nname: l9-a\n---\n", encoding="utf-8")
    target = root / "skills" / "l9-a" / "SKILL.md"
    target.unlink()
    os.symlink(foreign, target)
    record = dict(reg.load_registry(root).index["l9-a"])
    record["skill_sha256"] = _sha(foreign.read_bytes())
    with pytest.raises(mat.MaterializationError, match="escapes"):
        mat.resolve_skill_resource("l9-a", record, root)


def test_internal_symlink_within_root_allowed_when_registry_matches(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a"])
    real = root / "skills" / "l9-a" / "SKILL.md"
    alias_dir = root / "skills" / "l9-alias"
    alias_dir.mkdir()
    os.symlink(real, alias_dir / "SKILL.md")
    record = {
        "name": "l9-alias",
        "skill_md": "skills/l9-alias/SKILL.md",
        "skill_sha256": _sha(real.read_bytes()),
        "invocation": "model_allowed",
    }
    out = mat.resolve_skill_resource("l9-alias", record, root)
    assert Path(out["skill_md"]) == real.resolve()


def test_raw_dict_registry_requires_root(tmp_path: Path):
    root = make_root(tmp_path, ["l9-a"])
    data = json.loads((root / reg.REGISTRY_REL).read_text())
    with pytest.raises(mat.MaterializationError):
        mat.materialize_route(decision("l9-a"), data)
    out = mat.materialize_route(decision("l9-a"), data, root)
    assert out["primary"]["name"] == "l9-a"
