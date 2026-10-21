"""Behavioral tests for `scripts/verify_canonical_binding.py`.

The authority root is a synthetic git repository whose origin names the
canonical owner. Artifacts and receipts are built here in the shape the
producer (`l9-semantic-compiler`) emits for one source of
`l9.projection/coding-agent-execution@1`: a record-preserving payload under
the selected section, an envelope digest over every field but the digest, and
a receipt whose output names `<profile>#<source>`. Every case runs without
invoking any producer. Upstream law in the fixture is illustrative, not a copy
of `.github`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import zlib
from pathlib import Path
from typing import Any

import pytest
import yaml

PACK = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "coding_agent_verify_canonical_binding", PACK / "scripts" / "verify_canonical_binding.py"
)
assert _SPEC and _SPEC.loader
verifier = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verifier)


def id_selector(invariant_id: str) -> str:
    return f'$.invariants[?(@.id=="{invariant_id}")]'


SELECTED = ["L9-FIXTURE-001", "L9-FIXTURE-002"]
OUTPUT_SCHEMA = "l9.projection.coding-agent-execution/v1"
CONTRACTS_REF = "l9.source/contracts@1"
AUTHORITY_MODEL_REF = "l9.source/authority-model@1"
PROFILE = {
    "id": verifier.PROFILE_REF,
    "class": verifier.PROFILE_CLASS,
    "consumer": verifier.PROFILE_CONSUMER,
    # Three classes like the admitted profile: only `invariants` is re-selected record for
    # record; the other two are verified as bundle components (bytes, digests, receipts).
    "sources": {
        "invariants": {"selectors": [id_selector(i) for i in SELECTED]},
        "contracts": {"selectors": ['$.contracts[?(@.id=="l9.contract/fixture@1")]']},
        "authority_model": {"selectors": ["$.agent_authority"]},
    },
    "output": {"schema": OUTPUT_SCHEMA},
}
INVARIANTS = {
    "invariants": [
        {"id": "L9-FIXTURE-001", "scope": "global", "rule": "fixture rule one"},
        {"id": "L9-FIXTURE-UNSELECTED", "scope": "global", "rule": "global but not selected"},
        {"id": "L9-FIXTURE-002", "scope": "global", "rule": "fixture rule two"},
        {"id": "L9-FIXTURE-LOCAL", "scope": "repository", "rule": "not selected"},
    ]
}
CONTRACTS = {
    "contracts": [
        {"id": "l9.contract/fixture@1", "purpose": "fixture contract"},
        {"id": "l9.contract/unselected@1", "purpose": "not selected"},
    ]
}
AUTHORITY_MODEL = {
    "agent_authority": {"rules": ["fixture agent rule"]},
    "distribution_authority": {"rules": ["excluded sibling section"]},
}
SEMANTICS = {
    "canonical_sources.yaml": {
        "sources": [
            {
                "id": verifier.SOURCE_REF,
                "path": "semantics/invariants.yaml",
                "canonical": True,
                "projection_allowed": True,
            },
            {
                "id": CONTRACTS_REF,
                "path": "semantics/contracts.yaml",
                "canonical": True,
                "projection_allowed": True,
            },
            {
                "id": AUTHORITY_MODEL_REF,
                "path": "semantics/authority_model.yaml",
                "canonical": True,
                "projection_allowed": True,
            },
        ]
    },
    "projection_profiles.yaml": {
        "source_classes": {
            "invariants": {"canonical_artifact": "invariants.yaml"},
            "contracts": {"canonical_artifact": "contracts.yaml"},
            "authority_model": {"canonical_artifact": "authority_model.yaml"},
        },
        "projection_profiles": [PROFILE],
    },
    "invariants.yaml": INVARIANTS,
    "contracts.yaml": CONTRACTS,
    "authority_model.yaml": AUTHORITY_MODEL,
    "projection_artifact.schema.yaml": {
        "required": [
            "schema",
            "source_ref",
            "source_digest",
            "projection_profile_ref",
            "projection_profile_digest",
            "payload",
            "projection_digest",
        ],
        "properties": {"schema": {"const": "l9.projection-artifact/v1"}},
    },
    "compiler_receipt.schema.yaml": {
        "required": [
            "schema",
            "receipt_identity",
            "operation",
            "inputs",
            "profile",
            "output",
            "result",
            "producer_identity",
            "receipt_digest",
        ],
        "properties": {"schema": {"const": "l9.compiler-receipt/v1"}},
    },
    "vocabulary.yaml": {
        "organizational_target": {
            "l9-semantic-compiler": {"role": ["projection"]},
            "l9-bystander": {"role": ["consumer"]},
        }
    },
}
ORIGIN = "https://github.com/Quantum-L9/.github"
PRODUCER = {"compiler": "l9-semantic-compiler", "version": "fixture"}


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=fixture", "-c", "user.email=f@x", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit_all(root: Path, message: str, publish: bool = True) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    head = git(root, "rev-parse", "HEAD")
    if publish:  # what a fetch of the canonical owner leaves behind
        git(root, "update-ref", "refs/remotes/origin/main", head)
    return head


def write_semantics(root: Path, name: str, doc: Any) -> None:
    (root / "semantics" / name).write_text(yaml.safe_dump(doc, sort_keys=False))


@pytest.fixture
def authority(tmp_path: Path) -> Path:
    root = tmp_path / "authority"
    (root / "semantics").mkdir(parents=True)
    for name, doc in SEMANTICS.items():
        write_semantics(root, name, doc)
    (root / "README.md").write_text("fixture\n")
    git(root, "init", "-q")
    git(root, "remote", "add", "origin", ORIGIN)
    commit_all(root, "fixture law")
    return root


def head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD")


def envelope_digest(artifact: dict[str, Any]) -> str:
    return verifier.content_digest({k: v for k, v in artifact.items() if k != "projection_digest"})


def build_projection(
    root: Path,
    out: Path,
    *,
    source_bytes: bytes | None = None,
    producer: dict[str, str] | None = None,
    artifact_producer: dict[str, str] | None = None,
    result: str = "pass",
    payload_edit: Any = None,
    recompute: bool = True,
    output_ref: str | None = None,
) -> tuple[Path, Path]:
    """Emit artifact + receipt in the producer's shape, as a publisher would supply them."""
    producer = producer or PRODUCER
    raw = (
        source_bytes
        if source_bytes is not None
        else (root / "semantics/invariants.yaml").read_bytes()
    )
    catalog = yaml.safe_load((root / "semantics/projection_profiles.yaml").read_text())
    profile = next(p for p in catalog["projection_profiles"] if p["id"] == verifier.PROFILE_REF)
    # The fixture producer re-selects only the exact-id form; a profile carrying
    # another selector shape is the verifier's to refuse, not the fixture's.
    selected = [
        match.group(1)
        for s in profile["sources"]["invariants"]["selectors"]
        if (match := verifier.ID_SELECTOR.fullmatch(s)) is not None
    ]
    payload = {
        "invariants": [e for e in yaml.safe_load(raw)["invariants"] if e.get("id") in selected]
    }
    if payload_edit is not None:
        payload_edit(payload)
    artifact = {
        "schema": "l9.projection-artifact/v1",
        "source_ref": verifier.SOURCE_REF,
        "source_digest": verifier.bytes_digest(raw),
        "projection_profile_ref": verifier.PROFILE_REF,
        "projection_profile_digest": verifier.content_digest(profile),
        "payload": payload,
        "generated_by": dict(artifact_producer or producer),
    }
    artifact["projection_digest"] = envelope_digest(artifact)
    if payload_edit is not None and not recompute:
        untouched = dict(
            artifact,
            payload={
                "invariants": [
                    e for e in yaml.safe_load(raw)["invariants"] if e.get("id") in selected
                ]
            },
        )
        artifact["projection_digest"] = envelope_digest(untouched)
    subject = f"{verifier.PROFILE_REF}#{verifier.SOURCE_REF}"
    receipt: dict[str, Any] = {
        "schema": "l9.compiler-receipt/v1",
        "receipt_identity": "l9.receipt-instance/fixture",
        "receipt_type": "l9.receipt/compilation@1",
        "exact_subject_ref": subject,
        "claim": "fixture projection",
        "operation": "projection",
        "inputs": [
            {
                "ref": verifier.SOURCE_REF,
                "digest": artifact["source_digest"],
                "revision": head(root),
                "path": "semantics/invariants.yaml",
            }
        ],
        "profile": {"ref": verifier.PROFILE_REF, "digest": artifact["projection_profile_digest"]},
        "output": {"ref": output_ref or subject, "digest": artifact["projection_digest"]},
        "governing_coordinates": {"repository": verifier.OWNER_REPOSITORY, "revision": head(root)},
        "result": result,
        "verification_basis": {"coverage": "complete", "unresolved_criteria": []},
        "producer_identity": dict(producer),
        "diagnostics": [],
    }
    receipt["receipt_digest"] = verifier.content_digest(receipt)
    out.mkdir(parents=True, exist_ok=True)
    artifact_path, receipt_path = out / "artifact.json", out / "receipt.json"
    artifact_path.write_text(json.dumps(artifact))
    receipt_path.write_text(json.dumps(receipt))
    return artifact_path, receipt_path


def run(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    *argv: str,
) -> tuple[int, dict[str, Any], list[list[str]]]:
    calls: list[list[str]] = []
    real = subprocess.run

    def recording(cmd: list[str], *a: Any, **kw: Any) -> Any:
        calls.append([str(c) for c in cmd])
        return real(cmd, *a, **kw)

    capsys.readouterr()
    with monkeypatch.context() as m:
        m.setattr(verifier.subprocess, "run", recording)
        rc = verifier.main(list(argv))
    return rc, json.loads(capsys.readouterr().out), calls


def bind_args(root: Path, artifact: Path, receipt: Path, *extra: str) -> list[str]:
    return [
        "--authority-root",
        str(root),
        "--artifact",
        str(artifact),
        "--receipt",
        str(receipt),
        *extra,
    ]


# 1. A valid externally supplied artifact is consumed without any producer.
def test_supplied_projection_binds_without_running_a_producer(
    authority, tmp_path, capsys, monkeypatch
):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, calls = run(
        capsys,
        monkeypatch,
        *bind_args(authority, artifact, receipt, "--expect-revision", head(authority)),
        "--require-invariant",
        "L9-FIXTURE-001",
    )
    assert (rc, record["status"], record["reason"]) == (0, "BOUND", "PROJECTION_VERIFIED")
    assert record["applicable_invariants"][0]["id"] == "L9-FIXTURE-001"
    assert record["projected_invariant_count"] == 2
    assert record["profile"]["ref"] == "l9.projection/coding-agent-execution@1"
    assert record["authority_root"]["revision"] == head(authority)
    assert record["authority_root"]["revision_basis"] == "caller_pinned_not_authenticated"
    assert record["authority_root"]["content_basis"] == "pinned_commit_objects_hash_verified"
    assert record["receipt"]["producer_authentication"] == "unauthenticated_unkeyed_receipt"
    assert calls and all(c[0] == "git" for c in calls)
    assert not any(
        "semantic_compiler" in part or "semantic-compiler" in part for c in calls for part in c
    )


def test_default_selection_is_every_projected_invariant_in_source_order(
    authority, tmp_path, capsys, monkeypatch
):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bind_args(authority, artifact, receipt, "--expect-revision", head(authority)),
    )
    assert rc == 0
    assert [i["id"] for i in record["applicable_invariants"]] == SELECTED
    # The unselected global invariant is not part of the binding: the profile,
    # not the scope, decides what the coding agent binds.
    assert "L9-FIXTURE-UNSELECTED" not in {i["id"] for i in record["applicable_invariants"]}


# 2. An absent artifact is an explicit Unknown, reached without touching anything.
@pytest.mark.parametrize("supplied", ["none", "missing-files"])
def test_absent_projection_is_blocked_upstream(authority, tmp_path, capsys, monkeypatch, supplied):
    argv = ["--authority-root", str(authority), "--expect-revision", head(authority)]
    if supplied == "missing-files":
        argv += [
            "--artifact",
            str(tmp_path / "nope.json"),
            "--receipt",
            str(tmp_path / "nope.r.json"),
        ]
    rc, record, calls = run(capsys, monkeypatch, *argv)
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "BLOCKED_UPSTREAM_PROJECTION_PRODUCER",
    )
    assert calls == []


# 3. Missing or untrusted revision pins cannot produce a verified binding (F-02).
def test_missing_pin_is_blocked(authority, tmp_path, capsys, monkeypatch):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, _ = run(capsys, monkeypatch, *bind_args(authority, artifact, receipt))
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "AUTHORITY_REVISION_PIN_ABSENT",
    )


@pytest.mark.parametrize("pin", ["HEAD", "main", "abc1234", "ABCDEF" * 6 + "ABCD", "0" * 39 + "g"])
def test_malformed_pin_is_blocked(authority, tmp_path, capsys, monkeypatch, pin):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "AUTHORITY_REVISION_PIN_MALFORMED",
    )


def test_pin_other_than_checkout_is_stale(authority, tmp_path, capsys, monkeypatch):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", "1" * 40)
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "AUTHORITY_REVISION_MISMATCH")


def test_local_only_authority_commit_is_blocked(authority, tmp_path, capsys, monkeypatch):
    law = authority / "semantics" / "invariants.yaml"
    forged = yaml.safe_load(law.read_text())
    forged["invariants"][0]["rule"] = "locally rewritten law"
    law.write_text(yaml.safe_dump(forged, sort_keys=False))
    local = commit_all(authority, "local law edit", publish=False)
    artifact, receipt = build_projection(authority, tmp_path / "forged")
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", local)
    )
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "AUTHORITY_REVISION_NOT_ON_ORIGIN_TRACKING_REF",
    )


def test_noncanonical_origin_is_blocked(authority, tmp_path, capsys, monkeypatch):
    git(authority, "remote", "set-url", "origin", "https://github.com/someone/Quantum-L9/.github")
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bind_args(authority, artifact, receipt, "--expect-revision", head(authority)),
    )
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "AUTHORITY_ROOT_NOT_CANONICAL_OWNER",
    )


def test_prior_binding_recheck_requires_pin(authority, tmp_path, capsys, monkeypatch):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    pin = head(authority)
    _, bound, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    prior = tmp_path / "binding.json"
    prior.write_text(json.dumps(bound))
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--prior-binding", str(prior))
    )
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "AUTHORITY_REVISION_PIN_ABSENT",
    )


# Local substitution beneath a trusted pin: the bytes read are the pinned bytes.
def _tamper(authority: Path) -> bytes:
    forged = yaml.safe_load((authority / "semantics/invariants.yaml").read_text())
    forged["invariants"][2]["rule"] = "substituted law"
    return yaml.safe_dump(forged, sort_keys=False).encode()


def test_index_hidden_worktree_edit_cannot_bind(authority, tmp_path, capsys, monkeypatch):
    pin = head(authority)
    tampered = _tamper(authority)
    (authority / "semantics/invariants.yaml").write_bytes(tampered)
    git(authority, "update-index", "--skip-worktree", "semantics/invariants.yaml")
    assert git(authority, "status", "--porcelain", "--", "semantics") == ""
    artifact, receipt = build_projection(authority, tmp_path / "forged", source_bytes=tampered)
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "SOURCE_DIGEST_NOT_CURRENT")


def _blob_oid(authority: Path, pin: str) -> str:
    return git(authority, "rev-parse", f"{pin}:semantics/invariants.yaml")


def test_replace_ref_cannot_substitute_law(authority, tmp_path, capsys, monkeypatch):
    pin = head(authority)
    tampered = _tamper(authority)
    forged_file = tmp_path / "forged.yaml"
    forged_file.write_bytes(tampered)
    forged_oid = git(authority, "hash-object", "-w", str(forged_file))
    git(authority, "replace", _blob_oid(authority, pin), forged_oid)
    artifact, receipt = build_projection(authority, tmp_path / "forged", source_bytes=tampered)
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "SOURCE_DIGEST_NOT_CURRENT")


def test_rewritten_loose_object_is_rejected(authority, tmp_path, capsys, monkeypatch):
    pin = head(authority)
    oid = _blob_oid(authority, pin)
    tampered = _tamper(authority)
    loose = authority / ".git" / "objects" / oid[:2] / oid[2:]
    loose.chmod(0o644)
    loose.write_bytes(zlib.compress(f"blob {len(tampered)}\0".encode() + tampered))
    forged_file = tmp_path / "forged.yaml"
    forged_file.write_bytes(tampered)
    assert git(authority, "hash-object", "--no-filters", str(forged_file)) != oid
    artifact, receipt = build_projection(authority, tmp_path / "forged", source_bytes=tampered)
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    assert (rc, record["status"], record["reason"]) == (
        1,
        "REJECTED",
        "AUTHORITY_OBJECT_NOT_BOUND_TO_PIN",
    )


def test_uncommitted_semantics_edit_is_blocked(authority, tmp_path, capsys, monkeypatch):
    pin = head(authority)
    (authority / "semantics/invariants.yaml").write_bytes(_tamper(authority))
    artifact, receipt = build_projection(authority, tmp_path / "forged")
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    assert (rc, record["status"], record["reason"]) == (
        3,
        "BLOCKED",
        "AUTHORITY_ROOT_SEMANTICS_UNCOMMITTED",
    )


# 4. Tampered, stale, or mismatched evidence stays rejected.
def _drop_rule(payload: dict[str, Any]) -> None:
    payload["invariants"][0]["rule"] = "weakened"


def _reorder(payload: dict[str, Any]) -> None:
    payload["invariants"].reverse()


def _flatten(payload: dict[str, Any]) -> None:
    payload["flattened"] = payload.pop("invariants")


def _edit_receipt(path: Path, change: Any, redigest: bool) -> None:
    receipt = json.loads(path.read_text())
    change(receipt)
    if redigest:
        receipt["receipt_digest"] = verifier.content_digest(
            {k: v for k, v in receipt.items() if k != "receipt_digest"}
        )
    path.write_text(json.dumps(receipt))


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("payload_digest_not_recomputed", (1, "REJECTED", "PROJECTION_DIGEST_MISMATCH")),
        ("payload_altered_digests_recomputed", (1, "REJECTED", "PAYLOAD_NOT_FAITHFUL_TO_SOURCE")),
        ("payload_reordered_digests_recomputed", (1, "REJECTED", "PAYLOAD_NOT_IN_SOURCE_ORDER")),
        ("payload_section_renamed", (3, "BLOCKED", "PAYLOAD_SHAPE_UNRESOLVED")),
        ("envelope_coordinate_edited_digest_kept", (1, "REJECTED", "PROJECTION_DIGEST_MISMATCH")),
        ("receipt_field_tampered", (1, "REJECTED", "RECEIPT_DIGEST_MISMATCH")),
        ("receipt_unpinned_production", (1, "REJECTED", "RECEIPT_NOT_A_PASSING_PROJECTION")),
        ("receipt_output_other_artifact", (1, "REJECTED", "RECEIPT_OUTPUT_NOT_BOUND")),
        ("receipt_output_other_source", (1, "REJECTED", "RECEIPT_OUTPUT_NOT_BOUND")),
        (
            "producer_without_projection_role",
            (1, "REJECTED", "RECEIPT_PRODUCER_NOT_ASSIGNED_PROJECTION_ROLE"),
        ),
        ("artifact_producer_differs_from_receipt", (1, "REJECTED", "ARTIFACT_PRODUCER_MISMATCH")),
        (
            "artifact_producer_carries_extra_coordinate",
            (1, "REJECTED", "ARTIFACT_PRODUCER_MISMATCH"),
        ),
        ("artifact_wrong_profile", (1, "REJECTED", "PROFILE_IDENTITY_MISMATCH")),
        ("invariant_not_projected", (3, "BLOCKED", "REQUIRED_INVARIANT_NOT_PROJECTED")),
    ],
)
def test_tampered_or_mismatched_evidence_is_rejected(
    authority, tmp_path, capsys, monkeypatch, case, expected
):
    out = tmp_path / case
    extra: list[str] = []
    if case == "payload_digest_not_recomputed":
        artifact, receipt = build_projection(
            authority, out, payload_edit=_drop_rule, recompute=False
        )
    elif case == "payload_altered_digests_recomputed":
        artifact, receipt = build_projection(authority, out, payload_edit=_drop_rule)
    elif case == "payload_reordered_digests_recomputed":
        artifact, receipt = build_projection(authority, out, payload_edit=_reorder)
    elif case == "payload_section_renamed":
        artifact, receipt = build_projection(authority, out, payload_edit=_flatten)
    elif case == "receipt_unpinned_production":
        artifact, receipt = build_projection(authority, out, result="unknown")
    elif case == "receipt_output_other_source":
        artifact, receipt = build_projection(
            authority, out, output_ref=verifier.PROFILE_REF + "#l9.source/contracts@1"
        )
    elif case == "producer_without_projection_role":
        bystander = {"compiler": "l9-bystander", "version": "fixture"}
        artifact, receipt = build_projection(authority, out, producer=bystander)
    elif case == "artifact_producer_differs_from_receipt":
        artifact, receipt = build_projection(
            authority,
            out,
            artifact_producer={"compiler": "l9-semantic-compiler", "version": "other"},
        )
    elif case == "artifact_producer_carries_extra_coordinate":
        # Same compiler and version, but a build coordinate the receipt does not
        # carry: the whole identity must agree, not only its two leading fields.
        artifact, receipt = build_projection(
            authority, out, artifact_producer={**PRODUCER, "revision": "deadbeef"}
        )
    else:
        artifact, receipt = build_projection(authority, out)
    if case == "envelope_coordinate_edited_digest_kept":
        doc = json.loads(artifact.read_text())
        doc["generated_by"] = {"compiler": "l9-semantic-compiler", "version": "rewritten"}
        artifact.write_text(json.dumps(doc))
    elif case == "receipt_field_tampered":
        _edit_receipt(receipt, lambda r: r.update(claim="forged claim"), redigest=False)
    elif case == "receipt_output_other_artifact":
        _edit_receipt(
            receipt, lambda r: r["output"].update(digest="sha256:" + "0" * 64), redigest=True
        )
    elif case == "artifact_wrong_profile":
        doc = json.loads(artifact.read_text())
        doc["projection_profile_ref"] = "l9.projection/other@1"
        artifact.write_text(json.dumps(doc))
    elif case == "invariant_not_projected":
        extra = ["--require-invariant", "L9-FIXTURE-UNSELECTED"]
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bind_args(authority, artifact, receipt, "--expect-revision", head(authority), *extra),
    )
    assert (rc, record["status"], record["reason"]) == expected


# 5. Only the profile's exact-id selection form is re-selected; anything else is Unknown.
@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda p: p["sources"]["invariants"]["selectors"].append(
                '$.invariants[?(@.scope=="global")]'
            ),
            (3, "BLOCKED", "PROFILE_SELECTOR_FORM_UNRESOLVED"),
        ),
        (
            lambda p: p["sources"]["invariants"]["selectors"].append(id_selector("L9-FIXTURE-001")),
            (3, "BLOCKED", "PROFILE_SELECTOR_DUPLICATE_IDENTITY"),
        ),
        (
            lambda p: p["sources"]["invariants"]["selectors"].append(id_selector("L9-NOWHERE")),
            (3, "BLOCKED", "CANONICAL_INVARIANT_UNRESOLVED"),
        ),
        (lambda p: p.update(**{"class": "consumer"}), (3, "BLOCKED", "PROFILE_CONSUMER_MISMATCH")),
    ],
)
def test_profile_shapes_the_consumer_cannot_reselect_are_unknown(
    authority, tmp_path, capsys, monkeypatch, mutate, expected
):
    catalog = yaml.safe_load((authority / "semantics/projection_profiles.yaml").read_text())
    mutate(catalog["projection_profiles"][0])
    write_semantics(authority, "projection_profiles.yaml", catalog)
    pin = commit_all(authority, "profile edit")
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", pin)
    )
    assert (rc, record["status"], record["reason"]) == expected


def test_upstream_law_change_makes_supplied_projection_stale(
    authority, tmp_path, capsys, monkeypatch
):
    artifact, receipt = build_projection(authority, tmp_path / "old")
    _, bound, _ = run(
        capsys,
        monkeypatch,
        *bind_args(authority, artifact, receipt, "--expect-revision", head(authority)),
    )
    prior = tmp_path / "binding.json"
    prior.write_text(json.dumps(bound))
    law = authority / "semantics/invariants.yaml"
    changed = yaml.safe_load(law.read_text())
    changed["invariants"][0]["rule"] = "upstream amended rule"
    law.write_text(yaml.safe_dump(changed, sort_keys=False))
    new = commit_all(authority, "upstream amends law")
    rc, record, _ = run(
        capsys, monkeypatch, *bind_args(authority, artifact, receipt, "--expect-revision", new)
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "SOURCE_DIGEST_NOT_CURRENT")
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bind_args(
            authority, artifact, receipt, "--prior-binding", str(prior), "--expect-revision", new
        ),
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "SOURCE_DIGEST_CHANGED")
    assert record["affected_applicable_invariants"] == ["L9-FIXTURE-001"]


def test_unrelated_upstream_commit_keeps_binding_current(authority, tmp_path, capsys, monkeypatch):
    artifact, receipt = build_projection(authority, tmp_path / "supplied")
    _, bound, _ = run(
        capsys,
        monkeypatch,
        *bind_args(authority, artifact, receipt, "--expect-revision", head(authority)),
    )
    prior = tmp_path / "binding.json"
    prior.write_text(json.dumps(bound))
    (authority / "README.md").write_text("unrelated\n")
    new = commit_all(authority, "unrelated upstream commit")
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bind_args(
            authority, artifact, receipt, "--prior-binding", str(prior), "--expect-revision", new
        ),
    )
    assert (rc, record["status"], record["reason"]) == (
        0,
        "CURRENT",
        "UPSTREAM_REVISION_CHANGED_WITHOUT_DEPENDENCY_IMPACT",
    )


# --- Bundle mode: the consumer-committed bundle (ADR-021) ---------------------------------

CLASS_SOURCES = {
    "invariants": (verifier.SOURCE_REF, "invariants.yaml"),
    "contracts": (CONTRACTS_REF, "contracts.yaml"),
    "authority_model": (AUTHORITY_MODEL_REF, "authority_model.yaml"),
}


def _class_payload(cls: str, document: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """What the producer emits for each fixture class under the profile's selectors."""
    if cls == "invariants":
        selected = [
            m.group(1)
            for s in profile["sources"]["invariants"]["selectors"]
            if (m := verifier.ID_SELECTOR.fullmatch(s)) is not None
        ]
        return {"invariants": [e for e in document["invariants"] if e.get("id") in selected]}
    if cls == "contracts":
        return {
            "contracts": [e for e in document["contracts"] if e["id"] == "l9.contract/fixture@1"]
        }
    return {"agent_authority": document["agent_authority"]}


def build_bundle(
    root: Path,
    out: Path,
    *,
    revision: str | None = None,
    producer: dict[str, str] | None = None,
    classes: list[str] | None = None,
    lock_schema: str = verifier.LOCK_SCHEMA,
    unresolved: list[str] | None = None,
    payload_schema: str = OUTPUT_SCHEMA,
) -> Path:
    """Write a bundle in the driver's layout for every (or the given) profile class."""
    producer = producer or PRODUCER
    revision = revision or head(root)
    catalog = yaml.safe_load((root / "semantics/projection_profiles.yaml").read_text())
    profile = next(p for p in catalog["projection_profiles"] if p["id"] == verifier.PROFILE_REF)
    profile_digest = verifier.content_digest(profile)
    (out / "projections").mkdir(parents=True, exist_ok=True)
    (out / "receipts").mkdir(parents=True, exist_ok=True)
    components = []
    for cls in classes or list(profile["sources"]):
        ref, filename = CLASS_SOURCES[cls]
        raw = (root / "semantics" / filename).read_bytes()
        artifact = {
            "schema": "l9.projection-artifact/v1",
            "source_ref": ref,
            "source_digest": verifier.bytes_digest(raw),
            "projection_profile_ref": verifier.PROFILE_REF,
            "projection_profile_digest": profile_digest,
            "payload": _class_payload(cls, yaml.safe_load(raw), profile),
            "generated_by": dict(producer),
        }
        artifact["projection_digest"] = envelope_digest(artifact)
        subject = f"{verifier.PROFILE_REF}#{ref}"
        receipt: dict[str, Any] = {
            "schema": "l9.compiler-receipt/v1",
            "receipt_identity": f"l9.receipt-instance/fixture-{cls}",
            "receipt_type": "l9.receipt/compilation@1",
            "exact_subject_ref": subject,
            "claim": "fixture projection",
            "operation": "projection",
            "inputs": [{"ref": ref, "digest": artifact["source_digest"], "revision": revision}],
            "profile": {"ref": verifier.PROFILE_REF, "digest": profile_digest},
            "output": {"ref": subject, "digest": artifact["projection_digest"]},
            "governing_coordinates": {
                "repository": verifier.OWNER_REPOSITORY,
                "revision": revision,
            },
            "result": "pass",
            "verification_basis": {
                "coverage": "complete",
                "unresolved_criteria": list(unresolved or []),
                "criteria": {"payload_schema": {"status": "pass", "schema": payload_schema}},
            },
            "producer_identity": dict(producer),
            "diagnostics": [],
        }
        receipt["receipt_digest"] = verifier.content_digest(receipt)
        path, receipt_path = f"projections/{cls}.projection.json", f"receipts/{cls}.receipt.json"
        (out / path).write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
        (out / receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        components.append(
            {
                "source_class": cls,
                "source_ref": ref,
                "source_digest": artifact["source_digest"],
                "projection_digest": artifact["projection_digest"],
                "path": path,
                "sha256": verifier.bytes_digest((out / path).read_bytes()),
                "receipt": receipt_path,
            }
        )
    lock = {
        "schema": lock_schema,
        "authority": {"repository": verifier.OWNER_REPOSITORY, "revision": revision},
        "producer": {**producer, "repository": "fixture/producer", "revision": "f" * 40},
        "generated_by": "fixture",
        "projection_profile": {"ref": verifier.PROFILE_REF, "digest": profile_digest},
        "components": components,
    }
    (out / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    return out


def bundle_args(root: Path, bundle: Path, *extra: str) -> list[str]:
    return ["--authority-root", str(root), "--bundle", str(bundle), *extra]


def test_bundle_binds_every_declared_class(authority, tmp_path, capsys, monkeypatch):
    bundle = build_bundle(authority, tmp_path / "bundle")
    rc, record, calls = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (0, "BOUND", "PROJECTION_BUNDLE_VERIFIED")
    assert [c["source_class"] for c in record["components"]] == [
        "invariants",
        "contracts",
        "authority_model",
    ]
    assert record["projected_invariant_count"] == 2
    assert record["bundle"]["authority"]["revision"] == head(authority)
    assert record["bundle"]["producer_authentication"] == "unauthenticated_unkeyed_receipt"
    assert calls and all(c[0] == "git" for c in calls)


def test_bundle_missing_a_declared_class_is_rejected(authority, tmp_path, capsys, monkeypatch):
    bundle = build_bundle(authority, tmp_path / "bundle", classes=["invariants", "contracts"])
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (1, "REJECTED", "BUNDLE_COMPONENTS_MISMATCH")


def test_bundle_byte_change_outside_invariants_is_rejected(
    authority, tmp_path, capsys, monkeypatch
):
    bundle = build_bundle(authority, tmp_path / "bundle")
    target = bundle / "projections/contracts.projection.json"
    target.write_bytes(target.read_bytes() + b" ")
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (1, "REJECTED", "BUNDLE_BYTES_MISMATCH")
    assert record["path"] == "projections/contracts.projection.json"


def test_bundle_coherent_forgery_of_a_non_invariant_class_is_rejected(
    authority, tmp_path, capsys, monkeypatch
):
    """Rehashed bytes, lock and receipt still fail: the receipt digest no longer covers them."""
    bundle = build_bundle(authority, tmp_path / "bundle")
    path = bundle / "projections/authority_model.projection.json"
    artifact = json.loads(path.read_text())
    artifact["payload"]["agent_authority"]["rules"].append("forged rule")
    artifact["projection_digest"] = envelope_digest(artifact)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    lock = json.loads((bundle / "bundle.lock.json").read_text())
    for component in lock["components"]:
        if component["source_class"] == "authority_model":
            component["sha256"] = verifier.bytes_digest(path.read_bytes())
            component["projection_digest"] = artifact["projection_digest"]
    (bundle / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (1, "REJECTED", "RECEIPT_OUTPUT_NOT_BOUND")


def test_bundle_receipt_with_unresolved_criteria_is_rejected(
    authority, tmp_path, capsys, monkeypatch
):
    bundle = build_bundle(authority, tmp_path / "bundle", unresolved=["payload_schema"])
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (
        1,
        "REJECTED",
        "RECEIPT_NOT_A_PASSING_PROJECTION",
    )


def test_bundle_receipt_must_prove_the_declared_output_schema(
    authority, tmp_path, capsys, monkeypatch
):
    bundle = build_bundle(authority, tmp_path / "bundle", payload_schema="l9.projection.other/v1")
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (
        1,
        "REJECTED",
        "RECEIPT_PAYLOAD_SCHEMA_MISMATCH",
    )


def test_bundle_with_another_lock_schema_is_rejected(authority, tmp_path, capsys, monkeypatch):
    bundle = build_bundle(authority, tmp_path / "bundle", lock_schema="l9.other-bundle/v1")
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    assert (rc, record["status"], record["reason"]) == (1, "REJECTED", "LOCK_SCHEMA_MISMATCH")


def test_bundle_revision_outside_the_pin_history_is_stale(authority, tmp_path, capsys, monkeypatch):
    first = head(authority)
    (authority / "README.md").write_text("later\n")
    later = commit_all(authority, "later upstream commit")
    bundle = build_bundle(authority, tmp_path / "bundle", revision=later)
    # A pin older than the bundle's own revision cannot judge its currency.
    rc, record, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", first)
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "AUTHORITY_REVISION_MISMATCH")


def test_bundle_stays_current_across_an_unrelated_upstream_commit(
    authority, tmp_path, capsys, monkeypatch
):
    bundle = build_bundle(authority, tmp_path / "bundle")
    _, bound, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    prior = tmp_path / "binding.json"
    prior.write_text(json.dumps(bound))
    (authority / "README.md").write_text("unrelated\n")
    new = commit_all(authority, "unrelated upstream commit")
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bundle_args(authority, bundle, "--prior-binding", str(prior), "--expect-revision", new),
    )
    assert (rc, record["status"], record["reason"]) == (
        0,
        "CURRENT",
        "UPSTREAM_REVISION_CHANGED_WITHOUT_DEPENDENCY_IMPACT",
    )


def test_bundle_goes_stale_when_a_non_invariant_source_changes(
    authority, tmp_path, capsys, monkeypatch
):
    bundle = build_bundle(authority, tmp_path / "bundle")
    _, bound, _ = run(
        capsys, monkeypatch, *bundle_args(authority, bundle, "--expect-revision", head(authority))
    )
    prior = tmp_path / "binding.json"
    prior.write_text(json.dumps(bound))
    write_semantics(authority, "contracts.yaml", {"contracts": CONTRACTS["contracts"][:1]})
    new = commit_all(authority, "contracts ledger changed")
    rc, record, _ = run(
        capsys,
        monkeypatch,
        *bundle_args(authority, bundle, "--prior-binding", str(prior), "--expect-revision", new),
    )
    assert (rc, record["status"], record["reason"]) == (4, "STALE", "SOURCE_DIGEST_NOT_CURRENT")
    assert record["source_class"] == "contracts"
