"""GAR's architecture-intelligence consumer path: verify, record provenance, refuse closed."""

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

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]
PACK = REPO / "skills/l9-global-architect"
VERIFIER = PACK / "scripts/verify_architecture_intelligence.py"
BINDING = PACK / "integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml"
BUNDLE = REPO / "generated/governance/architecture_intelligence"
PRODUCER = REPO / "tools/authority/produce_architecture_intelligence.py"
RUN_STATE = PACK / "runtime/RUN_STATE.yaml"
OBSERVER = "l9.projection/gar-architecture-observer@1"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _verify(*args: str) -> tuple[int, dict]:
    completed = subprocess.run(
        [sys.executable, str(VERIFIER), *args], capture_output=True, text=True, env=ENV
    )
    return completed.returncode, json.loads(completed.stdout)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@invalid", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class Bundle:
    """A writable copy of the committed bundle whose lock follows every rewrite."""

    def __init__(self, root: Path) -> None:
        self.root = root
        shutil.copytree(BUNDLE, root)

    def lock(self) -> dict:
        return json.loads((self.root / "bundle.lock.json").read_text())

    def save_lock(self, lock: dict) -> None:
        (self.root / "bundle.lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True))

    def read(self, rel: str) -> dict:
        return json.loads((self.root / rel).read_text())

    def write(self, rel: str, document: dict) -> None:
        """Write *document* and refresh the lock's byte digest for it (a coherent forgery)."""
        raw = json.dumps(document, indent=2, sort_keys=True).encode()
        (self.root / rel).write_bytes(raw)
        lock = self.lock()
        sha = "sha256:" + hashlib.sha256(raw).hexdigest()
        for entry in [*lock["components"], lock["composed"]]:
            if entry["path"] == rel:
                entry["sha256"] = sha
        self.save_lock(lock)

    def verify(self, *args: str) -> tuple[int, dict]:
        return _verify("--bundle", str(self.root), *args)


@pytest.fixture
def bundle(tmp_path: Path) -> Bundle:
    return Bundle(tmp_path / "bundle")


def _refused(result: tuple[int, dict], status: str, reason: str) -> dict:
    code, report = result
    assert (code, report["status"], report["reason"]) == (
        {"REJECTED": 1, "BLOCKED": 3, "STALE": 4, "BUNDLE_VERIFIED": 5}[status],
        status,
        reason,
    ), report
    state = report["architecture_intelligence"]
    assert state["load_status"] == "NOT_LOADED" and state["fallback_used"] is False
    return report


def test_admitted_mode_requires_an_authority_checkout() -> None:
    # No authority checkout, no admission: the old "BOUND, currentness NOT_CHECKED" is gone.
    _refused(_verify(), "BLOCKED", "AUTHORITY_ROOT_REQUIRED")


def test_committed_bundle_verifies_as_a_non_authoritative_candidate() -> None:
    code, report = _verify("--mode", "candidate")
    assert code == 5 and report["status"] == "BUNDLE_VERIFIED", report
    assert report["authority_status"] == "NOT_EVALUATED"
    state = report["architecture_intelligence"]
    assert state["authoritative"] is False and state["load_status"] == "LOADED_AS_CANDIDATE"
    assert state["production_attested_by_verifier"] is False
    limitation = state["assurance_limitations"][0]
    assert limitation["forbidden_category"] == "unrelated_domain_payloads"
    assert limitation["independent_restrictive_power"] is False
    pins = yaml.safe_load(BINDING.read_text())["input"]["authority"]
    lock = json.loads((BUNDLE / "bundle.lock.json").read_text())
    assert state["projection_profile"] == {
        "ref": pins["projection_profile_ref"],
        "digest": pins["projection_profile_digest"],
    }
    assert state["composition_digest"] == lock["composed"]["composition_digest"]
    assert sorted(state["component_digests"]) == sorted(pins["expected_source_classes"])
    assert state["authority_revision"] == lock["authority"]["revision"]
    assert state["fallback_used"] is False
    composed = json.loads((BUNDLE / "composed.json").read_text())
    assert list(composed["payload"]) == sorted(pins["expected_source_classes"])


def test_absent_bundle_blocks_without_fallback(tmp_path: Path) -> None:
    report = _refused(
        _verify("--bundle", str(tmp_path / "absent")),
        "BLOCKED",
        "ARCHITECTURE_INTELLIGENCE_BUNDLE_ABSENT",
    )
    assert report["architecture_intelligence"]["status"] == "UNAVAILABLE"


def test_observer_projection_is_never_accepted(bundle: Bundle) -> None:
    lock = bundle.lock()
    lock["projection_profile"]["ref"] = OBSERVER
    bundle.save_lock(lock)
    _refused(bundle.verify(), "REJECTED", "PROJECTION_PROFILE_MISMATCH")


def test_wrong_envelope_schema_is_rejected(bundle: Bundle) -> None:
    composed = bundle.read("composed.json")
    composed["schema"] = "l9.composed-projection/v0"
    composed["composition_digest"] = _digest(
        {k: v for k, v in composed.items() if k != "composition_digest"}
    )
    bundle.write("composed.json", composed)
    _refused(bundle.verify(), "REJECTED", "WRONG_ENVELOPE_SCHEMA")


def test_wrong_payload_schema_is_rejected(bundle: Bundle) -> None:
    rel = bundle.lock()["composed"]["receipt"]
    receipt = bundle.read(rel)
    receipt["verification_basis"]["criteria"]["payload_schema"]["schema"] = (
        "l9.composed-projection.consumer-view/v1"
    )
    receipt["receipt_digest"] = _digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
    bundle.write(rel, receipt)
    _refused(bundle.verify(), "REJECTED", "PAYLOAD_SCHEMA_MISMATCH")


def test_missing_component_is_rejected(bundle: Bundle) -> None:
    lock = bundle.lock()
    lock["components"].pop(3)
    bundle.save_lock(lock)
    _refused(bundle.verify(), "REJECTED", "MISSING_COMPONENT")


def test_duplicate_source_is_rejected(bundle: Bundle) -> None:
    lock = bundle.lock()
    lock["components"].append(dict(lock["components"][0]))
    bundle.save_lock(lock)
    _refused(bundle.verify(), "REJECTED", "DUPLICATE_SOURCE")


def test_namespace_diverging_from_its_component_is_rejected(bundle: Bundle) -> None:
    composed = bundle.read("composed.json")
    composed["payload"]["invariants"]["invariants"][0]["statement"] = "rewritten"
    composed["composition_digest"] = _digest(
        {k: v for k, v in composed.items() if k != "composition_digest"}
    )
    bundle.write("composed.json", composed)
    lock = bundle.lock()
    lock["composed"]["composition_digest"] = composed["composition_digest"]
    bundle.save_lock(lock)
    _refused(bundle.verify(), "REJECTED", "NAMESPACE_PAYLOAD_DIVERGENCE")


def test_unlocked_byte_change_is_rejected(bundle: Bundle) -> None:
    path = bundle.root / bundle.lock()["components"][0]["path"]
    path.write_bytes(path.read_bytes() + b"\n")
    _refused(bundle.verify(), "REJECTED", "BUNDLE_BYTES_MISMATCH")


def test_receipt_that_is_not_pass_is_rejected(bundle: Bundle) -> None:
    rel = bundle.lock()["components"][0]["receipt"]
    receipt = bundle.read(rel)
    receipt["result"] = "unknown"
    receipt["receipt_digest"] = _digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
    bundle.write(rel, receipt)
    _refused(bundle.verify(), "REJECTED", "RECEIPT_RESULT_NOT_PASS")


def test_bundle_from_another_authority_revision_is_stale(tmp_path: Path) -> None:
    authority = tmp_path / "authority"
    authority.mkdir()
    _git(authority, "init", "-q")
    _git(authority, "commit", "-q", "--allow-empty", "-m", "newer authority")
    head = _git(authority, "rev-parse", "HEAD")
    _refused(
        _verify(
            "--mode", "candidate", "--authority-root", str(authority), "--expect-revision", head
        ),
        "STALE",
        "AUTHORITY_REVISION_MISMATCH",
    )


def _module():
    spec = importlib.util.spec_from_file_location("verify_ai", VERIFIER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # The pack forbids residue directories (validate_runtime_alignment.py), so the in-process
    # import must not leave scripts/__pycache__ behind.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def test_changed_source_bytes_are_stale(tmp_path: Path) -> None:
    module = _module()
    lock = json.loads((BUNDLE / "bundle.lock.json").read_text())
    component = lock["components"][0]
    authority = tmp_path / "authority"
    (authority / "semantics").mkdir(parents=True)
    (authority / "semantics/canonical_sources.yaml").write_text(
        yaml.safe_dump({"sources": [{"id": component["source_ref"], "path": "semantics/x.yaml"}]})
    )
    (authority / "semantics/x.yaml").write_text("changed: true\n")
    _git(authority, "init", "-q")
    _git(authority, "add", "-A")
    _git(authority, "commit", "-q", "-m", "changed source")
    head = _git(authority, "rev-parse", "HEAD")
    lock["authority"]["revision"] = head
    lock["components"] = [component]
    binding = yaml.safe_load(BINDING.read_text())
    with pytest.raises(module.Outcome) as caught:
        module.verify_currentness(authority, head, lock, binding)
    assert (caught.value.status, caught.value.reason) == ("STALE", "SOURCE_DIGEST_NOT_CURRENT")


STUB = textwrap.dedent(
    """
    import json, shutil, sys, yaml
    from pathlib import Path
    bundle = Path(sys.argv[1]); command = sys.argv[2]
    lock = json.loads((bundle / "bundle.lock.json").read_text())
    if command == "projection-coordinates":
        print(yaml.safe_dump({"projection_profile": lock["projection_profile"],
              "sources": [{"ref": c["source_ref"], "digest": c["source_digest"]}
                          for c in lock["components"]]}))
    else:
        request = yaml.safe_load(Path(sys.argv[3]).read_text())
        out = Path(request["output_root"]); out.mkdir(parents=True, exist_ok=True)
        entries = ([(c["path"], c["receipt"]) for c in lock["components"]]
                   if command == "project" else [("composed.json", lock["composed"]["receipt"])])
        artifacts = []
        for path, receipt in entries:
            target = out / Path(path).name; shutil.copyfile(bundle / path, target)
            rtarget = out / ("r-" + Path(receipt).name); shutil.copyfile(bundle / receipt, rtarget)
            artifacts.append({"path": str(target), "receipt_path": str(rtarget)})
        print(yaml.safe_dump({"result": "pass", "artifacts": artifacts}))
    """
)


def _coherent_forgery(bundle: Bundle, source_class: str = "invariants") -> str:
    """Rewrite one canonical fact and recompute every digest a hash-only check can see.

    The projection payload, its projection digest, its receipt (output digest and receipt
    digest), the composed namespace, the composed component list, the composition digest, the
    composed receipt and every lock hash are all made mutually consistent. Source digests are
    untouched, so currentness against the authority checkout still holds. Returns the forged
    statement."""
    forged = "FORGED: this invariant was never admitted"
    lock = bundle.lock()
    entry = next(c for c in lock["components"] if c["source_class"] == source_class)
    artifact = bundle.read(entry["path"])
    artifact["payload"][source_class][0]["statement"] = forged
    artifact["projection_digest"] = _digest(
        {k: v for k, v in artifact.items() if k != "projection_digest"}
    )
    bundle.write(entry["path"], artifact)
    receipt = bundle.read(entry["receipt"])
    receipt["output"]["digest"] = artifact["projection_digest"]
    receipt["receipt_digest"] = _digest({k: v for k, v in receipt.items() if k != "receipt_digest"})
    (bundle.root / entry["receipt"]).write_text(json.dumps(receipt, indent=2, sort_keys=True))
    composed = bundle.read("composed.json")
    composed["payload"][source_class] = artifact["payload"]
    for component in composed["components"]:
        if component["source_class"] == source_class:
            component["projection_digest"] = artifact["projection_digest"]
    composed["composition_digest"] = _digest(
        {k: v for k, v in composed.items() if k != "composition_digest"}
    )
    bundle.write("composed.json", composed)
    composed_receipt = bundle.read(lock["composed"]["receipt"])
    composed_receipt["output"]["digest"] = composed["composition_digest"]
    composed_receipt["receipt_digest"] = _digest(
        {k: v for k, v in composed_receipt.items() if k != "receipt_digest"}
    )
    (bundle.root / lock["composed"]["receipt"]).write_text(
        json.dumps(composed_receipt, indent=2, sort_keys=True)
    )
    lock = bundle.lock()
    for component in lock["components"]:
        if component["source_class"] == source_class:
            component["projection_digest"] = artifact["projection_digest"]
    lock["composed"]["composition_digest"] = composed["composition_digest"]
    bundle.save_lock(lock)
    return forged


def _fixture_authority(tmp_path: Path) -> tuple[Path, str]:
    authority = tmp_path / "authority"
    (authority / "semantics").mkdir(parents=True)
    # The driver re-derives the composition pin from the authority checkout; the fixture
    # authority declares an entry, so the regenerated pin is checked by the driver itself.
    (authority / "semantics/composition_profiles.yaml").write_text(
        yaml.safe_dump({"profiles": [{"id": "l9.compose/architecture-intelligence@1"}]})
    )
    _git(authority, "init", "-q")
    _git(authority, "add", "-A")
    _git(authority, "commit", "-q", "-m", "fixture authority")
    return authority, _git(authority, "rev-parse", "HEAD")


def _replay(tmp_path: Path, committed: Path) -> subprocess.CompletedProcess[str]:
    """The canonical-producer replay gate: regenerate with the producer and byte-compare.

    The stub stands in for the pinned compiler: it emits the canonical artifacts (the bytes
    the real compiler produced, kept in the repository's committed bundle), not whatever the
    candidate bundle under test contains."""
    authority, head = _fixture_authority(tmp_path)
    stub = tmp_path / "stub_compiler.py"
    stub.write_text(STUB)
    lock = json.loads((BUNDLE / "bundle.lock.json").read_text())
    return subprocess.run(
        [
            sys.executable,
            str(PRODUCER),
            "--authority-root",
            str(authority),
            "--authority-revision",
            head,
            "--compiler-revision",
            lock["producer"]["revision"],
            "--compiler",
            f"{sys.executable} {stub} {BUNDLE}",
            "--output",
            str(committed),
            "--check",
        ],
        env=ENV,
        capture_output=True,
        text=True,
    )


def test_coherent_forgery_passes_hash_checks_but_fails_producer_replay(
    tmp_path: Path, bundle: Bundle
) -> None:
    forged = _coherent_forgery(bundle)
    # Every digest is self-consistent, so the structural verifier cannot tell: that is the
    # boundary AIB-006 states. Hash checks prove integrity, never production.
    code, report = bundle.verify("--mode", "candidate")
    assert code == 5 and report["bundle_status"] == "BUNDLE_VERIFIED", report
    assert forged in (bundle.root / "composed.json").read_text()
    # The canonical-producer replay regenerates from the canonical compiler output and refuses.
    replay = _replay(tmp_path / "replay", bundle.root)
    clean = _replay(tmp_path / "clean", BUNDLE)
    lock = bundle.lock()
    entry = next(c for c in lock["components"] if c["source_class"] == "invariants")
    # Control: the untampered committed bundle drifts only in bundle.lock.json, because the
    # fixture authority's revision is not the one the committed lock names.
    assert clean.returncode == 1 and _drift(clean) == {"bundle.lock.json"}, clean.stderr
    # The forgery drifts additionally in every rewritten artifact: the replay refuses it.
    assert replay.returncode == 1, replay.stderr
    assert _drift(replay) == {
        "bundle.lock.json",
        "composed.json",
        entry["path"],
        entry["receipt"],
        lock["composed"]["receipt"],
    }, replay.stderr


def _drift(completed: subprocess.CompletedProcess[str]) -> set[str]:
    lines = completed.stderr.splitlines()
    assert lines and lines[0] == "stale architecture-intelligence bundle:", completed.stderr
    return {line.strip() for line in lines[1:] if line.strip()}


def test_producer_check_detects_drift(tmp_path: Path) -> None:
    lock = json.loads((BUNDLE / "bundle.lock.json").read_text())
    authority = tmp_path / "authority"
    (authority / "semantics").mkdir(parents=True)
    # The driver re-derives the composition pin from the authority checkout; the fixture
    # authority declares an entry, so the regenerated pin is checked by the driver itself.
    (authority / "semantics/composition_profiles.yaml").write_text(
        yaml.safe_dump({"profiles": [{"id": "l9.compose/architecture-intelligence@1"}]})
    )
    _git(authority, "init", "-q")
    _git(authority, "add", "-A")
    _git(authority, "commit", "-q", "-m", "fixture authority")
    head = _git(authority, "rev-parse", "HEAD")
    stub = tmp_path / "stub_compiler.py"
    stub.write_text(STUB)
    compiler = f"{sys.executable} {stub} {BUNDLE}"
    out = tmp_path / "produced"
    args = [
        sys.executable,
        str(PRODUCER),
        "--authority-root",
        str(authority),
        "--authority-revision",
        head,
        "--compiler-revision",
        lock["producer"]["revision"],
        "--compiler",
        compiler,
        "--output",
        str(out),
    ]
    assert subprocess.run(args, env=ENV, capture_output=True).returncode == 0
    produced = json.loads((out / "bundle.lock.json").read_text())
    assert [c["sha256"] for c in produced["components"]] == [
        c["sha256"] for c in lock["components"]
    ]
    assert subprocess.run([*args, "--check"], env=ENV, capture_output=True).returncode == 0
    victim = out / produced["components"][0]["path"]
    victim.write_bytes(victim.read_bytes() + b" ")
    drift = subprocess.run([*args, "--check"], env=ENV, capture_output=True, text=True)
    assert drift.returncode == 1 and produced["components"][0]["path"] in drift.stderr


# --- Authority separation (audit F1) and source-set closure (audit F3) -----------------------


class Authority:
    """A real git authority with canonical_sources, one source per class, and both profiles."""

    PROFILE = "l9.projection/architecture-intelligence@1"
    COMPOSITION = "l9.compose/architecture-intelligence@1"

    def __init__(self, root: Path, classes: tuple[str, ...] = ("alpha", "beta")) -> None:
        self.root = root
        (root / "semantics").mkdir(parents=True)
        _git(root, "init", "-q", "-b", "trunk")
        self.write_sources(classes)
        self.commit("canonical authority")
        _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")

    def write_sources(self, classes: tuple[str, ...], profile_classes=None) -> None:
        semantics = self.root / "semantics"
        (semantics / "canonical_sources.yaml").write_text(
            yaml.safe_dump(
                {
                    "sources": [
                        {"id": f"l9.source/{c}@1", "path": f"semantics/{c}.yaml"} for c in classes
                    ]
                }
            )
        )
        for c in classes:
            (semantics / f"{c}.yaml").write_text(f"{c}: [fact]\n")
        (semantics / "projection_profiles.yaml").write_text(
            yaml.safe_dump(
                {
                    "projection_profiles": [
                        {
                            "id": self.PROFILE,
                            "sources": {
                                c: {"selectors": [f"$.{c}"]} for c in (profile_classes or classes)
                            },
                        }
                    ]
                },
                sort_keys=False,
            )
        )
        (semantics / "composition_profiles.yaml").write_text(
            yaml.safe_dump({"profiles": [{"id": self.COMPOSITION}]})
        )

    def commit(self, message: str) -> str:
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return _git(self.root, "rev-parse", "HEAD")

    def profile_entry(self, revision: str, catalog: str, collection: str, ref: str) -> dict:
        raw = _git(self.root, "show", f"{revision}:semantics/{catalog}")
        return next(p for p in yaml.safe_load(raw)[collection] if p["id"] == ref)

    def lock_and_binding(self, revision: str) -> tuple[dict, dict]:
        """The lock and binding a producer at *revision* would pair with this authority."""
        registry = yaml.safe_load(
            _git(self.root, "show", f"{revision}:semantics/canonical_sources.yaml")
        )
        components = []
        for source in registry["sources"]:
            raw = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{revision}:{source['path']}"],
                check=True,
                capture_output=True,
            ).stdout
            components.append(
                {
                    "source_ref": source["id"],
                    "source_digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
                }
            )
        projection = self.profile_entry(
            revision, "projection_profiles.yaml", "projection_profiles", self.PROFILE
        )
        binding = yaml.safe_load(BINDING.read_text())
        pins = binding["input"]["authority"]
        pins["projection_profile_digest"] = _digest(projection)
        pins["composition_profile_digest"] = _digest(
            self.profile_entry(revision, "composition_profiles.yaml", "profiles", self.COMPOSITION)
        )
        pins["expected_source_classes"] = list(projection["sources"])
        lock = {
            "authority": {"repository": "Quantum-L9/.github", "revision": revision},
            "components": components,
        }
        return lock, binding


@pytest.fixture
def authority(tmp_path: Path) -> Authority:
    return Authority(tmp_path / "authority")


def test_valid_candidate_revision_that_is_not_admitted(authority: Authority) -> None:
    module = _module()
    _git(authority.root, "switch", "-q", "-c", "candidate")
    (authority.root / "semantics/alpha.yaml").write_text("alpha: [candidate fact]\n")
    candidate = authority.commit("candidate release")
    main_tip = module.resolve_authority_main(authority.root, None)
    assert main_tip != candidate
    lock, binding = authority.lock_and_binding(candidate)
    # The bundle is perfectly current at the revision it names...
    module.verify_currentness(authority.root, candidate, lock, binding)
    # ...but that revision is not integrated into main, so it is not admitted law.
    admission = module.resolve_admission(authority.root, candidate, main_tip, lock, binding)
    assert (admission["status"], admission["reason"]) == (
        "NOT_ADMITTED",
        "AUTHORITY_REVISION_NOT_INTEGRATED",
    )


def test_integrated_revision_stays_admission_unresolved(authority: Authority) -> None:
    # Integration into main is necessary, not sufficient: no admission decision record exists.
    module = _module()
    head = _git(authority.root, "rev-parse", "HEAD")
    lock, binding = authority.lock_and_binding(head)
    admission = module.resolve_admission(authority.root, head, head, lock, binding)
    assert (admission["status"], admission["reason"]) == (
        "ADMISSION_UNRESOLVED",
        "ADMISSION_DECISION_RECORD_UNDEFINED",
    )
    assert admission["integrated"] is True and admission["current_at_authority_main"] is True
    assert "explicit_decision_record" in admission["decision_record_required_by"]


def test_integrated_revision_whose_sources_changed_on_main_is_stale(
    authority: Authority,
) -> None:
    module = _module()
    produced = _git(authority.root, "rev-parse", "HEAD")
    lock, binding = authority.lock_and_binding(produced)
    (authority.root / "semantics/beta.yaml").write_text("beta: [changed on main]\n")
    tip = authority.commit("main moves on")
    with pytest.raises(module.Outcome) as caught:
        module.resolve_admission(authority.root, produced, tip, lock, binding)
    assert (caught.value.status, caught.value.reason) == ("STALE", "NOT_CURRENT_AT_AUTHORITY_MAIN")
    assert caught.value.detail["cause"] == "SOURCE_DIGEST_NOT_CURRENT"


def test_main_is_resolved_from_the_authority_not_the_lock(authority: Authority) -> None:
    module = _module()
    _git(authority.root, "update-ref", "-d", "refs/remotes/origin/main")
    with pytest.raises(module.Outcome) as caught:
        module.resolve_authority_main(authority.root, None)
    assert (caught.value.status, caught.value.reason) == ("BLOCKED", "AUTHORITY_MAIN_UNRESOLVED")
    with pytest.raises(module.Outcome) as caught:
        module.resolve_authority_main(authority.root, "0" * 40)
    assert caught.value.reason == "AUTHORITY_MAIN_UNRESOLVED"


def test_committed_bundle_is_not_admitted_against_an_authority_lacking_its_revision(
    authority: Authority,
) -> None:
    # The real bundle names .github 1d87032. Against an authority whose main does not contain
    # it, admitted mode verifies the bundle but refuses to load it.
    code, report = _verify(
        "--authority-root", str(authority.root), "--cite", "invariants:/invariants/0"
    )
    assert code == 5 and report["status"] == "BUNDLE_VERIFIED", report
    assert report["authority_status"] == "NOT_ADMITTED"
    state = report["architecture_intelligence"]
    assert state["load_status"] == "NOT_LOADED" and state["authoritative"] is False
    assert state["refusal_reason"] == "AUTHORITY_REVISION_NOT_INTEGRATED"
    assert report["citation"]["refused"] == "CITATION_REFUSED_NOT_LOADED"
    assert "value" not in report["citation"]


@pytest.mark.parametrize(
    ("binding_classes", "reason_field"),
    [
        (("alpha",), "missing_from_binding"),  # profile gains a source; binding not updated
        (("alpha", "beta", "gamma"), "absent_from_profile"),
        (("beta", "alpha"), "order_differs"),
    ],
)
def test_expected_source_set_must_equal_the_canonical_profile(
    authority: Authority, binding_classes: tuple[str, ...], reason_field: str
) -> None:
    module = _module()
    head = _git(authority.root, "rev-parse", "HEAD")
    lock, binding = authority.lock_and_binding(head)
    # The digest pin is current (a partial binding update); only the class list drifted.
    binding["input"]["authority"]["expected_source_classes"] = list(binding_classes)
    with pytest.raises(module.Outcome) as caught:
        module.verify_currentness(authority.root, head, lock, binding)
    assert (caught.value.status, caught.value.reason) == (
        "REJECTED",
        "EXPECTED_SOURCE_SET_MISMATCH",
    )
    assert caught.value.detail[reason_field]


def test_canonical_profile_gaining_a_source_is_caught_even_with_a_matching_digest_pin(
    authority: Authority,
) -> None:
    module = _module()
    authority.write_sources(("alpha", "beta"), profile_classes=("alpha", "beta", "gamma"))
    (authority.root / "semantics/gamma.yaml").write_text("gamma: [new]\n")
    head = authority.commit("profile gains gamma")
    lock, binding = authority.lock_and_binding(head)
    binding["input"]["authority"]["expected_source_classes"] = ["alpha", "beta"]
    with pytest.raises(module.Outcome) as caught:
        module.verify_currentness(authority.root, head, lock, binding)
    assert caught.value.reason == "EXPECTED_SOURCE_SET_MISMATCH"
    assert caught.value.detail["missing_from_binding"] == ["gamma"]


def test_committed_binding_equals_the_pinned_profile_sources() -> None:
    # The committed bundle carries the canonical profile's own source order in composition order.
    pins = yaml.safe_load(BINDING.read_text())["input"]["authority"]
    composed = json.loads((BUNDLE / "composed.json").read_text())
    assert [c["source_class"] for c in composed["components"]] == pins["expected_source_classes"]


# --- GAR session: verify, record provenance, cite a namespaced fact (audit F4) ---------------


class Session:
    """One GAR run's `$.architecture_intelligence` slot and append-only event log, built from
    runtime/RUN_STATE.yaml exactly as the bootloader instantiates it."""

    def __init__(self) -> None:
        spec = yaml.safe_load(RUN_STATE.read_text())
        self.spec = spec
        self.state = json.loads(json.dumps(spec["instance_template"]["architecture_intelligence"]))
        self.events: list[dict] = []

    def event(self, event_type: str, summary: str, **extra: object) -> None:
        assert event_type in self.spec["event_model"]["permitted_event_types"], event_type
        self.events.append(
            {
                "event_id": f"evt-{len(self.events) + 1}",
                "occurred_at": "2026-10-15T00:00:00Z",
                "event_type": event_type,
                "state": self.state["status"],
                "summary": summary,
                **extra,
            }
        )

    def load(self, *args: str, cite: str) -> dict:
        # Step 1: verify and record provenance. Step 2: read only through the recorded slot.
        code, report = _verify(*args)
        record = report["architecture_intelligence"]
        # The verifier owns every slot field but the session's citations: a verdict replaces the
        # slot whole, so nothing from an earlier verdict survives into this one.
        assert set(record) == set(self.state) - {"citations"}, set(record) ^ set(self.state)
        self.state = {**record, "citations": self.state["citations"]}
        if record["load_status"] == "NOT_LOADED":
            self.event("ARCHITECTURE_INTELLIGENCE_REFUSED", report["reason"])
            return report
        self.event(
            "ARCHITECTURE_INTELLIGENCE_ADMITTED"
            if record["authoritative"]
            else "ARCHITECTURE_INTELLIGENCE_CANDIDATE_INSPECTED",
            report["reason"],
        )
        _, cited = _verify(*args, "--cite", cite)
        citation = cited["citation"]
        self.state["citations"].append(citation)
        self.event(
            "ARCHITECTURE_INTELLIGENCE_FACT_CITED",
            f"{citation['source_class']} {citation['namespace_pointer']}",
            evidence_refs=[citation["source_ref"], citation["projection_digest"]],
        )
        return cited


def test_gar_session_cites_a_namespaced_fact_with_exact_source_provenance() -> None:
    session = Session()
    report = session.load("--mode", "candidate", cite="invariants:/invariants/0")
    citation = report["citation"]
    lock = json.loads((BUNDLE / "bundle.lock.json").read_text())
    component = next(c for c in lock["components"] if c["source_class"] == "invariants")
    artifact = json.loads((BUNDLE / component["path"]).read_text())
    # The fact read is the canonical source projection's own record, at an exact address.
    assert citation["value"] == artifact["payload"]["invariants"][0]
    assert citation["value"]["id"] == "L9-AUTH-001"
    assert citation["namespace_pointer"] == "/payload/invariants/invariants/0"
    # Its provenance is the exact source, projection, composition and authority revision.
    assert (citation["source_ref"], citation["source_digest"], citation["projection_digest"]) == (
        component["source_ref"],
        component["source_digest"],
        component["projection_digest"],
    )
    assert citation["composition_digest"] == lock["composed"]["composition_digest"]
    assert citation["authority_revision"] == lock["authority"]["revision"]
    # A candidate read is never admitted law, and the run state says so.
    assert citation["authoritative"] is False and session.state["authoritative"] is False
    assert session.state["load_status"] == "LOADED_AS_CANDIDATE"
    assert [e["event_type"] for e in session.events] == [
        "ARCHITECTURE_INTELLIGENCE_CANDIDATE_INSPECTED",
        "ARCHITECTURE_INTELLIGENCE_FACT_CITED",
    ]
    required = session.spec["event_model"]["required_fields"]
    assert all(set(required) <= set(e) for e in session.events)


def test_gar_session_refuses_unavailable_intelligence(tmp_path: Path) -> None:
    session = Session()
    report = session.load(
        "--bundle", str(tmp_path / "absent"), "--mode", "candidate", cite="invariants:/invariants/0"
    )
    assert report["status"] == "BLOCKED" and session.state["status"] == "UNAVAILABLE"
    assert session.state["citations"] == [] and session.state["fallback_used"] is False
    assert [e["event_type"] for e in session.events] == ["ARCHITECTURE_INTELLIGENCE_REFUSED"]


def test_gar_session_refuses_unauthoritative_intelligence_as_law(authority: Authority) -> None:
    # Admitted mode against an authority whose main lacks the bundle revision: nothing is read.
    session = Session()
    report = session.load("--authority-root", str(authority.root), cite="invariants:/invariants/0")
    assert report["status"] == "BUNDLE_VERIFIED" and report["authority_status"] == "NOT_ADMITTED"
    assert session.state["load_status"] == "NOT_LOADED" and session.state["citations"] == []
    assert [e["event_type"] for e in session.events] == ["ARCHITECTURE_INTELLIGENCE_REFUSED"]


def test_gar_session_refuses_tampered_intelligence(bundle: Bundle) -> None:
    path = bundle.root / bundle.lock()["components"][1]["path"]
    path.write_bytes(path.read_bytes() + b"\n")
    session = Session()
    report = session.load(
        "--bundle", str(bundle.root), "--mode", "candidate", cite="invariants:/invariants/0"
    )
    assert report["status"] == "REJECTED" and session.state["citations"] == []


def test_citation_pointer_must_resolve() -> None:
    _, report = _verify("--mode", "candidate", "--cite", "invariants:/invariants/99999")
    assert report["citation"]["refused"] == "CITATION_POINTER_UNRESOLVED"
    _, report = _verify("--mode", "candidate", "--cite", "nonexistent:/x")
    assert report["citation"]["refused"] == "CITATION_SOURCE_CLASS_UNKNOWN"


def test_a_later_verdict_leaves_nothing_of_an_earlier_one(authority: Authority) -> None:
    # Found by a live GAR session: a candidate load recorded after an admitted-mode refusal kept
    # the refusal's reason, and a refusal after a load would keep the loaded provenance.
    session = Session()
    session.load("--authority-root", str(authority.root), cite="invariants:/invariants/0")
    assert session.state["refusal_reason"] == "AUTHORITY_REVISION_NOT_INTEGRATED"
    session.load("--mode", "candidate", cite="invariants:/invariants/0")
    assert session.state["refusal_reason"] is None
    assert session.state["load_status"] == "LOADED_AS_CANDIDATE"
    assert len(session.state["citations"]) == 1
    session.load("--bundle", "/nonexistent", "--mode", "candidate", cite="invariants:/invariants/0")
    assert session.state["status"] == "UNAVAILABLE"
    assert session.state["component_sources"] == {} and session.state["composition_digest"] is None
    assert [e["event_type"] for e in session.events] == [
        "ARCHITECTURE_INTELLIGENCE_REFUSED",
        "ARCHITECTURE_INTELLIGENCE_CANDIDATE_INSPECTED",
        "ARCHITECTURE_INTELLIGENCE_FACT_CITED",
        "ARCHITECTURE_INTELLIGENCE_REFUSED",
    ]


def test_generation_holds_no_repository_publication_authority() -> None:
    """The bundle workflow and driver generate and verify; they never publish a change."""
    workflow_path = REPO / ".github/workflows/l9-architecture-intelligence-bundle.yml"
    workflow = yaml.safe_load(workflow_path.read_text())
    triggers = workflow[True] if True in workflow else workflow["on"]
    assert set(triggers) == {"pull_request", "push"}
    assert workflow["permissions"] == {"contents": "read"}
    for job in workflow["jobs"].values():
        assert job["permissions"] == {"contents": "read"}
    for text in (workflow_path.read_text(), PRODUCER.read_text()):
        assert "secrets." not in text
        for forbidden in ("git push", '"push"', "git commit", '"commit"', "gh pr", '"gh"'):
            assert forbidden not in text, forbidden
    producer = yaml.safe_load(BINDING.read_text())["input"]["producer"]
    assert "PR_REMEDIATE=0 make pr" in producer["publication"]
