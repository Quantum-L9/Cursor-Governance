"""Coding projection: consumer verification of producer-emitted pairs.

Cursor-Governance verifies ``l9.projection/coding-agent-execution@1`` and never
produces it. Every case runs against a throwaway git authority shaped like
Quantum-L9/.github: canonical sources and schemas on ``main``, and a
``projections`` branch carrying ``index.json`` plus one pair per source class,
built here by a test-only stand-in for ``l9-semantic-compiler`` following the
publisher's documented conventions. Acceptance: reject wrong producer role,
wrong origin, tampering, forged or partial receipts, revisions off main and
changed inputs; BOUND/CURRENT only with observed proof.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from ops.scripts import coding_projection_status as status
from tools.authority import verify_coding_projection as verifier

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "coding_projection"
ORIGIN = "https://github.com/Quantum-L9/.github"
PROFILE_REF = "l9.projection/coding-agent-execution@1"
CLASSES = ["authority_model", "contracts", "invariants"]

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
        "output": {"schema": "l9.projection.coding-agent-execution/v1"},
        "forbidden": ["execution_publication_or_merge_authority_grant"],
    }


def _catalog(profile: dict) -> dict:
    return {
        "artifact_id": "l9.projection-profile-catalog/global@1",
        "canonical": True,
        "source_classes": {
            "invariants": {"canonical_artifact": "invariants.yaml"},
            "contracts": {"canonical_artifact": "contracts.yaml"},
            "authority_model": {"canonical_artifact": "authority_model.yaml"},
        },
        "projection_profiles": [profile],
    }


def _source(source_id: str, path: str) -> dict:
    return {"id": source_id, "path": path, "canonical": True, "projection_allowed": True}


LEDGERS = {
    "semantics/invariants.yaml": {
        "artifact_id": "l9.invariants/global@1",
        "invariants": [{"id": "L9-AUTH-001", "statement": "authority is explicit"}],
    },
    "semantics/contracts.yaml": {
        "artifact_id": "l9.contracts/global@1",
        "contracts": [{"id": "l9.contract/projection@1"}],
    },
    "semantics/authority_model.yaml": {
        "artifact_id": "l9.authority-model/global@1",
        "agent_authority": {"may": ["implement"]},
    },
    "semantics/canonical_sources.yaml": {
        "authority": {"owner": "Quantum-L9/.github"},
        "sources": [
            _source("l9.source/invariants@1", "semantics/invariants.yaml"),
            _source("l9.source/contracts@1", "semantics/contracts.yaml"),
            _source("l9.source/authority-model@1", "semantics/authority_model.yaml"),
            _source(verifier.CATALOG_REF, "semantics/projection_profiles.yaml"),
        ],
    },
}


def _git(cwd: Path, *args: str, data: bytes | None = None) -> str:
    out = subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        capture_output=True,
        input=data,
        check=True,
    )
    return out.stdout.decode().strip()


def _commit_main(root: Path, files: dict[str, object], message: str) -> str:
    branch = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", "refs/heads/main"],
        capture_output=True,
        check=False,
    )
    if branch.returncode == 0:  # main is unborn until the first commit
        _git(root, "checkout", "-q", "main")
    for rel, value in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else yaml.safe_dump(value, sort_keys=False)
        path.write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", message)
    sha = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", "refs/remotes/origin/main", sha)
    return sha


def _pair(root: Path, revision: str, source_class: str, *, compiler: str = verifier.PRODUCER):
    """A stand-in compiler pair following the publisher's conventions."""
    pins = verifier.compute_pins(root, revision, PROFILE_REF, source_class)
    payload = {"source_class": source_class, "selectors": pins["selectors"]}
    artifact = {
        "schema": verifier.ARTIFACT_SCHEMA,
        "source_ref": pins["source_ref"],
        "source_digest": pins["source_digest"],
        "projection_profile_ref": PROFILE_REF,
        "projection_profile_digest": pins["profile_digest"],
        "payload": payload,
        "projection_digest": verifier.digest(payload),
        "generated_by": {"compiler": compiler, "version": "1.0.0"},
    }
    body = {
        "schema": verifier.RECEIPT_SCHEMA,
        "receipt_identity": "pending",
        "receipt_type": verifier.RECEIPT_TYPE,
        "exact_subject_ref": PROFILE_REF,
        "claim": "projection",
        "operation": "projection",
        "inputs": [
            {"ref": pins["source_ref"], "digest": pins["source_digest"]},
            {"ref": verifier.CATALOG_REF, "digest": pins["catalog_digest"]},
        ],
        "profile": {"ref": PROFILE_REF, "digest": pins["profile_digest"]},
        "output": {
            "ref": f"{PROFILE_REF}#{source_class}",
            "digest": artifact["projection_digest"],
        },
        "governing_coordinates": {
            "source_class": source_class,
            "selectors": pins["selectors"],
            "canonical_source_registry_digest": pins["registry_digest"],
            "authority_owner": verifier.OWNER_REPOSITORY,
            "authority_revision": revision,
        },
        "result": "pass",
        "verification_basis": {"basis": "test"},
        "producer_identity": {"compiler": compiler, "version": "1.0.0"},
    }
    body["receipt_identity"] = "l9.receipt-instance/" + verifier.digest(body)[7:]
    receipt = {**body, "receipt_digest": verifier.digest(body)}
    return (
        json.dumps(artifact, sort_keys=True).encode(),
        json.dumps(receipt, sort_keys=True).encode(),
    )


def _publish(
    root: Path,
    revision: str,
    pairs: dict[str, tuple[bytes, bytes]],
    *,
    mutate_entries=None,
    drop: str | None = None,
) -> str:
    """Write the projections branch (index + pairs) as one orphan commit.

    ``mutate_entries`` edits the index entries and ``drop`` omits one stored
    file, to model a corrupt index or a partial publication.
    """
    entries, files = {}, {}
    for source_class, (artifact, receipt) in pairs.items():
        receipt_digest = json.loads(receipt)["receipt_digest"]
        base = f"pairs/{source_class}/{receipt_digest[7:]}"
        files[f"{base}/projection.json"] = artifact
        files[f"{base}/receipt.json"] = receipt
        pins = verifier.compute_pins(root, revision, PROFILE_REF, source_class)
        entries[f"{PROFILE_REF}#{source_class}"] = {
            "current": {
                "pair": base,
                "files": {
                    "projection.json": verifier.digest_bytes(artifact),
                    "receipt.json": verifier.digest_bytes(receipt),
                },
                "receipt_digest": receipt_digest,
                "source_digest": pins["source_digest"],
                "profile_digest": pins["profile_digest"],
            },
            "history": [],
        }
    if mutate_entries is not None:
        mutate_entries(entries)
    if drop is not None:
        files = {path: data for path, data in files.items() if not path.endswith(drop)}
    files["index.json"] = json.dumps(
        {"transport_format": verifier.INDEX_FORMAT, "entries": entries}, indent=2
    ).encode()
    tree_input = []
    for path, data in sorted(files.items()):
        blob = _git(root, "hash-object", "-w", "--stdin", data=data)
        tree_input.append(f"100644 blob {blob}\t{path}")
    # mktree builds one level; build nested paths through a temporary index.
    env_index = root / ".git" / "projections-index"
    for line in tree_input:
        mode_type_blob, path = line.split("\t")
        mode, _type, blob = mode_type_blob.split()
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "update-index",
                "--add",
                "--cacheinfo",
                f"{mode},{blob},{path}",
            ],
            check=True,
            env={"GIT_INDEX_FILE": str(env_index), "PATH": "/usr/bin:/bin"},
        )
    tree = (
        subprocess.run(
            ["git", "-C", str(root), "write-tree"],
            check=True,
            capture_output=True,
            env={"GIT_INDEX_FILE": str(env_index), "PATH": "/usr/bin:/bin"},
        )
        .stdout.decode()
        .strip()
    )
    env_index.unlink()
    commit = _git(root, "commit-tree", tree, "-m", "publish")
    _git(root, "update-ref", "refs/remotes/origin/projections", commit)
    return commit


@pytest.fixture
def authority(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "authority"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "remote", "add", "origin", ORIGIN)
    files: dict[str, object] = dict(LEDGERS)
    files["semantics/projection_profiles.yaml"] = _catalog(_profile())
    for name in ("projection_artifact.schema.yaml", "compiler_receipt.schema.yaml"):
        files[f"semantics/{name}"] = (FIXTURES / name).read_text(encoding="utf-8")
    return root, _commit_main(root, files, "admit profile")


def _consumer(tmp_path: Path, profile: dict | None = None) -> Path:
    repo = tmp_path / "consumer"
    binding = yaml.safe_load((ROOT / status.BINDING_PATH).read_text(encoding="utf-8"))
    binding["upstream"]["profile_digest"] = verifier.digest(profile or _profile())
    path = repo / status.BINDING_PATH
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(binding, sort_keys=False), encoding="utf-8")
    return repo


def _all_pairs(root: Path, revision: str, **kwargs) -> dict[str, tuple[bytes, bytes]]:
    return {c: _pair(root, revision, c, **kwargs) for c in CLASSES}


def _classify(repo: Path, root: Path | None, expect_main: str | None = None) -> dict:
    return status.classify(
        repo_root=repo, workspace=None, authority_root=root, expect_main=expect_main
    )


def test_current_only_with_an_independent_main_record(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha))
    repo = _consumer(tmp_path)
    assert _classify(repo, root, expect_main=sha)["status"] == "CURRENT"
    # The same proof without an independent record is BOUND, never CURRENT.
    result = _classify(repo, root)
    assert result["status"] == "BOUND" and "not independently confirmed" in result["detail"]


def test_independent_record_that_disagrees_is_stale(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha))
    assert _classify(_consumer(tmp_path), root, expect_main="f" * 40)["status"] == "STALE"


def test_unverified_when_nothing_is_published(authority, tmp_path) -> None:
    root, _sha = authority
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "UNVERIFIED" and "no producer pair published" in result["detail"]


def test_unverified_when_one_class_is_unpublished(authority, tmp_path) -> None:
    root, sha = authority
    pairs = _all_pairs(root, sha)
    pairs.pop("contracts")
    _publish(root, sha, pairs)
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "UNVERIFIED" and "contracts" in result["detail"]


def test_unverified_without_any_authority_checkout(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv(status.ENV_AUTHORITY_ROOT, raising=False)
    result = _classify(_consumer(tmp_path), None)
    assert result["status"] == "UNVERIFIED" and "upstream not observed" in result["detail"]


def test_wrong_origin_is_rejected_not_trusted(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha))
    _git(root, "remote", "set-url", "origin", "https://github.com/someone/.github")
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "UNVERIFIED"
    assert "origin is not Quantum-L9/.github" in result["rejected_authority_roots"][0]


def test_a_workflows_folder_is_never_mistaken_for_the_authority(tmp_path) -> None:
    workspace = tmp_path / "some-repo"
    (workspace / ".github" / "workflows").mkdir(parents=True)
    _git(workspace, "init", "-q")
    _git(workspace, "remote", "add", "origin", ORIGIN)
    result = status.classify(repo_root=_consumer(tmp_path), workspace=workspace)
    assert result["status"] == "UNVERIFIED"
    assert any("top level" in r for r in result["rejected_authority_roots"])


def test_wrong_producer_role_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha, compiler="cursor-governance"))
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "BLOCKED" and "producer role" in result["detail"]


def test_tampered_payload_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    pairs = _all_pairs(root, sha)
    artifact = json.loads(pairs["invariants"][0])
    artifact["payload"]["selectors"] = ["forged"]
    pairs["invariants"] = (json.dumps(artifact).encode(), pairs["invariants"][1])
    _publish(root, sha, pairs)
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "BLOCKED" and "tampered" in result["detail"]


def test_forged_receipt_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    pairs = _all_pairs(root, sha)
    receipt = json.loads(pairs["contracts"][1])
    receipt["claim"] = "forged claim"
    pairs["contracts"] = (pairs["contracts"][0], json.dumps(receipt).encode())
    _publish(root, sha, pairs)
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "BLOCKED" and "receipt digest" in result["detail"]


def test_index_that_misnames_a_file_is_blocked(authority, tmp_path) -> None:
    root, sha = authority

    def corrupt(entries: dict) -> None:
        current = entries[f"{PROFILE_REF}#authority_model"]["current"]
        current["files"]["projection.json"] = verifier.digest_bytes(b"another file")

    _publish(root, sha, _all_pairs(root, sha), mutate_entries=corrupt)
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "BLOCKED" and "does not match the index" in result["detail"]


def test_partial_publication_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha), drop="receipt.json")
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "BLOCKED" and "absent" in result["detail"]


def test_pair_bound_to_a_revision_off_main_is_blocked(authority, tmp_path) -> None:
    root, sha = authority
    _git(root, "checkout", "-q", "-b", "side")
    (root / "SIDE.txt").write_text("side branch\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "side")
    side = _git(root, "rev-parse", "HEAD")
    _publish(root, side, _all_pairs(root, side))
    _git(root, "update-ref", "refs/remotes/origin/main", sha)
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "BLOCKED" and "not on main" in result["detail"]


def test_stale_when_a_source_changes_after_publication(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha))
    changed = yaml.safe_load(yaml.safe_dump(LEDGERS["semantics/invariants.yaml"]))
    changed["invariants"][0]["statement"] = "authority is explicit and narrower"
    _commit_main(root, {"semantics/invariants.yaml": changed}, "edit invariant")
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "STALE" and "invariants" in result["detail"]


def test_bound_when_main_moves_without_material_change(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha))
    _commit_main(root, {"README.md": "unrelated\n"}, "unrelated change")
    assert _classify(_consumer(tmp_path), root)["status"] == "BOUND"


def test_stale_when_the_pinned_profile_changes(authority, tmp_path) -> None:
    root, sha = authority
    _publish(root, sha, _all_pairs(root, sha))
    _commit_main(
        root,
        {"semantics/projection_profiles.yaml": _catalog(_profile(invariant="L9-OTHER-001"))},
        "change profile",
    )
    result = _classify(_consumer(tmp_path), root)
    assert result["status"] == "STALE" and "rebind" in result["detail"]


def test_unreadable_binding_is_blocked(tmp_path) -> None:
    repo = tmp_path / "consumer"
    (repo / status.BINDING_PATH).parent.mkdir(parents=True)
    (repo / status.BINDING_PATH).write_text("schema: something-else\n", encoding="utf-8")
    assert status.classify(repo_root=repo)["status"] == "BLOCKED"


def test_shipped_binding_is_a_report_only_consumer() -> None:
    binding = status.load_binding(ROOT / status.BINDING_PATH)
    assert binding["enforcement"] == {
        "mode": "report_only",
        "statuses": list(status.STATUSES),
        "blocks_mutation": False,
    }
    assert binding["publication"]["producer"] == verifier.PRODUCER
    assert sorted(binding["upstream"]["source_classes"]) == CLASSES
    # The consumer never ships a producer or produced output.
    assert not (ROOT / "tools" / "authority" / "project_coding_projection.py").exists()
    assert not (ROOT / "generated" / "governance" / "coding_projection").exists()


def test_status_cli_is_report_only_by_default(tmp_path, capsys, monkeypatch) -> None:
    monkeypatch.delenv(status.ENV_AUTHORITY_ROOT, raising=False)
    assert status.main(["--workspace", str(tmp_path)]) == 0
    assert capsys.readouterr().out.startswith("coding projection: ")
