"""Universal campaign ingress: architecture prose promotes without source mutation."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PE_ROOT = Path(__file__).resolve().parents[2]
if str(PE_ROOT) not in sys.path:
    sys.path.append(str(PE_ROOT))
SCRIPT = PE_ROOT / "scripts/campaign_input.py"

from compiler.architecture_intent import (  # noqa: E402
    ArchitectureAdmission,
    load_architecture_intent,
)
from compiler.architecture_target import (  # noqa: E402
    TargetResolutionError,
    resolve_architecture_target,
)


def _load():
    spec = importlib.util.spec_from_file_location("campaign_input_universal_arch", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ARCHITECTURE = """# Virtual Skill Plane

The gateway MUST be the only Cursor-native skill.

## Authority

The router MUST remain the sole semantic routing authority.

## Validation

CI MUST prove native discovery cardinality stays one.

## Rollback

Rollback MUST restore direct discovery without moving canonical skills.
"""


class UniversalArchitectureIngressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ci = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_architecture_grade_prose_auto_promotes(self) -> None:
        path = self.root / "virtual-skill-plane.md"
        path.write_text(ARCHITECTURE, encoding="utf-8")
        before = path.read_bytes()
        found = self.ci.classify(path)
        self.assertIs(found.kind, self.ci.CampaignInputKind.ARCHITECTURE_INTENT_V1)
        self.assertEqual(found.admission, "classified")
        self.assertTrue(found.evidence["qualified"])
        self.assertEqual(path.read_bytes(), before, "classification must not inject frontmatter")

    def test_plain_brief_remains_brief(self) -> None:
        path = self.root / "brief.md"
        path.write_text("# Note\n\nFix the typo in the title.\n", encoding="utf-8")
        found = self.ci.classify(path)
        self.assertIs(found.kind, self.ci.CampaignInputKind.BRIEF)
        self.assertEqual(found.admission, "")

    def test_declared_architecture_is_declared_not_classified(self) -> None:
        path = self.root / "declared.md"
        path.write_text(
            "---\n"
            f"schema: {self.ci.ARCHITECTURE_INTENT_SCHEMA}\n"
            "target: Quantum-L9/Cursor-Governance\n"
            "---\n\n" + ARCHITECTURE,
            encoding="utf-8",
        )
        found = self.ci.classify(path)
        self.assertEqual(found.admission, "declared")

    def test_small_design_cannot_bypass_classifier(self) -> None:
        path = self.root / "tiny.md"
        path.write_text("# Small design\n\nUse the current adapter.\n", encoding="utf-8")
        found = self.ci.classify(path)
        self.assertIs(found.kind, self.ci.CampaignInputKind.BRIEF)
        self.assertEqual(found.admission, "")


class TargetAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_bare_github_reference_is_not_mutation_authority(self) -> None:
        path = self.root / "reference.md"
        path.write_text(
            "# Architecture\n\nUse evidence from https://github.com/Quantum-L9/Donor.\n",
            encoding="utf-8",
        )
        with self.assertRaises(TargetResolutionError):
            resolve_architecture_target(path)

    def test_subject_target_wins_over_incidental_reference(self) -> None:
        path = self.root / "subject.md"
        path.write_text(
            "# Architecture\n\n"
            "This is an architecture review of `Quantum-L9/Target`.\n"
            "Reference: https://github.com/Quantum-L9/Donor\n",
            encoding="utf-8",
        )
        result = resolve_architecture_target(path)
        self.assertEqual(result.repository_id, "Quantum-L9/Target")
        self.assertEqual(result.source, "source_authority_repository")
        self.assertIn("Quantum-L9/Donor", result.reference_candidates)

    def test_explicit_target_cannot_retarget_source_subject(self) -> None:
        path = self.root / "retarget.md"
        path.write_text(
            "# Architecture\n\nThis is an architecture review of `Quantum-L9/Target`.\n",
            encoding="utf-8",
        )
        with self.assertRaises(TargetResolutionError):
            resolve_architecture_target(path, explicit_target="Quantum-L9/Other")

    def test_explicit_target_cannot_contradict_target_checkout(self) -> None:
        checkout = self.root / "explicit-checkout"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "remote",
                "add",
                "origin",
                "https://github.com/Quantum-L9/Other.git",
            ],
            check=True,
        )
        path = self.root / "explicit.md"
        path.write_text("# Architecture\n", encoding="utf-8")
        with self.assertRaises(TargetResolutionError):
            resolve_architecture_target(
                path,
                explicit_target="Quantum-L9/Target",
                target_checkout=checkout,
            )

    def test_source_target_cannot_contradict_target_checkout(self) -> None:
        checkout = self.root / "checkout"
        checkout.mkdir()
        subprocess.run(["git", "init", "-q", str(checkout)], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(checkout),
                "remote",
                "add",
                "origin",
                "https://github.com/Quantum-L9/Other.git",
            ],
            check=True,
        )
        path = self.root / "target.md"
        path.write_text("# Architecture\n\nRepository: Quantum-L9/Target\n", encoding="utf-8")
        with self.assertRaises(TargetResolutionError):
            resolve_architecture_target(path, target_checkout=checkout)

    def test_target_resolution_and_loader_share_source_identity(self) -> None:
        path = self.root / "identity.md"
        path.write_text(
            "# Architecture\r\n\r\nRepository: Quantum-L9/Target\r\n",
            encoding="utf-8",
        )
        resolution = resolve_architecture_target(path)
        intent = load_architecture_intent(
            path,
            target=resolution.repository_id,
            admission=ArchitectureAdmission.CLASSIFIED,
        )
        self.assertEqual(resolution.source_sha256, intent.sha256)


if __name__ == "__main__":
    unittest.main()
