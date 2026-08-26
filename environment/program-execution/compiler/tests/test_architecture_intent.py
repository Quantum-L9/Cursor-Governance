"""Deterministic source model tests: segmentation, digests, signals, frontmatter."""

from __future__ import annotations

import unittest

from compiler.architecture_intent import (
    ARCHITECTURE_INTENT_SCHEMA,
    ArchitectureIntentError,
    declares_architecture_intent,
    frontmatter_target,
    segment_source,
    unit_signals,
)

DOC = """# Title

First paragraph with an obligation: the router MUST fail closed.

## Section

- item one MUST NOT leak data
- item two is plain

| a | b |
| - | - |
| 1 | 2 |

```sh
echo "inert command; never executed by the compiler"
```

> quoted note

## Attached heading
Prose directly under the heading with no blank line between them.

Closing paragraph.
"""

FRONTMATTER_DOC = (
    "---\n"
    f"schema: {ARCHITECTURE_INTENT_SCHEMA}\n"
    "target: Quantum-L9/LLM-Router\n"
    "---\n\n"
    "# Body\n\nProse.\n"
)


class SegmentationTests(unittest.TestCase):
    def test_equivalent_canonical_source_has_identical_identity(self) -> None:
        first = segment_source(DOC)
        second = segment_source(DOC.replace("\n", "\r\n"))
        self.assertEqual(first.sha256, second.sha256)
        self.assertEqual(
            [(unit.id, unit.sha256, unit.line_start, unit.line_end) for unit in first.units],
            [(unit.id, unit.sha256, unit.line_start, unit.line_end) for unit in second.units],
        )

    def test_material_change_changes_the_digest(self) -> None:
        first = segment_source(DOC)
        second = segment_source(DOC.replace("MUST fail closed", "MAY fail open"))
        self.assertNotEqual(first.sha256, second.sha256)
        changed = [
            unit.id
            for unit, other in zip(first.units, second.units, strict=True)
            if unit.sha256 != other.sha256
        ]
        self.assertEqual(len(changed), 1)

    def test_boundaries_respect_structural_kinds(self) -> None:
        document = segment_source(DOC)
        kinds = [unit.kind for unit in document.units]
        self.assertIn("heading", kinds)
        self.assertIn("heading_and_paragraph", kinds)
        self.assertIn("paragraph", kinds)
        self.assertIn("list_item", kinds)
        self.assertIn("table", kinds)
        self.assertIn("code_fence", kinds)
        self.assertIn("blockquote", kinds)
        # Stable ids in document order, 1-based line ranges.
        self.assertEqual(document.units[0].id, "SRC-0001")
        self.assertEqual(document.units[0].line_start, 1)
        for earlier, later in zip(document.units, document.units[1:], strict=False):
            self.assertLess(earlier.line_end, later.line_start)

    def test_code_fences_carry_no_normative_signals(self) -> None:
        document = segment_source(DOC)
        fence = next(unit for unit in document.units if unit.kind == "code_fence")
        self.assertEqual(fence.signals, ())

    def test_signal_detection_is_deterministic(self) -> None:
        self.assertIn("MUST", unit_signals("The router MUST fail closed."))
        self.assertIn("FAIL CLOSED", unit_signals("The router MUST fail closed."))
        found = unit_signals("This MUST NOT happen.")
        self.assertIn("MUST NOT", found)
        self.assertNotIn("MUST", found)
        self.assertEqual(unit_signals("plain narrative text"), ())

    def test_empty_source_fails_cleanly(self) -> None:
        with self.assertRaises(ArchitectureIntentError):
            segment_source("   \n\n  ")

    def test_frontmatter_is_a_routing_unit(self) -> None:
        document = segment_source(FRONTMATTER_DOC)
        self.assertEqual(document.units[0].kind, "frontmatter")
        self.assertTrue(declares_architecture_intent(FRONTMATTER_DOC))
        self.assertEqual(frontmatter_target(FRONTMATTER_DOC), "Quantum-L9/LLM-Router")
        self.assertFalse(declares_architecture_intent(DOC))


if __name__ == "__main__":
    unittest.main()
