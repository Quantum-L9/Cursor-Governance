"""Synthetic orchestration tests. These do not constitute independent canonical replay."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from script_loader import load_sibling

_binding = load_sibling("verify_sv_binding")
COMPOSITION = _binding.COMPOSITION
CONTRACT = _binding.CONTRACT
MODEL = _binding.MODEL
PROFILE = _binding.PROFILE
REPO = _binding.REPO
SOURCE_CLASSES = _binding.SOURCE_CLASSES
BindingBlocked = _binding.BindingBlocked
read_lock = _binding.read_lock
verify_binding = _binding.verify_binding


class FakeAuthority:
    def __init__(self, root, revision, *, repository):
        assert repository == REPO
        self.root = root
        self.revision = revision

    def resolve_profile(self, ref):
        if ref == PROFILE:
            return SimpleNamespace(
                record={"sources": {s: {"selectors": []} for s in SOURCE_CLASSES}},
                digest="sha256:" + "a" * 64,
                catalog="synthetic-catalog",
            )
        if ref == COMPOSITION:
            return SimpleNamespace(
                record={
                    "composes": {"projection_profile": PROFILE},
                    "required_provenance": [
                        "source_projection_refs",
                        "source_projection_digests",
                        "composition_profile_ref",
                        "composition_profile_digest",
                    ],
                },
                digest=read_lock()["composition_profile_digest"],
            )
        raise RuntimeError("unexpected profile ref")

    def resolve_source(self, catalog, cls):
        return SimpleNamespace(
            ref="l9.source/"
            + ("strategic-value-model" if cls == "strategic_value_model" else cls.replace("_", "-"))
            + "@1"
        )

    def load(self, path):
        return SimpleNamespace(
            document={
                "artifact_id": MODEL,
                "canonical": True,
                "governed_by": {"invariants": ["L9-SV-001", "L9-SV-002"]},
                "identity": {"assessment_contract_ref": CONTRACT},
                "assessment_applicability": {
                    "claim_gate": (
                        "applies_only_to_assessments_asserting_objective_relative_"
                        "quantitative_strategic_value"
                    )
                },
            }
        )


def fake_projection(authority, artifact):
    return {"result": "pass"}


def fake_receipt(authority, artifact, receipt):
    return {"status": "pass"}


def fake_composition(authority, composed, artifacts):
    return {"result": "pass"}


def fake_composed_receipt(authority, composed, artifacts, receipt):
    return {"status": "pass"}


FAKE_ENGINE = (
    FakeAuthority,
    fake_projection,
    fake_receipt,
    fake_composition,
    fake_composed_receipt,
)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = read_lock()
        self.manifest = {
            "schema": "l9.planner-strategic-value-binding-request/v1",
            "authority_revision": self.lock["admission_revision"],
            "projections": [],
            "composition_artifact_path": "composed.json",
            "composition_receipt_path": "composed.receipt.json",
        }
        projections = []
        for cls in sorted(SOURCE_CLASSES):
            sr = FakeAuthority(None, None, repository=REPO).resolve_source("", cls).ref
            art = {
                "source_ref": sr,
                "projection_profile_ref": PROFILE,
                "projection_profile_digest": "sha256:" + "a" * 64,
                "projection_digest": self.lock["producer_projection_digests"][cls],
                "payload": {},
            }
            receipt = {
                "result": "pass",
                "verification_basis": {"coverage": "complete", "unresolved_criteria": []},
                "producer_identity": {"compiler": "l9-semantic-compiler"},
                "governing_coordinates": {
                    "revision": self.lock["admission_revision"],
                    "repository": REPO,
                },
            }
            pa = cls + ".json"
            pr = cls + ".receipt.json"
            (self.root / pa).write_text(json.dumps(art))
            (self.root / pr).write_text(json.dumps(receipt))
            self.manifest["projections"].append(
                {"source_class": cls, "artifact_path": pa, "receipt_path": pr}
            )
            projections.append(art)
        comp = {
            "composition_profile": {
                "ref": COMPOSITION,
                "digest": self.lock["composition_profile_digest"],
            },
            "composition_digest": self.lock["producer_composition_digest"],
            "components": [
                {
                    "projection_ref": PROFILE + "#" + a["source_ref"],
                    "projection_digest": a["projection_digest"],
                }
                for a in projections
            ],
            "payload": {k: {} for k in SOURCE_CLASSES},
        }
        comp_receipt = {
            "result": "pass",
            "verification_basis": {"coverage": "complete", "unresolved_criteria": []},
            "producer_identity": {"compiler": "l9-semantic-compiler"},
            "governing_coordinates": {
                "revision": self.lock["admission_revision"],
                "repository": REPO,
            },
        }
        (self.root / "composed.json").write_text(json.dumps(comp))
        (self.root / "composed.receipt.json").write_text(json.dumps(comp_receipt))
        self.flush()

    def flush(self):
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))

    def run_fake(self):
        return verify_binding(self.root, self.manifest_path, engine=FAKE_ENGINE)

    def test_lock_matches_admitted_not_retired_laws(self):
        self.assertEqual(set(self.lock["new_global_invariants"]), {"L9-SV-001", "L9-SV-002"})
        self.assertEqual(self.lock["release"], "v3.32.0")

    def test_complete_mock_only_not_canonical_bound(self):
        report = self.run_fake()
        self.assertEqual(report["status"], "SYNTHETIC_ADAPTER_TEST_ONLY")
        self.assertEqual(report["source_projection_count"], 5)
        self.assertFalse(report["numerical_model_verified"])

    def test_reject_omitted_source(self):
        self.manifest["projections"].pop()
        self.flush()
        with self.assertRaisesRegex(BindingBlocked, "FIVE_SOURCE"):
            self.run_fake()

    def test_reject_duplicate_class(self):
        self.manifest["projections"][1]["source_class"] = self.manifest["projections"][0][
            "source_class"
        ]
        self.flush()
        with self.assertRaisesRegex(BindingBlocked, "DUPLICATE_SOURCE_CLASS"):
            self.run_fake()

    def test_reject_wrong_admission_sha(self):
        self.manifest["authority_revision"] = "0" * 40
        self.flush()
        with self.assertRaisesRegex(BindingBlocked, "AUTHORITY_REVISION"):
            self.run_fake()

    def test_reject_tampered_projection_digest(self):
        p = self.root / self.manifest["projections"][0]["artifact_path"]
        data = json.loads(p.read_text())
        data["projection_digest"] = "sha256:" + "0" * 64
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(BindingBlocked, "ADMITTED_PRODUCER_DIGEST"):
            self.run_fake()

    def test_reject_incomplete_receipt(self):
        p = self.root / self.manifest["projections"][0]["receipt_path"]
        d = json.loads(p.read_text())
        d["verification_basis"]["coverage"] = "incomplete"
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(BindingBlocked, "UNRESOLVED_PRODUCER_VERIFICATION"):
            self.run_fake()

    def test_reject_wrong_profile(self):
        p = self.root / self.manifest["projections"][0]["artifact_path"]
        d = json.loads(p.read_text())
        d["projection_profile_ref"] = "l9.projection/other@1"
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(BindingBlocked, "WRONG_PROFILE"):
            self.run_fake()

    def test_reject_composition_missing_namespace(self):
        p = self.root / "composed.json"
        d = json.loads(p.read_text())
        d["payload"].pop("contracts")
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(BindingBlocked, "NAMESPACED_PAYLOAD_COVERAGE"):
            self.run_fake()

    def test_reject_composition_wrong_component_digest(self):
        p = self.root / "composed.json"
        d = json.loads(p.read_text())
        d["components"][0]["projection_digest"] = "sha256:" + "0" * 64
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(BindingBlocked, "COMPONENT_COVERAGE_OR_DIGEST"):
            self.run_fake()

    def test_reject_false_composition_pass(self):
        p = self.root / "composed.receipt.json"
        d = json.loads(p.read_text())
        d["result"] = "unknown"
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(BindingBlocked, "NOT_A_PASS_RECEIPT"):
            self.run_fake()

    def test_release_without_artifacts_is_blocked(self):
        with self.assertRaisesRegex(BindingBlocked, "CANONICAL_COMPILER_UNAVAILABLE"):
            verify_binding(self.root, self.manifest_path)


if __name__ == "__main__":
    unittest.main()
