"""Domain consumer binding bundles: driver ``--binding`` mode and the verifier that judges them.

End to end against a synthetic ``Quantum-L9/.github`` authority (a real git repository whose
origin names the canonical owner) and a fixture compiler that emits artifacts and receipts in
the producer's shape for whatever profile it is asked to project. The driver writes the bundle;
``skills/l9-coding-agent/scripts/verify_canonical_binding.py --binding-bundle`` verifies it.
Upstream law in the fixture is illustrative, not a copy of ``.github``.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
PRODUCER = REPO / "tools/authority/produce_projection_bundle.py"
VERIFIER = REPO / "skills/l9-coding-agent/scripts/verify_canonical_binding.py"
PIN = REPO / "governance/authority-bindings/coding-agent-domain-binding.yaml"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
ORIGIN = "https://github.com/Quantum-L9/.github"
BINDING = "l9.domain-consumer-binding/coding-agent@1"
COMPILER_REVISION = "c" * 40

_SPEC = importlib.util.spec_from_file_location("binding_bundle_producer", PRODUCER)
assert _SPEC and _SPEC.loader
producer = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(producer)


def _domain(name: str, sources: list[str]) -> dict[str, Any]:
    return {
        "id": f"l9.projection/{name}@1",
        "class": "domain",
        "consumer": f"semantic_domain.{name.replace('-', '_')}",
        "sources": {cls: {"selectors": ["$"]} for cls in sources},
        "output": {"schema": f"l9.projection.domain.{name}/v1"},
    }


def _binding(**override: Any) -> dict[str, Any]:
    binding: dict[str, Any] = {
        "id": BINDING,
        "consumer": {
            "kind": "skill",
            "identity": "l9-coding-agent",
            "repository_ref": "l9.repository-registry/global@1#cursor-governance",
            "entrypoint": {"path": "skills/l9-coding-agent/SKILL.md"},
        },
        "predecessor_profiles": ["l9.projection/coding-agent-execution@1"],
        "requires": ["l9.projection/alpha-beta@1", "l9.projection/gamma@1"],
        "conditional": [
            {"profile": "l9.projection/delta@1", "activation": "explicit_task_requirement"}
        ],
        "authority": {
            "binding_grants_permissions": False,
            "action_authority": "externally_resolved",
        },
        "unresolved": [
            {
                "coordinate": "added_selection_review",
                "reason": "fixture",
                "blocks": "consumer_migration",
            }
        ],
    }
    binding.update(override)
    return binding


def _semantics(binding: dict[str, Any]) -> dict[str, Any]:
    sources = {
        "invariants": ("l9.source/invariants@1", {"invariants": [{"id": "L9-FIXTURE-001"}]}),
        "contracts": ("l9.source/contracts@1", {"contracts": [{"id": "l9.contract/fixture@1"}]}),
        "authority_model": ("l9.source/authority-model@1", {"agent_authority": {"rules": ["r"]}}),
    }
    docs: dict[str, Any] = {f"{cls}.yaml": doc for cls, (_, doc) in sources.items()}
    docs["canonical_sources.yaml"] = {
        "sources": [
            {
                "id": ref,
                "path": f"semantics/{cls}.yaml",
                "canonical": True,
                "projection_allowed": True,
            }
            for cls, (ref, _) in sources.items()
        ]
    }
    docs["projection_profiles.yaml"] = {
        "source_classes": {cls: {"canonical_artifact": f"{cls}.yaml"} for cls in sources},
        "projection_profiles": [
            _domain("alpha-beta", ["invariants", "contracts"]),
            _domain("gamma", ["authority_model", "invariants"]),
            _domain("delta", ["contracts"]),
            {
                "id": "l9.projection/not-a-domain@1",
                "class": "runtime",
                "consumer": "Cursor-Governance",
                "sources": {"invariants": {"selectors": ["$"]}},
                "output": {"schema": "l9.projection.not-a-domain/v1"},
            },
        ],
    }
    docs["composition_profiles.yaml"] = {"profiles": []}
    docs["domain_consumer_bindings.yaml"] = {
        "schema": "l9.domain-consumer-binding-catalog/v1",
        "consumer_kinds": {
            "skill": {
                "requires": ["repository_ref", "entrypoint"],
                "forbids": ["actor_ref", "surface_refs"],
            },
            "host": {"requires": ["actor_ref", "surface_refs"], "forbids": ["entrypoint"]},
        },
        "activation_conditions": {
            "explicit_task_requirement": {"definition": "fixture"},
            "hosted_skill_requirement": {"definition": "fixture"},
        },
        "composition": {
            "compatibility_contract": "l9.contract/domain-composition-compatibility@1",
            "provenance_contract": "l9.contract/domain-composition-provenance@1",
        },
        "bindings": [binding],
    }
    docs["projection_artifact.schema.yaml"] = {
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
    }
    docs["compiler_receipt.schema.yaml"] = {
        "required": ["schema", "receipt_identity", "operation", "output", "receipt_digest"],
        "properties": {"schema": {"const": "l9.compiler-receipt/v1"}},
    }
    docs["vocabulary.yaml"] = {
        "organizational_target": {"l9-semantic-compiler": {"role": ["projection"]}}
    }
    return docs


# The fixture compiler: the producer's CLI shape (projection-coordinates / project), reading the
# authority from its commit objects and emitting artifact + receipt per declared source.
STUB = textwrap.dedent(
    """
    import hashlib, json, subprocess, sys, yaml
    from pathlib import Path

    def digest(value):
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "sha256:" + hashlib.sha256(raw.encode()).hexdigest()

    def show(root, revision, path):
        return subprocess.run(["git", "-C", root, "show", f"{revision}:{path}"],
                              check=True, capture_output=True).stdout

    def law(root, revision, profile_ref):
        catalog = yaml.safe_load(show(root, revision, "semantics/projection_profiles.yaml"))
        registry = yaml.safe_load(show(root, revision, "semantics/canonical_sources.yaml"))
        profile = next(p for p in catalog["projection_profiles"] if p["id"] == profile_ref)
        by_file = {Path(s["path"]).name: s for s in registry["sources"]}
        sources = []
        for cls in profile["sources"]:
            entry = by_file[catalog["source_classes"][cls]["canonical_artifact"]]
            raw = show(root, revision, entry["path"])
            sources.append((cls, entry["id"], raw))
        return profile, sources

    PRODUCER = {"compiler": "l9-semantic-compiler", "version": "fixture"}
    command = sys.argv[1]
    if command == "projection-coordinates":
        args = dict(zip(sys.argv[2::2], sys.argv[3::2]))
        profile, sources = law(args["--authority-root"], args["--revision"], args["--profile"])
        print(yaml.safe_dump({
            "projection_profile": {"ref": profile["id"], "digest": digest(profile)},
            "sources": [{"ref": ref, "digest": "sha256:" + hashlib.sha256(raw).hexdigest()}
                        for _, ref, raw in sources]}))
    elif command == "project":
        request = yaml.safe_load(Path(sys.argv[2]).read_text())
        root, revision = request["authority"]["root"], request["authority"]["revision"]
        profile, sources = law(root, revision, request["projection_profile"]["ref"])
        pin = {"ref": profile["id"], "digest": digest(profile)}
        out = Path(request["output_root"]); out.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for cls, ref, raw in sources:
            artifact = {"schema": "l9.projection-artifact/v1", "source_ref": ref,
                        "source_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
                        "projection_profile_ref": pin["ref"],
                        "projection_profile_digest": pin["digest"],
                        "payload": {cls: yaml.safe_load(raw)}, "generated_by": dict(PRODUCER)}
            artifact["projection_digest"] = digest(artifact)
            subject = f"{pin['ref']}#{ref}"
            receipt = {"schema": "l9.compiler-receipt/v1",
                       "receipt_identity": f"l9.receipt-instance/fixture-{cls}",
                       "receipt_type": "l9.receipt/compilation@1", "exact_subject_ref": subject,
                       "claim": "fixture projection", "operation": "projection",
                       "inputs": [{"ref": ref, "digest": artifact["source_digest"]}],
                       "profile": pin,
                       "output": {"ref": subject, "digest": artifact["projection_digest"]},
                       "governing_coordinates": {"repository": "Quantum-L9/.github",
                                                 "revision": revision},
                       "result": "pass",
                       "verification_basis": {"coverage": "complete", "unresolved_criteria": [],
                           "criteria": {"payload_schema": {"status": "pass",
                                        "schema": profile["output"]["schema"]}}},
                       "producer_identity": dict(PRODUCER), "diagnostics": []}
            receipt["receipt_digest"] = digest(receipt)
            path, rpath = out / f"{cls}.json", out / f"{cls}.receipt.json"
            path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\\n")
            rpath.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\\n")
            artifacts.append({"path": str(path), "receipt_path": str(rpath)})
        print(yaml.safe_dump({"result": "pass", "artifacts": artifacts}))
    else:
        sys.exit(f"fixture compiler: unsupported command {command}")
    """
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@invalid", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _commit(root: Path, docs: dict[str, Any], message: str) -> str:
    for name, doc in docs.items():
        (root / "semantics" / name).write_text(yaml.safe_dump(doc, sort_keys=False))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "update-ref", "refs/remotes/origin/main", head)  # what a fetch leaves behind
    return head


class Authority:
    def __init__(self, root: Path, binding: dict[str, Any]) -> None:
        self.root = root
        (root / "semantics").mkdir(parents=True)
        _git(root, "init", "-q")
        _git(root, "remote", "add", "origin", ORIGIN)
        self.head = _commit(root, _semantics(binding), "fixture law")

    def amend(self, binding: dict[str, Any]) -> str:
        self.head = _commit(self.root, _semantics(binding), "fixture change")
        return self.head


@pytest.fixture
def stub(tmp_path: Path) -> str:
    path = tmp_path / "stub_compiler.py"
    path.write_text(STUB)
    return f"{sys.executable} {path}"


def _produce(
    authority: Authority, stub: str, out: Path, *extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PRODUCER),
            "--binding",
            BINDING,
            "--authority-root",
            str(authority.root),
            "--authority-revision",
            authority.head,
            "--compiler-revision",
            COMPILER_REVISION,
            "--compiler",
            stub,
            "--output",
            str(out),
            *extra,
        ],
        env=ENV,
        capture_output=True,
        text=True,
    )


def _verify(authority: Authority, bundle: Path, *extra: str) -> tuple[int, dict[str, Any]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--authority-root",
            str(authority.root),
            "--binding-bundle",
            str(bundle),
            "--expect-revision",
            authority.head,
            *extra,
        ],
        env=ENV,
        capture_output=True,
        text=True,
    )
    return completed.returncode, json.loads(completed.stdout)


@pytest.fixture
def authority(tmp_path: Path) -> Authority:
    return Authority(tmp_path / "authority", _binding())


@pytest.fixture
def bundle(authority: Authority, stub: str, tmp_path: Path) -> Path:
    out = tmp_path / "bundle"
    produced = _produce(authority, stub, out)
    assert produced.returncode == 0, produced.stderr
    return out


def _lock(bundle: Path) -> dict[str, Any]:
    return json.loads((bundle / "binding.lock.json").read_text())


def _save(bundle: Path, lock: dict[str, Any]) -> None:
    (bundle / "binding.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def _refused(result: tuple[int, dict[str, Any]], status: str, reason: str) -> dict[str, Any]:
    code, record = result
    expected = {"REJECTED": 1, "BLOCKED": 3, "STALE": 4}[status]
    assert (code, record["status"], record["reason"]) == (expected, status, reason), record
    return record


# --- Driver ---------------------------------------------------------------------------------


def test_driver_writes_one_bundle_per_required_domain_and_an_index(bundle: Path) -> None:
    assert sorted(p.name for p in bundle.iterdir()) == ["alpha_beta", "binding.lock.json", "gamma"]
    lock = _lock(bundle)
    assert lock["schema"] == "l9.domain-binding-bundle/v1"
    assert [d["profile"]["ref"] for d in lock["domains"]] == [
        "l9.projection/alpha-beta@1",
        "l9.projection/gamma@1",
    ]
    for domain in lock["domains"]:
        sub = json.loads((bundle / domain["lock"]).read_text())
        assert sub["schema"] == "l9.projection-bundle/v1"
        assert sub["projection_profile"] == domain["profile"]
        assert "composition_profile" not in sub
        raw = (bundle / domain["lock"]).read_bytes()
        assert domain["lock_sha256"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    # Conditional domains are recorded, never materialized; nothing is composed or activated.
    assert lock["conditional"] == [
        {"ref": "l9.projection/delta@1", "activation": "explicit_task_requirement"}
    ]
    assert lock["cross_domain_composition"]["status"] == "not_produced"
    assert lock["activation"] == {
        "status": "blocked",
        "blocked_by": ["added_selection_review", "cross_domain_composition"],
    }
    assert lock["producer"]["revision"] == COMPILER_REVISION


def test_driver_check_is_byte_identical_and_detects_drift(
    authority: Authority, stub: str, bundle: Path
) -> None:
    assert _produce(authority, stub, bundle, "--check").returncode == 0
    victim = bundle / "gamma/projections/invariants.projection.json"
    victim.write_bytes(victim.read_bytes() + b" ")
    drift = _produce(authority, stub, bundle, "--check")
    assert drift.returncode == 1
    assert drift.stderr.splitlines()[0] == f"stale projection bundle {BINDING}:"
    assert "gamma/projections/invariants.projection.json" in drift.stderr


@pytest.mark.parametrize(
    ("override", "rule"),
    [
        (
            {"requires": ["l9.projection/alpha-beta@1", "l9.projection/not-a-domain@1"]},
            "BINDING-001",
        ),
        ({"requires": ["l9.projection/alpha-beta@1", "l9.projection/missing@1"]}, "BINDING-001"),
        (
            {"requires": ["l9.projection/alpha-beta@1", "l9.projection/delta@1"]},
            "BINDING-002",
        ),
        (
            {"conditional": [{"profile": "l9.projection/delta@1", "activation": "whenever"}]},
            "BINDING-002",
        ),
        (
            {
                "consumer": {
                    "kind": "skill",
                    "identity": "l9-coding-agent",
                    "repository_ref": "r",
                    "entrypoint": {"path": "p"},
                    "actor_ref": "l9.actor-registry/global@1#cursor",
                }
            },
            "BINDING-003",
        ),
        (
            {"authority": {"binding_grants_permissions": True, "action_authority": "x"}},
            "BINDING-004",
        ),
    ],
)
def test_driver_refuses_a_malformed_canonical_binding(
    tmp_path: Path, stub: str, override: dict[str, Any], rule: str
) -> None:
    authority = Authority(tmp_path / "authority", _binding(**override))
    produced = _produce(authority, stub, tmp_path / "bundle")
    assert produced.returncode == 3 and rule in produced.stderr, produced.stderr
    assert not (tmp_path / "bundle").exists()


def test_driver_rejects_a_composition_profile_for_a_binding(
    authority: Authority, stub: str, tmp_path: Path
) -> None:
    produced = _produce(
        authority, stub, tmp_path / "bundle", "--composition-profile", "l9.compose/x@1"
    )
    assert produced.returncode == 2 and "applies to --profile only" in produced.stderr


def test_domain_directory_names_follow_the_profile_ref() -> None:
    assert producer.domain_directory("l9.projection/capabilities-dependencies@1") == (
        "capabilities_dependencies"
    )
    with pytest.raises(producer.ProductionError):
        producer.domain_directory("l9.compose/architecture@1")


# --- Verifier -------------------------------------------------------------------------------


def test_produced_binding_bundle_verifies_but_is_never_activated(
    authority: Authority, bundle: Path
) -> None:
    code, record = _verify(authority, bundle)
    assert (code, record["status"], record["reason"]) == (
        5,
        "BUNDLE_VERIFIED",
        "DOMAIN_BINDING_BUNDLE_VERIFIED",
    ), record
    assert [d["profile"]["ref"] for d in record["domains"]] == [
        "l9.projection/alpha-beta@1",
        "l9.projection/gamma@1",
    ]
    assert [c["source_class"] for c in record["domains"][1]["components"]] == [
        "authority_model",
        "invariants",
    ]
    assert record["activation"] == {
        "status": "BLOCKED",
        "blocked_by": ["added_selection_review", "cross_domain_composition"],
    }
    assert record["admitted"] is False
    assert record["cross_domain_composition"] == "not_produced"


def test_absent_binding_bundle_is_blocked(authority: Authority, tmp_path: Path) -> None:
    _refused(
        _verify(authority, tmp_path / "nowhere"), "BLOCKED", "BLOCKED_UPSTREAM_PROJECTION_PRODUCER"
    )


def test_binding_not_in_the_pinned_catalog_is_blocked(authority: Authority, bundle: Path) -> None:
    _refused(
        _verify(authority, bundle, "--binding-ref", "l9.domain-consumer-binding/other@1"),
        "BLOCKED",
        "BINDING_UNRESOLVED",
    )


def test_changed_canonical_binding_makes_the_bundle_stale(
    authority: Authority, bundle: Path
) -> None:
    authority.amend(_binding(unresolved=[]))
    _refused(_verify(authority, bundle), "STALE", "BINDING_DIGEST_NOT_CURRENT")


def test_bundle_cut_outside_the_pin_history_is_stale(authority: Authority, bundle: Path) -> None:
    lock = _lock(bundle)
    lock["authority"]["revision"] = "e" * 40
    _save(bundle, lock)
    _refused(_verify(authority, bundle), "STALE", "LOCK_REVISION_NOT_IN_PIN_HISTORY")


def test_missing_required_domain_is_rejected(authority: Authority, bundle: Path) -> None:
    lock = _lock(bundle)
    lock["domains"] = lock["domains"][:1]
    _save(bundle, lock)
    shutil.rmtree(bundle / "gamma")
    _refused(_verify(authority, bundle), "REJECTED", "BINDING_DOMAINS_MISMATCH")


def test_conditional_domain_promoted_into_the_lock_is_rejected(
    authority: Authority, bundle: Path
) -> None:
    lock = _lock(bundle)
    lock["domains"].append({**lock["domains"][0], "profile": {"ref": "l9.projection/delta@1"}})
    _save(bundle, lock)
    _refused(_verify(authority, bundle), "REJECTED", "CONDITIONAL_DOMAIN_MATERIALIZED")


def test_conditional_domain_materialized_on_disk_is_rejected(
    authority: Authority, bundle: Path
) -> None:
    shutil.copytree(bundle / "gamma", bundle / "delta")
    _refused(_verify(authority, bundle), "REJECTED", "CONDITIONAL_DOMAIN_MATERIALIZED")


def test_hidden_unresolved_coordinate_is_rejected(authority: Authority, bundle: Path) -> None:
    lock = _lock(bundle)
    lock["unresolved"] = []
    lock["activation"] = {"status": "blocked", "blocked_by": ["cross_domain_composition"]}
    _save(bundle, lock)
    _refused(_verify(authority, bundle), "REJECTED", "BINDING_UNRESOLVED_MISMATCH")


@pytest.mark.parametrize(
    "activation",
    [
        {"status": "active", "blocked_by": []},
        {"status": "blocked", "blocked_by": ["cross_domain_composition"]},
    ],
)
def test_overclaimed_activation_is_rejected(
    authority: Authority, bundle: Path, activation: dict[str, Any]
) -> None:
    lock = _lock(bundle)
    lock["activation"] = activation
    _save(bundle, lock)
    _refused(_verify(authority, bundle), "REJECTED", "ACTIVATION_OVERCLAIMED")


def test_claimed_cross_domain_composition_is_rejected(authority: Authority, bundle: Path) -> None:
    lock = _lock(bundle)
    lock["cross_domain_composition"]["status"] = "produced"
    _save(bundle, lock)
    _refused(_verify(authority, bundle), "REJECTED", "COMPOSITION_OVERCLAIMED")


def test_composed_view_beside_the_bundle_is_rejected(authority: Authority, bundle: Path) -> None:
    (bundle / "composed.json").write_text("{}\n")
    _refused(_verify(authority, bundle), "REJECTED", "COMPOSITION_OVERCLAIMED")


def test_domain_lock_bytes_bound_by_the_index(authority: Authority, bundle: Path) -> None:
    victim = bundle / "gamma/bundle.lock.json"
    victim.write_bytes(victim.read_bytes() + b"\n")
    _refused(_verify(authority, bundle), "REJECTED", "DOMAIN_LOCK_BYTES_MISMATCH")


def test_domain_artifact_byte_change_is_rejected_by_the_shared_bundle_check(
    authority: Authority, bundle: Path
) -> None:
    victim = bundle / "alpha_beta/projections/contracts.projection.json"
    victim.write_bytes(victim.read_bytes() + b" ")
    _refused(_verify(authority, bundle), "REJECTED", "BUNDLE_BYTES_MISMATCH")


def test_domain_cut_by_another_producer_is_rejected(authority: Authority, bundle: Path) -> None:
    lock = _lock(bundle)
    lock["producer"]["revision"] = "d" * 40
    _save(bundle, lock)
    _refused(_verify(authority, bundle), "REJECTED", "DOMAIN_PRODUCER_MISMATCH")


# --- Committed pin --------------------------------------------------------------------------


def test_committed_pin_names_what_the_driver_and_verifier_use() -> None:
    pin = yaml.safe_load(PIN.read_text())
    ref = pin["upstream"]["binding_ref"]
    assert ref in producer.BINDINGS
    assert Path(pin["bundle"]["path"]) == producer.BINDINGS[ref]["output"]
    assert pin["bundle"]["lock_schema"] == producer.BINDING_LOCK_SCHEMA
    spec = importlib.util.spec_from_file_location("domain_binding_verifier", VERIFIER)
    assert spec and spec.loader
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    assert verifier.CODING_AGENT_DOMAIN_BINDING == ref
    assert verifier.BINDING_LOCK_SCHEMA == pin["bundle"]["lock_schema"]
    # A candidate pin: it names its blockers and never claims activation.
    assert pin["status"] == "candidate" and pin["activation"]["status"] == "blocked"
    assert {b["coordinate"] for b in pin["activation"]["blocked_by"]} >= {
        "added_selection_review",
        "cross_domain_composition",
    }
