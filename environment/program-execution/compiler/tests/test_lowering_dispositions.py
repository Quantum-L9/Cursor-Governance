"""W5 on the live lowering path — CE-AT-005 / CE-AT-006, not only in shadow.

`repo_truth.classify_dispositions` is the canonical grounding classifier, but
until the disposition reached `architecture_to_campaign.lower()` it had no
production caller: the shadow harness proved the semantics while the live
lowering path still asked `RepositoryFacts.path_exists`, a binary that cannot
tell HARDEN_WIRE_EXISTING from CREATE.

These exercise the real classifier against a real checkout, because the whole
point is grounding in repository truth — a stubbed one would prove nothing.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from compiler.architecture_extractor import (
    ArchitectureExtractorRequest,
    DeterministicExtractor,
    new_request_id,
)
from compiler.architecture_intent import load_architecture_intent
from compiler.architecture_ir import admit
from compiler.architecture_to_campaign import (
    RepositoryFacts,
    _action,
    _requirement_dispositions,
    inspect_repository,
)

#: This checkout. `compiler/intent.py` and `compiler/resolver.py` are real
#: files in it; `compiler/brand_new_thing.py` deliberately is not.
REPO_ROOT = Path(__file__).resolve().parents[4]
EXISTING = "environment/program-execution/compiler/intent.py"
ALSO_EXISTING = "environment/program-execution/compiler/resolver.py"
ABSENT = "environment/program-execution/compiler/brand_new_thing.py"

DOC = f"""# Compiler intent

The existing {EXISTING} MUST stay the strict parser.
The compiler MUST harden {ALSO_EXISTING} for ambiguity.
The compiler MUST create {ABSENT} for the new route.
"""


def _requirements(tmp: Path, text: str = DOC):
    path = tmp / "arch.md"
    path.write_text(text, encoding="utf-8")
    intent = load_architecture_intent(path, target="Quantum-L9/Cursor-Governance", forced=True)
    response = DeterministicExtractor().extract(
        ArchitectureExtractorRequest(
            request_id=new_request_id(),
            mode="extract",
            source_sha256=intent.sha256,
            units=intent.units,
            target=intent.target,
        )
    )
    accepted, _ = admit(response.items, unit_texts={u.id: u.text for u in intent.units})
    return intent, [
        item for item in accepted if item.material and item.kind in {"requirement", "constraint"}
    ]


class LiveDispositionTests(unittest.TestCase):
    def _by_path(self) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as raw:
            _, requirements = _requirements(Path(raw))
            self.assertTrue(requirements, "fixture produced no material requirement")
            facts = inspect_repository(REPO_ROOT, "Quantum-L9/Cursor-Governance")
            rows = _requirement_dispositions(requirements, facts)
            self.assertEqual(
                len(rows),
                len(requirements),
                "CE-AT-005: every material requirement gets an explicit disposition",
            )
            return {
                (rows[item.id].path or ""): rows[item.id].disposition
                for item in requirements
                if item.id in rows
            }

    def test_every_material_requirement_gets_a_disposition(self) -> None:
        """CE-AT-005. No material requirement reaches lowering unclassified."""
        by_path = self._by_path()
        self.assertIn(EXISTING, by_path)
        self.assertIn(ALSO_EXISTING, by_path)

    def test_existing_implementation_is_not_blindly_create(self) -> None:
        """CE-AT-006. The false-CREATE this classifier exists to prevent."""
        by_path = self._by_path()
        self.assertEqual(by_path.get(EXISTING), "KEEP")
        self.assertEqual(by_path.get(ALSO_EXISTING), "HARDEN_WIRE_EXISTING")
        for path, disposition in by_path.items():
            if path:
                self.assertNotEqual(
                    disposition, "CREATE", msg=f"{path} exists but was classified CREATE"
                )

    def test_an_absent_path_is_still_create(self) -> None:
        """Grounding must not turn every obligation into a keep."""
        with tempfile.TemporaryDirectory() as raw:
            _, requirements = _requirements(Path(raw))
            facts = inspect_repository(REPO_ROOT, "Quantum-L9/Cursor-Governance")
            rows = _requirement_dispositions(requirements, facts)
            self.assertIn(
                "CREATE",
                {row.disposition for row in rows.values()},
                msg={item.statement: rows[item.id].disposition for item in requirements},
            )

    def test_disposition_reaches_the_action_wording(self) -> None:
        """The point of grounding: the worker is told to harden, not rebuild."""
        with tempfile.TemporaryDirectory() as raw:
            _, requirements = _requirements(Path(raw))
            facts = inspect_repository(REPO_ROOT, "Quantum-L9/Cursor-Governance")
            rows = _requirement_dispositions(requirements, facts)
            actions = [_action(item, rows.get(item.id)) for item in requirements]
            self.assertTrue(
                any(action.startswith("Preserve the existing ") for action in actions), actions
            )
            self.assertTrue(
                any(action.startswith("Harden and wire the existing ") for action in actions),
                actions,
            )
            # CREATE and UNKNOWN keep the source's own wording.
            self.assertTrue(
                any(action.startswith("The compiler MUST create") for action in actions)
            )

    def test_no_checkout_grounds_nothing_and_never_raises(self) -> None:
        """Best-effort by contract: a classifier failure must not cost tasks."""
        with tempfile.TemporaryDirectory() as raw:
            _, requirements = _requirements(Path(raw))
            facts = RepositoryFacts(root=None, repository_id="Quantum-L9/Cursor-Governance")
            self.assertEqual(_requirement_dispositions(requirements, facts), {})
            for item in requirements:
                self.assertEqual(_action(item, None), _action(item))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
