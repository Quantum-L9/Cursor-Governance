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
        {"REJECTED": 1, "BLOCKED": 3, "STALE": 4}[status],
        status,
        reason,
    ), report
    state = report["architecture_intelligence"]
    assert state["load_status"] == "NOT_LOADED" and state["fallback_used"] is False
    return report


def test_committed_bundle_binds_and_records_provenance() -> None:
    code, report = _verify()
    assert code == 0 and report["status"] == "BOUND", report
    state = report["architecture_intelligence"]
    pins = yaml.safe_load(BINDING.read_text())["input"]["authority"]
    lock = json.loads((BUNDLE / "bundle.lock.json").read_text())
    assert state["projection_profile"] == {
        "ref": pins["projection_profile_ref"],
        "digest": pins["projection_profile_digest"],
    }
    assert state["composition_digest"] == lock["composed"]["composition_digest"]
    assert sorted(state["component_digests"]) == sorted(pins["expected_source_classes"])
    assert state["authority_revision"] == lock["authority"]["revision"]
    assert state["fallback_used"] is False and state["load_status"] == "LOADED"
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
        _verify("--authority-root", str(authority), "--expect-revision", head),
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
