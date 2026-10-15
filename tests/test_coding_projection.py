"""Coding projection: producer, integrity and SessionStart classifier.

Every case runs against a real throwaway git authority (a synthetic
Quantum-L9/.github with the same ledger shapes), so the proofs never depend on
this host's checkout or the network. Acceptance: reject wrong producer origin,
wrong profile, missing source, tampering, forged/partial receipt and changed
input; say BOUND/CURRENT only with observed proof; never upgrade from age.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from ops.scripts import coding_projection_status as status
from tools.authority import project_coding_projection as producer
from tools.authority.project_canonical_identity import ProjectionError

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://github.com/Quantum-L9/.github"
PROFILE_REF = "l9.projection/coding-agent-execution@1"
OUTPUT_SCHEMA = "l9.projection.coding-agent-execution/v1"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git(1) is required")


def _profile(invariant: str = "L9-AUTH-001") -> dict:
    return {
        "id": PROFILE_REF,
        "class": "runtime",
        "consumer": "Cursor-Governance",
        "purpose": "test profile",
        "sources": {
            "invariants": {"selectors": [f'$.invariants[?(@.id=="{invariant}")]']},
            "contracts": {"selectors": ['$.contracts[?(@.id=="l9.contract/projection@1")]']},
            "authority_model": {"selectors": ["$.agent_authority"]},
        },
        "output": {"schema": OUTPUT_SCHEMA},
        "forbidden": ["execution_publication_or_merge_authority_grant"],
    }


LEDGERS = {
    "semantics/invariants.yaml": {
        "artifact_id": "l9.invariants/global@1",
        "canonical": True,
        "invariants": [
            {"id": "L9-AUTH-001", "statement": "authority is explicit", "scope": "global"},
            {"id": "L9-OTHER-001", "statement": "not selected", "scope": "global"},
        ],
    },
    "semantics/contracts.yaml": {
        "artifact_id": "l9.contracts/global@1",
        "canonical": True,
        "contracts": [{"id": "l9.contract/projection@1", "scope": "global"}],
    },
    "semantics/authority_model.yaml": {
        "artifact_id": "l9.authority-model/global@1",
        "canonical": True,
        "agent_authority": {"may": ["implement"]},
        "human_authority": {"may": ["merge"]},
    },
    "semantics/canonical_sources.yaml": {
        "artifact_id": "l9.canonical-sources/global@1",
        "canonical": True,
        "sources": [
            {
                "id": "l9.source/invariants@1",
                "path": "semantics/invariants.yaml",
                "canonical": True,
                "projection_allowed": True,
            },
            {
                "id": "l9.source/contracts@1",
                "path": "semantics/contracts.yaml",
                "canonical": True,
                "projection_allowed": True,
            },
            {
                "id": "l9.source/authority-model@1",
                "path": "semantics/authority_model.yaml",
                "canonical": True,
                "projection_allowed": True,
            },
        ],
    },
}


def _git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def _commit(root: Path, files: dict[str, object], message: str) -> str:
    for rel, value in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", message)
    sha = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", "refs/remotes/origin/main", sha)
    return sha


@pytest.fixture
def authority(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "authority"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "remote", "add", "origin", ORIGIN)
    files = dict(LEDGERS)
    files["semantics/projection_profiles.yaml"] = {
        "artifact_id": "l9.projection-profile-catalog/global@1",
        "canonical": True,
        "projection_profiles": [_profile()],
    }
    return root, _commit(root, files, "admit profile")


def _consumer(tmp_path: Path, revision: str, profile: dict | None = None) -> Path:
    repo = tmp_path / "consumer"
    binding = yaml.safe_load((ROOT / producer.BINDING_PATH).read_text(encoding="utf-8"))
    binding["upstream"]["revision"] = revision
    binding["upstream"]["profile_digest"] = producer.canonical_digest(profile or _profile())
    path = repo / producer.BINDING_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")
    return repo


def _produce(repo: Path, authority_root: Path) -> int:
    return producer.main(
        [
            "--authority-root",
            str(authority_root),
            "--binding",
            str(repo / producer.BINDING_PATH),
            "--output-dir",
            str(repo / producer.OUTPUT_DIR),
        ]
    )


def _classify(repo: Path, authority_root: Path | None) -> dict:
    return status.classify(repo_root=repo, workspace=None, authority_root=authority_root)


def test_current_only_when_pinned_revision_is_observed_main(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    result = _classify(repo, root)
    assert result["status"] == "CURRENT", result
    assert "not fetched by this check" in result["detail"]


def test_bound_when_main_moved_without_touching_inputs(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    _commit(root, {"README.yaml": {"note": "unrelated"}}, "unrelated change")
    assert _classify(repo, root)["status"] == "BOUND"


def test_stale_when_a_selected_record_changes_upstream(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    changed = yaml.safe_load(yaml.safe_dump(LEDGERS["semantics/invariants.yaml"]))
    changed["invariants"][0]["statement"] = "authority is explicit and narrower"
    _commit(root, {"semantics/invariants.yaml": changed}, "edit selected invariant")
    result = _classify(repo, root)
    assert result["status"] == "STALE" and "rebind" in result["detail"]


def test_any_selected_ledger_byte_change_is_stale(authority, tmp_path) -> None:
    """PROJECTION-007: a source digest change marks the projection stale, even
    when the edited record is not one the profile selects."""
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    changed = yaml.safe_load(yaml.safe_dump(LEDGERS["semantics/invariants.yaml"]))
    changed["invariants"][1]["statement"] = "still not selected"
    _commit(root, {"semantics/invariants.yaml": changed}, "edit unselected invariant")
    assert _classify(repo, root)["status"] == "STALE"


def test_stale_when_the_profile_changes_upstream(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    catalog = {
        "artifact_id": "l9.projection-profile-catalog/global@1",
        "canonical": True,
        "projection_profiles": [_profile(invariant="L9-OTHER-001")],
    }
    _commit(root, {"semantics/projection_profiles.yaml": catalog}, "change profile")
    result = _classify(repo, root)
    assert result["status"] == "STALE" and "profile" in result["detail"]


def test_unverified_without_any_authority_checkout(authority, tmp_path, monkeypatch) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    monkeypatch.delenv(status.ENV_AUTHORITY_ROOT, raising=False)
    result = _classify(repo, None)
    assert result["status"] == "UNVERIFIED" and "upstream not observed" in result["detail"]


def test_wrong_origin_is_rejected_not_trusted(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    _git(root, "remote", "set-url", "origin", "https://github.com/someone/.github")
    result = _classify(repo, root)
    assert result["status"] == "UNVERIFIED"
    assert "not Quantum-L9/.github" in result["rejected_authority_roots"][0]
    assert _produce(repo, root) == 1


def test_unverified_when_pinned_commit_is_absent(authority, tmp_path) -> None:
    """A genuine Quantum-L9/.github checkout that lacks the pin proves nothing."""
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    other = tmp_path / "other-authority"
    other.mkdir()
    _git(other, "init", "-q")
    _git(other, "remote", "add", "origin", ORIGIN)
    _commit(other, {"README.yaml": {"note": "unrelated history"}}, "unrelated")
    result = _classify(repo, other)
    assert result["status"] == "UNVERIFIED" and "is not in" in result["detail"]


def test_a_workflows_folder_is_never_mistaken_for_the_authority(authority, tmp_path) -> None:
    """``<workspace>/.github`` in an ordinary repo is its workflows folder."""
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    workspace = tmp_path / "some-repo"
    (workspace / ".github" / "workflows").mkdir(parents=True)
    _git(workspace, "init", "-q")
    _git(workspace, "remote", "add", "origin", ORIGIN)
    result = status.classify(repo_root=repo, workspace=workspace, authority_root=None)
    assert result["status"] == "UNVERIFIED"
    assert any("top level" in r for r in result["rejected_authority_roots"])


def test_tampered_payload_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    path = repo / producer.OUTPUT_DIR / "invariants.projection.yaml"
    path.write_text(path.read_text().replace("authority is explicit", "authority is implied"))
    result = _classify(repo, None)
    assert result["status"] == "BLOCKED" and "tampered" in result["detail"]


def test_forged_receipt_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    path = repo / producer.OUTPUT_DIR / producer.RECEIPT_NAME
    path.write_text(path.read_text().replace("result: pass", "result: pass\ndiagnostics: []"))
    result = _classify(repo, None)
    assert result["status"] == "BLOCKED" and "receipt digest" in result["detail"]


def test_partial_receipt_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    (repo / producer.OUTPUT_DIR / "contracts.projection.yaml").unlink()
    assert _classify(repo, None)["status"] == "BLOCKED"


def test_self_consistent_forgery_is_caught_by_reproduction(authority, tmp_path) -> None:
    """Rewrite payload, its digest and the receipt: integrity passes, source does not."""
    root, sha = authority
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 0
    out = repo / producer.OUTPUT_DIR
    artifact = yaml.safe_load((out / "invariants.projection.yaml").read_text())
    artifact["payload"]["records"][0]["statement"] = "forged obligation"
    artifact["projection_digest"] = producer.canonical_digest(artifact["payload"])
    (out / "invariants.projection.yaml").write_text(yaml.safe_dump(artifact, sort_keys=False))
    receipt = yaml.safe_load((out / producer.RECEIPT_NAME).read_text())
    receipt["outputs"]["invariants.projection.yaml"] = artifact["projection_digest"]
    receipt["output"]["digest"] = producer.canonical_digest(receipt["outputs"])
    receipt.pop("receipt_digest")
    receipt["receipt_digest"] = producer.canonical_digest(receipt)
    (out / producer.RECEIPT_NAME).write_text(yaml.safe_dump(receipt, sort_keys=False))
    assert producer.check_integrity(out, producer.load_binding(repo / producer.BINDING_PATH)) == []
    assert _classify(repo, None)["status"] == "UNVERIFIED"
    result = _classify(repo, root)
    assert result["status"] == "BLOCKED" and "do not reproduce" in result["detail"]


def test_producer_rejects_a_profile_that_does_not_match_the_pin(authority, tmp_path) -> None:
    root, sha = authority
    repo = _consumer(tmp_path, sha, profile=_profile(invariant="L9-OTHER-001"))
    assert _produce(repo, root) == 1


def test_producer_rejects_missing_source(authority, tmp_path) -> None:
    root, _sha = authority
    _git(root, "rm", "-q", "semantics/contracts.yaml")
    _git(root, "-c", "user.email=t@example.com", "-c", "user.name=t", "commit", "-qm", "drop")
    sha = _git(root, "rev-parse", "HEAD")
    repo = _consumer(tmp_path, sha)
    assert _produce(repo, root) == 1


@pytest.mark.parametrize(
    "selector",
    ['$.invariants[?(@.statement=="x")]', "$..invariants", '$.invariants[?(@.id=="NOPE")]'],
)
def test_producer_rejects_non_exact_or_unresolved_selectors(selector) -> None:
    with pytest.raises(ProjectionError):
        producer._select(LEDGERS["semantics/invariants.yaml"], [selector], "invariants")


def test_committed_projection_is_internally_consistent() -> None:
    """The shipped outputs pass integrity with no upstream access at all."""
    binding = producer.load_binding(ROOT / producer.BINDING_PATH)
    assert producer.check_integrity(ROOT / producer.OUTPUT_DIR, binding) == []
    assert binding["enforcement"]["mode"] == "report_only"
    assert binding["enforcement"]["blocks_mutation"] is False


def test_status_cli_is_report_only_by_default(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.delenv(status.ENV_AUTHORITY_ROOT, raising=False)
    assert status.main(["--workspace", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("coding projection: ")
