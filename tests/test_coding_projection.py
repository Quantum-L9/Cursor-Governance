"""Tests for the repository-level coding projection consumer (ADR-021 bundle).

The authority is a synthetic git repository whose origin names the canonical owner, built
with the coding-agent pack's own test helpers so the bundle shape here is the one the pack
verifies. The consumer under test is ``tools/authority/verify_coding_projection.py`` plus the
``ops/scripts/coding_projection_status.py`` classifier; both delegate every digest, subject
and receipt check to ``skills/l9-coding-agent/scripts/verify_canonical_binding.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ops.scripts import coding_projection_status as status  # noqa: E402
from tools.authority import verify_coding_projection as consumer  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")

_SPEC = importlib.util.spec_from_file_location(
    "coding_agent_pack_tests",
    REPO / "skills/l9-coding-agent/tests/test_coding_agent_canonical_binding.py",
)
assert _SPEC and _SPEC.loader
pack = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pack)

BINDING = REPO / status.BINDING_PATH


def make_authority(tmp_path: Path) -> Path:
    root = tmp_path / "authority"
    (root / "semantics").mkdir(parents=True)
    for name, doc in pack.SEMANTICS.items():
        pack.write_semantics(root, name, doc)
    (root / "README.md").write_text("fixture\n")
    pack.git(root, "init", "-q")
    pack.git(root, "remote", "add", "origin", pack.ORIGIN)
    pack.commit_all(root, "fixture law")
    return root


def make_workspace(tmp_path: Path, authority: Path, bundle: Path | None) -> Path:
    """A repository root holding the shipped binding, the pack verifier, and the bundle."""
    repo = tmp_path / "repo"
    (repo / "governance/authority-bindings").mkdir(parents=True)
    binding = yaml.safe_load(BINDING.read_text())
    catalog = yaml.safe_load((authority / "semantics/projection_profiles.yaml").read_text())
    profile = next(
        p for p in catalog["projection_profiles"] if p["id"] == pack.verifier.PROFILE_REF
    )
    binding["upstream"]["profile_digest"] = pack.verifier.content_digest(profile)
    # The owner's decision for the fixture profile, at the fixture authority's main.
    binding["admission"]["decisions"] = [
        {
            **binding["admission"]["decisions"][0],
            "candidate_digest": binding["upstream"]["profile_digest"],
            "admitted_revision": pack.head(authority),
        }
    ]
    (repo / status.BINDING_PATH).write_text(yaml.safe_dump(binding, sort_keys=False))
    (repo / "skills").symlink_to(REPO / "skills", target_is_directory=True)
    if bundle is not None:
        (repo / consumer.BUNDLE_PATH).parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle, repo / consumer.BUNDLE_PATH)
    return repo


def classify(repo: Path, authority: Path | None, **kwargs: Any) -> dict[str, Any]:
    return status.classify(repo_root=repo, authority_root=authority, workspace=None, **kwargs)


def test_bound_against_local_origin_main(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    bundle = pack.build_bundle(authority, tmp_path / "bundle")
    repo = make_workspace(tmp_path, authority, bundle)
    result = classify(repo, authority)
    assert result["status"] == "BOUND", result
    assert result["components"] == ["invariants", "contracts", "authority_model"]
    assert result["projected_invariant_count"] == 2
    assert result["enforcement"] == "report_only"


def test_current_only_with_an_independent_main_record(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    assert classify(repo, authority, expect_main=pack.head(authority))["status"] == "CURRENT"
    disagree = classify(repo, authority, expect_main="0" * 40)
    assert disagree["status"] == "STALE" and "independent main record" in disagree["detail"]


def test_bound_when_main_moves_without_material_change(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    (authority / "README.md").write_text("unrelated\n")
    pack.commit_all(authority, "unrelated upstream commit")
    assert classify(repo, authority)["status"] == "BOUND"


def test_stale_when_a_bundled_source_changes_on_main(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    pack.write_semantics(
        authority, "contracts.yaml", {"contracts": pack.CONTRACTS["contracts"][:1]}
    )
    pack.commit_all(authority, "contracts changed")
    result = classify(repo, authority)
    assert result["status"] == "STALE" and "['contracts']" in result["detail"], result


def test_stale_when_the_pinned_profile_changes_on_main(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    catalog = yaml.safe_load((authority / "semantics/projection_profiles.yaml").read_text())
    catalog["projection_profiles"][0]["purpose"] = "changed"
    pack.write_semantics(authority, "projection_profiles.yaml", catalog)
    pack.commit_all(authority, "profile changed")
    result = classify(repo, authority)
    assert result["status"] == "STALE" and "'profile'" in result["detail"], result


def test_unverified_without_a_committed_bundle(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, None)
    result = classify(repo, authority)
    assert result["status"] == "UNVERIFIED" and "no committed bundle" in result["detail"]


def test_unverified_without_any_authority_checkout(tmp_path: Path, monkeypatch) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    monkeypatch.delenv(status.ENV_AUTHORITY_ROOT, raising=False)
    result = classify(repo, None)
    assert result["status"] == "UNVERIFIED" and "upstream not observed" in result["detail"]


def test_wrong_origin_is_rejected_not_trusted(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    pack.git(authority, "remote", "set-url", "origin", "https://github.com/someone/else")
    result = classify(repo, authority)
    assert result["status"] == "UNVERIFIED"
    assert (
        result["rejected_authority_roots"]
        and "origin is not" in result["rejected_authority_roots"][0]
    )


def test_bundle_revision_off_main_is_blocked(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    (authority / "README.md").write_text("local only\n")
    local_only = pack.commit_all(authority, "never published", publish=False)
    bundle = pack.build_bundle(authority, tmp_path / "bundle", revision=local_only)
    repo = make_workspace(tmp_path, authority, bundle)
    result = classify(repo, authority)
    assert result["status"] == "BLOCKED" and "is not on" in result["detail"], result


def test_tampered_component_is_blocked(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    bundle = pack.build_bundle(authority, tmp_path / "bundle")
    target = bundle / "projections/authority_model.projection.json"
    target.write_bytes(target.read_bytes() + b" ")
    repo = make_workspace(tmp_path, authority, bundle)
    result = classify(repo, authority)
    assert result["status"] == "BLOCKED" and "REJECTED BUNDLE_BYTES_MISMATCH" in result["detail"]


def test_components_must_match_the_binding(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    bundle = pack.build_bundle(authority, tmp_path / "bundle", classes=["invariants", "contracts"])
    repo = make_workspace(tmp_path, authority, bundle)
    result = classify(repo, authority)
    assert result["status"] == "BLOCKED" and "source classes" in result["detail"]


def test_unreadable_binding_is_blocked(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / status.BINDING_PATH).parent.mkdir(parents=True)
    (repo / status.BINDING_PATH).write_text("schema: something-else\n")
    result = classify(repo, None)
    assert result["status"] == "BLOCKED" and "binding schema" in result["detail"]


def test_shipped_binding_is_a_report_only_bundle_consumer() -> None:
    binding = yaml.safe_load(BINDING.read_text())
    assert binding["schema"] == status.BINDING_SCHEMA
    assert binding["enforcement"] == {
        "mode": "report_only",
        "statuses": list(status.STATUSES),
        "blocks_mutation": False,
    }
    assert Path(binding["bundle"]["path"]) == consumer.BUNDLE_PATH
    assert binding["bundle"]["lock_schema"] == pack.verifier.LOCK_SCHEMA
    assert Path(binding["verification"]["verifier"]) == consumer.VERIFIER_PATH
    assert (REPO / binding["verification"]["verifier"]).is_file()
    assert (REPO / binding["bundle"]["driver"]).is_file()
    assert (REPO / binding["bundle"]["trusted_replay"]).is_file()
    assert (REPO / binding["bundle"]["ci"]).is_file()
    assert binding["upstream"]["source_classes"] == ["invariants", "contracts", "authority_model"]
    # The committed bundle's inventory agrees with the binding's pins.
    lock = consumer.read_lock(REPO / consumer.BUNDLE_PATH)
    assert lock["schema"] == binding["bundle"]["lock_schema"]
    assert lock["projection_profile"]["digest"] == binding["upstream"]["profile_digest"]
    assert [c["source_class"] for c in lock["components"]] == binding["upstream"]["source_classes"]
    # No second convention or publisher transport survives in the consumer.
    text = (REPO / "tools/authority/verify_coding_projection.py").read_text()
    for retired in ("projections-index", "refs/remotes/origin/projections", "index.json"):
        assert retired not in text, retired


def _rewrite_binding(repo: Path, change: Any) -> None:
    binding = yaml.safe_load((repo / status.BINDING_PATH).read_text())
    change(binding)
    (repo / status.BINDING_PATH).write_text(yaml.safe_dump(binding, sort_keys=False))


def test_admission_is_judged_by_the_shared_resolver(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    result = classify(repo, authority)
    assert result["status"] == "BOUND", result
    assert result["admission"] == {"status": "ADMITTED_AND_CURRENT", "reason": "ADMITTED"}


def test_no_admission_decision_is_unverified(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    _rewrite_binding(repo, lambda b: b["admission"].update(decisions=[]))
    result = classify(repo, authority)
    assert result["status"] == "UNVERIFIED" and "no admission decision" in result["detail"]
    assert result["admission"]["reason"] == "ADMISSION_DECISION_RECORD_ABSENT"


def test_a_decision_for_another_digest_is_blocked(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    _rewrite_binding(
        repo,
        lambda b: b["admission"]["decisions"][0].update(candidate_digest="sha256:" + "0" * 64),
    )
    result = classify(repo, authority)
    assert result["status"] == "BLOCKED" and "not admitted" in result["detail"], result
    assert result["admission"]["reason"] == "ADMISSION_DECISION_SUBJECT_MISMATCH"


def test_an_admitted_revision_not_fetched_is_unverified_not_refused(tmp_path: Path) -> None:
    authority = make_authority(tmp_path)
    repo = make_workspace(tmp_path, authority, pack.build_bundle(authority, tmp_path / "bundle"))
    _rewrite_binding(
        repo, lambda b: b["admission"]["decisions"][0].update(admitted_revision="1" * 40)
    )
    result = classify(repo, authority)
    assert result["status"] == "UNVERIFIED" and "is not fetched" in result["detail"], result


def test_shipped_admission_decision_binds_the_pinned_profile() -> None:
    binding = yaml.safe_load(BINDING.read_text())
    (decision,) = binding["admission"]["decisions"]
    assert decision["candidate_ref"] == binding["upstream"]["profile_ref"]
    assert decision["candidate_digest"] == binding["upstream"]["profile_digest"]
    assert decision["admitted_revision"] == binding["upstream"]["admitted_revision"]
    assert decision["decision"] == "admit" and decision["authority_ref"]


def test_status_cli_is_report_only_by_default(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO / "ops/scripts/coding_projection_status.py"), "--format", "line"],
        capture_output=True,
        text=True,
        env={**os.environ, status.ENV_AUTHORITY_ROOT: str(tmp_path / "absent")},
        cwd=str(tmp_path),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert (
        completed.stdout.startswith("coding projection: ") and "(report-only)" in completed.stdout
    )
    assert (
        json.loads(
            subprocess.run(
                [
                    sys.executable,
                    str(REPO / "ops/scripts/coding_projection_status.py"),
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, status.ENV_AUTHORITY_ROOT: str(tmp_path / "absent")},
                cwd=str(tmp_path),
                check=False,
            ).stdout
        )["status"]
        in status.STATUSES
    )
